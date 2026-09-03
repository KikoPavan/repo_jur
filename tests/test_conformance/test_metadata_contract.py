from __future__ import annotations

import json
from pathlib import Path
import pytest

from pipeline_juridico.contracts import Phase1Artifacts, RouteTarget
from pipeline_juridico.domain_router import RoutingDecision, RoutingReasonCode
from pipeline_juridico.legal_producer import (
    LegalConceptType,
    produce,
    validate_producer_context,
)
from pipeline_juridico.legal_semantic_review import (
    LegalReviewProfile,
    LegalSemanticReviewEngine,
)

GOLDEN_DIR = Path("tests/test_conformance/golden")
CC_MD_PATH = GOLDEN_DIR / "L10.406_CC_2002.md"
CC_JSON_PATH = GOLDEN_DIR / "L10.406_CC_2002.json"

RESP_MD_PATH = GOLDEN_DIR / "REsp_1704551-SP.md"
RESP_JSON_PATH = GOLDEN_DIR / "REsp_1704551-SP.json"

AINT_MD_PATH = GOLDEN_DIR / "AINTARESP_1462304-PA.md"
AINT_JSON_PATH = GOLDEN_DIR / "AINTARESP_1462304-PA.json"


def _decision(target: RouteTarget = RouteTarget.LEGAL_KNOWLEDGE) -> RoutingDecision:
    reason = {
        RouteTarget.LEGAL_KNOWLEDGE:
            RoutingReasonCode.REQUESTED_DOMAIN_LEGAL_KNOWLEDGE,
        RouteTarget.JUDICIAL_PROCESS:
            RoutingReasonCode.REQUESTED_DOMAIN_JUDICIAL_PROCESS,
        RouteTarget.REVIEW_REQUIRED:
            RoutingReasonCode.MISSING_ROUTING_SIGNAL,
    }[target]
    return RoutingDecision(target, reason)


def test_ci_safe_golden_legislacao_conformance(tmp_path: Path) -> None:
    # 1. Load the golden files
    assert CC_MD_PATH.exists()
    assert CC_JSON_PATH.exists()

    markdown = CC_MD_PATH.read_text(encoding="utf-8")
    report_json = CC_JSON_PATH.read_text(encoding="utf-8")
    artifacts = Phase1Artifacts(markdown, report_json)

    # 2. Run semantic review engine to extract fields
    review = LegalSemanticReviewEngine().review(
        artifacts, LegalReviewProfile("default", "1.0", ())
    )

    # Verify fields extracted
    extracted_names = {f.name for f in review.extracted_fields}
    assert "repo_jur_lei_numero" in extracted_names
    assert "repo_jur_lei_ano" in extracted_names
    assert "repo_jur_lei_esfera" in extracted_names
    assert "repo_jur_lei_tipo" in extracted_names

    # Check the actual values extracted
    num_field = next(f for f in review.extracted_fields if f.name == "repo_jur_lei_numero")
    assert num_field.value == "10406"
    assert num_field.page_refs == ("1",)

    # 3. Produce candidate
    context = validate_producer_context({
        "type": "Legislacao",
        "evidence_resource": "input/L10.406_CC_2002.pdf",
    })
    result = produce(
        artifacts,
        _decision(),
        review,
        context,
        bundle_root=tmp_path / "bundle",
    )
    assert result.candidate is not None
    frontmatter = result.candidate.frontmatter

    # Verify canonical metadata profile alignment
    assert frontmatter["repo_jur_lei_numero"] == "10406"
    assert frontmatter["repo_jur_lei_ano"] == 2002
    assert frontmatter["repo_jur_lei_esfera"] == "federal"
    assert frontmatter["repo_jur_lei_tipo"] == "ordinaria"
    assert frontmatter["resource"] == "input/L10.406_CC_2002.pdf"

    # Confirm page_refs are transient and not written to canonical YAML frontmatter
    assert "page_refs" not in frontmatter

    # Verify generated.by format and generated.at exclusion / format
    generated = frontmatter["generated"]
    assert isinstance(generated, dict)
    assert generated.get("by") == "repo_jur_producer/1.0"
    if "at" in generated:
        assert "evidence:" not in str(generated.get("at"))

    # Human-owned fields: verify absence of status and verified
    assert "status" not in frontmatter
    assert "verified" not in frontmatter


def test_ci_safe_golden_jurisprudencia_resp_conformance(tmp_path: Path) -> None:
    assert RESP_MD_PATH.exists()
    assert RESP_JSON_PATH.exists()

    markdown = RESP_MD_PATH.read_text(encoding="utf-8")
    report_json = RESP_JSON_PATH.read_text(encoding="utf-8")
    artifacts = Phase1Artifacts(markdown, report_json)

    review = LegalSemanticReviewEngine().review(
        artifacts, LegalReviewProfile("default", "1.0", ())
    )

    extracted_names = {f.name for f in review.extracted_fields}
    assert "repo_jur_processo_numero" in extracted_names
    assert "repo_jur_tribunal" in extracted_names
    assert "repo_jur_relator" in extracted_names
    assert "repo_jur_data_julgamento" in extracted_names

    # Check extracted values
    proc_field = next(f for f in review.extracted_fields if f.name == "repo_jur_processo_numero")
    assert "1.704.551" in proc_field.value

    trib_field = next(f for f in review.extracted_fields if f.name == "repo_jur_tribunal")
    assert trib_field.value == "STJ"

    rel_field = next(f for f in review.extracted_fields if f.name == "repo_jur_relator")
    assert rel_field.value == "NANCY ANDRIGHI"

    data_field = next(f for f in review.extracted_fields if f.name == "repo_jur_data_julgamento")
    assert data_field.value == "2019-04-02"


def test_ci_safe_golden_jurisprudencia_aint_conformance(tmp_path: Path) -> None:
    assert AINT_MD_PATH.exists()
    assert AINT_JSON_PATH.exists()

    markdown = AINT_MD_PATH.read_text(encoding="utf-8")
    report_json = AINT_JSON_PATH.read_text(encoding="utf-8")
    artifacts = Phase1Artifacts(markdown, report_json)

    review = LegalSemanticReviewEngine().review(
        artifacts, LegalReviewProfile("default", "1.0", ())
    )

    extracted_names = {f.name for f in review.extracted_fields}
    assert "repo_jur_processo_numero" in extracted_names
    assert "repo_jur_tribunal" in extracted_names
    assert "repo_jur_relator" in extracted_names
    assert "repo_jur_data_julgamento" in extracted_names

    proc_field = next(f for f in review.extracted_fields if f.name == "repo_jur_processo_numero")
    assert "1462304" in proc_field.value

    rel_field = next(f for f in review.extracted_fields if f.name == "repo_jur_relator")
    assert rel_field.value == "GURGEL DE FARIA"

    data_field = next(f for f in review.extracted_fields if f.name == "repo_jur_data_julgamento")
    assert data_field.value == "2020-10-26"


@pytest.mark.skipif(not Path("input/L10.406_CC_2002.pdf").exists(), reason="raw PDF L10.406_CC_2002.pdf absent")
def test_opt_in_real_corpus_acceptance(tmp_path: Path) -> None:
    pdf_path = Path("input/L10.406_CC_2002.pdf")
    assert pdf_path.exists()
