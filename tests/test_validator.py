import pytest

from pipeline_juridico.converter import PageBlock, format_page_marker
from pipeline_juridico.models import Metodo, ResultadoPagina, StatusExecucao
from pipeline_juridico.validator import (
    MarkdownValidationError,
    validate_encoding_and_line_endings,
    validate_markdown_matches_report,
    validate_page_content,
    validate_page_markers,
)


def _page(number: int, method: Metodo = Metodo.texto_nativo) -> str:
    return f"{format_page_marker(number, method)}\n\nConteúdo da página {number}"


def _result(number: int, method: Metodo) -> ResultadoPagina:
    return ResultadoPagina(
        number=number,
        method=method,
        status=StatusExecucao.sucesso,
        characters=10,
        duration_ms=5,
        warnings=[],
        error=None,
    )


def test_validate_encoding_and_line_endings_accepts_valid_text():
    text = "Texto válido em português com acentuação: ção, ã, é.\n"

    validate_encoding_and_line_endings(text)


def test_validate_encoding_and_line_endings_rejects_carriage_return():
    text = "Texto com CRLF.\r\n"

    with pytest.raises(MarkdownValidationError):
        validate_encoding_and_line_endings(text)


def test_validate_encoding_and_line_endings_rejects_missing_trailing_newline():
    text = "Texto sem quebra final"

    with pytest.raises(MarkdownValidationError):
        validate_encoding_and_line_endings(text)


def test_validate_encoding_and_line_endings_rejects_multiple_trailing_newlines():
    text = "Texto com quebras finais em excesso.\n\n"

    with pytest.raises(MarkdownValidationError):
        validate_encoding_and_line_endings(text)


def test_validate_encoding_and_line_endings_accepts_empty_string():
    validate_encoding_and_line_endings("")


def test_validate_encoding_and_line_endings_rejects_undecodable_surrogate():
    text = "texto com surrogate: \udcff\n"

    with pytest.raises(MarkdownValidationError):
        validate_encoding_and_line_endings(text)


def test_validate_markdown_matches_report_accepts_matching_data():
    markdown = "\n\n".join(
        [
            _page(1, Metodo.texto_nativo),
            _page(2, Metodo.ocr_integral),
        ]
    )
    pages = [
        _result(1, Metodo.texto_nativo),
        _result(2, Metodo.ocr_integral),
    ]

    validate_markdown_matches_report(markdown, pages)


def test_validate_markdown_matches_report_rejects_page_missing_in_report():
    markdown = "\n\n".join(
        [
            _page(1, Metodo.texto_nativo),
            _page(2, Metodo.ocr_integral),
        ]
    )
    pages = [_result(1, Metodo.texto_nativo)]

    with pytest.raises(MarkdownValidationError):
        validate_markdown_matches_report(markdown, pages)


def test_validate_markdown_matches_report_rejects_page_missing_in_markdown():
    markdown = _page(1, Metodo.texto_nativo)
    pages = [
        _result(1, Metodo.texto_nativo),
        _result(2, Metodo.ocr_integral),
    ]

    with pytest.raises(MarkdownValidationError):
        validate_markdown_matches_report(markdown, pages)


def test_validate_markdown_matches_report_rejects_method_mismatch():
    markdown = _page(1, Metodo.texto_nativo)
    pages = [_result(1, Metodo.ocr_integral)]

    with pytest.raises(MarkdownValidationError):
        validate_markdown_matches_report(markdown, pages)


def test_validate_page_markers_accepts_valid_sequence():
    markdown = "\n\n".join(
        [
            _page(1, Metodo.texto_nativo),
            _page(2, Metodo.ocr_integral),
            _page(3, Metodo.hibrido),
        ]
    )

    validate_page_markers(markdown, 3)


def test_validate_page_markers_rejects_wrong_count():
    markdown = "\n\n".join([_page(1), _page(2)])

    with pytest.raises(MarkdownValidationError):
        validate_page_markers(markdown, 3)


def test_validate_page_markers_rejects_out_of_order():
    markdown = "\n\n".join([_page(1), _page(3), _page(2)])

    with pytest.raises(MarkdownValidationError):
        validate_page_markers(markdown, 3)


def test_validate_page_markers_rejects_gap_in_sequence():
    markdown = "\n\n".join([_page(1), _page(2), _page(4)])

    with pytest.raises(MarkdownValidationError):
        validate_page_markers(markdown, 3)


def test_validate_page_markers_rejects_duplicate_page_number():
    markdown = "\n\n".join([_page(1), _page(2), _page(2)])

    with pytest.raises(MarkdownValidationError):
        validate_page_markers(markdown, 3)


def test_validate_page_markers_rejects_marker_without_method_comment():
    markdown = "\n\n".join(
        [
            _page(1),
            "[[Pág. 2]]\n\nConteúdo da página 2",
            _page(3),
        ]
    )

    with pytest.raises(MarkdownValidationError):
        validate_page_markers(markdown, 3)


def test_validate_page_content_accepts_valid_blocks():
    blocks = [
        PageBlock(1, Metodo.texto_nativo, "Conteúdo nativo"),
        PageBlock(2, Metodo.ocr_integral, "Conteúdo OCR"),
        PageBlock(3, Metodo.hibrido, "Conteúdo híbrido"),
        PageBlock(4, Metodo.vazia, ""),
    ]

    validate_page_content(blocks)


def test_validate_page_content_rejects_erro_in_strict_mode():
    blocks = [PageBlock(1, Metodo.erro, "")]

    with pytest.raises(MarkdownValidationError):
        validate_page_content(blocks, strict=True)


def test_validate_page_content_allows_erro_when_not_strict():
    blocks = [PageBlock(1, Metodo.erro, "")]

    validate_page_content(blocks, strict=False)


def test_validate_page_content_rejects_vazia_with_content():
    blocks = [
        PageBlock(1, Metodo.vazia, "Texto que não deveria estar aqui"),
    ]

    with pytest.raises(MarkdownValidationError):
        validate_page_content(blocks)


def test_validate_page_content_rejects_texto_nativo_without_content():
    blocks = [PageBlock(1, Metodo.texto_nativo, "   ")]

    with pytest.raises(MarkdownValidationError):
        validate_page_content(blocks)


@pytest.mark.parametrize("method", [Metodo.ocr_integral, Metodo.hibrido])
def test_validate_page_content_rejects_ocr_methods_without_content(method):
    blocks = [PageBlock(1, method, "   ")]

    with pytest.raises(MarkdownValidationError):
        validate_page_content(blocks)
