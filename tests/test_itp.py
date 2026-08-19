from __future__ import annotations

import json

import pytest

from pipeline_juridico.itp import ITPManifest, ManifestValidationError, parse_manifest


def manifest_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "protocol_version": "1.0",
        "handoff_id": "opaque-retry-id",
        "evidence_reference": "evidence.pdf",
        "source_origin": "tribunal export batch 7",
        "retrieved_at": "2026-08-19T10:30:00-03:00",
        "collector": "process:collector",
        "media_type": "application/pdf",
        "byte_size": 123,
    }
    payload.update(overrides)
    return payload


def encode(payload: dict[str, object]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def test_parse_required_only_manifest() -> None:
    manifest = parse_manifest(encode(manifest_payload()))

    assert isinstance(manifest, ITPManifest)
    assert manifest.handoff_id == "opaque-retry-id"
    assert manifest.collector.value == "process:collector"
    assert manifest.candidate_sha256 is None


def test_parse_full_manifest_and_semantic_fingerprint_is_order_independent() -> None:
    payload = manifest_payload(
        last_modified="2026-08-18",
        candidate_sha256="a" * 64,
        legal_hints={"case": "not-canonical", "court": ["A", "B"]},
    )
    reversed_payload = dict(reversed(list(payload.items())))

    first = parse_manifest(encode(payload))
    second = parse_manifest(encode(reversed_payload))

    assert first.last_modified == "2026-08-18"
    assert first.legal_hints == payload["legal_hints"]
    assert first.semantic_fingerprint == second.semantic_fingerprint


@pytest.mark.parametrize(
    "actor", ["human:alice", "process:collector-7", "converter/1.2.3"]
)
def test_all_actor_forms_delegate_to_shared_contract(actor: str) -> None:
    assert parse_manifest(encode(manifest_payload(collector=actor))).collector.value == actor


@pytest.mark.parametrize("field", list(manifest_payload()))
def test_each_required_field_is_required(field: str) -> None:
    payload = manifest_payload()
    del payload[field]

    with pytest.raises(ManifestValidationError, match=field):
        parse_manifest(encode(payload))


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"protocol_version": "2.0"}, "protocol_version"),
        ({"handoff_id": ""}, "handoff_id"),
        ({"evidence_reference": "other.pdf"}, "evidence_reference"),
        ({"source_origin": ""}, "source_origin"),
        ({"retrieved_at": "2026-08-19T10:30:00"}, "retrieved_at"),
        ({"collector": "collector"}, "collector"),
        ({"media_type": "text/plain"}, "media_type"),
        ({"byte_size": 0}, "byte_size"),
        ({"byte_size": True}, "byte_size"),
        ({"last_modified": "19/08/2026"}, "last_modified"),
        ({"candidate_sha256": "A" * 64}, "candidate_sha256"),
        ({"legal_hints": []}, "legal_hints"),
    ],
)
def test_invalid_manifest_values_are_rejected(
    override: dict[str, object], field: str
) -> None:
    with pytest.raises(ManifestValidationError, match=field):
        parse_manifest(encode(manifest_payload(**override)))


def test_unknown_manifest_field_is_rejected_by_strict_schema() -> None:
    with pytest.raises(ManifestValidationError, match="unknown"):
        parse_manifest(encode(manifest_payload(unknown="value")))


def test_malformed_utf8_is_rejected() -> None:
    with pytest.raises(ManifestValidationError, match="UTF-8"):
        parse_manifest(b"\xff")


def test_malformed_json_is_rejected() -> None:
    with pytest.raises(ManifestValidationError, match="JSON"):
        parse_manifest(b"{")


@pytest.mark.parametrize(
    "data",
    [
        b'{"protocol_version":"1.0","protocol_version":"1.0"}',
        b'{"byte_size":NaN}',
    ],
)
def test_non_strict_json_constructs_are_rejected(data: bytes) -> None:
    with pytest.raises(ManifestValidationError, match="JSON"):
        parse_manifest(data)
