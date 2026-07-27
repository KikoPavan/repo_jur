import json
from dataclasses import asdict
from pathlib import Path

from .hashing import get_runtime_info, sha256_file
from .models import (
    Metodo,
    OcrInfo,
    Relatorio,
    ResultadoPagina,
    RuntimeInfo,
    StatusExecucao,
)


def build_runtime_info() -> RuntimeInfo:
    return get_runtime_info()


def build_ocr_info(
    enabled: bool,
    provider: str,
    model: str,
    prompt_path: str | Path,
) -> OcrInfo:
    return OcrInfo(
        enabled=enabled,
        provider=provider,
        model=model,
        prompt_sha256=sha256_file(prompt_path),
    )


def build_page_result(
    number: int,
    method: Metodo,
    status: StatusExecucao,
    content: str,
    duration_ms: int,
    warnings: list[str] | None = None,
    error: str | None = None,
) -> ResultadoPagina:
    return ResultadoPagina(
        number=number,
        method=method,
        status=status,
        characters=len(content),
        duration_ms=duration_ms,
        warnings=warnings or [],
        error=error,
    )


def ocr_page_numbers(pages: list[ResultadoPagina]) -> list[int]:
    return sorted(
        page.number
        for page in pages
        if page.method in (Metodo.ocr_integral, Metodo.hibrido)
    )


def build_report_json(relatorio: Relatorio) -> str:
    return json.dumps(asdict(relatorio), ensure_ascii=False, indent=2)
