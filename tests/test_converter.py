import pytest

from pipeline_juridico.converter import format_page_marker
from pipeline_juridico.models import Metodo


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
