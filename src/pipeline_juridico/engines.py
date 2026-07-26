from pathlib import Path

from markitdown import MarkItDown
from openai import OpenAI


def create_native_engine() -> MarkItDown:
    return MarkItDown(enable_plugins=False)


def load_ocr_prompt(
    path: str | Path = "prompts/ocr_literal_ptbr.txt",
) -> str:
    return Path(path).read_text(encoding="utf-8")


def create_ocr_engine(
    api_key: str,
    model: str,
    base_url: str | None = None,
    prompt: str | None = None,
) -> MarkItDown:
    client = OpenAI(api_key=api_key, base_url=base_url)
    return MarkItDown(
        enable_plugins=True,
        llm_client=client,
        llm_model=model,
        llm_prompt=prompt,
    )
