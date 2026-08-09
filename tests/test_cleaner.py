import re

import pytest

from pipeline_juridico.cleaner import (
    ILLEGIBLE_TEXT_MARKER,
    UnauthorizedIllegibleMarkerError,
    build_legislative_headings,
    clean_markdown,
    ensure_illegible_marker_authorized,
    join_symbol_across_page_break,
    mark_final_index,
    normalize_thin_space_entities,
    normalize_legal_symbols,
    recompose_native_paragraphs,
    remove_repetitive_margins,
)


def test_normalize_thin_space_entities_separates_word_before_number() -> None:
    markdown = "apreensão de &#8201;37 gramas"

    assert normalize_thin_space_entities(markdown) == "apreensão de 37 gramas"


def test_normalize_thin_space_entities_separates_abbreviation_and_number() -> None:
    markdown = "Lei n.&#8201;11.343/2006"

    assert normalize_thin_space_entities(markdown) == "Lei n. 11.343/2006"


def test_normalize_thin_space_entities_separates_glued_words() -> None:
    markdown = "na&#8201;realidade"

    assert normalize_thin_space_entities(markdown) == "na realidade"


def test_normalize_thin_space_entities_does_not_duplicate_adjacent_space() -> None:
    markdown = "regulamentar.&#8201; A diferença"

    result = normalize_thin_space_entities(markdown)

    assert result == "regulamentar. A diferença"
    assert "  " not in result


def test_normalize_thin_space_entities_handles_hex_variant() -> None:
    markdown = "apreensão de &#x2009;37 gramas"

    assert normalize_thin_space_entities(markdown) == "apreensão de 37 gramas"


def test_normalize_thin_space_entities_handles_uppercase_hex_variant() -> None:
    markdown = "apreensão de &#X2009;37 gramas"

    assert normalize_thin_space_entities(markdown) == "apreensão de 37 gramas"


def test_normalize_thin_space_entities_handles_named_variant() -> None:
    markdown = "apreensão de &thinsp;37 gramas"

    assert normalize_thin_space_entities(markdown) == "apreensão de 37 gramas"


def test_normalize_thin_space_entities_handles_uppercase_named_variant() -> None:
    markdown = "apreensão de &THINSP;37 gramas"

    assert normalize_thin_space_entities(markdown) == "apreensão de 37 gramas"


def test_normalize_thin_space_entities_preserves_other_html_entities() -> None:
    markdown = "Tom &amp; Ana: &lt;texto&gt; &nbsp; intacto"

    assert normalize_thin_space_entities(markdown) == markdown


def test_normalize_thin_space_entities_preserves_punctuation_and_page_marker() -> None:
    markdown = (
        "[[Pág. 9]]\n"
        "<!-- método: texto_nativo -->\n\n"
        "Lei n.&#8201;11.343/2006\n"
        "&#8201;\n"
        "Fim."
    )

    result = normalize_thin_space_entities(markdown)

    assert result == (
        "[[Pág. 9]]\n"
        "<!-- método: texto_nativo -->\n\n"
        "Lei n. 11.343/2006\n"
        " \n"
        "Fim."
    )
    assert "[[Pág. 9]]" in result
    assert "<!-- método: texto_nativo -->" in result


def test_normalize_thin_space_entities_is_idempotent() -> None:
    markdown = "apreensão de &#8201;37 gramas"

    normalized = normalize_thin_space_entities(markdown)

    assert normalize_thin_space_entities(normalized) == normalized


def test_normalize_thin_space_entities_no_op_without_entity() -> None:
    markdown = "[[Pág. 9]]\nTexto jurídico sem entidade.\t\n"

    assert normalize_thin_space_entities(markdown) == markdown


def test_join_symbol_across_page_break_preserves_page_marker() -> None:
    content = (
        "vigência do anterior, Lei n\n\n"
        "[[Pág. 176]]\n"
        "<!-- método: texto_nativo -->\n\n"
        "o 3.071, de 1 o de janeiro de 1916."
    )

    result = join_symbol_across_page_break(content)

    assert result == (
        "vigência do anterior, Lei nº\n\n"
        "[[Pág. 176]]\n"
        "<!-- método: texto_nativo -->\n\n"
        "3.071, de 1 o de janeiro de 1916."
    )


def test_clean_markdown_normalizes_line_endings() -> None:
    result = clean_markdown("Primeira\r\nSegunda\rTerceira")

    assert result == "Primeira\nSegunda\nTerceira\n"
    assert "\r" not in result


def test_clean_markdown_strips_trailing_whitespace() -> None:
    result = clean_markdown("Linha com espaços  \nLinha com tab\t\n  - item indentado  ")

    assert result == "Linha com espaços\nLinha com tab\n  - item indentado\n"
    assert all(not re.search(r"[ \t]$", line) for line in result.splitlines())


@pytest.mark.parametrize("line_breaks", [4, 5])
def test_clean_markdown_collapses_three_or_more_blank_lines_to_two(
    line_breaks: int,
) -> None:
    result = clean_markdown(f"Primeiro parágrafo{'\n' * line_breaks}Segundo parágrafo")

    assert result == "Primeiro parágrafo\n\nSegundo parágrafo\n"
    assert "\n\n\n" not in result


def test_clean_markdown_ensures_single_trailing_newline() -> None:
    result = clean_markdown("Texto sem quebra final")

    assert result.endswith("\n")
    assert not result.endswith("\n\n")


def test_clean_markdown_handles_multiple_trailing_newlines() -> None:
    result = clean_markdown("Texto com quebras finais\n\n\n\n")

    assert result == "Texto com quebras finais\n"


def test_clean_markdown_empty_string_stays_empty() -> None:
    assert clean_markdown("") == ""


@pytest.mark.parametrize(
    "text",
    [
        "Texto simples",
        "Primeira linha\r\nSegunda linha  \r\n\r\n\r\nTerceira\t",
        "  - item indentado\t\n\n\n\nParágrafo final\n\n",
    ],
)
def test_clean_markdown_is_idempotent(text: str) -> None:
    cleaned = clean_markdown(text)

    assert clean_markdown(cleaned) == cleaned


def test_clean_markdown_preserves_markdown_table() -> None:
    table = (
        "| Processo | Data | Situação |\n"
        "| --- | --- | --- |\n"
        "| 0001234-56.2020.8.26.0100 | 26/07/2026 | Ativo |\n"
        "| 0009876-54.2021.8.26.0200 | 27/07/2026 | Arquivado |"
    )
    text = (
        "\n\n\n"
        "| Processo | Data | Situação |  \n"
        "| --- | --- | --- |\n"
        "| 0001234-56.2020.8.26.0100 | 26/07/2026 | Ativo |\t\n"
        "| 0009876-54.2021.8.26.0200 | 27/07/2026 | Arquivado |  "
        "\n\n\n\n"
    )

    result = clean_markdown(text)

    assert table in result


def test_clean_markdown_preserves_ocr_delimiters() -> None:
    ocr_block = "*[Image OCR]\nTexto capturado por OCR aqui.\n[End OCR]*"
    text = f"\n\n\n{ocr_block}\n\n\n\n"

    result = clean_markdown(text)

    assert ocr_block in result


def test_clean_markdown_preserves_legal_citations() -> None:
    citation = (
        "Nos termos do art. 5º, inciso LIV, da Constituição Federal de 1988, "
        "e do art. 927 do Código Civil (Lei nº 10.406/2002)..."
    )
    text = f"\n\n\n{citation}  \n\n\n"

    result = clean_markdown(text)

    assert citation in result


def test_clean_markdown_preserves_dates() -> None:
    dates = ("26/07/2026", "26 de julho de 2026", "2026-07-26")
    text = f"\n\n\nDatas: {', '.join(dates)}.  \n\n\n"

    result = clean_markdown(text)

    assert all(date in result for date in dates)


def test_clean_markdown_preserves_process_numbers() -> None:
    process_number = "0001234-56.2020.8.26.0100"
    text = f"\n\n\nProcesso nº {process_number}.  \n\n\n"

    result = clean_markdown(text)

    assert process_number in result


def test_clean_markdown_preserves_signature_block() -> None:
    signature_block = "_______________________\nJoão da Silva\nOAB/SP 123.456"
    text = (
        "\n\n\n"
        "_______________________  \n"
        "João da Silva\t\n"
        "OAB/SP 123.456  "
        "\n\n\n\n"
    )

    result = clean_markdown(text)

    assert signature_block in result


def test_mark_final_index_preserves_document_without_structural_tail() -> None:
    markdown = (
        "# Decisão\n\n"
        "Art. 12. O pedido é julgado improcedente.\n\n"
        "Publique-se. Intimem-se.\n\n"
        "Documento assinado eletronicamente."
    )

    assert mark_final_index(markdown) == markdown


def test_mark_final_index_preserves_document_with_sparse_structural_tail() -> None:
    markdown = (
        "# Lei sintética\n\n"
        "Art. 99. Esta Lei entra em vigor na data de sua publicação.\n\n"
        "LIVRO I\n\n"
        "TÍTULO ÚNICO"
    )

    assert mark_final_index(markdown) == markdown


def test_mark_final_index_follows_terminal_literal_index_anchor() -> None:
    markdown = (
        "Art. 2.046. Todas as remissões, em diplomas legislativos, "
        "consideram-se feitas às disposições correspondentes deste Código. "
        "FERNANDO HENRIQUE CARDOSO\n\n"
        "Aloysio Nunes Ferreira Filho Este texto não substitui o publicado "
        "no DOU de 11.1.2002 ÍNDICE\n\n"
        "P A R T E G E R A L\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "CAPÍTULO I DA PERSONALIDADE"
    )

    result = mark_final_index(markdown)

    index_heading = result.index("# ÍNDICE")
    assert result.index("Aloysio Nunes Ferreira Filho") < index_heading
    assert (
        result.index("Este texto não substitui o publicado no DOU")
        < index_heading
    )
    assert index_heading < result.index("P A R T E")


def test_mark_final_index_replaces_isolated_terminal_index_paragraph() -> None:
    markdown = (
        "LEI Nº 10.406, DE 10 DE JANEIRO DE 2002\n\n"
        "Vigência\n\n"
        "ÍNDICE\n\n"
        "Art. 2.046. Todas as remissões consideram-se feitas às disposições "
        "correspondentes deste Código.\n\n"
        "Brasília, 10 de janeiro de 2002.\n\n"
        "FERNANDO HENRIQUE CARDOSO\n"
        "Aloysio Nunes Ferreira Filho\n\n"
        "Este texto não substitui o publicado no DOU de 11.1.2002\n\n"
        "ÍNDICE\n\n"
        "PARTE GERAL\n\n"
        "LIVRO I\n\n"
        "TÍTULO I\n\n"
        "CAPÍTULO I"
    )

    result = mark_final_index(markdown)

    assert result.count("# ÍNDICE") == 1
    assert re.findall(r"^ÍNDICE$", result, re.MULTILINE) == ["ÍNDICE"]
    assert result.index("ÍNDICE") < result.index("Art. 2.046.")
    assert (
        "Este texto não substitui o publicado no DOU de 11.1.2002\n\n"
        "# ÍNDICE"
    ) in result


def test_mark_final_index_demotes_heading_after_promoted_index() -> None:
    markdown = (
        "# PARTE GERAL\n\n"
        "Art. 2.046. Todas as remissões consideram-se feitas às disposições "
        "correspondentes deste Código.\n\n"
        "ÍNDICE\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        "[[Pág. 42]]\n"
        "<!-- método: texto_nativo -->\n\n"
        "# PARTE GERAL\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "CAPÍTULO I DA PERSONALIDADE"
    )

    result = mark_final_index(markdown)

    assert result.count("# ÍNDICE") == 1
    assert "# ÍNDICE\n\nLIVRO I DAS PESSOAS" in result
    assert "\n\n## PARTE GERAL\n\n" in result


def test_mark_final_index_demotes_heading_after_inserted_index() -> None:
    markdown = (
        "Art. 2.046. Todas as remissões consideram-se feitas às disposições "
        "correspondentes deste Código.\n\n"
        "Este texto não substitui o publicado no DOU — consulte o ÍNDICE\n\n"
        "# PARTE GERAL\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "CAPÍTULO I DA PERSONALIDADE"
    )

    result = mark_final_index(markdown)

    assert (
        "Este texto não substitui o publicado no DOU — consulte o ÍNDICE\n\n"
        "# ÍNDICE\n\n## PARTE GERAL"
    ) in result


def test_mark_final_index_demotes_all_headings_inside_index() -> None:
    markdown = (
        "Art. 2.046. Esta Lei entra em vigor na data de sua publicação.\n\n"
        "ÍNDICE\n\n"
        "# PARTE GERAL\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "# PARTE ESPECIAL"
    )

    result = mark_final_index(markdown)

    assert "\n\n## PARTE GERAL\n\n" in result
    assert result.endswith("\n\n## PARTE ESPECIAL")


def test_mark_final_index_preserves_heading_before_index() -> None:
    markdown = (
        "# PARTE GERAL\n\n"
        "Art. 2.046. Esta Lei entra em vigor na data de sua publicação.\n\n"
        "ÍNDICE\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "CAPÍTULO I DA PERSONALIDADE"
    )

    result = mark_final_index(markdown)

    assert result.startswith("# PARTE GERAL\n\nArt. 2.046.")


def test_mark_final_index_preserves_sparse_tail_with_heading_byte_for_byte() -> None:
    markdown = (
        "# PARTE GERAL\n\n"
        "Art. 99. Esta Lei entra em vigor na data de sua publicação.\n\n"
        "ÍNDICE\n\n"
        "# PARTE ESPECIAL\n\n"
        "LIVRO I"
    )

    assert mark_final_index(markdown) == markdown


def test_mark_final_index_preserves_plain_text_inside_index() -> None:
    markdown = (
        "Art. 2.046. Esta Lei entra em vigor na data de sua publicação.\n\n"
        "ÍNDICE\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "CAPÍTULO I DA PERSONALIDADE"
    )

    result = mark_final_index(markdown)

    assert "# ÍNDICE\n\nLIVRO I DAS PESSOAS\n\n" in result
    assert "# LIVRO I DAS PESSOAS" not in result


def test_mark_final_index_preserves_page_markers_around_and_inside_index() -> None:
    marker_before = "[[Pág. 41]]\n<!-- método: texto_nativo -->"
    marker_inside = "[[Pág. 42]]\n<!-- método: texto_nativo -->"
    markdown = (
        f"{marker_before}\n\n"
        "Art. 2.046. Esta Lei entra em vigor na data de sua publicação.\n\n"
        "ÍNDICE\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        f"{marker_inside}\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "CAPÍTULO I DA PERSONALIDADE"
    )

    result = mark_final_index(markdown)

    assert marker_before in result
    assert marker_inside in result
    assert result.count("<!-- método: texto_nativo -->") == 2


def test_mark_final_index_preserves_level_six_heading_inside_index() -> None:
    markdown = (
        "Art. 2.046. Esta Lei entra em vigor na data de sua publicação.\n\n"
        "ÍNDICE\n\n"
        "LIVRO I DAS PESSOAS\n\n"
        "TÍTULO I DAS PESSOAS NATURAIS\n\n"
        "CAPÍTULO I DA PERSONALIDADE\n\n"
        "###### DISPOSIÇÕES FINAIS"
    )

    result = mark_final_index(markdown)

    assert result.endswith("\n\n###### DISPOSIÇÕES FINAIS")
    assert "####### DISPOSIÇÕES FINAIS" not in result


def test_build_legislative_headings_builds_book_heading() -> None:
    result = build_legislative_headings("LIVRO I\n\nDAS PESSOAS")

    assert re.search(
        r"^##(?!#)\s+LIVRO I\b.*DAS PESSOAS",
        result,
        re.MULTILINE,
    )


def test_build_legislative_headings_builds_title_heading() -> None:
    result = build_legislative_headings("TÍTULO I\n\nDAS PESSOAS NATURAIS")

    assert re.search(
        r"^###(?!#)\s+TÍTULO I\b.*DAS PESSOAS NATURAIS",
        result,
        re.MULTILINE,
    )


def test_build_legislative_headings_builds_chapter_heading() -> None:
    result = build_legislative_headings(
        "CAPÍTULO I\n\nDa Personalidade e da Capacidade"
    )

    assert re.search(
        r"^####(?!#)\s+CAPÍTULO I\b.*Da Personalidade e da Capacidade",
        result,
        re.MULTILINE,
    )


def test_build_legislative_headings_builds_mixed_case_section_heading() -> None:
    result = build_legislative_headings(
        "Seção I\n\nDa Curadoria dos Bens do Ausente"
    )

    assert re.search(
        r"^#####(?!#)\s+Seção I\b.*Da Curadoria dos Bens do Ausente",
        result,
        re.MULTILINE,
    )


def test_build_legislative_headings_separates_subtitle_from_title() -> None:
    content = (
        "TÍTULO I\n\n"
        "Do Direito Pessoal\n\n"
        "SUBTÍTULO I\n\n"
        "Do Casamento"
    )

    result = build_legislative_headings(content)

    assert result == (
        "### TÍTULO I — Do Direito Pessoal\n\n"
        "#### SUBTÍTULO I — Do Casamento"
    )


def test_build_legislative_headings_preserves_single_line_subtitle_index() -> None:
    content = "SUBTÍTULO I DA SOCIEDADE NÃO PERSONIFICADA"

    assert build_legislative_headings(content) == content


def test_build_legislative_headings_preserves_complete_single_line_part() -> None:
    content = "PARTE GERAL"

    assert build_legislative_headings(content) == content


def test_build_legislative_headings_preserves_common_uppercase_text() -> None:
    content = (
        "Texto de introdução qualquer.\n\n"
        "TÍTULO INSTITUCIONAL SEM MARCADOR"
    )

    assert build_legislative_headings(content) == content


def test_build_legislative_headings_preserves_remaining_content() -> None:
    article = "Art. 1º Toda pessoa é capaz de direitos e deveres."
    content = f"LIVRO I\n\nDAS PESSOAS\n\n{article}"

    result = build_legislative_headings(content)

    assert re.search(
        r"^##(?!#)\s+LIVRO I\b.*DAS PESSOAS",
        result,
        re.MULTILINE,
    )
    assert article in result


def test_build_legislative_headings_preserves_page_marker_and_method() -> None:
    page_marker = "[[Pág. 1]]"
    method_comment = "<!-- método: texto_nativo -->"
    content = (
        f"{page_marker}\n{method_comment}\n\n"
        "LIVRO I\n\nDAS PESSOAS"
    )

    result = build_legislative_headings(content)

    assert page_marker in result
    assert method_comment in result
    assert re.search(
        r"^##(?!#)\s+LIVRO I\b.*DAS PESSOAS",
        result,
        re.MULTILINE,
    )


def test_build_legislative_headings_accepts_roman_numeral_a_suffix() -> None:
    content = (
        "TÍTULO I-A (Incluído pela Lei nº 12.441, de 2011) (Vigência)\n\n"
        "DA EMPRESA INDIVIDUAL DE RESPONSABILIDADE LIMITADA\n\n"
        "CAPÍTULO VII-A (Incluído pela Lei nº 13.777, de 2018) "
        "(Vigência)\n\n"
        "DO CONDOMÍNIO EM MULTIPROPRIEDADE"
    )

    result = build_legislative_headings(content)

    assert (
        "### TÍTULO I-A (Incluído pela Lei nº 12.441, de 2011) "
        "(Vigência) — DA EMPRESA INDIVIDUAL DE RESPONSABILIDADE LIMITADA"
        in result
    )
    assert (
        "#### CAPÍTULO VII-A (Incluído pela Lei nº 13.777, de 2018) "
        "(Vigência) — DO CONDOMÍNIO EM MULTIPROPRIEDADE"
        in result
    )


def test_build_legislative_headings_accepts_feminine_unique_qualifier() -> None:
    content = "Seção Única\n\nDa Caracterização"

    result = build_legislative_headings(content)

    assert result == "##### Seção Única — Da Caracterização"


def test_build_legislative_headings_accepts_complementary_qualifier() -> None:
    content = "LIVRO COMPLEMENTAR\n\nDAS Disposições Finais e Transitórias"

    result = build_legislative_headings(content)

    assert result == (
        "## LIVRO COMPLEMENTAR — DAS Disposições Finais e Transitórias"
    )


def test_build_legislative_headings_absorbs_separate_annotations() -> None:
    content = (
        "CAPÍTULO VII-A (Incluído pela Lei nº 13.777, de 2018) "
        "(Vigência)\n\n"
        "DO CONDOMÍNIO EM MULTIPROPRIEDADE\n\n"
        "Seção I\n\n"
        "(Incluído pela Lei nº 13.777, de 2018) (Vigência)\n\n"
        "Disposições Gerais"
    )

    result = build_legislative_headings(content)

    assert (
        "##### Seção I (Incluído pela Lei nº 13.777, de 2018) "
        "(Vigência) — Disposições Gerais"
        in result
    )
    assert (
        "##### Seção I — (Incluído pela Lei nº 13.777, de 2018)"
        not in result
    )


def test_build_legislative_headings_converts_letter_spaced_parts() -> None:
    content = "P A R T E G E R A L\n\nP A R T E E S P E C I A L"

    result = build_legislative_headings(content)

    assert result == "# PARTE GERAL\n\n# PARTE ESPECIAL"


def test_build_legislative_headings_splits_attached_letter_spaced_part() -> None:
    article = (
        "Art. 232. A recusa à perícia médica ordenada pelo juiz poderá suprir "
        "a prova que se pretendia obter com o exame."
    )
    content = (
        f"{article} P A R T E E S P E C I A L\n\n"
        "LIVRO I\n\nDO DIREITO DAS OBRIGAÇÕES"
    )

    result = build_legislative_headings(content)

    assert result == (
        f"{article}\n\n"
        "# PARTE ESPECIAL\n\n"
        "## LIVRO I — DO DIREITO DAS OBRIGAÇÕES"
    )
    assert build_legislative_headings(result) == result


def test_build_legislative_headings_preserves_unknown_letter_spaced_suffix() -> None:
    content = "Consulte também a seção técnica de apoio A P O I O T E C N I C O"

    assert build_legislative_headings(content) == content


def test_remove_repetitive_margins_removes_repeated_textual_header_fused_to_continuation() -> None:
    legal_header = "Superior Tribunal de Justiça"
    continuation = (
        "agravada, pois demonstrado o rebate do fundamento da falta de "
        "interesse recursal em impugnar o valor da causa."
    )
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"{legal_header}\n"
            f"Conteúdo jurídico exclusivo da página {page_number}."
        )
        for page_number in range(1, 4)
    ]
    pages.extend(
        [
            (
                "[[Pág. 4]]\n"
                "<!-- método: texto_nativo -->\n"
                "6. A decisão recorrida deve ser"
            ),
            (
                "[[Pág. 5]]\n"
                "<!-- método: texto_nativo -->\n"
                f"{legal_header} {continuation}"
            ),
        ]
    )

    result = remove_repetitive_margins("\n".join(pages))

    assert legal_header not in result
    assert (
        "[[Pág. 5]]\n<!-- método: texto_nativo -->\n"
        f"{continuation}"
    ) in result
    for page_number in range(1, 4):
        assert f"Conteúdo jurídico exclusivo da página {page_number}." in result
        assert f"[[Pág. {page_number}]]" in result


def test_remove_repetitive_margins_removes_isolated_recognized_header_without_affecting_content() -> None:
    repeated_header = "https://tribunal.example/documento"
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"{repeated_header}\n"
            f"Conteúdo preservado da página {page_number}."
        )
        for page_number in range(1, 4)
    ]
    pages.extend(
        [
            "[[Pág. 4]]\n<!-- método: texto_nativo -->\nQuarta página intacta.",
            "[[Pág. 5]]\n<!-- método: texto_nativo -->\nQuinta página intacta.",
        ]
    )

    result = remove_repetitive_margins("\n".join(pages))

    assert repeated_header not in result
    for page_number in range(1, 4):
        assert f"Conteúdo preservado da página {page_number}." in result
        assert f"[[Pág. {page_number}]]" in result
    assert "Quarta página intacta." in result
    assert "Quinta página intacta." in result


def test_remove_repetitive_margins_preserves_textual_header_mentioned_in_body() -> None:
    legal_header = "Superior Tribunal de Justiça"
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Abertura exclusiva da página {page_number}.\n"
            f"O precedente do {legal_header} orienta este julgamento.\n"
            f"Fechamento exclusivo da página {page_number}."
        )
        for page_number in range(1, 6)
    ]

    result = remove_repetitive_margins("\n".join(pages))

    assert result.count(legal_header) == len(pages)


def test_remove_repetitive_margins_preserves_normal_cross_page_continuation() -> None:
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Continuação própria da página {page_number}."
        )
        for page_number in range(1, 6)
    ]
    markdown = "\n".join(pages)

    assert remove_repetitive_margins(markdown) == markdown


def test_remove_repetitive_margins_preserves_textual_candidate_below_threshold() -> None:
    legal_header = "Superior Tribunal de Justiça"
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            + (f"{legal_header}\n" if page_number <= 2 else "")
            + f"Conteúdo exclusivo da página {page_number}."
        )
        for page_number in range(1, 6)
    ]

    result = remove_repetitive_margins("\n".join(pages))

    assert result.count(legal_header) == 2


def test_remove_repetitive_margins_preserves_textual_candidate_only_seen_fused() -> None:
    legal_header = "Superior Tribunal de Justiça"
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"{legal_header} continuação exclusiva da página {page_number}."
        )
        for page_number in range(1, 6)
    ]

    result = remove_repetitive_margins("\n".join(pages))

    assert result.count(legal_header) == len(pages)


def test_remove_repetitive_margins_removes_isolated_technical_footer_with_varying_page_counter() -> None:
    footer = (
        "GABGF09 AREsp 1462304 Petição : 592169/2020 "
        "C542506155;0029089584@ Documento"
    )
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Conteúdo exclusivo da página {page_number}.\n"
            f"{footer} Página {page_number} de 8"
        )
        for page_number in range(1, 4)
    ]
    pages.extend(
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Conteúdo exclusivo da página {page_number}. "
            f"{footer} Página {page_number} de 8"
        )
        for page_number in range(4, 6)
    )

    result = remove_repetitive_margins("\n".join(pages))

    assert "GABGF09 AREsp 1462304 Petição" not in result
    for page_number in range(1, 6):
        assert f"Conteúdo exclusivo da página {page_number}." in result
        assert f"[[Pág. {page_number}]]" in result


def test_remove_repetitive_margins_removes_technical_footer_fused_to_paragraph_end() -> None:
    footer = (
        "GABGF09 AREsp 1462304 Petição : 592169/2020 "
        "C542506155;0029089584@ Documento"
    )
    legal_sentence = (
        "6. Afastado o óbice da Súmula 283 do STF, empregado na decisão"
    )
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Conteúdo jurídico exclusivo da página {page_number}.\n"
            f"{footer} Página {page_number} de 8"
        )
        for page_number in range(1, 4)
    ]
    pages.extend(
        [
            (
                "[[Pág. 4]]\n"
                "<!-- método: texto_nativo -->\n"
                f"{legal_sentence} {footer} Página 4 de 8"
            ),
            "[[Pág. 5]]\n<!-- método: texto_nativo -->\nPágina final intacta.",
        ]
    )

    result = remove_repetitive_margins("\n".join(pages))

    assert legal_sentence in result
    assert f"{legal_sentence}\n[[Pág. 5]]" in result
    assert footer not in result


def test_remove_repetitive_margins_removes_footer_interrupting_name_across_page_break() -> None:
    footer = (
        "Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - "
        "DJe: 04/04/2019"
    )
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Conteúdo exclusivo da página {page_number}.\n"
            f"{footer} Página {page_number} de 6"
        )
        for page_number in range(1, 4)
    ]
    pages.extend(
        [
            (
                "[[Pág. 4]]\n"
                "<!-- método: texto_nativo -->\n"
                f"Votaram com o Sr. Ministro Relator os Srs. Ministros Paulo de "
                f"{footer} Página 4 de 6"
            ),
            (
                "[[Pág. 5]]\n"
                "<!-- método: texto_nativo -->\n"
                "Tarso Sanseverino, Nancy Andrighi e Ricardo Villas Bôas Cueva."
            ),
        ]
    )

    result = remove_repetitive_margins("\n".join(pages))

    assert "Ministros Paulo de\n[[Pág. 5]]" in result
    assert (
        "[[Pág. 5]]\n<!-- método: texto_nativo -->\n"
        "Tarso Sanseverino, Nancy Andrighi e Ricardo Villas Bôas Cueva."
    ) in result
    assert "Documento: 1807307 - Inteiro Teor do Acórdão" not in result


def test_remove_repetitive_margins_removes_footer_fused_immediately_before_page_marker() -> None:
    footer = (
        "Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - "
        "DJe: 04/04/2019"
    )
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Conteúdo exclusivo da página {page_number}.\n"
            f"{footer} Página {page_number} de 6"
        )
        for page_number in range(1, 4)
    ]
    substantive_text = "A decisão recorrida deve ser integralmente mantida."
    pages.extend(
        [
            (
                "[[Pág. 4]]\n"
                "<!-- método: texto_nativo -->\n"
                f"{substantive_text} {footer} Página 4 de 6"
            ),
            "[[Pág. 5]]\n<!-- método: texto_nativo -->\nPágina seguinte intacta.",
        ]
    )

    result = remove_repetitive_margins("\n".join(pages))

    assert f"{substantive_text}\n[[Pág. 5]]" in result
    assert "Documento: 1807307 - Inteiro Teor do Acórdão" not in result
    assert (
        "[[Pág. 5]]\n<!-- método: texto_nativo -->\nPágina seguinte intacta."
    ) in result
    assert re.findall(r"\[\[Pág\. (\d+)\]\]", result) == [
        "1",
        "2",
        "3",
        "4",
        "5",
    ]


def test_remove_repetitive_margins_removes_stacked_recurring_footers() -> None:
    technical_footer = (
        "GABGF09 AREsp 1462304 Petição : 592169/2020 "
        "C542506155;0029089584@ Documento"
    )
    electronic_signature = (
        "Documento eletrônico VDA27282965 assinado eletronicamente. "
        "Código de Controle do Documento: 0123456789abcdef"
    )
    substantive_text = "A decisão recorrida deve ser integralmente mantida."
    page_contents = [
        f"{substantive_text}\n{technical_footer}\n{electronic_signature}",
        technical_footer,
        technical_footer,
        electronic_signature,
        electronic_signature,
    ]
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"{page_content}"
        )
        for page_number, page_content in enumerate(page_contents, start=1)
    ]

    result = remove_repetitive_margins("\n".join(pages))

    assert technical_footer not in result
    assert electronic_signature not in result
    assert substantive_text in result


def test_remove_repetitive_margins_preserves_low_frequency_electronic_signature() -> None:
    signature = (
        "Documento eletrônico VDA27282965 assinado eletronicamente nos termos "
        "do Art.1º §2º inciso III da Lei 11.419/2006"
    )
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Conteúdo exclusivo da página {page_number}."
            + (f"\n{signature}" if page_number <= 2 else "")
        )
        for page_number in range(1, 6)
    ]
    markdown = "\n".join(pages)

    assert remove_repetitive_margins(markdown) == markdown


def test_remove_repetitive_margins_preserves_non_recurring_citation_with_similar_words() -> None:
    citations = [
        "Documento citado na Página 12 do processo, juntado em 03/05/2020.",
        "A Página 19 do Documento registra julgamento em 14/06/2021.",
        "Segundo o Documento de fls. 31, o DJe ocorreu em 22/08/2022.",
        "A data do Documento referido na Página 44 é 09/11/2023.",
        "Consulte a Página 57 do Documento protocolado em 10/01/2024.",
    ]
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"{citation}"
        )
        for page_number, citation in enumerate(citations, start=1)
    ]
    markdown = "\n".join(pages)

    assert remove_repetitive_margins(markdown) == markdown


def test_remove_repetitive_margins_preserves_r01_subtitulo_and_index_examples() -> None:
    repeated_legal_text = "Art. 44 §2º — subtítulo do índice sistemático"
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"Abertura exclusiva {page_number}.\n"
            f"{repeated_legal_text}\n"
            f"Fechamento exclusivo {page_number}."
        )
        for page_number in range(1, 6)
    ]
    markdown = "\n".join(pages)

    assert remove_repetitive_margins(markdown) == markdown


def test_remove_repetitive_margins_does_not_alter_papel_nome_style_fusion() -> None:
    markdown = (
        "[[Pág. 1]]\n"
        "<!-- método: texto_nativo -->\n"
        "Papel\n"
        "Nome"
    )

    assert remove_repetitive_margins(markdown) == markdown


def test_illegible_text_marker_constant_value() -> None:
    assert ILLEGIBLE_TEXT_MARKER == "[[TEXTO ILEGÍVEL]]"


def test_ensure_illegible_marker_authorized_allows_when_permitted() -> None:
    text = f"Trecho não reconhecido: {ILLEGIBLE_TEXT_MARKER}"

    ensure_illegible_marker_authorized(text, allow_partial=True)


def test_ensure_illegible_marker_authorized_raises_when_not_permitted() -> None:
    text = f"Trecho não reconhecido: {ILLEGIBLE_TEXT_MARKER}"

    with pytest.raises(UnauthorizedIllegibleMarkerError):
        ensure_illegible_marker_authorized(text, allow_partial=False)


def test_ensure_illegible_marker_authorized_ignores_text_without_marker() -> None:
    ensure_illegible_marker_authorized(
        "Todo o conteúdo foi reconhecido.",
        allow_partial=False,
    )


def test_dollar_variant_is_not_recognized_as_illegible_marker() -> None:
    ensure_illegible_marker_authorized(
        "Trecho legado: $$TEXTO ILEGÍVEL$$",
        allow_partial=False,
    )


def test_recompose_native_paragraphs_joins_nearby_plain_lines() -> None:
    content = "Este texto continua\nna linha seguinte."
    blocks = [
        (10.0, 21.0, "Este texto continua"),
        (22.0, 33.0, "na linha seguinte."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "Este texto continua na linha seguinte."


RECURSO_HEADING_CONTENT = (
    "RECURSO \nESPECIAL. \nPROCESSUAL \nCIVIL. \nARBITRAGEM. \nNULIDADE \nDE \n"
    "COMPROMISSO ARBITRAL E DE SENTENÇA ARBITRAL. OMISSÃO, CONTRADIÇÃO OU \n"
    "ERRO MATERIAL. AUSÊNCIA. VALOR DA CAUSA. IMPUGNAÇÃO. MENSURAÇÃO DO \n"
    "CONTEÚDO \nECONÔMICO. \nCONDENAÇÃO \nEM \nSENTENÇA \nARBITRAL. \n"
    "POSSIBILIDADE.\n"
)
RECURSO_HEADING_BLOCKS = [(339.75, 650.0, RECURSO_HEADING_CONTENT)]
RECURSO_HEADING_LINE_X0S = [[
    160.1, 220.1, 280.9, 357.45, 398.4, 478.8, 542.7, 160.1,
    160.1, 160.1, 234.0, 318.1, 405.4, 438.9, 507.2, 160.1,
]]
RECURSO_HEADING_EXPECTED = (
    "RECURSO ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE "
    "COMPROMISSO ARBITRAL E DE SENTENÇA ARBITRAL. OMISSÃO, CONTRADIÇÃO OU "
    "ERRO MATERIAL. AUSÊNCIA. VALOR DA CAUSA. IMPUGNAÇÃO. MENSURAÇÃO DO "
    "CONTEÚDO ECONÔMICO. CONDENAÇÃO EM SENTENÇA ARBITRAL. POSSIBILIDADE."
)


def test_recompose_native_paragraphs_unifies_recurso_especial_with_x0_signal() -> None:
    result = recompose_native_paragraphs(
        RECURSO_HEADING_CONTENT,
        RECURSO_HEADING_BLOCKS,
        line_x0s=RECURSO_HEADING_LINE_X0S,
    )

    assert RECURSO_HEADING_EXPECTED in result.split("\n\n")
    assert len(re.findall(r"\w+", result)) == len(
        re.findall(r"\w+", RECURSO_HEADING_CONTENT)
    )
    assert result.count(".") == RECURSO_HEADING_CONTENT.count(".")


def _assert_native_label_separated(
    content, blocks, line_x0s, label, value_start, *, legacy_fallback=False
):
    try:
        result = recompose_native_paragraphs(content, blocks, line_x0s=line_x0s)
    except TypeError as error:
        if not legacy_fallback or "unexpected keyword argument 'line_x0s'" not in str(error):
            raise
        result = recompose_native_paragraphs(content, blocks)
    assert label in result.split("\n\n")
    assert f"{label} {value_start}" not in result


def test_recompose_native_paragraphs_keeps_processo_label_separated() -> None:
    _assert_native_label_separated(
            "PROCESSO\nProcesso em segredo de justiça, Rel. Ministro Antonio Carlos Ferreira,\n"
            "Corte Especial, por unanimidade, julgado em 4/12/2024, DJEN\n16/12/2024.\n",
            [(297.0, 337.0, "PROCESSO\nProcesso em segredo de justiça, Rel. Ministro Antonio Carlos Ferreira,\nCorte Especial, por unanimidade, julgado em 4/12/2024, DJEN\n16/12/2024.\n")],
            [[145.6, 218.4, 218.4, 218.4]],
            "PROCESSO",
            "Processo em segredo",
            legacy_fallback=True,
    )


def test_recompose_native_paragraphs_keeps_tema_label_separated() -> None:
    _assert_native_label_separated(
            "TEMA\nAção penal privada subsidiária da pública. Ausência de inércia do\nMinistério Público. Discordância do querelante quanto à tipificação\ndos fatos dada pelo Ministério Público não autoriza a propositura de\nqueixa-crime. Crimes contra a honra de servidor público. Preclusão\nda via da ação penal privada.\n",
            [(387.0, 457.0, "TEMA\nAção penal privada subsidiária da pública. Ausência de inércia do\nMinistério Público. Discordância do querelante quanto à tipificação\ndos fatos dada pelo Ministério Público não autoriza a propositura de\nqueixa-crime. Crimes contra a honra de servidor público. Preclusão\nda via da ação penal privada.\n")],
            [[171.8, 218.4, 218.4, 218.4, 218.4, 218.4]],
            "TEMA",
            "Ação penal privada",
    )


def test_recompose_native_paragraphs_keeps_ramo_do_direito_label_separated() -> None:
    _assert_native_label_separated(
            "RAMO DO DIREITO\nDIREITO PENAL, DIREITO PROCESSUAL PENAL\n",
            [(357.0, 367.0, "RAMO DO DIREITO\nDIREITO PENAL, DIREITO PROCESSUAL PENAL\n")],
            [[108.6, 218.4]],
            "RAMO DO DIREITO",
            "DIREITO PENAL",
    )


def test_recompose_native_paragraphs_keeps_recorrente_label_separated() -> None:
    content = (
        "RECORRENTE\n: DAIBY S/A \nADVOGADO\n: JOÃO JOAQUIM MARTINELLI  - SP175215A\n"
        "RECORRIDO \n: ITAU UNIBANCO S.A \nADVOGADOS\n: FÁBIO LIMA QUINTAS  - DF017721 \n"
        " LUIZ CARLOS STURZENEGGER  - DF001942A\n RICARDO CHIAVEGATTI  - SP183217 \n"
        " MARCOS CAVALCANTE DE OLIVEIRA  - SP244461 \n"
        " MARINA PEREIRA ANTUNES DE FREITAS E OUTRO(S) - DF037075 \n"
        " LUCAS FOSSALUSSA LISSE E OUTRO(S) - SP317353 \n BRUNO SANTIN FERREIRA  - DF047090 \n"
        " LEONARDO VASCONCELOS LINS FONSECA  - DF040094 \n"
    )
    blocks = [(429.93, 562.93, content)]
    line_x0s = [[
        104.25, 203.4, 104.25, 203.4, 104.25, 203.4, 104.25,
        203.4, 203.4, 203.4, 203.4, 203.4, 203.4, 203.4,
    ]]

    try:
        result = recompose_native_paragraphs(content, blocks, line_x0s=line_x0s)
    except TypeError as error:
        if "unexpected keyword argument 'line_x0s'" not in str(error):
            raise
        result = recompose_native_paragraphs(content, blocks)

    assert "RECORRENTE" in result.split("\n\n")
    assert "RECORRENTE : DAIBY S/A" not in result


def test_recompose_native_paragraphs_boundary_exactly_fifty_percent_keeps_protection() -> None:
    content = "RÓTULO\ncontinuação na mesma margem\ncontinuação deslocada.\n"
    blocks = [(10.0, 30.0, content)]

    result = recompose_native_paragraphs(
        content, blocks, line_x0s=[[100.0, 101.0, 120.0]]
    )

    assert "RÓTULO" in result.split("\n\n")


def test_recompose_native_paragraphs_boundary_above_fifty_percent_disables_protection() -> None:
    content = "RÓTULO\nprimeira continuação\nsegunda continuação\nfecho deslocado.\n"
    blocks = [(10.0, 40.0, content)]

    result = recompose_native_paragraphs(
        content, blocks, line_x0s=[[100.0, 100.5, 101.0, 120.0]]
    )

    assert result.startswith("RÓTULO primeira continuação")


def test_recompose_native_paragraphs_block_without_extra_lines_keeps_protection() -> None:
    content = "RÓTULO\nvalor em outro bloco.\n"
    blocks = [(10.0, 20.0, "RÓTULO\n"), (21.0, 31.0, "valor em outro bloco.\n")]

    result = recompose_native_paragraphs(
        content, blocks, line_x0s=[[100.0], [100.0]]
    )

    assert "RÓTULO" in result.split("\n\n")


def test_recompose_native_paragraphs_without_x0_parameter_preserves_legacy_behavior() -> None:
    result = recompose_native_paragraphs(
        RECURSO_HEADING_CONTENT, RECURSO_HEADING_BLOCKS
    )

    assert result == f"RECURSO\n\n{RECURSO_HEADING_EXPECTED.removeprefix('RECURSO ')}"


def _editorial_cover_scenario() -> tuple[str, list[tuple[float, float, str]]]:
    content = (
        "Informativo\nde Jurisprudência\n"
        "Informativo de Jurisprudência n. 24 - Edição Extraordinária     "
        "28 de janeiro de 2025 \nDireito Penal\n"
        "Este periódico destaca teses jurisprudenciais e não consiste em "
        "repositório oficial de jurisprudência.\nCORTE ESPECIAL\nPROCESSO\n"
        "Processo em segredo de justiça, Rel. Ministro Antonio Carlos Ferreira,\n"
        "Corte Especial, por unanimidade, julgado em 4/12/2024, DJEN\n"
        "16/12/2024.\n"
    )
    blocks = [
        (50.0, 102.0, "Informativo\nde Jurisprudência\n"),
        (53.1, 197.0, "  \n  \n  \n  \n  \n  \n  \nInformativo de "
         "Jurisprudência n. 24 - Edição Extraordinária     28 de janeiro de "
         "2025 \nDireito Penal\n"),
        (217.2, 245.6, "Este periódico destaca teses jurisprudenciais e não "
         "consiste em repositório oficial de jurisprudência.\n \n"),
        (252.0, 267.0, "CORTE ESPECIAL\n"),
        (297.0, 337.0, "PROCESSO\nProcesso em segredo de justiça, Rel. Ministro "
         "Antonio Carlos Ferreira,\nCorte Especial, por unanimidade, julgado em "
         "4/12/2024, DJEN\n16/12/2024.\n"),
    ]
    return content, blocks


def test_recompose_native_paragraphs_separates_cover_elements_with_leading_blank_lines(
) -> None:
    content, blocks = _editorial_cover_scenario()
    result = recompose_native_paragraphs(content, blocks, page_has_large_text=True)
    paragraphs = result.split("\n\n")
    edition = ("Informativo de Jurisprudência n. 24 - Edição Extraordinária "
               "28 de janeiro de 2025 Direito Penal")
    notice = ("Este periódico destaca teses jurisprudenciais e não consiste em "
              "repositório oficial de jurisprudência.")

    assert edition in paragraphs
    assert next(item for item in paragraphs if edition in item) == edition
    assert notice in paragraphs
    assert "CORTE ESPECIAL" in paragraphs
    assert "PROCESSO" not in next(item for item in paragraphs if "CORTE ESPECIAL" in item)
    assert len(re.findall(r"\w+", result)) == len(re.findall(r"\w+", content))


def test_recompose_native_paragraphs_blank_lines_gate_requires_large_text() -> None:
    content, blocks = _editorial_cover_scenario()
    legacy_result = recompose_native_paragraphs(content, blocks)
    result = recompose_native_paragraphs(content, blocks, page_has_large_text=False)
    # Captura o comportamento legado defeituoso quando o gate está desligado.
    expected = (
        "Informativo de Jurisprudência Informativo de Jurisprudência n. 24 - "
        "Edição Extraordinária 28 de janeiro de 2025 Direito Penal Este periódico "
        "destaca teses jurisprudenciais e não consiste em repositório oficial de "
        "jurisprudência. CORTE ESPECIAL\n\nPROCESSO\n\nProcesso em segredo de "
        "justiça, Rel. Ministro Antonio Carlos Ferreira, Corte Especial, por "
        "unanimidade, julgado em 4/12/2024, DJEN 16/12/2024."
    )
    assert legacy_result == expected
    assert result == expected


def test_recompose_native_paragraphs_gate_threshold_boundary() -> None:
    content = "Título\ncontinuação\nFecho\n"
    blocks = [(0.0, 20.0, "Título\n \n \ncontinuação\n"),
              (30.0, 40.0, "Fecho\n")]

    gated = recompose_native_paragraphs(content, blocks, page_has_large_text=True)
    legacy = recompose_native_paragraphs(content, blocks, page_has_large_text=False)

    assert gated != legacy


def test_recompose_native_paragraphs_joins_uppercase_words_fragmented_within_block(
) -> None:
    block_text = (
        "PROCESSUAL CIVIL. DEMANDA INDENIZATÓRIA. \n"
        "VALOR \n"
        "DA \n"
        "CAUSA. \n"
        "PROVEITO \n"
        "ECONÔMICO \n"
        "PERSEGUIDO. \n"
    )
    blocks = [(0.0, 70.0, block_text)]

    result = recompose_native_paragraphs(block_text, blocks)

    assert result == (
        "PROCESSUAL CIVIL. DEMANDA INDENIZATÓRIA. VALOR DA CAUSA. "
        "PROVEITO ECONÔMICO PERSEGUIDO."
    )


def test_recompose_native_paragraphs_recomposes_unrelated_block_when_page_has_colon_label(
) -> None:
    fields = (
        "RELATOR\n"
        ": MINISTRO GURGEL DE FARIA\n"
        "AGRAVANTE \n"
        ": NORTE ENERGIA S.A. \n"
        "ADVOGADOS\n"
        ": PRISCILA SANTOS ARTIGAS  - PR022529 \n"
    )
    summary = (
        "PROCESSUAL CIVIL. DEMANDA INDENIZATÓRIA. \n"
        "VALOR \n"
        "DA \n"
        "CAUSA. \n"
        "PROVEITO \n"
        "ECONÔMICO \n"
        "PERSEGUIDO. \n"
    )
    content = f"{fields}\n{summary}"
    blocks = [
        (74.2, 143.1, fields),
        (331.4, 413.4, summary),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert (
        "PROCESSUAL CIVIL. DEMANDA INDENIZATÓRIA. VALOR DA CAUSA. "
        "PROVEITO ECONÔMICO PERSEGUIDO."
    ) in result
    assert "RELATOR : MINISTRO GURGEL DE FARIA" not in result


def test_recompose_native_paragraphs_recomposes_unrelated_block_resp_case() -> None:
    fields = (
        "RECORRENTE\n"
        ": DAIBY S/A \n"
        "ADVOGADO\n"
        ": JOÃO JOAQUIM MARTINELLI  - SP175215A\n"
    )
    excerpt = (
        "Cuida-se \n"
        "de \n"
        "recurso \n"
        "especial \n"
        "interposto \n"
        "por \n"
        "DAIBY \n"
        "S/A, \n"
    )
    content = f"{fields}\n{excerpt}"
    blocks = [
        (90.6, 140.6, fields),
        (391.2, 405.2, excerpt),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert "Cuida-se de recurso especial interposto por DAIBY S/A," in result
    assert "RECORRENTE : DAIBY S/A" not in result


def test_recompose_native_paragraphs_preserves_colon_label_pair_within_block(
) -> None:
    block_text = "RELATOR\n: MINISTRO GURGEL DE FARIA\n"
    blocks = [(74.2, 97.2, block_text)]

    result = recompose_native_paragraphs(block_text, blocks)

    assert "RELATOR : MINISTRO GURGEL DE FARIA" not in result


def test_recompose_native_paragraphs_preserves_multiple_consecutive_colon_fields(
) -> None:
    block_text = (
        "AGRAVANTE \n"
        ": NORTE ENERGIA S.A. \n"
        "ADVOGADOS\n"
        ": PRISCILA SANTOS ARTIGAS  - PR022529 \n"
    )
    blocks = [(97.2, 143.1, block_text)]

    result = recompose_native_paragraphs(block_text, blocks)

    assert "AGRAVANTE : NORTE ENERGIA S.A." not in result
    assert ": NORTE ENERGIA S.A. ADVOGADOS" not in result
    assert "ADVOGADOS : PRISCILA SANTOS ARTIGAS" not in result


def test_recompose_native_paragraphs_joins_thematic_field_value_fragmented_within_label_block(
) -> None:
    block_text = (
        "RAMO DO DIREITO\n"
        "DIREITO\n"
        " PROCESSUAL\n"
        " PENAL,\n"
        " DIREITO\n"
        " DA\n"
        " PESSOA\n"
        " COM\n"
        "DEFICIÊNCIA\n"
    )
    blocks = [(0.0, 90.0, block_text)]

    result = recompose_native_paragraphs(block_text, blocks)

    assert result == (
        "RAMO DO DIREITO\n\n"
        "DIREITO PROCESSUAL PENAL, DIREITO DA PESSOA COM DEFICIÊNCIA"
    )


@pytest.mark.parametrize("label", ["TEMA", "PROCESSO", "DESTAQUE"])
def test_recompose_native_paragraphs_preserves_field_label_as_first_line_of_own_block(
    label: str,
) -> None:
    value = "Valor descritivo do campo"
    content = f"{label}\n{value}"
    blocks = [
        (0.0, 10.0, label),
        (11.0, 21.0, value),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{label}\n\n{value}"


def test_recompose_native_paragraphs_joins_single_word_lines_interspersed_with_multi_word_lines(
) -> None:
    block_text = (
        "AGRAVO INTERNO NO RECURSO ESPECIAL. IMPUGNAÇÃO AO VALOR \n"
        "DA \n"
        "CAUSA. \n"
        "PRETENSÃO \n"
        "DE \n"
        "NATUREZA \n"
        "DECLARATÓRIA \n"
        "E \n"
        "MANDAMENTAL, COM PEDIDO CONDENATÓRIO DE OBRIGAÇÃO DE \n"
        "FAZER. CONTEÚDO ECONÔMICO DA CAUSA. AUSÊNCIA. FIXAÇÃO EM \n"
        "CARÁTER ESTIMATIVO. RAZOABILIDADE E PROPORCIONALIDADE. SÚM \n"
        "7 DO STJ."
    )
    blocks = [(0.0, 40.0, block_text)]

    result = recompose_native_paragraphs(block_text, blocks)

    assert result == (
        "AGRAVO INTERNO NO RECURSO ESPECIAL. IMPUGNAÇÃO AO VALOR DA CAUSA. "
        "PRETENSÃO DE NATUREZA DECLARATÓRIA E MANDAMENTAL, COM PEDIDO "
        "CONDENATÓRIO DE OBRIGAÇÃO DE FAZER. CONTEÚDO ECONÔMICO DA CAUSA. "
        "AUSÊNCIA. FIXAÇÃO EM CARÁTER ESTIMATIVO. RAZOABILIDADE E "
        "PROPORCIONALIDADE. SÚM 7 DO STJ."
    )


def test_recompose_native_paragraphs_joins_resp_1704551_sp_fragmented_value_of_claim(
) -> None:
    block_text = (
        "RECURSO ESPECIAL. AÇÃO DECLARATÓRIA. \n"
        "CONTROVÉRSIA SOBRE A COMPETÊNCIA. \n"
        "VALOR\n"
        "DA\n"
        "CAUSA.\n"
        "CONTEÚDO ECONÔMICO PRETENDIDO."
    )
    blocks = [(0.0, 60.0, block_text)]

    result = recompose_native_paragraphs(block_text, blocks)

    assert result == (
        "RECURSO ESPECIAL. AÇÃO DECLARATÓRIA. CONTROVÉRSIA SOBRE A "
        "COMPETÊNCIA. VALOR DA CAUSA. CONTEÚDO ECONÔMICO PRETENDIDO."
    )


def test_recompose_native_paragraphs_does_not_join_subtitle_to_article() -> None:
    article = (
        "Art. 985. A sociedade adquire personalidade jurídica com a "
        "inscrição, no registro próprio e na forma da lei, dos seus atos "
        "constitutivos (arts. 45 e 1.150)."
    )
    subtitle = "SUBTÍTULO I"
    denomination = "Da Sociedade Não Personificada"
    content = f"{article}\n{subtitle}\n{denomination}"
    blocks = [
        (10.0, 21.0, article),
        (22.0, 33.0, subtitle),
        (34.0, 45.0, denomination),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{article}\n\n{subtitle}\n\n{denomination}"


def test_recompose_native_paragraphs_does_not_join_subtitle_to_unique_paragraph() -> None:
    paragraph = (
        "Parágrafo único. Havendo mais de um sócio ostensivo, as respectivas "
        "contas serão prestadas e julgadas no mesmo processo."
    )
    subtitle = "SUBTÍTULO II"
    content = f"{paragraph}\n{subtitle}"
    blocks = [
        (10.0, 21.0, paragraph),
        (22.0, 33.0, subtitle),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{paragraph}\n\n{subtitle}"


def test_recompose_native_paragraphs_does_not_join_subtitle_to_item() -> None:
    item = (
        "IV - os bens que aos filhos couberem na herança, quando os pais "
        "forem excluídos da sucessão."
    )
    subtitle = "SUBTÍTULO III"
    content = f"{item}\n{subtitle}"
    blocks = [
        (10.0, 21.0, item),
        (22.0, 33.0, subtitle),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{item}\n\n{subtitle}"


def test_recompose_native_paragraphs_joins_lowercase_subtitle_in_prose() -> None:
    first_line = "A nota explica por que"
    second_line = "o subtítulo do capítulo foi escolhido."
    content = f"{first_line}\n{second_line}"
    blocks = [
        (10.0, 21.0, first_line),
        (22.0, 33.0, second_line),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_line} {second_line}"
    assert build_legislative_headings(result) == result


def test_recompose_native_paragraphs_joins_art_129_lowercase_parte() -> None:
    first_line = (
        "Art. 129. Reputa-se verificada, quanto aos efeitos jurídicos, a "
        "condição cujo implemento for maliciosamente obstado pela"
    )
    second_line = (
        "parte a quem desfavorecer, considerando-se, ao contrário, não "
        "verificada a condição maliciosamente levada a efeito por aquele a "
        "quem aproveita o seu implemento."
    )
    content = f"{first_line}\n{second_line}"
    blocks = [
        (10.0, 21.0, first_line),
        (22.0, 33.0, second_line),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_line} {second_line}"


def test_recompose_native_paragraphs_joins_livro_reference_with_parte_prose() -> None:
    first_line = (
        "Art. 44. § 2º As disposições concernentes às associações aplicam-se "
        "subsidiariamente às sociedades que são objeto do Livro II da"
    )
    second_line = (
        "Parte Especial deste Código. (Incluído pela Lei nº 10.825, de "
        "22.12.2003)"
    )
    content = f"{first_line}\n{second_line}"
    blocks = [
        (10.0, 21.0, first_line),
        (22.0, 33.0, second_line),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_line} {second_line}"


def test_recompose_native_paragraphs_joins_capitulo_reference_in_prose() -> None:
    first_line = "Art. 593. A prestação de serviço reger-se-á pelas disposições deste"
    second_line = "Capítulo."
    content = f"{first_line}\n{second_line}"
    blocks = [
        (10.0, 21.0, first_line),
        (22.0, 33.0, second_line),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_line} {second_line}"


def test_recompose_native_paragraphs_joins_secao_reference_in_prose() -> None:
    first_line = "Art. 1.458. Aplicam-se à sociedade em comandita simples as normas da"
    first_line += " sociedade em nome coletivo, no que forem compatíveis com as"
    first_line += " disposições estabelecidas pela presente"
    second_line = "Seção."
    content = f"{first_line}\n{second_line}"
    blocks = [
        (10.0, 21.0, first_line),
        (22.0, 33.0, second_line),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_line} {second_line}"


@pytest.mark.parametrize(
    "second_entry",
    [
        "Seção II Da Sucessão Provisória",
        "Capítulo IV-A Da Tutela",
        "Seção Única Da Caracterização",
        "Livro Complementar Das Disposições Finais e Transitórias",
    ],
)
def test_recompose_native_paragraphs_separates_structured_index_entries(
    second_entry: str,
) -> None:
    first_entry = "Seção I Da Curadoria dos Bens do Ausente"
    content = f"{first_entry}\n{second_entry}"
    blocks = [
        (10.0, 21.0, first_entry),
        (22.0, 33.0, second_entry),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_entry}\n\n{second_entry}"


@pytest.mark.parametrize(
    "heading",
    [
        "CAPÍTULO II — DAS ASSOCIAÇÕES",
        "TÍTULO III",
    ],
)
def test_recompose_native_paragraphs_does_not_join_article_to_structure_heading(
    heading: str,
) -> None:
    article = "Art. 44. São pessoas jurídicas de direito privado:"
    content = f"{article}\n{heading}"
    blocks = [
        (10.0, 21.0, article),
        (22.0, 33.0, heading),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{article}\n\n{heading}"


def test_recompose_native_paragraphs_does_not_join_across_jurisprudence_closing() -> None:
    previous_text = (
        "VII - Agravo Interno improvido.\n"
        "(AgInt no REsp 1739440/SP, Rel. Ministra REGINA HELENA COSTA, \n"
        "PRIMEIRA TURMA, julgado em 08/11/2018, DJe 26/11/2018) (Grifos \n"
        "acrescidos).\n"
    )
    current_text = (
        "RECURSO ESPECIAL. INDENIZAÇÃO POR DANO MORAL. VALOR DA \n"
        "CAUSA. CRITÉRIO DE FIXAÇÃO. ...\n"
    )
    content = previous_text + current_text
    blocks = [
        (10.0, 54.0, previous_text),
        (55.0, 77.0, current_text),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == (
        "VII - Agravo Interno improvido. (AgInt no REsp 1739440/SP, Rel. "
        "Ministra REGINA HELENA COSTA, PRIMEIRA TURMA, julgado em 08/11/2018, "
        "DJe 26/11/2018) (Grifos acrescidos).\n\n"
        "RECURSO ESPECIAL. INDENIZAÇÃO POR DANO MORAL. VALOR DA CAUSA. "
        "CRITÉRIO DE FIXAÇÃO. ..."
    )


def test_recompose_native_paragraphs_does_not_join_consecutive_articles() -> None:
    first_article = "Art. 593. A prestação de serviço será contratada."
    second_article = "Art. 594. Toda a espécie de serviço pode ser contratada."
    content = f"{first_article}\n{second_article}"
    blocks = [
        (10.0, 21.0, first_article),
        (22.0, 33.0, second_article),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_article}\n\n{second_article}"


def test_recompose_native_paragraphs_does_not_join_across_page_marker() -> None:
    first_line = "Texto simples antes da mudança de página."
    marker = "[[Pág. 2]]"
    second_line = "Texto simples depois da mudança de página."
    content = f"{first_line}\n{marker}\n{second_line}"
    blocks = [
        (10.0, 21.0, first_line),
        (22.0, 33.0, marker),
        (50.0, 61.0, second_line),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"{first_line}\n\n{marker}\n\n{second_line}"


def test_recompose_native_paragraphs_separates_federal_law_closing() -> None:
    article = (
        "Art. 2.046. Todas as remissões, em diplomas legislativos, aos "
        "Códigos referidos no artigo antecedente, consideram-se feitas às\n"
        "disposições correspondentes deste Código.\n"
    )
    promulgation = (
        "Brasília, 10 de janeiro de 2002; 181 o da Independência e 114 o "
        "da República.\n"
    )
    signatures = (
        "FERNANDO HENRIQUE CARDOSO\nAloysio Nunes Ferreira Filho\n"
    )
    publication_note = (
        "Este texto não substitui o publicado no DOU de 11.1.2002\n"
    )
    index = "ÍNDICE\n"
    content = article + promulgation + signatures + publication_note + index
    blocks = [
        (28.6, 51.7, article),
        (62.3, 77.5, promulgation),
        (88.4, 110.9, signatures),
        (120.7, 131.9, publication_note),
        (142.6, 153.7, index),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == (
        "Art. 2.046. Todas as remissões, em diplomas legislativos, aos "
        "Códigos referidos no artigo antecedente, consideram-se feitas às "
        "disposições correspondentes deste Código.\n\n"
        "Brasília, 10 de janeiro de 2002; 181 o da Independência e 114 o "
        "da República.\n\n"
        "FERNANDO HENRIQUE CARDOSO\n\n"
        "Aloysio Nunes Ferreira Filho\n\n"
        "Este texto não substitui o publicado no DOU de 11.1.2002\n\n"
        "ÍNDICE"
    )


def test_recompose_native_paragraphs_still_joins_unstructured_lines() -> None:
    content = (
        "A obrigação deve ser cumprida no prazo estabelecido\n"
        "pelas partes no instrumento contratual."
    )
    blocks = [
        (10.0, 21.0, "A obrigação deve ser cumprida no prazo estabelecido"),
        (31.5, 42.5, "pelas partes no instrumento contratual."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == (
        "A obrigação deve ser cumprida no prazo estabelecido "
        "pelas partes no instrumento contratual."
    )


def test_recompose_native_paragraphs_does_not_join_article() -> None:
    content = "Disposição preliminar\nArt. 2 Esta norma entra em vigor."
    blocks = [
        (10.0, 21.0, "Disposição preliminar"),
        (22.0, 33.0, "Art. 2 Esta norma entra em vigor."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "Disposição preliminar\n\nArt. 2 Esta norma entra em vigor."


def test_recompose_native_paragraphs_does_not_join_numbered_paragraph() -> None:
    content = "Regra geral\n§ 1 O prazo será contado em dias úteis."
    blocks = [
        (10.0, 21.0, "Regra geral"),
        (22.0, 33.0, "§ 1 O prazo será contado em dias úteis."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "Regra geral\n\n§ 1 O prazo será contado em dias úteis."


@pytest.mark.parametrize(
    "paragraph",
    [
        "Parágrafo único Esta regra aplica-se imediatamente.",
        "Parágrafo 2 O prazo poderá ser prorrogado.",
    ],
)
def test_recompose_native_paragraphs_does_not_join_named_paragraph(
    paragraph: str,
) -> None:
    content = f"Regra geral\n{paragraph}"
    blocks = [
        (10.0, 21.0, "Regra geral"),
        (22.0, 33.0, paragraph),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"Regra geral\n\n{paragraph}"


def test_recompose_native_paragraphs_does_not_join_roman_numeral_item() -> None:
    content = "São requisitos:\nIV - comprovação da capacidade técnica."
    blocks = [
        (10.0, 21.0, "São requisitos:"),
        (22.0, 33.0, "IV - comprovação da capacidade técnica."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "São requisitos:\n\nIV - comprovação da capacidade técnica."


def test_recompose_native_paragraphs_does_not_join_lettered_item() -> None:
    content = "Documentos exigidos:\na) comprovante de residência."
    blocks = [
        (10.0, 21.0, "Documentos exigidos:"),
        (22.0, 33.0, "a) comprovante de residência."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "Documentos exigidos:\n\na) comprovante de residência."


def test_recompose_native_paragraphs_does_not_join_numbered_item() -> None:
    content = "Etapas do procedimento:\n1) apresentação do requerimento."
    blocks = [
        (10.0, 21.0, "Etapas do procedimento:"),
        (22.0, 33.0, "1) apresentação do requerimento."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "Etapas do procedimento:\n\n1) apresentação do requerimento."


@pytest.mark.parametrize(
    "marker",
    [
        "PARTE GERAL",
        "LIVRO DAS OBRIGAÇÕES",
        "TÍTULO DOS CONTRATOS",
        "CAPÍTULO DAS DISPOSIÇÕES GERAIS",
        "SEÇÃO DOS PRAZOS",
        "SUBSEÇÃO DOS RECURSOS",
    ],
)
def test_recompose_native_paragraphs_does_not_join_formal_structure_marker(
    marker: str,
) -> None:
    content = f"Texto introdutório\n{marker}"
    blocks = [
        (10.0, 21.0, "Texto introdutório"),
        (22.0, 33.0, marker),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == f"Texto introdutório\n\n{marker}"


def test_recompose_native_paragraphs_does_not_join_after_bare_structure() -> None:
    content = "LIVRO I\nDAS PESSOAS"
    blocks = [
        (10.0, 21.0, "LIVRO I"),
        (22.0, 33.0, "DAS PESSOAS"),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "LIVRO I\n\nDAS PESSOAS"


def test_recompose_native_paragraphs_does_not_join_across_large_gap() -> None:
    content = "Primeiro parágrafo.\nSegundo parágrafo."
    blocks = [
        (10.0, 21.0, "Primeiro parágrafo."),
        (51.0, 62.0, "Segundo parágrafo."),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "Primeiro parágrafo.\n\nSegundo parágrafo."


def test_recompose_native_paragraphs_preserves_uppercase_label_and_value() -> None:
    content = "RELATOR\n: MINISTRO FULANO"
    blocks = [
        (10.0, 21.0, "RELATOR"),
        (22.0, 33.0, ": MINISTRO FULANO"),
    ]

    result = recompose_native_paragraphs(content, blocks)

    # A proteção é por bloco, não um no-op da página; rótulo e valor não se fundem.
    assert result == "RELATOR\n\n: MINISTRO FULANO"


def test_recompose_native_paragraphs_preserves_markdown_table() -> None:
    content = (
        "| Campo | Valor |\n"
        "| --- | --- |\n"
        "| Relator | Ministro Fulano |"
    )
    blocks = [
        (10.0, 21.0, "Campo Valor"),
        (22.0, 33.0, "Relator Ministro Fulano"),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == content


def test_recompose_native_paragraphs_preserves_content_with_empty_blocks() -> None:
    content = "Primeira linha\nSegunda linha"

    result = recompose_native_paragraphs(content, [])

    assert result == content


def test_recompose_native_paragraphs_does_not_split_legal_sentence_with_saiba_mais_vocabulary(
) -> None:
    content = (
        "A controvérsia deve ser resolvida conforme o Informativo de\n"
        "Jurisprudência n. 500/STJ, julgado em 10/04/2019, DJe 16/04/2019."
    )
    blocks = [
        (10.0, 20.0, "A controvérsia deve ser resolvida conforme o Informativo de"),
        (
            27.0,
            37.0,
            "Jurisprudência n. 500/STJ, julgado em 10/04/2019, DJe 16/04/2019.",
        ),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == (
        "A controvérsia deve ser resolvida conforme o Informativo de "
        "Jurisprudência n. 500/STJ, julgado em 10/04/2019, DJe 16/04/2019."
    )


def test_recompose_native_paragraphs_separates_saiba_mais_items_after_two_line_block(
) -> None:
    content = (
        "SAIBA MAIS\n"
        "Informativo de Jurisprudência n. 135\n"
        "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA SEÇÃO, julgado em\n"
        "10/04/2019, DJe 16/04/2019\n"
        "Informativo de Jurisprudência n. 474\n"
        "Informativo de Jurisprudência n. 346\n"
        "Informativo de Jurisprudência n. 174\n"
        "VÍDEO DO JULGAMENTO"
    )
    blocks = [
        (55.0, 70.0, "SAIBA MAIS"),
        (85.0, 95.0, "Informativo de Jurisprudência n. 135"),
        (
            110.0,
            135.0,
            "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, "
            "TERCEIRA SEÇÃO, julgado em\n10/04/2019, DJe 16/04/2019",
        ),
        (150.0, 160.0, "Informativo de Jurisprudência n. 474"),
        (175.0, 185.0, "Informativo de Jurisprudência n. 346"),
        (200.0, 210.0, "Informativo de Jurisprudência n. 174"),
        (284.0, 292.0, "VÍDEO DO JULGAMENTO"),
    ]

    result = recompose_native_paragraphs(content, blocks)
    precedent = (
        "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA "
        "SEÇÃO, julgado em 10/04/2019, DJe 16/04/2019"
    )
    items = [
        "Informativo de Jurisprudência n. 135",
        precedent,
        "Informativo de Jurisprudência n. 474",
        "Informativo de Jurisprudência n. 346",
        "Informativo de Jurisprudência n. 174",
    ]

    assert precedent in result.splitlines()
    assert "Informativo de Jurisprudência n. 474" not in next(
        line for line in result.splitlines() if precedent in line
    )
    paragraphs = result.split("\n\n")
    assert all(item in paragraphs for item in items)
    assert "SAIBA MAIS" in paragraphs
    assert "VÍDEO DO JULGAMENTO" in paragraphs


def test_recompose_native_paragraphs_saiba_mais_guard_does_not_affect_blocks_outside_section(
) -> None:
    content = (
        "Alguma seção anterior\n"
        "Texto de referência que quebra em\n"
        "duas linhas físicas do mesmo bloco\n"
        "Próximo bloco corrido"
    )
    blocks = [
        (10.0, 20.0, "Alguma seção anterior"),
        (
            35.0,
            60.0,
            "Texto de referência que quebra em\n"
            "duas linhas físicas do mesmo bloco",
        ),
        (67.0, 77.0, "Próximo bloco corrido"),
    ]

    result = recompose_native_paragraphs(content, blocks)

    # Baseline anterior ao guard: fora de SAIBA MAIS, a geometria continua
    # autorizando a união do terceiro bloco ao bloco físico anterior.
    assert result == (
        "Alguma seção anterior\n\n"
        "Texto de referência que quebra em duas linhas físicas do mesmo bloco "
        "Próximo bloco corrido"
    )


def test_recompose_native_paragraphs_preserves_intra_block_join_inside_saiba_mais(
) -> None:
    content = (
        "SAIBA MAIS\n"
        "Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 117:\n"
        "INTERCEPTAÇÃO TELEFÔNICA - I\n"
        "Informativo de Jurisprudência n. 751\n"
        "VÍDEO DO JULGAMENTO"
    )
    blocks = [
        (55.0, 70.0, "SAIBA MAIS"),
        (
            85.0,
            110.0,
            "Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO "
            "N. 117:\nINTERCEPTAÇÃO TELEFÔNICA - I",
        ),
        (117.0, 127.0, "Informativo de Jurisprudência n. 751"),
        (150.0, 160.0, "VÍDEO DO JULGAMENTO"),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert (
        "Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 117: "
        "INTERCEPTAÇÃO TELEFÔNICA - I"
    ) in result.splitlines()


def test_recompose_native_paragraphs_saiba_mais_label_stays_separate_from_first_item(
) -> None:
    content = "SAIBA MAIS\nInformativo de Jurisprudência n. 135"
    blocks = [
        (55.0, 70.0, "SAIBA MAIS"),
        (75.0, 85.0, "Informativo de Jurisprudência n. 135"),
    ]

    result = recompose_native_paragraphs(content, blocks)

    assert result == "SAIBA MAIS\n\nInformativo de Jurisprudência n. 135"


def test_normalize_legal_symbols_normalizes_article_ordinal() -> None:
    content = "Art. 1 o Toda pessoa é capaz..."

    result = normalize_legal_symbols(content)

    assert "Art. 1º Toda pessoa é capaz..." in result
    assert "Art. 1 o " not in result


def test_normalize_legal_symbols_normalizes_lowercase_article_ordinal() -> None:
    content = "nos termos do art. 3 o Código..."

    result = normalize_legal_symbols(content)

    assert "art. 3º Código..." in result


def test_normalize_legal_symbols_normalizes_numbered_paragraph() -> None:
    content = "§ 1 o Findo o prazo..."

    result = normalize_legal_symbols(content)

    assert "§ 1º Findo o prazo..." in result
    assert "Findo o prazo..." in result


def test_normalize_legal_symbols_removes_space_before_ordinal_symbol() -> None:
    content = "§ 1 º Nos aforamentos..."

    result = normalize_legal_symbols(content)

    assert "§ 1º Nos aforamentos..." in result


def test_normalize_legal_symbols_normalizes_law_number() -> None:
    content = "Lei n o 8.069, de 13 de julho de 1990"

    result = normalize_legal_symbols(content)

    assert "Lei nº 8.069, de 13 de julho de 1990" in result


def test_normalize_legal_symbols_removes_space_in_law_number_symbol() -> None:
    content = "Revogado pela Lei n º 13.105, de 2015"

    result = normalize_legal_symbols(content)

    assert "Lei nº 13.105" in result


def test_normalize_legal_symbols_normalizes_day_of_month_ordinal() -> None:
    content = "de 1 o de janeiro de 1916"

    result = normalize_legal_symbols(content)

    assert "de 1º de janeiro de 1916" in result


def test_normalize_legal_symbols_normalizes_named_paragraph_ordinal() -> None:
    content = "No caso do parágrafo 2 o , reverterão..."

    result = normalize_legal_symbols(content)

    assert "No caso do parágrafo 2º, reverterão..." in result


def test_normalize_legal_symbols_preserves_unanchored_office_ordinal() -> None:
    content = "...ou, em sua falta, no 1 o Ofício da Capital do Estado..."

    result = normalize_legal_symbols(content)

    assert result == content


def test_normalize_legal_symbols_normalizes_promulgation_ordinals() -> None:
    content = "181 o da Independência e 114 o da República"

    result = normalize_legal_symbols(content)

    assert "181º da Independência e 114º da República" in result


def test_normalize_legal_symbols_normalizes_split_year_in_date() -> None:
    content = "de 1 o de janeiro de 191 6, poderá"

    result = normalize_legal_symbols(content)

    assert "de 1º de janeiro de 1916, poderá" in result


def test_normalize_legal_symbols_preserves_split_number_outside_date() -> None:
    content = "O identificador 191 6 permanece separado."

    result = normalize_legal_symbols(content)

    assert result == content


@pytest.mark.parametrize(
    "content",
    [
        "O prazo é de 10 outubro.",
        "O contrato prevê 5 obrigações.",
    ],
)
def test_normalize_legal_symbols_preserves_words_starting_with_o(
    content: str,
) -> None:
    result = normalize_legal_symbols(content)

    assert result == content


def test_normalize_legal_symbols_is_idempotent() -> None:
    content = "Art. 1º Toda pessoa é capaz..."

    normalized = normalize_legal_symbols(content)

    assert normalized == content
    assert normalize_legal_symbols(normalized) == normalized
