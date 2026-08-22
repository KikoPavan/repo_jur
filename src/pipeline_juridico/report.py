import hashlib
import json
import re
from dataclasses import asdict, replace
from pathlib import Path

from .hashing import get_runtime_info, sha256_file
from .models import (
    Metodo,
    OcrInfo,
    Relatorio,
    ResultadoInfo,
    ResultadoPagina,
    RuntimeInfo,
    StatusExecucao,
)


class ReportContractError(Exception):
    pass


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


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


def _validate_sha256(value: str, path: str) -> None:
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ReportContractError(f"Valor inválido em {path}")


def validate_report_contract(data: dict) -> None:
    _require_type(data, dict, "report")

    top_level_types = (
        ("schema_version", str),
        ("execution_id", str),
        ("input", dict),
        ("phase1", dict),
        ("result", dict),
        ("artifacts", dict),
        ("pages", list),
        ("telemetry", dict),
    )
    for field, expected_type in top_level_types:
        value = _require_field(data, field, field)
        _require_type(value, expected_type, field)

    if not data["execution_id"]:
        raise ReportContractError("Valor vazio em execution_id")

    _validate_object_fields(
        data["input"],
        "input",
        (("sha256", str), ("byte_size", int), ("page_count", int)),
    )
    _validate_sha256(data["input"]["sha256"], "input.sha256")
    if data["input"]["byte_size"] < 0 or data["input"]["page_count"] < 1:
        raise ReportContractError("Valor inválido em input")
    _validate_object_fields(
        data["phase1"], "phase1", (
            ("implementation", str),
            ("implementation_version", str),
            ("logical_processing_version", str),
            ("relevant_config_fingerprint", str),
        ),
    )
    phase1_fields = (
        "implementation",
        "implementation_version",
        "logical_processing_version",
        "relevant_config_fingerprint",
    )
    if any(not data["phase1"][name] for name in phase1_fields):
        raise ReportContractError("Valor vazio em phase1")
    _validate_object_fields(
        data["result"],
        "result",
        (("quality_gate", str), ("warnings", list), ("errors", list)),
    )
    if data["result"]["quality_gate"] not in {"PASS", "PASS_WITH_WARNINGS", "FAIL"}:
        raise ReportContractError("Valor inválido em result.quality_gate")
    _validate_object_fields(
        data["artifacts"], "artifacts", (("markdown_sha256", str),)
    )
    _validate_sha256(
        data["artifacts"]["markdown_sha256"],
        "artifacts.markdown_sha256",
    )

    allowed_methods = {method.value for method in Metodo}
    page_numbers: list[int] = []
    for index, page in enumerate(data["pages"]):
        page_path = f"pages[{index}]"
        _require_type(page, dict, page_path)
        page_fields = (
            ("page_number", int),
            ("method", str),
            ("char_count", int),
            ("warnings", list),
            ("errors", list),
            ("truncated", bool),
        )
        for field, expected_type in page_fields:
            field_path = f"{page_path}.{field}"
            value = _require_field(page, field, field_path)
            _require_type(value, expected_type, field_path)

        if page["method"] not in allowed_methods:
            raise ReportContractError(
                f"Valor inválido em {page_path}.method: {page['method']!r}"
            )
        if page["char_count"] < 0:
            raise ReportContractError(f"Valor inválido em {page_path}.char_count")
        page_numbers.append(page["page_number"])

    expected_numbers = list(range(1, data["input"]["page_count"] + 1))
    if (
        len(data["pages"]) != data["input"]["page_count"]
        or sorted(page_numbers) != expected_numbers
    ):
        raise ReportContractError("Inventário de páginas incompleto")


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
    page_number: int,
    method: Metodo,
    content: str,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    truncated: bool = False,
) -> ResultadoPagina:
    return ResultadoPagina(
        page_number=page_number,
        method=method,
        char_count=len(content),
        warnings=warnings or [],
        errors=errors or [],
        truncated=truncated,
    )


def ocr_page_numbers(pages: list[ResultadoPagina]) -> list[int]:
    return sorted(
        page.page_number
        for page in pages
        if page.method in (Metodo.ocr_integral, Metodo.hibrido)
    )


def determine_final_status(
    pages: list[ResultadoPagina],
    allow_partial: bool,
) -> StatusExecucao:
    has_failed_pages = any(
        page.method == Metodo.erro for page in pages
    )
    if not has_failed_pages:
        return StatusExecucao.sucesso
    if allow_partial:
        return StatusExecucao.incompleto
    return StatusExecucao.falha


def build_report_json(relatorio: Relatorio) -> str:
    return json.dumps(asdict(relatorio), ensure_ascii=False, indent=2)


def build_candidate_report_json(relatorio: Relatorio) -> str:
    payload = asdict(relatorio)
    payload.pop("result", None)
    return json.dumps(payload, ensure_ascii=False, indent=2)


def attach_gate_result(
    candidate: Relatorio,
    *,
    quality_gate: str,
    warnings: tuple = (),
    errors: tuple = (),
) -> Relatorio:
    return replace(
        candidate,
        result=ResultadoInfo(
            quality_gate=quality_gate,
            warnings=list(warnings),
            errors=list(errors),
        ),
    )


def compute_relevant_config_fingerprint(
    *, allow_partial: bool, use_ocr: bool, routing_config
) -> str:
    routing = asdict(routing_config) if routing_config is not None else {}
    payload = json.dumps(
        {
            "allow_partial": allow_partial,
            "routing_config": routing,
            "use_ocr": use_ocr,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


_TECHNICAL_ROUTING_METADATA = re.compile(
    r"^(\[\[Pág\. [1-9]\d*\]\]\r?\n)"
    r"<!-- método: (?:texto_nativo|ocr_integral|hibrido|vazia|erro) -->"
    r"(?:\r?\n|$)",
    re.MULTILINE,
)


def strip_technical_routing_metadata(markdown: str) -> str:
    return _TECHNICAL_ROUTING_METADATA.sub(r"\1", markdown)
