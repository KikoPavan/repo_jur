"""Deterministic, read-only process review seam."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from .contracts import GateState, Phase1Artifacts, RouteTarget
from .domain_router import RoutingDecision


class ReviewState(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class ProcessPatch:
    before: str
    after: str
    reason: str
    confidence: float
    page_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessExtractedField:
    name: str
    value: str
    page_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProcessClassificationSuggestion:
    type: str | None
    basis: str
    confidence: float


@dataclass(frozen=True)
class ProcessReviewResult:
    state: ReviewState
    patches: tuple[ProcessPatch, ...]
    extracted_fields: tuple[ProcessExtractedField, ...]
    classification_suggestions: tuple[ProcessClassificationSuggestion, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ProcessReviewRule:
    rule_id: str
    rule_version: str
    scope: str
    source: str
    validation_logic_version: str
    evaluate: Callable[[str], list[ProcessPatch]]


@dataclass(frozen=True)
class ProcessReviewProfile:
    profile_id: str
    profile_version: str
    enabled_rule_ids: tuple[str, ...]


class ProcessSemanticReviewError(Exception):
    pass


class ProcessSemanticReviewConfigurationError(ProcessSemanticReviewError):
    pass


class ProcessSemanticReviewBlockedError(ProcessSemanticReviewError):
    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


_GATES = frozenset(item.value for item in GateState)


def _recorded_gate_outcome(report_json: str) -> GateState:
    if not isinstance(report_json, str):
        raise ProcessSemanticReviewBlockedError(
            "technical report must be serialized JSON", reason="invalid_report"
        )
    try:
        report: object = json.loads(report_json)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as error:
        raise ProcessSemanticReviewBlockedError(
            "technical report JSON is not parseable", reason="invalid_report"
        ) from error
    if not isinstance(report, dict) or not isinstance(report.get("result"), dict):
        raise ProcessSemanticReviewBlockedError(
            "technical report does not record a Quality Gate outcome",
            reason="invalid_report",
        )
    value = report["result"].get("quality_gate")
    if not isinstance(value, str) or value not in _GATES:
        raise ProcessSemanticReviewBlockedError(
            "technical report does not record a valid Quality Gate outcome",
            reason="invalid_report",
        )
    return GateState(value)


def _preserves_words(patch: ProcessPatch) -> bool:
    return Counter(patch.before.split()) == Counter(patch.after.split())


@dataclass(frozen=True, init=False)
class ProcessSemanticReviewEngine:
    _rules: Mapping[str, ProcessReviewRule]

    def __init__(self, rules: Iterable[ProcessReviewRule] = ()) -> None:
        registry: dict[str, ProcessReviewRule] = {}
        required = (
            "rule_id", "rule_version", "scope", "source",
            "validation_logic_version", "evaluate",
        )
        for rule in rules:
            if any(not getattr(rule, name, None) for name in required):
                raise ProcessSemanticReviewConfigurationError(
                    "review rule is missing required provenance"
                )
            if rule.rule_id in registry:
                raise ProcessSemanticReviewConfigurationError(
                    "review rule identifier is duplicated"
                )
            registry[rule.rule_id] = rule
        object.__setattr__(self, "_rules", MappingProxyType(registry))

    @property
    def rules(self) -> tuple[ProcessReviewRule, ...]:
        return tuple(self._rules.values())

    def review(
        self,
        phase1_artifacts: Phase1Artifacts,
        routing_decision: RoutingDecision,
        profile: ProcessReviewProfile,
    ) -> ProcessReviewResult:
        gate = _recorded_gate_outcome(phase1_artifacts.report_json)
        if gate is GateState.FAIL:
            raise ProcessSemanticReviewBlockedError(
                "recorded Quality Gate outcome stops review", reason="fail_gate"
            )
        if (
            not isinstance(routing_decision, RoutingDecision)
            or routing_decision.target is not RouteTarget.JUDICIAL_PROCESS
        ):
            raise ProcessSemanticReviewConfigurationError(
                "routing decision is not judicial_process"
            )
        if not isinstance(profile, ProcessReviewProfile):
            raise ProcessSemanticReviewConfigurationError(
                "review profile must be a ProcessReviewProfile"
            )
        if not profile.profile_id or not profile.profile_version:
            raise ProcessSemanticReviewConfigurationError(
                "review profile is missing required provenance"
            )
        if len(profile.enabled_rule_ids) != len(set(profile.enabled_rule_ids)):
            raise ProcessSemanticReviewConfigurationError(
                "review profile contains a duplicate rule identifier"
            )
        enabled: list[ProcessReviewRule] = []
        for rule_id in profile.enabled_rule_ids:
            try:
                enabled.append(self._rules[rule_id])
            except KeyError as error:
                raise ProcessSemanticReviewConfigurationError(
                    "profile references an unregistered rule"
                ) from error
        accepted: list[ProcessPatch] = []
        warnings: list[str] = []
        requires_review = False
        for rule in enabled:
            proposed = rule.evaluate(phase1_artifacts.markdown)
            if not isinstance(proposed, list) or any(
                not isinstance(patch, ProcessPatch) for patch in proposed
            ):
                raise ProcessSemanticReviewConfigurationError(
                    f"rule {rule.rule_id} returned an invalid result"
                )
            for patch in proposed:
                if not _preserves_words(patch):
                    requires_review = True
                    warnings.append(
                        f"rule {rule.rule_id} produced a non-structural patch"
                    )
                else:
                    accepted.append(patch)
        state = (
            ReviewState.REVIEW_REQUIRED if requires_review
            else ReviewState.WARNING if accepted else ReviewState.OK
        )
        return ProcessReviewResult(
            state, tuple(accepted), (), (), tuple(warnings)
        )
