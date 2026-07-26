from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

import fitz

from pipeline_juridico import hashing
from pipeline_juridico.models import FonteInfo


class PdfInspectionError(Exception):
    ...


class PdfNotFoundError(PdfInspectionError):
    ...


class PdfInvalidError(PdfInspectionError):
    ...


class PdfEncryptedError(PdfInspectionError):
    ...


class PdfEmptyError(PdfInspectionError):
    ...


def validate_pdf_path(path: str | Path) -> Path:
    path_obj = Path(path)
    if not path_obj.exists():
        raise PdfNotFoundError(f"PDF path does not exist: {path_obj}")
    if not path_obj.is_file():
        raise PdfInvalidError(f"PDF path is not a regular file: {path_obj}")
    return path_obj


def open_pdf(path: str | Path) -> fitz.Document:
    path_obj = validate_pdf_path(path)
    try:
        doc = fitz.open(path_obj)
    except Exception as exc:
        raise PdfInvalidError(f"Failed to open PDF: {path_obj}") from exc
    if doc.is_encrypted or doc.needs_pass:
        doc.close()
        raise PdfEncryptedError(f"PDF is encrypted and requires a password: {path_obj}")
    if doc.page_count == 0:
        doc.close()
        raise PdfEmptyError(f"PDF has no pages: {path_obj}")
    return doc


def isolate_pages(doc: fitz.Document, dest_dir: str | Path) -> list[Path]:
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for i in range(doc.page_count):
        page_path = dest / f"page_{i + 1:04d}.pdf"
        novo_doc = fitz.open()
        novo_doc.insert_pdf(doc, from_page=i, to_page=i)
        novo_doc.save(page_path)
        novo_doc.close()
        paths.append(page_path)
    return paths


def inspect_source(path: str | Path) -> FonteInfo:
    doc = open_pdf(path)
    path_obj = Path(path)
    size_bytes = path_obj.stat().st_size
    sha256 = hashing.sha256_file(path)
    pages = doc.page_count
    doc.close()
    return FonteInfo(
        path=str(path_obj),
        size_bytes=size_bytes,
        sha256=sha256,
        pages=pages,
    )


@contextmanager
def isolated_page_workspace(
    source_path: str | Path,
    temp_root: str | Path,
    keep_temp: bool = False,
) -> list[Path]:
    doc = open_pdf(source_path)
    Path(temp_root).mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(dir=str(temp_root)))
    try:
        pages = isolate_pages(doc, run_dir)
        yield pages
    finally:
        doc.close()
        if not keep_temp:
            shutil.rmtree(run_dir, ignore_errors=True)
