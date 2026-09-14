"""Filename-only routing for operational legal-knowledge ingestion."""

from dataclasses import dataclass
from pathlib import Path

from .legal_producer import LegalConceptType

PREFIX_MAP: dict[str, LegalConceptType] = {
    "LEG_": LegalConceptType.Legislacao,
    "JUR_": LegalConceptType.Jurisprudencia,
    "PRE_": LegalConceptType.PrecedenteVinculante,
    "TEM_": LegalConceptType.TemaJuridico,
}


@dataclass(frozen=True)
class ClassificationResult:
    path: Path
    concept_type: LegalConceptType | None
    blocked: bool
    blocked_reason: str | None


def classify_by_prefix(filename: str) -> ClassificationResult:
    """Classify solely from an exact basename prefix and extension."""
    path = Path(filename)
    name = path.name
    if not name.endswith(".pdf"):
        return ClassificationResult(
            path, None, True, "unsupported_media_type"
        )
    concept_type = PREFIX_MAP.get(name[:4])
    if concept_type is None:
        return ClassificationResult(
            path, None, True, "invalid_or_missing_prefix"
        )
    return ClassificationResult(path, concept_type, False, None)
