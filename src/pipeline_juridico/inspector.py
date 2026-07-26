from __future__ import annotations

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
