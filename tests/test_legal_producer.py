from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path

import pytest

from pipeline_juridico.contracts import (
    Phase1Artifacts,
    RouteTarget,
    guard_legal_bundle_write,
)
from pipeline_juridico.domain_router import (
    RoutingDecision,
    RoutingReasonCode,
)
from pipeline_juridico.legal_semantic_review import (
    ClassificationSuggestion,
    ExtractedField,
    ReviewResult,
    ReviewState,
)

MODULE_PATH = Path("src/pipeline_juridico/legal_producer.py")
MARKDOWN = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nConteúdo literal\n"


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _artifacts(
    evidence: Path,
    *,
    markdown: str = MARKDOWN,
    gate: str = "PASS",
    input_hash: str | None = None,
    phase1_overrides: dict[str, str] | None = None,
) -> Phase1Artifacts:
    phase1 = {
        "implementation": "shared-core",
        "implementation_version": "1.0",
        "logical_processing_version": "1.0",
        "relevant_config_fingerprint": "config-a",
    }
    phase1.update(phase1_overrides or {})
    report = {
        "schema_version": "1.0",
        "execution_id": "execution-must-not-affect-render",
        "input": {
            "sha256": input_hash or _hash(evidence.read_bytes()),
            "byte_size": evidence.stat().st_size,
            "page_count": 1,
        },
        "phase1": phase1,
        "result": {"quality_gate": gate, "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": _hash(markdown.encode())},
        "pages": [
            {
                "page_number": 1,
                "method": "texto_nativo",
                "char_count": len(markdown),
                "warnings": [],
                "errors": [],
                "truncated": False,
            }
        ],
        "telemetry": {},
    }
    return Phase1Artifacts(markdown, json.dumps(report, ensure_ascii=False))


def _decision(target: RouteTarget = RouteTarget.LEGAL_KNOWLEDGE) -> RoutingDecision:
    reason = {
        RouteTarget.LEGAL_KNOWLEDGE:
            RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE,
        RouteTarget.JUDICIAL_PROCESS:
            RoutingReasonCode.REQUESTED_DOMAIN_JUDICIAL_PROCESS,
        RouteTarget.REVIEW_REQUIRED:
            RoutingReasonCode.MISSING_ROUTING_SIGNAL,
    }[target]
    return RoutingDecision(target, reason)


def _review(
    *,
    state: ReviewState = ReviewState.OK,
    suggestion: str | None = None,
    extracted: tuple[ExtractedField, ...] | None = None,
    concept_type: str = "Legislacao",
) -> ReviewResult:
    suggestions = (
        (ClassificationSuggestion(suggestion, "non-authoritative", 0.5),)
        if suggestion is not None
        else ()
    )
    # Explicit design: no silent defaults desu!
    fields = extracted if extracted is not None else ()
    return ReviewResult(state, (), tuple(fields), suggestions, ())


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    path = tmp_path / "Ação Nº 10.PDF"
    path.write_bytes(b"pdf evidence")
    return path


def _api():
    from pipeline_juridico.legal_producer import (
        LegalConceptType,
        validate_producer_context,
    )

    return LegalConceptType, validate_producer_context


def _context(evidence: Path, concept_type: str = "Legislacao"):
    _, validate = _api()
    return validate({"type": concept_type, "evidence_resource": str(evidence)})


# Helper to get valid legislative fields desu~!
def _valid_legislacao_fields() -> tuple[ExtractedField, ...]:
    return (
        ExtractedField("repo_jur_lei_esfera", "federal", ("1",)),
        ExtractedField("repo_jur_lei_numero", "10406", ("1",)),
        ExtractedField("repo_jur_lei_ano", "2002", ("1",)),
        ExtractedField("repo_jur_lei_tipo", "ordinaria", ("1",)),
    )


# 3.1 / 3.2 — fixed boundary and validated context.
def test_input_contract_gate_route_and_context(evidence: Path, tmp_path: Path) -> None:
    from pipeline_juridico.legal_producer import (
        LegalProducerBlockedError,
        LegalProducerConfigurationError,
        produce,
    )

    context = _context(evidence)
    valid_review = _review(extracted=_valid_legislacao_fields())

    with pytest.raises(LegalProducerBlockedError):
        produce(
            _artifacts(evidence, gate="FAIL"), _decision(), valid_review, context,
            bundle_root=tmp_path / "bundle",
        )
    missing_gate = _artifacts(evidence)
    missing_gate = replace(missing_gate, report_json='{"result": {}}')
    with pytest.raises(LegalProducerBlockedError):
        produce(missing_gate, _decision(), valid_review, context,
                bundle_root=tmp_path / "bundle")
    for target in (RouteTarget.JUDICIAL_PROCESS, RouteTarget.REVIEW_REQUIRED):
        with pytest.raises(LegalProducerConfigurationError):
            produce(_artifacts(evidence), _decision(target), valid_review, context,
                    bundle_root=tmp_path / "bundle")
    with pytest.raises(LegalProducerConfigurationError):
        produce(_artifacts(evidence), None, valid_review, context,
                bundle_root=tmp_path / "bundle")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"type": "Other"}, {"type": 3}, [],
     {"type": "Legislacao", "unknown": "x"},
     {"type": "Legislacao", "evidence_resource": 3},
     {"type": "Legislacao", "evidence_resource": ""},
     {"type": "Legislacao", "evidence_resource": "not a path?"}],
)
def test_context_rejects_absent_unknown_or_structurally_invalid(payload: object) -> None:
    from pipeline_juridico.legal_producer import (
        LegalProducerConfigurationError,
        validate_producer_context,
    )

    with pytest.raises(LegalProducerConfigurationError):
        validate_producer_context(payload)  # type: ignore[arg-type]


def test_public_contracts_are_exact_and_frozen(evidence: Path) -> None:
    from pipeline_juridico.legal_producer import (
        ConceptCandidate,
        DuplicateResolution,
        LegalConceptType,
        MaterialityCategory,
        ProducerContext,
        ProducerRunResult,
    )

    assert [item.value for item in LegalConceptType] == [
        "Legislacao", "Jurisprudencia", "TemaJuridico", "PrecedenteVinculante"
    ]
    assert {item.value for item in DuplicateResolution} == {
        "new_concept", "noop", "regenerate", "add_source",
        "human_review_required",
    }
    assert {item.value for item in MaterialityCategory} == {"technical", "material"}
    assert tuple(field.name for field in fields(ProducerContext)) == (
        "type", "evidence_resource"
    )
    assert tuple(field.name for field in fields(ConceptCandidate)) == (
        "type", "frontmatter", "body", "path"
    )
    assert tuple(field.name for field in fields(ProducerRunResult)) == (
        "candidate", "resolution", "materiality", "written", "concept_path"
    )
    context = _context(evidence)
    with pytest.raises(FrozenInstanceError):
        context.evidence_resource = "changed"  # type: ignore[misc]


# 3.3 / 3.4 / 3.5 — authority, immutability, render, and profile isolation.
def test_type_authority_conflict_blocks_without_writing(
    evidence: Path, tmp_path: Path
) -> None:
    from pipeline_juridico.legal_producer import (
        LegalProducerBlockedError,
        produce,
    )

    root = tmp_path / "bundle"
    valid_review_with_conflict = _review(suggestion="Jurisprudencia", extracted=_valid_legislacao_fields())
    with pytest.raises(LegalProducerBlockedError, match="review_required"):
        produce(
            _artifacts(evidence), _decision(),
            valid_review_with_conflict, _context(evidence),
            bundle_root=root,
        )
    assert not root.exists()


@pytest.mark.parametrize(
    ("concept_type", "expected_dir", "field_name", "type_fields"),
    [
        ("Legislacao", "legislacao", "repo_jur_lei_tipo", (
            ExtractedField("repo_jur_lei_esfera", "federal", ("1",)),
            ExtractedField("repo_jur_lei_numero", "10406", ("1",)),
            ExtractedField("repo_jur_lei_ano", "2002", ("1",)),
        )),
        ("Jurisprudencia", "jurisprudencia", "repo_jur_ramo_direito", (
            ExtractedField("repo_jur_processo_numero", "REsp 1.704.551 - SP", ("1",)),
            ExtractedField("repo_jur_tribunal", "STJ", ("1",)),
            ExtractedField("repo_jur_relator", "NANCY ANDRIGHI", ("1",)),
            ExtractedField("repo_jur_data_julgamento", "2019-04-02", ("1",)),
        )),
        ("TemaJuridico", "temas", "repo_jur_tema_numero", (
            ExtractedField("repo_jur_tribunal", "STJ", ("1",)),
        )),
        ("PrecedenteVinculante", "precedentes", "repo_jur_precedente_numero", (
            ExtractedField("repo_jur_precedente_status", "ativo", ("1",)),
            ExtractedField("repo_jur_tribunal", "STF", ("1",)),
        )),
    ],
)
def test_render_is_valid_deterministic_and_profile_scoped(
    evidence: Path,
    tmp_path: Path,
    concept_type: str,
    expected_dir: str,
    field_name: str,
    type_fields: tuple[ExtractedField, ...],
) -> None:
    from pipeline_juridico.legal_producer import PRODUCER_VERSION, produce

    artifacts = _artifacts(evidence)
    before_markdown = _hash(artifacts.markdown.encode())
    before_report = artifacts.report_json
    extracted_fields = type_fields + (ExtractedField(field_name, "valor", ("1",)),)
    result = produce(
        artifacts, _decision(),
        _review(extracted=extracted_fields, concept_type=concept_type),
        _context(evidence, concept_type), bundle_root=tmp_path / "bundle",
    )
    candidate = result.candidate
    assert candidate is not None
    text = candidate.render_text()
    assert text.startswith(f'---\ntype: "{concept_type}"\n')
    assert f'generated: {{"by":"repo_jur_producer/{PRODUCER_VERSION}"' in text
    assert "\n---\n" + MARKDOWN == text[text.index("\n---\n"):]
    assert candidate.body == MARKDOWN
    assert candidate.path.parent.name == expected_dir
    assert candidate.frontmatter[field_name] == "valor"
    other_fields = {"repo_jur_lei_tipo", "repo_jur_ramo_direito", "repo_jur_tema_numero", "repo_jur_precedente_numero"} - {field_name}
    assert not other_fields & candidate.frontmatter.keys()
    assert "verified" not in candidate.frontmatter
    assert "status" not in candidate.frontmatter
    assert _hash(artifacts.markdown.encode()) == before_markdown
    assert artifacts.report_json == before_report


# 3.6 / 3.7 — evidence and PDF-cardinality provenance.
def test_single_pdf_provenance_and_hash_cross_check(evidence: Path, tmp_path: Path) -> None:
    from pipeline_juridico.legal_producer import (
        LegalProducerConfigurationError,
        produce,
        validate_producer_context,
    )

    valid_review = _review(extracted=_valid_legislacao_fields())
    result = produce(_artifacts(evidence), _decision(), valid_review, _context(evidence),
                     bundle_root=tmp_path / "bundle")
    frontmatter = result.candidate.frontmatter  # type: ignore[union-attr]
    assert frontmatter["repo_jur_pdf_hash"] == _hash(evidence.read_bytes())
    assert "repo_jur_pdf_hashes" not in frontmatter
    assert frontmatter["repo_jur_evidence_sha256"] == _hash(evidence.read_bytes())
    assert frontmatter["sources"] == [
        {"id": "pdf_1", "resource": str(evidence), "media_type": "application/pdf"}
    ]
    with pytest.raises(LegalProducerConfigurationError):
        produce(
            _artifacts(evidence, input_hash="0" * 64), _decision(), valid_review,
            _context(evidence), bundle_root=tmp_path / "other",
        )
    missing = validate_producer_context({"type": "Legislacao"})
    with pytest.raises(LegalProducerConfigurationError):
        produce(_artifacts(evidence), _decision(), valid_review, missing,
                bundle_root=tmp_path / "missing")


def test_candidate_validation_rejects_cardinality_and_mapping(evidence: Path) -> None:
    from pipeline_juridico.legal_producer import (
        ConceptCandidate,
        LegalProducerConfigurationError,
        validate_candidate,
    )

    base = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0"},
        "sources": [
            {"id": "pdf_1", "resource": str(evidence),
             "media_type": "application/pdf"},
            {"id": "web_1", "resource": "https://example.test/source",
             "media_type": "text/html"},
        ],
    }
    bad_both = dict(base, repo_jur_pdf_hash="a" * 64,
                    repo_jur_pdf_hashes={"pdf_1": "a" * 64})
    bad_mapping = dict(base, repo_jur_pdf_hashes={"web_1": "a" * 64})
    for frontmatter in (bad_both, bad_mapping):
        candidate = ConceptCandidate(_api()[0].Legislacao, frontmatter, MARKDOWN,
                                     Path("bundle/legislacao/test.md"))
        with pytest.raises(LegalProducerConfigurationError):
            validate_candidate(candidate)


# 3.8–3.11 — lifecycle merge, verification, timestamps, duplicate state machine.
def test_equivalent_rerun_is_noop_and_preserves_generated_at(
    evidence: Path, tmp_path: Path
) -> None:
    from pipeline_juridico.legal_producer import DuplicateResolution, produce

    root = tmp_path / "bundle"
    valid_review = _review(extracted=_valid_legislacao_fields())
    first = produce(_artifacts(evidence), _decision(), valid_review, _context(evidence),
                    bundle_root=root)
    before = first.concept_path.read_bytes()  # type: ignore[union-attr]
    second = produce(_artifacts(evidence), _decision(), valid_review, _context(evidence),
                     bundle_root=root)
    assert second.resolution is DuplicateResolution.NOOP
    assert second.written is False
    assert second.concept_path.read_bytes() == before  # type: ignore[union-attr]
    assert second.candidate.render_text().encode() == before  # type: ignore[union-attr]


def test_technical_regeneration_preserves_human_shared_unknown_and_verified(
    evidence: Path, tmp_path: Path
) -> None:
    from pipeline_juridico.legal_producer import (
        DuplicateResolution,
        MaterialityCategory,
        parse_candidate_text,
        produce,
    )

    root = tmp_path / "bundle"
    valid_review = _review(extracted=_valid_legislacao_fields())
    first = produce(_artifacts(evidence), _decision(), valid_review, _context(evidence),
                    bundle_root=root)
    path = first.concept_path
    existing = parse_candidate_text(path.read_text(), path)  # type: ignore[union-attr]
    existing.frontmatter.update({
        "status": "draft",
        "title": "Curadoria humana",
        "x_extension": {"keep": True},
        "verified": {"by": "human:ana", "at": "2026-01-01T12:00:00Z"},
        "generated": {"by": "repo_jur_producer/old", "at": "2026-01-01T11:00:00Z"},
    })
    path.write_text(existing.render_text())  # type: ignore[union-attr]
    changed = _artifacts(
        evidence,
        phase1_overrides={"implementation_version": "1.1"},
    )
    result = produce(changed, _decision(), valid_review, _context(evidence),
                     bundle_root=root, overwrite=True)
    assert result.resolution is DuplicateResolution.REGENERATE
    assert result.materiality is MaterialityCategory.TECHNICAL
    frontmatter = result.candidate.frontmatter  # type: ignore[union-attr]
    assert frontmatter["status"] == "draft"
    assert frontmatter["title"] == "Curadoria humana"
    assert frontmatter["x_extension"] == {"keep": True}
    assert frontmatter["verified"] == {"by": "human:ana", "at": "2026-01-01T12:00:00Z"}
    assert frontmatter["generated"]["at"] == "2026-01-01T11:00:00Z"  # type: ignore[index]
    assert "repo_jur_verification_history" not in frontmatter
    assert "_v2" not in path.name and "uuid" not in result.candidate.render_text().lower()  # type: ignore[union-attr]


def test_material_body_change_requires_human_review_and_no_write(
    evidence: Path, tmp_path: Path
) -> None:
    from pipeline_juridico.legal_producer import (
        DuplicateResolution,
        MaterialityCategory,
        produce,
    )

    root = tmp_path / "bundle"
    valid_review = _review(extracted=_valid_legislacao_fields())
    first = produce(_artifacts(evidence), _decision(), valid_review, _context(evidence),
                    bundle_root=root)
    before = first.concept_path.read_bytes()  # type: ignore[union-attr]
    result = produce(
        _artifacts(evidence, markdown=MARKDOWN.replace("literal", "alterado")),
        _decision(), valid_review, _context(evidence), bundle_root=root,
        overwrite=True,
    )
    assert result.resolution is DuplicateResolution.HUMAN_REVIEW
    assert result.materiality is MaterialityCategory.MATERIAL
    assert result.written is False
    assert result.concept_path.read_bytes() == before  # type: ignore[union-attr]


def test_material_merge_archives_only_real_verification_event(evidence: Path) -> None:
    from pipeline_juridico.legal_producer import (
        ConceptCandidate,
        MaterialityCategory,
        merge_existing_candidate,
    )

    concept_type = _api()[0].Legislacao
    old = ConceptCandidate(
        concept_type,
        {"type": "Legislacao", "generated": {"by": "old"},
         "verified": {"by": "human:ana", "at": "2026-01-01T12:00:00Z"},
         "repo_jur_verification_history": [
             {"by": "human:beto", "at": "2025-01-01T12:00:00Z", "reason": "prior"}
         ]},
        "old body\n", Path("concept.md"),
    )
    new = ConceptCandidate(
        concept_type,
        {"type": "Legislacao", "generated": {"by": "repo_jur_producer/1.0"}},
        "new body\n", Path("concept.md"),
    )
    merged = merge_existing_candidate(old, new, MaterialityCategory.MATERIAL,
                                      reason="body changed")
    assert "verified" not in merged.frontmatter
    history = merged.frontmatter["repo_jur_verification_history"]
    assert history[0] == {"by": "human:beto", "at": "2025-01-01T12:00:00Z", "reason": "prior"}
    assert history[1]["by"] == "human:ana"
    assert history[1]["at"] == "2026-01-01T12:00:00Z"
    assert history[1]["invalidated_by"] == "repo_jur_producer/1.0"
    assert history[1]["reason"] == "body changed"


# 3.12 / 3.13 — validation, guarded atomic publication, positional path.
def test_publication_uses_guard_and_creates_only_selected_tree(
    evidence: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import pipeline_juridico.legal_producer as module

    calls: list[tuple[RouteTarget, Path, Path]] = []
    original = module.guard_legal_bundle_write

    def recording_guard(*, acting_domain, target, legal_bundle_root):
        calls.append((acting_domain, Path(target), Path(legal_bundle_root)))
        return original(acting_domain=acting_domain, target=target,
                        legal_bundle_root=legal_bundle_root)

    monkeypatch.setattr(module, "guard_legal_bundle_write", recording_guard)
    root = tmp_path / "bundle"
    assert not root.exists()
    valid_review = _review(extracted=_valid_legislacao_fields())
    result = module.produce(
        _artifacts(evidence), _decision(), valid_review, _context(evidence),
        bundle_root=root,
    )
    assert result.written and result.concept_path.exists()  # type: ignore[union-attr]
    assert calls == [(RouteTarget.LEGAL_KNOWLEDGE, result.concept_path, root)]
    assert result.concept_path.name == "acao_no_10.md"  # type: ignore[union-attr]
    assert {path.name for path in root.iterdir()} == {"legislacao"}
    assert not list(root.rglob("*.tmp"))


def test_non_legal_guard_denies_bundle_target(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    target = root / "legislacao" / "x.md"
    with pytest.raises(PermissionError):
        guard_legal_bundle_write(
            acting_domain=RouteTarget.REVIEW_REQUIRED,
            target=target,
            legal_bundle_root=root,
        )
    assert not target.exists()


def test_path_cannot_escape_bundle(evidence: Path, tmp_path: Path) -> None:
    from pipeline_juridico.legal_producer import resolve_concept_path

    path = resolve_concept_path(
        _api()[0].Legislacao, "../../Fora.pdf", tmp_path / "bundle"
    )
    assert path.is_relative_to((tmp_path / "bundle").resolve())
    assert ".." not in path.parts


# 3.14 / 3.15 — pure bytes and source-level isolation.
def test_candidate_ignores_execution_metadata(evidence: Path, tmp_path: Path) -> None:
    from pipeline_juridico.legal_producer import produce

    first_artifacts = _artifacts(evidence)
    report = json.loads(first_artifacts.report_json)
    report["execution_id"] = "different-run"
    report["telemetry"] = {"duration": 999, "timestamp": "tomorrow"}
    second_artifacts = replace(first_artifacts, report_json=json.dumps(report))
    valid_review = _review(extracted=_valid_legislacao_fields())
    first = produce(first_artifacts, _decision(), valid_review, _context(evidence),
                    bundle_root=tmp_path / "one")
    second = produce(second_artifacts, _decision(), valid_review, _context(evidence),
                     bundle_root=tmp_path / "two")
    assert first.candidate.render_text() == second.candidate.render_text()  # type: ignore[union-attr]


def test_source_has_no_later_stage_or_upstream_coupling() -> None:
    source = MODULE_PATH.read_text().lower()
    for forbidden in (
        "judicial", "process_schema", "retrieval", "index", "converter",
        "engines", "inspector", "ocr", "llm", "openai", "google", "cli",
    ):
        assert forbidden not in source
    for git_operation in ("git commit", "git push", "git merge"):
        assert git_operation not in source


# 1. EXTRACTION BOUNDARY REGRESSION TEST — BLOCKER desu~!
def test_producer_validation_does_not_depend_on_body_text(evidence: Path) -> None:
    from pipeline_juridico.legal_producer import validate_candidate, ConceptCandidate, LegalConceptType

    # Valid candidate with arbitrary body text (even containing "constituição")
    # Must NOT block because validate_candidate only inspects frontmatter!
    frontmatter = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "123",
        "repo_jur_lei_ano": 2002,
        "repo_jur_lei_tipo": "ordinaria",
    }
    candidate = ConceptCandidate(
        LegalConceptType.Legislacao,
        frontmatter,
        "CONSTITUIÇÃO DA REPÚBLICA...",  # text contains "constituição"
        Path("test.md")
    )
    # This should pass without raising any exception desu~!
    validate_candidate(candidate)


# 2. LEGISLACAO CONDITIONAL MANDATORY TESTS — BLOCKER desu~!
def test_legislacao_numbered_vs_non_numbered(evidence: Path) -> None:
    from pipeline_juridico.legal_producer import validate_candidate, ConceptCandidate, LegalConceptType, LegalProducerBlockedError

    # a) Ordinary numbered law (requires numero/ano) -> passes
    frontmatter_numbered = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_ano": 2002,
        "repo_jur_lei_tipo": "ordinaria",
    }
    candidate_numbered = ConceptCandidate(LegalConceptType.Legislacao, frontmatter_numbered, "body", Path("test.md"))
    validate_candidate(candidate_numbered)

    # b) Non-numbered legislation (neither numero nor ano -> legitimate non-numbered) -> passes
    frontmatter_non_numbered = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_tipo": "constituicao",
    }
    candidate_non_numbered = ConceptCandidate(LegalConceptType.Legislacao, frontmatter_non_numbered, "body", Path("test.md"))
    validate_candidate(candidate_non_numbered)

    # c) Only number is present -> blocks desu~!
    frontmatter_only_num = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_tipo": "ordinaria",
    }
    candidate_only_num = ConceptCandidate(LegalConceptType.Legislacao, frontmatter_only_num, "body", Path("test.md"))
    with pytest.raises(LegalProducerBlockedError, match="missing conditional mandatory field"):
        validate_candidate(candidate_only_num)

    # d) Only year is present -> blocks desu~!
    frontmatter_only_ano = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_ano": 2002,
        "repo_jur_lei_tipo": "ordinaria",
    }
    candidate_only_ano = ConceptCandidate(LegalConceptType.Legislacao, frontmatter_only_ano, "body", Path("test.md"))
    with pytest.raises(LegalProducerBlockedError, match="missing conditional mandatory field"):
        validate_candidate(candidate_only_ano)


# 3. TEMAJURIDICO CONDITIONAL FIELD TESTS — BLOCKER desu~!
def test_temajuridico_conditional_mandatory() -> None:
    from pipeline_juridico.legal_producer import validate_candidate, ConceptCandidate, LegalConceptType, LegalProducerBlockedError

    # a) Official numbered court theme (both present) -> passes
    frontmatter_numbered = {
        "type": "TemaJuridico",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_tema_numero": "123",
        "repo_jur_tribunal": "STJ",
    }
    candidate_numbered = ConceptCandidate(LegalConceptType.TemaJuridico, frontmatter_numbered, "body", Path("test.md"))
    validate_candidate(candidate_numbered)

    # b) Official court theme (tribunal present, tema_numero absent) -> passes
    frontmatter_court = {
        "type": "TemaJuridico",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_tribunal": "STF",
    }
    candidate_court = ConceptCandidate(LegalConceptType.TemaJuridico, frontmatter_court, "body", Path("test.md"))
    validate_candidate(candidate_court)

    # c) Doctrinal/abstract theme with neither field -> passes desu~!
    frontmatter_doctrinal = {
        "type": "TemaJuridico",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
    }
    candidate_doctrinal = ConceptCandidate(LegalConceptType.TemaJuridico, frontmatter_doctrinal, "body", Path("test.md"))
    validate_candidate(candidate_doctrinal)

    # d) Condition applies but required field absent (repo_jur_tema_numero present but repo_jur_tribunal missing) -> blocked
    frontmatter_bad = {
        "type": "TemaJuridico",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_tema_numero": "123",
    }
    candidate_bad = ConceptCandidate(LegalConceptType.TemaJuridico, frontmatter_bad, "body", Path("test.md"))
    with pytest.raises(LegalProducerBlockedError, match="missing conditional mandatory field repo_jur_tribunal"):
        validate_candidate(candidate_bad)


# 5. GENERATED.AT VALIDATION TESTS — BLOCKER desu~!
def test_generated_at_timestamp_validation() -> None:
    from pipeline_juridico.legal_producer import validate_candidate, ConceptCandidate, LegalConceptType, LegalProducerConfigurationError

    # Positive test: valid ISO 8601 datetime String
    frontmatter_ok = {
        "type": "TemaJuridico",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
    }
    candidate_ok = ConceptCandidate(LegalConceptType.TemaJuridico, frontmatter_ok, "body", Path("test.md"))
    validate_candidate(candidate_ok)

    # Negative test: "evidence:..." is invalid
    frontmatter_evidence = {
        "type": "TemaJuridico",
        "generated": {"by": "repo_jur_producer/1.0", "at": "evidence:some_uri"},
    }
    candidate_evidence = ConceptCandidate(LegalConceptType.TemaJuridico, frontmatter_evidence, "body", Path("test.md"))
    with pytest.raises(LegalProducerConfigurationError, match="candidate generated at timestamp is invalid"):
        validate_candidate(candidate_evidence)

    # Negative test: arbitrary text is invalid
    frontmatter_arbitrary = {
        "type": "TemaJuridico",
        "generated": {"by": "repo_jur_producer/1.0", "at": "not-a-date"},
    }
    candidate_arbitrary = ConceptCandidate(LegalConceptType.TemaJuridico, frontmatter_arbitrary, "body", Path("test.md"))
    with pytest.raises(LegalProducerConfigurationError, match="candidate generated at timestamp is invalid"):
        validate_candidate(candidate_arbitrary)


# 6. LEGISLACAO ESFERA EXTRACTION TESTS — MAJOR desu~!
def test_esfera_false_positive_prevention() -> None:
    from pipeline_juridico.legal_semantic_review import _deterministic_extract

    # Case containing "união estável" but NO other federal structural headers
    # MUST NOT yield federal!
    markdown = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nNós celebramos uma união estável sob as regras do Código Civil."
    extracted = _deterministic_extract(markdown)
    assert not any(f.name == "repo_jur_lei_esfera" for f in extracted)


# 7. PRECEDENTE STATUS TESTS — MAJOR desu~!
def test_precedente_status_deterministic_extraction() -> None:
    from pipeline_juridico.legal_semantic_review import _deterministic_extract

    # a) Explicit cancelado -> cancelado
    md_cancelado = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nSúmula n. 714 foi cancelada pelo STF."
    ext_cancelado = _deterministic_extract(md_cancelado)
    status_field = next(f for f in ext_cancelado if f.name == "repo_jur_precedente_status")
    assert status_field.value == "cancelado"

    # b) Explicit revisado -> revisado
    md_revisado = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nSúmula n. 714 foi revisada pelo tribunal."
    ext_revisado = _deterministic_extract(md_revisado)
    status_field = next(f for f in ext_revisado if f.name == "repo_jur_precedente_status")
    assert status_field.value == "revisado"

    # c) Explicit ativo -> ativo
    md_ativo = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nSúmula n. 714 permanece ativa/vigente."
    ext_ativo = _deterministic_extract(md_ativo)
    status_field = next(f for f in ext_ativo if f.name == "repo_jur_precedente_status")
    assert status_field.value == "ativo"

    # d) No status evidence -> status field is NOT extracted
    md_no_status = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nSúmula n. 714 do STF"
    ext_no_status = _deterministic_extract(md_no_status)
    assert not any(f.name == "repo_jur_precedente_status" for f in ext_no_status)


# 8. LEGISLACAO TYPE EXTRACTION TESTS — MAJOR desu~!
def test_legislacao_type_extraction_matrix() -> None:
    from pipeline_juridico.legal_semantic_review import _deterministic_extract

    # a) LEI Nº ... -> ordinaria
    ext = _deterministic_extract("[[Pág. 1]]\n<!-- método: texto_nativo -->\nLEI Nº 10.406, DE 10 DE JANEIRO DE 2002")
    tipo = next(f for f in ext if f.name == "repo_jur_lei_tipo")
    assert tipo.value == "ordinaria"

    # b) LEI COMPLEMENTAR Nº ... -> complementar
    ext = _deterministic_extract("[[Pág. 1]]\n<!-- método: texto_nativo -->\nLEI COMPLEMENTAR Nº 123, DE 14 DE DEZEMBRO DE 2006")
    tipo = next(f for f in ext if f.name == "repo_jur_lei_tipo")
    assert tipo.value == "complementar"

    # c) DECRETO Nº ... -> decreto
    ext = _deterministic_extract("[[Pág. 1]]\n<!-- método: texto_nativo -->\nDECRETO Nº 3.048, DE 6 DE MAIO DE 1999")
    tipo = next(f for f in ext if f.name == "repo_jur_lei_tipo")
    assert tipo.value == "decreto"

    # d) MEDIDA PROVISÓRIA Nº ... -> medida_provisoria
    ext = _deterministic_extract("[[Pág. 1]]\n<!-- método: texto_nativo -->\nMEDIDA PROVISÓRIA Nº 1.234, DE 2026")
    tipo = next(f for f in ext if f.name == "repo_jur_lei_tipo")
    assert tipo.value == "medida_provisoria"

    # e) CONSTITUIÇÃO -> constituicao
    ext = _deterministic_extract("[[Pág. 1]]\n<!-- método: texto_nativo -->\nCONSTITUIÇÃO DA REPÚBLICA FEDERATIVA DO BRASIL DE 1988")
    tipo = next(f for f in ext if f.name == "repo_jur_lei_tipo")
    assert tipo.value == "constituicao"


# 13. OMIT RESOURCE IF ABSENT desu~!
def test_omit_resource_when_absent() -> None:
    from pipeline_juridico.legal_producer import ConceptCandidate, LegalConceptType
    # Create candidate with NO resource key
    frontmatter = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_ano": 2002,
        "repo_jur_lei_tipo": "ordinaria",
    }
    candidate = ConceptCandidate(LegalConceptType.Legislacao, frontmatter, "body", Path("test.md"))
    text = candidate.render_text()
    assert "resource:" not in text


# --- AUDIT COMPLIANCE TESTS desu~! (◕‿◕)✿ ---

def test_audit_shared_field_preserved() -> None:
    from pipeline_juridico.legal_producer import (
        ConceptCandidate, LegalConceptType, MaterialityCategory, merge_existing_candidate
    )
    existing_fm = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_ano": 2002,
        "repo_jur_lei_tipo": "human_curated_shared",  # Human-curated shared field!
        "repo_jur_ramo_direito": "human_curated_ramo",
        "repo_jur_precedente_status": "human_curated_status",
    }
    existing = ConceptCandidate(LegalConceptType.Legislacao, existing_fm, "body", Path("test.md"))

    new_fm = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_ano": 2002,
        "repo_jur_lei_tipo": "ordinaria",  # Automatically proposed
        "repo_jur_ramo_direito": "DIREITO CIVIL",
        "repo_jur_precedente_status": "ativo",
    }
    new = ConceptCandidate(LegalConceptType.Legislacao, new_fm, "body", Path("test.md"))

    merged = merge_existing_candidate(existing, new, MaterialityCategory.TECHNICAL, reason="test")
    # Must preserve the human curated shared field value desu~!
    assert merged.frontmatter["repo_jur_lei_tipo"] == "human_curated_shared"
    assert merged.frontmatter["repo_jur_ramo_direito"] == "human_curated_ramo"
    assert merged.frontmatter["repo_jur_precedente_status"] == "human_curated_status"


def test_audit_metadata_after_page_3() -> None:
    from pipeline_juridico.legal_semantic_review import _deterministic_extract
    # Legislative and Jurisprudência elements on page 4 desu~!
    markdown = "[[Pág. 1]]\nEmpty...\n[[Pág. 2]]\nEmpty...\n[[Pág. 3]]\nEmpty...\n[[Pág. 4]]\nLEI COMPLEMENTAR Nº 123, DE 14 DE DEZEMBRO DE 2006\nRELATOR: MINISTRO KIKO"
    ext = _deterministic_extract(markdown)

    extracted_names = {f.name for f in ext}
    assert "repo_jur_lei_numero" in extracted_names
    assert "repo_jur_lei_ano" in extracted_names
    assert "repo_jur_relator" in extracted_names

    num_field = next(f for f in ext if f.name == "repo_jur_lei_numero")
    assert num_field.value == "123"
    assert num_field.page_refs == ("4",)


def test_audit_non_numbered_not_rejected() -> None:
    from pipeline_juridico.legal_producer import validate_candidate, ConceptCandidate, LegalConceptType
    # Legitimate non-numbered acts (neither number nor year) must not be rejected desu~!
    frontmatter = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_tipo": "constituicao",
    }
    candidate = ConceptCandidate(LegalConceptType.Legislacao, frontmatter, "body", Path("test.md"))
    validate_candidate(candidate)  # Passes!


def test_audit_incomplete_numbered_act_blocks() -> None:
    from pipeline_juridico.legal_semantic_review import LegalSemanticReviewEngine, LegalReviewProfile, ReviewState
    from pipeline_juridico.contracts import Phase1Artifacts
    import json

    # Act recognized as numbered ("LEI COMPLEMENTAR Nº ...") but missing year desu~!
    markdown = "[[Pág. 1]]\nLEI COMPLEMENTAR Nº 123"
    artifacts = Phase1Artifacts(markdown, json.dumps({"result": {"quality_gate": "PASS"}}))
    profile = LegalReviewProfile("default", "1.0", ())

    result = LegalSemanticReviewEngine().review(artifacts, profile)
    # Must set REVIEW_REQUIRED state desu~!
    assert result.state == ReviewState.REVIEW_REQUIRED


def test_audit_extension_unknown_keys_preserved() -> None:
    from pipeline_juridico.legal_producer import (
        ConceptCandidate, LegalConceptType, MaterialityCategory, merge_existing_candidate
    )
    existing_fm = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_ano": 2002,
        "aliases": ["CC", "Código Civil"],  # Unknown extension keys!
        "related": ["lei-13105"],
        "my_custom_key": "special_value",
    }
    existing = ConceptCandidate(LegalConceptType.Legislacao, existing_fm, "body", Path("test.md"))

    new_fm = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/1.0"},
        "repo_jur_lei_esfera": "federal",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_ano": 2002,
    }
    new = ConceptCandidate(LegalConceptType.Legislacao, new_fm, "body", Path("test.md"))

    merged = merge_existing_candidate(existing, new, MaterialityCategory.TECHNICAL, reason="test")
    # Must preserve the extension/unknown keys desu~!
    assert merged.frontmatter["aliases"] == ["CC", "Código Civil"]
    assert merged.frontmatter["related"] == ["lei-13105"]
    assert merged.frontmatter["my_custom_key"] == "special_value"


def test_audit_legacy_keys_rejected() -> None:
    from pipeline_juridico.legal_producer import validate_candidate, ConceptCandidate, LegalConceptType, LegalProducerConfigurationError
    for legacy_key in ("jurisdicao", "ambito", "tipo_norma", "ementa", "tema", "subtema", "tese_fixada", "tribunal", "relator"):
        frontmatter = {
            "type": "Legislacao",
            "generated": {"by": "repo_jur_producer/1.0", "at": "2026-08-26T12:00:00Z"},
            "repo_jur_lei_esfera": "federal",
            "repo_jur_lei_numero": "10406",
            "repo_jur_lei_ano": 2002,
            legacy_key: "some legacy value",
        }
        candidate = ConceptCandidate(LegalConceptType.Legislacao, frontmatter, "body", Path("test.md"))
        with pytest.raises(LegalProducerConfigurationError, match="legacy or unauthorized key"):
            validate_candidate(candidate)
