from __future__ import annotations

import json
import zipfile
from pathlib import Path

import fitz
import pytest

from pipeline_juridico.domain_router_cli import main
from pipeline_juridico.hashing import sha256_bytes


def valid_pdf() -> bytes:
    document = fitz.open()
    document.new_page()
    data = document.tobytes()
    document.close()
    return data


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
    manifest: dict[str, object] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = json.dumps(manifest or manifest_for(evidence)).encode()
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("evidence.pdf", evidence)
    return path


def test_ingress_cli_accepts_valid_envelope(tmp_path, monkeypatch, capsys) -> None:
    # Setup operational directories outside bundle
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INGRESS_INBOX_DIR", str(tmp_path / "inbox"))
    monkeypatch.setenv("INGRESS_QUARANTINE_DIR", str(tmp_path / "quarantine"))
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("INGRESS_STATE_DIR", str(tmp_path / "state"))

    evidence = valid_pdf()
    digest = sha256_bytes(evidence)
    envelope = write_zip(tmp_path / "handoff-1.zip", evidence)

    result = main(["ingress", str(envelope), "--json"])

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["handoff_id"] == "handoff-1"
    assert output["official_evidence_sha256"] == digest
    assert output["evidence_reference"].startswith("file://")
    assert output["reused"] is False

    # Verify evidence preserved
    preserved_path = Path(output["evidence_reference"].removeprefix("file://"))
    assert preserved_path.exists()
    assert preserved_path.read_bytes() == evidence
    assert not (tmp_path / "bundle").exists()


def test_ingress_cli_idempotency_reuses_result(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OBJECT_STORAGE_ROOT", str(tmp_path / "objects"))
    monkeypatch.setenv("INGRESS_STATE_DIR", str(tmp_path / "state"))

    evidence = valid_pdf()
    envelope = write_zip(tmp_path / "handoff-1.zip", evidence)

    # First run
    main(["ingress", str(envelope)])
    capsys.readouterr()

    # Second run
    result = main(["ingress", str(envelope), "--json"])
    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["reused"] is True


def test_ingress_cli_conflicting_handoff_fails(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("INGRESS_STATE_DIR", str(tmp_path / "state"))

    evidence = valid_pdf()
    envelope1 = write_zip(tmp_path / "handoff-1.zip", evidence)
    main(["ingress", str(envelope1)])
    capsys.readouterr()

    # Different evidence with same handoff_id
    evidence2 = evidence + b"noise"
    envelope2 = write_zip(tmp_path / "retry" / "handoff-1.zip", evidence2,
                         manifest=manifest_for(evidence2, handoff_id="handoff-1"))

    result = main(["ingress", str(envelope2), "--json"])
    assert result == 1
    output = json.loads(capsys.readouterr().out)
    assert "conflict" in output["error"].lower()


def test_ingress_cli_invalid_envelope_fails(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    envelope = tmp_path / "handoff-1.zip"
    envelope.write_bytes(b"not a zip")

    result = main(["ingress", str(envelope), "--json"])
    assert result == 1
    output = json.loads(capsys.readouterr().out)
    assert "error" in output


def test_ingress_cli_divergent_candidate_sha_fails(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.chdir(tmp_path)
    evidence = valid_pdf()
    manifest = manifest_for(evidence, candidate_sha256="f" * 64)
    envelope = write_zip(tmp_path / "handoff-1.zip", evidence, manifest=manifest)

    result = main(["ingress", str(envelope), "--json"])
    assert result == 1
    output = json.loads(capsys.readouterr().out)
    assert "candidate_sha256" in output["error"]
