import pytest
from markitdown import MarkItDown

from pipeline_juridico.engines import (
    OcrConfigurationError,
    create_native_engine,
    create_ocr_engine,
    load_ocr_prompt,
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
