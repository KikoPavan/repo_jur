from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


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
class ResultadoPagina:
    page_number: int
    method: Metodo
    char_count: int
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    truncated: bool = False


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
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


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
    input: Optional[InputInfo] = None
    phase1: Optional[Phase1Info] = None
    result: Optional[ResultadoInfo] = None
    artifacts: Optional[ArtifactsInfo] = None
    pages: List[ResultadoPagina] = field(default_factory=list)
    telemetry: dict = field(default_factory=dict)
