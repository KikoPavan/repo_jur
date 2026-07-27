from types import SimpleNamespace

import fitz
import pytest

from pipeline_juridico.cleaner import ILLEGIBLE_TEXT_MARKER
from pipeline_juridico.converter import convert_document
from pipeline_juridico.engines import OcrConfigurationError
from pipeline_juridico.models import Metodo, Relatorio, StatusExecucao
from pipeline_juridico.validator import MarkdownValidationError


def _create_native_pdf(path, page_count: int = 2) -> None:
    document = fitz.open()
    for number in range(1, page_count + 1):
        page = document.new_page()
        page.insert_text(
            (50, 50),
            "Conteúdo jurídico nativo suficientemente longo para superar o "
            f"limite mínimo de caracteres úteis da página {number}.",
        )
    document.save(path)
    document.close()


def _create_scanned_pdf(path) -> None:
    document = fitz.open()
    page = document.new_page()
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pixmap.set_rect(pixmap.irect, (255, 0, 0))
    page.insert_image(page.rect, pixmap=pixmap)
    document.save(path)
    document.close()


def test_convert_document_all_native_pages(tmp_path) -> None:
    source = tmp_path / "nativo.pdf"
    _create_native_pdf(source)

    result = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        allow_partial=False,
        use_ocr=True,
    )

    assert isinstance(result, tuple)
    markdown, relatorio = result
    assert isinstance(markdown, str)
    assert isinstance(relatorio, Relatorio)
    assert "[[Pág. 1]]" in markdown
    assert "[[Pág. 2]]" in markdown
    assert relatorio.status == StatusExecucao.sucesso
    assert len(relatorio.pages) == 2
    assert all(
        page.method == Metodo.texto_nativo for page in relatorio.pages
    )


def test_convert_document_with_ocr_page_success(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)
    simulated_text = "Texto extraído com sucesso pelo OCR simulado."
    fake_engine = SimpleNamespace(
        convert=lambda _path: SimpleNamespace(text_content=simulated_text)
    )
    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        lambda **_kwargs: fake_engine,
    )

    markdown, relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=True,
        ocr_api_key="fake-key-for-tests",
        ocr_model="gemini-2.0-flash",
    )

    assert relatorio.status == StatusExecucao.sucesso
    assert relatorio.pages[0].method == Metodo.ocr_integral
    assert simulated_text in markdown


def test_convert_document_ocr_needed_but_no_ocr_flag(tmp_path) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)

    with pytest.raises(MarkdownValidationError):
        convert_document(
            pdf_path=source,
            output_path=tmp_path / "saida.md",
            temp_root=tmp_path / "temp",
            use_ocr=False,
        )


def test_convert_document_ocr_needed_no_ocr_flag_with_allow_partial(
    tmp_path,
) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)

    markdown, relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
        allow_partial=True,
    )

    assert relatorio.status == StatusExecucao.incompleto
    assert ILLEGIBLE_TEXT_MARKER in markdown


def test_convert_document_missing_ocr_config_raises(tmp_path) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)

    with pytest.raises(OcrConfigurationError):
        convert_document(
            pdf_path=source,
            output_path=tmp_path / "saida.md",
            temp_root=tmp_path / "temp",
            use_ocr=True,
        )
