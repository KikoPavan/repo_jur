import os
import shutil
import pytest
import uuid
import json
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from pipeline_juridico.config import IntakeConfig, IngressConfig
from pipeline_juridico.intake_manager import IntakeManager, IntakeState, IntakeRegistryEntry, ObservedSource, ManifestData
from pipeline_juridico.intake_orchestrator import IntakeOrchestrator
from pipeline_juridico.hashing import sha256_file
from pipeline_juridico.legal_producer import LegalConceptType, DuplicateResolution, ProducerRunResult, LegalProducerBlockedError
from pipeline_juridico.models import Relatorio, InputInfo, ResultadoPagina, Phase1Info, Metodo, ResultadoInfo

@pytest.fixture
def temp_env(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    for d in ["legislacao", "jurisprudencia", "temas", "precedentes"]:
        (input_dir / d).mkdir()
        (input_dir / d / ".gitkeep").touch()

    var_dir = tmp_path / "var"
    registry_dir = var_dir / "intake/registry"
    registry_dir.mkdir(parents=True)
    processing_dir = var_dir / "intake/processing"
    processing_dir.mkdir(parents=True)
    failed_dir = var_dir / "intake/failed"
    failed_dir.mkdir(parents=True)
    inbox_dir = var_dir / "ingress/inbox"
    inbox_dir.mkdir(parents=True)
    storage_root = var_dir / "object-storage"
    storage_root.mkdir(parents=True)

    (tmp_path / "output").mkdir()
    (tmp_path / "logs").mkdir()
    (var_dir / "routing/state").mkdir(parents=True)
    (tmp_path / "bundle").mkdir()
    (tmp_path / "bundle" / "legislacao").mkdir()
    (tmp_path / "bundle" / "jurisprudencia").mkdir()
    (tmp_path / "bundle" / "temas").mkdir()
    (tmp_path / "bundle" / "precedentes").mkdir()

    config = IntakeConfig(
        input_dir=input_dir,
        registry_dir=registry_dir,
        processing_dir=processing_dir,
        failed_dir=failed_dir,
        lease_timeout_seconds=5
    )
    ingress_config = IngressConfig(
        inbox_dir=inbox_dir,
        object_storage_root=storage_root
    )
    return config, ingress_config, tmp_path

# --- 1. Identidade, Tipo e Mapeamento ---

def test_type_mapping_correct(temp_env):
    config, _, _ = temp_env
    manager = IntakeManager(config)

    mappings = {
        "legislacao": LegalConceptType.Legislacao,
        "jurisprudencia": LegalConceptType.Jurisprudencia,
        "temas": LegalConceptType.TemaJuridico,
        "precedentes": LegalConceptType.PrecedenteVinculante,
    }

    for folder, expected_type in mappings.items():
        pdf = config.input_dir / folder / f"test_{folder}.pdf"
        pdf.write_bytes(f"%PDF-1.4\ncontent {folder}".encode())
        entry = manager.claim_file(pdf)
        assert entry is not None
        assert entry.okf_type == expected_type

def test_root_pdf_ignored_and_reported(temp_env, caplog):
    config, ingress_config, _ = temp_env
    pdf = config.input_dir / "unclassified.pdf"
    pdf.write_bytes(b"%PDF-1.4\nroot content")

    orch = IntakeOrchestrator(config, ingress_config, logging.getLogger("test"))
    with caplog.at_level(logging.WARNING):
        orch.scan_and_process()

    assert "SKIP_UNCLASSIFIED" in caplog.text
    assert pdf.exists()

    manager = IntakeManager(config)
    assert manager.load_entry(sha256_file(pdf)) is None

# --- 2. Concorrência, Lease e Heartbeat ---

def test_lease_claim_id_isolation(temp_env):
    config, _, _ = temp_env
    pdf = config.input_dir / "jurisprudencia" / "concy.pdf"
    pdf.write_bytes(b"%PDF-1.4\nconcy")

    m1 = IntakeManager(config, claim_id="CLAIM_1")
    e1 = m1.claim_file(pdf)
    assert e1 is not None

    m2 = IntakeManager(config, claim_id="CLAIM_2")
    pdf2 = config.input_dir / "jurisprudencia" / "dup_concy.pdf"
    pdf2.write_bytes(b"%PDF-1.4\nconcy")
    e2 = m2.claim_file(pdf2)

    assert e2 is None

def test_old_worker_blocked_after_takeover(temp_env):
    config, _, _ = temp_env
    pdf = config.input_dir / "jurisprudencia" / "stale.pdf"
    pdf.write_bytes(b"%PDF-1.4\nstale")

    m1 = IntakeManager(config, claim_id="CLAIM_1")
    e1 = m1.claim_file(pdf)
    assert e1 is not None
    assert e1.lease is not None

    e1.lease.heartbeat_at = "2000-01-01T00:00:00+00:00"
    m1.save_entry_atomic(e1)

    m2 = IntakeManager(config, claim_id="CLAIM_2")
    pdf2 = config.input_dir / "jurisprudencia" / "takeover.pdf"
    pdf2.write_bytes(b"%PDF-1.4\nstale")
    e2 = m2.claim_file(pdf2)
    assert e2 is not None
    assert e2.lease is not None
    assert e2.lease.claim_id == "CLAIM_2"

    with pytest.raises(RuntimeError, match="não possui o lease ativo"):
        m1.save_entry_atomic(e2)

# --- 3. Imutabilidade e Ocorrência ---

def test_new_occurrence_different_handoff_id(temp_env):
    config, _, _ = temp_env
    pdf = config.input_dir / "jurisprudencia" / "occ.pdf"
    pdf.write_bytes(b"%PDF-1.4\nocc")

    manager = IntakeManager(config)
    e1 = manager.claim_file(pdf)
    assert e1 is not None
    h1 = e1.handoff_id

    e1.state = IntakeState.PUBLISHED
    manager.save_entry_atomic(e1)
    (config.processing_dir / f"{e1.sha256}.pdf").unlink()

    pdf2 = config.input_dir / "jurisprudencia" / "occ2.pdf"
    pdf2.write_bytes(b"%PDF-1.4\nocc")
    e2 = manager.claim_file(pdf2)
    assert e2 is not None
    assert e2.handoff_id != h1
    assert e2.state == IntakeState.PROCESSING

def test_recovery_same_occurrence_same_handoff_id(temp_env):
    config, _, _ = temp_env
    pdf = config.input_dir / "jurisprudencia" / "recov.pdf"
    pdf.write_bytes(b"%PDF-1.4\nrecov")

    manager = IntakeManager(config)
    e1 = manager.claim_file(pdf)
    assert e1 is not None
    h1 = e1.handoff_id
    t1 = e1.manifest_data.retrieved_at

    assert e1.lease is not None
    e1.lease.heartbeat_at = "2000-01-01T00:00:00+00:00"
    manager.save_entry_atomic(e1)

    shutil.move(str(config.processing_dir / f"{e1.sha256}.pdf"), str(config.input_dir / "jurisprudencia" / "recov.pdf"))
    e2 = manager.claim_file(config.input_dir / "jurisprudencia" / "recov.pdf")

    assert e2 is not None
    assert e2.handoff_id == h1
    assert e2.manifest_data.retrieved_at == t1

# --- 4. Integridade e Deduplicação ---

def test_published_missing_bundle_becomes_failed(temp_env):
    config, ingress_config, _ = temp_env
    manager = IntakeManager(config)

    pdf = config.input_dir / "jurisprudencia" / "missing.pdf"
    pdf.write_bytes(b"%PDF-1.4\nmissing")
    e = manager.claim_file(pdf)
    assert e is not None

    e.state = IntakeState.PUBLISHED
    e.evidence_reference = "evidence.pdf"
    e.concept_id = "jurisprudencia/missing.md"
    manager.save_entry_atomic(e)
    (config.processing_dir / f"{e.sha256}.pdf").unlink()

    orch = IntakeOrchestrator(config, ingress_config, logging.getLogger("test"))
    pdf_dup = config.input_dir / "jurisprudencia" / "missing_dup.pdf"
    pdf_dup.write_bytes(b"%PDF-1.4\nmissing")

    orch.scan_and_process()

    e2 = manager.load_entry(e.sha256)
    assert e2 is not None
    assert e2.state == IntakeState.FAILED
    assert (config.failed_dir / f"{e.sha256}.pdf").exists()

# --- 5. E2E Operational Test ---

@patch("pipeline_juridico.intake_orchestrator.convert_document")
@patch("pipeline_juridico.intake_orchestrator.LegalSemanticReviewEngine")
@patch("pipeline_juridico.intake_orchestrator.produce")
@patch("pipeline_juridico.intake_orchestrator.preflight_envelope")
def test_full_e2e_flow(mock_preflight, mock_produce, mock_review, mock_convert, temp_env):
    config, ingress_config, tmp_path = temp_env

    pdf = config.input_dir / "legislacao" / "doc.pdf"
    content = b"%PDF-1.4\npdf binary content"
    pdf.write_bytes(content)
    sha = sha256_file(pdf)

    mock_preflight.return_value = MagicMock(evidence_reference="evidence.pdf")

    rel = Relatorio(
        input=InputInfo(sha256=sha, page_count=1),
        pages=[ResultadoPagina(page_number=1, method=Metodo.texto_nativo, char_count=100, errors=[], warnings=[])],
        phase1=Phase1Info(implementation="test"),
        result=ResultadoInfo(quality_gate="PASS")
    )
    mock_convert.return_value = ("[[Pág. 1]]\n# My Legislative Markdown", rel)

    mock_review_inst = MagicMock()
    mock_review.return_value = mock_review_inst
    mock_review_inst.review.return_value = MagicMock()

    concept_path = tmp_path / "bundle" / "legislacao" / "concept.md"
    mock_produce.return_value = ProducerRunResult(candidate=None, resolution=DuplicateResolution.NEW_CONCEPT, materiality=None, written=True, concept_path=concept_path)
    concept_path.touch()

    (ingress_config.object_storage_root / "evidence.pdf").touch()

    orch = IntakeOrchestrator(config, ingress_config, logging.getLogger("test"), bundle_root=tmp_path / "bundle")
    orch.output_dir = tmp_path / "output"
    orch.logs_dir = tmp_path / "logs"

    orch.scan_and_process()

    manager = IntakeManager(config)
    entry = manager.load_entry(sha)
    assert entry is not None
    assert entry.state == IntakeState.PUBLISHED
    assert entry.concept_id == "legislacao/concept.md"
    assert not (config.processing_dir / f"{sha}.pdf").exists()

# --- 6. Review Required Handling ---

@patch("pipeline_juridico.intake_orchestrator.convert_document")
@patch("pipeline_juridico.intake_orchestrator.LegalSemanticReviewEngine")
@patch("pipeline_juridico.intake_orchestrator.produce")
@patch("pipeline_juridico.intake_orchestrator.preflight_envelope")
def test_review_required_remains_preserved(mock_preflight, mock_produce, mock_review, mock_convert, temp_env):
    config, ingress_config, tmp_path = temp_env
    pdf = config.input_dir / "jurisprudencia" / "review.pdf"
    pdf.write_bytes(b"%PDF-1.4\nreview")
    sha = sha256_file(pdf)

    mock_preflight.return_value = MagicMock(evidence_reference="evidence.pdf")
    rel = Relatorio(
        input=InputInfo(sha256=sha, page_count=1),
        pages=[ResultadoPagina(page_number=1, method=Metodo.texto_nativo, char_count=100, errors=[], warnings=[])],
        phase1=Phase1Info(implementation="test"),
        result=ResultadoInfo(quality_gate="PASS")
    )
    mock_convert.return_value = ("[[Pág. 1]]\n# Markdown", rel)
    mock_review_inst = MagicMock()
    mock_review.return_value = mock_review_inst
    mock_review_inst.review.return_value = MagicMock()

    # Simulate LegalProducerBlockedError(review_required)
    mock_produce.side_effect = LegalProducerBlockedError("Review needed", reason="review_required")

    orch = IntakeOrchestrator(config, ingress_config, logging.getLogger("test"), bundle_root=tmp_path / "bundle")
    orch.output_dir = tmp_path / "output"
    orch.logs_dir = tmp_path / "logs"

    orch.scan_and_process()

    manager = IntakeManager(config)
    entry = manager.load_entry(sha)
    assert entry is not None
    assert entry.state == IntakeState.PRESERVED
    assert (config.processing_dir / f"{sha}.pdf").exists()
    assert entry.concept_id is None

# --- 7. Zero Write and Privacy ---

def test_intake_zero_write_in_bundle(temp_env):
    config, _, tmp_path = temp_env
    manager = IntakeManager(config)
    pdf = config.input_dir / "jurisprudencia" / "test.pdf"
    pdf.write_bytes(b"%PDF-1.4\nbinary")
    manager.claim_file(pdf)
    assert len(list((tmp_path / "bundle" / "jurisprudencia").iterdir())) == 0

def test_partial_ignored(temp_env):
    config, _, _ = temp_env
    pdf = config.input_dir / "jurisprudencia" / "test.pdf.partial"
    pdf.write_bytes(b"%PDF-1.4\nbin")
    manager = IntakeManager(config)
    assert manager.claim_file(pdf) is None
