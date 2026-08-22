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
    extracted: tuple[ExtractedField, ...] = (),
) -> ReviewResult:
    suggestions = (
        (ClassificationSuggestion(suggestion, "non-authoritative", 0.5),)
        if suggestion is not None
        else ()
    )
    return ReviewResult(state, (), extracted, suggestions, ())


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


# 3.1 / 3.2 — fixed boundary and validated context.
def test_input_contract_gate_route_and_context(evidence: Path, tmp_path: Path) -> None:
    from pipeline_juridico.legal_producer import (
        LegalProducerBlockedError,
        LegalProducerConfigurationError,
        produce,
    )

    context = _context(evidence)
    with pytest.raises(LegalProducerBlockedError):
        produce(
            _artifacts(evidence, gate="FAIL"), _decision(), _review(), context,
            bundle_root=tmp_path / "bundle",
        )
    missing_gate = _artifacts(evidence)
    missing_gate = replace(missing_gate, report_json='{"result": {}}')
    with pytest.raises(LegalProducerBlockedError):
        produce(missing_gate, _decision(), _review(), context,
                bundle_root=tmp_path / "bundle")
    for target in (RouteTarget.JUDICIAL_PROCESS, RouteTarget.REVIEW_REQUIRED):
        with pytest.raises(LegalProducerConfigurationError):
            produce(_artifacts(evidence), _decision(target), _review(), context,
                    bundle_root=tmp_path / "bundle")
    with pytest.raises(LegalProducerConfigurationError):
        produce(_artifacts(evidence), None, _review(), context,
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
    with pytest.raises(LegalProducerBlockedError, match="review_required"):
        produce(
            _artifacts(evidence), _decision(),
            _review(suggestion="Jurisprudencia"), _context(evidence),
            bundle_root=root,
        )
    assert not root.exists()


@pytest.mark.parametrize(
    ("concept_type", "expected_dir", "field_name"),
    [
        ("Legislacao", "legislacao", "jurisdicao"),
        ("Jurisprudencia", "jurisprudencia", "tribunal"),
        ("TemaJuridico", "temas", "ementa"),
        ("PrecedenteVinculante", "precedentes", "tese_fixada"),
    ],
)
def test_render_is_valid_deterministic_and_profile_scoped(
    evidence: Path,
    tmp_path: Path,
    concept_type: str,
    expected_dir: str,
    field_name: str,
) -> None:
    from pipeline_juridico.legal_producer import PRODUCER_VERSION, produce

    artifacts = _artifacts(evidence)
    before_markdown = _hash(artifacts.markdown.encode())
    before_report = artifacts.report_json
    result = produce(
        artifacts, _decision(),
        _review(extracted=(ExtractedField(field_name, "valor", ("1",)),)),
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
    other_fields = {"jurisdicao", "tribunal", "ementa", "tese_fixada"} - {field_name}
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

    result = produce(_artifacts(evidence), _decision(), _review(), _context(evidence),
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
            _artifacts(evidence, input_hash="0" * 64), _decision(), _review(),
            _context(evidence), bundle_root=tmp_path / "other",
        )
    missing = validate_producer_context({"type": "Legislacao"})
    with pytest.raises(LegalProducerConfigurationError):
        produce(_artifacts(evidence), _decision(), _review(), missing,
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
    first = produce(_artifacts(evidence), _decision(), _review(), _context(evidence),
                    bundle_root=root)
    before = first.concept_path.read_bytes()  # type: ignore[union-attr]
    second = produce(_artifacts(evidence), _decision(), _review(), _context(evidence),
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
    first = produce(_artifacts(evidence), _decision(), _review(), _context(evidence),
                    bundle_root=root)
    path = first.concept_path
    existing = parse_candidate_text(path.read_text(), path)  # type: ignore[union-attr]
    existing.frontmatter.update({
        "status": "draft",
        "title": "Curadoria humana",
        "x_extension": {"keep": True},
        "verified": {"by": "human:ana", "at": "2026-01-01"},
        "generated": {"by": "repo_jur_producer/old", "at": "prior-event"},
    })
    path.write_text(existing.render_text())  # type: ignore[union-attr]
    changed = _artifacts(
        evidence,
        phase1_overrides={"implementation_version": "1.1"},
    )
    result = produce(changed, _decision(), _review(), _context(evidence),
                     bundle_root=root, overwrite=True)
    assert result.resolution is DuplicateResolution.REGENERATE
    assert result.materiality is MaterialityCategory.TECHNICAL
    frontmatter = result.candidate.frontmatter  # type: ignore[union-attr]
    assert frontmatter["status"] == "draft"
    assert frontmatter["title"] == "Curadoria humana"
    assert frontmatter["x_extension"] == {"keep": True}
    assert frontmatter["verified"] == {"by": "human:ana", "at": "2026-01-01"}
    assert frontmatter["generated"]["at"] == "prior-event"  # type: ignore[index]
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
    first = produce(_artifacts(evidence), _decision(), _review(), _context(evidence),
                    bundle_root=root)
    before = first.concept_path.read_bytes()  # type: ignore[union-attr]
    result = produce(
        _artifacts(evidence, markdown=MARKDOWN.replace("literal", "alterado")),
        _decision(), _review(), _context(evidence), bundle_root=root,
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
         "verified": {"by": "human:ana", "at": "2026-01-01"},
         "repo_jur_verification_history": [
             {"by": "human:beto", "at": "2025-01-01", "reason": "prior"}
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
    assert history[0] == {"by": "human:beto", "at": "2025-01-01", "reason": "prior"}
    assert history[1] == {
        "by": "human:ana", "at": "2026-01-01",
        "invalidated_by": "repo_jur_producer/1.0", "reason": "body changed",
    }


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
    result = module.produce(
        _artifacts(evidence), _decision(), _review(), _context(evidence),
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
    first = produce(first_artifacts, _decision(), _review(), _context(evidence),
                    bundle_root=tmp_path / "one")
    second = produce(second_artifacts, _decision(), _review(), _context(evidence),
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
