"""Deterministic post-Quality-Gate domain routing seam (Stage 6)."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from .contracts import (
    CriticalValidationStatus,
    GateState,
    Phase1Artifacts,
    RouteTarget,
)


class RoutingConfigurationError(Exception):
    """A routing context (or routing input) violates its fixed contract."""


class RoutingBlockedError(Exception):
    """Deterministic 'stop': routing produces no decision for this execution."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        # "fail_gate": recorded gate outcome is FAIL; routing stops.
        # "invalid_report": the technical report cannot be routed.
        self.reason = reason


class RoutingReasonCode(str, Enum):
    """Fixed vocabulary of deterministic routing reason codes."""

    CRITICAL_REVIEW_REQUIRED = "critical_review_required"
    REQUESTED_DOMAIN_LEGAL_KNOWLEDGE = "requested_domain_legal_knowledge"
    REQUESTED_DOMAIN_JUDICIAL_PROCESS = "requested_domain_judicial_process"
    MISSING_ROUTING_SIGNAL = "missing_routing_signal"
    SIGNAL_CONFLICT = "signal_conflict"


@dataclass(frozen=True)
class RoutingDecision:
    """The deterministic decision envelope produced for the three route targets."""

    target: RouteTarget
    reason: RoutingReasonCode


_PERMITTED_SIGNAL_KEYS = frozenset({"requested_domain"})
_DOMAIN_SIGNAL_TARGETS = frozenset(
    {RouteTarget.LEGAL_KNOWLEDGE, RouteTarget.JUDICIAL_PROCESS}
)
_GATE_VOCABULARY = frozenset(state.value for state in GateState)
_RECORD_SCHEMA_VERSION = "1.0"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class RoutingContext:
    """A validated routing context carrying the single permitted signal."""

    requested_domain: RouteTarget | None = None

    def __post_init__(self) -> None:
        value = self.requested_domain
        if value is None:
            return
        if isinstance(value, str):
            try:
                value = RouteTarget(value)
            except ValueError as exc:
                raise RoutingConfigurationError(
                    "requested_domain must be legal_knowledge or judicial_process"
                ) from exc
        if value not in _DOMAIN_SIGNAL_TARGETS:
            raise RoutingConfigurationError(
                "requested_domain must be legal_knowledge or judicial_process"
            )
        object.__setattr__(self, "requested_domain", value)

    @property
    def signal_keys(self) -> tuple[str, ...]:
        """Presence of permitted signal keys; never signal values."""
        return ("requested_domain",) if self.requested_domain is not None else ()


def validate_routing_context(
    payload: Mapping[str, object] | None,
) -> RoutingContext:
    """Validate a routing-context carrier against the fixed signal vocabulary.

    Raises ``RoutingConfigurationError`` for any key outside the vocabulary,
    for an invalid ``requested_domain`` value, and for structurally invalid
    payloads. ``None`` and an empty mapping both produce an absent signal.
    """
    if payload is None:
        return RoutingContext()
    if not isinstance(payload, Mapping):
        raise RoutingConfigurationError(
            "routing context must be a mapping of signal keys"
        )
    unknown_keys = sorted(
        (key for key in payload if key not in _PERMITTED_SIGNAL_KEYS),
        key=repr,
    )
    if unknown_keys:
        raise RoutingConfigurationError(
            "unrecognized routing context signal key(s): "
            + ", ".join(repr(key) for key in unknown_keys)
        )
    if "requested_domain" not in payload:
        return RoutingContext()
    requested = payload["requested_domain"]
    if not isinstance(requested, str):
        raise RoutingConfigurationError(
            "requested_domain must be one of the permitted values"
        )
    try:
        domain = RouteTarget(requested)
    except ValueError as exc:
        raise RoutingConfigurationError(
            "requested_domain has an invalid value"
        ) from exc
    if domain is RouteTarget.REVIEW_REQUIRED:
        raise RoutingConfigurationError(
            "requested_domain must be legal_knowledge or judicial_process"
        )
    return RoutingContext(requested_domain=domain)


def _parse_report(report_json: str) -> dict:
    if not isinstance(report_json, str):
        raise RoutingBlockedError(
            "technical report must be a serialized JSON string",
            reason="invalid_report",
        )
    try:
        parsed: object = json.loads(report_json)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as exc:
        raise RoutingBlockedError(
            "technical report JSON is not parseable",
            reason="invalid_report",
        ) from exc
    if not isinstance(parsed, dict):
        raise RoutingBlockedError(
            "technical report root must be an object",
            reason="invalid_report",
        )
    return parsed


def _recorded_gate_outcome(report_json: str) -> GateState:
    """Read the recorded Quality Gate outcome from the technical report."""
    report = _parse_report(report_json)
    result = report.get("result")
    if not isinstance(result, dict):
        raise RoutingBlockedError(
            "technical report does not record a Quality Gate outcome",
            reason="invalid_report",
        )
    gate_value = result.get("quality_gate")
    if not isinstance(gate_value, str) or gate_value not in _GATE_VOCABULARY:
        raise RoutingBlockedError(
            "technical report does not record a valid Quality Gate outcome",
            reason="invalid_report",
        )
    return GateState(gate_value)


def _report_input_hash(report: dict) -> str:
    input_info = report.get("input")
    if not isinstance(input_info, dict):
        raise RoutingBlockedError(
            "technical report input must be an object",
            reason="invalid_report",
        )
    sha256_value = input_info.get("sha256")
    if (
        not isinstance(sha256_value, str)
        or _SHA256_PATTERN.match(sha256_value) is None
    ):
        raise RoutingBlockedError(
            "technical report input.sha256 must be a lowercase SHA-256 value",
            reason="invalid_report",
        )
    return sha256_value


def route(
    phase1_artifacts: Phase1Artifacts,
    *,
    critical_status: CriticalValidationStatus,
    routing_context: RoutingContext | None = None,
) -> RoutingDecision:
    """Decide the route target from the recorded gate, critical status, and
    validated routing context.

    Precedence: (1) recorded gate ``FAIL`` stops routing; (2) critical status
    ``REVIEW_REQUIRED`` routes to ``review_required`` before any signal; (3)
    ``requested_domain == legal_knowledge``; (4) ``requested_domain ==
    judicial_process``; (5) ``requested_domain`` absent routes to
    ``review_required``. The literal Phase 1 content is never inspected.
    """
    gate = _recorded_gate_outcome(phase1_artifacts.report_json)
    if gate is GateState.FAIL:
        raise RoutingBlockedError(
            "recorded Quality Gate outcome is FAIL: routing stops",
            reason="fail_gate",
        )
    if not isinstance(critical_status, CriticalValidationStatus):
        raise RoutingConfigurationError(
            "critical status must be a CriticalValidationStatus value"
        )
    if critical_status is CriticalValidationStatus.REVIEW_REQUIRED:
        return RoutingDecision(
            RouteTarget.REVIEW_REQUIRED,
            RoutingReasonCode.CRITICAL_REVIEW_REQUIRED,
        )
    if routing_context is not None:
        if not isinstance(routing_context, RoutingContext):
            raise RoutingConfigurationError(
                "routing context must be a validated RoutingContext"
            )
        if routing_context.requested_domain is RouteTarget.LEGAL_KNOWLEDGE:
            return RoutingDecision(
                RouteTarget.LEGAL_KNOWLEDGE,
                RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE,
            )
        if routing_context.requested_domain is RouteTarget.JUDICIAL_PROCESS:
            return RoutingDecision(
                RouteTarget.JUDICIAL_PROCESS,
                RoutingReasonCode.REQUESTED_DOMAIN_JUDICIAL_PROCESS,
            )
        if routing_context.requested_domain is not None:
            raise RoutingConfigurationError(
                "routing context carries an invalid requested_domain"
            )
    return RoutingDecision(
        RouteTarget.REVIEW_REQUIRED,
        RoutingReasonCode.MISSING_ROUTING_SIGNAL,
    )


def build_routing_record(
    *,
    phase1_artifacts: Phase1Artifacts,
    critical_status: CriticalValidationStatus,
    routing_context: RoutingContext | None,
    decision: RoutingDecision,
    recorded_at: str | None = None,
) -> dict[str, object]:
    """Assemble the content-safe routing observability payload (no I/O).

    The payload records provenance, the gate outcome, the critical status,
    routing-signal presence (keys only), the decision, and the reason code.
    It never carries document content, full critical identifier values, or
    routing-signal values.
    """
    report = _parse_report(phase1_artifacts.report_json)
    record: dict[str, object] = {
        "schema_version": _RECORD_SCHEMA_VERSION,
        "record_type": "routing",
        "provenance_sha256": _report_input_hash(report),
        "gate": _recorded_gate_outcome(phase1_artifacts.report_json).value,
        "critical_status": critical_status.value,
        "routing_context_keys": (
            list(routing_context.signal_keys)
            if routing_context is not None
            else []
        ),
        "decision": decision.target.value,
        "reason": decision.reason.value,
    }
    execution_id = report.get("execution_id")
    if isinstance(execution_id, str) and execution_id:
        record["execution_id"] = execution_id
    if recorded_at is not None:
        record["recorded_at"] = recorded_at
    return record


def _safe_filename_stem(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)


def routing_state_filename(phase1_artifacts: Phase1Artifacts) -> str:
    """Deterministic record filename derived from the Phase 1 report.

    Uses the report execution id when present, falling back to the report
    provenance hash. The stem is sanitized so the derived name cannot escape
    the configured state directory.
    """
    report = _parse_report(phase1_artifacts.report_json)
    execution_id = report.get("execution_id")
    if isinstance(execution_id, str) and execution_id:
        stem = _safe_filename_stem(execution_id)
    else:
        stem = _report_input_hash(report)
    return f"{stem}.json"
