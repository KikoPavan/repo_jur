"""Deterministic derived chunking of canonical Legal Knowledge bodies."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from hashlib import sha256

from .index import CanonicalConcept

CHUNKER_LOGICAL_VERSION = "1"
_PAGE = re.compile(r"\[\[Pág\.\s*(\d+)\]\]")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ChunkingProfile:
    profile_version: str = "1"
    measurement_unit: str = "characters"
    soft_limit: int = 6000
    hard_limit: int = 12000
    forced_split_overlap: int = 200

    def __post_init__(self) -> None:
        if self.measurement_unit != "characters":
            raise ValueError("measurement_unit must be characters")
        if self.soft_limit <= 0 or self.hard_limit <= self.soft_limit:
            raise ValueError("chunk limits require hard_limit > soft_limit > 0")
        if self.forced_split_overlap < 0 or self.forced_split_overlap >= self.hard_limit:
            raise ValueError("forced_split_overlap must be non-negative and below hard_limit")

    def config_fingerprint(self) -> str:
        payload = {
            "profile_version": self.profile_version,
            "measurement_unit": self.measurement_unit,
            "soft_limit": self.soft_limit,
            "hard_limit": self.hard_limit,
            "forced_split_overlap": self.forced_split_overlap,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Chunk:
    chunk_ordinal: int
    body_range: tuple[int, int]
    text_content: str
    page_refs: tuple[int, ...]
    section_path: tuple[str, ...]
    table_header_context: tuple[str, ...]


@dataclass(frozen=True)
class ChunkSet:
    concept_id: str
    chunks: tuple[Chunk, ...]
    chunk_set_fingerprint: str


def _structural_units(body: str) -> list[tuple[int, int]]:
    """Return lossless block spans, keeping separators with the preceding block."""
    if not body:
        return []
    spans: list[tuple[int, int]] = []
    start = 0
    in_fence = False
    offset = 0
    lines = body.splitlines(keepends=True)
    for line in lines:
        offset += len(line)
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not in_fence and line.strip() == "":
            spans.append((start, offset)); start = offset
    if start < len(body):
        spans.append((start, len(body)))
    return spans


def _split_unit(start: int, end: int, hard_limit: int, overlap: int) -> list[tuple[int, int]]:
    step = hard_limit - overlap
    spans: list[tuple[int, int]] = []
    position = start
    while position < end:
        piece_end = min(position + hard_limit, end)
        spans.append((position, piece_end))
        if piece_end == end:
            break
        position += step
    return spans


def _page_refs(body: str, start: int, end: int) -> tuple[int, ...]:
    markers = [(match.start(), int(match.group(1))) for match in _PAGE.finditer(body)]
    pages: list[int] = []
    prior = [page for position, page in markers if position < start]
    if prior:
        pages.append(prior[-1])
    for position, page in markers:
        if start <= position < end and page not in pages:
            pages.append(page)
    return tuple(pages)


def _context(body: str, start: int, end: int) -> tuple[tuple[str, ...], tuple[str, ...]]:
    headings: list[tuple[int, int, str]] = []
    for match in _HEADING.finditer(body, 0, end):
        headings.append((match.start(), len(match.group(1)), match.group(2)))
    path: list[str] = []
    for _, level, title in headings:
        path = path[: level - 1]
        path.append(title)
    table_headers: tuple[str, ...] = ()
    text = body[start:end]
    lines = text.splitlines()
    for index in range(len(lines) - 1):
        if lines[index].lstrip().startswith("|") and re.match(r"^\s*\|?\s*:?-+", lines[index + 1]):
            table_headers = tuple(cell.strip() for cell in lines[index].strip("|").split("|"))
            break
    return tuple(path), table_headers


def chunk_concept(
    concept: CanonicalConcept,
    profile: ChunkingProfile | None = None,
    *,
    chunker_logical_version: str = CHUNKER_LOGICAL_VERSION,
) -> ChunkSet:
    profile = profile or ChunkingProfile()
    body = concept.body
    atomic: list[tuple[int, int]] = []
    for start, end in _structural_units(body):
        atomic.extend(
            _split_unit(start, end, profile.hard_limit, profile.forced_split_overlap)
            if end - start > profile.hard_limit
            else [(start, end)]
        )
    grouped: list[tuple[int, int]] = []
    for start, end in atomic:
        if not grouped:
            grouped.append((start, end))
        elif grouped[-1][1] - grouped[-1][0] < profile.soft_limit and end - grouped[-1][0] <= profile.hard_limit:
            grouped[-1] = (grouped[-1][0], end)
        else:
            grouped.append((start, end))
    chunks: list[Chunk] = []
    for ordinal, (start, end) in enumerate(grouped):
        section_path, table_context = _context(body, start, end)
        chunks.append(Chunk(ordinal, (start, end), body[start:end], _page_refs(body, start, end), section_path, table_context))
    fingerprint_payload = {
        "concept_id": concept.concept_id,
        "body_sha256": sha256(body.encode("utf-8")).hexdigest(),
        "profile_version": profile.profile_version,
        "profile_config_fingerprint": profile.config_fingerprint(),
        "chunker_logical_version": chunker_logical_version,
    }
    fingerprint = sha256(json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ChunkSet(concept.concept_id, tuple(chunks), fingerprint)
