"""Normative direct read-only filesystem fallback search."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from pipeline_juridico.config import RetrievalConfig

from .index import _write_atomic_json, enumerate_concepts
from .materializer import materialize


@dataclass(frozen=True)
class FallbackOutcome:
    results: tuple[Mapping[str, Any], ...]
    degraded: bool = True
    reason: str = "index_unavailable"


def _matches(value: Any, expected: Any, key: str) -> bool:
    if key == "tags":
        wanted = expected if isinstance(expected, (list, tuple)) else [expected]
        return isinstance(value, list) and all(item in value for item in wanted)
    return str(value) == str(expected)


def filesystem_search(bundle_root: Path, query: str, filters: Mapping[str, Any], limit: int, *, config: RetrievalConfig, reason: str = "index_unavailable") -> FallbackOutcome:
    terms = re.findall(r'"([^"]+)"|([^\s]+)', query)
    needles = [next(part for part in pair if part).casefold() for pair in terms]
    scored: list[tuple[int, str, Mapping[str, Any]]] = []
    for concept in enumerate_concepts(bundle_root):
        haystack = concept.body.casefold()
        if not all(needle in haystack for needle in needles):
            continue
        if not all(_matches(concept.metadata.get(key), value, key) for key, value in filters.items()):
            continue
        item = materialize(concept.concept_id, bundle_root, derived_root=config.derived_root).result
        scored.append((-sum(haystack.count(needle) for needle in needles), concept.concept_id, item))
    scored.sort(key=lambda item: (item[0], item[1]))
    _write_atomic_json(config.derived_root / "observability" / "last-search.json", {"degraded": True, "reason": reason, "result_count": min(len(scored), limit), "ranking_equivalent": False})
    return FallbackOutcome(tuple(item[2] for item in scored[:limit]), True, reason)
