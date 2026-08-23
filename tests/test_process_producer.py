from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pipeline_juridico.contracts import Phase1Artifacts, RouteTarget
from pipeline_juridico.domain_router import RoutingDecision, RoutingReasonCode
from pipeline_juridico.process_producer import (
    PROCESS_PRODUCER_ACTOR, ProcessConceptCandidate,
    ProcessDuplicateResolution, ProcessMaterialityCategory,
    classify_process_materiality, merge_existing_process_candidate,
    parse_process_candidate_text, produce_process, validate_process_candidate,
)
from pipeline_juridico.process_semantic_review import (
    ProcessClassificationSuggestion, ProcessReviewResult, ReviewState,
)
from pipeline_juridico.process_storage import (
    ProcessConceptType, ProcessProducerBlockedError,
    ProcessProducerConfigurationError, validate_process_producer_context,
)


MARKDOWN = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nLiteral\n"


def _artifacts(evidence: Path, *, markdown: str = MARKDOWN,
               gate: str = "PASS") -> Phase1Artifacts:
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    report = {
        "schema_version": "1.0", "execution_id": "process-test",
        "input": {"sha256": digest, "byte_size": evidence.stat().st_size,
                  "page_count": 1},
        "phase1": {"implementation": "shared-core",
                   "implementation_version": "1.0",
                   "logical_processing_version": "1.0",
                   "relevant_config_fingerprint": "config-a"},
        "result": {"quality_gate": gate, "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": hashlib.sha256(markdown.encode()).hexdigest()},
        "pages": [{"page_number": 1, "method": "texto_nativo",
                   "char_count": len(markdown), "warnings": [], "errors": [],
                   "truncated": False}], "telemetry": {},
    }
    return Phase1Artifacts(markdown, json.dumps(report))


def _decision(target: RouteTarget = RouteTarget.JUDICIAL_PROCESS) -> RoutingDecision:
    reason = (RoutingReasonCode.REQUESTED_DOMAIN_JUDICIAL_PROCESS
              if target is RouteTarget.JUDICIAL_PROCESS
              else RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE)
    return RoutingDecision(target, reason)


def _review(*, state: ReviewState = ReviewState.OK,
            suggestion: str | None = None) -> ProcessReviewResult:
    suggestions = (() if suggestion is None else
        (ProcessClassificationSuggestion(suggestion, "hint", .5),))
    return ProcessReviewResult(state, (), (), suggestions, ())


def _context(evidence: Path):
    return validate_process_producer_context(
        {"type": "Decisao", "evidence_resource": str(evidence)}
    )


@pytest.fixture
def evidence(tmp_path: Path) -> Path:
    path = tmp_path / "Decisão 10.pdf"
    path.write_bytes(b"pdf evidence")
    return path


def test_new_concept_is_guarded_atomic_and_body_is_literal(
    evidence: Path, tmp_path: Path
) -> None:
    artifacts = _artifacts(evidence)
    before = (artifacts.markdown, artifacts.report_json)
    result = produce_process(
        artifacts, _decision(), _review(), _context(evidence),
        process_root=tmp_path / "process", bundle_root=tmp_path / "bundle",
    )
    assert result.resolution is ProcessDuplicateResolution.NEW_CONCEPT
    assert result.written and result.concept_path.is_file()
    assert result.candidate.body == MARKDOWN
    assert result.candidate.frontmatter["generated"] == {"by": PROCESS_PRODUCER_ACTOR}
    assert "status" not in result.candidate.frontmatter
    assert "verified" not in result.candidate.frontmatter
    assert before == (artifacts.markdown, artifacts.report_json)
    assert not (tmp_path / "bundle").exists()


def test_equivalent_rerun_is_noop(evidence: Path, tmp_path: Path) -> None:
    kwargs = {"process_root": tmp_path / "process", "bundle_root": tmp_path / "bundle"}
    first = produce_process(_artifacts(evidence), _decision(), _review(),
                            _context(evidence), **kwargs)
    before = first.concept_path.read_bytes()
    second = produce_process(_artifacts(evidence), _decision(), _review(),
                             _context(evidence), **kwargs)
    assert second.resolution is ProcessDuplicateResolution.NOOP
    assert not second.written and before == first.concept_path.read_bytes()


def test_material_change_requires_human_review_without_write(
    evidence: Path, tmp_path: Path
) -> None:
    kwargs = {"process_root": tmp_path / "process", "bundle_root": tmp_path / "bundle"}
    first = produce_process(_artifacts(evidence), _decision(), _review(),
                            _context(evidence), **kwargs)
    before = first.concept_path.read_bytes()
    result = produce_process(_artifacts(evidence, markdown=MARKDOWN + "novo\n"),
                             _decision(), _review(), _context(evidence), **kwargs)
    assert result.resolution is ProcessDuplicateResolution.HUMAN_REVIEW
    assert result.materiality is ProcessMaterialityCategory.MATERIAL
    assert not result.written and first.concept_path.read_bytes() == before


@pytest.mark.parametrize("decision", [_decision(RouteTarget.LEGAL_KNOWLEDGE), None])
def test_non_process_decision_is_configuration_error(evidence: Path, tmp_path: Path,
                                                     decision) -> None:
    with pytest.raises(ProcessProducerConfigurationError):
        produce_process(_artifacts(evidence), decision, _review(), _context(evidence),
                        process_root=tmp_path / "p", bundle_root=tmp_path / "b")


def test_review_required_and_conflicting_suggestion_block(
    evidence: Path, tmp_path: Path
) -> None:
    for review in (_review(state=ReviewState.REVIEW_REQUIRED), _review(suggestion="Peticao")):
        with pytest.raises(ProcessProducerBlockedError) as caught:
            produce_process(_artifacts(evidence), _decision(), review, _context(evidence),
                            process_root=tmp_path / "p", bundle_root=tmp_path / "b")
        assert caught.value.reason == "review_required"


def test_candidate_round_trip_and_cardinality_validation(tmp_path: Path) -> None:
    digest = "a" * 64
    candidate = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [{"id": "pdf_1", "resource": "x.pdf",
                     "media_type": "application/pdf"}],
        "repo_jur_pdf_hash": digest,
    }, MARKDOWN, tmp_path / "x.md")
    validate_process_candidate(candidate)
    parsed = parse_process_candidate_text(candidate.render_text(), candidate.path)
    assert parsed.frontmatter == candidate.frontmatter and parsed.body == candidate.body
    candidate.frontmatter["repo_jur_pdf_hashes"] = {"pdf_1": digest}
    with pytest.raises(ProcessProducerConfigurationError, match="exclusive"):
        validate_process_candidate(candidate)


def test_material_merge_archives_real_verification_deterministically(tmp_path: Path) -> None:
    digest = "a" * 64
    old = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR,
                                            "at": "old"},
        "sources": [], "verified": {"by": "human:reviewer", "at": "yesterday"},
        "status": "curated", "title": "Human title", "extension": 1,
        "repo_jur_evidence_sha256": "b" * 64,
    }, "old", tmp_path / "x.md")
    new = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [], "repo_jur_evidence_sha256": digest,
    }, "new", tmp_path / "x.md")
    merged = merge_existing_process_candidate(
        old, new, ProcessMaterialityCategory.MATERIAL, reason="changed"
    )
    assert merged.frontmatter["status"] == "curated"
    assert merged.frontmatter["title"] == "Human title"
    assert merged.frontmatter["extension"] == 1
    assert "verified" not in merged.frontmatter
    assert merged.frontmatter["generated"]["at"] == f"evidence:{digest}"
    history = merged.frontmatter["repo_jur_verification_history"]
    assert history == [{"by": "human:reviewer", "at": "yesterday",
                        "invalidated_by": PROCESS_PRODUCER_ACTOR,
                        "reason": "changed"}]


def test_materiality_uses_body_and_provenance_not_generated_metadata(tmp_path: Path) -> None:
    base = {"type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
            "sources": []}
    old = ProcessConceptCandidate(ProcessConceptType.Decisao, base, "body", tmp_path / "x")
    technical = ProcessConceptCandidate(ProcessConceptType.Decisao,
        {**base, "generated": {"by": PROCESS_PRODUCER_ACTOR, "at": "x"}},
        "body", tmp_path / "x")
    material = ProcessConceptCandidate(ProcessConceptType.Decisao, base, "other", tmp_path / "x")
    assert classify_process_materiality(old, technical) is ProcessMaterialityCategory.TECHNICAL
    assert classify_process_materiality(old, material) is ProcessMaterialityCategory.MATERIAL


# 3.6 — A PDF-derived concept without an evidence reference is a configuration
# error: no invented resource, no publication.
def test_missing_evidence_resource_is_configuration_error(
    evidence: Path, tmp_path: Path
) -> None:
    context = validate_process_producer_context({"type": "Decisao"})
    with pytest.raises(ProcessProducerConfigurationError):
        produce_process(_artifacts(evidence), _decision(), _review(), context,
                        process_root=tmp_path / "p", bundle_root=tmp_path / "b")


# 5.3 — Status is never inserted or mutated; Human-Owned values survive
# regeneration; no _v2/UUID/stable-id is created.
def test_regeneration_preserves_human_owned_status_and_no_versioning(
    evidence: Path, tmp_path: Path
) -> None:
    kwargs = {"process_root": tmp_path / "process", "bundle_root": tmp_path / "bundle"}
    first = produce_process(_artifacts(evidence), _decision(), _review(),
                            _context(evidence), **kwargs)
    assert first.candidate is not None
    assert "status" not in first.candidate.frontmatter
    path = first.concept_path
    assert path is not None
    text = path.read_text(encoding="utf-8")
    text = text.replace("---\n", "---\nstatus: \"curated\"\n", 1)
    path.write_text(text, encoding="utf-8")
    second = produce_process(_artifacts(evidence), _decision(), _review(),
                             _context(evidence), **kwargs)
    # Equivalent inputs: NOOP, no write, and the Human-Owned status on disk
    # survives untouched (the Producer never inserts or mutates it).
    assert second.resolution is ProcessDuplicateResolution.NOOP
    assert not second.written
    stored = path.read_text(encoding="utf-8")
    assert 'status: "curated"' in stored
    assert "_v2" not in stored


# 5.4 — verified is never auto-created; a technical change preserves an active
# verified event; history never becomes active verified.
def test_technical_merge_preserves_active_verified(tmp_path: Path) -> None:
    old = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [], "verified": {"by": "human:revisor", "at": "2026-01-01"},
    }, "body", tmp_path / "x.md")
    new = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [],
    }, "body", tmp_path / "x.md")
    merged = merge_existing_process_candidate(
        old, new, ProcessMaterialityCategory.TECHNICAL, reason="technical"
    )
    assert merged.frontmatter["verified"] == {"by": "human:revisor",
                                              "at": "2026-01-01"}
    assert "repo_jur_verification_history" not in merged.frontmatter


def test_technical_merge_never_creates_verified(tmp_path: Path) -> None:
    old = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [],
    }, "body", tmp_path / "x.md")
    new = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [],
    }, "body", tmp_path / "x.md")
    merged = merge_existing_process_candidate(
        old, new, ProcessMaterialityCategory.TECHNICAL, reason="technical"
    )
    assert "verified" not in merged.frontmatter


# 5.5 — generated.at is not updated without a meaningful change.
def test_generated_at_preserved_on_technical_change(tmp_path: Path) -> None:
    old = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR,
                                        "at": "evidence:old"},
        "sources": [],
    }, "body", tmp_path / "x.md")
    new = ProcessConceptCandidate(ProcessConceptType.Decisao, {
        "type": "Decisao", "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [],
    }, "body", tmp_path / "x.md")
    merged = merge_existing_process_candidate(
        old, new, ProcessMaterialityCategory.TECHNICAL, reason="technical"
    )
    generated = merged.frontmatter["generated"]
    assert isinstance(generated, dict) and generated["at"] == "evidence:old"


# 5.8 — Identical inputs yield identical candidate bytes on every evaluation;
# no execution id, timestamp, or duration influences the candidate.
def test_render_is_deterministic(evidence: Path, tmp_path: Path) -> None:
    first = produce_process(_artifacts(evidence), _decision(), _review(),
                            _context(evidence),
                            process_root=tmp_path / "p1",
                            bundle_root=tmp_path / "b1")
    second = produce_process(_artifacts(evidence), _decision(), _review(),
                             _context(evidence),
                             process_root=tmp_path / "p2",
                             bundle_root=tmp_path / "b2")
    assert first.candidate is not None and second.candidate is not None
    assert first.candidate.render_text() == second.candidate.render_text()
    assert "execution" not in first.candidate.render_text()
