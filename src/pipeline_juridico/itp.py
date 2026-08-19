"""Strict parsing for the ITP/1.0 ingress manifest."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping

from .contracts import Actor, validate_actor


class ManifestValidationError(ValueError):
    """The manifest is not valid ITP/1.0 data."""


_REQUIRED = {
    "protocol_version",
    "handoff_id",
    "evidence_reference",
    "source_origin",
    "retrieved_at",
    "collector",
    "media_type",
    "byte_size",
}
_OPTIONAL = {"last_modified", "candidate_sha256", "legal_hints"}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class ITPManifest:
    protocol_version: str
    handoff_id: str
    evidence_reference: str
    source_origin: str
    retrieved_at: str
    collector: Actor
    media_type: str
    byte_size: int
    last_modified: str | None = None
    candidate_sha256: str | None = None
    legal_hints: Mapping[str, Any] | None = None

    @property
    def semantic_fingerprint(self) -> str:
        canonical = {
            "protocol_version": self.protocol_version,
            "handoff_id": self.handoff_id,
            "evidence_reference": self.evidence_reference,
            "source_origin": self.source_origin,
            "retrieved_at": self.retrieved_at,
            "collector": self.collector.value,
            "media_type": self.media_type,
            "byte_size": self.byte_size,
        }
        if self.last_modified is not None:
            canonical["last_modified"] = self.last_modified
        if self.candidate_sha256 is not None:
            canonical["candidate_sha256"] = self.candidate_sha256
        if self.legal_hints is not None:
            canonical["legal_hints"] = self.legal_hints
        encoded = json.dumps(
            canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _zoned_datetime(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise ManifestValidationError(f"{field} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ManifestValidationError(f"{field} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ManifestValidationError(f"{field} must include a timezone")
    return value


def _last_modified(value: object) -> str:
    if not isinstance(value, str):
        raise ManifestValidationError("last_modified must be ISO-8601")
    try:
        if "T" in value or "t" in value or " " in value:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            date.fromisoformat(value)
    except ValueError as exc:
        raise ManifestValidationError("last_modified must be ISO-8601") from exc
    return value


def parse_manifest(data: bytes) -> ITPManifest:
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ManifestValidationError("manifest must be strict UTF-8") from exc

    def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON property: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> None:
        raise ValueError(f"non-standard JSON constant: {value}")

    try:
        payload = json.loads(
            text,
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except (json.JSONDecodeError, ValueError) as exc:
        raise ManifestValidationError("manifest must contain valid JSON") from exc
    if not isinstance(payload, dict):
        raise ManifestValidationError("manifest JSON must be an object")

    missing = _REQUIRED - payload.keys()
    if missing:
        raise ManifestValidationError(f"missing required field: {sorted(missing)[0]}")
    unknown = payload.keys() - _REQUIRED - _OPTIONAL
    if unknown:
        raise ManifestValidationError(f"unknown manifest field: {sorted(unknown)[0]}")

    def nonempty(field: str) -> str:
        value = payload[field]
        if not isinstance(value, str) or not value:
            raise ManifestValidationError(f"{field} must be a non-empty string")
        return value

    if payload["protocol_version"] != "1.0":
        raise ManifestValidationError("protocol_version must be 1.0")
    if payload["evidence_reference"] != "evidence.pdf":
        raise ManifestValidationError("evidence_reference must be evidence.pdf")
    if payload["media_type"] != "application/pdf":
        raise ManifestValidationError("media_type must be application/pdf")
    byte_size = payload["byte_size"]
    if isinstance(byte_size, bool) or not isinstance(byte_size, int) or byte_size <= 0:
        raise ManifestValidationError("byte_size must be a positive integer")
    try:
        collector = validate_actor(payload["collector"])
    except ValueError as exc:
        raise ManifestValidationError(f"collector is invalid: {exc}") from exc

    candidate = payload.get("candidate_sha256")
    if candidate is not None and (
        not isinstance(candidate, str) or _SHA256.fullmatch(candidate) is None
    ):
        raise ManifestValidationError("candidate_sha256 must be 64 lowercase hex")
    legal_hints = payload.get("legal_hints")
    if legal_hints is not None and not isinstance(legal_hints, dict):
        raise ManifestValidationError("legal_hints must be a mapping")

    return ITPManifest(
        protocol_version="1.0",
        handoff_id=nonempty("handoff_id"),
        evidence_reference="evidence.pdf",
        source_origin=nonempty("source_origin"),
        retrieved_at=_zoned_datetime(payload["retrieved_at"], "retrieved_at"),
        collector=collector,
        media_type="application/pdf",
        byte_size=byte_size,
        last_modified=(
            _last_modified(payload["last_modified"])
            if "last_modified" in payload
            else None
        ),
        candidate_sha256=candidate,
        legal_hints=legal_hints,
    )
