"""Domain-neutral facade over the stabilized PDF conversion implementation."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from .config import RoutingConfig
from .converter import convert_document
from .report import build_report_json, validate_report_contract


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


@dataclass(frozen=True)
class Phase1Artifacts:
    markdown: str
    report_json: str


class EvidenceReferenceError(Exception):
    """A preserved-evidence reference cannot be resolved to a readable file."""


_TECHNICAL_ROUTING_METADATA = re.compile(
    r"^(\[\[Pág\. [1-9]\d*\]\]\r?\n)"
    r"<!-- método: (?:texto_nativo|ocr_integral|hibrido|vazia|erro) -->"
    r"(?:\r?\n|$)",
    re.MULTILINE,
)


def strip_technical_routing_metadata(markdown: str) -> str:
    """Remove canonical marker-adjacent method comments from Markdown."""

    return _TECHNICAL_ROUTING_METADATA.sub(r"\1", markdown)


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
        report_json = build_report_json(relatorio)
        validate_report_contract(json.loads(report_json))
        return Phase1Artifacts(
            markdown=strip_technical_routing_metadata(markdown),
            report_json=report_json,
        )
