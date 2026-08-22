from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import pytest

from pipeline_juridico.contracts import (
    CriticalFinding,
    CriticalValidationStatus,
    GateState,
)
from pipeline_juridico.conversion_engine import Phase1Artifacts
from pipeline_juridico.critical_data import (
    CriticalDataValidator,
    CriticalValidationProfile,
    CriticalValidationRule,
)
from pipeline_juridico.quality_gate import QualityGateResult, evaluate


def _page(
    number: int,
    *,
    method: str = "texto_nativo",
    status: str = "sucesso",
    characters: int = 20,
    warnings: list[object] | None = None,
    error: str | None = None,
    truncated: bool = False,
) -> dict[str, object]:
    return {
        "page_number": number,
        "method": method,
        "char_count": characters,
        "warnings": [] if warnings is None else warnings,
        "errors": ([] if error is None and status == "sucesso" else [error or status]),
        "truncated": truncated,
    }


def _report(
    *,
    page_count: int = 1,
    pages: list[dict[str, object]] | None = None,
    status: str = "sucesso",
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "execution_id": "00000000-0000-0000-0000-000000000001",
        "input": {
            "byte_size": 1234,
            "sha256": "a" * 64,
            "page_count": page_count,
        },
        "phase1": {}, "artifacts": {"markdown_sha256": "b" * 64},
        "telemetry": {},
        "pages": (
            [_page(number) for number in range(1, page_count + 1)]
            if pages is None
            else pages
        ),
    }


def _artifacts(
    *,
    markdown: str = "[[Pág. 1]]\nConteúdo literal\n",
    report: dict[str, object] | None = None,
    report_json: str | None = None,
) -> Phase1Artifacts:
    serialized = json.dumps(_report() if report is None else report, ensure_ascii=False)
    return Phase1Artifacts(
        markdown=markdown,
        report_json=serialized if report_json is None else report_json,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _assert_fail(artifacts: Phase1Artifacts, fragment: str | None = None) -> None:
    result = evaluate(artifacts)
    assert result.state is GateState.FAIL
    assert result.errors
    if fragment is not None:
        assert any(fragment in error.lower() for error in result.errors)


def test_boundary_accepts_phase1_artifacts_without_conversion_path() -> None:
    assert evaluate(_artifacts()).state is GateState.PASS

    source = Path("src/pipeline_juridico/quality_gate.py").read_text()
    for forbidden in (
        ".converter",
        ".engines",
        ".inspector",
        ".evidence",
        ".router",
    ):
        assert forbidden not in source


def test_three_state_contract_and_serialized_value() -> None:
    passing = evaluate(_artifacts())
    warned_report = _report(pages=[_page(1, warnings=["aviso técnico"])])
    warned = evaluate(_artifacts(report=warned_report))
    failed = evaluate(_artifacts(markdown="sem marcador"))

    assert passing.state is GateState.PASS
    assert warned.state is GateState.PASS_WITH_WARNINGS
    assert warned.state.value == "PASS_WITH_WARNINGS"
    assert warned.state.value != "PASS WITH WARNINGS"
    assert failed.state is GateState.FAIL
    assert {result.state for result in (passing, warned, failed)} <= set(GateState)


def test_exact_ordered_page_markers_pass() -> None:
    markdown = "[[Pág. 1]]\nUm\n[[Pág. 2]]\nDois\n[[Pág. 3]]\nTrês\n"
    assert evaluate(_artifacts(markdown=markdown, report=_report(page_count=3))).state is GateState.PASS


@pytest.mark.parametrize(
    ("markdown", "page_count"),
    [
        ("[[Pág. 1]]\n", 2),
        ("[[Pág. 1]]\n[[Pág. 1]]\n", 2),
        ("[[Pág. 2]]\n[[Pág. 1]]\n", 2),
        ("[[Pág. 1]]\n[[Pág. 2]]\n", 1),
        ("sem marcadores", 1),
    ],
)
def test_marker_deficiencies_fail(markdown: str, page_count: int) -> None:
    _assert_fail(_artifacts(markdown=markdown, report=_report(page_count=page_count)), "marker")


def test_zero_physical_pages_fails() -> None:
    _assert_fail(_artifacts(markdown="", report=_report(page_count=0)), "page")


@pytest.mark.parametrize("status", ["falha", "incompleto", "pendente"])
@pytest.mark.parametrize("error", [None, "informational detail"])
def test_not_completed_page_errors_fail_independently_of_other_fields(
    status: str, error: str | None
) -> None:
    _assert_fail(
        _artifacts(report=_report(pages=[_page(1, status=status, error=error)])),
        "errors",
    )


@pytest.mark.parametrize("status", ["sucesso", "falha"])
def test_error_method_is_independently_fatal(status: str) -> None:
    report = _report(
        status="incompleto",
        pages=[_page(1, method="erro", status=status, characters=0)],
    )
    _assert_fail(_artifacts(report=report), "method")


def test_empty_return_is_fatal_but_blank_page_passes_without_warning() -> None:
    empty = evaluate(_artifacts(report=_report(pages=[_page(1, characters=0)])))
    blank = evaluate(
        _artifacts(report=_report(pages=[_page(1, method="vazia", characters=0)]))
    )

    assert empty.state is GateState.FAIL
    assert any("empty" in error.lower() for error in empty.errors)
    assert blank.state is GateState.PASS
    assert blank.warnings == ()


def test_top_level_incomplete_status_alone_does_not_fail() -> None:
    result = evaluate(_artifacts(report=_report(status="incompleto")))
    assert result.state is GateState.PASS


@pytest.mark.parametrize(
    ("markdown", "fragment"),
    [
        ("[[Pág. 1]]\n\ud800", "utf-8"),
        ("[[Pág. 1]]\nNUL:\x00", "nul"),
        ("[[Pág. 1]]\r\nConteúdo", "cr"),
        ("[[Pág. 1]]\n<!-- método: texto_nativo -->\n", "method comment"),
    ],
)
def test_markdown_structural_failures(markdown: str, fragment: str) -> None:
    _assert_fail(_artifacts(markdown=markdown), fragment)


def test_markers_only_boundary_literal_passes_textual_checks() -> None:
    assert evaluate(_artifacts(markdown="[[Pág. 1]]\nLiteral\n")).state is GateState.PASS


def test_unparseable_report_fails() -> None:
    _assert_fail(_artifacts(report_json="{not-json"), "json")


def test_null_report_root_fails() -> None:
    result = evaluate(_artifacts(report_json="null"))

    assert result.state is GateState.FAIL
    assert any("root must be an object" in error for error in result.errors)


@pytest.mark.parametrize("field", ["sha256", "page_count"])
def test_missing_required_source_field_fails(field: str) -> None:
    report = _report()
    del report["input"][field]  # type: ignore[index]
    _assert_fail(_artifacts(report=report), field)


@pytest.mark.parametrize("field", ["page_number", "method", "char_count", "errors", "truncated"])
def test_missing_required_page_field_fails(field: str) -> None:
    page = _page(1)
    del page[field]
    _assert_fail(_artifacts(report=_report(pages=[page])), field)


@pytest.mark.parametrize(
    "pages",
    [
        [_page(1)],
        [_page(1), _page(1)],
        [_page(1), _page(3)],
        [_page(1), _page(2), _page(3)],
    ],
)
def test_inventory_must_be_exactly_complete(pages: list[dict[str, object]]) -> None:
    _assert_fail(
        _artifacts(
            markdown="[[Pág. 1]]\n[[Pág. 2]]\n",
            report=_report(page_count=2, pages=pages),
        ),
        "inventory",
    )


def test_inventory_record_order_is_not_normative() -> None:
    report = _report(page_count=2, pages=[_page(2), _page(1)])
    result = evaluate(_artifacts(markdown="[[Pág. 1]]\n[[Pág. 2]]\n", report=report))
    assert result.state is GateState.PASS


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sha256", 123),
        ("page_count", "1"),
    ],
)
def test_required_source_fields_have_exact_types(field: str, value: object) -> None:
    report = _report()
    report["input"][field] = value  # type: ignore[index]
    _assert_fail(_artifacts(report=report), field)


def test_invalid_method_and_page_field_types_fail() -> None:
    for field, value in (
        ("page_number", True),
        ("method", "unknown"),
        ("char_count", False),
        ("errors", "bad"),
    ):
        page = _page(1)
        page[field] = value
        _assert_fail(_artifacts(report=_report(pages=[page])), field)


def test_warning_aggregation_uses_completed_pages_in_report_order() -> None:
    report = _report(
        page_count=2,
        pages=[
            _page(2, warnings=["", "segundo"]),
            _page(1, warnings=["primeiro", 12, "  "]),
        ],
    )
    result = evaluate(_artifacts(markdown="[[Pág. 1]]\n[[Pág. 2]]\n", report=report))
    assert result.state is GateState.PASS_WITH_WARNINGS
    assert result.warnings == ("segundo", "primeiro")


@pytest.mark.parametrize("method", ["ocr_integral", "hibrido", "vazia"])
def test_ocr_and_blank_methods_do_not_synthesize_warnings(method: str) -> None:
    characters = 0 if method == "vazia" else 20
    result = evaluate(
        _artifacts(report=_report(pages=[_page(1, method=method, characters=characters)]))
    )
    assert result.state is GateState.PASS
    assert result.warnings == ()


def test_markers_and_observability_fields_do_not_synthesize_warnings() -> None:
    report = _report()
    report["input"]["byte_size"] = 10**12  # type: ignore[index]
    report["telemetry"] = {"runtime": {"markitdown": "engine-identity"}, "duration_ms": 10**12}
    artifacts = _artifacts(markdown="[[Pág. 1]]\n[[TEXTO ILEGÍVEL]]\n", report=report)
    result = evaluate(artifacts)
    assert result.state is GateState.PASS
    assert result.warnings == ()


def test_evaluation_is_deterministic_and_has_no_telemetry() -> None:
    artifacts = _artifacts()
    first = evaluate(artifacts)
    second = evaluate(artifacts)
    assert (first.state, first.warnings, first.errors) == (
        second.state,
        second.warnings,
        second.errors,
    )
    assert not ({"execution_id", "run_id", "timestamp", "duration"} & set(vars(first)))


def test_diagnostics_are_non_authoritative() -> None:
    result = evaluate(_artifacts())
    normative = (result.state, result.warnings, result.errors)
    result.diagnostics["score"] = -999
    result.diagnostics.clear()
    assert (result.state, result.warnings, result.errors) == normative


@pytest.mark.parametrize(
    "artifacts",
    [
        _artifacts(),
        _artifacts(report=_report(pages=[_page(1, warnings=["external warning"])])),
        _artifacts(markdown="missing marker"),
    ],
)
def test_evaluation_never_mutates_artifacts(artifacts: Phase1Artifacts) -> None:
    markdown_hash = _sha256(artifacts.markdown)
    report_bytes = artifacts.report_json.encode("utf-8")
    result = evaluate(artifacts)
    assert _sha256(artifacts.markdown) == markdown_hash
    assert artifacts.report_json.encode("utf-8") == report_bytes
    assert not any(text in artifacts.markdown for text in (*result.warnings, *result.errors))


def test_module_source_is_domain_neutral_and_storage_independent() -> None:
    source = Path("src/pipeline_juridico/quality_gate.py").read_text()
    forbidden = (
        "CriticalValidationResult",
        "CriticalValidationStatus",
        "CriticalFinding",
        "CriticalDataValidator",
        "RouteTarget",
        "bundle",
    )
    assert all(token not in source for token in forbidden)


def test_critical_data_review_required_does_not_change_physical_gate() -> None:
    artifacts = _artifacts()
    finding = CriticalFinding(code="TEST_REVIEW", message="review")
    rule = CriticalValidationRule(
        rule_id="test.review",
        rule_version="1.0",
        applies_to="test-field",
        source="test-specification-v1",
        validation_logic_version="1.0",
        failure_status=CriticalValidationStatus.REVIEW_REQUIRED,
        evaluate=lambda _artifacts: [finding],
    )
    profile = CriticalValidationProfile("test.profile", "1.0", (rule.rule_id,))
    critical = CriticalDataValidator([rule]).validate(artifacts, profile)
    gate = evaluate(artifacts)

    assert critical.status is CriticalValidationStatus.REVIEW_REQUIRED
    assert gate.state is GateState.PASS
    assert set(vars(gate)) == {"state", "warnings", "errors", "diagnostics"}
    assert all("critical" not in name and "review" not in name for name in vars(gate))


@pytest.mark.parametrize(
    "factory",
    [
        lambda: _artifacts(),
        lambda: _artifacts(report=_report(pages=[_page(1, warnings=["warning"])])),
        lambda: _artifacts(markdown="invalid"),
    ],
)
def test_gate_never_writes_or_creates_lifecycle_values(
    factory: Callable[[], Phase1Artifacts],
) -> None:
    canonical_path = Path("repo_jur") / "bundle"
    assert not canonical_path.exists()
    result = evaluate(factory())
    assert not canonical_path.exists()
    assert set(vars(result)) == {"state", "warnings", "errors", "diagnostics"}
    assert "verified" not in vars(result)
    assert "status" not in vars(result)


def test_no_truncation_signal_is_inferred_and_empty_return_stays_distinct() -> None:
    conformant = evaluate(_artifacts())
    empty = evaluate(_artifacts(report=_report(pages=[_page(1, characters=0)])))

    assert conformant.state is GateState.PASS
    assert empty.state is GateState.FAIL
    assert any("empty" in error.lower() for error in empty.errors)
    assert all("truncat" not in error.lower() for error in empty.errors)


def test_explicit_known_truncation_is_fatal():
    _assert_fail(_artifacts(report=_report(pages=[_page(1, truncated=True)])), "truncat")


@pytest.mark.parametrize("value", [None, 0, "false"])
def test_missing_or_non_boolean_truncation_fails(value):
    page = _page(1)
    if value is None: del page["truncated"]
    else: page["truncated"] = value
    _assert_fail(_artifacts(report=_report(pages=[page])), "truncated")


def test_result_and_telemetry_are_ignored():
    report = _report(); report["result"] = {"quality_gate": "FAIL"}; report["telemetry"] = {"anything": object().__class__.__name__}
    assert evaluate(_artifacts(report=report)).state is GateState.PASS


def test_result_is_frozen_and_has_contract_shape() -> None:
    result = evaluate(_artifacts())
    assert isinstance(result, QualityGateResult)
    with pytest.raises(AttributeError):
        result.state = GateState.FAIL  # type: ignore[misc]
    assert set(vars(result)) == {"state", "warnings", "errors", "diagnostics"}
