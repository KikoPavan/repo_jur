"""Process profile, context validation, paths, and write boundary."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import unquote, urlparse

from .contracts import RouteTarget


class ProcessProducerError(Exception):
    pass


class ProcessProducerConfigurationError(ProcessProducerError):
    pass


class ProcessProducerBlockedError(ProcessProducerError):
    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class ProcessConceptType(str, Enum):
    Peticao = "Peticao"
    Contestacao = "Contestacao"
    Decisao = "Decisao"
    Procuracao = "Procuracao"
    Testamento = "Testamento"
    Anexo = "Anexo"
    OutraPeca = "OutraPeca"


_TYPE_DIRECTORIES = {
    ProcessConceptType.Peticao: "peticao",
    ProcessConceptType.Contestacao: "contestacao",
    ProcessConceptType.Decisao: "decisao",
    ProcessConceptType.Procuracao: "procuracao",
    ProcessConceptType.Testamento: "testamento",
    ProcessConceptType.Anexo: "anexo",
    ProcessConceptType.OutraPeca: "outra_peca",
}
PROCESS_PROFILE_FIELDS = {kind: () for kind in ProcessConceptType}
PROCESS_PRODUCER_OWNED_KEYS = frozenset({
    "type", "generated", "sources", "repo_jur_pdf_hash",
    "repo_jur_pdf_hashes", "repo_jur_evidence_sha256", "repo_jur_phase1",
} | {name for names in PROCESS_PROFILE_FIELDS.values() for name in names})
PROCESS_HUMAN_OWNED_KEYS = frozenset({"status", "verified"})
PROCESS_SHARED_KEYS = frozenset({"title", "aliases", "tags", "related"})

_PERMITTED_CONTEXT_KEYS = frozenset({"type", "evidence_resource"})
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_URI_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*\Z")


@dataclass(frozen=True)
class ProcessProducerContext:
    type: ProcessConceptType
    evidence_resource: str | None


def _plausible_reference(value: str) -> bool:
    if not value or value != value.strip() or "\x00" in value:
        return False
    parsed = urlparse(value)
    if parsed.scheme:
        return bool(_URI_SCHEME.match(parsed.scheme)) and bool(
            parsed.netloc or parsed.path
        )
    return not any(character in value for character in "?*<>|\n\r")


def validate_process_producer_context(
    payload: Mapping[str, object] | None,
) -> ProcessProducerContext:
    if not isinstance(payload, Mapping):
        raise ProcessProducerConfigurationError(
            "producer context must be a mapping"
        )
    if any(key not in _PERMITTED_CONTEXT_KEYS for key in payload):
        raise ProcessProducerConfigurationError("unknown producer context key")
    raw_type = payload.get("type")
    if not isinstance(raw_type, str):
        raise ProcessProducerConfigurationError("producer context type is required")
    try:
        concept_type = ProcessConceptType(raw_type)
    except ValueError as error:
        raise ProcessProducerConfigurationError(
            "producer context type is invalid"
        ) from error
    resource = payload.get("evidence_resource")
    if resource is not None and (
        not isinstance(resource, str) or not _plausible_reference(resource)
    ):
        raise ProcessProducerConfigurationError("evidence resource is invalid")
    return ProcessProducerContext(concept_type, resource)


def _slug(resource: str | None, report: Mapping[str, object]) -> str:
    if resource:
        parsed = urlparse(resource)
        stem = Path(unquote(parsed.path) if parsed.scheme else resource).stem
    else:
        stem = str(report["input"]["sha256"])  # type: ignore[index]
    ascii_stem = unicodedata.normalize("NFKD", stem).encode(
        "ascii", "ignore"
    ).decode()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_stem.lower()).strip("_")
    return slug or str(report["input"]["sha256"])  # type: ignore[index]


def resolve_process_concept_path(
    concept_type: ProcessConceptType,
    evidence_resource: str | None,
    process_root: str | Path,
) -> Path:
    if not isinstance(concept_type, ProcessConceptType):
        raise ProcessProducerConfigurationError("candidate type is invalid")
    root = Path(process_root).resolve()
    fake_report: dict[str, object] = {"input": {"sha256": "0" * 64}}
    candidate = (
        root / _TYPE_DIRECTORIES[concept_type]
        / f"{_slug(evidence_resource, fake_report)}.md"
    ).resolve()
    if not candidate.is_relative_to(root):
        raise ProcessProducerConfigurationError("concept path escapes process root")
    return candidate


def guard_process_write(
    *, acting_domain: RouteTarget, target: str | Path,
    process_root: str | Path, legal_bundle_root: str | Path,
) -> Path:
    resolved_target = Path(target).resolve()
    resolved_process = Path(process_root).resolve()
    resolved_bundle = Path(legal_bundle_root).resolve()
    if acting_domain is not RouteTarget.JUDICIAL_PROCESS:
        raise PermissionError(
            "Only the judicial_process domain may write process storage"
        )
    if resolved_target == resolved_bundle or resolved_target.is_relative_to(
        resolved_bundle
    ):
        raise PermissionError("process domain cannot write to the Legal bundle")
    if not resolved_target.is_relative_to(resolved_process):
        raise PermissionError("target escapes the process root")
    return resolved_target


def ensure_outside_process_storage(
    path: str | Path, process_root: str | Path
) -> Path:
    resolved = Path(path).resolve()
    root = Path(process_root).resolve()
    if resolved == root or resolved.is_relative_to(root):
        raise ValueError("state directory is inside process-domain storage")
    return resolved
