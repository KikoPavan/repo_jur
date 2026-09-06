from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from pipeline_juridico.conversion_engine import ConversionConfig
from pipeline_juridico.legal_producer import (
    ConceptCandidate,
    LegalConceptType,
    PROFILE_FIELDS,
    _find_migration_collision,
    _resolve_legal_identity,
)
from pipeline_juridico.legal_semantic_review import _deterministic_extract


def test_shared_conversion_core_has_no_object_storage_contract() -> None:
    assert "object_storage_root" not in {field.name for field in fields(ConversionConfig)}


def test_legislation_identity() -> None:
    assert _resolve_legal_identity(
        LegalConceptType.Legislacao,
        {
            "publication_ramo_principal": "direito_civil",
            "repo_jur_lei_tipo": "ordinaria",
            "repo_jur_lei_numero": "10406",
            "repo_jur_lei_ano": 2002,
            "repo_jur_lei_esfera": "federal",
        },
        "file:///tmp/evidence.pdf",
    ) == "legislacao/direito_civil/lei_10406_2002"


def test_other_trees_are_flat() -> None:
    assert _resolve_legal_identity(
        LegalConceptType.Jurisprudencia,
        {"repo_jur_tribunal": "STJ", "repo_jur_processo_numero": "REsp 1.704.551 - SP"},
        "file:///tmp/evidence.pdf",
    ) == "jurisprudencia/stj_resp_1_704_551_sp"
    assert _resolve_legal_identity(
        LegalConceptType.TemaJuridico,
        {"repo_jur_tribunal": "STJ", "repo_jur_tema_numero": "123"},
        "file:///tmp/evidence.pdf",
    ) == "temas/tema_stj_123"
    assert _resolve_legal_identity(
        LegalConceptType.PrecedenteVinculante,
        {"repo_jur_tribunal": "STF", "repo_jur_precedente_numero": "714"},
        "file:///tmp/evidence.pdf",
    ) == "precedentes/precedente_stf_714"


def test_code_civil_branch_is_operational_only() -> None:
    extracted = _deterministic_extract(
        "[[Pág. 1]]\nPresidência da República\nLEI Nº 10.406, DE 10 DE JANEIRO DE 2002\nInstitui o Código Civil.\n"
    )
    ramo = [f for f in extracted if f.name == "publication_ramo_principal"]
    assert len(ramo) == 1 and ramo[0].value == "direito_civil"
    assert "publication_ramo_principal" not in PROFILE_FIELDS[LegalConceptType.Legislacao]


def test_incidental_code_citation_does_not_classify_branch() -> None:
    extracted = _deterministic_extract(
        "[[Pág. 1]]\nA controvérsia faz referência ao Código Civil em caráter incidental.\n"
    )
    assert not any(f.name == "publication_ramo_principal" for f in extracted)


def test_old_positional_identity_collision(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    old_path = root / "legislacao" / ("a" * 64 + ".md")
    old_path.parent.mkdir(parents=True)
    fm = {
        "type": "Legislacao",
        "generated": {"by": "repo_jur_producer/old"},
        "sources": [{"id": "pdf_1", "resource": "file:///tmp/a.pdf", "media_type": "application/pdf"}],
        "repo_jur_pdf_hash": "a" * 64,
        "repo_jur_lei_tipo": "ordinaria",
        "repo_jur_lei_numero": "10406",
        "repo_jur_lei_ano": 2002,
        "repo_jur_lei_esfera": "federal",
        "repo_jur_evidence_sha256": "a" * 64,
        "repo_jur_phase1": {"implementation": "old"},
    }
    old = ConceptCandidate(LegalConceptType.Legislacao, fm, "[[Pág. 1]]\nTexto", old_path)
    old_path.write_text(old.render_text(), encoding="utf-8")
    target = root / "legislacao" / "direito_civil" / "lei_10406_2002.md"
    new = ConceptCandidate(
        LegalConceptType.Legislacao,
        {
            "type": "Legislacao",
            "generated": {"by": "repo_jur_producer/1.0"},
            "sources": [{"id": "pdf_1", "resource": "file:///tmp/a.pdf", "media_type": "application/pdf"}],
            "repo_jur_pdf_hash": "a" * 64,
            "repo_jur_lei_tipo": "ordinaria",
            "repo_jur_lei_numero": "10406",
            "repo_jur_lei_ano": 2002,
            "repo_jur_lei_esfera": "federal",
        },
        "[[Pág. 1]]\nTexto",
        target,
    )
    assert _find_migration_collision(new, root) == old_path
    assert not target.exists()
