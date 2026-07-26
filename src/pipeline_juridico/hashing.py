from __future__ import annotations

import hashlib
import os
import platform
from importlib import metadata

from .models import RuntimeInfo

_CHUNK_SIZE = 65536


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str | os.PathLike) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def get_runtime_info() -> RuntimeInfo:
    return RuntimeInfo(
        python=platform.python_version(),
        markitdown=metadata.version("markitdown"),
        markitdown_ocr=metadata.version("markitdown-ocr"),
        pymupdf=metadata.version("pymupdf"),
    )
