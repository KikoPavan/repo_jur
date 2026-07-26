from pathlib import Path

from markitdown import MarkItDown
from openai import OpenAI


OCR_NO_TEXT_MARKER = "[No text could be extracted from this page]"
OCR_PAGE_ERROR_MARKER = "[Error processing page"
OCR_FATAL_ERROR_MARKER = "[Error: Could not process scanned PDF]"


class OcrConfigurationError(Exception):
    pass


def sanitize_ocr_error(marker: str) -> str:
    messages = {
        OCR_NO_TEXT_MARKER: (
            "Falha na chamada de OCR: evidência de texto não foi obtida "
            "para esta página."
        ),
        OCR_PAGE_ERROR_MARKER: (
            "Falha na chamada de OCR: não foi possível processar esta página."
        ),
        OCR_FATAL_ERROR_MARKER: (
            "Falha na chamada de OCR: não foi possível processar o PDF "
            "digitalizado."
        ),
    }
    return messages.get(marker, "Falha técnica durante o processamento de OCR.")


def scan_ocr_warnings(markdown: str) -> list[str]:
    markers = (
        OCR_NO_TEXT_MARKER,
        OCR_PAGE_ERROR_MARKER,
        OCR_FATAL_ERROR_MARKER,
    )
    return [
        sanitize_ocr_error(marker)
        for marker in markers
        if marker in markdown
    ]


def create_native_engine() -> MarkItDown:
    return MarkItDown(enable_plugins=False)


def load_ocr_prompt(
    path: str | Path = "prompts/ocr_literal_ptbr.txt",
) -> str:
    return Path(path).read_text(encoding="utf-8")


def create_ocr_engine(
    api_key: str | None,
    model: str | None,
    base_url: str | None = None,
    prompt: str | None = None,
) -> MarkItDown:
    missing_items = []
    if api_key is None or not api_key.strip():
        missing_items.append("GEMINI_API_KEY ausente")
    if model is None or not model.strip():
        missing_items.append("modelo (GEMINI_MODEL) ausente")
    if missing_items:
        raise OcrConfigurationError(
            f"Configuração de OCR incompleta: {', '.join(missing_items)}"
        )

    client = OpenAI(api_key=api_key, base_url=base_url)
    return MarkItDown(
        enable_plugins=True,
        llm_client=client,
        llm_model=model,
        llm_prompt=prompt,
    )
