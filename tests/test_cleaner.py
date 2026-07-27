import re

import pytest

from pipeline_juridico.cleaner import (
    ILLEGIBLE_TEXT_MARKER,
    UnauthorizedIllegibleMarkerError,
    clean_markdown,
    ensure_illegible_marker_authorized,
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
