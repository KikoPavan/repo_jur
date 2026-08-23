from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pipeline_juridico.contracts import RouteTarget
from pipeline_juridico.process_producer import (
    PROCESS_PRODUCER_ACTOR, ProcessConceptCandidate,
    validate_process_candidate,
)
from pipeline_juridico.process_storage import (
    ProcessConceptType, ProcessProducerConfigurationError,
    ensure_outside_process_storage, guard_process_write,
    resolve_process_concept_path, validate_process_producer_context,
)

PROCESS_MODULES = [
    Path("src/pipeline_juridico/process_storage.py"),
    Path("src/pipeline_juridico/process_producer.py"),
    Path("src/pipeline_juridico/process_semantic_review.py"),
    Path("src/pipeline_juridico/process_producer_cli.py"),
]


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    return {
        alias.name.rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }


def _candidate(tmp_path: Path, *, sources: list[dict], singular: str | None = None,
               plural: dict | None = None) -> ProcessConceptCandidate:
    frontmatter: dict[str, object] = {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": sources,
    }
    if singular is not None:
        frontmatter["repo_jur_pdf_hash"] = singular
    if plural is not None:
        frontmatter["repo_jur_pdf_hashes"] = plural
    return ProcessConceptCandidate(
        ProcessConceptType.Decisao, frontmatter, "corpo\n", tmp_path / "x.md"
    )


def test_process_type_vocabulary_and_context() -> None:
    assert tuple(item.value for item in ProcessConceptType) == (
        "Peticao", "Contestacao", "Decisao", "Procuracao",
        "Testamento", "Anexo", "OutraPeca",
    )
    context = validate_process_producer_context(
        {"type": "Decisao", "evidence_resource": "evidence/Ação 10.pdf"}
    )
    assert context.type is ProcessConceptType.Decisao


@pytest.mark.parametrize("payload", [None, {}, {"type": "Other"},
    {"type": "Decisao", "unknown": True},
    {"type": "Decisao", "evidence_resource": " bad"}])
def test_invalid_context_is_rejected(payload) -> None:
    with pytest.raises(ProcessProducerConfigurationError):
        validate_process_producer_context(payload)


def test_positional_paths_are_deterministic_and_do_not_create_dirs(tmp_path: Path) -> None:
    root = tmp_path / "process"
    path = resolve_process_concept_path(
        ProcessConceptType.OutraPeca, "file:///tmp/Ação Nº 10.PDF", root
    )
    assert path == root / "outra_peca" / "acao_no_10.md"
    assert not root.exists()


def test_process_guard_enforces_domain_root_and_bundle(tmp_path: Path) -> None:
    root, bundle = tmp_path / "process", tmp_path / "bundle"
    target = root / "decisao" / "x.md"
    assert guard_process_write(
        acting_domain=RouteTarget.JUDICIAL_PROCESS, target=target,
        process_root=root, legal_bundle_root=bundle,
    ) == target.resolve()
    with pytest.raises(PermissionError):
        guard_process_write(
            acting_domain=RouteTarget.LEGAL_KNOWLEDGE, target=target,
            process_root=root, legal_bundle_root=bundle,
        )
    with pytest.raises(PermissionError):
        guard_process_write(
            acting_domain=RouteTarget.JUDICIAL_PROCESS, target=bundle / "x.md",
            process_root=root, legal_bundle_root=bundle,
        )


def test_state_directory_cannot_be_inside_process_storage(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ensure_outside_process_storage(tmp_path / "process/state", tmp_path / "process")


# 3.4 / 3.7 / 5.9 — source-inspection: no Legal coupling, no bundle guard,
# no retrieval artifacts, no legal vocabulary in any process module.
def test_process_modules_have_no_legal_or_retrieval_coupling() -> None:
    for module in PROCESS_MODULES:
        source = module.read_text()
        imported = _imported_modules(source)
        assert not any(name.startswith("legal") for name in imported)
        assert not imported & {
            "converter", "conversion_engine", "engines", "inspector",
            "evidence", "ocr", "openai", "google", "genai",
        }
        for forbidden in (
            "guard_legal_bundle_write", "shared_index", "semantic_model",
            "external_classification", "rerank", "chunk",
        ):
            assert forbidden not in source
        assert "bundle/" not in source
        assert "search(" not in source


def test_process_vocabulary_has_no_legal_type_values() -> None:
    values = {item.value for item in ProcessConceptType}
    assert not values & {
        "Legislacao", "Jurisprudencia", "TemaJuridico", "PrecedenteVinculante",
    }


# 3.5 — PDF cardinality: singular only for one PDF; plural mapping for 2+ PDFs;
# non-PDF sources stay in sources but never enter the hash mapping.
def test_single_pdf_candidate_uses_singular_field(tmp_path: Path) -> None:
    digest = "a" * 64
    candidate = _candidate(
        tmp_path,
        sources=[{"id": "pdf_1", "resource": "x.pdf",
                  "media_type": "application/pdf"}],
        singular=digest,
    )
    validate_process_candidate(candidate)
    assert "repo_jur_pdf_hashes" not in candidate.frontmatter


def test_multi_pdf_candidate_uses_plural_mapping(tmp_path: Path) -> None:
    first, second = "a" * 64, "b" * 64
    candidate = _candidate(
        tmp_path,
        sources=[
            {"id": "pdf_1", "resource": "a.pdf",
             "media_type": "application/pdf"},
            {"id": "pdf_2", "resource": "b.pdf",
             "media_type": "application/pdf"},
            {"id": "nota_1", "resource": "nota.txt",
             "media_type": "text/plain"},
        ],
        plural={"pdf_1": first, "pdf_2": second},
    )
    validate_process_candidate(candidate)
    assert "repo_jur_pdf_hash" not in candidate.frontmatter
    plural = candidate.frontmatter["repo_jur_pdf_hashes"]
    assert isinstance(plural, dict) and set(plural) == {"pdf_1", "pdf_2"}


@pytest.mark.parametrize("bad", [
    {"pdf_1": "a" * 64},              # missing pdf_2
    {"pdf_1": "a" * 64, "pdf_2": "Z" * 64},  # invalid hash
])
def test_multi_pdf_mapping_mismatch_is_rejected(tmp_path: Path, bad: dict) -> None:
    candidate = _candidate(
        tmp_path,
        sources=[
            {"id": "pdf_1", "resource": "a.pdf",
             "media_type": "application/pdf"},
            {"id": "pdf_2", "resource": "b.pdf",
             "media_type": "application/pdf"},
        ],
        plural=bad,
    )
    with pytest.raises(ProcessProducerConfigurationError):
        validate_process_candidate(candidate)


def test_both_pdf_hash_fields_together_are_rejected(tmp_path: Path) -> None:
    digest = "a" * 64
    candidate = _candidate(
        tmp_path,
        sources=[{"id": "pdf_1", "resource": "x.pdf",
                  "media_type": "application/pdf"}],
        singular=digest, plural={"pdf_1": digest},
    )
    with pytest.raises(ProcessProducerConfigurationError, match="exclusive"):
        validate_process_candidate(candidate)


# 3.3 — Candidate frontmatter: type first, approved producer actor, no verified.
def test_candidate_frontmatter_follows_process_profile(tmp_path: Path) -> None:
    digest = "a" * 64
    candidate = _candidate(
        tmp_path,
        sources=[{"id": "pdf_1", "resource": "x.pdf",
                  "media_type": "application/pdf"}],
        singular=digest,
    )
    rendered = candidate.render_text()
    assert rendered.startswith("---\ntype: \"Decisao\"\n")
    assert f"\"by\":\"{PROCESS_PRODUCER_ACTOR}\"" in rendered
    assert "verified" not in candidate.frontmatter
    assert "status" not in candidate.frontmatter


# 3.9 — A process run leaves a pre-existing Legal bundle byte-identical.
def test_process_publication_leaves_bundle_byte_identical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    import hashlib
    import json

    from pipeline_juridico.domain_router_cli import main

    evidence = tmp_path / "Decisão.pdf"
    evidence.write_bytes(b"pdf evidence")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    markdown = tmp_path / "phase1.md"
    markdown.write_text("[[Pág. 1]]\n<!-- método: texto_nativo -->\nLiteral\n",
                        encoding="utf-8")
    report = {
        "schema_version": "1.0", "execution_id": "bundle-immutability",
        "input": {"sha256": digest, "byte_size": evidence.stat().st_size,
                  "page_count": 1},
        "phase1": {"implementation": "shared-core",
                   "implementation_version": "1.0",
                   "logical_processing_version": "1.0",
                   "relevant_config_fingerprint": "config-a"},
        "result": {"quality_gate": "PASS", "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": hashlib.sha256(
            markdown.read_bytes()).hexdigest()},
        "pages": [{"page_number": 1, "method": "texto_nativo",
                   "char_count": 44, "warnings": [], "errors": [],
                   "truncated": False}],
        "telemetry": {},
    }
    report_path = tmp_path / "phase1.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    routing = tmp_path / "routing"
    routing.mkdir()
    (routing / "bundle-immutability.json").write_text(json.dumps({
        "schema_version": "1.0",
        "record_type": "routing",
        "provenance_sha256": digest,
        "decision": "judicial_process",
        "reason": "requested_domain_judicial_process",
    }))
    monkeypatch.setenv("ROUTING_STATE_DIR", str(routing))
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    bundle_file = bundle / "legislacao" / "existente.md"
    bundle_file.parent.mkdir(parents=True)
    bundle_file.write_text("conteúdo legal existente\n", encoding="utf-8")
    before = bundle_file.read_bytes()

    assert main(["process", "build", str(markdown), str(report_path),
                 "--type", "Decisao", "--evidence-resource", str(evidence),
                 "--process-root", str(tmp_path / "process"),
                 "--state-dir", str(tmp_path / "state"), "--json"]) == 0
    candidate_path = tmp_path / "candidate.md"
    candidate_path.write_text(json.loads(capsys.readouterr().out)["candidate"])
    assert main(["process", "publish", str(candidate_path),
                 "--process-root", str(tmp_path / "process"),
                 "--state-dir", str(tmp_path / "state")]) == 0

    assert bundle_file.read_bytes() == before
    assert not (tmp_path / "process").is_relative_to(bundle)
    assert not any(bundle.rglob("*.json"))
