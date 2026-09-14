from pathlib import Path

import pytest

from pipeline_juridico.ingest_router import classify_by_prefix
from pipeline_juridico.legal_producer import LegalConceptType


@pytest.mark.parametrize("prefix, expected", [
    ("LEG_", LegalConceptType.Legislacao),
    ("JUR_", LegalConceptType.Jurisprudencia),
    ("PRE_", LegalConceptType.PrecedenteVinculante),
    ("TEM_", LegalConceptType.TemaJuridico),
])
def test_exact_prefixes(prefix, expected) -> None:
    result = classify_by_prefix(f"{prefix}qualquer texto.pdf")
    assert result.path == Path(f"{prefix}qualquer texto.pdf")
    assert result.concept_type is expected
    assert not result.blocked


@pytest.mark.parametrize("name", [
    "arquivo.pdf", "LE.pdf", "leg_lei.pdf", "xLEG_lei.pdf", "LEGS_lei.pdf",
])
def test_invalid_variants_are_never_coerced(name: str) -> None:
    result = classify_by_prefix(name)
    assert result.blocked_reason == "invalid_or_missing_prefix"
    assert result.concept_type is None


@pytest.mark.parametrize("name", ["LEG_readme.txt", "LEG_lei.PDF", "LEG_lei"])
def test_non_pdf_is_explicitly_blocked(name: str) -> None:
    result = classify_by_prefix(name)
    assert result.blocked_reason == "unsupported_media_type"
