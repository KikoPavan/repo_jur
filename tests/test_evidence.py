from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_juridico.evidence import LocalFilesystemObjectStorageGateway
from pipeline_juridico.hashing import sha256_bytes


def test_local_gateway_put_is_content_addressed_stable_and_atomic(
    tmp_path: Path, monkeypatch
) -> None:
    root = tmp_path / "objects"
    gateway = LocalFilesystemObjectStorageGateway(root)
    evidence = b"exact accepted evidence bytes"
    replace_calls: list[tuple[Path, Path]] = []

    import pipeline_juridico.evidence as evidence_module

    real_replace = evidence_module.os.replace

    def recording_replace(source: str | Path, target: str | Path) -> None:
        replace_calls.append((Path(source), Path(target)))
        real_replace(source, target)

    monkeypatch.setattr(evidence_module.os, "replace", recording_replace)

    first = gateway.put(evidence, content_type="application/pdf")
    second = gateway.put(evidence, content_type="application/pdf")

    expected_path = root / f"{sha256_bytes(evidence)}.pdf"
    assert first == second == expected_path.resolve().as_uri()
    assert expected_path.read_bytes() == evidence
    assert replace_calls
    assert all(source.parent == target.parent == root for source, target in replace_calls)
    assert not list(root.glob("*.tmp"))


def test_gateway_never_writes_to_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    gateway = LocalFilesystemObjectStorageGateway(tmp_path / "storage")

    gateway.put(b"pdf", content_type="application/pdf")

    assert not bundle.exists()


def test_gateway_rejects_canonical_bundle_root() -> None:
    canonical_bundle = Path.cwd() / "bundle"
    existed_before = canonical_bundle.exists()

    with pytest.raises(ValueError, match="bundle"):
        LocalFilesystemObjectStorageGateway(canonical_bundle)

    assert canonical_bundle.exists() is existed_before
