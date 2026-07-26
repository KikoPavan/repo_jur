from __future__ import annotations

from pathlib import Path

import fitz

from pipeline_juridico import hashing
from pipeline_juridico.inspector import inspect_source, open_pdf


def test_open_pdf_valid_one_page(tmp_path) -> None:
    pdf_path = tmp_path / "valid.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    result = open_pdf(str(pdf_path))
    assert result.page_count == 1
    result.close()


def test_inspect_source_valid_one_page(tmp_path) -> None:
    pdf_path = tmp_path / "valid.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    info = inspect_source(str(pdf_path))

    assert info.pages == 1
    assert info.size_bytes == Path(pdf_path).stat().st_size
    assert info.sha256 == hashing.sha256_file(str(pdf_path))
    assert info.path == str(pdf_path)
