import re

import pytest

from pipeline_juridico.cleaner import (
    ILLEGIBLE_TEXT_MARKER,
    UnauthorizedIllegibleMarkerError,
    clean_markdown,
    ensure_illegible_marker_authorized,
    recompose_native_paragraphs,
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
