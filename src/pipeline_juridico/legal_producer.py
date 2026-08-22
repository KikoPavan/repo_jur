"""Deterministic Legal Knowledge concept production and guarded publication."""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import unquote, urlparse

from .contracts import (
    GateState,
    Phase1Artifacts,
    RouteTarget,
    guard_legal_bundle_write,
)
from .domain_router import RoutingDecision
from .hashing import sha256_file
from .legal_semantic_review import ReviewResult, ReviewState
from .report import ReportContractError, validate_report_contract
from .validator import write_atomic


PRODUCER_VERSION = "1.0"
PRODUCER_ACTOR = f"repo_jur_producer/{PRODUCER_VERSION}"


class LegalProducerError(Exception):
    """Base error for this module."""


class LegalProducerConfigurationError(LegalProducerError):
    """The supplied contract or candidate configuration is invalid."""


class LegalProducerBlockedError(LegalProducerError):
    """A deterministic stop that carries no candidate."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


class LegalConceptType(str, Enum):
    Legislacao = "Legislacao"
    Jurisprudencia = "Jurisprudencia"
    TemaJuridico = "TemaJuridico"
    PrecedenteVinculante = "PrecedenteVinculante"


@dataclass(frozen=True)
class ProducerContext:
    type: LegalConceptType
    evidence_resource: str | None


@dataclass(frozen=True)
class ConceptCandidate:
    type: LegalConceptType
    frontmatter: dict[str, object]
    body: str
    path: Path

    def render_text(self) -> str:
        """Render a deterministic YAML subset: one JSON scalar per YAML key."""
        ordered = _ordered_frontmatter(self.frontmatter)
        lines = ["---"]
        for key, value in ordered.items():
            encoded = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            lines.append(f"{key}: {encoded}")
        lines.append("---")
        return "\n".join(lines) + "\n" + self.body


class DuplicateResolution(str, Enum):
    NEW_CONCEPT = "new_concept"
    NOOP = "noop"
    REGENERATE = "regenerate"
    ADD_SOURCE = "add_source"
    HUMAN_REVIEW = "human_review_required"


class MaterialityCategory(str, Enum):
    TECHNICAL = "technical"
    MATERIAL = "material"


@dataclass(frozen=True)
class ProducerRunResult:
    candidate: ConceptCandidate | None
    resolution: DuplicateResolution
    materiality: MaterialityCategory | None
    written: bool
    concept_path: Path | None


PROFILE_FIELDS: dict[LegalConceptType, tuple[str, ...]] = {
    LegalConceptType.Legislacao: ("jurisdicao", "ambito", "tipo_norma"),
    LegalConceptType.Jurisprudencia: ("tribunal", "relator"),
    LegalConceptType.TemaJuridico: ("ementa", "tema", "subtema"),
    LegalConceptType.PrecedenteVinculante: ("tese_fixada", "tribunal"),
}
PRODUCER_OWNED_KEYS = frozenset(
    {
        "type",
        "generated",
        "sources",
        "repo_jur_pdf_hash",
        "repo_jur_pdf_hashes",
        "repo_jur_evidence_sha256",
        "repo_jur_phase1",
    }
    | {name for names in PROFILE_FIELDS.values() for name in names}
)
HUMAN_OWNED_KEYS = frozenset({"status", "verified"})
SHARED_KEYS = frozenset({"title", "aliases", "tags", "related"})

_PERMITTED_CONTEXT_KEYS = frozenset({"type", "evidence_resource"})
_TYPE_DIRECTORIES = {
    LegalConceptType.Legislacao: "legislacao",
    LegalConceptType.Jurisprudencia: "jurisprudencia",
    LegalConceptType.TemaJuridico: "temas",
    LegalConceptType.PrecedenteVinculante: "precedentes",
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_URI_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*\Z")
_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def validate_producer_context(
    payload: Mapping[str, object] | None,
) -> ProducerContext:
    """Validate the exact producer-context vocabulary without defaults."""
    if not isinstance(payload, Mapping):
        raise LegalProducerConfigurationError("producer context must be a mapping")
    unknown = sorted((key for key in payload if key not in _PERMITTED_CONTEXT_KEYS),
                     key=repr)
    if unknown:
        raise LegalProducerConfigurationError("unknown producer context key")
    raw_type = payload.get("type")
    if not isinstance(raw_type, str):
        raise LegalProducerConfigurationError("producer context type is required")
    try:
        concept_type = LegalConceptType(raw_type)
    except ValueError as error:
        raise LegalProducerConfigurationError("producer context type is invalid") from error
    resource = payload.get("evidence_resource")
    if resource is not None:
        if not isinstance(resource, str) or not _plausible_reference(resource):
            raise LegalProducerConfigurationError("evidence resource is invalid")
    return ProducerContext(concept_type, resource)


def _plausible_reference(value: str) -> bool:
    if not value or value != value.strip() or "\x00" in value:
        return False
    parsed = urlparse(value)
    if parsed.scheme:
        return bool(_URI_SCHEME.match(parsed.scheme)) and bool(
            parsed.netloc or parsed.path
        )
    return not any(character in value for character in "?*<>|\n\r")


def _report(artifacts: Phase1Artifacts) -> dict[str, object]:
    if not isinstance(artifacts, Phase1Artifacts):
        raise LegalProducerConfigurationError("Phase 1 artifacts are required")
    try:
        value = json.loads(artifacts.report_json)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as error:
        raise LegalProducerBlockedError(
            "technical report is invalid", reason="invalid_report"
        ) from error
    if not isinstance(value, dict):
        raise LegalProducerBlockedError(
            "technical report is invalid", reason="invalid_report"
        )
    try:
        validate_report_contract(value)
    except ReportContractError as error:
        raise LegalProducerBlockedError(
            "technical report is invalid", reason="invalid_report"
        ) from error
    gate = GateState(value["result"]["quality_gate"])
    if gate is GateState.FAIL:
        raise LegalProducerBlockedError(
            "recorded gate outcome is FAIL", reason="fail_gate"
        )
    return value


def _local_reference(resource: str) -> Path | None:
    parsed = urlparse(resource)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    if parsed.scheme:
        return None
    return Path(resource)


def _slug(resource: str | None, report: Mapping[str, object]) -> str:
    """Use evidence basename, else provenance hash; never use body content."""
    if resource:
        parsed = urlparse(resource)
        stem = Path(unquote(parsed.path) if parsed.scheme else resource).stem
    else:
        input_data = report["input"]
        stem = str(input_data["sha256"])
    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_stem.lower()).strip("_")
    return slug or str(report["input"]["sha256"])


def resolve_concept_path(
    concept_type: LegalConceptType,
    evidence_resource: str | None,
    bundle_root: str | Path,
) -> Path:
    root = Path(bundle_root).resolve()
    fake_report: dict[str, object] = {"input": {"sha256": "0" * 64}}
    candidate = (root / _TYPE_DIRECTORIES[concept_type] /
                 f"{_slug(evidence_resource, fake_report)}.md").resolve()
    if not candidate.is_relative_to(root):
        raise LegalProducerConfigurationError("concept path escapes bundle root")
    return candidate


def _ordered_frontmatter(frontmatter: Mapping[str, object]) -> dict[str, object]:
    if "type" not in frontmatter:
        raise LegalProducerConfigurationError("candidate type is missing")
    return {"type": frontmatter["type"], **{
        key: value for key, value in frontmatter.items() if key != "type"
    }}


def parse_candidate_text(text: str, path: str | Path) -> ConceptCandidate:
    """Parse the deterministic YAML subset emitted by ``render_text``."""
    if not isinstance(text, str) or not text.startswith("---\n"):
        raise LegalProducerConfigurationError("candidate YAML is invalid")
    boundary = text.find("\n---\n", 4)
    if boundary < 0:
        raise LegalProducerConfigurationError("candidate YAML boundary is missing")
    frontmatter: dict[str, object] = {}
    for line in text[4:boundary].splitlines():
        key, separator, encoded = line.partition(": ")
        if not separator or not _KEY.match(key) or key in frontmatter:
            raise LegalProducerConfigurationError("candidate YAML entry is invalid")
        try:
            frontmatter[key] = json.loads(encoded)
        except json.JSONDecodeError as error:
            raise LegalProducerConfigurationError("candidate YAML value is invalid") from error
    raw_type = frontmatter.get("type")
    try:
        concept_type = LegalConceptType(raw_type)
    except (ValueError, TypeError) as error:
        raise LegalProducerConfigurationError("candidate type is invalid") from error
    return ConceptCandidate(concept_type, frontmatter, text[boundary + 5:], Path(path))


def validate_candidate(candidate: ConceptCandidate) -> None:
    if not isinstance(candidate, ConceptCandidate):
        raise LegalProducerConfigurationError("candidate contract is invalid")
    frontmatter = candidate.frontmatter
    if frontmatter.get("type") != candidate.type.value:
        raise LegalProducerConfigurationError("candidate type does not match")
    generated = frontmatter.get("generated")
    if not isinstance(generated, dict) or not isinstance(generated.get("by"), str):
        raise LegalProducerConfigurationError("candidate generated actor is missing")
    singular = frontmatter.get("repo_jur_pdf_hash")
    plural = frontmatter.get("repo_jur_pdf_hashes")
    if singular is not None and plural is not None:
        raise LegalProducerConfigurationError("PDF cardinality fields are exclusive")
    sources = frontmatter.get("sources", [])
    if not isinstance(sources, list) or any(not isinstance(item, dict) for item in sources):
        raise LegalProducerConfigurationError("candidate sources are invalid")
    pdf_sources = [item for item in sources if item.get("media_type") == "application/pdf"]
    if singular is not None:
        if len(pdf_sources) != 1 or not isinstance(singular, str) or not _SHA256.match(singular):
            raise LegalProducerConfigurationError("singular PDF provenance is invalid")
    if plural is not None:
        if len(pdf_sources) < 2 or not isinstance(plural, dict):
            raise LegalProducerConfigurationError("plural PDF provenance is invalid")
        ids = {item.get("id") for item in pdf_sources}
        if None in ids or set(plural) != ids or any(
            not isinstance(value, str) or not _SHA256.match(value)
            for value in plural.values()
        ):
            raise LegalProducerConfigurationError("PDF source mapping is invalid")
    if pdf_sources and singular is None and plural is None:
        raise LegalProducerConfigurationError("PDF provenance is missing")
    if any(field in frontmatter for kind, names in PROFILE_FIELDS.items()
           if kind is not candidate.type for field in names
           if field not in PROFILE_FIELDS[candidate.type]):
        raise LegalProducerConfigurationError("profile field is used by the wrong type")
    rendered = candidate.render_text()
    reparsed = parse_candidate_text(rendered, candidate.path)
    if reparsed.frontmatter != frontmatter or reparsed.body != candidate.body:
        raise LegalProducerConfigurationError("candidate render is not lossless")


def classify_materiality(
    existing_candidate: ConceptCandidate,
    new_candidate: ConceptCandidate,
) -> MaterialityCategory:
    """Classify body or provenance changes as material; other drift as technical."""
    if existing_candidate.body != new_candidate.body:
        return MaterialityCategory.MATERIAL
    material_keys = {
        "sources", "repo_jur_pdf_hash", "repo_jur_pdf_hashes",
        "repo_jur_evidence_sha256", "type",
    }
    if any(existing_candidate.frontmatter.get(key) != new_candidate.frontmatter.get(key)
           for key in material_keys):
        return MaterialityCategory.MATERIAL
    return MaterialityCategory.TECHNICAL


def merge_existing_candidate(
    existing: ConceptCandidate,
    new: ConceptCandidate,
    materiality: MaterialityCategory,
    *,
    reason: str,
) -> ConceptCandidate:
    """Recompute owned fields while retaining curation and extension keys."""
    merged = dict(existing.frontmatter)
    for key in PRODUCER_OWNED_KEYS:
        if key in new.frontmatter:
            merged[key] = new.frontmatter[key]
        else:
            merged.pop(key, None)
    old_generated = existing.frontmatter.get("generated")
    generated = dict(new.frontmatter["generated"])  # type: ignore[arg-type]
    if isinstance(old_generated, dict) and "at" in old_generated:
        generated["at"] = old_generated["at"]
    if materiality is MaterialityCategory.MATERIAL:
        provenance = new.frontmatter.get("repo_jur_evidence_sha256", "unknown")
        generated["at"] = f"evidence:{provenance}"
        verified = existing.frontmatter.get("verified")
        if isinstance(verified, dict) and isinstance(verified.get("by"), str) and isinstance(
            verified.get("at"), str
        ):
            history = list(existing.frontmatter.get("repo_jur_verification_history", []))
            history.append({
                "by": verified["by"],
                "at": verified["at"],
                "invalidated_by": PRODUCER_ACTOR,
                "reason": reason,
            })
            merged["repo_jur_verification_history"] = history
        merged.pop("verified", None)
    merged["generated"] = generated
    return ConceptCandidate(new.type, _ordered_frontmatter(merged), new.body, new.path)


def _base_candidate(
    artifacts: Phase1Artifacts,
    report: Mapping[str, object],
    review_result: ReviewResult,
    context: ProducerContext,
    bundle_root: str | Path,
) -> ConceptCandidate:
    if context.evidence_resource is None:
        raise LegalProducerConfigurationError("PDF evidence resource is required")
    input_data = report["input"]
    input_hash = input_data["sha256"]
    local = _local_reference(context.evidence_resource)
    physical_hash = input_hash
    if local is not None and local.exists():
        if not local.is_file():
            raise LegalProducerConfigurationError("evidence resource is not a file")
        physical_hash = sha256_file(local)
        if physical_hash != input_hash:
            raise LegalProducerConfigurationError("evidence hash does not match report")
    path = resolve_concept_path(context.type, context.evidence_resource, bundle_root)
    phase1 = report["phase1"]
    frontmatter: dict[str, object] = {
        "type": context.type.value,
        "generated": {"by": PRODUCER_ACTOR},
        "sources": [{
            "id": "pdf_1",
            "resource": context.evidence_resource,
            "media_type": "application/pdf",
        }],
        "repo_jur_pdf_hash": physical_hash,
        "repo_jur_evidence_sha256": input_hash,
        "repo_jur_phase1": {
            key: phase1[key]
            for key in (
                "implementation", "implementation_version",
                "logical_processing_version", "relevant_config_fingerprint",
            )
        },
    }
    allowed = PROFILE_FIELDS[context.type]
    for extracted in review_result.extracted_fields:
        if extracted.name in allowed and extracted.name not in frontmatter:
            frontmatter[extracted.name] = extracted.value
    return ConceptCandidate(context.type, frontmatter, artifacts.markdown, path)


def produce(
    phase1_artifacts: Phase1Artifacts,
    routing_decision: RoutingDecision,
    review_result: ReviewResult,
    producer_context: ProducerContext,
    *,
    bundle_root: str | Path,
    overwrite: bool = False,
) -> ProducerRunResult:
    """Build, resolve, validate, authorize, and atomically publish a concept."""
    report = _report(phase1_artifacts)
    if not isinstance(routing_decision, RoutingDecision) or routing_decision.target is not RouteTarget.LEGAL_KNOWLEDGE:
        raise LegalProducerConfigurationError("routing decision is not legal_knowledge")
    if not isinstance(producer_context, ProducerContext):
        raise LegalProducerConfigurationError("validated producer context is required")
    if not isinstance(review_result, ReviewResult):
        raise LegalProducerConfigurationError("review result contract is invalid")
    if review_result.state is ReviewState.REVIEW_REQUIRED:
        raise LegalProducerBlockedError("review_required", reason="review_required")
    for suggestion in review_result.classification_suggestions:
        if suggestion.type is not None and suggestion.type != producer_context.type.value:
            raise LegalProducerBlockedError("review_required: type conflict",
                                            reason="review_required")

    candidate = _base_candidate(
        phase1_artifacts, report, review_result, producer_context, bundle_root
    )
    validate_candidate(candidate)
    path = candidate.path
    if path.exists():
        existing = parse_candidate_text(path.read_text(encoding="utf-8"), path)
        materiality = classify_materiality(existing, candidate)
        if materiality is MaterialityCategory.MATERIAL:
            return ProducerRunResult(candidate, DuplicateResolution.HUMAN_REVIEW,
                                     materiality, False, path)
        merged = merge_existing_candidate(
            existing, candidate, materiality, reason="technical producer change"
        )
        old_phase1 = existing.frontmatter.get("repo_jur_phase1")
        new_phase1 = candidate.frontmatter.get("repo_jur_phase1")
        if old_phase1 == new_phase1:
            return ProducerRunResult(existing, DuplicateResolution.NOOP, None, False, path)
        validate_candidate(merged)
        authorized = guard_legal_bundle_write(
            acting_domain=RouteTarget.LEGAL_KNOWLEDGE,
            target=path,
            legal_bundle_root=bundle_root,
        )
        write_atomic(merged.render_text(), authorized, authorized.parent, overwrite=overwrite)
        return ProducerRunResult(merged, DuplicateResolution.REGENERATE,
                                 materiality, True, authorized)

    authorized = guard_legal_bundle_write(
        acting_domain=RouteTarget.LEGAL_KNOWLEDGE,
        target=path,
        legal_bundle_root=bundle_root,
    )
    write_atomic(candidate.render_text(), authorized, authorized.parent, overwrite=False)
    return ProducerRunResult(candidate, DuplicateResolution.NEW_CONCEPT, None,
                             True, authorized)
