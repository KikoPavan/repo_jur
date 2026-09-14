from __future__ import annotations

import hashlib
from pathlib import Path

import pipeline_juridico.legal_segment_identity as identity_module
import pipeline_juridico.legal_source_segmentation as segmentation_module
from pipeline_juridico.legal_source_segmentation import (
    DEFAULT_SEGMENTATION_REGISTRY,
    BoundaryMatch,
    Segment,
    SegmentationOutcome,
    SegmentationRule,
    SegmentationRuleRegistry,
    segment_markdown,
)
from pipeline_juridico.legal_segment_identity import IdentityStatus, resolve_segment_identity


def _edition(number: int, page: int, text: str) -> str:
    return (
        f"[[Pág. {page}]]\n"
        f"Edição n. {number} Brasília, {page} de junho de 2021\n"
        f"EDIÇÃO N. {number}: TITLE\n{text}\n"
    )


def _precedent(number: int, page: int, text: str) -> str:
    return (
        f"[[Pág. {page}]]\n"
        f"Tema Repetitivo {number}  Situação Afetado  Órgão Primeira Seção\n"
        f"{text}\n"
    )


def _precedent_pua(number: int, page: int, text: str) -> str:
    return (
        f"[[Pág. {page}]]\n"
        f"Tema Repetitivo {number} \ue205 Situação Afetado Órgão Primeira Seção\n"
        f"Registro relativo ao Tema {number}/STJ.\n{text}\n"
    )


def test_no_boundary_is_single_and_preserves_body() -> None:
    markdown = "[[Pág. 1]]\nAcórdão mono-conceito\nTema n. 12 citado em prosa.\n"
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert result.outcome is SegmentationOutcome.SINGLE
    assert len(result.segments) == 1
    assert result.segments[0].body == markdown
    assert result.segments[0].boundary_rule_id is None


def test_edition_boundaries_split_without_leakage_and_with_page_ranges() -> None:
    markdown = _edition(171, 1, "somente primeira") + _edition(172, 3, "somente segunda")
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [item.segment_id for item in result.segments] == ["segment-0001", "segment-0002"]
    assert [(item.page_start, item.page_end) for item in result.segments] == [(1, 3), (3, 3)]
    assert "somente segunda" not in result.segments[0].body
    assert "somente primeira" not in result.segments[1].body


def test_precedent_fixed_headers_split() -> None:
    result = segment_markdown(
        _precedent(692, 4, "primeiro") + _precedent(1016, 7, "segundo"),
        DEFAULT_SEGMENTATION_REGISTRY,
    )
    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [segment.source_unit_label for segment in result.segments] == [
        "Tema Repetitivo 692  Situação Afetado  Órgão Primeira Seção",
        "Tema Repetitivo 1016  Situação Afetado  Órgão Primeira Seção",
    ]


def test_internal_citations_and_running_headers_are_not_boundaries() -> None:
    citation = "[[Pág. 1]]\nA Edição n. 172 cita Tema n. 11 em prosa.\n"
    assert segment_markdown(citation, DEFAULT_SEGMENTATION_REGISTRY).outcome is SegmentationOutcome.SINGLE

    markdown = (
        _edition(171, 1, "primeira página")
        + "EDIÇÃO N. 171: TITLE\n[[Pág. 2]]\ncontinuação\n"
        + _edition(172, 3, "outra unidade")
    )
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert len(result.segments) == 2
    assert result.segments[0].page_end == 3


def test_two_rules_matching_once_are_ambiguous_and_name_both_rules() -> None:
    markdown = _edition(171, 1, "texto") + _precedent(692, 2, "texto")
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert result.outcome is SegmentationOutcome.AMBIGUOUS
    assert result.segments == ()
    assert "jurisprudencia-em-teses-edicao-v1" in (result.ambiguity_reason or "")
    assert "precedentes-qualificados-tema-repetitivo-v1" in (result.ambiguity_reason or "")


def test_boundary_before_first_page_marker_has_unresolved_page_context() -> None:
    markdown = (
        "Edição n. 171 Brasília, 1 de junho de 2021\nsem marcador\n"
        + _edition(172, 2, "com marcador")
    )
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert result.outcome is SegmentationOutcome.AMBIGUOUS
    assert result.segments == ()
    assert result.ambiguity_reason == "unresolved_page_context"


def test_determinism_and_input_hash_immutability() -> None:
    markdown = _edition(171, 1, "um") + _edition(172, 2, "dois")
    before = hashlib.sha256(markdown.encode()).hexdigest()
    first = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    second = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert first == second
    assert hashlib.sha256(markdown.encode()).hexdigest() == before


def test_registry_rejects_missing_provenance() -> None:
    rule = SegmentationRule("", "1", "scope", "source", "logic", lambda _: [])
    try:
        SegmentationRuleRegistry((rule,))
    except ValueError as error:
        assert "provenance" in str(error)
    else:
        raise AssertionError("missing provenance accepted")


def test_custom_boundary_match_contract() -> None:
    def detect(markdown: str) -> list[BoundaryMatch]:
        return [BoundaryMatch(0, "Header")]

    registry = SegmentationRuleRegistry((SegmentationRule("r", "1", "s", "x", "1", detect),))
    assert segment_markdown("[[Pág. 1]]\nbody", registry).outcome is SegmentationOutcome.SINGLE


def _precedent_segment(body: str, *, label: str = "Tema Repetitivo 692") -> Segment:
    return Segment(
        "segment-0001", label, body, 1, 1,
        "precedentes-qualificados-tema-repetitivo-v1",
    )


def test_precedent_identity_comes_from_own_fixed_header_not_internal_citation() -> None:
    body = (
        "Tema Repetitivo 692  Situação Afetado  Órgão Primeira Seção\n"
        "[[Pág. 1]]\nA revisão é relativa ao Tema 692/STJ.\n"
        "A tese menciona Tema em IRDR n. 11/TJSP e Tema Repetitivo 731 em prosa.\n"
    )
    identity = resolve_segment_identity("PrecedenteVinculante", _precedent_segment(body))
    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_precedente_numero"] == "692"
    assert identity.fields["repo_jur_tribunal"] == "STJ"
    assert "11" not in identity.fields.values()


def test_editorial_edition_is_never_resolved_as_tema_juridico() -> None:
    for citations in ("", "Tema n. 11", "Tema n. 11 e Tema n. 22"):
        segment = Segment(
            "segment-0042",
            "Edição n. 171 Brasília, 4 de junho de 2021",
            f"Edição n. 171 Brasília, 4 de junho de 2021\n[[Pág. 1]]\n{citations}\n",
            1, 1,
            "jurisprudencia-em-teses-edicao-v1",
        )
        identity = resolve_segment_identity("TemaJuridico", segment)
        assert identity.status is IdentityStatus.REQUIRES_OPERATOR_METADATA
        assert identity.fields == {}
        assert "jurisprudencia_em_teses_edicao_not_valid_temajuridico" in (identity.reason or "")


def test_conflicting_singular_identity_is_ambiguous() -> None:
    body = (
        "Tema Repetitivo 692  Situação Afetado  Órgão Primeira Seção\n"
        "Tema Repetitivo 693  Situação Afetado  Órgão Primeira Seção\n"
        "[[Pág. 1]]\nSuperior Tribunal de Justiça\n"
    )
    identity = resolve_segment_identity("PrecedenteVinculante", _precedent_segment(body))
    assert identity.status is IdentityStatus.AMBIGUOUS
    assert identity.fields == {}


def test_operational_segment_metadata_never_becomes_identity() -> None:
    body = (
        "Tema Repetitivo 692  Situação Afetado  Órgão Primeira Seção\n"
        "[[Pág. 1]]\nRegistro relativo ao Tema 692/STJ.\n"
    )
    segment = _precedent_segment(body, label="segment-0001 Tema Repetitivo 692")
    identity = resolve_segment_identity("PrecedenteVinculante", segment)
    assert identity.status is IdentityStatus.RESOLVED
    assert "segment_id" not in identity.fields
    assert "source_unit_label" not in identity.fields
    assert segment.segment_id not in identity.fields.values()
    assert segment.source_unit_label not in identity.fields.values()


def test_precedent_u_e205_complete_headers_are_recognized() -> None:
    markdown = _precedent_pua(692, 4, "primeiro") + _precedent_pua(1016, 7, "segundo")
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [segment.source_unit_label for segment in result.segments] == [
        "Tema Repetitivo 692 \ue205 Situação Afetado Órgão Primeira Seção",
        "Tema Repetitivo 1016 \ue205 Situação Afetado Órgão Primeira Seção",
    ]


def test_precedent_two_ascii_space_headers_remain_recognized() -> None:
    result = segment_markdown(
        _precedent(692, 4, "primeiro") + _precedent(1016, 7, "segundo"),
        DEFAULT_SEGMENTATION_REGISTRY,
    )
    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert len(result.segments) == 2


def test_two_u_e205_headers_split_without_leakage_and_preserve_page_ranges() -> None:
    markdown = (
        _precedent_pua(692, 4, "conteúdo exclusivo 692\n[[Pág. 5]]\ncontinuação 692")
        + _precedent_pua(1016, 7, "conteúdo exclusivo 1016\n[[Pág. 9]]\ncontinuação 1016")
    )
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert len(result.segments) == 2
    assert [(segment.page_start, segment.page_end) for segment in result.segments] == [(4, 7), (7, 9)]
    assert "conteúdo exclusivo 1016" not in result.segments[0].body
    assert "conteúdo exclusivo 692" not in result.segments[1].body
    assert "[[Pág. 4]]" not in result.segments[0].body
    assert "[[Pág. 9]]" in result.segments[1].body


def test_u_e205_and_internal_citations_without_full_header_are_not_boundaries() -> None:
    cases = (
        "[[Pág. 1]]\nA prosa contém \ue205 como glifo isolado.\n",
        "[[Pág. 1]]\nA tese cita Tema Repetitivo 731 em prosa.\n",
        "[[Pág. 1]]\nA tese cita Tema Repetitivo 731\ue205 em prosa.\n",
    )
    for markdown in cases:
        result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
        assert result.outcome is SegmentationOutcome.SINGLE
        assert result.segments[0].body == markdown


def test_incomplete_precedent_headers_do_not_split() -> None:
    incomplete_headers = (
        "Tema Repetitivo 692 Situação Afetado Órgão Primeira Seção",
        "Tema Repetitivo 692 \ue205 Situação Afetado Primeira Seção",
        "Tema Repetitivo 692 \ue205 Afetado Órgão Primeira Seção",
        "Tema Repetitivo 692  Afetado  Órgão Primeira Seção",
    )
    for header in incomplete_headers:
        markdown = f"{header}\n[[Pág. 1]]\ncorpo\n{header}\n[[Pág. 2]]\ncorpo\n"
        result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
        assert result.outcome is SegmentationOutcome.SINGLE
        assert result.segments[0].body == markdown


def test_old_symmetric_u_e205_separator_forms_do_not_split() -> None:
    rejected_headers = (
        "Tema Repetitivo 692\ue205Situação Afetado\ue205Órgão Primeira Seção",
        "Tema Repetitivo 692 \ue205 Situação Afetado \ue205 Órgão Primeira Seção",
        "Tema Repetitivo 692\ue205\ue205Situação Afetado\ue205\ue205Órgão Primeira Seção",
    )
    for header in rejected_headers:
        markdown = f"{header}\n[[Pág. 1]]\ncorpo\n{header}\n[[Pág. 2]]\ncorpo\n"
        result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
        assert result.outcome is SegmentationOutcome.SINGLE
        assert result.segments[0].body == markdown


def test_u_e205_segment_operational_metadata_never_becomes_identity() -> None:
    result = segment_markdown(
        _precedent_pua(692, 4, "Cita internamente o Tema Repetitivo 731 em contexto diverso.")
        + _precedent_pua(1016, 7, "outro segmento"),
        DEFAULT_SEGMENTATION_REGISTRY,
    )
    segment = result.segments[0]
    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert "segment_id" not in identity.fields
    assert "source_unit_label" not in identity.fields
    assert segment.segment_id not in identity.fields.values()
    assert segment.source_unit_label not in identity.fields.values()


def _page_map_header(number: int) -> str:
    return f"Tema Repetitivo {number}  Situação Afetado  Órgão Primeira Seção\n"


def test_page_map_two_segments_share_one_page() -> None:
    markdown = (
        "[[Pág. 4]]\n"
        + _page_map_header(978)
        + "Registro relativo ao Tema 978/STJ.\nprimeiro\n"
        + _page_map_header(999)
        + "Registro relativo ao Tema 999/STJ.\nsegundo\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [(segment.page_start, segment.page_end) for segment in result.segments] == [(4, 4), (4, 4)]


def test_page_map_three_segments_share_one_page() -> None:
    markdown = "[[Pág. 4]]\n" + "".join(
        _page_map_header(number) + f"conteúdo {number}\n" for number in (692, 731, 954)
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [(segment.page_start, segment.page_end) for segment in result.segments] == [
        (4, 4),
        (4, 4),
        (4, 4),
    ]


def test_page_map_mixed_shared_and_distinct_pages() -> None:
    markdown = (
        "[[Pág. 4]]\n"
        + _page_map_header(692)
        + "primeiro\n"
        + _page_map_header(731)
        + "segundo\n[[Pág. 5]]\n"
        + _page_map_header(954)
        + "terceiro\n"
    )

    third_marker = markdown.index("[[Pág. 5]]")

    def detect(_: str) -> list[BoundaryMatch]:
        return [
            BoundaryMatch(markdown.index(_page_map_header(692)), _page_map_header(692).rstrip()),
            BoundaryMatch(markdown.index(_page_map_header(731)), _page_map_header(731).rstrip()),
            BoundaryMatch(third_marker, _page_map_header(954).rstrip()),
        ]

    registry = SegmentationRuleRegistry((SegmentationRule("page-map-test", "1", "test", "test", "1", detect),))
    result = segment_markdown(markdown, registry)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [(segment.page_start, segment.page_end) for segment in result.segments] == [
        (4, 4),
        (4, 4),
        (5, 5),
    ]


def test_page_map_segment_can_cross_pages() -> None:
    markdown = (
        "[[Pág. 4]]\n"
        + _page_map_header(692)
        + "início\n[[Pág. 5]]\ncontinuação\n"
        + _page_map_header(731)
        + "fim\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [(segment.page_start, segment.page_end) for segment in result.segments] == [(4, 5), (5, 5)]


def test_page_map_bodies_are_exact_contiguous_source_slices() -> None:
    markdown = (
        "prefácio\n[[Pág. 4]]\n"
        + _page_map_header(978)
        + "primeiro sem marcador próprio\n"
        + _page_map_header(999)
        + "segundo\n[[Pág. 5]]\ncontinuação\n"
    )
    starts = [markdown.index(_page_map_header(number)) for number in (978, 999)]

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [segment.body for segment in result.segments] == [
        markdown[starts[0]:starts[1]],
        markdown[starts[1]:],
    ]
    assert "[[Pág. 4]]" not in result.segments[0].body
    assert "[[Pág. 4]]" not in result.segments[1].body


def test_page_map_boundary_before_any_marker_is_ambiguous() -> None:
    markdown = (
        _page_map_header(692)
        + "sem contexto de página\n"
        + _page_map_header(731)
        + "[[Pág. 4]]\ncom marcador tardio\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.AMBIGUOUS
    assert result.segments == ()
    assert result.ambiguity_reason == "unresolved_page_context"


def test_page_map_regressive_markers_are_ambiguous() -> None:
    markdown = (
        "[[Pág. 5]]\n"
        + _page_map_header(692)
        + "primeiro\n[[Pág. 4]]\n"
        + _page_map_header(731)
        + "segundo\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.AMBIGUOUS
    assert result.segments == ()
    assert result.ambiguity_reason == "non_monotonic_page_markers"


def test_page_map_shared_page_preserves_independent_legal_identities() -> None:
    markdown = (
        "[[Pág. 4]]\n"
        + _page_map_header(978)
        + "Registro relativo ao Tema 978/STJ.\nprimeiro\n"
        + _page_map_header(999)
        + "Registro relativo ao Tema 999/STJ.\nsegundo\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    identities = [
        resolve_segment_identity("PrecedenteVinculante", segment)
        for segment in result.segments
    ]

    assert [segment.segment_id for segment in result.segments] == ["segment-0001", "segment-0002"]
    assert [segment.source_unit_label for segment in result.segments] == [
        _page_map_header(978).rstrip(),
        _page_map_header(999).rstrip(),
    ]
    assert [identity.status for identity in identities] == [IdentityStatus.RESOLVED, IdentityStatus.RESOLVED]
    assert [identity.fields["repo_jur_precedente_numero"] for identity in identities] == ["978", "999"]
    assert [identity.fields["repo_jur_tribunal"] for identity in identities] == ["STJ", "STJ"]


def test_page_map_internal_tema_repetitivo_citation_is_not_a_boundary() -> None:
    markdown = (
        "[[Pág. 4]]\n"
        + _page_map_header(692)
        + "A fundamentação cita Tema Repetitivo 978 em prosa.\n"
        + _page_map_header(731)
        + "segundo\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert len(result.segments) == 2
    assert [segment.source_unit_label for segment in result.segments] == [
        _page_map_header(692).rstrip(),
        _page_map_header(731).rstrip(),
    ]


def test_shared_parser_resolves_real_u_e205_header_identity() -> None:
    segment = _precedent_segment(_precedent_pua(692, 4, "conteúdo"))

    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_precedente_numero"] == "692"


def test_shared_parser_resolves_ascii_two_space_header_identity() -> None:
    segment = _precedent_segment(_precedent(731, 4, "A revisão é relativa ao Tema 731/STJ."))

    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_precedente_numero"] == "731"


def test_shared_parser_keeps_distinct_direct_segment_identities() -> None:
    identities = [
        resolve_segment_identity(
            "PrecedenteVinculante",
            _precedent_segment(_precedent_pua(number, 4, "conteúdo")),
        )
        for number in (978, 999)
    ]

    assert [identity.status for identity in identities] == [
        IdentityStatus.RESOLVED,
        IdentityStatus.RESOLVED,
    ]
    assert [identity.fields["repo_jur_precedente_numero"] for identity in identities] == [
        "978",
        "999",
    ]


def test_shared_parser_ignores_internal_different_precedent_citation() -> None:
    body = _precedent_pua(
        1014,
        7,
        "A fundamentação cita Tema Repetitivo 692 em prosa.",
    )

    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _precedent_segment(body),
    )

    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_precedente_numero"] == "1014"


def test_shared_parser_rejects_bare_citation_and_truncated_header() -> None:
    bodies = (
        "[[Pág. 1]]\nSuperior Tribunal de Justiça (STJ)\nCita Tema Repetitivo 692 em prosa.\n",
        "Tema Repetitivo 692 \ue205 Situação Afetado\n[[Pág. 1]]\nSuperior Tribunal de Justiça (STJ)\n",
    )

    for body in bodies:
        identity = resolve_segment_identity(
            "PrecedenteVinculante",
            _precedent_segment(body),
        )
        assert identity.status is not IdentityStatus.RESOLVED
        assert "repo_jur_precedente_numero" not in identity.fields


def test_shared_parser_resolves_distinct_identities_from_one_segmentation() -> None:
    markdown = (
        "[[Pág. 9]]\n"
        "Tema Repetitivo 1039 \ue205 Situação Afetado Órgão Primeira Seção\n"
        "Registro relativo ao Tema 1039/STJ.\nprimeiro\n"
        "Tema Repetitivo 1065 \ue205 Situação Afetado Órgão Primeira Seção\n"
        "Registro relativo ao Tema 1065/STJ.\nsegundo\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    identities = [
        resolve_segment_identity("PrecedenteVinculante", segment)
        for segment in result.segments
    ]

    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert [identity.status for identity in identities] == [
        IdentityStatus.RESOLVED,
        IdentityStatus.RESOLVED,
    ]
    assert [identity.fields["repo_jur_precedente_numero"] for identity in identities] == [
        "1039",
        "1065",
    ]


def test_boundary_and_identity_use_same_compiled_precedent_header_pattern() -> None:
    boundary_pattern = getattr(segmentation_module, "PRECEDENT_HEADER_PATTERN", None)
    identity_pattern = getattr(identity_module, "PRECEDENT_HEADER_PATTERN", None)

    assert boundary_pattern is not None
    assert identity_pattern is boundary_pattern
    precedent_rule = next(
        rule
        for rule in DEFAULT_SEGMENTATION_REGISTRY.rules
        if rule.rule_id == "precedentes-qualificados-tema-repetitivo-v1"
    )
    closure_values = tuple(cell.cell_contents for cell in (precedent_rule.detect.__closure__ or ()))
    assert boundary_pattern in closure_values


def test_segment_identity_extracts_tribunal_from_prefix_before_internal_marker() -> None:
    body = (
        "Tema Repetitivo 999 \ue205 Situação Afetado Órgão Primeira Seção\n"
        "Registro relativo ao Tema 999/STJ.\ntexto exclusivo do prefixo\n"
        "[[Pág. 5]]\nrestante sem tribunal\n"
    )
    segment = Segment(
        "segment-0001", "Tema Repetitivo 999", body, 4, 5,
        "precedentes-qualificados-tema-repetitivo-v1",
    )

    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_precedente_numero"] == "999"
    assert identity.fields["repo_jur_tribunal"] == "STJ"


def test_mid_page_segment_keeps_fields_found_only_in_its_prefix() -> None:
    body = (
        "Tema Repetitivo 731  Situação Afetado  Órgão Primeira Seção\n"
        "Registro relativo ao Tema 731/STJ.\n"
        "[[Pág. 6]]\ncontinuação\n"
    )
    segment = Segment(
        "segment-0001", "Tema Repetitivo 731", body, 5, 6,
        "precedentes-qualificados-tema-repetitivo-v1",
    )

    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_precedente_numero"] == "731"
    assert identity.fields["repo_jur_tribunal"] == "STJ"


def test_shared_page_second_segment_extracts_only_its_own_prefix() -> None:
    markdown = (
        "[[Pág. 4]]\n"
        "Tema Repetitivo 978 \ue205 Situação Afetado Órgão Primeira Seção\n"
        "Registro relativo ao Tema 978/STF.\nprimeiro\n"
        "Tema Repetitivo 999 \ue205 Situação Afetado Órgão Primeira Seção\n"
        "Registro relativo ao Tema 999/STJ.\nsegundo\n"
        "[[Pág. 5]]\ncontinuação somente do segundo\n"
    )

    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    first, second = result.segments
    first_identity = resolve_segment_identity("PrecedenteVinculante", first)
    second_identity = resolve_segment_identity("PrecedenteVinculante", second)

    assert first.page_start == second.page_start == 4
    assert first.body not in second.body
    assert first_identity.fields["repo_jur_tribunal"] == "STF"
    assert second_identity.fields["repo_jur_tribunal"] == "STJ"


def test_segment_without_internal_marker_uses_its_existing_page_context() -> None:
    body = (
        "Tema Repetitivo 1039 \ue205 Situação Afetado Órgão Primeira Seção\n"
        "Registro relativo ao Tema 1039/STJ.\n"
    )
    segment = Segment(
        "segment-0001", "Tema Repetitivo 1039", body, 9, 9,
        "precedentes-qualificados-tema-repetitivo-v1",
    )

    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_tribunal"] == "STJ"


def test_prefix_internal_citation_does_not_override_own_tribunal() -> None:
    body = (
        "Tema Repetitivo 692 \ue205 Situação Afetado Órgão Primeira Seção\n"
        "Registro relativo ao Tema 692/STJ.\n"
        "A fundamentação cita Repercussão Geral Tema 999/STF.\n"
        "[[Pág. 2]]\ncontinuação\n"
    )
    segment = Segment(
        "segment-0001", "Tema Repetitivo 692", body, 1, 2,
        "precedentes-qualificados-tema-repetitivo-v1",
    )

    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_tribunal"] == "STJ"


def test_genuinely_conflicting_tribunals_without_own_header_stays_unresolved() -> None:
    segment = Segment(
        "segment-0001", "", "STJ e STF aparecem sem cabeçalho estrutural próprio.\n", 3, 3,
        "precedentes-qualificados-tema-repetitivo-v1",
    )

    identity = resolve_segment_identity("PrecedenteVinculante", segment)

    assert identity.status in {
        IdentityStatus.AMBIGUOUS,
        IdentityStatus.REQUIRES_OPERATOR_METADATA,
    }
    assert identity.fields == {}


def _tribunal_segment(number: int, evidence: str) -> Segment:
    body = (
        f"Tema Repetitivo {number}  Situação Afetado  Órgão Primeira Seção\n"
        f"[[Pág. 1]]\n{evidence}\n"
    )
    return Segment(
        "segment-0001",
        f"Tema Repetitivo {number}",
        body,
        1,
        1,
        "precedentes-qualificados-tema-repetitivo-v1",
    )


def test_precedent_tribunal_own_number_self_citation_resolves_stj() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante", _tribunal_segment(692, "Revisão relativa ao Tema 692/STJ.")
    )
    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_tribunal"] == "STJ"


def test_precedent_tribunal_different_theme_citation_does_not_resolve() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante", _tribunal_segment(1016, "Aplicam-se as teses do Tema 952/STJ.")
    )
    assert identity.status is IdentityStatus.REQUIRES_OPERATOR_METADATA


def test_precedent_tribunal_explicit_self_referential_phrase_resolves_stj() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _tribunal_segment(
            1016,
            "O Superior Tribunal de Justiça (STJ) ouviu especialistas no presente Tema Repetitivo.",
        ),
    )
    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_tribunal"] == "STJ"


def test_precedent_tribunal_parallel_repercussao_geral_does_not_resolve() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _tribunal_segment(1014, "Repercussão Geral Tema 1151/STF - questão paralela."),
    )
    assert identity.status is IdentityStatus.REQUIRES_OPERATOR_METADATA


def test_precedent_tribunal_satellite_process_mention_does_not_resolve() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante", _tribunal_segment(1065, "Processo STF RE 1456456 - concluso ao relator.")
    )
    assert identity.status is IdentityStatus.REQUIRES_OPERATOR_METADATA


def test_precedent_tribunal_vice_presidency_act_on_satellite_process_does_not_resolve() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _tribunal_segment(
            1031,
            "A Vice-Presidência do STJ admitiu o recurso extraordinário no REsp 1.830.508/RS.",
        ),
    )
    assert identity.status is IdentityStatus.REQUIRES_OPERATOR_METADATA


def test_precedent_tribunal_own_stj_evidence_ignores_foreign_stf_cross_reference() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _tribunal_segment(692, "Repercussão Geral Tema 799/STF. Revisão relativa ao Tema 692/STJ."),
    )
    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_tribunal"] == "STJ"


def test_precedent_tribunal_own_stf_evidence_ignores_foreign_stj_cross_reference() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _tribunal_segment(1151, "Vide Tema 954/STJ. Julgamento do tema pelo STF."),
    )
    assert identity.status is IdentityStatus.RESOLVED
    assert identity.fields["repo_jur_tribunal"] == "STF"


def test_precedent_tribunal_genuine_own_evidence_conflict_is_ambiguous() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _tribunal_segment(692, "Tema 692/STJ. O julgamento do tema pelo STF concluiu em sentido diverso."),
    )
    assert identity.status is IdentityStatus.AMBIGUOUS


def test_precedent_tribunal_only_discarded_cross_references_requires_metadata() -> None:
    identity = resolve_segment_identity(
        "PrecedenteVinculante",
        _tribunal_segment(
            1031,
            "Vide Controvérsia n. 133/STJ. Repercussão Geral Tema 1209/STF. Processo STF RE 1.",
        ),
    )
    assert identity.status is IdentityStatus.REQUIRES_OPERATOR_METADATA


def test_precedent_tribunal_resolution_is_independent_of_mention_order() -> None:
    cross_reference = "Repercussão Geral Tema 799/STF."
    own_evidence = "Revisão relativa ao Tema 692/STJ."
    identities = [
        resolve_segment_identity(
            "PrecedenteVinculante",
            _tribunal_segment(692, " ".join(parts)),
        )
        for parts in ((own_evidence, cross_reference), (cross_reference, own_evidence))
    ]
    assert [identity.status for identity in identities] == [
        IdentityStatus.RESOLVED,
        IdentityStatus.RESOLVED,
    ]
    assert [identity.fields["repo_jur_tribunal"] for identity in identities] == ["STJ", "STJ"]


TRAILER = (
    "Exportar todos Imprimir todos Imprimir selecionados\n\n"
    "Esta pesquisa recupera informações inseridas pelo NUGEPNAC nesta página e as presentes na "
    "base de dados da Secretaria de Jurisprudência do STJ. Versão 3.2.2.1 | de 29/04/2026 13:13.\n\n"
    "SAFS - Quadra 06 - Lote 01 - CEP: 70095-900 - Brasília - DF +55 61 3319-8000\n"
)


def _two_precedents_with_tail(tail: str) -> str:
    return (
        _precedent(1039, 9, "Tema 1039/STJ. conteúdo anterior")
        + _precedent(
            1065,
            9,
            "Tema 1065/STJ. conteúdo válido\n[[Pág. 10]]\nÚltima atualização: 07/11/2025",
        )
        + tail
    )


def test_precedent_document_trailer_is_excluded_from_last_segment() -> None:
    result = segment_markdown(_two_precedents_with_tail(TRAILER), DEFAULT_SEGMENTATION_REGISTRY)
    assert result.outcome is SegmentationOutcome.SEGMENTS
    assert "Última atualização: 07/11/2025" in result.segments[-1].body
    assert "Exportar todos Imprimir todos Imprimir selecionados" not in result.segments[-1].body
    assert "Esta pesquisa recupera informações" not in result.segments[-1].body


def test_in_body_partial_trailer_anchor_does_not_cut() -> None:
    markdown = _two_precedents_with_tail("Exportar apenas este registro\nconteúdo até EOF\n")
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert result.segments[-1].body.endswith("Exportar apenas este registro\nconteúdo até EOF\n")


def test_precedent_without_trailer_keeps_last_segment_to_eof() -> None:
    markdown = _two_precedents_with_tail("fim legítimo exato\n")
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert result.segments[-1].body.endswith("fim legítimo exato\n")


def test_real_tema_1065_keeps_valid_content_and_excludes_trailer() -> None:
    markdown = Path("output/STJ - Precedentes Qualificados.md").read_text(encoding="utf-8")
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    body = result.segments[-1].body
    assert "Relator NANCY ANDRIGHI Acórdão publicado em 11/05/2022 ROA" in body
    assert "Embargos de Declaração 28/10/2022 Trânsito em Julgado -" in body
    assert "Última atualização: 07/11/2025" in body
    assert "Exportar todos Imprimir todos Imprimir selecionados" not in body


def test_real_tema_1065_page_range_survives_trailer_cut() -> None:
    markdown = Path("output/STJ - Precedentes Qualificados.md").read_text(encoding="utf-8")
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    assert (result.segments[-1].page_start, result.segments[-1].page_end) == (9, 10)


def test_trailer_never_participates_in_any_segment_identity_fields() -> None:
    result = segment_markdown(_two_precedents_with_tail(TRAILER), DEFAULT_SEGMENTATION_REGISTRY)
    identities = [resolve_segment_identity("PrecedenteVinculante", segment) for segment in result.segments]
    assert all("NUGEPNAC" not in str(dict(identity.fields)) for identity in identities)
    assert all("Secretaria de Jurisprudência" not in str(dict(identity.fields)) for identity in identities)


def test_trailer_cut_inserts_no_synthetic_page_marker() -> None:
    markdown = _two_precedents_with_tail(TRAILER)
    result = segment_markdown(markdown, DEFAULT_SEGMENTATION_REGISTRY)
    first_boundary = markdown.index("Tema Repetitivo 1039")
    trailer_start = markdown.index("Exportar todos Imprimir todos Imprimir selecionados")
    assert "".join(segment.body for segment in result.segments) == markdown[first_boundary:trailer_start]
