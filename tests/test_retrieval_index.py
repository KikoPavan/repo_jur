from __future__ import annotations

import ast
import json
import subprocess
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from pipeline_juridico.config import RetrievalConfig
from pipeline_juridico.retrieval.index import (
    INDEXER_LOGICAL_VERSION,
    INDEX_SCHEMA_VERSION,
    IndexState,
    LexicalIndexBackend,
    SqliteFts5Index,
    derive_concept_id,
    enumerate_concepts,
    index_config_fingerprint,
)
from pipeline_juridico.retrieval.chunking import ChunkingProfile


def _document(body: str, **metadata: object) -> str:
    values = {"type": "legislacao", "status": "vigente", "tags": ["civil"]}
    values.update(metadata)
    lines = ["---", *(f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in values.items()), "---", body]
    return "\n".join(lines) + "\n"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _bundle(tmp_path: Path) -> Path:
    bundle = tmp_path / "bundle"
    _write(bundle / "legislacao" / "codigo-civil.md", _document("Lei 10.406"))
    _write(bundle / "jurisprudencia" / "stj" / "resp.md", _document("REsp 1.704.551", type="jurisprudencia"))
    _write(bundle / "temas" / "index.md", "reserved\n")
    _write(bundle / "precedentes" / "log.md", "reserved\n")
    _write(bundle / "temas" / "notes.txt", "not markdown\n")
    _write(bundle / "fora-da-arvore" / "ignorar.md", _document("ignored"))
    return bundle


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _backend(tmp_path: Path, bundle: Path) -> SqliteFts5Index:
    return SqliteFts5Index(bundle, RetrievalConfig(derived_root=tmp_path / "state"))


def test_walker_indexes_only_eligible_concepts_in_deterministic_order(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)

    concepts = enumerate_concepts(bundle)

    assert [concept.concept_id for concept in concepts] == [
        "jurisprudencia/stj/resp",
        "legislacao/codigo-civil",
    ]
    assert derive_concept_id(bundle / "legislacao" / "codigo-civil.md", bundle) == "legislacao/codigo-civil"


def test_backend_protocol_and_build_are_zero_write(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    backend = _backend(tmp_path, bundle)
    before = _hash_tree(bundle)

    assert isinstance(backend, LexicalIndexBackend)
    result = backend.build(enumerate_concepts(bundle), backend.config)

    assert result.operations == ("CREATE", "CREATE")
    assert _hash_tree(bundle) == before
    assert backend.database_path.is_file()
    assert backend.database_path.is_relative_to(backend.config.derived_root)
    assert [record.concept_id for record in backend.records()] == [
        "jurisprudencia/stj/resp",
        "legislacao/codigo-civil",
    ]


def test_backend_rejects_derived_root_inside_bundle(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    with pytest.raises(ValueError, match="outside bundle"):
        SqliteFts5Index(bundle, RetrievalConfig(derived_root=bundle / "derived"))


def test_sync_classifies_create_update_move_delete_and_noop(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    backend = _backend(tmp_path, bundle)
    backend.rebuild(enumerate_concepts(bundle), backend.config)
    original = {record.concept_id: record for record in backend.records()}

    assert backend.sync(enumerate_concepts(bundle), backend.config).operations == ()

    created = bundle / "temas" / "novo.md"
    _write(created, _document("Tema novo", type="temas"))
    assert backend.sync(enumerate_concepts(bundle), backend.config).operations == ("CREATE",)

    existing = bundle / "legislacao" / "codigo-civil.md"
    _write(existing, _document("Lei 10.406 atualizada", repo_jur_lei_ano=2002))
    update = backend.sync(enumerate_concepts(bundle), backend.config)
    assert update.operations == ("CONTENT UPDATE",)
    current = {record.concept_id: record for record in backend.records()}
    assert current["legislacao/codigo-civil"].content_fingerprint != original["legislacao/codigo-civil"].content_fingerprint

    moved = bundle / "precedentes" / "novo-nome.md"
    moved.parent.mkdir(parents=True, exist_ok=True)
    created.rename(moved)
    move = backend.sync(enumerate_concepts(bundle), backend.config)
    assert move.operations == ("DELETE", "CREATE")
    assert "temas/novo" not in {record.concept_id for record in backend.records()}
    assert "precedentes/novo-nome" in {record.concept_id for record in backend.records()}

    moved.unlink()
    assert backend.sync(enumerate_concepts(bundle), backend.config).operations == ("DELETE",)


def test_stale_detection_covers_content_metadata_and_versions(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    backend = _backend(tmp_path, bundle)
    backend.rebuild(enumerate_concepts(bundle), backend.config)
    records = backend.records()

    assert backend.state(enumerate_concepts(bundle), backend.config) == IndexState("fresh", "fingerprints_match")
    assert all(record.index_schema_version == INDEX_SCHEMA_VERSION for record in records)
    assert all(record.indexer_logical_version == INDEXER_LOGICAL_VERSION for record in records)
    assert all(record.index_config_fingerprint == index_config_fingerprint(backend.config) for record in records)

    path = bundle / "legislacao" / "codigo-civil.md"
    _write(path, _document("Lei 10.406", status="revogada", tags=["civil", "historic"] ))
    assert backend.state(enumerate_concepts(bundle), backend.config).status == "stale"

    changed_config = replace(backend.config, search_default_limit=9)
    assert backend.state(enumerate_concepts(bundle), changed_config).reason == "config_fingerprint_mismatch"
    refreshed = backend.sync(enumerate_concepts(bundle), changed_config)
    assert "CONFIG" in refreshed.operations
    assert backend.state(enumerate_concepts(bundle), changed_config).status == "fresh"


def test_index_config_fingerprint_preserves_v1_payload_value() -> None:
    config = RetrievalConfig()
    profile = ChunkingProfile()
    legacy_chunk_profile = {
        "profile_version": "1",
        "measurement_unit": "characters",
        "soft_limit": 6000,
        "hard_limit": 12000,
        "forced_split_overlap": 200,
    }
    legacy_chunk_config_fingerprint = sha256(
        json.dumps(legacy_chunk_profile, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload = {
        "filter_schema_version": config.filter_schema_version,
        "filter_vocabulary": config.filter_vocabulary,
        "public_to_canonical_field": config.public_to_canonical_field,
        "search_default_limit": config.search_default_limit,
        "search_max_limit": config.search_max_limit,
        "chunking_profile_version": profile.profile_version,
        "chunking_profile_config_fingerprint": legacy_chunk_config_fingerprint,
    }
    expected = sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    assert profile.config_fingerprint() == legacy_chunk_config_fingerprint
    assert index_config_fingerprint(config) == expected


def test_state_is_degraded_when_database_absent_or_corrupt(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    backend = _backend(tmp_path, bundle)
    assert backend.state(enumerate_concepts(bundle), backend.config).status == "degraded"
    backend.database_path.parent.mkdir(parents=True)
    backend.database_path.write_text("not sqlite", encoding="utf-8")
    assert backend.state(enumerate_concepts(bundle), backend.config).status == "degraded"


def test_rebuild_is_deterministic_zero_write_and_observable(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    backend = _backend(tmp_path, bundle)
    before = _hash_tree(bundle)

    first = backend.rebuild(enumerate_concepts(bundle), backend.config)
    first_records = backend.records()
    second = backend.rebuild(enumerate_concepts(bundle), backend.config)

    assert backend.records() == first_records
    assert first.operations == second.operations == ("CREATE", "CREATE")
    assert _hash_tree(bundle) == before
    assert (backend.config.derived_root / "observability" / "index-state.json").is_file()
    event = json.loads((backend.config.derived_root / "observability" / "last-index-event.json").read_text(encoding="utf-8"))
    assert event["event"] == "rebuild"
    assert "text_content" not in event


def test_worktree_derived_files_are_gitignored() -> None:
    repository_root = Path(__file__).resolve().parents[1]
    ignored = subprocess.run(
        ["git", "check-ignore", "-q", "var/retrieval/index/lexical.sqlite3"],
        cwd=repository_root,
        check=False,
    )
    assert ignored.returncode == 0


def test_retrieval_index_source_has_no_forbidden_coupling() -> None:
    package = Path(__file__).resolve().parents[1] / "src" / "pipeline_juridico" / "retrieval"
    forbidden = {"converter", "engines", "inspector", "ocr", "producer", "router", "llm", "semantic", "process_storage"}
    for path in (package / "index.py", package / "__init__.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = {
            part.lower()
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for name in ([node.module or ""] if isinstance(node, ast.ImportFrom) else [alias.name for alias in node.names])
            for part in name.split(".")
        }
        assert forbidden.isdisjoint(imports)
        assert "process-storage" not in source.lower()
