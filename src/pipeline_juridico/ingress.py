"""Filesystem discovery and ordered ITP Stage 2 preflight."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from .config import IngressConfig, PreflightLimits
from .contracts import resolve_safe_path
from .evidence import ObjectStorageGateway
from .hashing import sha256_file
from .inspector import PdfInspectionError, open_pdf
from .itp import ITPManifest, ManifestValidationError, parse_manifest


class IngressError(Exception):
    """An envelope failed Stage 2 preflight."""


class ArchiveSecurityError(IngressError):
    """An archive container or member violates an ingress security rule."""


class HandoffConflictError(IngressError):
    """A retry-stable handoff id was reused for different semantic input."""


@dataclass(frozen=True)
class PreflightResult:
    handoff_id: str
    official_evidence_sha256: str
    evidence_reference: str
    reused: bool = False


_ALLOWED_COMPRESSION = {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}
_EXPECTED_MEMBERS = {"manifest.json", "evidence.pdf"}
_CHUNK_SIZE = 64 * 1024


def discover_ready_envelopes(inbox_dir: str | Path) -> list[Path]:
    inbox = Path(inbox_dir)
    if not inbox.exists():
        return []
    return sorted(path for path in inbox.iterdir() if path.is_file() and path.suffix == ".zip")


def _normalized_member_name(name: str) -> str:
    return unicodedata.normalize("NFC", name.replace("\\", "/"))


def _validate_member_names(infos: list[zipfile.ZipInfo]) -> None:
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise ArchiveSecurityError("duplicate member names are prohibited")
    normalized = [_normalized_member_name(name) for name in names]
    if len(normalized) != len(set(normalized)):
        raise ArchiveSecurityError("normalized-name collisions are prohibited")
    for name in names:
        try:
            resolve_safe_path("/ingress-member-root", name)
        except ValueError as exc:
            raise ArchiveSecurityError(f"unsafe member name: {name}") from exc
        posix_name = PurePosixPath(name.replace("\\", "/"))
        if len(posix_name.parts) != 1 or name.endswith(("/", "\\")):
            raise ArchiveSecurityError("members must be regular root files")
    if set(names) != _EXPECTED_MEMBERS or len(names) != 2:
        raise ArchiveSecurityError("archive must contain only manifest.json and evidence.pdf")


def _validate_member_metadata(
    infos: list[zipfile.ZipInfo], limits: PreflightLimits
) -> None:
    total_compressed = 0
    total_uncompressed = 0
    for info in infos:
        if info.flag_bits & 0x1:
            raise ArchiveSecurityError("encrypted archive members are prohibited")
        if info.compress_type not in _ALLOWED_COMPRESSION:
            raise ArchiveSecurityError("unsupported compression method")
        mode = (info.external_attr >> 16) & 0xFFFF
        file_type = stat.S_IFMT(mode)
        if info.is_dir() or file_type not in (0, stat.S_IFREG):
            raise ArchiveSecurityError("directories, links, and special members are prohibited")
        total_compressed += info.compress_size
        total_uncompressed += info.file_size
        ratio = (
            info.file_size / info.compress_size
            if info.compress_size
            else (float("inf") if info.file_size else 1.0)
        )
        if ratio > limits.max_compression_ratio:
            raise ArchiveSecurityError("compression ratio limit exceeded")
    if total_compressed > limits.max_compressed_bytes:
        raise ArchiveSecurityError("compressed-size limit exceeded")
    if total_uncompressed > limits.max_uncompressed_bytes:
        raise ArchiveSecurityError("uncompressed-size limit exceeded")


def _bounded_read(stream: BinaryIO, maximum: int, label: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := stream.read(min(_CHUNK_SIZE, maximum - total + 1)):
        total += len(chunk)
        if total > maximum:
            raise ArchiveSecurityError(f"{label} size limit exceeded")
        chunks.append(chunk)
    return b"".join(chunks)


def _stream_to_temporary(
    stream: BinaryIO, target: BinaryIO, maximum: int
) -> int:
    total = 0
    while chunk := stream.read(_CHUNK_SIZE):
        total += len(chunk)
        if total > maximum:
            raise ArchiveSecurityError("evidence uncompressed-size limit exceeded")
        target.write(chunk)
    target.flush()
    os.fsync(target.fileno())
    return total


def _state_path(config: IngressConfig, handoff_id: str) -> Path:
    key = hashlib.sha256(handoff_id.encode("utf-8")).hexdigest()
    return config.ingress_state_dir / f"{key}.json"


def _load_prior(config: IngressConfig, handoff_id: str) -> dict[str, object] | None:
    path = _state_path(config, handoff_id)
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IngressError("ingress state is unreadable") from exc
    if state.get("handoff_id") != handoff_id:
        raise IngressError("ingress state key mismatch")
    return state


def _write_state(
    config: IngressConfig, manifest: ITPManifest, result: PreflightResult
) -> None:
    config.ingress_state_dir.mkdir(parents=True, exist_ok=True)
    path = _state_path(config, manifest.handoff_id)
    state = {
        "handoff_id": manifest.handoff_id,
        "manifest_semantic_fingerprint": manifest.semantic_fingerprint,
        "official_evidence_sha256": result.official_evidence_sha256,
        "result": result.evidence_reference,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=config.ingress_state_dir
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(state, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _reuse_or_conflict(
    prior: dict[str, object] | None,
    manifest: ITPManifest,
    official_sha256: str,
) -> PreflightResult | None:
    if prior is None:
        return None
    equivalent = (
        prior.get("manifest_semantic_fingerprint") == manifest.semantic_fingerprint
        and prior.get("official_evidence_sha256") == official_sha256
    )
    if not equivalent:
        raise HandoffConflictError("handoff_id conflicts with prior ingress input")
    stored = prior.get("result")
    if not isinstance(stored, str) or not stored:
        raise IngressError("prior ingress result is invalid")
    return PreflightResult(
        handoff_id=manifest.handoff_id,
        official_evidence_sha256=official_sha256,
        evidence_reference=stored,
        reused=True,
    )


def preflight_envelope(
    envelope_path: str | Path,
    config: IngressConfig,
    limits: PreflightLimits,
    storage: ObjectStorageGateway,
) -> PreflightResult:
    """Run the normative ordered preflight and preserve accepted evidence."""

    envelope = Path(envelope_path)
    if not envelope.is_file():
        raise ArchiveSecurityError("ZIP container is not a regular file")
    if envelope.stat().st_size > limits.max_compressed_bytes:
        raise ArchiveSecurityError("compressed-size limit exceeded")

    temporary_path: Path | None = None
    try:
        # 1. ZIP container validation; 2. central-directory inspection.
        try:
            archive = zipfile.ZipFile(envelope, "r")
            infos = archive.infolist()
        except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as exc:
            raise ArchiveSecurityError("invalid ZIP container") from exc

        with archive:
            # 3. member names; 4. encryption/special metadata; 5. limits.
            _validate_member_names(infos)
            _validate_member_metadata(infos, limits)
            info_by_name = {info.filename: info for info in infos}

            # 6. bounded manifest read; 7. UTF-8/JSON; 8. ITP schema.
            try:
                with archive.open(info_by_name["manifest.json"], "r") as stream:
                    manifest_bytes = _bounded_read(
                        stream, limits.max_manifest_bytes, "manifest"
                    )
                manifest = parse_manifest(manifest_bytes)
                if envelope.name != f"{manifest.handoff_id}.zip":
                    raise IngressError(
                        "finalized envelope filename does not match manifest handoff_id"
                    )
                if manifest.byte_size != info_by_name["evidence.pdf"].file_size:
                    raise IngressError(
                        "byte_size does not match evidence central-directory size"
                    )
            except ManifestValidationError as exc:
                raise IngressError(str(exc)) from exc
            except (RuntimeError, zipfile.BadZipFile, OSError) as exc:
                raise ArchiveSecurityError("manifest member could not be read safely") from exc

            # 9. bounded streaming evidence extraction to quarantine.
            config.quarantine_dir.mkdir(parents=True, exist_ok=True)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix="preflight-", suffix=".pdf", dir=config.quarantine_dir
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as target, archive.open(
                    info_by_name["evidence.pdf"], "r"
                ) as source:
                    byte_size = _stream_to_temporary(
                        source, target, limits.max_uncompressed_bytes
                    )
            except (RuntimeError, zipfile.BadZipFile, OSError) as exc:
                raise ArchiveSecurityError("evidence member could not be read safely") from exc

        if byte_size != info_by_name["evidence.pdf"].file_size:
            raise ArchiveSecurityError("evidence size changed while streaming")

        # 10. official receiver hash; 11. candidate comparison.
        official_sha256 = sha256_file(temporary_path)
        if (
            manifest.candidate_sha256 is not None
            and manifest.candidate_sha256 != official_sha256
        ):
            raise IngressError("candidate_sha256 does not match official receiver hash")

        # 12. safe structural PDF compatibility validation.
        try:
            document = open_pdf(temporary_path)
        except PdfInspectionError as exc:
            raise IngressError("evidence is not a compatible structural PDF") from exc
        else:
            document.close()

        prior = _load_prior(config, manifest.handoff_id)
        reused = _reuse_or_conflict(prior, manifest, official_sha256)
        if reused is not None:
            return reused

        # 13. exact-byte evidence preservation, then durable ingress result.
        accepted_bytes = temporary_path.read_bytes()
        evidence_reference = storage.put(
            accepted_bytes, content_type=manifest.media_type
        )
        result = PreflightResult(
            handoff_id=manifest.handoff_id,
            official_evidence_sha256=official_sha256,
            evidence_reference=evidence_reference,
        )
        _write_state(config, manifest, result)
        return result
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
