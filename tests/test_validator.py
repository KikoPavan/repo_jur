import pytest

from pipeline_juridico.converter import format_page_marker
from pipeline_juridico.models import Metodo
from pipeline_juridico.validator import (
    MarkdownValidationError,
    validate_page_markers,
)


def _page(number: int, method: Metodo = Metodo.texto_nativo) -> str:
    return f"{format_page_marker(number, method)}\n\nConteúdo da página {number}"


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
