"""Domain-neutral facade over the stabilized PDF conversion implementation."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from .config import RoutingConfig
from .contracts import Phase1Artifacts
from .converter import convert_document
from .quality_gate import evaluate
from .report import (
    attach_gate_result,
    build_candidate_report_json,
    build_report_json,
    strip_technical_routing_metadata,
    validate_report_contract,
)


@dataclass(frozen=True)
class ConversionConfig:
    temp_root: str | Path
    allow_partial: bool = False
    use_ocr: bool = True
    ocr_api_key: str | None = None
    ocr_model: str | None = None
    ocr_base_url: str | None = None
    ocr_prompt_path: str | Path = "prompts/ocr_literal_ptbr.txt"
    routing_config: RoutingConfig | None = None
    keep_temp: bool = False


class EvidenceReferenceError(Exception):
    """A preserved-evidence reference cannot be resolved to a readable file."""


def resolve_evidence_reference(evidence_ref: str) -> Path:
    """Resolve the local ``file://`` representation used by current storage."""

    try:
        parsed = urlparse(evidence_ref)
    except (TypeError, ValueError) as exc:
        raise EvidenceReferenceError("malformed evidence reference") from exc

    if (
        parsed.scheme != "file"
        or parsed.netloc not in ("", "localhost")
        or not parsed.path
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise EvidenceReferenceError("unsupported or malformed evidence reference")

    try:
        path = Path(unquote(parsed.path)).resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise EvidenceReferenceError("evidence reference cannot be resolved") from exc

    if not path.is_file() or not os.access(path, os.R_OK):
        raise EvidenceReferenceError("evidence reference is not a readable file")
    return path


class ConversionEngine:
    def convert(
        self, evidence_ref: str, config: ConversionConfig
    ) -> Phase1Artifacts:
        pdf_path = resolve_evidence_reference(evidence_ref)
        markdown, relatorio = convert_document(
            pdf_path,
            output_path=str(pdf_path) + ".md",
            temp_root=config.temp_root,
            allow_partial=config.allow_partial,
            use_ocr=config.use_ocr,
            ocr_api_key=config.ocr_api_key,
            ocr_model=config.ocr_model,
            ocr_base_url=config.ocr_base_url,
            ocr_prompt_path=config.ocr_prompt_path,
            routing_config=config.routing_config,
            keep_temp=config.keep_temp,
        )
        literal = strip_technical_routing_metadata(markdown)
        candidate_json = build_candidate_report_json(relatorio)
        gate_result = evaluate(
            Phase1Artifacts(markdown=literal, report_json=candidate_json)
        )
        final = attach_gate_result(
            relatorio,
            quality_gate=gate_result.state.value,
            warnings=gate_result.warnings,
            errors=gate_result.errors,
        )
        report_json = build_report_json(final)
        validate_report_contract(json.loads(report_json))
        return Phase1Artifacts(
            markdown=literal,
            report_json=report_json,
        )
