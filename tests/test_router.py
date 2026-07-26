from __future__ import annotations

import fitz

from pipeline_juridico.router import inspect_native_text, inspect_raster_content


def test_inspect_native_text_with_content() -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50),
        "Texto de teste com bastante conteúdo para validar a métrica de caracteres.",
    )
    signal = inspect_native_text(page)
    assert signal.char_count > 0
    assert signal.block_count >= 1
    doc.close()


def test_inspect_native_text_empty_page() -> None:
    doc = fitz.open()
    page = doc.new_page()
    signal = inspect_native_text(page)
    assert signal.char_count == 0
    assert signal.block_count == 0
    doc.close()


def test_inspect_raster_content_without_image() -> None:
    doc = fitz.open()
    page = doc.new_page()
    signal = inspect_raster_content(page)
    assert signal.image_count == 0
    assert signal.total_image_area_ratio == 0.0
    assert signal.largest_image_area_ratio == 0.0
    doc.close()


def test_inspect_raster_content_with_full_page_image() -> None:
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pix.set_rect(pix.irect, (255, 0, 0))
    page.insert_image(page.rect, pixmap=pix)

    signal = inspect_raster_content(page)

    assert signal.image_count == 1
    assert signal.largest_image_area_ratio > 0.95
    doc.close()


def test_inspect_raster_content_with_small_image() -> None:
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pix.set_rect(pix.irect, (255, 0, 0))
    page.insert_image(fitz.Rect(0, 0, 50, 50), pixmap=pix)

    signal = inspect_raster_content(page)

    assert signal.image_count == 1
    assert signal.largest_image_area_ratio < 0.15
    doc.close()
