from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def ensure_outside_canonical_bundle(path: str | Path) -> Path:
    """Reject operational paths that target this repository's bundle tree."""

    resolved = Path(path).resolve()
    bundle = (Path(__file__).resolve().parents[2] / "bundle").resolve()
    if resolved == bundle or resolved.is_relative_to(bundle):
        raise ValueError("Stage 2 operational paths must remain outside bundle/")
    return resolved


@dataclass(frozen=True)
class RoutingConfig:
    native_min_text_chars: int = 50
    full_page_image_min_ratio: float = 0.70
    significant_image_min_ratio: float = 0.15

    def __post_init__(self) -> None:
        if self.native_min_text_chars < 0:
            raise ValueError("native_min_text_chars deve ser maior ou igual a zero")
        if not 0.0 <= self.full_page_image_min_ratio <= 1.0:
            raise ValueError(
                "full_page_image_min_ratio deve estar entre 0.0 e 1.0"
            )
        if not 0.0 <= self.significant_image_min_ratio <= 1.0:
            raise ValueError(
                "significant_image_min_ratio deve estar entre 0.0 e 1.0"
            )
        if self.significant_image_min_ratio > self.full_page_image_min_ratio:
            raise ValueError(
                "o limite de imagem significativa não pode ser maior que o de "
                "página inteira"
            )

    @classmethod
    def from_env(cls) -> RoutingConfig:
        return cls(
            native_min_text_chars=int(
                os.environ.get("NATIVE_MIN_TEXT_CHARS", "50")
            ),
            full_page_image_min_ratio=float(
                os.environ.get("FULL_PAGE_IMAGE_MIN_RATIO", "0.70")
            ),
            significant_image_min_ratio=float(
                os.environ.get("SIGNIFICANT_IMAGE_MIN_RATIO", "0.15")
            ),
        )


@dataclass(frozen=True)
class IngressConfig:
    """Operational Stage 2 paths.

    Defaults are implementation choices and may be overridden by environment.
    All operational data is deliberately outside the canonical ``bundle/``.
    """

    inbox_dir: Path = Path("var/ingress/inbox")
    quarantine_dir: Path = Path("var/ingress/quarantine")
    object_storage_root: Path = Path("var/object-storage")
    ingress_state_dir: Path = Path("var/ingress/state")

    def __post_init__(self) -> None:
        for field_name in (
            "inbox_dir",
            "quarantine_dir",
            "object_storage_root",
            "ingress_state_dir",
        ):
            value = ensure_outside_canonical_bundle(getattr(self, field_name))
            object.__setattr__(self, field_name, value)

    @classmethod
    def from_env(cls) -> IngressConfig:
        return cls(
            inbox_dir=Path(os.environ.get("INGRESS_INBOX_DIR", "var/ingress/inbox")),
            quarantine_dir=Path(
                os.environ.get("INGRESS_QUARANTINE_DIR", "var/ingress/quarantine")
            ),
            object_storage_root=Path(
                os.environ.get("OBJECT_STORAGE_ROOT", "var/object-storage")
            ),
            ingress_state_dir=Path(
                os.environ.get("INGRESS_STATE_DIR", "var/ingress/state")
            ),
        )


@dataclass(frozen=True)
class IntakeConfig:
    """Operational Intake Queue configuration."""

    input_dir: Path = Path("input")
    registry_dir: Path = Path("var/intake/registry")
    processing_dir: Path = Path("var/intake/processing")
    failed_dir: Path = Path("var/intake/failed")
    lease_timeout_seconds: int = 300

    def __post_init__(self) -> None:
        for field_name in (
            "registry_dir",
            "processing_dir",
            "failed_dir",
        ):
            value = ensure_outside_canonical_bundle(getattr(self, field_name))
            object.__setattr__(self, field_name, value)

    @classmethod
    def from_env(cls) -> IntakeConfig:
        return cls(
            input_dir=Path(os.environ.get("INTAKE_INPUT_DIR", "input")),
            registry_dir=Path(os.environ.get("INTAKE_REGISTRY_DIR", "var/intake/registry")),
            processing_dir=Path(os.environ.get("INTAKE_PROCESSING_DIR", "var/intake/processing")),
            failed_dir=Path(os.environ.get("INTAKE_FAILED_DIR", "var/intake/failed")),
            lease_timeout_seconds=int(os.environ.get("INTAKE_LEASE_TIMEOUT", "300")),
        )


@dataclass(frozen=True)
class PreflightLimits:
    """Configurable archive bounds; defaults are implementation choices."""

    max_manifest_bytes: int = 1_048_576
    max_compressed_bytes: int = 268_435_456
    max_uncompressed_bytes: int = 536_870_912
    max_compression_ratio: float = 100.0

    def __post_init__(self) -> None:
        for name in (
            "max_manifest_bytes",
            "max_compressed_bytes",
            "max_uncompressed_bytes",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_compression_ratio <= 0:
            raise ValueError("max_compression_ratio must be positive")

    @classmethod
    def from_env(cls) -> PreflightLimits:
        return cls(
            max_manifest_bytes=int(
                os.environ.get("PREFLIGHT_MAX_MANIFEST_BYTES", "1048576")
            ),
            max_compressed_bytes=int(
                os.environ.get("PREFLIGHT_MAX_COMPRESSED_BYTES", "268435456")
            ),
            max_uncompressed_bytes=int(
                os.environ.get("PREFLIGHT_MAX_UNCOMPRESSED_BYTES", "536870912")
            ),
            max_compression_ratio=float(
                os.environ.get("PREFLIGHT_MAX_COMPRESSION_RATIO", "100.0")
            ),
        )


FILTER_SCHEMA_VERSION = "1"
RETRIEVAL_FILTER_SCHEMA_VERSION = FILTER_SCHEMA_VERSION
PUBLIC_TO_CANONICAL_FIELD = {
    "lei_numero": "repo_jur_lei_numero",
    "lei_ano": "repo_jur_lei_ano",
    "lei_esfera": "repo_jur_lei_esfera",
    "lei_tipo": "repo_jur_lei_tipo",
    "processo_numero": "repo_jur_processo_numero",
    "tribunal": "repo_jur_tribunal",
    "relator": "repo_jur_relator",
    "data_julgamento": "repo_jur_data_julgamento",
    "ramo_direito": "repo_jur_ramo_direito",
    "precedente_numero": "repo_jur_precedente_numero",
    "precedente_status": "repo_jur_precedente_status",
    "tema_numero": "repo_jur_tema_numero",
}
RETRIEVAL_FILTER_VOCABULARY = (
    "type",
    "status",
    "tags",
    "lei_numero",
    "lei_ano",
    "lei_esfera",
    "lei_tipo",
    "processo_numero",
    "tribunal",
    "relator",
    "data_julgamento",
    "ramo_direito",
    "precedente_numero",
    "precedente_status",
    "tema_numero",
)


@dataclass(frozen=True)
class RetrievalConfig:
    """Validated, derived-only configuration for Legal Knowledge retrieval."""

    derived_root: Path = Path("var/retrieval")
    search_default_limit: int = 10
    search_max_limit: int = 50
    filter_schema_version: str = RETRIEVAL_FILTER_SCHEMA_VERSION
    filter_vocabulary: tuple[str, ...] = RETRIEVAL_FILTER_VOCABULARY
    public_to_canonical_field: dict[str, str] = field(
        default_factory=lambda: PUBLIC_TO_CANONICAL_FIELD.copy()
    )

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "derived_root",
            ensure_outside_canonical_bundle(self.derived_root),
        )
        if not 1 <= self.search_default_limit <= self.search_max_limit:
            raise ValueError(
                "search limits require maximum >= default >= 1"
            )
        if not self.filter_schema_version or not self.filter_vocabulary:
            raise ValueError("retrieval filter schema must be declared")

    @classmethod
    def from_env(cls) -> RetrievalConfig:
        return cls(
            derived_root=Path(
                os.environ.get("RETRIEVAL_STATE_DIR", "var/retrieval")
            ),
            search_default_limit=int(
                os.environ.get("RETRIEVAL_SEARCH_DEFAULT_LIMIT", "10")
            ),
            search_max_limit=int(
                os.environ.get("RETRIEVAL_SEARCH_MAX_LIMIT", "50")
            ),
        )
