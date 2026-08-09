import fitz
import pytest

from pipeline_juridico.converter import (
    PageBlock,
    _page_has_large_text,
    compose_document,
    format_page_marker,
)
from pipeline_juridico.models import Metodo


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
