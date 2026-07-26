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
    number: int
    method: Metodo
    status: StatusExecucao
    characters: int
    duration_ms: int
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class FonteInfo:
    path: str
    size_bytes: int
    sha256: str
    pages: int


@dataclass
class SaidaInfo:
    path: str
    sha256: str


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
    run_id: str = ""
    status: StatusExecucao = StatusExecucao.sucesso
    source: Optional[FonteInfo] = None
    output: Optional[SaidaInfo] = None
    runtime: Optional[RuntimeInfo] = None
    ocr: Optional[OcrInfo] = None
    timing: Optional[TimingInfo] = None
    pages: List[ResultadoPagina] = field(default_factory=list)
