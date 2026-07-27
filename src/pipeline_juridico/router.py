from __future__ import annotations

from dataclasses import dataclass

import fitz

from .config import RoutingConfig
from .models import Metodo


@dataclass
class NativeTextSignal:
    block_count: int
    char_count: int


@dataclass
class RasterSignal:
    image_count: int
    total_image_area_ratio: float
    largest_image_area_ratio: float


def inspect_native_text(page: fitz.Page) -> NativeTextSignal:
    blocks = page.get_text("blocks")
    text_blocks = [b for b in blocks if len(b) > 6 and b[6] == 0]
    block_count = len(text_blocks)
    char_count = sum(
        len("".join(b[4].split())) for b in text_blocks
    )
    return NativeTextSignal(block_count=block_count, char_count=char_count)


def inspect_raster_content(page: fitz.Page) -> RasterSignal:
    page_area = page.rect.width * page.rect.height
    images = page.get_image_info()
    if not images or page_area <= 0:
        return RasterSignal(0, 0.0, 0.0)

    image_areas = []
    for image in images:
        x0, y0, x1, y1 = image["bbox"]
        area = max(0.0, x1 - x0) * max(0.0, y1 - y0)
        image_areas.append(area)

    return RasterSignal(
        image_count=len(images),
        total_image_area_ratio=min(1.0, sum(image_areas) / page_area),
        largest_image_area_ratio=min(1.0, max(image_areas) / page_area),
    )


def route_page(
    page: fitz.Page,
    config: RoutingConfig | None = None,
) -> Metodo:
    if config is None:
        config = RoutingConfig()

    native = inspect_native_text(page)
    raster = inspect_raster_content(page)

    has_native = native.char_count >= config.native_min_text_chars
    has_full_page_image = (
        raster.largest_image_area_ratio >= config.full_page_image_min_ratio
    )
    has_significant_raster = (
        raster.total_image_area_ratio >= config.significant_image_min_ratio
    )
    has_raster_signal = has_full_page_image or has_significant_raster
    # Ten times the native minimum (500 chars with the default config) plus
    # three text blocks distinguishes substantial page text from a long
    # caption or isolated label. In that case, summed decorative images must
    # not promote the page to hybrid; a full-page image still always does.
    has_clearly_sufficient_native = (
        native.char_count >= config.native_min_text_chars * 10
        and native.block_count >= 3
    )

    if not has_native and not has_raster_signal:
        return Metodo.vazia
    if has_native and not has_raster_signal:
        return Metodo.texto_nativo
    if has_native and has_raster_signal:
        if has_clearly_sufficient_native and not has_full_page_image:
            return Metodo.texto_nativo
        return Metodo.hibrido
    return Metodo.ocr_integral
