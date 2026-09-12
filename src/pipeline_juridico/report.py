import hashlib
import json
import re
from dataclasses import asdict, replace
from pathlib import Path

from .hashing import get_runtime_info, sha256_file
from .models import (
    FidelityAudit,
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
    valid = type(value) is int if expected_type is int else isinstance(value, expected_type)
    if not valid:
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


def _require_exact_fields(data: dict, expected: set[str], path: str) -> None:
    if set(data) != expected:
        raise ReportContractError(f"Campos inválidos em {path}")


def _validate_document_fidelity_audit(data: dict, pages: list[dict]) -> None:
    _require_exact_fields(data, {"issues"}, "fidelity_audit")
    issues = data["issues"]
    page_lengths = {page["page_number"]: page["char_count"] for page in pages}
    for issue_index, issue in enumerate(issues):
        issue_path = f"fidelity_audit.issues[{issue_index}]"
        _validate_object_fields(
            issue,
            issue_path,
            (
                ("issue_id", str),
                ("detector", str),
                ("issue_type", str),
                ("resolution", str),
                ("groups", list),
            ),
        )
        _require_exact_fields(
            issue,
            {"issue_id", "detector", "issue_type", "resolution", "groups"},
            issue_path,
        )
        if (
            issue["detector"] != "entity_consistency_checker"
            or issue["issue_type"] != "entity_inconsistency"
        ):
            raise ReportContractError(f"Valor inválido em {issue_path}")
        for group_index, group in enumerate(issue["groups"]):
            group_path = f"{issue_path}.groups[{group_index}]"
            _validate_object_fields(
                group, group_path, (("group", int), ("occurrences", list))
            )
            _require_exact_fields(group, {"group", "occurrences"}, group_path)
            for occurrence_index, occurrence in enumerate(group["occurrences"]):
                occurrence_path = (
                    f"{group_path}.occurrences[{occurrence_index}]"
                )
                fields = {
                    "page_number", "offset_start", "offset_end", "size"
                }
                _validate_object_fields(
                    occurrence,
                    occurrence_path,
                    tuple((field, int) for field in fields),
                )
                _require_exact_fields(occurrence, fields, occurrence_path)
                page_number = occurrence["page_number"]
                start = occurrence["offset_start"]
                end = occurrence["offset_end"]
                size = occurrence["size"]
                if (
                    page_number not in page_lengths
                    or start < 0
                    or end <= start
                    or end > page_lengths[page_number]
                    or size != end - start
                ):
                    raise ReportContractError(
                        f"Valor inválido em {occurrence_path}.offset_end"
                    )


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

    if data["schema_version"] in {"1.1", "1.2"}:
        fidelity_audit = _require_field(data, "fidelity_audit", "fidelity_audit")
        _validate_object_fields(
            fidelity_audit,
            "fidelity_audit",
            (("issues", list),),
        )
    elif data["schema_version"] != "1.0":
        raise ReportContractError("Valor inválido em schema_version")

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
        data["phase1"],
        "phase1",
        (
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
    for field in ("warnings", "errors"):
        for index, value in enumerate(data["result"][field]):
            _require_type(value, str, f"result.{field}[{index}]")
    _validate_object_fields(data["artifacts"], "artifacts", (("markdown_sha256", str),))
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

        fidelity_audit = page.get("fidelity_audit")
        if fidelity_audit is not None:
            _require_type(fidelity_audit, dict, f"{page_path}.fidelity_audit")
            issues = _require_field(fidelity_audit, "issues", f"{page_path}.fidelity_audit.issues")
            if not isinstance(issues, list):
                 raise ReportContractError(f"Tipo incorreto em {page_path}.fidelity_audit.issues")
            for i, issue in enumerate(issues):
                issue_path = f"{page_path}.fidelity_audit.issues[{i}]"
                _validate_object_fields(
                    issue,
                    issue_path,
                    (
                        ("issue_id", str),
                        ("issue_type", str),
                        ("detector", str),
                        ("page_number", int),
                        ("resolution", str),
                    ),
                )
                # Optional fields but must be correct type if present
                for opt_f, opt_t in [("offset_start", int), ("offset_end", int), ("size", int), ("related_offsets", list)]:
                    if opt_f in issue and issue[opt_f] is not None:
                        _require_type(issue[opt_f], opt_t, f"{issue_path}.{opt_f}")
                start = issue.get("offset_start")
                end = issue.get("offset_end")
                size = issue.get("size")
                if start is not None and not 0 <= start <= page["char_count"]:
                    raise ReportContractError(f"Valor inválido em {issue_path}.offset_start")
                if end is not None and not 0 <= end <= page["char_count"]:
                    raise ReportContractError(f"Valor inválido em {issue_path}.offset_end")
                if start is not None and end is not None and end < start:
                    raise ReportContractError(f"Valor inválido em {issue_path}.offset_end")
                if start is not None and end is not None and size is not None and size != end - start:
                    raise ReportContractError(f"Valor inválido em {issue_path}.size")
                for related_index, offset in enumerate(issue.get("related_offsets", [])):
                    _require_type(
                        offset,
                        int,
                        f"{issue_path}.related_offsets[{related_index}]",
                    )
                    if not 0 <= offset < page["char_count"]:
                        raise ReportContractError(
                            f"Valor inválido em {issue_path}.related_offsets[{related_index}]"
                        )

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

    if data["schema_version"] in {"1.1", "1.2"}:
        _validate_document_fidelity_audit(data["fidelity_audit"], data["pages"])


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
    fidelity_audit: FidelityAudit | None = None,
) -> ResultadoPagina:
    return ResultadoPagina(
        page_number=page_number,
        method=method,
        char_count=len(content),
        warnings=warnings or [],
        errors=errors or [],
        truncated=truncated,
        fidelity_audit=fidelity_audit,
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
    has_failed_pages = any(page.method == Metodo.erro for page in pages)
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
