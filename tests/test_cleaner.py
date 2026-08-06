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
    normalize_legal_symbols,
    recompose_native_paragraphs,
    remove_repetitive_margins,
)


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


def test_remove_repetitive_margins_preserves_repeated_legal_header() -> None:
    legal_header = "Superior Tribunal de Justiça"
    pages = [
        (
            f"[[Pág. {page_number}]]\n"
            "<!-- método: texto_nativo -->\n"
            f"{legal_header}\n"
            f"Conteúdo jurídico exclusivo da página {page_number}."
        )
        for page_number in range(1, 6)
    ]

    result = remove_repetitive_margins("\n".join(pages))

    assert result.count(legal_header) == len(pages)
    for page_number in range(1, 6):
        page = result.split(f"[[Pág. {page_number}]]", maxsplit=1)[1]
        assert (
            f"<!-- método: texto_nativo -->\n{legal_header}\n"
            in page
        )


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

    assert result == content


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
