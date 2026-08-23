"""Deterministic concept-level lexical index over the canonical legal bundle."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence, runtime_checkable

from pipeline_juridico.config import RetrievalConfig

INDEX_SCHEMA_VERSION = "1"
INDEXER_LOGICAL_VERSION = "1"
FILTER_FIELDS = (
    "repo_jur_lei_numero",
    "repo_jur_lei_ano",
    "repo_jur_lei_esfera",
    "repo_jur_lei_tipo",
    "repo_jur_processo_numero",
    "repo_jur_tribunal",
    "repo_jur_relator",
    "repo_jur_data_julgamento",
    "repo_jur_ramo_direito",
    "repo_jur_precedente_numero",
    "repo_jur_precedente_status",
    "repo_jur_tema_numero",
)
_TYPE_TREES = ("legislacao", "jurisprudencia", "temas", "precedentes")
_RESERVED_NAMES = {"index.md", "log.md"}


@dataclass(frozen=True)
class CanonicalConcept:
    concept_id: str
    path: Path
    metadata: Mapping[str, Any]
    body: str


@dataclass(frozen=True)
class IndexRecord:
    concept_id: str
    content_fingerprint: str
    index_schema_version: str
    indexer_logical_version: str
    index_config_fingerprint: str
    type: str | None
    status: str | None
    tags: str
    indexed_text: str
    repo_jur_lei_numero: str | None = None
    repo_jur_lei_ano: str | None = None
    repo_jur_lei_esfera: str | None = None
    repo_jur_lei_tipo: str | None = None
    repo_jur_processo_numero: str | None = None
    repo_jur_tribunal: str | None = None
    repo_jur_relator: str | None = None
    repo_jur_data_julgamento: str | None = None
    repo_jur_ramo_direito: str | None = None
    repo_jur_precedente_numero: str | None = None
    repo_jur_precedente_status: str | None = None
    repo_jur_tema_numero: str | None = None


@dataclass(frozen=True)
class IndexState:
    status: str
    reason: str


@dataclass(frozen=True)
class SyncResult:
    operations: tuple[str, ...]
    state: IndexState


@runtime_checkable
class LexicalIndexBackend(Protocol):
    def build(
        self, concepts: Sequence[CanonicalConcept], config: RetrievalConfig
    ) -> SyncResult: ...

    def sync(
        self, concepts: Sequence[CanonicalConcept], config: RetrievalConfig
    ) -> SyncResult: ...

    def search(
        self, query: str, filters: Mapping[str, Any], limit: int
    ) -> list[str]: ...


def derive_concept_id(path: Path, bundle_root: Path) -> str:
    relative = path.resolve().relative_to(bundle_root.resolve())
    if relative.suffix != ".md":
        raise ValueError("concept path must be Markdown")
    return relative.with_suffix("").as_posix()


def parse_canonical_document(text: str) -> tuple[dict[str, Any], str]:
    """Parse the Producer's deterministic JSON-scalar YAML subset."""

    if not text.startswith("---\n"):
        return {}, text
    boundary = text.find("\n---\n", 4)
    if boundary < 0:
        return {}, text
    metadata: dict[str, Any] = {}
    for line in text[4:boundary].splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        try:
            metadata[key.strip()] = json.loads(raw.strip())
        except json.JSONDecodeError:
            metadata[key.strip()] = raw.strip()
    return metadata, text[boundary + 5 :]


def enumerate_concepts(bundle_root: Path) -> list[CanonicalConcept]:
    root = Path(bundle_root).resolve()
    concepts: list[CanonicalConcept] = []
    for tree_name in _TYPE_TREES:
        tree = root / tree_name
        if not tree.is_dir():
            continue
        for path in sorted(tree.rglob("*.md"), key=lambda item: item.as_posix()):
            if path.name in _RESERVED_NAMES or not path.is_file():
                continue
            metadata, body = parse_canonical_document(
                path.read_text(encoding="utf-8")
            )
            concepts.append(
                CanonicalConcept(
                    concept_id=derive_concept_id(path, root),
                    path=path,
                    metadata=metadata,
                    body=body,
                )
            )
    return sorted(concepts, key=lambda concept: concept.concept_id)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_fingerprint(concept: CanonicalConcept) -> str:
    metadata = {
        key: concept.metadata.get(key)
        for key in ("type", "status", "tags", *FILTER_FIELDS)
        if key in concept.metadata
    }
    payload = _stable_json({"body": concept.body, "metadata": metadata})
    return sha256(payload.encode("utf-8")).hexdigest()


def index_config_fingerprint(config: RetrievalConfig) -> str:
    from .chunking import ChunkingProfile

    chunk_profile = ChunkingProfile()
    payload = {
        "filter_schema_version": config.filter_schema_version,
        "filter_vocabulary": config.filter_vocabulary,
        "public_to_canonical_field": config.public_to_canonical_field,
        "search_default_limit": config.search_default_limit,
        "search_max_limit": config.search_max_limit,
        "chunking_profile_version": chunk_profile.profile_version,
        "chunking_profile_config_fingerprint": chunk_profile.config_fingerprint(),
    }
    return sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def _record(concept: CanonicalConcept, config: RetrievalConfig) -> IndexRecord:
    metadata = concept.metadata
    indexed_values = [
        str(metadata[key])
        for key in ("type", "status", "tags", *FILTER_FIELDS)
        if metadata.get(key) is not None
    ]
    values = {
        field: None if metadata.get(field) is None else str(metadata[field])
        for field in FILTER_FIELDS
    }
    return IndexRecord(
        concept_id=concept.concept_id,
        content_fingerprint=content_fingerprint(concept),
        index_schema_version=INDEX_SCHEMA_VERSION,
        indexer_logical_version=INDEXER_LOGICAL_VERSION,
        index_config_fingerprint=index_config_fingerprint(config),
        type=None if metadata.get("type") is None else str(metadata["type"]),
        status=None if metadata.get("status") is None else str(metadata["status"]),
        tags=_stable_json(metadata.get("tags", [])),
        indexed_text="\n".join((*indexed_values, concept.body)),
        **values,
    )


def _write_atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def persist_chunk_sets(
    concepts: Sequence[CanonicalConcept], config: RetrievalConfig
) -> None:
    """Persist independently valid, fully rebuildable chunk sets."""
    from .chunking import CHUNKER_LOGICAL_VERSION, ChunkingProfile, chunk_concept

    chunks_root = config.derived_root / "chunks"
    expected: set[Path] = set()
    profile = ChunkingProfile()
    for concept in concepts:
        chunk_set = chunk_concept(concept, profile)
        path = chunks_root / f"{concept.concept_id}.json"
        expected.add(path.resolve())
        payload = {
            "concept_id": chunk_set.concept_id,
            "chunk_set_fingerprint": chunk_set.chunk_set_fingerprint,
            "profile_version": profile.profile_version,
            "profile_config_fingerprint": profile.config_fingerprint(),
            "chunker_logical_version": CHUNKER_LOGICAL_VERSION,
            "content_fingerprint": content_fingerprint(concept),
            "chunks": [asdict(chunk) for chunk in chunk_set.chunks],
        }
        _write_atomic_json(path, payload)
    if chunks_root.is_dir():
        for path in chunks_root.rglob("*.json"):
            if path.resolve() not in expected:
                path.unlink()


class SqliteFts5Index:
    """SQLite FTS5 reference backend; all writes stay under ``derived_root``."""

    def __init__(self, bundle_root: Path, config: RetrievalConfig) -> None:
        self.bundle_root = Path(bundle_root).resolve()
        self.config = config
        derived = config.derived_root.resolve()
        if derived == self.bundle_root or derived.is_relative_to(self.bundle_root):
            raise ValueError("retrieval derived root must remain outside bundle/")
        self.database_path = derived / "index" / "lexical.sqlite3"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _create_schema(connection: sqlite3.Connection) -> None:
        columns = ",\n".join(f"{field} TEXT" for field in FILTER_FIELDS)
        connection.executescript(
            f"""
            CREATE TABLE records (
                concept_id TEXT PRIMARY KEY,
                content_fingerprint TEXT NOT NULL,
                index_schema_version TEXT NOT NULL,
                indexer_logical_version TEXT NOT NULL,
                index_config_fingerprint TEXT NOT NULL,
                type TEXT,
                status TEXT,
                tags TEXT NOT NULL,
                indexed_text TEXT NOT NULL,
                {columns}
            );
            CREATE VIRTUAL TABLE records_fts USING fts5(
                concept_id UNINDEXED,
                indexed_text,
                tokenize='unicode61'
            );
            """
        )

    @staticmethod
    def _insert(connection: sqlite3.Connection, record: IndexRecord) -> None:
        values = asdict(record)
        columns = tuple(values)
        connection.execute(
            f"INSERT INTO records ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
            tuple(values[column] for column in columns),
        )
        connection.execute(
            "INSERT INTO records_fts(concept_id, indexed_text) VALUES (?, ?)",
            (record.concept_id, record.indexed_text),
        )

    def _write_observability(
        self, event: str, operations: tuple[str, ...], state: IndexState
    ) -> None:
        root = self.config.derived_root / "observability"
        _write_atomic_json(root / "index-state.json", asdict(state))
        _write_atomic_json(
            root / "last-index-event.json",
            {"event": event, "operations": list(operations), "state": state.status},
        )

    def rebuild(
        self, concepts: Sequence[CanonicalConcept], config: RetrievalConfig
    ) -> SyncResult:
        self.config = config
        self.database_path = config.derived_root / "index" / "lexical.sqlite3"
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.database_path.unlink(missing_ok=True)
        ordered = sorted(concepts, key=lambda concept: concept.concept_id)
        with self._connect() as connection:
            self._create_schema(connection)
            for concept in ordered:
                self._insert(connection, _record(concept, config))
        persist_chunk_sets(ordered, config)
        operations = tuple("CREATE" for _ in ordered)
        state = IndexState("fresh", "fingerprints_match")
        self._write_observability("rebuild", operations, state)
        return SyncResult(operations, state)

    def build(
        self, concepts: Sequence[CanonicalConcept], config: RetrievalConfig
    ) -> SyncResult:
        return self.rebuild(concepts, config)

    def records(self) -> list[IndexRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM records ORDER BY concept_id"
            ).fetchall()
        return [IndexRecord(**dict(row)) for row in rows]

    def state(
        self, concepts: Sequence[CanonicalConcept], config: RetrievalConfig
    ) -> IndexState:
        if not self.database_path.is_file():
            return IndexState("degraded", "index_absent")
        try:
            stored = {record.concept_id: record for record in self.records()}
        except sqlite3.DatabaseError:
            return IndexState("degraded", "index_corrupt")
        expected = {
            concept.concept_id: _record(concept, config) for concept in concepts
        }
        if stored and any(
            record.index_config_fingerprint != index_config_fingerprint(config)
            for record in stored.values()
        ):
            return IndexState("stale", "config_fingerprint_mismatch")
        if stored.keys() != expected.keys():
            return IndexState("stale", "concept_set_mismatch")
        if any(
            stored[key].index_schema_version != INDEX_SCHEMA_VERSION
            or stored[key].indexer_logical_version != INDEXER_LOGICAL_VERSION
            or stored[key].content_fingerprint != expected[key].content_fingerprint
            for key in stored
        ):
            return IndexState("stale", "record_fingerprint_mismatch")
        return IndexState("fresh", "fingerprints_match")

    def sync(
        self, concepts: Sequence[CanonicalConcept], config: RetrievalConfig
    ) -> SyncResult:
        if not self.database_path.is_file():
            return self.rebuild(concepts, config)
        current_state = self.state(concepts, config)
        if current_state.reason == "config_fingerprint_mismatch":
            rebuilt = self.rebuild(concepts, config)
            result = SyncResult(("CONFIG", *rebuilt.operations), rebuilt.state)
            self._write_observability("sync", result.operations, result.state)
            return result
        if current_state.status == "degraded":
            return self.rebuild(concepts, config)
        old = {record.concept_id: record for record in self.records()}
        new = {concept.concept_id: _record(concept, config) for concept in concepts}
        deleted = sorted(old.keys() - new.keys())
        created = sorted(new.keys() - old.keys())
        updated = sorted(
            key
            for key in old.keys() & new.keys()
            if old[key].content_fingerprint != new[key].content_fingerprint
        )
        operations = tuple(
            ["DELETE"] * len(deleted)
            + ["CREATE"] * len(created)
            + ["CONTENT UPDATE"] * len(updated)
        )
        if operations:
            with self._connect() as connection:
                for key in (*deleted, *updated):
                    connection.execute("DELETE FROM records WHERE concept_id = ?", (key,))
                    connection.execute("DELETE FROM records_fts WHERE concept_id = ?", (key,))
                for key in (*created, *updated):
                    self._insert(connection, new[key])
        persist_chunk_sets(concepts, config)
        state = self.state(concepts, config)
        self._write_observability("sync", operations, state)
        return SyncResult(operations, state)

    def search(
        self, query: str, filters: Mapping[str, Any], limit: int
    ) -> list[str]:
        import re

        phrases = re.findall(r'"([^"]+)"', query)
        remainder = re.sub(r'"[^"]+"', " ", query)
        terms = phrases + re.findall(r"[^\s]+", remainder)
        normalized_terms = []
        for term in terms:
            tokens = re.findall(r"\w+", term, flags=re.UNICODE)
            if tokens:
                normalized_terms.append('"' + " ".join(tokens).replace('"', '""') + '"')
        match_query = " AND ".join(normalized_terms)
        if not match_query:
            return []
        clauses = ["records_fts MATCH ?"]
        parameters: list[Any] = [match_query]
        for key, value in filters.items():
            if key == "tags":
                wanted = value if isinstance(value, (list, tuple)) else [value]
                for tag in wanted:
                    clauses.append("EXISTS (SELECT 1 FROM json_each(records.tags) WHERE value = ?)")
                    parameters.append(tag)
                continue
            if key not in {"type", "status", *FILTER_FIELDS}:
                raise ValueError(f"unsupported index filter: {key}")
            clauses.append(f"records.{key} = ?")
            parameters.append(str(value))
        parameters.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT records.concept_id FROM records_fts "
                "JOIN records USING (concept_id) WHERE "
                + " AND ".join(clauses)
                + " ORDER BY bm25(records_fts), records.concept_id LIMIT ?",
                parameters,
            ).fetchall()
        return [str(row[0]) for row in rows]
