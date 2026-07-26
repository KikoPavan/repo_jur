from __future__ import annotations

import fitz

from pipeline_juridico.router import inspect_native_text


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
