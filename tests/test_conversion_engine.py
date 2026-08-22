from __future__ import annotations

import json
import zipfile
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

from pipeline_juridico.config import IngressConfig, PreflightLimits, RoutingConfig
from pipeline_juridico.conversion_engine import (
    ConversionConfig,
    ConversionEngine,
    EvidenceReferenceError,
    Phase1Artifacts,
    resolve_evidence_reference,
    strip_technical_routing_metadata,
)
from pipeline_juridico.converter import convert_document
from pipeline_juridico.evidence import LocalFilesystemObjectStorageGateway
from pipeline_juridico.hashing import sha256_bytes
from pipeline_juridico.ingress import preflight_envelope
from pipeline_juridico.report import validate_report_contract


def _create_pdf(path: Path, kind: str) -> None:
    document = fitz.open()
    if kind in {"textual", "mixed"}:
        page = document.new_page()
        page.insert_text(
            (50, 50),
            "Conteúdo jurídico nativo suficientemente longo para ser "
            "classificado como texto nativo pelo roteador.",
        )
    if kind in {"scanned", "mixed"}:
        page = document.new_page()
        pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
        pixmap.set_rect(pixmap.irect, (255, 0, 0))
        page.insert_image(page.rect, pixmap=pixmap)
    if kind == "blank":
        document.new_page()
    document.save(path)
    document.close()


def _config(tmp_path: Path, *, allow_partial: bool = False) -> ConversionConfig:
    return ConversionConfig(
        temp_root=tmp_path / "facade-temp",
        allow_partial=allow_partial,
        use_ocr=False,
    )


def _direct(source: Path, config: ConversionConfig) -> tuple[str, object]:
    return convert_document(
        source,
        output_path=str(source) + ".md",
        temp_root=config.temp_root,
        allow_partial=config.allow_partial,
        use_ocr=config.use_ocr,
        ocr_api_key=config.ocr_api_key,
        ocr_model=config.ocr_model,
        ocr_base_url=config.ocr_base_url,
        ocr_prompt_path=config.ocr_prompt_path,
        routing_config=config.routing_config,
        keep_temp=config.keep_temp,
    )


def test_resolve_file_uri_to_readable_path(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence with spaces.pdf"
    evidence.write_bytes(b"%PDF-readable")

    assert resolve_evidence_reference(evidence.resolve().as_uri()) == evidence.resolve()


@pytest.mark.parametrize(
    "reference",
    ["file:///definitely/missing/evidence.pdf", "https://example.test/evidence.pdf", "not-a-uri"],
)
def test_unresolvable_or_malformed_reference_raises(reference: str) -> None:
    with pytest.raises(EvidenceReferenceError):
        resolve_evidence_reference(reference)


def test_unreadable_reference_raises(tmp_path: Path) -> None:
    directory = tmp_path / "not-a-file.pdf"
    directory.mkdir()

    with pytest.raises(EvidenceReferenceError):
        resolve_evidence_reference(directory.resolve().as_uri())


def test_boundary_dataclasses_are_frozen_and_have_contract_defaults(tmp_path: Path) -> None:
    config = ConversionConfig(temp_root=tmp_path)
    artifacts = Phase1Artifacts(markdown="body", report_json="{}")

    assert config.allow_partial is False
    assert config.use_ocr is True
    assert config.ocr_api_key is None
    assert config.ocr_model is None
    assert config.ocr_base_url is None
    assert config.ocr_prompt_path == "prompts/ocr_literal_ptbr.txt"
    assert config.routing_config is None
    assert config.keep_temp is False
    assert artifacts.markdown == "body"
    with pytest.raises(FrozenInstanceError):
        config.use_ocr = False  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        artifacts.markdown = "changed"  # type: ignore[misc]


@pytest.mark.parametrize(
    "method", ["texto_nativo", "ocr_integral", "hibrido", "vazia", "erro"]
)
def test_strip_technical_routing_metadata_removes_only_marker_adjacent_comment(
    method: str,
) -> None:
    markdown = (
        "Conteúdo anterior\n"
        "<!-- método: texto_nativo -->\n\n"
        "[[Pág. 7]]\n"
        f"<!-- método: {method} -->\n\n"
        "Conteúdo literal posterior\n"
    )

    assert strip_technical_routing_metadata(markdown) == (
        "Conteúdo anterior\n"
        "<!-- método: texto_nativo -->\n\n"
        "[[Pág. 7]]\n\n"
        "Conteúdo literal posterior\n"
    )


@pytest.mark.parametrize(
    ("kind", "allow_partial", "expected_pages"),
    [
        ("textual", False, 1),
        ("scanned", True, 1),
        ("mixed", True, 2),
        ("blank", False, 1),
    ],
)
def test_facade_markdown_equals_direct_converter(
    tmp_path: Path, kind: str, allow_partial: bool, expected_pages: int
) -> None:
    source = tmp_path / f"{kind}.pdf"
    _create_pdf(source, kind)
    config = _config(tmp_path, allow_partial=allow_partial)

    direct_markdown, _ = _direct(source, config)
    artifacts = ConversionEngine().convert(source.resolve().as_uri(), config)
    report = json.loads(artifacts.report_json)

    assert artifacts.markdown == strip_technical_routing_metadata(direct_markdown)
    assert "<!-- método:" not in artifacts.markdown
    assert [page["page_number"] for page in report["pages"]] == list(
        range(1, expected_pages + 1)
    )
    assert all(page["method"] for page in report["pages"])
    assert all(f"[[Pág. {number}]]" in artifacts.markdown for number in range(1, expected_pages + 1))


def test_facade_preserves_converter_ocr_fallback_behavior(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "ocr-fallback.pdf"
    _create_pdf(source, "scanned")
    config = ConversionConfig(
        temp_root=tmp_path / "temp",
        allow_partial=True,
        use_ocr=True,
        ocr_api_key="non-secret-test-value",
        ocr_model="test-model",
    )

    def fail_conversion(_path: Path) -> object:
        raise RuntimeError("simulated OCR conversion failure")

    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        lambda **_kwargs: SimpleNamespace(convert=fail_conversion),
    )
    direct_markdown, _ = _direct(source, config)
    artifacts = ConversionEngine().convert(source.resolve().as_uri(), config)

    assert artifacts.markdown == strip_technical_routing_metadata(direct_markdown)


def test_technical_report_metadata_is_not_injected_into_markdown(tmp_path: Path) -> None:
    source = tmp_path / "textual.pdf"
    _create_pdf(source, "textual")
    sentinel_model = "MODEL_METADATA_MUST_STAY_IN_REPORT"
    artifacts = ConversionEngine().convert(
        source.resolve().as_uri(),
        ConversionConfig(
            temp_root=tmp_path / "temp",
            use_ocr=False,
            ocr_model=sentinel_model,
        ),
    )
    report = json.loads(artifacts.report_json)

    assert sentinel_model in artifacts.report_json
    assert sentinel_model not in artifacts.markdown
    assert "<!-- método:" not in artifacts.markdown
    assert report["pages"][0]["method"] == "texto_nativo"
    assert report["telemetry"]["ocr"]["provider"] not in artifacts.markdown
    assert report["telemetry"]["timing"]["started_at"] not in artifacts.markdown
    assert not any(warning in artifacts.markdown for page in report["pages"] for warning in page["warnings"])


def test_unresolvable_reference_creates_no_artifact_or_bundle_write(
    tmp_path: Path,
) -> None:
    bundle = Path.cwd() / "bundle"
    before = set(bundle.rglob("*")) if bundle.exists() else set()

    with pytest.raises(EvidenceReferenceError):
        ConversionEngine().convert(
            (tmp_path / "missing.pdf").resolve().as_uri(), _config(tmp_path)
        )

    after = set(bundle.rglob("*")) if bundle.exists() else set()
    assert after == before


def _write_envelope(path: Path, evidence: bytes) -> None:
    manifest = {
        "protocol_version": "1.0",
        "handoff_id": "stage2-stage3",
        "evidence_reference": "evidence.pdf",
        "source_origin": "test fixture",
        "retrieved_at": "2026-08-19T12:00:00Z",
        "collector": "process:test",
        "media_type": "application/pdf",
        "byte_size": len(evidence),
        "candidate_sha256": sha256_bytes(evidence),
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest).encode())
        archive.writestr("evidence.pdf", evidence)


def test_stage2_preflight_reference_flows_into_conversion_engine(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    _create_pdf(source, "textual")
    evidence = source.read_bytes()
    envelope = tmp_path / "stage2-stage3.zip"
    _write_envelope(envelope, evidence)
    ingress_config = IngressConfig(
        inbox_dir=tmp_path / "inbox",
        quarantine_dir=tmp_path / "quarantine",
        object_storage_root=tmp_path / "objects",
        ingress_state_dir=tmp_path / "state",
    )
    result = preflight_envelope(
        envelope,
        ingress_config,
        PreflightLimits(),
        LocalFilesystemObjectStorageGateway(ingress_config.object_storage_root),
    )
    resolved = resolve_evidence_reference(result.evidence_reference)
    config = _config(tmp_path)

    direct_markdown, _ = _direct(resolved, config)
    artifacts = ConversionEngine().convert(result.evidence_reference, config)
    report = json.loads(artifacts.report_json)
    validate_report_contract(report)

    assert artifacts.markdown == strip_technical_routing_metadata(direct_markdown)
    assert report["input"] == {
        "byte_size": len(evidence),
        "sha256": result.official_evidence_sha256,
        "page_count": 1,
    }
    assert report["telemetry"]["input_path"] == str(resolved)


def test_different_evidence_bytes_have_different_report_hashes(tmp_path: Path) -> None:
    hashes = []
    for page_count in (1, 2):
        source = tmp_path / f"source-{page_count}.pdf"
        document = fitz.open()
        for _ in range(page_count):
            document.new_page()
        document.save(source)
        document.close()
        artifacts = ConversionEngine().convert(
            source.resolve().as_uri(), _config(tmp_path)
        )
        hashes.append(json.loads(artifacts.report_json)["input"]["sha256"])

    assert hashes[0] != hashes[1]


def test_facade_source_avoids_downstream_domain_types() -> None:
    source = Path("src/pipeline_juridico/conversion_engine.py").read_text()

    assert "GateState" not in source
    assert "RouteTarget" not in source
    assert "CriticalValidationResult" not in source
    assert "bundle" not in source
    assert RoutingConfig is not None
