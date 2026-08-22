from __future__ import annotations

import ast
import hashlib
import json
from dataclasses import fields
from pathlib import Path

import pytest

from pipeline_juridico.contracts import (
    CriticalValidationStatus,
    GateState,
    RouteTarget,
)
from pipeline_juridico.conversion_engine import Phase1Artifacts
from pipeline_juridico.domain_router import (
    RoutingBlockedError,
    RoutingConfigurationError,
    RoutingContext,
    RoutingDecision,
    RoutingReasonCode,
    build_routing_record,
    route,
    routing_state_filename,
    validate_routing_context,
)


def _page(number: int, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "page_number": number,
        "method": "texto_nativo",
        "char_count": 20,
        "warnings": [],
        "errors": [],
        "truncated": False,
    }
    payload.update(overrides)
    return payload


def _report(
    *,
    gate: str = "PASS",
    page_count: int = 1,
    execution_id: str | None = "00000000-0000-0000-0000-000000000001",
    sha256: str | None = "a" * 64,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "execution_id": execution_id,
        "input": {
            "byte_size": 1234,
            "sha256": sha256,
            "page_count": page_count,
        },
        "phase1": {},
        "artifacts": {"markdown_sha256": "b" * 64},
        "telemetry": {},
        "pages": [_page(number) for number in range(1, page_count + 1)],
        "result": {"quality_gate": gate, "warnings": [], "errors": []},
    }


def _artifacts(
    markdown: str = "[[Pág. 1]]\nConteúdo literal\n",
    report: dict[str, object] | None = None,
    report_json: str | None = None,
) -> Phase1Artifacts:
    serialized = json.dumps(
        _report() if report is None else report,
        ensure_ascii=False,
    )
    return Phase1Artifacts(
        markdown=markdown,
        report_json=serialized if report_json is None else report_json,
    )


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _context(
    requested_domain: RouteTarget | None = None,
) -> RoutingContext:
    return RoutingContext(requested_domain=requested_domain)


# ---------------------------------------------------------------------------
# 1.1 Input contract: conformant Phase 1 artifacts, no conversion path
# ---------------------------------------------------------------------------


def test_boundary_accepts_phase1_artifacts_without_conversion_path() -> None:
    decision = route(
        _artifacts(),
        critical_status=CriticalValidationStatus.OK,
        routing_context=None,
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED

    source = Path("src/pipeline_juridico/domain_router.py").read_text()
    for forbidden in (
        ".converter",
        ".engines",
        ".inspector",
        ".evidence",
        ".ocr",
        ".router",
    ):
        assert forbidden not in source

    tree = ast.parse(source)
    imported_modules = {
        alias.name.rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imported_modules & {
        "converter",
        "conversion_engine",
        "engines",
        "inspector",
        "evidence",
        "ocr",
        "router",
    }


# ---------------------------------------------------------------------------
# 1.2 Post-gate invariant: PASS / PASS_WITH_WARNINGS eligible; FAIL stops
# ---------------------------------------------------------------------------


def test_recorded_pass_gate_is_eligible_for_routing() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )

    assert decision.target is RouteTarget.LEGAL_KNOWLEDGE


def test_recorded_pass_with_warnings_gate_is_eligible_for_routing() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS_WITH_WARNINGS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.JUDICIAL_PROCESS),
    )

    assert decision.target is RouteTarget.JUDICIAL_PROCESS


def test_recorded_fail_gate_stops_routing_with_no_decision() -> None:
    with pytest.raises(RoutingBlockedError) as excinfo:
        route(
            _artifacts(report=_report(gate="FAIL")),
            critical_status=CriticalValidationStatus.OK,
            routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
        )

    assert excinfo.value.reason == "fail_gate"


def test_unparseable_report_blocks_routing() -> None:
    with pytest.raises(RoutingBlockedError) as excinfo:
        route(
            _artifacts(report_json="não é json"),
            critical_status=CriticalValidationStatus.OK,
            routing_context=None,
        )

    assert excinfo.value.reason == "invalid_report"


def test_missing_gate_outcome_blocks_routing() -> None:
    report = _report()
    report["result"] = {"warnings": [], "errors": []}

    with pytest.raises(RoutingBlockedError) as excinfo:
        route(
            _artifacts(report=report),
            critical_status=CriticalValidationStatus.OK,
            routing_context=None,
        )

    assert excinfo.value.reason == "invalid_report"


def test_gate_outcome_is_read_from_report_not_from_caller() -> None:
    # The entry point exposes no gate override; a FAIL recorded in the report
    # wins over any routing signal.
    with pytest.raises(RoutingBlockedError):
        route(
            _artifacts(report=_report(gate="FAIL")),
            critical_status=CriticalValidationStatus.OK,
            routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
        )


# ---------------------------------------------------------------------------
# 1.3 Critical-Data precedence: REVIEW_REQUIRED wins before any signal
# ---------------------------------------------------------------------------


def test_critical_review_required_routes_to_review_required_before_signal() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.REVIEW_REQUIRED,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED
    assert decision.reason is RoutingReasonCode.CRITICAL_REVIEW_REQUIRED


def test_critical_review_required_wins_over_judicial_process_signal() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS_WITH_WARNINGS")),
        critical_status=CriticalValidationStatus.REVIEW_REQUIRED,
        routing_context=_context(RouteTarget.JUDICIAL_PROCESS),
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED


def test_critical_ok_alone_never_selects_route() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=None,
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED
    assert decision.reason is RoutingReasonCode.MISSING_ROUTING_SIGNAL


def test_critical_warning_allows_signal_evaluation() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.WARNING,
        routing_context=_context(RouteTarget.JUDICIAL_PROCESS),
    )

    assert decision.target is RouteTarget.JUDICIAL_PROCESS


# ---------------------------------------------------------------------------
# 1.4 The approved initial routing signal: requested_domain
# ---------------------------------------------------------------------------


def test_requested_domain_legal_knowledge_selects_legal_knowledge() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )

    assert decision.target is RouteTarget.LEGAL_KNOWLEDGE
    assert decision.reason is RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE


def test_requested_domain_judicial_process_selects_judicial_process() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.JUDICIAL_PROCESS),
    )

    assert decision.target is RouteTarget.JUDICIAL_PROCESS
    assert decision.reason is RoutingReasonCode.REQUESTED_DOMAIN_JUDICIAL_PROCESS


def test_no_routing_context_yields_review_required() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=None,
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED
    assert decision.reason is RoutingReasonCode.MISSING_ROUTING_SIGNAL


def test_empty_routing_context_yields_review_required() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=validate_routing_context({}),
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED


def test_no_domain_is_selected_by_any_key_other_than_requested_domain() -> None:
    with pytest.raises(RoutingConfigurationError):
        validate_routing_context({"legal_hints": {"process_number": "x"}})
    with pytest.raises(RoutingConfigurationError):
        validate_routing_context({"domain_hint": "legal_knowledge"})


# ---------------------------------------------------------------------------
# 1.5 Approved fixed precedence (HR-2)
# ---------------------------------------------------------------------------


def test_precedence_fail_stops_before_any_signal() -> None:
    with pytest.raises(RoutingBlockedError):
        route(
            _artifacts(report=_report(gate="FAIL")),
            critical_status=CriticalValidationStatus.OK,
            routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
        )


def test_precedence_critical_review_required_precedes_signal() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.REVIEW_REQUIRED,
        routing_context=_context(RouteTarget.JUDICIAL_PROCESS),
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED
    assert decision.reason is RoutingReasonCode.CRITICAL_REVIEW_REQUIRED


def test_precedence_legal_knowledge_signal() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )

    assert decision.target is RouteTarget.LEGAL_KNOWLEDGE


def test_precedence_judicial_process_signal() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.JUDICIAL_PROCESS),
    )

    assert decision.target is RouteTarget.JUDICIAL_PROCESS


def test_precedence_absent_signal_routes_to_review_required() -> None:
    decision = route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=None,
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED


# ---------------------------------------------------------------------------
# 1.6 Configuration-error contract (HR-3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"legal_hints": {"process_number": "0001234-56.2020.8.26.0100"}},
        {"another_signal": "legal_knowledge"},
        {"requested_domain": "review_required"},
        {"requested_domain": "LEGAL_KNOWLEDGE"},
        {"requested_domain": "legal knowledge"},
        {"requested_domain": 123},
        {"requested_domain": None},
        {"requested_domain": ["legal_knowledge"]},
        {"requested_domain": {"value": "legal_knowledge"}},
        ["requested_domain"],
        "requested_domain",
        42,
        {1: "legal_knowledge", "requested_domain": "legal_knowledge"},
    ],
)
def test_configuration_error_contract_never_produces_a_decision(
    payload: object,
) -> None:
    with pytest.raises(RoutingConfigurationError):
        validate_routing_context(payload)  # type: ignore[arg-type]


def test_invalid_requested_domain_carrier_cannot_be_constructed() -> None:
    with pytest.raises(RoutingConfigurationError):
        RoutingContext(requested_domain=RouteTarget.REVIEW_REQUIRED)
    with pytest.raises(RoutingConfigurationError):
        RoutingContext(requested_domain="not-a-domain")
    with pytest.raises(RoutingConfigurationError):
        RoutingContext(requested_domain=42)  # type: ignore[arg-type]


def test_invalid_critical_status_is_a_configuration_error() -> None:
    with pytest.raises(RoutingConfigurationError):
        route(
            _artifacts(report=_report(gate="PASS")),
            critical_status="OK",  # type: ignore[arg-type]
            routing_context=None,
        )


def test_wrong_shape_context_passed_directly_is_a_configuration_error() -> None:
    with pytest.raises(RoutingConfigurationError):
        route(
            _artifacts(report=_report(gate="PASS")),
            critical_status=CriticalValidationStatus.OK,
            routing_context={"requested_domain": "legal_knowledge"},  # type: ignore[arg-type]
        )


def test_fail_gate_precedes_invalid_critical_status() -> None:
    with pytest.raises(RoutingBlockedError) as excinfo:
        route(
            _artifacts(report=_report(gate="FAIL")),
            critical_status="OK",  # type: ignore[arg-type]
            routing_context=None,
        )

    assert excinfo.value.reason == "fail_gate"


# ---------------------------------------------------------------------------
# 1.7 Determinism and idempotency
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("context", "expected_target"),
    [
        (None, RouteTarget.REVIEW_REQUIRED),
        (_context(RouteTarget.LEGAL_KNOWLEDGE), RouteTarget.LEGAL_KNOWLEDGE),
        (_context(RouteTarget.JUDICIAL_PROCESS), RouteTarget.JUDICIAL_PROCESS),
    ],
)
def test_repeated_evaluation_is_identical(
    context: RoutingContext | None,
    expected_target: RouteTarget,
) -> None:
    artifacts = _artifacts(report=_report(gate="PASS"))

    first = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=context,
    )
    second = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=context,
    )

    assert first == second
    assert first.target is expected_target
    assert first.reason == second.reason


def test_decision_carries_no_run_identity_or_timing() -> None:
    assert {field.name for field in fields(RoutingDecision)} == {
        "target",
        "reason",
    }


# ---------------------------------------------------------------------------
# 1.8 Non-mutation invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "context",
    [
        None,
        _context(RouteTarget.LEGAL_KNOWLEDGE),
        _context(RouteTarget.JUDICIAL_PROCESS),
    ],
)
def test_markdown_and_report_are_byte_identical_after_routing(
    context: RoutingContext | None,
) -> None:
    markdown = "[[Pág. 1]]\nConteúdo literal de teste\n"
    artifacts = _artifacts(
        markdown=markdown,
        report=_report(gate="PASS"),
    )
    markdown_before = _sha256(artifacts.markdown)
    report_before = artifacts.report_json

    decision = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=context,
    )

    assert _sha256(artifacts.markdown) == markdown_before
    assert artifacts.report_json == report_before
    assert decision.target is not None


def test_blocked_outcome_does_not_mutate_artifacts() -> None:
    markdown = "[[Pág. 1]]\nConteúdo literal de teste\n"
    artifacts = _artifacts(
        markdown=markdown,
        report=_report(gate="FAIL"),
    )
    markdown_before = _sha256(artifacts.markdown)
    report_before = artifacts.report_json

    with pytest.raises(RoutingBlockedError):
        route(
            artifacts,
            critical_status=CriticalValidationStatus.OK,
            routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
        )

    assert _sha256(artifacts.markdown) == markdown_before
    assert artifacts.report_json == report_before


# ---------------------------------------------------------------------------
# 1.9 The signal is never derived from document content
# ---------------------------------------------------------------------------

_KEYWORD_MARKDOWN = (
    "[[Pág. 1]]\n"
    "REsp 1.234.567 - STJ - jurisprudência consolidada - súmula vinculante\n"
    "[[Pág. 2]]\n"
    "Processo nº 0001234-56.2020.8.26.0100 - petição inicial - audiência\n"
)


def test_content_keywords_without_signal_yield_review_required() -> None:
    decision = route(
        _artifacts(
            markdown=_KEYWORD_MARKDOWN,
            report=_report(gate="PASS", page_count=2),
        ),
        critical_status=CriticalValidationStatus.OK,
        routing_context=None,
    )

    assert decision.target is RouteTarget.REVIEW_REQUIRED


def test_content_keywords_do_not_override_validated_signal() -> None:
    artifacts = _artifacts(
        markdown=_KEYWORD_MARKDOWN,
        report=_report(gate="PASS", page_count=2),
    )

    legal = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )
    judicial = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.JUDICIAL_PROCESS),
    )

    assert legal.target is RouteTarget.LEGAL_KNOWLEDGE
    assert judicial.target is RouteTarget.JUDICIAL_PROCESS


def test_mutating_only_markdown_body_never_changes_the_decision() -> None:
    report = _report(gate="PASS", page_count=2)

    first = route(
        _artifacts(markdown=_KEYWORD_MARKDOWN, report=report),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )
    second = route(
        _artifacts(markdown="[[Pág. 1]]\nConteúdo totalmente diferente\n", report=report),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )

    assert first == second
    assert second.target is RouteTarget.LEGAL_KNOWLEDGE


# ---------------------------------------------------------------------------
# 1.10 Domain-neutrality and independence source inspection
# ---------------------------------------------------------------------------


def test_router_source_has_no_prohibited_coupling_or_content_path() -> None:
    source = Path("src/pipeline_juridico/domain_router.py").read_text()

    for forbidden in (
        "llm",
        "classifier",
        "semantic",
        "enrich",
        "producer",
        "publish",
        "publication",
        "yaml",
        "guard_legal_bundle_write",
        "bundle",
        "markdown",
        "ocr",
        ".converter",
        ".engines",
        ".inspector",
        ".evidence",
        ".router",
        "open(",
        "write_atomic",
        "Path",
    ):
        assert forbidden not in source, f"prohibited token {forbidden!r} in source"


def test_router_source_reuses_the_shared_contracts() -> None:
    source = Path("src/pipeline_juridico/domain_router.py").read_text()

    assert "RouteTarget" in source
    assert "Phase1Artifacts" in source
    assert "CriticalValidationStatus" in source


# ---------------------------------------------------------------------------
# 1.11 The router never writes
# ---------------------------------------------------------------------------


def test_routing_performs_no_filesystem_write(tmp_path, monkeypatch) -> None:
    bundle_dir = tmp_path / "repo_jur" / "bundle"
    process_dir = tmp_path / "process-storage"
    bundle_dir.mkdir(parents=True)
    process_dir.mkdir()
    monkeypatch.chdir(tmp_path)

    route(
        _artifacts(report=_report(gate="PASS")),
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )

    assert list(bundle_dir.rglob("*")) == []
    assert list(process_dir.rglob("*")) == []


def test_router_source_performs_no_io_at_all() -> None:
    source = Path("src/pipeline_juridico/domain_router.py").read_text()

    assert "write_atomic" not in source
    assert "open(" not in source
    assert "Path" not in source


# ---------------------------------------------------------------------------
# 1.12 Exact route-target outcomes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("gate", "critical", "context", "expected_value"),
    [
        ("PASS", "OK", RouteTarget.LEGAL_KNOWLEDGE, "legal_knowledge"),
        ("PASS_WITH_WARNINGS", "WARNING", RouteTarget.JUDICIAL_PROCESS, "judicial_process"),
        ("PASS", "REVIEW_REQUIRED", RouteTarget.LEGAL_KNOWLEDGE, "review_required"),
        ("PASS", "OK", None, "review_required"),
    ],
)
def test_every_decision_serializes_to_a_canonical_route_target(
    gate: str,
    critical: str,
    context: RouteTarget | None,
    expected_value: str,
) -> None:
    decision = route(
        _artifacts(report=_report(gate=gate)),
        critical_status=CriticalValidationStatus(critical),
        routing_context=_context(context) if context is not None else None,
    )

    assert isinstance(decision.target, RouteTarget)
    assert decision.target.value in {
        target.value for target in RouteTarget
    }
    assert decision.target.value == expected_value


# ---------------------------------------------------------------------------
# 1.13 Decision envelope and reason-code vocabulary
# ---------------------------------------------------------------------------


def test_reason_code_vocabulary_is_fixed() -> None:
    assert [code.value for code in RoutingReasonCode] == [
        "critical_review_required",
        "requested_domain_legal_knowledge",
        "requested_domain_judicial_process",
        "missing_routing_signal",
        "signal_conflict",
    ]


@pytest.mark.parametrize(
    ("gate", "critical", "context", "expected_reason"),
    [
        ("PASS", "REVIEW_REQUIRED", None, "critical_review_required"),
        ("PASS", "OK", RouteTarget.LEGAL_KNOWLEDGE, "requested_domain_legal_knowledge"),
        ("PASS", "OK", RouteTarget.JUDICIAL_PROCESS, "requested_domain_judicial_process"),
        ("PASS", "OK", None, "missing_routing_signal"),
    ],
)
def test_reason_code_is_derived_solely_from_inputs(
    gate: str,
    critical: str,
    context: RouteTarget | None,
    expected_reason: str,
) -> None:
    decision = route(
        _artifacts(report=_report(gate=gate)),
        critical_status=CriticalValidationStatus(critical),
        routing_context=_context(context) if context is not None else None,
    )

    assert decision.reason.value == expected_reason


# ---------------------------------------------------------------------------
# 1.14 Observability-record safety and location
# ---------------------------------------------------------------------------


def _routed_record(
    *,
    gate: str = "PASS",
    critical: str = "OK",
    context: RoutingContext | None = None,
    report: dict[str, object] | None = None,
    recorded_at: str | None = None,
) -> tuple[dict[str, object], Phase1Artifacts]:
    artifacts = _artifacts(
        report=_report(gate=gate) if report is None else report,
    )
    decision = route(
        artifacts,
        critical_status=CriticalValidationStatus(critical),
        routing_context=context,
    )
    record = build_routing_record(
        phase1_artifacts=artifacts,
        critical_status=CriticalValidationStatus(critical),
        routing_context=context,
        decision=decision,
        recorded_at=recorded_at,
    )
    return record, artifacts


def test_record_carries_provenance_hash_gate_critical_and_decision() -> None:
    record, artifacts = _routed_record(
        gate="PASS",
        critical="OK",
        context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )

    report = json.loads(artifacts.report_json)
    assert record["schema_version"] == "1.0"
    assert record["record_type"] == "routing"
    assert record["provenance_sha256"] == report["input"]["sha256"]
    assert record["gate"] == "PASS"
    assert record["critical_status"] == "OK"
    assert record["decision"] == "legal_knowledge"
    assert record["reason"] == "requested_domain_legal_knowledge"
    assert record["execution_id"] == report["execution_id"]


def test_record_rejects_a_non_sha256_provenance_value() -> None:
    with pytest.raises(RoutingBlockedError) as excinfo:
        build_routing_record(
            phase1_artifacts=_artifacts(report=_report(sha256="not-a-sha256")),
            critical_status=CriticalValidationStatus.OK,
            routing_context=None,
            decision=RoutingDecision(
                RouteTarget.REVIEW_REQUIRED,
                RoutingReasonCode.MISSING_ROUTING_SIGNAL,
            ),
        )

    assert excinfo.value.reason == "invalid_report"


def test_record_records_signal_keys_only_never_values() -> None:
    present, _artifacts_present = _routed_record(
        context=_context(RouteTarget.JUDICIAL_PROCESS),
    )
    absent, _artifacts_absent = _routed_record(context=None)

    assert present["routing_context_keys"] == ["requested_domain"]
    assert absent["routing_context_keys"] == []
    serialized = json.dumps(present, ensure_ascii=False)
    # the signal key appears only as presence inside routing_context_keys;
    # no field stores the requested_domain value as a signal-value pair
    assert '"requested_domain": "legal_knowledge"' not in serialized
    assert '"requested_domain": "judicial_process"' not in serialized


def test_record_omits_execution_id_when_absent_from_report() -> None:
    report = _report(gate="PASS")
    report["execution_id"] = ""

    record, _artifacts = _routed_record(report=report)

    assert "execution_id" not in record


def test_record_omits_recorded_at_when_not_supplied() -> None:
    record, _artifacts = _routed_record()

    assert "recorded_at" not in record


def test_record_includes_recorded_at_when_supplied() -> None:
    record, _artifacts = _routed_record(recorded_at="2026-08-22T12:00:00+00:00")

    assert record["recorded_at"] == "2026-08-22T12:00:00+00:00"


def test_record_never_contains_document_content() -> None:
    secret_content = "CONTEUDO-CONFIDENCIAL-DO-PROCESSO-789"
    artifacts = _artifacts(
        markdown=f"[[Pág. 1]]\n{secret_content}\n",
        report=_report(gate="PASS"),
    )
    decision = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
    )
    record = build_routing_record(
        phase1_artifacts=artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=_context(RouteTarget.LEGAL_KNOWLEDGE),
        decision=decision,
    )

    serialized = json.dumps(record, ensure_ascii=False)
    assert secret_content not in serialized


def test_record_never_contains_full_critical_identifier_values() -> None:
    cnj_value = "0001234-56.2020.8.26.0100"
    artifacts = _artifacts(
        markdown=f"[[Pág. 1]]\nProcesso {cnj_value}\n",
        report=_report(gate="PASS"),
    )
    decision = route(
        artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=None,
    )
    record = build_routing_record(
        phase1_artifacts=artifacts,
        critical_status=CriticalValidationStatus.OK,
        routing_context=None,
        decision=decision,
    )

    serialized = json.dumps(record, ensure_ascii=False)
    assert cnj_value not in serialized


def test_record_builder_is_pure_and_requires_no_filesystem() -> None:
    record, _artifacts = _routed_record()

    assert isinstance(record, dict)
    assert set(record) >= {
        "schema_version",
        "record_type",
        "provenance_sha256",
        "gate",
        "critical_status",
        "routing_context_keys",
        "decision",
        "reason",
    }


def test_state_filename_is_deterministic_and_derived_from_execution_id() -> None:
    artifacts = _artifacts(report=_report(execution_id="exec-12345"))

    assert routing_state_filename(artifacts) == "exec-12345.json"
    assert routing_state_filename(artifacts) == routing_state_filename(artifacts)


def test_state_filename_differs_for_different_execution_ids() -> None:
    first = _artifacts(report=_report(execution_id="exec-aaa"))
    second = _artifacts(report=_report(execution_id="exec-bbb"))

    assert routing_state_filename(first) != routing_state_filename(second)


def test_state_filename_falls_back_to_provenance_hash_without_execution_id() -> None:
    artifacts = _artifacts(report=_report(execution_id=""))

    assert routing_state_filename(artifacts) == ("a" * 64) + ".json"


def test_state_filename_sanitizes_execution_id_path_separators() -> None:
    artifacts = _artifacts(report=_report(execution_id="../../etc/passwd"))

    filename = routing_state_filename(artifacts)

    assert filename == ".._.._etc_passwd.json"
    assert "/" not in filename
