import fitz
import pytest

import pipeline_juridico.converter as converter_module
from pipeline_juridico.converter import (
    PageBlock,
    _geometric_reading_order_text,
    _page_has_large_text,
    compose_document,
    convert_document,
    format_page_marker,
)
from pipeline_juridico.models import Metodo


VERTICAL_BLOCK_TEXT = "Registro digital genérico para teste."
HORIZONTAL_BODY_TEXT = (
    "Texto horizontal normal do corpo com conteúdo suficiente para que a "
    "página sintética seja classificada como texto nativo."
)


def _insert_rotated_text(
    page: fitz.Page,
    text: str = VERTICAL_BLOCK_TEXT,
    *,
    x: float = 550,
    y: float = 700,
) -> None:
    page.insert_text((x, y), text, fontsize=8, rotate=90)


def _save_native_pdf_with_duplicated_rotated_block(path) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)
        document.save(path)
    finally:
        document.close()


def test_has_duplicated_rotated_block_detects_overlapping_vertical_duplicate(
) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is True
    finally:
        document.close()


def test_geometric_reading_order_text_deduplicates_repeated_vertical_block(
) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        result = _geometric_reading_order_text(page)

        assert result.count(VERTICAL_BLOCK_TEXT) == 1
    finally:
        document.close()


def test_convert_document_avoids_single_character_noise_from_rotated_duplicate(
    tmp_path,
) -> None:
    source = tmp_path / "bloco-vertical-duplicado.pdf"
    _save_native_pdf_with_duplicated_rotated_block(source)

    markdown, _report = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    single_character_lines = [
        line for line in markdown.splitlines() if len(line.strip()) == 1
    ]
    assert len(single_character_lines) < 5


def test_convert_document_bypasses_native_engine_for_rotated_duplicate(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "bloco-vertical-duplicado.pdf"
    _save_native_pdf_with_duplicated_rotated_block(source)

    class FailingNativeEngine:
        def convert(self, _page_path):
            raise AssertionError(
                "MarkItDown não deveria ser chamado nesta página"
            )

    monkeypatch.setattr(
        converter_module,
        "create_native_engine",
        lambda: FailingNativeEngine(),
    )

    markdown, _report = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert VERTICAL_BLOCK_TEXT in markdown


def test_has_duplicated_rotated_block_single_legitimate_vertical_block(
) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_ignores_horizontal_duplicate() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_different_text_same_position() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page, "Primeiro registro vertical genérico.")
        _insert_rotated_text(page, "Segundo registro vertical genérico.")

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_bbox_beyond_tolerance() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page, y=720)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_bbox_within_tolerance() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page, y=701)

        assert converter_module._has_duplicated_rotated_block(page) is True
    finally:
        document.close()


def test_has_duplicated_rotated_block_absent_keeps_current_behavior() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_page_has_large_text_threshold_boundary() -> None:
    below_threshold_document = fitz.open()
    at_threshold_document = fitz.open()
    try:
        page_below_threshold = below_threshold_document.new_page()
        page_below_threshold.insert_text(
            (72, 72),
            "Texto abaixo do limiar",
            fontsize=19.9,
        )
        page_at_threshold = at_threshold_document.new_page()
        page_at_threshold.insert_text(
            (72, 72),
            "Texto no limiar",
            fontsize=20.0,
        )

        assert _page_has_large_text(page_below_threshold) is False
        assert _page_has_large_text(page_at_threshold) is True
    finally:
        below_threshold_document.close()
        at_threshold_document.close()


def test_format_page_marker_texto_nativo() -> None:
    assert (
        format_page_marker(1, Metodo.texto_nativo)
        == "[[Pág. 1]]\n<!-- método: texto_nativo -->"
    )


def test_format_page_marker_different_number_and_method() -> None:
    assert (
        format_page_marker(42, Metodo.ocr_integral)
        == "[[Pág. 42]]\n<!-- método: ocr_integral -->"
    )


@pytest.mark.parametrize("method", list(Metodo))
def test_format_page_marker_preserves_exact_method_value(method: Metodo) -> None:
    assert format_page_marker(1, method) == (
        f"[[Pág. 1]]\n<!-- método: {method.value} -->"
    )


def test_compose_document_single_block() -> None:
    result = compose_document(
        [
            PageBlock(
                number=1,
                method=Metodo.texto_nativo,
                content="Conteúdo da página um.",
            )
        ]
    )

    marker_index = result.index("[[Pág. 1]]")
    method_index = result.index("<!-- método: texto_nativo -->")
    content_index = result.index("Conteúdo da página um.")

    assert marker_index < method_index < content_index


def test_compose_document_orders_by_number_even_if_input_unordered() -> None:
    blocks = [
        PageBlock(3, Metodo.texto_nativo, "Página três."),
        PageBlock(1, Metodo.texto_nativo, "Página um."),
        PageBlock(2, Metodo.texto_nativo, "Página dois."),
    ]

    result = compose_document(blocks)

    assert (
        result.index("[[Pág. 1]]")
        < result.index("[[Pág. 2]]")
        < result.index("[[Pág. 3]]")
    )


def test_compose_document_separates_pages_without_leaking_context() -> None:
    blocks = [
        PageBlock(1, Metodo.texto_nativo, "- item a\n- item b"),
        PageBlock(2, Metodo.texto_nativo, "- item c"),
    ]

    result = compose_document(blocks)

    assert "- item b\n\n[[Pág. 2]]" in result


def test_compose_document_handles_empty_page_content() -> None:
    result = compose_document([PageBlock(1, Metodo.vazia, "")])

    assert "[[Pág. 1]]" in result
    assert "<!-- método: vazia -->" in result
