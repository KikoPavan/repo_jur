from pathlib import Path

from markitdown import MarkItDown
from openai import OpenAI


class OcrConfigurationError(Exception):
    pass


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
