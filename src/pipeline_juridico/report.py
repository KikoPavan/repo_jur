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


class ReportContractError(Exception):
    pass


def _require_field(data: dict, field: str, path: str) -> object:
    if field not in data:
        raise ReportContractError(f"Campo obrigatório ausente: {path}")
    return data[field]


def _require_type(value: object, expected_type: type, path: str) -> None:
    if type(value) is not expected_type:
        raise ReportContractError(
            f"Tipo incorreto em {path}: esperado "
            f"{expected_type.__name__}, recebido {type(value).__name__}"
        )


def _validate_object_fields(
    data: object,
    path: str,
    fields: tuple[tuple[str, type], ...],
) -> None:
    _require_type(data, dict, path)
    for field, expected_type in fields:
        field_path = f"{path}.{field}"
        value = _require_field(data, field, field_path)
        _require_type(value, expected_type, field_path)


def validate_report_contract(data: dict) -> None:
    _require_type(data, dict, "report")

    top_level_types = (
        ("schema_version", str),
        ("run_id", str),
        ("status", str),
        ("source", dict),
        ("output", dict),
        ("runtime", dict),
        ("ocr", dict),
        ("timing", dict),
        ("pages", list),
    )
    for field, expected_type in top_level_types:
        value = _require_field(data, field, field)
        _require_type(value, expected_type, field)

    allowed_statuses = {status.value for status in StatusExecucao}
    if data["status"] not in allowed_statuses:
        raise ReportContractError(
            f"Valor inválido em status: {data['status']!r}"
        )

    _validate_object_fields(
        data["source"],
        "source",
        (
            ("path", str),
            ("size_bytes", int),
            ("sha256", str),
            ("pages", int),
        ),
    )
    _validate_object_fields(
        data["output"],
        "output",
        (("path", str), ("sha256", str)),
    )
    _validate_object_fields(
        data["runtime"],
        "runtime",
        (
            ("python", str),
            ("markitdown", str),
            ("markitdown_ocr", str),
            ("pymupdf", str),
        ),
    )
    _validate_object_fields(
        data["ocr"],
        "ocr",
        (
            ("enabled", bool),
            ("provider", str),
            ("model", str),
            ("prompt_sha256", str),
        ),
    )
    _validate_object_fields(
        data["timing"],
        "timing",
        (
            ("started_at", str),
            ("finished_at", str),
            ("duration_ms", int),
        ),
    )

    allowed_methods = {method.value for method in Metodo}
    for index, page in enumerate(data["pages"]):
        page_path = f"pages[{index}]"
        _require_type(page, dict, page_path)
        page_fields = (
            ("number", int),
            ("method", str),
            ("status", str),
            ("characters", int),
            ("duration_ms", int),
            ("warnings", list),
        )
        for field, expected_type in page_fields:
            field_path = f"{page_path}.{field}"
            value = _require_field(page, field, field_path)
            _require_type(value, expected_type, field_path)

        error_path = f"{page_path}.error"
        error = _require_field(page, "error", error_path)
        if error is not None:
            _require_type(error, str, error_path)

        if page["method"] not in allowed_methods:
            raise ReportContractError(
                f"Valor inválido em {page_path}.method: {page['method']!r}"
            )
        if page["status"] not in allowed_statuses:
            raise ReportContractError(
                f"Valor inválido em {page_path}.status: {page['status']!r}"
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


def determine_final_status(
    pages: list[ResultadoPagina],
    allow_partial: bool,
) -> StatusExecucao:
    has_failed_pages = any(
        page.status == StatusExecucao.falha for page in pages
    )
    if not has_failed_pages:
        return StatusExecucao.sucesso
    if allow_partial:
        return StatusExecucao.incompleto
    return StatusExecucao.falha


def build_report_json(relatorio: Relatorio) -> str:
    return json.dumps(asdict(relatorio), ensure_ascii=False, indent=2)
