from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Metodo(str, Enum):
    texto_nativo = "texto_nativo"
    ocr_integral = "ocr_integral"
    hibrido = "hibrido"
    vazia = "vazia"
    erro = "erro"


class StatusExecucao(str, Enum):
    sucesso = "sucesso"
    incompleto = "incompleto"
    falha = "falha"


@dataclass
class FidelityIssue:
    issue_id: str
    issue_type: str  # duplication, entity_inconsistency, sensitive_token_uncertainty, visual_uncertainty
    detector: str
    page_number: int
    offset_start: int | None = None
    offset_end: int | None = None
    size: int | None = None
    related_offsets: list[int] = field(default_factory=list)
    resolution: str = "flagged"  # accepted, flagged, illegible


@dataclass
class FidelityAudit:
    issues: list[FidelityIssue] = field(default_factory=list)


@dataclass
class ResultadoPagina:
    page_number: int
    method: Metodo
    char_count: int
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    truncated: bool = False
    fidelity_audit: FidelityAudit | None = None


@dataclass
class FonteInfo:
    path: str
    size_bytes: int
    sha256: str
    pages: int


@dataclass
class InputInfo:
    sha256: str = ""
    byte_size: int = 0
    page_count: int = 0


@dataclass
class Phase1Info:
    implementation: str = ""
    implementation_version: str = ""
    logical_processing_version: str = ""
    relevant_config_fingerprint: str = ""


@dataclass
class ResultadoInfo:
    quality_gate: str = ""
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ArtifactsInfo:
    markdown_sha256: str = ""


@dataclass
class RuntimeInfo:
    python: str
    markitdown: str
    markitdown_ocr: str
    pymupdf: str


@dataclass
class OcrInfo:
    enabled: bool
    provider: str
    model: str
    prompt_sha256: str


@dataclass
class TimingInfo:
    started_at: str
    finished_at: str
    duration_ms: int


@dataclass
class Relatorio:
    schema_version: str = "1.0"
    execution_id: str = ""
    input: InputInfo | None = None
    phase1: Phase1Info | None = None
    result: ResultadoInfo | None = None
    artifacts: ArtifactsInfo | None = None
    pages: list[ResultadoPagina] = field(default_factory=list)
    telemetry: dict = field(default_factory=dict)
