from types import SimpleNamespace

import fitz
import pytest

from pipeline_juridico.converter import convert_document
from pipeline_juridico.models import Metodo, StatusExecucao
from pipeline_juridico.validator import MarkdownValidationError


def _substantial_text(page_number: int) -> str:
    return (
        "Petição jurídica com conteúdo nativo substancial para assegurar a "
        "classificação correta da página pelo roteador, preservar os fatos e "
        f"fundamentos apresentados e identificar esta como a página {page_number}."
    )


def _build_digital_pdf(path) -> None:
    document = fitz.open()

    page = document.new_page()
    page.insert_text((50, 50), "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO")
    page.insert_text((50, 80), _substantial_text(1))
    page.insert_text((50, 110), "Processo nº 0001234-56.2020.8.26.0100")

    page = document.new_page()
    page.insert_text((50, 50), _substantial_text(2))
    page.insert_text((50, 80), "Documento datado de 26/07/2026.")
    page.insert_text(
        (50, 110),
        "Pedido formulado nos termos do art. 5º da Constituição Federal.",
    )

    page = document.new_page()
    page.insert_text((50, 50), _substantial_text(3))
    page.insert_text((50, 650), "_______________________")
    page.insert_text((50, 680), "João da Silva")
    page.insert_text((50, 710), "OAB/SP 123.456")

    document.save(path)
    document.close()


def _full_page_pixmap() -> fitz.Pixmap:
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pixmap.set_rect(pixmap.irect, (255, 255, 255))
    return pixmap


def _build_scanned_pdf(path, page_count=3) -> None:
    document = fitz.open()
    for _ in range(page_count):
        page = document.new_page()
        page.insert_image(page.rect, pixmap=_full_page_pixmap())
    document.save(path)
    document.close()


def _build_mixed_pdf(path) -> None:
    document = fitz.open()

    page = document.new_page()
    page.insert_text((50, 50), _substantial_text(1))

    page = document.new_page()
    page.insert_text((50, 50), _substantial_text(2))
    page.insert_image(page.rect, pixmap=_full_page_pixmap())

    page = document.new_page()
    page.insert_image(page.rect, pixmap=_full_page_pixmap())

    document.new_page()
    document.save(path)
    document.close()


class _FakeOcrClient:
    def __init__(self, text=None, error=None):
        self._text = text
        self._error = error
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    def _create(self, **_kwargs):
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._text),
                )
            ]
        )

    def convert(self, _path):
        response = self.chat.completions.create()
        return SimpleNamespace(
            text_content=response.choices[0].message.content,
        )


def _patch_successful_ocr(monkeypatch) -> None:
    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        lambda **_kwargs: _FakeOcrClient(
            text="Texto jurídico recuperado via OCR simulado desta página."
        ),
    )


def _convert(source, tmp_path, **kwargs):
    return convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        **kwargs,
    )


def test_9_1_fully_digital_pdf_never_calls_ocr(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "digital.pdf"
    _build_digital_pdf(source)

    def unexpected_ocr(**_kwargs):
        raise AssertionError(
            "OCR não deveria ser chamado para PDF totalmente digital"
        )

    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        unexpected_ocr,
    )

    _markdown, relatorio = _convert(source, tmp_path, use_ocr=True)

    assert all(not page.errors for page in relatorio.pages)
    assert all(
        page.method == Metodo.texto_nativo for page in relatorio.pages
    )


def test_9_2_fully_scanned_pdf_has_ocr_evidence_on_all_pages(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "scanned.pdf"
    _build_scanned_pdf(source)
    _patch_successful_ocr(monkeypatch)

    _markdown, relatorio = _convert(
        source,
        tmp_path,
        use_ocr=True,
        ocr_api_key="fake-key",
        ocr_model="fake-model",
    )

    assert all(not page.errors for page in relatorio.pages)
    assert len(relatorio.pages) == 3
    assert all(
        page.method == Metodo.ocr_integral and page.char_count > 0
        for page in relatorio.pages
    )


def test_9_3_mixed_pdf_records_each_page_method_correctly(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "mixed.pdf"
    _build_mixed_pdf(source)
    _patch_successful_ocr(monkeypatch)

    _markdown, relatorio = _convert(
        source,
        tmp_path,
        use_ocr=True,
        ocr_api_key="fake-key",
        ocr_model="fake-model",
    )

    assert [page.method for page in relatorio.pages] == [
        Metodo.texto_nativo,
        Metodo.hibrido,
        Metodo.ocr_integral,
        Metodo.vazia,
    ]
    assert all(not page.errors for page in relatorio.pages)


def test_9_4_page_count_matches_markdown_blocks_and_report(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "mixed.pdf"
    _build_mixed_pdf(source)
    _patch_successful_ocr(monkeypatch)

    markdown, relatorio = _convert(
        source,
        tmp_path,
        use_ocr=True,
        ocr_api_key="fake-key",
        ocr_model="fake-model",
    )

    assert len(relatorio.pages) == 4
    assert markdown.count("[[Pág. ") == 4
    assert [page.page_number for page in relatorio.pages] == [1, 2, 3, 4]


def test_9_5_ocr_failure_never_produces_global_success(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "scanned.pdf"
    _build_scanned_pdf(source, page_count=1)
    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        lambda **_kwargs: _FakeOcrClient(
            error=RuntimeError("falha OCR simulada")
        ),
    )

    with pytest.raises(MarkdownValidationError):
        _convert(
            source,
            tmp_path,
            use_ocr=True,
            ocr_api_key="fake-key",
            ocr_model="fake-model",
        )

    _markdown, relatorio = _convert(
        source,
        tmp_path,
        use_ocr=True,
        allow_partial=True,
        ocr_api_key="fake-key",
        ocr_model="fake-model",
    )

    assert relatorio.pages[0].method is Metodo.erro
    assert relatorio.pages[0].errors


def test_9_6_report_contains_source_output_hashes_and_versions(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "digital.pdf"
    _build_digital_pdf(source)
    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        lambda **_kwargs: pytest.fail("OCR inesperado"),
    )

    _markdown, relatorio = _convert(source, tmp_path, use_ocr=True)

    hexadecimal = set("0123456789abcdef")
    assert len(relatorio.input.sha256) == 64
    assert set(relatorio.input.sha256) <= hexadecimal
    assert len(relatorio.artifacts.markdown_sha256) == 64
    assert set(relatorio.artifacts.markdown_sha256) <= hexadecimal
    assert relatorio.telemetry["runtime"]["python"]
    assert relatorio.telemetry["runtime"]["markitdown"]
    assert relatorio.telemetry["runtime"]["markitdown_ocr"]
    assert relatorio.telemetry["runtime"]["pymupdf"]


def test_9_7_representative_legal_content_survives_conversion(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "digital.pdf"
    _build_digital_pdf(source)
    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        lambda **_kwargs: pytest.fail("OCR inesperado"),
    )

    markdown, _relatorio = _convert(source, tmp_path, use_ocr=True)

    assert "26/07/2026" in markdown
    assert "0001234-56.2020.8.26.0100" in markdown
    assert "nos termos do art. 5º da Constituição Federal" in markdown
    assert "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO" in markdown
    assert "_______________________" in markdown
    assert "João da Silva" in markdown
    assert "OAB/SP 123.456" in markdown
