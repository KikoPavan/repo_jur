from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Callable

import pytest

from pipeline_juridico.contracts import Phase1Artifacts
from pipeline_juridico.legal_semantic_review import (
    ClassificationSuggestion,
    ExtractedField,
    LegalPatch,
    LegalReviewProfile,
    LegalReviewRule,
    LegalSemanticReviewBlockedError,
    LegalSemanticReviewConfigurationError,
    LegalSemanticReviewEngine,
    ReviewResult,
    ReviewState,
)


MODULE_PATH = Path("src/pipeline_juridico/legal_semantic_review.py")


def _artifacts(
    *,
    markdown: str = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nConteúdo literal\n",
    gate: str = "PASS",
    report_json: str | None = None,
) -> Phase1Artifacts:
    report = {"result": {"quality_gate": gate}}
    return Phase1Artifacts(
        markdown=markdown,
        report_json=json.dumps(report) if report_json is None else report_json,
    )


def _profile(*rule_ids: str) -> LegalReviewProfile:
    return LegalReviewProfile("test.profile", "1.0", tuple(rule_ids))


def _patch(
    *,
    before: str = "campo dois campo um",
    after: str = "campo um campo dois",
) -> LegalPatch:
    return LegalPatch(
        before=before,
        after=after,
        reason="structural association",
        confidence=1.0,
        page_refs=("1",),
        evidence_refs=("sha256:test",),
    )


def _rule(
    rule_id: str = "test.rule",
    *,
    evaluate: Callable[[str], list[LegalPatch]] | None = None,
) -> LegalReviewRule:
    return LegalReviewRule(
        rule_id=rule_id,
        rule_version="1.0",
        scope="page-marker-boundary",
        source="technical-implementation-spec-repo-jur-v1.2-FROZEN",
        validation_logic_version="1.0",
        evaluate=evaluate or (lambda _markdown: []),
    )


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


# 1.1 — Phase 1 input only; no upstream processing or resolution coupling.
def test_review_accepts_phase1_artifacts_without_upstream_dependencies() -> None:
    result = LegalSemanticReviewEngine().review(_artifacts(), _profile())
    assert result.state is ReviewState.OK

    imported = _imported_modules(MODULE_PATH.read_text())
    assert not imported & {
        "converter",
        "conversion_engine",
        "engines",
        "inspector",
        "evidence",
        "ocr",
    }


# 1.2 — Recorded post-gate invariant.
@pytest.mark.parametrize("gate", ["PASS", "PASS_WITH_WARNINGS"])
def test_eligible_recorded_gate_proceeds(gate: str) -> None:
    assert LegalSemanticReviewEngine().review(
        _artifacts(gate=gate), _profile()
    ).state is ReviewState.OK


@pytest.mark.parametrize(
    "artifacts",
    [
        _artifacts(gate="FAIL"),
        _artifacts(report_json="not-json"),
        _artifacts(report_json="[]"),
        _artifacts(report_json="{}"),
        _artifacts(report_json='{"result": {}}'),
        _artifacts(gate="UNKNOWN"),
    ],
)
def test_fail_or_invalid_recorded_gate_blocks_without_result(
    artifacts: Phase1Artifacts,
) -> None:
    with pytest.raises(LegalSemanticReviewBlockedError):
        LegalSemanticReviewEngine().review(artifacts, _profile())


def test_review_has_no_gate_override_parameter() -> None:
    with pytest.raises(TypeError):
        LegalSemanticReviewEngine().review(  # type: ignore[call-arg]
            _artifacts(gate="FAIL"), _profile(), gate="PASS"
        )


# 1.3 — Inputs are byte-identical and output remains external.
def test_review_keeps_phase1_artifacts_byte_identical() -> None:
    artifacts = _artifacts()
    markdown_hash = _hash(artifacts.markdown)
    report_before = artifacts.report_json
    patch = _patch()
    result = LegalSemanticReviewEngine(
        [_rule(evaluate=lambda _markdown: [patch])]
    ).review(artifacts, _profile("test.rule"))

    assert _hash(artifacts.markdown) == markdown_hash
    assert artifacts.report_json == report_before
    assert patch.reason not in artifacts.markdown
    assert result.state.value not in artifacts.report_json


# 1.4 — Frozen, deterministic result vocabulary and shape.
def test_review_result_contract_is_frozen_and_has_no_run_metadata() -> None:
    result = LegalSemanticReviewEngine().review(_artifacts(), _profile())
    assert result == ReviewResult(ReviewState.OK, (), (), (), ())
    assert {member.value for member in ReviewState} == {
        "OK",
        "WARNING",
        "REVIEW_REQUIRED",
    }
    assert tuple(field.name for field in fields(result)) == (
        "state",
        "patches",
        "extracted_fields",
        "classification_suggestions",
        "warnings",
    )
    assert isinstance(result.warnings, tuple)
    with pytest.raises(FrozenInstanceError):
        result.state = ReviewState.WARNING  # type: ignore[misc]
    assert result == LegalSemanticReviewEngine().review(_artifacts(), _profile())


def test_auxiliary_output_contracts_are_frozen() -> None:
    extracted = ExtractedField("field", "value", ("1",))
    suggestion = ClassificationSuggestion(None, "operator review", 0.0)
    assert extracted.page_refs == ("1",)
    assert suggestion.type is None
    with pytest.raises(FrozenInstanceError):
        extracted.value = "changed"  # type: ignore[misc]


# 1.5 / 1.7 — Exact token-multiset preservation and ambiguity handling.
def test_word_preserving_structural_patch_is_returned() -> None:
    patch = _patch(before="A B A", after="A A B")
    result = LegalSemanticReviewEngine(
        [_rule(evaluate=lambda _markdown: [patch])]
    ).review(_artifacts(), _profile("test.rule"))
    assert result.state is ReviewState.WARNING
    assert result.patches == (patch,)
    assert result.warnings == ()


@pytest.mark.parametrize(
    ("before", "after"),
    [("texto original", "texto"), ("texto", "texto inventado"), ("Texto", "texto")],
)
def test_word_changing_patch_is_rejected_and_requires_review(
    before: str, after: str
) -> None:
    result = LegalSemanticReviewEngine(
        [_rule(evaluate=lambda _markdown: [_patch(before=before, after=after)])]
    ).review(_artifacts(), _profile("test.rule"))
    assert result.state is ReviewState.REVIEW_REQUIRED
    assert result.patches == ()
    assert result.warnings == ("rule test.rule produced a non-structural patch",)
    assert after not in result.patches


# 1.6 — Patch provenance and no whole-body replacement surface.
def test_patch_has_complete_structured_provenance() -> None:
    assert tuple(field.name for field in fields(LegalPatch)) == (
        "before",
        "after",
        "reason",
        "confidence",
        "page_refs",
        "evidence_refs",
    )
    assert LegalPatch("a", "a", "reason", 1.0).page_refs == ()
    assert LegalPatch("a", "a", "reason", 1.0).evidence_refs == ()

    source = MODULE_PATH.read_text().lower()
    assert "full_document" not in source
    assert "overwrite" not in source


# 1.8 — Provenance registry and profile contracts.
@pytest.mark.parametrize(
    "missing",
    ["rule_id", "rule_version", "scope", "source", "validation_logic_version", "evaluate"],
)
def test_registry_rejects_missing_rule_provenance(missing: str) -> None:
    values = {
        "rule_id": "test.rule",
        "rule_version": "1.0",
        "scope": "boundary",
        "source": "frozen-spec-v1",
        "validation_logic_version": "1.0",
        "evaluate": lambda _markdown: [],
    }
    del values[missing]
    with pytest.raises(LegalSemanticReviewConfigurationError):
        LegalSemanticReviewEngine([SimpleNamespace(**values)])  # type: ignore[list-item]


def test_registry_is_immutable_and_rejects_duplicate_ids() -> None:
    rule = _rule()
    engine = LegalSemanticReviewEngine([rule])
    assert isinstance(engine._rules, MappingProxyType)
    assert engine._rules == {rule.rule_id: rule}
    with pytest.raises(TypeError):
        engine._rules["other"] = rule  # type: ignore[index]
    with pytest.raises(LegalSemanticReviewConfigurationError):
        LegalSemanticReviewEngine([rule, rule])


def test_empty_registry_is_valid_zero_rule_run() -> None:
    engine = LegalSemanticReviewEngine()
    assert engine._rules == {}
    assert engine.review(_artifacts(), _profile()) == ReviewResult(
        ReviewState.OK, (), (), (), ()
    )


def test_profile_rejects_unknown_and_duplicate_rule_ids_before_evaluation() -> None:
    calls = 0

    def evaluate(_markdown: str) -> list[LegalPatch]:
        nonlocal calls
        calls += 1
        return []

    engine = LegalSemanticReviewEngine([_rule(evaluate=evaluate)])
    with pytest.raises(LegalSemanticReviewConfigurationError):
        engine.review(_artifacts(), _profile("missing"))
    with pytest.raises(LegalSemanticReviewConfigurationError):
        engine.review(_artifacts(), _profile("test.rule", "test.rule"))
    assert calls == 0


# 1.9–1.11 — Engine neutrality, no writes, and bounded-context isolation.
def test_source_has_no_external_engine_model_or_storage_coupling() -> None:
    source = MODULE_PATH.read_text()
    lower = source.lower()
    imported = _imported_modules(source)
    assert not imported & {
        "converter",
        "conversion_engine",
        "engines",
        "inspector",
        "evidence",
        "ocr",
        "openai",
        "google",
    }
    for forbidden in (
        "guard_legal_bundle_write",
        "write_atomic",
        "bundle/",
        "judicial",
        "process_schema",
        "shared_index",
        "semantic_model",
        "external_classification",
    ):
        assert forbidden not in lower


def test_review_performs_no_filesystem_write(tmp_path: Path) -> None:
    before = tuple(tmp_path.rglob("*"))
    result = LegalSemanticReviewEngine().review(_artifacts(), _profile())
    assert result.state is ReviewState.OK
    assert tuple(tmp_path.rglob("*")) == before
