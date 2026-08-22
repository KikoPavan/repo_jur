"""Deterministic, read-only Legal Semantic Review seam."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from .contracts import GateState, Phase1Artifacts


class ReviewState(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class LegalPatch:
    before: str
    after: str
    reason: str
    confidence: float
    page_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: str
    page_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClassificationSuggestion:
    type: str | None
    basis: str
    confidence: float


@dataclass(frozen=True)
class ReviewResult:
    state: ReviewState
    patches: tuple[LegalPatch, ...]
    extracted_fields: tuple[ExtractedField, ...]
    classification_suggestions: tuple[ClassificationSuggestion, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class LegalReviewRule:
    rule_id: str
    rule_version: str
    scope: str
    source: str
    validation_logic_version: str
    evaluate: Callable[[str], list[LegalPatch]]


@dataclass(frozen=True)
class LegalReviewProfile:
    profile_id: str
    profile_version: str
    enabled_rule_ids: tuple[str, ...]


class LegalSemanticReviewError(Exception):
    """Base error for the review boundary."""


class LegalSemanticReviewConfigurationError(LegalSemanticReviewError):
    """The rule registry or selected profile is invalid."""


class LegalSemanticReviewBlockedError(LegalSemanticReviewError):
    """The recorded technical outcome deterministically stops review."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


_GATE_VOCABULARY = frozenset(state.value for state in GateState)
_ELIGIBLE_GATES = frozenset(
    {GateState.PASS, GateState.PASS_WITH_WARNINGS}
)


def _recorded_gate_outcome(report_json: str) -> GateState:
    if not isinstance(report_json, str):
        raise LegalSemanticReviewBlockedError(
            "technical report must be serialized JSON",
            reason="invalid_report",
        )
    try:
        report: object = json.loads(report_json)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as error:
        raise LegalSemanticReviewBlockedError(
            "technical report JSON is not parseable",
            reason="invalid_report",
        ) from error
    if not isinstance(report, dict):
        raise LegalSemanticReviewBlockedError(
            "technical report root must be an object",
            reason="invalid_report",
        )
    result = report.get("result")
    if not isinstance(result, dict):
        raise LegalSemanticReviewBlockedError(
            "technical report does not record a Quality Gate outcome",
            reason="invalid_report",
        )
    value = result.get("quality_gate")
    if not isinstance(value, str) or value not in _GATE_VOCABULARY:
        raise LegalSemanticReviewBlockedError(
            "technical report does not record a valid Quality Gate outcome",
            reason="invalid_report",
        )
    return GateState(value)


def _preserves_words(patch: LegalPatch) -> bool:
    return Counter(patch.before.split()) == Counter(patch.after.split())


@dataclass(frozen=True, init=False)
class LegalSemanticReviewEngine:
    _rules: Mapping[str, LegalReviewRule]

    def __init__(self, rules: Iterable[LegalReviewRule] = ()) -> None:
        registry: dict[str, LegalReviewRule] = {}
        required_fields = (
            "rule_id",
            "rule_version",
            "scope",
            "source",
            "validation_logic_version",
            "evaluate",
        )
        for rule in rules:
            if any(
                not getattr(rule, field_name, None)
                for field_name in required_fields
            ):
                raise LegalSemanticReviewConfigurationError(
                    "review rule is missing required provenance"
                )
            if rule.rule_id in registry:
                raise LegalSemanticReviewConfigurationError(
                    "review rule identifier is duplicated"
                )
            registry[rule.rule_id] = rule
        object.__setattr__(self, "_rules", MappingProxyType(registry))

    def review(
        self,
        phase1_artifacts: Phase1Artifacts,
        profile: LegalReviewProfile,
    ) -> ReviewResult:
        gate = _recorded_gate_outcome(phase1_artifacts.report_json)
        if gate not in _ELIGIBLE_GATES:
            raise LegalSemanticReviewBlockedError(
                "recorded Quality Gate outcome stops review",
                reason="fail_gate",
            )
        if not isinstance(profile, LegalReviewProfile):
            raise LegalSemanticReviewConfigurationError(
                "review profile must be a LegalReviewProfile"
            )
        if not profile.profile_id or not profile.profile_version:
            raise LegalSemanticReviewConfigurationError(
                "review profile is missing required provenance"
            )
        if len(profile.enabled_rule_ids) != len(set(profile.enabled_rule_ids)):
            raise LegalSemanticReviewConfigurationError(
                "review profile contains a duplicate rule identifier"
            )

        enabled: list[LegalReviewRule] = []
        for rule_id in profile.enabled_rule_ids:
            try:
                enabled.append(self._rules[rule_id])
            except KeyError as error:
                raise LegalSemanticReviewConfigurationError(
                    "review profile references an unregistered rule"
                ) from error

        accepted: list[LegalPatch] = []
        warnings: list[str] = []
        requires_review = False
        for rule in enabled:
            proposed = rule.evaluate(phase1_artifacts.markdown)
            if not isinstance(proposed, list) or any(
                not isinstance(patch, LegalPatch) for patch in proposed
            ):
                raise LegalSemanticReviewConfigurationError(
                    f"review rule {rule.rule_id} returned an invalid result"
                )
            for patch in proposed:
                if not _preserves_words(patch):
                    requires_review = True
                    warnings.append(
                        f"rule {rule.rule_id} produced a non-structural patch"
                    )
                    continue
                accepted.append(patch)

        if requires_review:
            state = ReviewState.REVIEW_REQUIRED
        elif accepted:
            state = ReviewState.WARNING
        else:
            state = ReviewState.OK
        return ReviewResult(
            state=state,
            patches=tuple(accepted),
            extracted_fields=(),
            classification_suggestions=(),
            warnings=tuple(warnings),
        )
