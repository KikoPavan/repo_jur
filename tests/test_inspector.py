from __future__ import annotations

from pathlib import Path

import fitz

from pipeline_juridico import hashing
from pipeline_juridico.inspector import inspect_source, isolate_pages, open_pdf


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


def test_isolate_pages(tmp_path) -> None:
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    doc = open_pdf(str(pdf_path))
    try:
        dest = tmp_path / "paginas"
        result = isolate_pages(doc, dest)

        assert len(result) == 3
        for p in result:
            assert p.exists()
        for i, p in enumerate(result):
            assert p.name == f"page_{i + 1:04d}.pdf"
            with fitz.open(p) as single:
                assert single.page_count == 1
    finally:
        doc.close()
