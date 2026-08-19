from __future__ import annotations

import os
from dataclasses import dataclass
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
