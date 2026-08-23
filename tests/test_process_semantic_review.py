from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Callable

import pytest

from pipeline_juridico.contracts import Phase1Artifacts, RouteTarget
from pipeline_juridico.domain_router import RoutingDecision, RoutingReasonCode
from pipeline_juridico.process_semantic_review import (
    ProcessPatch, ProcessReviewProfile, ProcessReviewRule, ProcessReviewResult,
    ProcessSemanticReviewBlockedError, ProcessSemanticReviewConfigurationError,
    ProcessSemanticReviewEngine, ReviewState,
)

MODULE_PATH = Path("src/pipeline_juridico/process_semantic_review.py")


def _artifacts(gate: str = "PASS") -> Phase1Artifacts:
    return Phase1Artifacts("[[Pág. 1]]\ntexto\n", json.dumps(
        {"result": {"quality_gate": gate}}
    ))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _decision(target: RouteTarget = RouteTarget.JUDICIAL_PROCESS) -> RoutingDecision:
    reason = (RoutingReasonCode.REQUESTED_DOMAIN_JUDICIAL_PROCESS
              if target is RouteTarget.JUDICIAL_PROCESS
              else RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE)
    return RoutingDecision(target, reason)


def _profile(*ids: str) -> ProcessReviewProfile:
    return ProcessReviewProfile("default", "1.0", tuple(ids))


def _rule(after: str = "dois um") -> ProcessReviewRule:
    return ProcessReviewRule(
        "r", "1", "page", "approved", "1",
        lambda _: [ProcessPatch("um dois", after, "structure", 1.0)],
    )


@pytest.mark.parametrize("gate", ["PASS", "PASS_WITH_WARNINGS"])
def test_eligible_gate_and_process_decision(gate: str) -> None:
    result = ProcessSemanticReviewEngine().review(
        _artifacts(gate), _decision(), _profile()
    )
    assert result == ProcessReviewResult(ReviewState.OK, (), (), (), ())


@pytest.mark.parametrize("report", ["x", "{}", '{"result":{}}'])
def test_invalid_report_is_blocked(report: str) -> None:
    with pytest.raises(ProcessSemanticReviewBlockedError) as caught:
        ProcessSemanticReviewEngine().review(
            Phase1Artifacts("x", report), _decision(), _profile()
        )
    assert caught.value.reason == "invalid_report"


def test_fail_gate_is_blocked_and_gate_override_absent() -> None:
    with pytest.raises(ProcessSemanticReviewBlockedError) as caught:
        ProcessSemanticReviewEngine().review(_artifacts("FAIL"), _decision(), _profile())
    assert caught.value.reason == "fail_gate"
    with pytest.raises(TypeError):
        ProcessSemanticReviewEngine().review(  # type: ignore[call-arg]
            _artifacts(), _decision(), _profile(), gate="PASS"
        )


@pytest.mark.parametrize("decision", [_decision(RouteTarget.LEGAL_KNOWLEDGE), None])
def test_non_process_or_absent_decision_is_configuration_error(decision) -> None:
    with pytest.raises(ProcessSemanticReviewConfigurationError):
        ProcessSemanticReviewEngine().review(_artifacts(), decision, _profile())


def test_structural_patch_is_warning_and_ambiguous_patch_requires_review() -> None:
    accepted = ProcessSemanticReviewEngine([_rule()]).review(
        _artifacts(), _decision(), _profile("r")
    )
    assert accepted.state is ReviewState.WARNING and len(accepted.patches) == 1
    rejected = ProcessSemanticReviewEngine([_rule("um dois inventado")]).review(
        _artifacts(), _decision(), _profile("r")
    )
    assert rejected.state is ReviewState.REVIEW_REQUIRED
    assert rejected.patches == () and rejected.warnings


def test_registry_is_immutable_and_profile_validation_is_strict() -> None:
    engine = ProcessSemanticReviewEngine([_rule()])
    assert isinstance(engine._rules, MappingProxyType)
    with pytest.raises(ProcessSemanticReviewConfigurationError):
        ProcessSemanticReviewEngine([_rule(), _rule()])
    with pytest.raises(ProcessSemanticReviewConfigurationError):
        engine.review(_artifacts(), _decision(), _profile("missing"))
    with pytest.raises(ProcessSemanticReviewConfigurationError):
        engine.review(_artifacts(), _decision(), _profile("r", "r"))


def test_result_and_engine_are_frozen_and_inputs_remain_identical() -> None:
    artifacts = _artifacts()
    before = (artifacts.markdown, artifacts.report_json)
    result = ProcessSemanticReviewEngine().review(artifacts, _decision(), _profile())
    with pytest.raises(FrozenInstanceError):
        result.state = ReviewState.WARNING  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        ProcessSemanticReviewEngine()._rules = {}  # type: ignore[misc]
    assert before == (artifacts.markdown, artifacts.report_json)


# 1.1 / 1.3 / 1.10 / 1.11 / 1.12 — source-inspection: no upstream, routing,
# LLM, storage, or Legal coupling in the review module.
def test_review_source_has_no_upstream_or_engine_coupling() -> None:
    source = MODULE_PATH.read_text()
    imported = _imported_modules(source)
    assert not imported & {
        "converter", "conversion_engine", "engines", "inspector",
        "evidence", "ocr", "openai", "google", "genai",
    }
    for forbidden in (
        "guard_legal_bundle_write", "write_atomic", "bundle/",
        "shared_index", "semantic_model", "external_classification",
        "legal_", "full_document", "overwrite",
    ):
        assert forbidden not in source
    # The decision type is consumed, never re-derived: no routing call site.
    assert "route(" not in source.replace("_recorded_gate_outcome(", "")


def test_review_performs_no_filesystem_write(tmp_path: Path) -> None:
    before = tuple(tmp_path.rglob("*"))
    ProcessSemanticReviewEngine().review(_artifacts(), _decision(), _profile())
    assert tuple(tmp_path.rglob("*")) == before


def test_review_is_deterministic_across_states() -> None:
    first = ProcessSemanticReviewEngine().review(_artifacts(), _decision(), _profile())
    second = ProcessSemanticReviewEngine().review(_artifacts(), _decision(), _profile())
    assert first == second
    assert tuple(field.name for field in fields(first)) == (
        "state", "patches", "extracted_fields",
        "classification_suggestions", "warnings",
    )
    assert isinstance(first.warnings, tuple)


# 1.4 — Phase 1 immutability across OK / WARNING / REVIEW_REQUIRED states.
def test_phase1_artifacts_stay_byte_identical_across_states() -> None:
    artifacts = _artifacts()
    markdown_digest = _hash(artifacts.markdown)
    report_before = artifacts.report_json
    results = [
        ProcessSemanticReviewEngine().review(artifacts, _decision(), _profile()),
        ProcessSemanticReviewEngine([_rule()]).review(
            artifacts, _decision(), _profile("r")
        ),
        ProcessSemanticReviewEngine([_rule("um dois inventado")]).review(
            artifacts, _decision(), _profile("r")
        ),
    ]
    assert {result.state for result in results} == {
        ReviewState.OK, ReviewState.WARNING, ReviewState.REVIEW_REQUIRED,
    }
    assert _hash(artifacts.markdown) == markdown_digest
    assert artifacts.report_json == report_before
    for result in results:
        assert result.state.value not in artifacts.report_json


# 1.6 — Word preservation rejects additions, removals, and paraphrases.
@pytest.mark.parametrize(
    ("before", "after"),
    [("texto original", "texto"), ("texto", "texto inventado"),
     ("Texto", "texto")],
)
def test_word_changing_patch_requires_review(before: str, after: str) -> None:
    result = ProcessSemanticReviewEngine([
        _rule(after=after)
    ]).review(_artifacts(), _decision(), _profile("r"))
    assert result.state is ReviewState.REVIEW_REQUIRED
    assert result.patches == ()


# 1.7 — Structured patch provenance shape.
def test_patch_carries_full_structured_provenance() -> None:
    assert tuple(field.name for field in fields(ProcessPatch)) == (
        "before", "after", "reason", "confidence", "page_refs", "evidence_refs",
    )
    patch = ProcessPatch("a", "a", "reason", 1.0)
    assert patch.page_refs == () and patch.evidence_refs == ()


# 1.9 — Rule provenance is enforced at registration.
@pytest.mark.parametrize(
    "missing",
    ["rule_id", "rule_version", "scope", "source",
     "validation_logic_version", "evaluate"],
)
def test_registry_rejects_missing_rule_provenance(missing: str) -> None:
    values = {
        "rule_id": "r", "rule_version": "1", "scope": "page",
        "source": "approved", "validation_logic_version": "1",
        "evaluate": lambda _markdown: [],
    }
    del values[missing]
    with pytest.raises(ProcessSemanticReviewConfigurationError):
        ProcessSemanticReviewEngine([SimpleNamespace(**values)])  # type: ignore[list-item]


def test_empty_registry_is_a_zero_rule_run() -> None:
    engine = ProcessSemanticReviewEngine()
    assert engine._rules == {}
    assert engine.review(_artifacts(), _decision(), _profile()) == ProcessReviewResult(
        ReviewState.OK, (), (), (), ()
    )


def test_profile_provenance_is_required() -> None:
    with pytest.raises(ProcessSemanticReviewConfigurationError):
        ProcessSemanticReviewEngine().review(
            _artifacts(), _decision(), ProcessReviewProfile("", "1.0", ())
        )


def test_review_rule_evaluation_error_is_configuration_error() -> None:
    def broken(_markdown: str) -> list[ProcessPatch]:
        return ["not-a-patch"]  # type: ignore[return-value]

    engine = ProcessSemanticReviewEngine([
        ProcessReviewRule("bad", "1", "page", "approved", "1", broken)
    ])
    with pytest.raises(ProcessSemanticReviewConfigurationError):
        engine.review(_artifacts(), _decision(), _profile("bad"))
