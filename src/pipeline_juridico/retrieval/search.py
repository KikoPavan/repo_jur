"""Legal Knowledge lexical search with canonical materialization and fallback."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pipeline_juridico.config import RetrievalConfig

from .fallback import filesystem_search
from .index import SqliteFts5Index, enumerate_concepts
from .materializer import MaterializationError, materialize
from .reranking import RerankingProfile, rerank


class FilterConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class SearchOutcome:
    results: tuple[Mapping[str, Any], ...]
    degraded: bool
    reason: str | None
    rerank_state: str = "disabled"


@dataclass(frozen=True)
class SearchDiagnosis:
    outcome: SearchOutcome
    candidate_discovery: Mapping[str, Any]
    filter_application: Mapping[str, Any]
    materialization: Mapping[str, Any]
    fallback: Mapping[str, Any]
    reranking: str


def validate_filters(filters: Mapping[str, Any] | None, config: RetrievalConfig) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in (filters or {}).items():
        if key not in config.filter_vocabulary:
            raise FilterConfigurationError(f"unknown retrieval filter: {key}")
        normalized[config.public_to_canonical_field.get(key, key)] = value
    return normalized


def _validated_limit(limit: int | None, config: RetrievalConfig) -> int:
    value = config.search_default_limit if limit is None else limit
    if value < 1 or value > config.search_max_limit:
        raise FilterConfigurationError("search limit outside validated range")
    return value


def search(bundle_root: Path, derived_root: Path, query: str, filters: Mapping[str, Any] | None = None, limit: int | None = None, *, config: RetrievalConfig | None = None, reranking_profile: RerankingProfile | None = None) -> SearchOutcome:
    config = config or RetrievalConfig(derived_root=derived_root)
    normalized = validate_filters(filters, config)
    bounded = _validated_limit(limit, config)
    concepts = enumerate_concepts(bundle_root)
    backend = SqliteFts5Index(bundle_root, config)
    try:
        state = backend.state(concepts, config)
        if state.status != "fresh":
            fallback = filesystem_search(bundle_root, query, normalized, bounded, config=config, reason=state.reason)
            outcome = SearchOutcome(fallback.results, True, fallback.reason)
            _record_query(config, outcome, len(fallback.results), normalized)
            return outcome
        candidate_ids = backend.search(query, normalized, bounded)
    except Exception as error:
        fallback = filesystem_search(bundle_root, query, normalized, bounded, config=config, reason=f"index_initialization_failed:{type(error).__name__}")
        outcome = SearchOutcome(fallback.results, True, fallback.reason)
        _record_query(config, outcome, len(fallback.results), normalized)
        return outcome
    reranked = rerank(query, candidate_ids, reranking_profile)
    results: list[Mapping[str, Any]] = []
    missing = False
    for concept_id in reranked.candidates:
        try:
            results.append(materialize(concept_id, bundle_root, derived_root=config.derived_root).result)
        except MaterializationError:
            missing = True
    outcome = SearchOutcome(tuple(results), missing, "materialization_missing" if missing else None, reranked.state)
    _record_query(config, outcome, len(candidate_ids), normalized)
    return outcome


def _record_query(config: RetrievalConfig, outcome: SearchOutcome, candidate_count: int, filters: Mapping[str, Any]) -> None:
    from .index import _write_atomic_json

    _write_atomic_json(
        config.derived_root / "observability" / "last-query.json",
        {
            "candidate_count": candidate_count,
            "filter_keys": sorted(filters),
            "result_count": len(outcome.results),
            "degraded": outcome.degraded,
            "reason": outcome.reason,
            "reranking": outcome.rerank_state,
        },
    )


def search_diagnose(bundle_root: Path, derived_root: Path, query: str, filters: Mapping[str, Any] | None = None, limit: int | None = None, *, config: RetrievalConfig | None = None, reranking_profile: RerankingProfile | None = None) -> SearchDiagnosis:
    outcome = search(bundle_root, derived_root, query, filters, limit, config=config, reranking_profile=reranking_profile)
    return SearchDiagnosis(outcome, {"result_count": len(outcome.results), "state": "degraded" if outcome.degraded else "fresh"}, {"keys": sorted((filters or {}).keys()), "state": "applied"}, {"missing": int(outcome.reason == "materialization_missing"), "state": "completed"}, {"used": outcome.degraded, "reason": outcome.reason}, outcome.rerank_state)
