"""Optional deterministic reranking seam, disabled and fail-open by default."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

RERANK_STATES = ("disabled", "bypassed", "applied", "failed_fallback")


class RerankingAdapter(Protocol):
    def reorder(
        self, query: str, candidates: tuple[str, ...], timeout_seconds: float
    ) -> Sequence[str]: ...


@dataclass(frozen=True)
class RerankingProfile:
    profile_version: str = "1"
    enabled: bool = False
    trigger_policy: str = "always"
    candidate_limit: int = 50
    timeout_seconds: float = 2.0
    implementation: str = "none"
    adapter: RerankingAdapter | None = None

    def __post_init__(self) -> None:
        if not self.profile_version:
            raise ValueError("reranking profile version is required")
        if self.trigger_policy not in {"always", "never", "multiple"}:
            raise ValueError("unsupported reranking trigger policy")
        if self.candidate_limit < 1 or self.timeout_seconds <= 0:
            raise ValueError("reranking execution bounds must be positive")


@dataclass(frozen=True)
class RerankingOutcome:
    candidates: tuple[str, ...]
    state: str


@dataclass(frozen=True)
class FakePriorityAdapter:
    """Deterministic experimental adapter used by tests only."""

    priority: tuple[str, ...]

    def reorder(
        self, query: str, candidates: tuple[str, ...], timeout_seconds: float
    ) -> tuple[str, ...]:
        preferred = [item for item in self.priority if item in candidates]
        return tuple((*preferred, *(item for item in candidates if item not in preferred)))


def should_rerank(
    query: str, candidates: Sequence[str], profile: RerankingProfile | None
) -> bool:
    effective = profile or RerankingProfile()
    if not effective.enabled or not query.strip():
        return False
    if effective.trigger_policy == "never":
        return False
    if effective.trigger_policy == "multiple":
        return len(candidates) > 1
    return bool(candidates)


def rerank(
    query: str,
    candidates: Sequence[str],
    profile: RerankingProfile | None = None,
) -> RerankingOutcome:
    effective = profile or RerankingProfile()
    original = tuple(candidates)
    if not effective.enabled:
        return RerankingOutcome(original, "disabled")
    if not should_rerank(query, original, effective):
        return RerankingOutcome(original, "bypassed")
    if effective.adapter is None:
        return RerankingOutcome(original, "failed_fallback")
    try:
        proposed = tuple(
            effective.adapter.reorder(
                query,
                original[: effective.candidate_limit],
                effective.timeout_seconds,
            )
        )
    except Exception:
        return RerankingOutcome(original, "failed_fallback")
    # A valid reranker changes order only: it may neither add nor remove evidence.
    if len(proposed) != len(original) or set(proposed) != set(original):
        return RerankingOutcome(original, "failed_fallback")
    return RerankingOutcome(proposed, "applied")
