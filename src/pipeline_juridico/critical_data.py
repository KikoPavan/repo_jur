from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from .contracts import (
    CriticalFinding,
    CriticalValidationResult,
    CriticalValidationStatus,
)
from .conversion_engine import Phase1Artifacts


class CriticalValidationConfigurationError(Exception):
    """The validation rule registry or profile cannot be resolved."""


@dataclass(frozen=True)
class CriticalValidationRule:
    rule_id: str
    rule_version: str
    applies_to: str
    source: str
    validation_logic_version: str
    failure_status: CriticalValidationStatus
    evaluate: Callable[[Phase1Artifacts], list[CriticalFinding]]


@dataclass(frozen=True)
class CriticalValidationProfile:
    profile_id: str
    profile_version: str
    enabled_rule_ids: tuple[str, ...]


@dataclass(frozen=True, init=False)
class CriticalDataValidator:
    _rules: Mapping[str, CriticalValidationRule]

    def __init__(self, rules: Iterable[CriticalValidationRule] = ()) -> None:
        registry: dict[str, CriticalValidationRule] = {}
        required_fields = (
            "rule_id",
            "rule_version",
            "applies_to",
            "source",
            "validation_logic_version",
            "failure_status",
        )
        for rule in rules:
            if any(not getattr(rule, field_name, None) for field_name in required_fields):
                raise CriticalValidationConfigurationError(
                    "validation rule is missing required provenance"
                )
            if rule.failure_status is not CriticalValidationStatus.WARNING and (
                rule.failure_status is not CriticalValidationStatus.REVIEW_REQUIRED
            ):
                raise CriticalValidationConfigurationError(
                    "validation rule has an invalid failure status"
                )
            if rule.rule_id in registry:
                raise CriticalValidationConfigurationError(
                    "validation rule identifier is duplicated"
                )
            registry[rule.rule_id] = rule

        object.__setattr__(self, "_rules", MappingProxyType(registry))

    def validate(
        self,
        phase1_artifacts: Phase1Artifacts,
        profile: CriticalValidationProfile,
    ) -> CriticalValidationResult:
        if len(profile.enabled_rule_ids) != len(set(profile.enabled_rule_ids)):
            raise CriticalValidationConfigurationError(
                "validation profile contains a duplicate rule identifier"
            )

        enabled_rules: list[CriticalValidationRule] = []
        for rule_id in profile.enabled_rule_ids:
            try:
                enabled_rules.append(self._rules[rule_id])
            except KeyError as error:
                raise CriticalValidationConfigurationError(
                    "validation profile references an unregistered rule"
                ) from error

        findings: list[CriticalFinding] = []
        status = CriticalValidationStatus.OK
        for rule in enabled_rules:
            rule_findings = rule.evaluate(phase1_artifacts)
            findings.extend(rule_findings)
            if rule_findings:
                if rule.failure_status is CriticalValidationStatus.REVIEW_REQUIRED:
                    status = CriticalValidationStatus.REVIEW_REQUIRED
                elif status is CriticalValidationStatus.OK:
                    status = CriticalValidationStatus.WARNING

        return CriticalValidationResult(status=status, findings=findings)
