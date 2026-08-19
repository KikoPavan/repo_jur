"""Evidence-preservation storage seam and local adapter."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Protocol

from .config import ensure_outside_canonical_bundle
from .hashing import sha256_bytes


class ObjectStorageGateway(Protocol):
    def put(self, data: bytes, *, content_type: str) -> str:
        """Preserve exact bytes and return a stable resolvable reference."""


class LocalFilesystemObjectStorageGateway:
    def __init__(self, root: str | Path) -> None:
        self.root = ensure_outside_canonical_bundle(root)

    def put(self, data: bytes, *, content_type: str) -> str:
        suffix = ".pdf" if content_type == "application/pdf" else ".bin"
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / f"{sha256_bytes(data)}{suffix}"
        if target.exists():
            if target.read_bytes() != data:
                raise OSError("content-addressed object collision")
            return target.resolve().as_uri()

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.", suffix=".tmp", dir=self.root
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target.resolve().as_uri()
