"""Deterministic Legal Knowledge concept production and guarded publication."""

from __future__ import annotations

import json
import datetime
import re
import unicodedata
import yaml
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
        """Render deterministic YAML using standard nested mappings."""
        ordered = _ordered_frontmatter(self.frontmatter)
        # Use PyYAML for standard rendering
        header = yaml.dump(
            ordered,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False,
            indent=2,
            width=1000,
        )
        return f"---\n{header}---" + "\n" + self.body


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


LEGACY_KEYS = frozenset({
    "jurisdicao",
    "ambito",
    "tipo_norma",
    "ementa",
    "tema",
    "subtema",
    "tese_fixada",
    "tribunal",
    "relator",
})

DEPRECATED_TECHNICAL_KEYS = frozenset({
    "repo_jur_evidence_sha256",
    "repo_jur_phase1",
})


PROFILE_FIELDS: dict[LegalConceptType, tuple[str, ...]] = {
    LegalConceptType.Legislacao: (
        "repo_jur_lei_numero",
        "repo_jur_lei_ano",
        "repo_jur_lei_esfera",
        "repo_jur_lei_tipo",
    ),
    LegalConceptType.Jurisprudencia: (
        "repo_jur_processo_numero",
        "repo_jur_tribunal",
        "repo_jur_relator",
        "repo_jur_data_julgamento",
        "repo_jur_ramo_direito",
    ),
    LegalConceptType.TemaJuridico: (
        "repo_jur_tema_numero",
        "repo_jur_tribunal",
    ),
    LegalConceptType.PrecedenteVinculante: (
        "repo_jur_precedente_numero",
        "repo_jur_precedente_status",
        "repo_jur_tribunal",
    ),
}
PRODUCER_OWNED_KEYS = frozenset(
    {
        "type",
        "generated",
        "sources",
        "repo_jur_pdf_hash",
        "repo_jur_pdf_hashes",
        "resource",
        "repo_jur_lei_numero",
        "repo_jur_lei_ano",
        "repo_jur_lei_esfera",
        "repo_jur_processo_numero",
        "repo_jur_tribunal",
        "repo_jur_relator",
        "repo_jur_data_julgamento",
        "repo_jur_tema_numero",
        "repo_jur_precedente_numero",
    }
)
HUMAN_OWNED_KEYS = frozenset({"status", "verified"})
SHARED_KEYS = frozenset({
    "title", "tags", "description", "stale_after",
    "repo_jur_lei_tipo",
    "repo_jur_ramo_direito",
    "repo_jur_precedente_status",
})

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


def _normalize_id(value: str) -> str:
    """Normalize a path component to canonical [a-z0-9_] form."""
    val = value.lower()
    val = unicodedata.normalize("NFKD", val).encode("ascii", "ignore").decode()
    val = re.sub(r"[^a-z0-9]+", "_", val)
    return re.sub(r"_+", "_", val).strip("_")


def _clean_number(value: str) -> str:
    """Remove dots, slashes, and other non-alphanumeric characters from numbers."""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _resolve_legal_identity(
    concept_type: LegalConceptType,
    metadata: Mapping[str, object],
    evidence_resource: str | None = None,
    report: Mapping[str, object] | None = None,
) -> str:
    """Derive positional Legal Knowledge identity from canonical metadata."""
    fake_report = report or {"input": {"sha256": "0" * 64}}

    if concept_type is LegalConceptType.Legislacao:
        ramo = _normalize_id(str(metadata.get("publication_ramo_principal", "")))
        canonical_present = any(
            key in metadata
            for key in (
                "repo_jur_lei_tipo",
                "repo_jur_lei_numero",
                "repo_jur_lei_ano",
                "repo_jur_lei_esfera",
            )
        )
        if canonical_present and not ramo:
            raise LegalProducerBlockedError(
                "missing or ambiguous publication_ramo_principal",
                reason="review_required",
            )
        if not ramo:
            return f"legislacao/{_slug(evidence_resource, fake_report)}"

        raw_tipo = _normalize_id(str(metadata.get("repo_jur_lei_tipo", "")))
        tipo_map = {
            "ordinaria": "lei",
            "complementar": "lei_complementar",
            "constituicao": "constituicao",
            "decreto": "decreto",
            "portaria": "portaria",
            "medida_provisoria": "medida_provisoria",
        }
        tipo = tipo_map.get(raw_tipo, raw_tipo)
        numero = _clean_number(str(metadata.get("repo_jur_lei_numero", "")))
        ano = _clean_number(str(metadata.get("repo_jur_lei_ano", "")))
        if tipo and numero and ano:
            filename = f"{tipo}_{numero}_{ano}"
        elif tipo and ano:
            filename = f"{tipo}_{ano}"
        elif tipo:
            filename = tipo
        else:
            filename = _slug(evidence_resource, fake_report)
        return f"legislacao/{ramo}/{filename}"

    if concept_type is LegalConceptType.Jurisprudencia:
        tribunal = _normalize_id(str(metadata.get("repo_jur_tribunal", "")))
        processo = _normalize_id(str(metadata.get("repo_jur_processo_numero", "")))
        parts = [part for part in (tribunal, processo) if part]
        filename = "_".join(parts) if parts else _slug(evidence_resource, fake_report)
        return f"jurisprudencia/{filename}"

    if concept_type is LegalConceptType.TemaJuridico:
        tribunal = _normalize_id(str(metadata.get("repo_jur_tribunal", "")))
        numero = _clean_number(str(metadata.get("repo_jur_tema_numero", "")))
        filename = f"tema_{tribunal}_{numero}" if tribunal and numero else _slug(evidence_resource, fake_report)
        return f"temas/{filename}"

    if concept_type is LegalConceptType.PrecedenteVinculante:
        tribunal = _normalize_id(str(metadata.get("repo_jur_tribunal", "")))
        numero = _clean_number(str(metadata.get("repo_jur_precedente_numero", "")))
        filename = f"precedente_{tribunal}_{numero}" if tribunal and numero else _slug(evidence_resource, fake_report)
        return f"precedentes/{filename}"

    return f"{_TYPE_DIRECTORIES[concept_type]}/{_slug(evidence_resource, fake_report)}"


def resolve_concept_path(
    concept_type: LegalConceptType,
    evidence_resource: str | None,
    bundle_root: str | Path,
    metadata: Mapping[str, object] | None = None,
) -> Path:
    root = Path(bundle_root).resolve()
    identity = _resolve_legal_identity(concept_type, metadata or {}, evidence_resource)
    candidate = (root / f"{identity}.md").resolve()
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
    """Parse the standard YAML frontmatter."""
    if not isinstance(text, str) or not text.startswith("---\n"):
        raise LegalProducerConfigurationError("candidate YAML is invalid")
    boundary = text.find("\n---\n", 4)
    if boundary < 0:
        raise LegalProducerConfigurationError("candidate YAML boundary is missing")
    try:
        frontmatter = yaml.safe_load(text[4:boundary])
    except yaml.YAMLError as error:
        raise LegalProducerConfigurationError("candidate YAML is invalid") from error
    if not isinstance(frontmatter, dict):
        raise LegalProducerConfigurationError("candidate frontmatter must be a mapping")
    raw_type = frontmatter.get("type")
    try:
        concept_type = LegalConceptType(raw_type)
    except (ValueError, TypeError) as error:
        raise LegalProducerConfigurationError("candidate type is invalid") from error
    return ConceptCandidate(concept_type, frontmatter, text[boundary + 5:], Path(path))


def validate_iso8601(val: str) -> bool:
    if not isinstance(val, str):
        return False
    try:
        # Strict ISO 8601 datetime parsing
        # Must contain time component to be a valid datetime
        if "T" not in val and " " not in val:
            return False
        datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def validate_candidate(candidate: ConceptCandidate) -> None:
    if not isinstance(candidate, ConceptCandidate):
        raise LegalProducerConfigurationError("candidate contract is invalid")
    frontmatter = candidate.frontmatter
    if frontmatter.get("type") != candidate.type.value:
        raise LegalProducerConfigurationError("candidate type does not match")
    generated = frontmatter.get("generated")
    if not isinstance(generated, dict) or not isinstance(generated.get("by"), str):
        raise LegalProducerConfigurationError("candidate generated actor is missing")
    if "at" in generated:
        at_val = generated["at"]
        if not isinstance(at_val, str) or not validate_iso8601(at_val):
            raise LegalProducerConfigurationError("candidate generated at timestamp is invalid")
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

    # Rejection of legacy, un-prefixed, or inappropriate fields
    for legacy_key in LEGACY_KEYS:
        if legacy_key in frontmatter:
            raise LegalProducerConfigurationError(f"legacy or unauthorized key '{legacy_key}' is rejected")

    for technical_key in DEPRECATED_TECHNICAL_KEYS:
        if technical_key in frontmatter:
            raise LegalProducerConfigurationError(
                f"deprecated technical key '{technical_key}' is rejected"
            )

    # Strict Mandatory and Conditional Mandatory field checks (raising LegalProducerBlockedError)
    if candidate.type is LegalConceptType.Legislacao:
        if "repo_jur_lei_esfera" not in frontmatter:
            raise LegalProducerBlockedError("missing mandatory field repo_jur_lei_esfera", reason="review_required")

        has_num = "repo_jur_lei_numero" in frontmatter
        has_ano = "repo_jur_lei_ano" in frontmatter
        if (has_num and not has_ano) or (has_ano and not has_num):
            raise LegalProducerBlockedError("missing conditional mandatory field repo_jur_lei_numero or repo_jur_lei_ano", reason="review_required")

    elif candidate.type is LegalConceptType.Jurisprudencia:
        for field in ("repo_jur_processo_numero", "repo_jur_tribunal", "repo_jur_relator", "repo_jur_data_julgamento"):
            if field not in frontmatter:
                raise LegalProducerBlockedError(f"missing mandatory field {field}", reason="review_required")

    elif candidate.type is LegalConceptType.TemaJuridico:
        # repo_jur_tema_numero is required only for official numbered themes
        # repo_jur_tribunal is required only for official court themes
        # doctrinal/abstract TemaJuridico may omit them
        if "repo_jur_tema_numero" in frontmatter and "repo_jur_tribunal" not in frontmatter:
            raise LegalProducerBlockedError("missing conditional mandatory field repo_jur_tribunal for numbered theme", reason="review_required")

    elif candidate.type is LegalConceptType.PrecedenteVinculante:
        for field in ("repo_jur_precedente_numero", "repo_jur_precedente_status", "repo_jur_tribunal"):
            if field not in frontmatter:
                raise LegalProducerBlockedError(f"missing mandatory field {field}", reason="review_required")
    rendered = candidate.render_text()
    reparsed = parse_candidate_text(rendered, candidate.path)
    if reparsed.frontmatter != frontmatter or reparsed.body != candidate.body:
        raise LegalProducerConfigurationError("candidate render is not lossless")


def classify_materiality(
    existing_candidate: ConceptCandidate,
    new_candidate: ConceptCandidate,
) -> MaterialityCategory:
    """Treat body, evidence provenance, type, or canonical legal metadata drift as material."""
    if existing_candidate.body != new_candidate.body:
        return MaterialityCategory.MATERIAL
    material_keys = {
        "type",
        "sources",
        "repo_jur_pdf_hash",
        "repo_jur_pdf_hashes",
        *{field for fields in PROFILE_FIELDS.values() for field in fields},
    }
    if any(
        existing_candidate.frontmatter.get(key) != new_candidate.frontmatter.get(key)
        for key in material_keys
    ):
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
    # Universal rejection/stripping of legacy, un-prefixed, or inappropriate fields
    for legacy_key in LEGACY_KEYS:
        merged.pop(legacy_key, None)

    for key in PRODUCER_OWNED_KEYS:
        if key in new.frontmatter:
            merged[key] = new.frontmatter[key]
        else:
            merged.pop(key, None)
    old_generated = existing.frontmatter.get("generated")
    generated: dict[str, object] = dict(new.frontmatter["generated"])  # type: ignore[arg-type,assignment]
    if isinstance(old_generated, dict) and "at" in old_generated:
        generated["at"] = old_generated["at"]
    if materiality is MaterialityCategory.MATERIAL:
        generated["at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
    physical_hash = input_hash
    local = _local_reference(context.evidence_resource)
    if local is not None and local.exists():
        if not local.is_file():
            raise LegalProducerConfigurationError("evidence resource is not a file")
        physical_hash = sha256_file(local)
        if physical_hash != input_hash:
            raise LegalProducerConfigurationError("evidence hash does not match report")

    metadata: dict[str, object] = {}
    publication_ramo: str | None = None
    allowed = PROFILE_FIELDS[context.type]
    for extracted in review_result.extracted_fields:
        if extracted.name in allowed:
            val: object = extracted.value
            if extracted.name == "repo_jur_lei_ano":
                try:
                    val = int(extracted.value)
                except ValueError:
                    pass
            metadata[extracted.name] = val
        elif context.type is LegalConceptType.Legislacao and extracted.name == "publication_ramo_principal":
            normalized = _normalize_id(extracted.value)
            if publication_ramo is not None and normalized != publication_ramo:
                raise LegalProducerBlockedError("ambiguous publication_ramo_principal", reason="review_required")
            publication_ramo = normalized

    if context.type is LegalConceptType.Legislacao:
        if not publication_ramo:
            raise LegalProducerBlockedError(
                "missing or ambiguous publication_ramo_principal",
                reason="review_required",
            )
        metadata["publication_ramo_principal"] = publication_ramo

    path = resolve_concept_path(context.type, context.evidence_resource, bundle_root, metadata=metadata)
    frontmatter: dict[str, object] = {
        "type": context.type.value,
        "generated": {"by": PRODUCER_ACTOR},
        "sources": [{
            "id": "pdf_1",
            "resource": context.evidence_resource,
            "media_type": "application/pdf",
        }],
        "repo_jur_pdf_hash": physical_hash,
    }
    for name, val in metadata.items():
        if name != "publication_ramo_principal" and name not in frontmatter:
            frontmatter[name] = val
    return ConceptCandidate(context.type, frontmatter, artifacts.markdown, path)


def _identity_signature(candidate: ConceptCandidate) -> tuple[object, ...] | None:
    fm = candidate.frontmatter
    if candidate.type is LegalConceptType.Legislacao:
        keys = ("repo_jur_lei_tipo", "repo_jur_lei_numero", "repo_jur_lei_ano", "repo_jur_lei_esfera")
    elif candidate.type is LegalConceptType.Jurisprudencia:
        keys = ("repo_jur_tribunal", "repo_jur_processo_numero")
    elif candidate.type is LegalConceptType.TemaJuridico:
        keys = ("repo_jur_tribunal", "repo_jur_tema_numero")
    else:
        keys = ("repo_jur_tribunal", "repo_jur_precedente_numero")
    values = tuple(fm.get(key) for key in keys)
    if not any(value not in (None, "") for value in values):
        return None
    return (candidate.type.value, *values)


def _find_migration_collision(candidate: ConceptCandidate, bundle_root: str | Path) -> Path | None:
    """Block only the same logical concept at an old path; allow 1 PDF -> N concepts."""
    root = Path(bundle_root).resolve()
    target = candidate.path.resolve()
    candidate_hash = candidate.frontmatter.get("repo_jur_pdf_hash")
    if not isinstance(candidate_hash, str) or not root.exists():
        return None
    signature = _identity_signature(candidate)
    for current in root.rglob("*.md"):
        if current.resolve() == target:
            continue
        try:
            existing = parse_candidate_text(current.read_text(encoding="utf-8"), current)
        except (OSError, UnicodeError, LegalProducerConfigurationError):
            continue
        if existing.frontmatter.get("repo_jur_pdf_hash") != candidate_hash or existing.type is not candidate.type:
            continue
        existing_signature = _identity_signature(existing)
        if existing.body == candidate.body or (signature is not None and existing_signature == signature):
            return current
    return None


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
            return ProducerRunResult(candidate, DuplicateResolution.HUMAN_REVIEW, materiality, False, path)
        return ProducerRunResult(existing, DuplicateResolution.NOOP, None, False, path)

    collision = _find_migration_collision(candidate, bundle_root)
    if collision is not None:
        return ProducerRunResult(
            candidate,
            DuplicateResolution.HUMAN_REVIEW,
            MaterialityCategory.MATERIAL,
            False,
            collision,
        )

    authorized = guard_legal_bundle_write(
        acting_domain=RouteTarget.LEGAL_KNOWLEDGE,
        target=path,
        legal_bundle_root=bundle_root,
    )
    write_atomic(candidate.render_text(), authorized, authorized.parent, overwrite=False)
    return ProducerRunResult(candidate, DuplicateResolution.NEW_CONCEPT, None,
                             True, authorized)
