from __future__ import annotations

import hashlib
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Callable

import pytest

from pipeline_juridico.contracts import (
    CriticalFinding,
    CriticalValidationResult,
    CriticalValidationStatus,
)
from pipeline_juridico.conversion_engine import Phase1Artifacts
from pipeline_juridico.critical_data import (
    CriticalDataValidator,
    CriticalValidationConfigurationError,
    CriticalValidationProfile,
    CriticalValidationRule,
)


def _artifacts(markdown: str = "conteudo literal") -> Phase1Artifacts:
    return Phase1Artifacts(markdown=markdown, report_json="{}")


def _profile(*rule_ids: str) -> CriticalValidationProfile:
    return CriticalValidationProfile(
        profile_id="test.profile",
        profile_version="1.0",
        enabled_rule_ids=tuple(rule_ids),
    )


def _rule(
    rule_id: str = "test.rule",
    *,
    failure_status: CriticalValidationStatus = CriticalValidationStatus.WARNING,
    evaluate: Callable[[Phase1Artifacts], list[CriticalFinding]] | None = None,
) -> CriticalValidationRule:
    return CriticalValidationRule(
        rule_id=rule_id,
        rule_version="1.0",
        applies_to="test-field",
        source="test-specification-v1",
        validation_logic_version="1.0",
        failure_status=failure_status,
        evaluate=evaluate or (lambda _artifacts: []),
    )


def _finding(code: str = "TEST_INCONSISTENCY") -> CriticalFinding:
    return CriticalFinding(code=code, message=f"message for {code}")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def test_registry_lifecycle_stores_valid_rules_in_immutable_mapping() -> None:
    rule = _rule()
    validator = CriticalDataValidator([rule])

    assert isinstance(validator._rules, MappingProxyType)
    assert validator._rules == {rule.rule_id: rule}
    with pytest.raises(TypeError):
        validator._rules["test.another"] = rule  # type: ignore[index]
    with pytest.raises(AttributeError):
        validator._rules = {}  # type: ignore[misc]


@pytest.mark.parametrize(
    "missing_field",
    [
        "rule_id",
        "rule_version",
        "applies_to",
        "source",
        "validation_logic_version",
        "failure_status",
    ],
)
def test_registry_rejects_each_missing_provenance_field(
    missing_field: str,
) -> None:
    evaluated = False

    def evaluate(_artifacts: Phase1Artifacts) -> list[CriticalFinding]:
        nonlocal evaluated
        evaluated = True
        return [_finding()]

    values = {
        "rule_id": "test.rule",
        "rule_version": "1.0",
        "applies_to": "test-field",
        "source": "test-specification-v1",
        "validation_logic_version": "1.0",
        "failure_status": CriticalValidationStatus.WARNING,
        "evaluate": evaluate,
    }
    del values[missing_field]

    with pytest.raises(CriticalValidationConfigurationError):
        CriticalDataValidator([SimpleNamespace(**values)])  # type: ignore[list-item]
    assert evaluated is False


def test_registry_rejects_invalid_failure_status_without_evaluation() -> None:
    evaluated = False

    def evaluate(_artifacts: Phase1Artifacts) -> list[CriticalFinding]:
        nonlocal evaluated
        evaluated = True
        return [_finding()]

    rule = _rule(
        failure_status=CriticalValidationStatus.OK,
        evaluate=evaluate,
    )
    with pytest.raises(CriticalValidationConfigurationError):
        CriticalDataValidator([rule])
    assert evaluated is False


def test_registry_rejects_duplicate_rule_id_and_defaults_to_empty() -> None:
    with pytest.raises(CriticalValidationConfigurationError):
        CriticalDataValidator([_rule(), _rule()])

    validator = CriticalDataValidator()
    assert isinstance(validator._rules, MappingProxyType)
    assert validator._rules == {}


@pytest.mark.parametrize(
    "markdown",
    [
        "[[Pag. 1]] texto nativo",
        "[[Pag. 1]] texto de OCR",
        "[[Pag. 1]] texto hibrido",
        "",
    ],
)
def test_zero_rule_default_is_ok_for_representative_artifacts(markdown: str) -> None:
    result = CriticalDataValidator().validate(_artifacts(markdown), _profile())

    assert result == CriticalValidationResult(
        status=CriticalValidationStatus.OK,
        findings=[],
    )


@pytest.mark.parametrize(
    "status",
    [CriticalValidationStatus.WARNING, CriticalValidationStatus.REVIEW_REQUIRED],
)
def test_validation_never_mutates_markdown_with_or_without_findings(
    status: CriticalValidationStatus,
) -> None:
    artifacts = _artifacts("literal markdown 123")
    before = _sha256(artifacts.markdown)
    CriticalDataValidator().validate(artifacts, _profile())
    assert _sha256(artifacts.markdown) == before

    rule = _rule(failure_status=status, evaluate=lambda _artifacts: [_finding()])
    CriticalDataValidator([rule]).validate(artifacts, _profile(rule.rule_id))
    assert _sha256(artifacts.markdown) == before


def test_findings_remain_outside_markdown() -> None:
    artifacts = _artifacts("original literal body")
    finding = _finding("TEST_EXTERNAL_FINDING")
    rule = _rule(evaluate=lambda _artifacts: [finding])

    result = CriticalDataValidator([rule]).validate(
        artifacts, _profile(rule.rule_id)
    )

    assert result.findings == [finding]
    assert finding.code not in artifacts.markdown
    assert finding.message not in artifacts.markdown


def test_module_source_avoids_downstream_types_and_storage_concern() -> None:
    source = Path("src/pipeline_juridico/critical_data.py").read_text()

    assert "GateState" not in source
    assert "RouteTarget" not in source
    assert "bundle" not in source


def test_profile_selects_only_named_rules_and_empty_profile_runs_none() -> None:
    calls: list[str] = []

    def evaluator(name: str) -> Callable[[Phase1Artifacts], list[CriticalFinding]]:
        def evaluate(_artifacts: Phase1Artifacts) -> list[CriticalFinding]:
            calls.append(name)
            return [_finding(name)]

        return evaluate

    first = _rule("test.first", evaluate=evaluator("first"))
    second = _rule("test.second", evaluate=evaluator("second"))
    validator = CriticalDataValidator([first, second])

    result = validator.validate(_artifacts(), _profile(second.rule_id))
    assert calls == ["second"]
    assert result.findings == [_finding("second")]

    calls.clear()
    result = validator.validate(_artifacts(), _profile())
    assert calls == []
    assert result == CriticalValidationResult(CriticalValidationStatus.OK, [])


def test_unresolvable_profile_rule_is_configuration_error() -> None:
    with pytest.raises(CriticalValidationConfigurationError):
        CriticalDataValidator().validate(_artifacts(), _profile("test.missing"))


def test_duplicate_profile_rule_is_rejected_before_any_rule_executes() -> None:
    calls = 0

    def evaluate(_artifacts: Phase1Artifacts) -> list[CriticalFinding]:
        nonlocal calls
        calls += 1
        return [_finding()]

    rule = _rule(evaluate=evaluate)
    validator = CriticalDataValidator([rule])
    with pytest.raises(CriticalValidationConfigurationError):
        validator.validate(_artifacts(), _profile(rule.rule_id, rule.rule_id))
    assert calls == 0


@pytest.mark.parametrize(
    "failure_status",
    [CriticalValidationStatus.WARNING, CriticalValidationStatus.REVIEW_REQUIRED],
)
def test_rule_declared_severity_is_returned_without_dynamic_reassignment(
    failure_status: CriticalValidationStatus,
) -> None:
    rule = _rule(
        failure_status=failure_status,
        evaluate=lambda _artifacts: [_finding()],
    )

    result = CriticalDataValidator([rule]).validate(
        _artifacts(), _profile(rule.rule_id)
    )

    assert result.status is failure_status


def test_aggregation_uses_highest_severity_and_preserves_all_findings() -> None:
    warning_findings = [_finding("WARNING_ONE"), _finding("WARNING_TWO")]
    warning = _rule(
        "test.warning",
        failure_status=CriticalValidationStatus.WARNING,
        evaluate=lambda _artifacts: warning_findings,
    )
    review_finding = _finding("REVIEW_ONE")
    review = _rule(
        "test.review",
        failure_status=CriticalValidationStatus.REVIEW_REQUIRED,
        evaluate=lambda _artifacts: [review_finding],
    )
    no_findings = _rule("test.empty")
    validator = CriticalDataValidator([warning, review, no_findings])

    empty = validator.validate(_artifacts(), _profile(no_findings.rule_id))
    warnings = validator.validate(_artifacts(), _profile(warning.rule_id))
    mixed = validator.validate(
        _artifacts(), _profile(warning.rule_id, review.rule_id)
    )

    assert empty == CriticalValidationResult(CriticalValidationStatus.OK, [])
    assert warnings.status is CriticalValidationStatus.WARNING
    assert warnings.findings == warning_findings
    assert mixed.status is CriticalValidationStatus.REVIEW_REQUIRED
    assert mixed.findings == [*warning_findings, review_finding]


def test_rule_discovers_its_own_candidates_deterministically_and_read_only() -> None:
    artifacts = _artifacts("TEST-ID: invalid\nOther field: untouched")
    before = _sha256(artifacts.markdown)

    def discover_and_evaluate(value: Phase1Artifacts) -> list[CriticalFinding]:
        return [_finding("TEST_ID_INVALID")] if "TEST-ID: invalid" in value.markdown else []

    rule = _rule(evaluate=discover_and_evaluate)
    validator = CriticalDataValidator([rule])

    first = validator.validate(artifacts, _profile(rule.rule_id))
    second = validator.validate(artifacts, _profile(rule.rule_id))

    assert first == second
    assert first.findings == [_finding("TEST_ID_INVALID")]
    assert _sha256(artifacts.markdown) == before


def test_non_ok_result_has_only_reused_status_and_findings_shape() -> None:
    rule = _rule(evaluate=lambda _artifacts: [_finding()])
    result = CriticalDataValidator([rule]).validate(
        _artifacts(), _profile(rule.rule_id)
    )

    assert type(result) is CriticalValidationResult
    assert type(result.status) is CriticalValidationStatus
    assert set(vars(result)) == {"status", "findings"}


def test_conflicting_looking_content_is_ignored_without_authorized_rule() -> None:
    artifacts = _artifacts("TEST-ID: 111\nTEST-ID: 222")

    result = CriticalDataValidator().validate(artifacts, _profile())

    assert result == CriticalValidationResult(CriticalValidationStatus.OK, [])


def test_authorized_rule_signals_conflict_without_selecting_a_value() -> None:
    artifacts = _artifacts("TEST-ID: 111\nTEST-ID: 222")
    finding = _finding("TEST_CONFLICT")
    rule = _rule(
        failure_status=CriticalValidationStatus.REVIEW_REQUIRED,
        evaluate=lambda value: [finding]
        if {"TEST-ID: 111", "TEST-ID: 222"}.issubset(value.markdown.splitlines())
        else [],
    )

    result = CriticalDataValidator([rule]).validate(
        artifacts, _profile(rule.rule_id)
    )

    assert result == CriticalValidationResult(
        CriticalValidationStatus.REVIEW_REQUIRED, [finding]
    )
    assert artifacts.markdown == "TEST-ID: 111\nTEST-ID: 222"


def test_rule_does_not_cross_check_redundant_values_outside_its_scope() -> None:
    artifacts = _artifacts("SCOPED-ID: valid\nOTHER-ID: one\nOTHER-ID: two")

    def evaluate(value: Phase1Artifacts) -> list[CriticalFinding]:
        return [] if "SCOPED-ID: valid" in value.markdown else [_finding()]

    rule = _rule(evaluate=evaluate)
    result = CriticalDataValidator([rule]).validate(
        artifacts, _profile(rule.rule_id)
    )

    assert result == CriticalValidationResult(CriticalValidationStatus.OK, [])
