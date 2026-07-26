from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pipeline_juridico import hashing
from pipeline_juridico.inspector import (
    inspect_source,
    isolated_page_workspace,
    isolate_pages,
    open_pdf,
)


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


def test_isolated_page_workspace_success(tmp_path) -> None:
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    temp_root = tmp_path / "temp_root"
    with isolated_page_workspace(str(pdf_path), temp_root) as pages:
        assert len(pages) == 2
        for p in pages:
            assert p.exists()
        parent_dir = pages[0].parent

    assert not parent_dir.exists()


def test_isolated_page_workspace_failure(tmp_path) -> None:
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    temp_root = tmp_path / "temp_root"
    with pytest.raises(RuntimeError):
        with isolated_page_workspace(str(pdf_path), temp_root) as pages:
            parent_dir = pages[0].parent
            raise RuntimeError("falha simulada")

    assert not parent_dir.exists()


def test_isolated_page_workspace_keep_temp(tmp_path) -> None:
    pdf_path = tmp_path / "source.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    temp_root = tmp_path / "temp_root"
    with isolated_page_workspace(str(pdf_path), temp_root, keep_temp=True) as pages:
        parent_dir = pages[0].parent
        assert parent_dir.exists()

    assert parent_dir.exists()
