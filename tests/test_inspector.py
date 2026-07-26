from __future__ import annotations

from pathlib import Path

import fitz
import pytest

from pipeline_juridico import hashing
from pipeline_juridico.inspector import (
    PdfEmptyError,
    PdfEncryptedError,
    PdfInvalidError,
    PdfNotFoundError,
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


def test_open_pdf_missing_file_raises(tmp_path) -> None:
    caminho = tmp_path / "nao_existe.pdf"
    with pytest.raises(PdfNotFoundError) as exc_info:
        open_pdf(caminho)
    assert str(caminho) in str(exc_info.value)


def test_open_pdf_invalid_path_raises(tmp_path) -> None:
    with pytest.raises(PdfInvalidError) as exc_info:
        open_pdf(tmp_path)
    assert str(tmp_path) in str(exc_info.value)


def test_open_pdf_corrupted_file_raises(tmp_path) -> None:
    caminho = tmp_path / "corrupto.pdf"
    caminho.write_bytes(b"%PDF-1.4 not a real pdf body")
    with pytest.raises(PdfInvalidError) as exc_info:
        open_pdf(caminho)
    assert str(caminho) in str(exc_info.value)


def test_open_pdf_encrypted_file_raises(tmp_path) -> None:
    caminho = tmp_path / "criptografado.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(caminho, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="secret", owner_pw="secret")
    doc.close()
    with pytest.raises(PdfEncryptedError) as exc_info:
        open_pdf(caminho)
    assert str(caminho) in str(exc_info.value)


def test_open_pdf_zero_pages_raises(tmp_path) -> None:
    caminho = tmp_path / "zero_paginas.pdf"
    caminho.write_text(
        "%PDF-1.4\n"
        "1 0 obj\n"
        "<< /Type /Catalog /Pages 2 0 R >>\n"
        "endobj\n"
        "2 0 obj\n"
        "<< /Type /Pages /Kids [] /Count 0 >>\n"
        "endobj\n"
        "xref\n"
        "0 3\n"
        "0000000000 65535 f \n"
        "0000000009 00000 n \n"
        "0000000058 00000 n \n"
        "trailer\n"
        "<< /Size 3 /Root 1 0 R >>\n"
        "startxref\n"
        "114\n"
        "%%EOF\n"
    )
    with pytest.raises(PdfEmptyError) as exc_info:
        open_pdf(caminho)
    assert str(caminho) in str(exc_info.value)
