"""Deterministic physical quality evaluation for Phase 1 artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .contracts import GateState
from .conversion_engine import Phase1Artifacts


_MARKER_PATTERN = re.compile(r"\[\[Pág\. (\d+)\]\]")
_METHOD_COMMENT_PATTERN = re.compile(r"<!--\s*método\s*:")
_METHODS = frozenset(
    {"texto_nativo", "ocr_integral", "hibrido", "vazia", "erro"}
)


@dataclass(frozen=True)
class QualityGateResult:
    state: GateState
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    diagnostics: dict[str, object] = field(default_factory=dict)


def _is_exact_type(value: object, expected: type[object]) -> bool:
    return type(value) is expected


def evaluate(phase1_artifacts: Phase1Artifacts) -> QualityGateResult:
    """Evaluate already-converted artifacts without changing either artifact."""

    markdown = phase1_artifacts.markdown
    report_json = phase1_artifacts.report_json
    errors: list[str] = []
    warnings: list[str] = []
    page_count: int | None = None
    pages: list[object] = []
    method_counts: dict[str, int] = {}

    try:
        parsed: object = json.loads(report_json)
        parse_succeeded = True
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError):
        parse_succeeded = False
        errors.append("Technical report JSON is not parseable")

    if parse_succeeded:
        if not isinstance(parsed, dict):
            errors.append("Technical report root must be an object")
        else:
            source = parsed.get("source")
            if not isinstance(source, dict):
                errors.append("Technical report source must be an object")
            else:
                source_hash = source.get("sha256")
                if not _is_exact_type(source_hash, str) or not source_hash:
                    errors.append("Technical report source.sha256 must be a string")

                source_pages = source.get("pages")
                if not _is_exact_type(source_pages, int):
                    errors.append("Technical report source.pages must be an integer")
                else:
                    page_count = source_pages
                    if page_count < 1:
                        errors.append("Technical report physical page count must be at least 1")

            inventory = parsed.get("pages")
            if not isinstance(inventory, list):
                errors.append("Technical report page inventory must be a list")
            else:
                pages = inventory

    inventory_numbers: list[int] = []
    for index, record in enumerate(pages):
        label = f"Page inventory record {index}"
        if not isinstance(record, dict):
            errors.append(f"{label} must be an object")
            continue

        number = record.get("number")
        method = record.get("method")
        status = record.get("status")
        characters = record.get("characters")

        valid_number = _is_exact_type(number, int)
        valid_method = _is_exact_type(method, str) and method in _METHODS
        valid_status = _is_exact_type(status, str)
        valid_characters = _is_exact_type(characters, int)

        if not valid_number:
            errors.append(f"{label}.number must be an integer")
        else:
            inventory_numbers.append(number)

        if not valid_method:
            errors.append(f"{label}.method must use the allowed method vocabulary")
        else:
            method_counts[method] = method_counts.get(method, 0) + 1

        if not valid_status:
            errors.append(f"{label}.status must be a string")
        elif status != "sucesso":
            errors.append(f"{label}.status is not completed: {status}")

        if not valid_characters:
            errors.append(f"{label}.characters must be an integer")

        if valid_method and method == "erro":
            errors.append(f"{label}.method is erro")

        if (
            valid_method
            and valid_characters
            and characters == 0
            and method != "vazia"
        ):
            errors.append(f"{label} has an empty return for a non-blank method")

        page_warnings = record.get("warnings")
        if status == "sucesso" and isinstance(page_warnings, list):
            warnings.extend(
                warning
                for warning in page_warnings
                if isinstance(warning, str) and warning.strip()
            )

    if page_count is not None:
        expected_numbers = list(range(1, page_count + 1))
        if len(pages) != page_count or sorted(inventory_numbers) != expected_numbers:
            errors.append("Technical report page inventory is not exactly complete")
    else:
        expected_numbers = []

    marker_numbers = [int(value) for value in _MARKER_PATTERN.findall(markdown)]
    if not marker_numbers:
        errors.append("Markdown has zero canonical page markers")
    if page_count is not None and marker_numbers != expected_numbers:
        errors.append("Markdown marker sequence does not exactly match physical pages")

    try:
        markdown.encode("utf-8")
    except UnicodeEncodeError:
        errors.append("Markdown is not encodable as UTF-8")
    if "\x00" in markdown:
        errors.append("Markdown contains a NUL byte")
    if "\r" in markdown:
        errors.append("Markdown contains a CR line ending")
    if _METHOD_COMMENT_PATTERN.search(markdown):
        errors.append("Markdown contains a technical method comment")

    diagnostics: dict[str, object] = {
        "marker_count": len(marker_numbers),
        "page_count": page_count,
        "method_counts": dict(sorted(method_counts.items())),
    }
    if errors:
        state = GateState.FAIL
    elif warnings:
        state = GateState.PASS_WITH_WARNINGS
    else:
        state = GateState.PASS
    return QualityGateResult(
        state=state,
        warnings=tuple(warnings),
        errors=tuple(errors),
        diagnostics=diagnostics,
    )
