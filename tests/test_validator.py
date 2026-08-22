from pathlib import Path

import pytest

import pipeline_juridico.validator as validator_module
from pipeline_juridico.converter import PageBlock, format_page_marker
from pipeline_juridico.models import Metodo, ResultadoPagina
from pipeline_juridico.validator import (
    MarkdownValidationError,
    OutputAlreadyExistsError,
    validate_encoding_and_line_endings,
    validate_markdown_matches_report,
    validate_page_content,
    validate_page_markers,
    write_atomic,
)


def _page(number: int, method: Metodo = Metodo.texto_nativo) -> str:
    return f"{format_page_marker(number, method)}\n\nConteúdo da página {number}"


def _result(number: int, method: Metodo) -> ResultadoPagina:
    return ResultadoPagina(
        page_number=number,
        method=method,
        char_count=10,
        warnings=[],
        errors=[],
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


def test_write_atomic_creates_file_with_content(tmp_path):
    content = "conteúdo de teste\n"
    destination = tmp_path / "saida" / "documento.md"

    write_atomic(content, destination, tmp_path / "temp")

    assert destination.exists()
    assert Path(destination).read_text(encoding="utf-8") == content


def test_write_atomic_creates_parent_directories(tmp_path):
    destination = tmp_path / "a" / "b" / "c.md"
    temp_dir = tmp_path / "temp" / "run"

    write_atomic("conteúdo\n", destination, temp_dir)

    assert destination.parent.is_dir()
    assert temp_dir.is_dir()


def test_write_atomic_leaves_no_leftover_temp_files(tmp_path):
    destination = tmp_path / "saida" / "documento.md"
    temp_dir = tmp_path / "temp"

    write_atomic("conteúdo\n", destination, temp_dir)

    assert list(temp_dir.iterdir()) == []


def test_write_atomic_raises_when_destination_exists_and_not_overwrite(tmp_path):
    destination = tmp_path / "documento.md"
    destination.write_text("conteúdo antigo\n", encoding="utf-8")

    with pytest.raises(OutputAlreadyExistsError):
        write_atomic("conteúdo novo\n", destination, tmp_path / "temp")

    assert destination.read_text(encoding="utf-8") == "conteúdo antigo\n"


def test_write_atomic_overwrites_when_overwrite_true(tmp_path):
    destination = tmp_path / "documento.md"
    destination.write_text("conteúdo antigo\n", encoding="utf-8")

    write_atomic(
        "conteúdo novo\n",
        destination,
        tmp_path / "temp",
        overwrite=True,
    )

    assert destination.read_text(encoding="utf-8") == "conteúdo novo\n"


def test_write_atomic_preserves_existing_output_when_write_fails(tmp_path):
    previous_content = "conteúdo válido anterior\n"
    destination = tmp_path / "documento.md"
    temp_dir = tmp_path / "temp"
    destination.write_text(previous_content, encoding="utf-8")

    with pytest.raises(UnicodeEncodeError):
        write_atomic(
            "texto com surrogate: \udcff\n",
            destination,
            temp_dir,
            overwrite=True,
        )

    assert destination.read_text(encoding="utf-8") == previous_content
    assert list(temp_dir.iterdir()) == []


def test_write_atomic_preserves_existing_output_when_replace_fails(
    tmp_path,
    monkeypatch,
):
    previous_content = "conteúdo válido anterior\n"
    destination = tmp_path / "documento.md"
    temp_dir = tmp_path / "temp"
    destination.write_text(previous_content, encoding="utf-8")

    def fail_replace(*args, **kwargs):
        raise OSError("falha simulada de renomeação")

    monkeypatch.setattr(validator_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="falha simulada de renomeação"):
        write_atomic(
            "conteúdo novo válido\n",
            destination,
            temp_dir,
            overwrite=True,
        )

    assert destination.read_text(encoding="utf-8") == previous_content
    assert list(temp_dir.iterdir()) == []


def test_write_atomic_does_not_create_destination_on_failure_when_no_prior_output(
    tmp_path,
):
    destination = tmp_path / "documento.md"
    temp_dir = tmp_path / "temp"

    with pytest.raises(UnicodeEncodeError):
        write_atomic(
            "texto com surrogate: \udcff\n",
            destination,
            temp_dir,
        )

    assert not destination.exists()
