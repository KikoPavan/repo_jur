from __future__ import annotations

import platform

import pytest

from pipeline_juridico.hashing import get_runtime_info, sha256_bytes, sha256_file

_ABC_SHA256 = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_sha256_bytes_known_vector() -> None:
    assert sha256_bytes(b"abc") == _ABC_SHA256


def test_sha256_file(tmp_path: pytest.TempPathFactory) -> None:
    p = tmp_path / "sample.bin"
    p.write_bytes(b"abc")
    assert sha256_file(p) == _ABC_SHA256


def test_get_runtime_info() -> None:
    info = get_runtime_info()
    assert info.python == platform.python_version()
    assert isinstance(info.markitdown, str) and len(info.markitdown) > 0
    assert isinstance(info.markitdown_ocr, str) and len(info.markitdown_ocr) > 0
    assert isinstance(info.pymupdf, str) and len(info.pymupdf) > 0
