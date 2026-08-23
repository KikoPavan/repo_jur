"""Deterministic process candidate production and guarded publication."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from urllib.parse import unquote, urlparse

from .contracts import GateState, Phase1Artifacts, RouteTarget
from .domain_router import RoutingDecision
from .hashing import sha256_file
from .process_semantic_review import ProcessReviewResult, ReviewState
from .process_storage import (
    PROCESS_PRODUCER_OWNED_KEYS,
    PROCESS_PROFILE_FIELDS,
    ProcessConceptType,
    ProcessProducerBlockedError,
    ProcessProducerConfigurationError,
    ProcessProducerContext,
    _KEY,
    _SHA256,
    guard_process_write,
    resolve_process_concept_path,
)
from .report import ReportContractError, validate_report_contract
from .validator import write_atomic


PROCESS_PRODUCER_VERSION = "1.0"
PROCESS_PRODUCER_ACTOR = "repo_jur_process_producer/1.0"


@dataclass(frozen=True)
class ProcessConceptCandidate:
    type: ProcessConceptType
    frontmatter: dict[str, object]
    body: str
    path: Path

    def render_text(self) -> str:
        lines = ["---"]
        for key, value in _ordered_frontmatter(self.frontmatter).items():
            lines.append(f"{key}: " + json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ))
        lines.append("---")
        return "\n".join(lines) + "\n" + self.body


class ProcessDuplicateResolution(str, Enum):
    NEW_CONCEPT = "new_concept"
    NOOP = "noop"
    REGENERATE = "regenerate"
    HUMAN_REVIEW = "human_review_required"


class ProcessMaterialityCategory(str, Enum):
    TECHNICAL = "technical"
    MATERIAL = "material"


@dataclass(frozen=True)
class ProcessProducerRunResult:
    candidate: ProcessConceptCandidate | None
    resolution: ProcessDuplicateResolution
    materiality: ProcessMaterialityCategory | None
    written: bool
    concept_path: Path | None


def _ordered_frontmatter(frontmatter: Mapping[str, object]) -> dict[str, object]:
    if "type" not in frontmatter:
        raise ProcessProducerConfigurationError("candidate type is missing")
    return {"type": frontmatter["type"], **{
        key: value for key, value in frontmatter.items() if key != "type"
    }}


def parse_process_candidate_text(
    text: str, path: str | Path
) -> ProcessConceptCandidate:
    if not isinstance(text, str) or not text.startswith("---\n"):
        raise ProcessProducerConfigurationError("candidate YAML is invalid")
    boundary = text.find("\n---\n", 4)
    if boundary < 0:
        raise ProcessProducerConfigurationError("candidate YAML boundary is missing")
    frontmatter: dict[str, object] = {}
    for line in text[4:boundary].splitlines():
        key, separator, encoded = line.partition(": ")
        if not separator or not _KEY.match(key) or key in frontmatter:
            raise ProcessProducerConfigurationError("candidate YAML entry is invalid")
        try:
            frontmatter[key] = json.loads(encoded)
        except json.JSONDecodeError as error:
            raise ProcessProducerConfigurationError(
                "candidate YAML value is invalid"
            ) from error
    try:
        concept_type = ProcessConceptType(frontmatter.get("type"))
    except (ValueError, TypeError) as error:
        raise ProcessProducerConfigurationError("candidate type is invalid") from error
    return ProcessConceptCandidate(
        concept_type, frontmatter, text[boundary + 5:], Path(path)
    )


def validate_process_candidate(candidate: ProcessConceptCandidate) -> None:
    if not isinstance(candidate, ProcessConceptCandidate):
        raise ProcessProducerConfigurationError("candidate contract is invalid")
    frontmatter = candidate.frontmatter
    if frontmatter.get("type") != candidate.type.value:
        raise ProcessProducerConfigurationError("candidate type does not match")
    generated = frontmatter.get("generated")
    if not isinstance(generated, dict) or not isinstance(generated.get("by"), str):
        raise ProcessProducerConfigurationError("candidate generated actor is missing")
    singular = frontmatter.get("repo_jur_pdf_hash")
    plural = frontmatter.get("repo_jur_pdf_hashes")
    if singular is not None and plural is not None:
        raise ProcessProducerConfigurationError(
            "PDF cardinality fields are exclusive"
        )
    sources = frontmatter.get("sources", [])
    if not isinstance(sources, list) or any(
        not isinstance(item, dict) for item in sources
    ):
        raise ProcessProducerConfigurationError("candidate sources are invalid")
    pdf_sources = [
        item for item in sources if item.get("media_type") == "application/pdf"
    ]
    if singular is not None and (
        len(pdf_sources) != 1 or not isinstance(singular, str)
        or not _SHA256.match(singular)
    ):
        raise ProcessProducerConfigurationError("singular PDF provenance is invalid")
    if plural is not None:
        if len(pdf_sources) < 2 or not isinstance(plural, dict):
            raise ProcessProducerConfigurationError("plural PDF provenance is invalid")
        ids = {item.get("id") for item in pdf_sources}
        if None in ids or set(plural) != ids or any(
            not isinstance(value, str) or not _SHA256.match(value)
            for value in plural.values()
        ):
            raise ProcessProducerConfigurationError("PDF source mapping is invalid")
    if pdf_sources and singular is None and plural is None:
        raise ProcessProducerConfigurationError("PDF provenance is missing")
    if any(
        field in frontmatter
        for kind, names in PROCESS_PROFILE_FIELDS.items()
        if kind is not candidate.type
        for field in names
        if field not in PROCESS_PROFILE_FIELDS[candidate.type]
    ):
        raise ProcessProducerConfigurationError(
            "profile field is used by the wrong type"
        )
    reparsed = parse_process_candidate_text(candidate.render_text(), candidate.path)
    if reparsed.frontmatter != frontmatter or reparsed.body != candidate.body:
        raise ProcessProducerConfigurationError("candidate render is not lossless")


def classify_process_materiality(
    existing: ProcessConceptCandidate, new: ProcessConceptCandidate,
) -> ProcessMaterialityCategory:
    if existing.body != new.body:
        return ProcessMaterialityCategory.MATERIAL
    material_keys = {
        "sources", "repo_jur_pdf_hash", "repo_jur_pdf_hashes",
        "repo_jur_evidence_sha256", "type",
    }
    if any(existing.frontmatter.get(key) != new.frontmatter.get(key)
           for key in material_keys):
        return ProcessMaterialityCategory.MATERIAL
    return ProcessMaterialityCategory.TECHNICAL


def merge_existing_process_candidate(
    existing: ProcessConceptCandidate,
    new: ProcessConceptCandidate,
    materiality: ProcessMaterialityCategory,
    *, reason: str,
) -> ProcessConceptCandidate:
    merged = dict(existing.frontmatter)
    for key in PROCESS_PRODUCER_OWNED_KEYS:
        if key in new.frontmatter:
            merged[key] = new.frontmatter[key]
        else:
            merged.pop(key, None)
    generated = dict(new.frontmatter["generated"])  # type: ignore[arg-type]
    old_generated = existing.frontmatter.get("generated")
    if isinstance(old_generated, dict) and "at" in old_generated:
        generated["at"] = old_generated["at"]
    if materiality is ProcessMaterialityCategory.MATERIAL:
        provenance = new.frontmatter.get("repo_jur_evidence_sha256", "unknown")
        generated["at"] = f"evidence:{provenance}"
        verified = existing.frontmatter.get("verified")
        if isinstance(verified, dict) and isinstance(
            verified.get("by"), str
        ) and isinstance(verified.get("at"), str):
            old_history = existing.frontmatter.get(
                "repo_jur_verification_history", []
            )
            history = list(old_history) if isinstance(old_history, list) else []
            history.append({
                "by": verified["by"], "at": verified["at"],
                "invalidated_by": PROCESS_PRODUCER_ACTOR, "reason": reason,
            })
            merged["repo_jur_verification_history"] = history
        merged.pop("verified", None)
    merged["generated"] = generated
    return ProcessConceptCandidate(
        new.type, _ordered_frontmatter(merged), new.body, new.path
    )


def _report(artifacts: Phase1Artifacts) -> dict[str, object]:
    if not isinstance(artifacts, Phase1Artifacts):
        raise ProcessProducerConfigurationError("Phase 1 artifacts are required")
    try:
        value: object = json.loads(artifacts.report_json)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as error:
        raise ProcessProducerBlockedError(
            "technical report is invalid", reason="invalid_report"
        ) from error
    if not isinstance(value, dict):
        raise ProcessProducerBlockedError(
            "technical report is invalid", reason="invalid_report"
        )
    try:
        validate_report_contract(value)
    except ReportContractError as error:
        raise ProcessProducerBlockedError(
            "technical report is invalid", reason="invalid_report"
        ) from error
    if GateState(value["result"]["quality_gate"]) is GateState.FAIL:  # type: ignore[index]
        raise ProcessProducerBlockedError(
            "recorded gate outcome is FAIL", reason="fail_gate"
        )
    return value


def _local_reference(resource: str) -> Path | None:
    parsed = urlparse(resource)
    if parsed.scheme == "file":
        return Path(unquote(parsed.path))
    return None if parsed.scheme else Path(resource)


def _base_candidate(
    artifacts: Phase1Artifacts,
    report: Mapping[str, object],
    review_result: ProcessReviewResult,
    context: ProcessProducerContext,
    process_root: str | Path,
) -> ProcessConceptCandidate:
    if context.evidence_resource is None:
        raise ProcessProducerConfigurationError("PDF evidence resource is required")
    input_data = report["input"]
    input_hash = input_data["sha256"]  # type: ignore[index]
    local = _local_reference(context.evidence_resource)
    physical_hash = input_hash
    if local is not None and local.exists():
        if not local.is_file():
            raise ProcessProducerConfigurationError("evidence resource is not a file")
        physical_hash = sha256_file(local)
        if physical_hash != input_hash:
            raise ProcessProducerConfigurationError(
                "evidence hash does not match report"
            )
    phase1 = report["phase1"]
    frontmatter: dict[str, object] = {
        "type": context.type.value,
        "generated": {"by": PROCESS_PRODUCER_ACTOR},
        "sources": [{"id": "pdf_1", "resource": context.evidence_resource,
                     "media_type": "application/pdf"}],
        "repo_jur_pdf_hash": physical_hash,
        "repo_jur_evidence_sha256": input_hash,
        "repo_jur_phase1": {key: phase1[key] for key in (  # type: ignore[index]
            "implementation", "implementation_version",
            "logical_processing_version", "relevant_config_fingerprint",
        )},
    }
    for extracted in review_result.extracted_fields:
        if extracted.name in PROCESS_PROFILE_FIELDS[context.type]:
            frontmatter.setdefault(extracted.name, extracted.value)
    return ProcessConceptCandidate(
        context.type, frontmatter, artifacts.markdown,
        resolve_process_concept_path(
            context.type, context.evidence_resource, process_root
        ),
    )


def produce_process(
    phase1_artifacts: Phase1Artifacts,
    routing_decision: RoutingDecision,
    review_result: ProcessReviewResult,
    producer_context: ProcessProducerContext,
    *, process_root: str | Path, bundle_root: str | Path,
    overwrite: bool = False,
) -> ProcessProducerRunResult:
    report = _report(phase1_artifacts)
    if not isinstance(routing_decision, RoutingDecision) or (
        routing_decision.target is not RouteTarget.JUDICIAL_PROCESS
    ):
        raise ProcessProducerConfigurationError(
            "routing decision is not judicial_process"
        )
    if not isinstance(producer_context, ProcessProducerContext):
        raise ProcessProducerConfigurationError(
            "validated producer context is required"
        )
    if not isinstance(review_result, ProcessReviewResult):
        raise ProcessProducerConfigurationError("review result contract is invalid")
    if review_result.state is ReviewState.REVIEW_REQUIRED:
        raise ProcessProducerBlockedError(
            "review_required", reason="review_required"
        )
    if any(suggestion.type is not None and suggestion.type != producer_context.type.value
           for suggestion in review_result.classification_suggestions):
        raise ProcessProducerBlockedError(
            "review_required: type conflict", reason="review_required"
        )
    candidate = _base_candidate(
        phase1_artifacts, report, review_result, producer_context, process_root
    )
    validate_process_candidate(candidate)
    path = candidate.path
    if path.exists():
        existing = parse_process_candidate_text(path.read_text(encoding="utf-8"), path)
        materiality = classify_process_materiality(existing, candidate)
        if materiality is ProcessMaterialityCategory.MATERIAL:
            return ProcessProducerRunResult(
                candidate, ProcessDuplicateResolution.HUMAN_REVIEW,
                materiality, False, path,
            )
        merged = merge_existing_process_candidate(
            existing, candidate, materiality, reason="technical producer change"
        )
        if existing.frontmatter.get("repo_jur_phase1") == candidate.frontmatter.get(
            "repo_jur_phase1"
        ):
            return ProcessProducerRunResult(
                existing, ProcessDuplicateResolution.NOOP, None, False, path
            )
        validate_process_candidate(merged)
        authorized = guard_process_write(
            acting_domain=RouteTarget.JUDICIAL_PROCESS, target=path,
            process_root=process_root, legal_bundle_root=bundle_root,
        )
        write_atomic(
            merged.render_text(), authorized, authorized.parent, overwrite=overwrite
        )
        return ProcessProducerRunResult(
            merged, ProcessDuplicateResolution.REGENERATE,
            materiality, True, authorized,
        )
    authorized = guard_process_write(
        acting_domain=RouteTarget.JUDICIAL_PROCESS, target=path,
        process_root=process_root, legal_bundle_root=bundle_root,
    )
    write_atomic(candidate.render_text(), authorized, authorized.parent, overwrite=False)
    return ProcessProducerRunResult(
        candidate, ProcessDuplicateResolution.NEW_CONCEPT, None, True, authorized
    )
