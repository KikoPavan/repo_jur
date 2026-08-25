"""Executable Stage 10 conformance and regression checks."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path

import pymupdf
import pytest

from pipeline_juridico.config import IngressConfig, PreflightLimits, RetrievalConfig
from pipeline_juridico.contracts import (
    CriticalValidationStatus,
    GateState,
    Phase1Artifacts,
    RouteTarget,
)
from pipeline_juridico.converter import convert_document
from pipeline_juridico.domain_router import (
    RoutingBlockedError,
    RoutingContext,
    RoutingDecision,
    RoutingReasonCode,
    route,
)
from pipeline_juridico.evidence import LocalFilesystemObjectStorageGateway
from pipeline_juridico.hashing import sha256_file
from pipeline_juridico.ingress import ArchiveSecurityError, IngressError, preflight_envelope
from pipeline_juridico.models import Metodo, ResultadoPagina
from pipeline_juridico.process_producer import produce_process
from pipeline_juridico.process_semantic_review import ProcessReviewResult, ReviewState
from pipeline_juridico.process_storage import validate_process_producer_context
from pipeline_juridico.retrieval.index import SqliteFts5Index, enumerate_concepts
from pipeline_juridico.retrieval.search import search
from pipeline_juridico.report import strip_technical_routing_metadata
from pipeline_juridico.validator import (
    MarkdownValidationError,
    validate_markdown_matches_report,
    validate_page_markers,
)


REAL_CORPUS_FILENAMES = (
    "AINTARESP_1462304-PA.pdf",
    "REsp_1704551-SP.pdf",
    "Inf0024E.pdf",
    "L10.406_CC_2002.pdf",
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REAL_CORPUS_ROOT = PROJECT_ROOT / "input"
GOLDEN_ROOT = Path(__file__).with_name("golden")


def assert_normalized_markdown_equal(actual: str, expected: str) -> None:
    """Assert Markdown identity after deterministic whitespace normalization."""

    def normalize(markdown: str) -> str:
        unix_lines = markdown.replace("\r\n", "\n").replace("\r", "\n")
        stripped_lines = [
            re.sub(r"[^\S\n]+", " ", line).strip()
            for line in unix_lines.split("\n")
        ]
        return re.sub(r"\n+", "\n", "\n".join(stripped_lines)).strip()

    assert normalize(actual) == normalize(expected)


@pytest.fixture(scope="session")
def real_corpus_pdfs() -> dict[str, Path]:
    paths = {name: REAL_CORPUS_ROOT / name for name in REAL_CORPUS_FILENAMES}
    missing = [path for path in paths.values() if not path.is_file()]
    if missing:
        missing_names = ", ".join(path.name for path in missing)
        raise pytest.UsageError(
            "Real-corpus regression environment is incomplete. Missing PDF(s) "
            f"under {REAL_CORPUS_ROOT}: {missing_names}. These raw fixtures are "
            "gitignored; link or copy them from /home/kiko/devops/repo_jur/input, "
            "or obtain the approved corpus files from the project maintainer, "
            "before running the regression suite."
        )
    return paths


@pytest.fixture(scope="session")
def real_corpus_markdown(
    real_corpus_pdfs: dict[str, Path],
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, str]:
    workspace = tmp_path_factory.mktemp("real-corpus-conversion")
    converted: dict[str, str] = {}
    for filename, pdf_path in real_corpus_pdfs.items():
        stem = Path(filename).stem
        markdown, _report = convert_document(
            pdf_path=pdf_path,
            output_path=workspace / f"{stem}.md",
            temp_root=workspace / f"{stem}-pages",
            use_ocr=False,
        )
        converted[filename] = strip_technical_routing_metadata(markdown)
    return converted


class StorageMutationWatcher:
    """Snapshot a storage tree and report every created, changed, or removed file."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.before = self._snapshot()

    def _snapshot(self) -> dict[str, str]:
        if not self.root.exists():
            return {}
        return {
            path.relative_to(self.root).as_posix(): hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        }

    @property
    def mutations(self) -> set[str]:
        after = self._snapshot()
        return {
            name
            for name in self.before.keys() | after.keys()
            if self.before.get(name) != after.get(name)
        }

    def assert_zero_writes(self) -> None:
        assert self.mutations == set(), f"storage mutations detected: {self.mutations}"


def _pdf_bytes() -> bytes:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "prova sintetica")
    data = document.tobytes()
    document.close()
    return data


def _manifest(handoff_id: str, evidence: bytes, candidate: str | None = None) -> bytes:
    payload = {
        "protocol_version": "1.0",
        "handoff_id": handoff_id,
        "evidence_reference": "evidence.pdf",
        "source_origin": "https://example.invalid/evidence.pdf",
        "retrieved_at": "2026-08-24T12:00:00-03:00",
        "collector": "process:conformance",
        "media_type": "application/pdf",
        "byte_size": len(evidence),
    }
    if candidate is not None:
        payload["candidate_sha256"] = candidate
    return json.dumps(payload, sort_keys=True).encode()


def _envelope(
    path: Path,
    evidence: bytes,
    *,
    candidate: str | None = None,
    evidence_name: str = "evidence.pdf",
    duplicate: bool = False,
) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", _manifest(path.stem, evidence, candidate))
        archive.writestr(evidence_name, evidence)
        if duplicate:
            archive.writestr(evidence_name, evidence)
    return path


def _mark_encrypted(path: Path) -> None:
    """Set the traditional-encryption bit in local and central ZIP headers."""

    data = bytearray(path.read_bytes())
    position = 0
    while position < len(data):
        signature = bytes(data[position : position + 4])
        if signature == b"PK\x03\x04":
            flags_at = position + 6
            name_length, extra_length = struct.unpack_from("<HH", data, position + 26)
            compressed_size = struct.unpack_from("<I", data, position + 18)[0]
            position += 30 + name_length + extra_length + compressed_size
        elif signature == b"PK\x01\x02":
            flags_at = position + 8
            name_length, extra_length, comment_length = struct.unpack_from(
                "<HHH", data, position + 28
            )
            position += 46 + name_length + extra_length + comment_length
        elif signature == b"PK\x05\x06":
            break
        else:
            position += 1
            continue
        flags = struct.unpack_from("<H", data, flags_at)[0]
        struct.pack_into("<H", data, flags_at, flags | 1)
    path.write_bytes(data)


def _ingress_config(tmp_path: Path) -> IngressConfig:
    return IngressConfig(
        inbox_dir=tmp_path / "inbox",
        quarantine_dir=tmp_path / "quarantine",
        object_storage_root=tmp_path / "objects",
        ingress_state_dir=tmp_path / "state",
    )


def _phase1(evidence: Path, *, gate: str = "PASS") -> Phase1Artifacts:
    markdown = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nLiteral\n"
    digest = sha256_file(evidence)
    report = {
        "schema_version": "1.0",
        "execution_id": "conformance-process",
        "input": {"sha256": digest, "byte_size": evidence.stat().st_size, "page_count": 1},
        "phase1": {
            "implementation": "shared-core",
            "implementation_version": "1.0",
            "logical_processing_version": "1.0",
            "relevant_config_fingerprint": "conformance-config",
        },
        "result": {"quality_gate": gate, "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": hashlib.sha256(markdown.encode()).hexdigest()},
        "pages": [{
            "page_number": 1,
            "method": "texto_nativo",
            "char_count": len(markdown),
            "warnings": [],
            "errors": [],
            "truncated": False,
        }],
        "telemetry": {},
    }
    return Phase1Artifacts(markdown, json.dumps(report))


def _write_legal_concept(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '---\ntype: "legislacao"\nstatus: "vigente"\ntags: ["civil"]\n---\n'
        "Lei 10.406 conformidade isolamento\n",
        encoding="utf-8",
    )


@pytest.mark.conformance
def test_1_1_zip_preflight_conformance(tmp_path: Path) -> None:
    evidence = _pdf_bytes()
    config = _ingress_config(tmp_path)
    storage = LocalFilesystemObjectStorageGateway(config.object_storage_root)
    valid = _envelope(tmp_path / "valid.zip", evidence)

    result = preflight_envelope(valid, config, PreflightLimits(), storage)
    preserved = Path(result.evidence_reference.removeprefix("file://"))
    assert preserved.read_bytes() == evidence

    encrypted = _envelope(tmp_path / "encrypted.zip", evidence)
    _mark_encrypted(encrypted)
    malformed = tmp_path / "malformed.zip"
    malformed.write_bytes(b"not a zip")
    duplicate = _envelope(tmp_path / "duplicate.zip", evidence, duplicate=True)
    traversal = _envelope(
        tmp_path / "traversal.zip", evidence, evidence_name="../escape.pdf"
    )
    for archive in (encrypted, malformed, duplicate, traversal):
        with pytest.raises(ArchiveSecurityError):
            preflight_envelope(archive, config, PreflightLimits(), storage)


@pytest.mark.conformance
def test_1_2_sha_preservation_conformance(tmp_path: Path) -> None:
    evidence = _pdf_bytes()
    digest = hashlib.sha256(evidence).hexdigest()
    config = _ingress_config(tmp_path)
    storage = LocalFilesystemObjectStorageGateway(config.object_storage_root)
    accepted = _envelope(tmp_path / "sha-ok.zip", evidence, candidate=digest)

    result = preflight_envelope(accepted, config, PreflightLimits(), storage)
    preserved = Path(result.evidence_reference.removeprefix("file://"))
    state = json.loads(next(config.ingress_state_dir.glob("*.json")).read_text())
    assert sha256_file(preserved) == result.official_evidence_sha256 == digest
    assert state["official_evidence_sha256"] == digest

    mismatch = _envelope(tmp_path / "sha-bad.zip", evidence, candidate="0" * 64)
    before = set(config.object_storage_root.iterdir())
    with pytest.raises(IngressError, match="candidate_sha256"):
        preflight_envelope(mismatch, config, PreflightLimits(), storage)
    assert set(config.object_storage_root.iterdir()) == before


@pytest.mark.conformance
def test_1_3_page_records_and_markers_conformance() -> None:
    markdown = (
        "[[Pág. 1]]\n<!-- método: texto_nativo -->\nPrimeira\n"
        "[[Pág. 2]]\n<!-- método: ocr_integral -->\nSegunda\n"
    )
    pages = [
        ResultadoPagina(1, Metodo.texto_nativo, 8),
        ResultadoPagina(2, Metodo.ocr_integral, 7),
    ]
    validate_page_markers(markdown, expected_page_count=2)
    validate_markdown_matches_report(markdown, pages)

    invalid_documents = (
        markdown.replace("[[Pág. 2]]", "[[Pagina 2]]"),
        markdown.replace("<!-- método: ocr_integral -->", "<!-- metodo: ocr_integral -->"),
        markdown.replace("[[Pág. 2]]", "[[Pág. 3]]"),
        markdown.replace("[[Pág. 2]]", "[[Pág. 1]]"),
    )
    for invalid in invalid_documents:
        with pytest.raises(MarkdownValidationError):
            validate_page_markers(invalid, expected_page_count=2)

    with pytest.raises(MarkdownValidationError, match="Método divergente"):
        validate_markdown_matches_report(
            markdown, [pages[0], ResultadoPagina(2, Metodo.hibrido, 7)]
        )


@pytest.mark.conformance
def test_1_4_quality_gate_and_producer_conformance(tmp_path: Path) -> None:
    assert {state.value for state in GateState} == {
        "PASS", "PASS_WITH_WARNINGS", "FAIL"
    }
    evidence = tmp_path / "evidence.pdf"
    evidence.write_bytes(b"synthetic evidence")
    entered_producer = False

    def route_then_produce(artifacts: Phase1Artifacts) -> None:
        nonlocal entered_producer
        decision = route(
            artifacts,
            critical_status=CriticalValidationStatus.OK,
            routing_context=RoutingContext(RouteTarget.JUDICIAL_PROCESS),
        )
        entered_producer = True
        produce_process(  # pragma: no cover - FAIL must stop before this line
            artifacts,
            decision,
            ProcessReviewResult(ReviewState.OK, (), (), (), ()),
            validate_process_producer_context(
                {"type": "Decisao", "evidence_resource": str(evidence)}
            ),
            process_root=tmp_path / "var/process",
            bundle_root=tmp_path / "repo_jur/bundle",
        )

    with pytest.raises(RoutingBlockedError, match="FAIL") as blocked:
        route_then_produce(_phase1(evidence, gate="FAIL"))
    assert blocked.value.reason == "fail_gate"
    assert not entered_producer
    assert not (tmp_path / "var/process").exists()


@pytest.mark.conformance
def test_1_5_storage_boundary_isolation_conformance(tmp_path: Path) -> None:
    bundle = tmp_path / "repo_jur/bundle"
    _write_legal_concept(bundle / "legislacao/existing.md")
    watcher = StorageMutationWatcher(bundle)
    process_root = tmp_path / "var/process"
    evidence = tmp_path / "evidence.pdf"
    evidence.write_bytes(b"synthetic process evidence")
    artifacts = _phase1(evidence)
    decision = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=RoutingContext(RouteTarget.JUDICIAL_PROCESS),
    )
    result = produce_process(
        artifacts,
        decision,
        ProcessReviewResult(ReviewState.OK, (), (), (), ()),
        validate_process_producer_context(
            {"type": "Decisao", "evidence_resource": str(evidence)}
        ),
        process_root=process_root,
        bundle_root=bundle,
    )

    watcher.assert_zero_writes()
    assert result.written and result.concept_path is not None
    assert result.concept_path.is_relative_to(process_root.resolve())
    assert {path for path in process_root.rglob("*") if path.is_file()} == {
        result.concept_path
    }


@pytest.mark.conformance
def test_1_6_retrieval_zero_write_and_isolation_conformance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle = tmp_path / "repo_jur/bundle"
    _write_legal_concept(bundle / "legislacao/codigo.md")
    process_root = tmp_path / "var/process"
    process_sentinel = process_root / "decisao/secret.md"
    process_sentinel.parent.mkdir(parents=True)
    process_sentinel.write_text("judicial-process-only", encoding="utf-8")
    bundle_watcher = StorageMutationWatcher(bundle)
    process_watcher = StorageMutationWatcher(process_root)
    config = RetrievalConfig(derived_root=tmp_path / "var/retrieval")

    original_open = Path.open

    def guarded_open(path: Path, *args: object, **kwargs: object):
        resolved = path.resolve()
        if resolved == process_root.resolve() or resolved.is_relative_to(process_root.resolve()):
            raise AssertionError(f"retrieval accessed judicial process storage: {resolved}")
        return original_open(path, *args, **kwargs)

    with monkeypatch.context() as retrieval_guard:
        retrieval_guard.setattr(Path, "open", guarded_open)
        backend = SqliteFts5Index(bundle, config)
        backend.rebuild(enumerate_concepts(bundle), config)
        backend.sync(enumerate_concepts(bundle), config)
        outcome = search(bundle, config.derived_root, "conformidade", config=config)

    assert outcome.results
    bundle_watcher.assert_zero_writes()
    process_watcher.assert_zero_writes()
    assert backend.database_path.is_relative_to(config.derived_root)


@pytest.mark.regression
def test_3_1_real_corpus_citation_preservation(
    real_corpus_markdown: dict[str, str],
) -> None:
    markdown = real_corpus_markdown["L10.406_CC_2002.pdf"]
    critical_tokens = (
        "Art. 1º Toda pessoa é capaz de direitos e deveres na ordem civil.",
        "Art. 2º A personalidade civil da pessoa começa do nascimento com vida;",
        "Parágrafo único. A capacidade dos indígenas será regulada por legislação especial.",
    )

    for token in critical_tokens:
        assert token in markdown, f"critical legislative token was altered: {token!r}"


@pytest.mark.regression
def test_3_2_real_corpus_reading_order(
    real_corpus_markdown: dict[str, str],
) -> None:
    expected_sequences = {
        "AINTARESP_1462304-PA.pdf": (
            "Requer, ao final, o provimento do especial com a atribuição do valor de",
            "R$ 10.000,00 (dez mil reais) à causa.",
            "Diante do exposto, DOU PARCIAL PROVIMENTO ao agravo",
            "interno, apenas para afastar a Súmula 283 do STF.",
        ),
        "Inf0024E.pdf": (
            "PROCESSO",
            "RAMO DO DIREITO",
            "TEMA",
            "DESTAQUE",
            "INFORMAÇÕES DO INTEIRO TEOR",
            "INFORMAÇÕES ADICIONAIS",
        ),
    }

    for filename, phrases in expected_sequences.items():
        markdown = real_corpus_markdown[filename]
        positions = [markdown.index(phrase) for phrase in phrases]
        assert positions == sorted(positions), (
            f"unexpected paragraph/heading reading order in {filename}: {phrases}"
        )


@pytest.mark.regression
def test_3_3_real_corpus_heading_and_repetitive_element_cleanup(
    real_corpus_markdown: dict[str, str],
) -> None:
    resp = real_corpus_markdown["REsp_1704551-SP.pdf"]
    civil_code = real_corpus_markdown["L10.406_CC_2002.pdf"]

    assert "RECURSO ESPECIAL Nº 1.704.551 - SP" in resp
    assert "O propósito recursal consiste em determinar" in resp
    assert "Página 1 de 14" not in resp
    assert "www.stj.jus.br" not in resp
    assert "Código de Controle do Documento:" not in resp

    assert "LEI Nº 10.406, DE 10 DE JANEIRO DE 2002" in civil_code
    assert "Art. 2º A personalidade civil da pessoa" in civil_code
    assert "30/11/24, 19:06 L10406compilada" not in civil_code
    assert "https://www.planalto.gov.br/ccivil_03/leis/2002/" not in civil_code


@pytest.mark.regression
def test_3_4_golden_file_assertions(
    real_corpus_markdown: dict[str, str],
) -> None:
    for filename in REAL_CORPUS_FILENAMES:
        expected_path = GOLDEN_ROOT / f"{Path(filename).stem}.md"
        assert expected_path.is_file(), f"missing git-tracked golden: {expected_path}"
        assert_normalized_markdown_equal(
            real_corpus_markdown[filename],
            expected_path.read_text(encoding="utf-8"),
        )
