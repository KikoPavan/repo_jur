from __future__ import annotations

from dataclasses import replace

import pytest

from pipeline_juridico.retrieval.chunking import ChunkingProfile, chunk_concept
from pipeline_juridico.retrieval.index import CanonicalConcept


def _concept(body: str, concept_id: str = "legislacao/codigo") -> CanonicalConcept:
    return CanonicalConcept(concept_id, __import__("pathlib").Path("unused.md"), {"type": "legislacao"}, body)


def _assert_literal_coverage(body: str, result: object) -> None:
    covered_until = 0
    for chunk in result.chunks:
        start, end = chunk.body_range
        assert start <= covered_until
        assert end > covered_until
        assert chunk.text_content == body[start:end]
        covered_until = end
    assert covered_until == len(body)


def test_profile_defaults_validation_and_fingerprint() -> None:
    profile = ChunkingProfile()
    assert (profile.measurement_unit, profile.soft_limit, profile.hard_limit, profile.forced_split_overlap) == ("characters", 6000, 12000, 200)
    assert profile.config_fingerprint() == ChunkingProfile().config_fingerprint()
    with pytest.raises(ValueError):
        ChunkingProfile(soft_limit=0)
    with pytest.raises(ValueError):
        ChunkingProfile(soft_limit=10, hard_limit=10)
    with pytest.raises(ValueError):
        ChunkingProfile(measurement_unit="tokens")
    with pytest.raises(ValueError):
        ChunkingProfile(forced_split_overlap=-1)
    with pytest.raises(ValueError):
        ChunkingProfile(forced_split_overlap=12000)


def test_structural_chunks_are_literal_lossless_and_context_is_separate() -> None:
    body = "# Titulo\n\nParagrafo um.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n> Citacao\n"
    result = chunk_concept(_concept(body), ChunkingProfile(soft_limit=18, hard_limit=45, forced_split_overlap=5))
    _assert_literal_coverage(body, result)
    assert [chunk.chunk_ordinal for chunk in result.chunks] == list(range(len(result.chunks)))
    assert [chunk.body_range for chunk in result.chunks] == [(sum(len(c.text_content) for c in result.chunks[:i]), sum(len(c.text_content) for c in result.chunks[: i + 1])) for i in range(len(result.chunks))]
    assert any(chunk.section_path == ("Titulo",) for chunk in result.chunks)
    assert any(chunk.table_header_context for chunk in result.chunks)
    assert sum(chunk.text_content.count("# Titulo") for chunk in result.chunks) == 1
    assert sum(chunk.text_content.count("| A | B |") for chunk in result.chunks) == 1


def test_page_refs_and_forced_split_are_deterministic_and_lossless() -> None:
    body = "antes\n\n[[Pág. 7]]\n" + ("x" * 31) + "\n[[Pág. 8]]\nfim\n"
    profile = ChunkingProfile(soft_limit=10, hard_limit=20, forced_split_overlap=4)
    first = chunk_concept(_concept(body), profile)
    second = chunk_concept(_concept(body), profile)
    assert first == second
    _assert_literal_coverage(body, first)
    overlaps = [
        left.body_range[1] - right.body_range[0]
        for left, right in zip(first.chunks, first.chunks[1:])
        if right.body_range[0] < left.body_range[1]
    ]
    assert overlaps and all(value == profile.forced_split_overlap for value in overlaps)
    assert first.chunks[0].page_refs == ()
    assert 7 in {page for chunk in first.chunks for page in chunk.page_refs}
    assert 8 in {page for chunk in first.chunks for page in chunk.page_refs}
    assert all(len(chunk.text_content) <= profile.hard_limit for chunk in first.chunks)


def test_forced_split_overlap_is_effective_literal_bounded_and_configurable() -> None:
    body = "0123456789" * 5
    overlapping = ChunkingProfile(soft_limit=10, hard_limit=20, forced_split_overlap=4)
    result = chunk_concept(_concept(body), overlapping)

    assert [chunk.body_range for chunk in result.chunks] == [(0, 20), (16, 36), (32, 50)]
    assert all(
        left.body_range[1] - right.body_range[0] == overlapping.forced_split_overlap
        for left, right in zip(result.chunks, result.chunks[1:])
    )
    assert all(len(chunk.text_content) <= overlapping.hard_limit for chunk in result.chunks)
    _assert_literal_coverage(body, result)

    zero_overlap = replace(overlapping, forced_split_overlap=0)
    zero_result = chunk_concept(_concept(body), zero_overlap)
    assert [chunk.body_range for chunk in zero_result.chunks] == [(0, 20), (20, 40), (40, 50)]
    assert "".join(chunk.text_content for chunk in zero_result.chunks) == body
    assert zero_result.chunk_set_fingerprint != result.chunk_set_fingerprint


def test_forced_split_page_refs_cover_the_effectively_duplicated_span() -> None:
    body = ("a" * 17) + "[[Pág. 9]]" + ("b" * 20)
    profile = ChunkingProfile(soft_limit=10, hard_limit=20, forced_split_overlap=4)

    result = chunk_concept(_concept(body), profile)

    assert result.chunks[0].body_range == (0, 20)
    assert result.chunks[1].body_range == (16, 36)
    assert result.chunks[0].page_refs == (9,)
    assert result.chunks[1].page_refs == (9,)
    _assert_literal_coverage(body, result)


def test_chunk_set_fingerprint_invalidates_on_all_inputs() -> None:
    base = _concept("corpo\n")
    profile = ChunkingProfile()
    fingerprint = chunk_concept(base, profile).chunk_set_fingerprint
    variants = [
        chunk_concept(_concept("mudou\n"), profile).chunk_set_fingerprint,
        chunk_concept(_concept("corpo\n", "legislacao/outro"), profile).chunk_set_fingerprint,
        chunk_concept(base, replace(profile, profile_version="2")).chunk_set_fingerprint,
        chunk_concept(base, replace(profile, soft_limit=5999)).chunk_set_fingerprint,
        chunk_concept(base, replace(profile, forced_split_overlap=199)).chunk_set_fingerprint,
        chunk_concept(base, profile, chunker_logical_version="future").chunk_set_fingerprint,
    ]
    assert all(value != fingerprint for value in variants)
    assert not hasattr(first_chunk := chunk_concept(base, profile).chunks[0], "chunk_id")
    assert first_chunk.text_content == "corpo\n"
