"""Shared, domain-independent contracts and filesystem guards."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import re


# Structural rule only: a component is any non-empty run of characters that
# does not contain the Actor grammar's structural separators (``:`` for the
# principal kind, ``/`` for the producer/version form).  No character whitelist
# is imposed: accents, symbols, and other identifier characters are accepted.
_COMPONENT = r"[^:/]+"
_PRINCIPAL_ACTOR_PATTERN = re.compile(
    rf"(?P<kind>human|process):(?P<identifier>{_COMPONENT})\Z"
)
_PRODUCER_ACTOR_PATTERN = re.compile(
    rf"(?P<identifier>{_COMPONENT})/(?P<version>{_COMPONENT})\Z"
)


@dataclass(frozen=True)
class Actor:
    """A validated Actor reference."""

    value: str
    kind: str
    identifier: str
    version: str | None = None


def parse_actor(value: str) -> Actor:
    """Parse a canonical Actor reference or raise ``ValueError``."""

    if not isinstance(value, str):
        raise ValueError("Actor reference must be a string")

    principal_match = _PRINCIPAL_ACTOR_PATTERN.fullmatch(value)
    if principal_match is not None:
        return Actor(
            value=value,
            kind=principal_match.group("kind"),
            identifier=principal_match.group("identifier"),
        )

    producer_match = _PRODUCER_ACTOR_PATTERN.fullmatch(value)
    if producer_match is not None:
        return Actor(
            value=value,
            kind="producer",
            identifier=producer_match.group("identifier"),
            version=producer_match.group("version"),
        )

    raise ValueError(
        "Actor reference must use human:<id>, process:<id>, or <producer>/<version>"
    )


def validate_actor(value: str) -> Actor:
    """Validate and return a canonical Actor reference."""

    return parse_actor(value)


def resolve_safe_path(allowed_root: str | Path, reference: str | Path) -> Path:
    """Resolve a relative reference while ensuring it remains under a root."""

    relative_path = Path(reference)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise ValueError("reference must be a safe relative path")

    root = Path(allowed_root).resolve()
    candidate = (root / relative_path).resolve()
    if not candidate.is_relative_to(root):
        raise ValueError("resolved reference escapes the allowed root")
    return candidate


class GateState(str, Enum):
    PASS = "PASS"
    PASS_WITH_WARNINGS = "PASS_WITH_WARNINGS"
    FAIL = "FAIL"


class CriticalValidationStatus(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class CriticalFinding:
    code: str
    message: str
    evidence_reference: str | None = None


@dataclass
class CriticalValidationResult:
    status: CriticalValidationStatus
    findings: list[CriticalFinding] = field(default_factory=list)


class RouteTarget(str, Enum):
    LEGAL_KNOWLEDGE = "legal_knowledge"
    JUDICIAL_PROCESS = "judicial_process"
    REVIEW_REQUIRED = "review_required"


def guard_legal_bundle_write(
    *,
    acting_domain: RouteTarget,
    target: str | Path,
    legal_bundle_root: str | Path,
) -> Path:
    """Authorize a target while reserving the Legal bundle for its domain."""

    resolved_target = Path(target).resolve()
    resolved_bundle = Path(legal_bundle_root).resolve()
    targets_bundle = resolved_target == resolved_bundle or resolved_target.is_relative_to(
        resolved_bundle
    )
    if targets_bundle and acting_domain != RouteTarget.LEGAL_KNOWLEDGE:
        raise PermissionError(
            "Only the legal_knowledge domain may write to the Legal bundle"
        )
    return resolved_target
