from __future__ import annotations

import os
from dataclasses import dataclass


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
