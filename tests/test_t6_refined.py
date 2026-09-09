
from __future__ import annotations

import json
from pathlib import Path

from pipeline_juridico.contracts import Phase1Artifacts, RouteTarget
from pipeline_juridico.domain_router import RoutingDecision, RoutingReasonCode
from pipeline_juridico.legal_producer import (
    ConceptCandidate,
    DuplicateResolution,
    LegalConceptType,
    MaterialityCategory,
    ProducerContext,
    _resolve_legal_identity,
    classify_materiality,
    merge_existing_candidate,
    produce,
)
from pipeline_juridico.legal_semantic_review import (
    ExtractedField,
    ReviewResult,
    ReviewState,
    _deterministic_extract,
)

# Setup standard report for tests
REPORT = {
    "schema_version": "1.0",
    "execution_id": "test_id",
    "input": {
        "sha256": "a" * 64,
        "byte_size": 100,
        "page_count": 1
    },
    "phase1": {
        "implementation": "test",
        "implementation_version": "1.0",
        "logical_processing_version": "1.0",
        "relevant_config_fingerprint": "test"
    },
    "result": {
        "quality_gate": "PASS",
        "warnings": [],
        "errors": []
    },
    "artifacts": {
        "markdown_sha256": "a" * 64
    },
    "pages": [
        {
            "page_number": 1,
            "method": "texto_nativo",
            "char_count": 10,
            "warnings": [],
            "errors": [],
            "truncated": False
        }
    ],
    "telemetry": {}
}
REPORT_STR = json.dumps(REPORT)

def test_normas_referenciadas_availability_in_all_types(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    
    norms = [{"concept_id": "legislacao/direito_civil/lei_10406_2002"}]
    
    types_to_test = [
        (LegalConceptType.Jurisprudencia, "jurisprudencia/stj_123"),
        (LegalConceptType.TemaJuridico, "temas/tema_stj_1"),
        (LegalConceptType.PrecedenteVinculante, "precedentes/precedente_stf_1")
    ]
    
    for c_type, expected_path in types_to_test:
        review = ReviewResult(
            state=ReviewState.OK,
            patches=(),
            extracted_fields=(
                ExtractedField("repo_jur_normas_referenciadas", norms),
                ExtractedField("repo_jur_processo_numero", "123") if c_type == LegalConceptType.Jurisprudencia else ExtractedField("repo_jur_tribunal", "STJ"),
                ExtractedField("repo_jur_tribunal", "STJ"),
                ExtractedField("repo_jur_relator", "MINISTRO") if c_type == LegalConceptType.Jurisprudencia else ExtractedField("repo_jur_tema_numero", "1") if c_type == LegalConceptType.TemaJuridico else ExtractedField("repo_jur_precedente_numero", "1"),
                ExtractedField("repo_jur_data_julgamento", "2026-01-01") if c_type == LegalConceptType.Jurisprudencia else ExtractedField("repo_jur_precedente_status", "ativo") if c_type == LegalConceptType.PrecedenteVinculante else ExtractedField("repo_jur_tribunal", "STJ"),
            ),
            classification_suggestions=(),
            warnings=()
        )
        
        artifacts = Phase1Artifacts(markdown="body", report_json=REPORT_STR)
        decision = RoutingDecision(target=RouteTarget.LEGAL_KNOWLEDGE, reason=RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE)
        context = ProducerContext(type=c_type, evidence_resource="file:///tmp/a.pdf")
        
        result = produce(artifacts, decision, review, context, bundle_root=root, overwrite=True)
        assert "repo_jur_normas_referenciadas" in result.candidate.frontmatter
        assert result.candidate.frontmatter["repo_jur_normas_referenciadas"] == norms

def test_article_association_negative_scenario() -> None:
    # Scenario: CC + article correctly linked, CPC mentioned but not linked to art.
    markdown = "[[Pág. 1]]\nConforme o art. 421 do Código Civil e também o art. 85 do CPC."
    extracted = _deterministic_extract(markdown)
    norms_field = next(f for f in extracted if f.name == "repo_jur_normas_referenciadas")
    
    # art. 421 should be in CC/2002
    cc_ref = next(n for n in norms_field.value if n["concept_id"] == "legislacao/direito_civil/lei_10406_2002")
    assert "421" in cc_ref["artigos"]
    # art. 85 should NOT be in CC/2002 because it's linked to CPC
    assert "85" not in cc_ref["artigos"]

def test_norm_link_without_articles() -> None:
    # Scenario: Law identified but no specific article linked
    markdown = "[[Pág. 1]]\nA Lei 10.406/2002 é fundamental para o caso."
    extracted = _deterministic_extract(markdown)
    norms_field = next(f for f in extracted if f.name == "repo_jur_normas_referenciadas")
    cc_ref = next(n for n in norms_field.value if n["concept_id"] == "legislacao/direito_civil/lei_10406_2002")
    assert "artigos" not in cc_ref

def test_ramo_direito_materiality_and_merging(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    
    # 1. Compatibility: String vs List equivalence for Materiality
    c1 = ConceptCandidate(LegalConceptType.Jurisprudencia, {"repo_jur_ramo_direito": "DIREITO CIVIL"}, "body", Path("a.md"))
    c2 = ConceptCandidate(LegalConceptType.Jurisprudencia, {"repo_jur_ramo_direito": ["DIREITO CIVIL"]}, "body", Path("a.md"))
    assert classify_materiality(c1, c2) == MaterialityCategory.TECHNICAL
    
    # 2. Materiality: Adding a NEW branch is MATERIAL
    c3 = ConceptCandidate(LegalConceptType.Jurisprudencia, {"repo_jur_ramo_direito": ["DIREITO CIVIL", "DIREITO PENAL"]}, "body", Path("a.md"))
    assert classify_materiality(c1, c3) == MaterialityCategory.MATERIAL
    
    # 3. Merging: Preserve existing human values
    existing_fm = {
        "type": "Jurisprudencia",
        "generated": {"by": "old", "at": "2026-01-01T00:00:00Z"},
        "repo_jur_ramo_direito": "DIREITO CIVIL",
        "repo_jur_processo_numero": "123",
        "repo_jur_tribunal": "STJ",
        "repo_jur_relator": "MINISTRO",
        "repo_jur_data_julgamento": "2026-01-01",
        "sources": [{"id": "pdf_1", "resource": "file:///tmp/a.pdf", "media_type": "application/pdf"}],
        "repo_jur_pdf_hash": "a" * 64
    }
    path = root / "jurisprudencia" / "stj_123.md"
    path.parent.mkdir(exist_ok=True)
    c_existing = ConceptCandidate(LegalConceptType.Jurisprudencia, existing_fm, "body", path)
    path.write_text(c_existing.render_text())
    
    # Review with NEW branch
    review = ReviewResult(
        state=ReviewState.OK,
        patches=(),
        extracted_fields=(
            ExtractedField("repo_jur_ramo_direito", ["DIREITO PROCESSUAL CIVIL"]),
            ExtractedField("repo_jur_processo_numero", "123"),
            ExtractedField("repo_jur_tribunal", "STJ"),
            ExtractedField("repo_jur_relator", "MINISTRO"),
            ExtractedField("repo_jur_data_julgamento", "2026-01-01"),
        ),
        classification_suggestions=(),
        warnings=()
    )
    
    artifacts = Phase1Artifacts(markdown="body", report_json=REPORT_STR)
    decision = RoutingDecision(target=RouteTarget.LEGAL_KNOWLEDGE, reason=RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE)
    context = ProducerContext(type=LegalConceptType.Jurisprudencia, evidence_resource="file:///tmp/a.pdf")
    
    # Regenerate should result in Human Review because it's MATERIAL (new branch)
    result = produce(artifacts, decision, review, context, bundle_root=root, overwrite=True)
    assert result.resolution == DuplicateResolution.HUMAN_REVIEW
    assert result.materiality == MaterialityCategory.MATERIAL
    
    # If we force overwrite/update, it should merge them
    merged = merge_existing_candidate(c_existing, result.candidate, result.materiality, reason="update")
    assert isinstance(merged.frontmatter["repo_jur_ramo_direito"], list)
    assert "DIREITO CIVIL" in merged.frontmatter["repo_jur_ramo_direito"]
    assert "DIREITO PROCESSUAL CIVIL" in merged.frontmatter["repo_jur_ramo_direito"]

def test_precedente_especie_filename() -> None:
    # Test that sumula species is reflected in filename
    metadata = {
        "repo_jur_tribunal": "STF",
        "repo_jur_precedente_numero": "714",
        "repo_jur_precedente_especie": "sumula"
    }
    path = _resolve_legal_identity(LegalConceptType.PrecedenteVinculante, metadata)
    assert path == "precedentes/sumula_stf_714"

    # Test fallback
    metadata_generic = {
        "repo_jur_tribunal": "STJ",
        "repo_jur_precedente_numero": "123"
    }
    path_generic = _resolve_legal_identity(LegalConceptType.PrecedenteVinculante, metadata_generic)
    assert path_generic == "precedentes/precedente_stj_123"

def test_repo_jur_normas_referenciadas_preservation(tmp_path: Path) -> None:
    root = tmp_path / "bundle"
    root.mkdir()
    
    # 1. Existing concept with curated norms
    curated_norms = [{"concept_id": "legislacao/direito_civil/lei_10406_2002", "artigos": ["1"]}]
    existing_fm = {
        "type": "Jurisprudencia",
        "generated": {"by": "human", "at": "2026-01-01T00:00:00Z"},
        "repo_jur_normas_referenciadas": curated_norms,
        "repo_jur_processo_numero": "123",
        "repo_jur_tribunal": "STJ",
        "repo_jur_relator": "MINISTRO",
        "repo_jur_data_julgamento": "2026-01-01",
        "sources": [{"id": "pdf_1", "resource": "file:///tmp/a.pdf", "media_type": "application/pdf"}],
        "repo_jur_pdf_hash": "a" * 64
    }
    path = root / "jurisprudencia" / "stj_123.md"
    path.parent.mkdir()
    
    c_existing = ConceptCandidate(LegalConceptType.Jurisprudencia, existing_fm, "body", path)
    path.write_text(c_existing.render_text())
    
    # 2. New review with DIFFERENT extracted norms
    extracted_norms = [{"concept_id": "legislacao/direito_civil/lei_10406_2002", "artigos": ["2"]}]
    review = ReviewResult(
        state=ReviewState.OK,
        patches=(),
        extracted_fields=(
            ExtractedField("repo_jur_normas_referenciadas", extracted_norms),
            ExtractedField("repo_jur_processo_numero", "123"),
            ExtractedField("repo_jur_tribunal", "STJ"),
            ExtractedField("repo_jur_relator", "MINISTRO"),
            ExtractedField("repo_jur_data_julgamento", "2026-01-01"),
        ),
        classification_suggestions=(),
        warnings=()
    )
    
    artifacts = Phase1Artifacts(markdown="body", report_json=REPORT_STR)
    decision = RoutingDecision(target=RouteTarget.LEGAL_KNOWLEDGE, reason=RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE)
    context = ProducerContext(type=LegalConceptType.Jurisprudencia, evidence_resource="file:///tmp/a.pdf")
    
    # Produce - it should be MATERIAL due to difference in PROFILE_FIELDS
    result = produce(artifacts, decision, review, context, bundle_root=root, overwrite=True)
    assert result.resolution == DuplicateResolution.HUMAN_REVIEW
    assert result.materiality == MaterialityCategory.MATERIAL
    
    # Verify merging logic preserves existing curated value for SHARED_KEY
    merged = merge_existing_candidate(c_existing, result.candidate, result.materiality, reason="update")
    
    # repo_jur_normas_referenciadas is SHARED, so it should be preserved if existing is not None
    assert merged.frontmatter["repo_jur_normas_referenciadas"] == curated_norms
    assert merged.frontmatter["repo_jur_normas_referenciadas"] != extracted_norms
