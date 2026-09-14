"""Deterministic structural segmentation of literal Phase 1 Markdown."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from enum import Enum


class SegmentationOutcome(str, Enum):
    SINGLE = "single"
    SEGMENTS = "segments"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class BoundaryMatch:
    start: int
    label: str


@dataclass(frozen=True)
class Segment:
    segment_id: str
    source_unit_label: str
    body: str
    page_start: int
    page_end: int
    boundary_rule_id: str | None


@dataclass(frozen=True)
class SegmentationResult:
    outcome: SegmentationOutcome
    segments: tuple[Segment, ...]
    ambiguity_reason: str | None


@dataclass(frozen=True)
class SegmentationRule:
    rule_id: str
    rule_version: str
    scope: str
    source: str
    validation_logic_version: str
    detect: Callable[[str], list[BoundaryMatch]]
    detect_trailer: Callable[[str, int], int | None] | None = None


class SegmentationRuleRegistry:
    def __init__(self, rules: Iterable[SegmentationRule] = ()) -> None:
        registered = tuple(rules)
        for rule in registered:
            provenance = (
                rule.rule_id,
                rule.rule_version,
                rule.scope,
                rule.source,
                rule.validation_logic_version,
            )
            if not all(isinstance(value, str) and value.strip() for value in provenance):
                raise ValueError("segmentation rule provenance is required")
            if not callable(rule.detect):
                raise ValueError("segmentation rule detector is required")
        identifiers = [rule.rule_id for rule in registered]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("segmentation rule identifiers must be unique")
        self.rules = registered


_PAGE = re.compile(r"\[\[Pág\.\s*(\d+)\]\]")
_EDITION = re.compile(
    r"^Edição n\. \d+ Brasília, \d{1,2} de [^\W\d_]+ de \d{4}\s*$",
    re.MULTILINE | re.UNICODE,
)
PRECEDENT_HEADER_PATTERN = re.compile(
    r"^Tema Repetitivo (\d+)(?: {2}| \ue205 )Situação "
    r"([^\s\ue205](?:[^\r\n\ue205]*?[^\s\ue205])?)(?: {2}| )"
    r"Órgão (\S(?:[^\r\n]*\S)?)$",
    re.MULTILINE,
)
_PRECEDENT_TRAILER_PATTERN = re.compile(
    r"^Exportar todos Imprimir todos Imprimir selecionados\s*\r?\n"
    r"\s*Esta pesquisa recupera informações inseridas pelo NUGEPNAC "
    r"[^\r\n]*Secretaria de Jurisprudência do STJ\. Versão "
    r"\d+(?:\.\d+){3} \| de \d{2}/\d{2}/\d{4} \d{2}:\d{2}\.\s*$",
    re.MULTILINE,
)


def _regex_detector(pattern: re.Pattern[str]) -> Callable[[str], list[BoundaryMatch]]:
    def detect(markdown: str) -> list[BoundaryMatch]:
        return [BoundaryMatch(match.start(), match.group(0).rstrip()) for match in pattern.finditer(markdown)]

    return detect


def _precedent_trailer_start(markdown: str, after: int) -> int | None:
    """Return the unique structural trailer start after the final record, if present."""
    matches = [match for match in _PRECEDENT_TRAILER_PATTERN.finditer(markdown) if match.start() > after]
    if len(matches) != 1:
        return None
    return matches[0].start()


DEFAULT_SEGMENTATION_REGISTRY = SegmentationRuleRegistry((
    SegmentationRule(
        "jurisprudencia-em-teses-edicao-v1",
        "1.0",
        "STJ Jurisprudência em Teses once-per-edition dated heading",
        "multi-concept-legal-source-segmentation/design.md Decision 2",
        "1.0",
        _regex_detector(_EDITION),
    ),
    SegmentationRule(
        "precedentes-qualificados-tema-repetitivo-v1",
        "1.0",
        "STJ Precedentes Qualificados fixed three-field record header",
        "multi-concept-legal-source-segmentation/design.md Decision 2",
        "1.0",
        _regex_detector(PRECEDENT_HEADER_PATTERN),
        _precedent_trailer_start,
    ),
))


def _page_range(body: str) -> tuple[int, int] | None:
    pages = [int(match.group(1)) for match in _PAGE.finditer(body)]
    if not pages:
        return None
    if pages != sorted(pages):
        return None
    return pages[0], pages[-1]


def _single(markdown: str) -> SegmentationResult:
    pages = _page_range(markdown)
    page_start, page_end = pages if pages is not None else (1, 1)
    return SegmentationResult(
        SegmentationOutcome.SINGLE,
        (Segment("segment-0001", "", markdown, page_start, page_end, None),),
        None,
    )


def segment_markdown(markdown: str, registry: SegmentationRuleRegistry) -> SegmentationResult:
    """Return a pure, position-derived segmentation of ``markdown``."""
    detected = [(rule, tuple(rule.detect(markdown))) for rule in registry.rules]
    active = [(rule, matches) for rule, matches in detected if matches]
    if len(active) > 1:
        ids = ",".join(rule.rule_id for rule, _ in active)
        return SegmentationResult(
            SegmentationOutcome.AMBIGUOUS, (), f"conflicting_boundary_rules:{ids}"
        )
    if not active or len(active[0][1]) < 2:
        return _single(markdown)

    rule, matches = active[0]
    page_map = [(match.start(), int(match.group(1))) for match in _PAGE.finditer(markdown)]
    if any(
        current_page < previous_page
        for (_, previous_page), (_, current_page) in zip(page_map, page_map[1:])
    ):
        return SegmentationResult(
            SegmentationOutcome.AMBIGUOUS, (), "non_monotonic_page_markers"
        )

    def page_at(position: int) -> int | None:
        for offset, page in reversed(page_map):
            if offset <= position:
                return page
        return None

    starts = [match.start for match in matches]
    if starts != sorted(starts) or len(starts) != len(set(starts)):
        return SegmentationResult(SegmentationOutcome.AMBIGUOUS, (), "non_monotonic_boundaries")

    segments: list[Segment] = []
    for index, match in enumerate(matches):
        if index + 1 < len(matches):
            end = matches[index + 1].start
        else:
            trailer_start = rule.detect_trailer(markdown, match.start) if rule.detect_trailer else None
            end = trailer_start if trailer_start is not None else len(markdown)
        body = markdown[match.start:end]
        page_start = page_at(match.start)
        if page_start is None:
            return SegmentationResult(
                SegmentationOutcome.AMBIGUOUS, (), "unresolved_page_context"
            )
        page_end = page_at(end - 1)
        assert page_end is not None
        segments.append(Segment(
            f"segment-{index + 1:04d}",
            match.label,
            body,
            page_start,
            page_end,
            rule.rule_id,
        ))
    return SegmentationResult(SegmentationOutcome.SEGMENTS, tuple(segments), None)
