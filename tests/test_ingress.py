from __future__ import annotations

import json
import stat
import struct
import zipfile
from pathlib import Path

import fitz
import pytest

from pipeline_juridico.config import IngressConfig, PreflightLimits
from pipeline_juridico.evidence import LocalFilesystemObjectStorageGateway
from pipeline_juridico.hashing import sha256_bytes
from pipeline_juridico.ingress import (
    ArchiveSecurityError,
    HandoffConflictError,
    IngressError,
    discover_ready_envelopes,
    preflight_envelope,
)


def valid_pdf() -> bytes:
    document = fitz.open()
    document.new_page()
    data = document.tobytes()
    document.close()
    return data


def empty_pdf() -> bytes:
    parts = [b"%PDF-1.4\n"]
    offsets = [0]
    for body in (
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n",
    ):
        offsets.append(sum(map(len, parts)))
        parts.append(body)
    xref_offset = sum(map(len, parts))
    parts.append(
        b"xref\n0 3\n0000000000 65535 f \n"
        + b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:])
        + b"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )
    return b"".join(parts)


def manifest_for(evidence: bytes, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "protocol_version": "1.0",
        "handoff_id": "handoff-1",
        "evidence_reference": "evidence.pdf",
        "source_origin": "filesystem export",
        "retrieved_at": "2026-08-19T12:00:00Z",
        "collector": "process:test",
        "media_type": "application/pdf",
        "byte_size": len(evidence),
    }
    payload.update(overrides)
    return payload


def write_zip(
    path: Path,
    evidence: bytes,
    *,
    manifest: dict[str, object] | bytes | None = None,
    members: list[tuple[str, bytes]] | None = None,
    compression: int = zipfile.ZIP_DEFLATED,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = (
        json.dumps(manifest or manifest_for(evidence)).encode()
        if not isinstance(manifest, bytes)
        else manifest
    )
    entries = members or [("manifest.json", manifest_bytes), ("evidence.pdf", evidence)]
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, data in entries:
            archive.writestr(name, data)
    return path


def config(tmp_path: Path) -> IngressConfig:
    return IngressConfig(
        inbox_dir=tmp_path / "inbox",
        quarantine_dir=tmp_path / "quarantine",
        object_storage_root=tmp_path / "objects",
        ingress_state_dir=tmp_path / "state",
    )


def limits(**overrides: int | float) -> PreflightLimits:
    values: dict[str, int | float] = {
        "max_manifest_bytes": 32_000,
        "max_compressed_bytes": 2_000_000,
        "max_uncompressed_bytes": 2_000_000,
        "max_compression_ratio": 100.0,
    }
    values.update(overrides)
    return PreflightLimits(**values)


def accept(path: Path, tmp_path: Path, *, custom_limits=None):
    cfg = config(tmp_path)
    gateway = LocalFilesystemObjectStorageGateway(cfg.object_storage_root)
    return preflight_envelope(path, cfg, custom_limits or limits(), gateway)


def test_discovery_ignores_partial_and_non_zip_files(tmp_path: Path) -> None:
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    ready = inbox / "ready.zip"
    ready.touch()
    (inbox / "still.partial").touch()
    (inbox / "notes.txt").touch()

    assert discover_ready_envelopes(inbox) == [ready]


def test_exact_two_member_zip_is_preserved_with_official_hash(tmp_path: Path) -> None:
    evidence = valid_pdf()
    envelope = write_zip(tmp_path / "handoff-1.zip", evidence)

    result = accept(envelope, tmp_path)

    assert result.handoff_id == "handoff-1"
    assert result.official_evidence_sha256 == sha256_bytes(evidence)
    assert Path(result.evidence_reference.removeprefix("file://")).read_bytes() == evidence
    assert result.reused is False


def test_candidate_hash_match_proceeds_and_known_hash_does_not_fuse(
    tmp_path: Path,
) -> None:
    evidence = valid_pdf()
    digest = sha256_bytes(evidence)
    first = write_zip(
        tmp_path / "handoff-1.zip",
        evidence,
        manifest=manifest_for(evidence, candidate_sha256=digest),
    )
    second = write_zip(
        tmp_path / "different-handoff.zip",
        evidence,
        manifest=manifest_for(evidence, handoff_id="different-handoff"),
    )

    first_result = accept(first, tmp_path)
    second_result = accept(second, tmp_path)

    assert first_result.official_evidence_sha256 == second_result.official_evidence_sha256
    assert first_result.handoff_id != second_result.handoff_id
    assert second_result.reused is False


def test_retry_equivalence_reuses_prior_result(tmp_path: Path) -> None:
    evidence = valid_pdf()
    manifest = manifest_for(evidence, legal_hints={"court": "X"})
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first_dir.mkdir()
    second_dir.mkdir()
    first = write_zip(first_dir / "handoff-1.zip", evidence, manifest=manifest)
    second = write_zip(
        second_dir / "handoff-1.zip",
        evidence,
        manifest=dict(reversed(list(manifest.items()))),
        compression=zipfile.ZIP_STORED,
    )

    original = accept(first, tmp_path)
    retried = accept(second, tmp_path)

    assert retried == original.__class__(**{**original.__dict__, "reused": True})
    assert len(list((tmp_path / "objects").glob("*.pdf"))) == 1
    state = json.loads(next((tmp_path / "state").glob("*.json")).read_text())
    assert state["result"] == original.evidence_reference
    assert not isinstance(state["result"], dict)
    assert "accepted" not in state.values()


@pytest.mark.parametrize("changed", ["manifest", "evidence"])
def test_same_handoff_with_changed_manifest_or_evidence_conflicts(
    tmp_path: Path, changed: str
) -> None:
    evidence = valid_pdf()
    first = write_zip(tmp_path / "handoff-1.zip", evidence)
    accept(first, tmp_path)
    if changed == "manifest":
        altered_evidence = evidence
        altered_manifest = manifest_for(evidence, source_origin="different")
    else:
        document = fitz.open(stream=evidence, filetype="pdf")
        document.new_page()
        altered_evidence = document.tobytes()
        document.close()
        altered_manifest = manifest_for(altered_evidence)
    second = write_zip(
        tmp_path / "retry" / "handoff-1.zip",
        altered_evidence,
        manifest=altered_manifest,
    )

    with pytest.raises(HandoffConflictError):
        accept(second, tmp_path)


@pytest.mark.parametrize(
    "members",
    [
        [("manifest.json", b"{}"), ("evidence.pdf", b"x"), ("extra.txt", b"x")],
        [("manifest.json", b"{}")],
        [("manifest.json", b"{}"), ("manifest.json", b"{}"), ("evidence.pdf", b"x")],
        [("/manifest.json", b"{}"), ("evidence.pdf", b"x")],
        [("../manifest.json", b"{}"), ("evidence.pdf", b"x")],
        [("nested/manifest.json", b"{}"), ("evidence.pdf", b"x")],
        [("manifest.json/", b""), ("evidence.pdf", b"x")],
    ],
)
def test_invalid_member_sets_and_names_are_rejected(
    tmp_path: Path, members: list[tuple[str, bytes]]
) -> None:
    envelope = write_zip(tmp_path / "bad.zip", b"x", members=members)

    with pytest.raises(ArchiveSecurityError):
        accept(envelope, tmp_path)


def test_symlink_member_is_rejected(tmp_path: Path) -> None:
    envelope = tmp_path / "symlink.zip"
    with zipfile.ZipFile(envelope, "w") as archive:
        archive.writestr("manifest.json", b"{}")
        info = zipfile.ZipInfo("evidence.pdf")
        info.create_system = 3
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, b"target")

    with pytest.raises(ArchiveSecurityError):
        accept(envelope, tmp_path)


def test_unsupported_compression_is_rejected_from_central_directory(
    tmp_path: Path,
) -> None:
    envelope = write_zip(tmp_path / "bad-method.zip", valid_pdf())
    raw = bytearray(envelope.read_bytes())
    central = raw.find(b"PK\x01\x02")
    local = raw.find(b"PK\x03\x04")
    struct.pack_into("<H", raw, central + 10, 99)
    struct.pack_into("<H", raw, local + 8, 99)
    envelope.write_bytes(raw)

    with pytest.raises(ArchiveSecurityError, match="compression"):
        accept(envelope, tmp_path)


def test_encrypted_member_flag_is_rejected(tmp_path: Path) -> None:
    envelope = write_zip(tmp_path / "encrypted.zip", valid_pdf())
    raw = bytearray(envelope.read_bytes())
    central = raw.find(b"PK\x01\x02")
    local = raw.find(b"PK\x03\x04")
    central_flags = struct.unpack_from("<H", raw, central + 8)[0]
    local_flags = struct.unpack_from("<H", raw, local + 6)[0]
    struct.pack_into("<H", raw, central + 8, central_flags | 1)
    struct.pack_into("<H", raw, local + 6, local_flags | 1)
    envelope.write_bytes(raw)

    with pytest.raises(ArchiveSecurityError, match="encrypted"):
        accept(envelope, tmp_path)


@pytest.mark.parametrize(
    "custom_limits",
    [
        limits(max_compressed_bytes=1),
        limits(max_uncompressed_bytes=1),
        limits(max_compression_ratio=0.5),
        limits(max_manifest_bytes=1),
    ],
)
def test_all_configured_archive_limits_are_enforced(
    tmp_path: Path, custom_limits: PreflightLimits
) -> None:
    envelope = write_zip(tmp_path / "handoff-1.zip", valid_pdf())

    with pytest.raises(ArchiveSecurityError):
        accept(envelope, tmp_path, custom_limits=custom_limits)


def test_compressed_limit_applies_to_received_zip_container(tmp_path: Path) -> None:
    envelope = write_zip(tmp_path / "handoff-1.zip", valid_pdf())
    with zipfile.ZipFile(envelope) as archive:
        member_compressed_size = sum(info.compress_size for info in archive.infolist())
    assert envelope.stat().st_size > member_compressed_size

    with pytest.raises(ArchiveSecurityError, match="compressed-size"):
        accept(
            envelope,
            tmp_path,
            custom_limits=limits(max_compressed_bytes=member_compressed_size),
        )


@pytest.mark.parametrize("manifest", [b"\xff", b"{"])
def test_malformed_manifest_bytes_are_rejected(
    tmp_path: Path, manifest: bytes
) -> None:
    envelope = write_zip(tmp_path / "bad-manifest.zip", valid_pdf(), manifest=manifest)

    with pytest.raises(IngressError):
        accept(envelope, tmp_path)


def test_candidate_hash_and_byte_size_mismatch_are_rejected(tmp_path: Path) -> None:
    evidence = valid_pdf()
    for name, manifest in [
        ("handoff-1.zip", manifest_for(evidence, candidate_sha256="0" * 64)),
        ("handoff-1.zip", manifest_for(evidence, byte_size=len(evidence) + 1)),
    ]:
        envelope = write_zip(tmp_path / name, evidence, manifest=manifest)
        with pytest.raises(IngressError):
            accept(envelope, tmp_path)


@pytest.mark.parametrize("kind", ["invalid", "empty", "encrypted"])
def test_invalid_empty_and_encrypted_pdfs_are_rejected(
    tmp_path: Path, kind: str
) -> None:
    if kind == "invalid":
        evidence = b"%PDF-not-structurally-valid"
    else:
        document = fitz.open()
        if kind == "encrypted":
            document.new_page()
            evidence = document.tobytes(
                encryption=fitz.PDF_ENCRYPT_AES_256,
                owner_pw="owner",
                user_pw="user",
            )
        else:
            evidence = empty_pdf()
        document.close()
    envelope = write_zip(tmp_path / "handoff-1.zip", evidence)

    with pytest.raises(IngressError):
        accept(envelope, tmp_path)


def test_invalid_zip_is_rejected(tmp_path: Path) -> None:
    envelope = tmp_path / "not.zip"
    envelope.write_bytes(b"not a zip")

    with pytest.raises(ArchiveSecurityError):
        accept(envelope, tmp_path)


def test_flow_never_writes_under_bundle(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    envelope = write_zip(tmp_path / "handoff-1.zip", valid_pdf())

    accept(envelope, tmp_path)

    assert not bundle.exists()


def test_ingress_config_rejects_operational_path_under_canonical_bundle(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="bundle"):
        IngressConfig(
            inbox_dir=tmp_path / "inbox",
            quarantine_dir=Path.cwd() / "bundle" / "quarantine",
            object_storage_root=tmp_path / "objects",
            ingress_state_dir=tmp_path / "state",
        )


def test_ingress_config_keeps_resolved_paths_stable_after_cwd_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured_from = tmp_path / "configured-from"
    configured_from.mkdir()
    monkeypatch.chdir(configured_from)
    cfg = IngressConfig(
        inbox_dir=Path("inbox"),
        quarantine_dir=Path("quarantine"),
        object_storage_root=Path("objects"),
        ingress_state_dir=Path("state"),
    )

    expected = configured_from / "inbox"
    monkeypatch.chdir(tmp_path)

    assert cfg.inbox_dir == expected
    assert cfg.inbox_dir.is_absolute()


def test_finalized_filename_must_match_manifest_handoff_id(tmp_path: Path) -> None:
    evidence = valid_pdf()
    matching = write_zip(tmp_path / "handoff-1.zip", evidence)
    mismatching = write_zip(tmp_path / "different-name.zip", evidence)

    assert accept(matching, tmp_path).handoff_id == "handoff-1"
    with pytest.raises(IngressError, match="filename"):
        accept(mismatching, tmp_path)
