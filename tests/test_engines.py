from types import SimpleNamespace

import fitz
import pytest
from markitdown import MarkItDown

from pipeline_juridico.engines import (
    OcrConfigurationError,
    create_native_engine,
    create_ocr_engine,
    load_ocr_prompt,
    scan_ocr_warnings,
    verify_ocr_evidence,
)
from pipeline_juridico.models import Metodo


class _SuccessfulOcrClient:
    class _Completions:
        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=(
                                "Texto extraído com sucesso pelo OCR simulado."
                            )
                        )
                    )
                ]
            )

    def __init__(self):
        self.chat = SimpleNamespace(completions=self._Completions())


class _FailureWarningOcrClient:
    class _Completions:
        def create(self, **kwargs):
            raise RuntimeError("falha simulada da API")

    def __init__(self):
        self.chat = SimpleNamespace(completions=self._Completions())


class _EmptyResponseOcrClient:
    class _Completions:
        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="")
                    )
                ]
            )

    def __init__(self):
        self.chat = SimpleNamespace(completions=self._Completions())


class _TimeoutOcrClient:
    class _Completions:
        def create(self, **kwargs):
            raise TimeoutError("tempo esgotado")

    def __init__(self):
        self.chat = SimpleNamespace(completions=self._Completions())


class _ModelUnavailableOcrClient:
    class _Completions:
        def create(self, **kwargs):
            raise RuntimeError("model not found")

    def __init__(self):
        self.chat = SimpleNamespace(completions=self._Completions())


@pytest.fixture
def scanned_pdf_for_ocr(tmp_path):
    source = tmp_path / "pagina_digitalizada.pdf"
    document = fitz.open()
    page = document.new_page()
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pixmap.set_rect(pixmap.irect, (255, 0, 0))
    page.insert_image(page.rect, pixmap=pixmap)
    document.save(source)
    document.close()

    # Aciona o fallback de página inteira do plugin sem invalidar o PDF no PyMuPDF.
    source.write_bytes(source.read_bytes()[:-20])
    return source


def _ocr_engine_with(client):
    return MarkItDown(
        enable_plugins=True,
        llm_client=client,
        llm_model="fake-model",
        llm_prompt="Transcreva literalmente o texto da imagem.",
    )


def test_create_native_engine_converts_plain_text(tmp_path):
    source = tmp_path / "documento.txt"
    source.write_text("Conteúdo jurídico simples.", encoding="utf-8")

    engine = create_native_engine()
    result = engine.convert(source)

    assert isinstance(engine, MarkItDown)
    assert result.text_content
    assert "Conteúdo jurídico simples." in result.text_content


def test_load_ocr_prompt_reads_file():
    prompt = load_ocr_prompt()

    assert prompt
    assert "ilegível" in prompt


def test_create_ocr_engine_returns_markitdown_instance():
    engine = create_ocr_engine(
        api_key="fake-key-for-tests",
        model="gemini-2.0-flash",
        prompt="prompt de teste",
    )

    assert isinstance(engine, MarkItDown)


def test_create_ocr_engine_raises_when_api_key_missing():
    with pytest.raises(OcrConfigurationError) as exc_info:
        create_ocr_engine(api_key=None, model="gemini-2.0-flash")

    message = str(exc_info.value)
    assert "GEMINI_API_KEY ausente" in message
    assert "None" not in message


def test_create_ocr_engine_raises_when_api_key_empty():
    with pytest.raises(OcrConfigurationError) as exc_info:
        create_ocr_engine(api_key="", model="gemini-2.0-flash")

    message = str(exc_info.value)
    assert "GEMINI_API_KEY ausente" in message
    assert "None" not in message


def test_create_ocr_engine_raises_when_model_missing():
    with pytest.raises(OcrConfigurationError) as exc_info:
        create_ocr_engine(api_key="fake-key-for-tests", model=None)

    message = str(exc_info.value)
    assert "modelo (GEMINI_MODEL) ausente" in message
    assert "fake-key-for-tests" not in message


def test_create_ocr_engine_raises_when_both_missing():
    with pytest.raises(OcrConfigurationError) as exc_info:
        create_ocr_engine(api_key=None, model=None)

    message = str(exc_info.value)
    assert "GEMINI_API_KEY ausente" in message
    assert "modelo (GEMINI_MODEL) ausente" in message
    assert "None" not in message


def test_scan_ocr_warnings_detects_no_text_marker():
    markdown = (
        "algum texto \n\n"
        "*[No text could be extracted from this page]*\n\n"
        " mais texto"
    )

    warnings = scan_ocr_warnings(markdown)

    assert warnings
    assert all("No text could be extracted" not in warning for warning in warnings)


def test_scan_ocr_warnings_detects_page_error_marker_and_sanitizes():
    markdown = (
        "*[Error processing page 3: "
        "FileNotFoundError: /home/user/secreto/documento.pdf]*"
    )

    warnings = scan_ocr_warnings(markdown)

    assert warnings
    assert all(
        "/home/user/secreto/documento.pdf" not in warning for warning in warnings
    )
    assert all("FileNotFoundError" not in warning for warning in warnings)


def test_scan_ocr_warnings_detects_fatal_marker():
    markdown = "*[Error: Could not process scanned PDF]*"

    warnings = scan_ocr_warnings(markdown)

    assert warnings


def test_scan_ocr_warnings_returns_empty_for_clean_markdown():
    markdown = "Texto jurídico normal, sem nenhum marcador de falha."

    warnings = scan_ocr_warnings(markdown)

    assert warnings == []


def test_verify_ocr_evidence_passes_through_texto_nativo():
    markdown_samples = (
        "qualquer coisa",
        "",
        "*[No text could be extracted from this page]*",
    )

    for markdown in markdown_samples:
        result = verify_ocr_evidence(markdown, Metodo.texto_nativo)

        assert result == (Metodo.texto_nativo, [])


def test_verify_ocr_evidence_accepts_valid_ocr_content():
    result = verify_ocr_evidence(
        "Texto jurídico obtido por OCR.",
        Metodo.ocr_integral,
    )

    assert result == (Metodo.ocr_integral, [])


def test_verify_ocr_evidence_promotes_to_erro_on_empty_markdown():
    method, warnings = verify_ocr_evidence("   ", Metodo.ocr_integral)

    assert method is Metodo.erro
    assert warnings


def test_verify_ocr_evidence_promotes_to_erro_on_failure_marker():
    raw_marker = "*[No text could be extracted from this page]*"

    method, warnings = verify_ocr_evidence(raw_marker, Metodo.hibrido)

    assert method is Metodo.erro
    assert warnings
    assert all(raw_marker not in warning for warning in warnings)


def test_ocr_engine_simulated_success(scanned_pdf_for_ocr):
    engine = _ocr_engine_with(_SuccessfulOcrClient())

    markdown = engine.convert(scanned_pdf_for_ocr).text_content

    assert "Texto extraído com sucesso pelo OCR simulado." in markdown
    assert scan_ocr_warnings(markdown) == []


def test_ocr_engine_simulated_failure_warning_only(scanned_pdf_for_ocr):
    engine = _ocr_engine_with(_FailureWarningOcrClient())

    # A raiz difere, mas falhas são OCR vazio/marcador por design do plugin.
    markdown = engine.convert(scanned_pdf_for_ocr).text_content
    warnings = scan_ocr_warnings(markdown)

    assert warnings
    assert all("falha simulada da API" not in warning for warning in warnings)


def test_ocr_engine_simulated_empty_response(scanned_pdf_for_ocr):
    engine = _ocr_engine_with(_EmptyResponseOcrClient())

    # A raiz difere, mas falhas são OCR vazio/marcador por design do plugin.
    markdown = engine.convert(scanned_pdf_for_ocr).text_content
    method, warnings = verify_ocr_evidence(markdown, Metodo.ocr_integral)

    assert method is Metodo.erro
    assert warnings


def test_ocr_engine_simulated_timeout(scanned_pdf_for_ocr):
    engine = _ocr_engine_with(_TimeoutOcrClient())

    # A raiz difere, mas falhas são OCR vazio/marcador por design do plugin.
    markdown = engine.convert(scanned_pdf_for_ocr).text_content
    method, warnings = verify_ocr_evidence(markdown, Metodo.ocr_integral)

    assert method is Metodo.erro
    assert warnings


def test_ocr_engine_simulated_model_unavailable(scanned_pdf_for_ocr):
    engine = _ocr_engine_with(_ModelUnavailableOcrClient())

    # A raiz difere, mas falhas são OCR vazio/marcador por design do plugin.
    markdown = engine.convert(scanned_pdf_for_ocr).text_content
    method, warnings = verify_ocr_evidence(markdown, Metodo.ocr_integral)

    assert method is Metodo.erro
    assert warnings
