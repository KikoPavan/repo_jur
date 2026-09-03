"""Operational ``repo-jur producer`` commands for Stage 7."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Mapping

from .config import ensure_outside_canonical_bundle
from .contracts import Phase1Artifacts, RouteTarget, guard_legal_bundle_write
from .domain_router import RoutingDecision, RoutingReasonCode
from .legal_producer import (
    ConceptCandidate,
    DuplicateResolution,
    LegalConceptType,
    LegalProducerBlockedError,
    LegalProducerConfigurationError,
    MaterialityCategory,
    _base_candidate,
    _report,
    classify_materiality,
    parse_candidate_text,
    resolve_concept_path,
    validate_candidate,
    validate_producer_context,
)
from .legal_semantic_review import (
    LegalReviewProfile,
    LegalSemanticReviewBlockedError,
    LegalSemanticReviewConfigurationError,
    LegalSemanticReviewEngine,
    ReviewState,
)
from .report import ReportContractError, validate_report_contract
from .validator import OutputAlreadyExistsError, write_atomic


EXIT_OK = 0
EXIT_INPUT = 1
EXIT_UNEXPECTED = 2
EXIT_CONFIG = 3
EXIT_BLOCKED = 5
DEFAULT_STATE_DIR = "var/producer/state"
STATE_DIR_ENV = "PRODUCER_STATE_DIR"
DEFAULT_BUNDLE_ROOT = Path(__file__).resolve().parents[2] / "bundle"
_TYPES = tuple(item.value for item in LegalConceptType)


def _common(parser: argparse.ArgumentParser, *, state: bool) -> None:
    parser.add_argument("--bundle-root", default=str(DEFAULT_BUNDLE_ROOT), metavar="DIR")
    if state:
        parser.add_argument("--state-dir", metavar="DIR")
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument("--json", action="store_true")


def build_producer_parser(subparsers: argparse._SubParsersAction) -> None:
    producer = subparsers.add_parser("producer", help="Constrói e publica conceitos jurídicos.")
    commands = producer.add_subparsers(dest="producer_command", required=True)
    build = commands.add_parser("build")
    build.add_argument("markdown")
    build.add_argument("report")
    build.add_argument("--type", dest="concept_type", metavar="TIPO")
    build.add_argument("--evidence-resource", metavar="URI")
    build.add_argument("--context", metavar="CONTEXT_JSON")
    _common(build, state=True)
    validate = commands.add_parser("validate")
    validate.add_argument("candidate")
    _common(validate, state=False)
    publish = commands.add_parser("publish")
    publish.add_argument("candidate")
    publish.add_argument("--overwrite", action="store_true")
    _common(publish, state=True)


def _state_dir(value: str | None) -> Path:
    return ensure_outside_canonical_bundle(value or os.environ.get(STATE_DIR_ENV, DEFAULT_STATE_DIR))


def _read(path_value: str, label: str) -> str:
    path = Path(path_value)
    if not path.is_file():
        raise FileNotFoundError(f"{label} não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _load_report(text: str) -> dict[str, object]:
    try:
        payload: object = json.loads(text)
    except json.JSONDecodeError as error:
        raise LegalProducerConfigurationError("relatório técnico ilegível") from error
    if not isinstance(payload, dict):
        raise LegalProducerConfigurationError("relatório técnico deve ser objeto JSON")
    try:
        validate_report_contract(payload)
    except ReportContractError as error:
        raise LegalProducerConfigurationError("contrato do relatório técnico inválido") from error
    return payload


def _context(args: argparse.Namespace):
    loaded: dict[str, object] = {}
    if args.context is not None:
        try:
            value: object = json.loads(_read(args.context, "contexto do Producer"))
        except (OSError, UnicodeError, json.JSONDecodeError, FileNotFoundError) as error:
            raise LegalProducerConfigurationError("contexto do Producer ilegível") from error
        if not isinstance(value, dict):
            raise LegalProducerConfigurationError("contexto do Producer deve ser objeto JSON")
        loaded = value
    supplied = {"type": args.concept_type, "evidence_resource": args.evidence_resource}
    for key, value in supplied.items():
        if value is None:
            continue
        if key in loaded and loaded[key] != value:
            raise LegalProducerConfigurationError(f"--context e --{key.replace('_', '-')} discordam")
        loaded[key] = value
    return validate_producer_context(loaded)


def _filename(report: Mapping[str, object]) -> str:
    execution_id = report.get("execution_id")
    stem = execution_id if isinstance(execution_id, str) and execution_id else report["input"]["sha256"]  # type: ignore[index]
    safe = "".join(character if character.isalnum() or character in "._-" else "_" for character in str(stem))
    return f"{safe}.json"


def _record(
    *, record_type: str, provenance: str, gate: str, concept_path: Path,
    resolution: DuplicateResolution, materiality: MaterialityCategory | None,
    patch_count: int = 0, review_required: bool = False,
    publication_result: str, verified_action: str = "none",
    generated_at_action: str = "none",
    extracted_fields: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    res = {
        "schema_version": "1.0",
        "record_type": record_type,
        "input": {"sha256": provenance},
        "provenance_sha256": provenance,
        "gate": gate,
        "routing_decision": RouteTarget.LEGAL_KNOWLEDGE.value,
        "review": {"patch_count": patch_count, "review_required": review_required},
        "resolution_outcome": resolution.value,
        "materiality_category": materiality.value if materiality else None,
        "verified_action": verified_action,
        "verified": {"action": verified_action},
        "publication_result": publication_result,
        "generated_at_action": generated_at_action,
        "generated": {"at": {"action": generated_at_action}},
        "concept_path": str(concept_path),
    }
    if extracted_fields is not None:
        res["extracted_fields"] = extracted_fields
    return res


def _write_record(record: Mapping[str, object], state_dir: Path, filename: str) -> Path:
    destination = state_dir / filename
    write_atomic(json.dumps(record, ensure_ascii=False, indent=2), destination, state_dir, overwrite=True)
    return destination


def _emit(payload: Mapping[str, object], json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def _run_build(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        state_dir = _state_dir(args.state_dir)
        markdown = _read(args.markdown, "Markdown da Fase 1")
        report_json = _read(args.report, "relatório técnico")
    except (OSError, UnicodeError, FileNotFoundError) as error:
        logger.error("Falha de entrada: %s", error)
        return EXIT_INPUT
    except ValueError as error:
        logger.error("Diretório de estado inválido: %s", error)
        return EXIT_CONFIG
    try:
        report = _load_report(report_json)
        context = _context(args)
        artifacts = Phase1Artifacts(markdown, report_json)
        try:
            review = LegalSemanticReviewEngine().review(
                artifacts, LegalReviewProfile("default", "1.0", ())
            )
            if review.state is ReviewState.REVIEW_REQUIRED:
                raise LegalSemanticReviewBlockedError("review is required for this candidate", reason="review_required")
            candidate = _base_candidate(artifacts, _report(artifacts), review, context, args.bundle_root)
            phase1_metadata = candidate.frontmatter.get("repo_jur_phase1")
            if isinstance(phase1_metadata, dict):
                phase1_metadata["quality_gate"] = report["result"]["quality_gate"]  # type: ignore[index]
            validate_candidate(candidate)
        except (LegalSemanticReviewBlockedError, LegalProducerBlockedError):
            concept_path = resolve_concept_path(
                context.type, context.evidence_resource, args.bundle_root
            )
            record = _record(
                record_type="producer.review_required",
                provenance=report["input"]["sha256"],  # type: ignore[index]
                gate=report["result"]["quality_gate"],  # type: ignore[index]
                concept_path=concept_path,
                resolution=DuplicateResolution.HUMAN_REVIEW,
                materiality=None,
                review_required=True,
                publication_result="blocked",
            )
            _write_record(record, state_dir, _filename(report))
            raise
        extracted_fields_data = [
            {"name": f.name, "value": f.value, "page_refs": list(f.page_refs)}
            for f in review.extracted_fields
        ]
        record = _record(
            record_type="producer.build", provenance=report["input"]["sha256"],  # type: ignore[index]
            gate=report["result"]["quality_gate"], concept_path=candidate.path,  # type: ignore[index]
            resolution=DuplicateResolution.NEW_CONCEPT, materiality=None,
            patch_count=len(review.patches), review_required=False,
            publication_result="blocked",
            extracted_fields=extracted_fields_data,
        )
        record_path = _write_record(record, state_dir, _filename(report))
    except (LegalProducerConfigurationError, LegalSemanticReviewConfigurationError) as error:
        logger.error("Erro de configuração do Producer: %s", error)
        return EXIT_CONFIG
    except (LegalProducerBlockedError, LegalSemanticReviewBlockedError) as error:
        logger.error("Producer bloqueado: %s", error)
        return EXIT_BLOCKED
    _emit({"candidate": candidate.render_text(), "concept_path": str(candidate.path),
           "record_path": str(record_path)}, args.json)
    return EXIT_OK


def _load_candidate(args: argparse.Namespace) -> ConceptCandidate:
    text = _read(args.candidate, "candidato")
    return parse_candidate_text(text, args.candidate)


def _run_validate(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        candidate = _load_candidate(args)
        validate_candidate(candidate)
    except (OSError, UnicodeError, FileNotFoundError) as error:
        logger.error("Falha de entrada: %s", error)
        return EXIT_INPUT
    except LegalProducerConfigurationError as error:
        logger.error("Candidato inválido: %s", error)
        return EXIT_CONFIG
    _emit({"valid": True, "candidate": str(Path(args.candidate))}, args.json)
    return EXIT_OK


def _candidate_provenance(candidate: ConceptCandidate) -> tuple[str, str]:
    provenance = candidate.frontmatter.get("repo_jur_evidence_sha256")
    phase1 = candidate.frontmatter.get("repo_jur_phase1")
    if not isinstance(provenance, str) or len(provenance) != 64 or not isinstance(phase1, dict):
        raise LegalProducerConfigurationError("proveniência do candidato é inválida")
    gate = phase1.get("quality_gate", "PASS")
    if gate not in ("PASS", "PASS_WITH_WARNINGS"):
        raise LegalProducerConfigurationError("gate do candidato é inválido")
    return provenance, str(gate)


def _publish_target(candidate: ConceptCandidate, bundle_root: str) -> Path:
    sources = candidate.frontmatter.get("sources")
    resource = sources[0].get("resource") if isinstance(sources, list) and sources and isinstance(sources[0], dict) else None
    if not isinstance(resource, str):
        raise LegalProducerConfigurationError("fonte do candidato é inválida")
    return resolve_concept_path(candidate.type, resource, bundle_root)


def _run_publish(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        state_dir = _state_dir(args.state_dir)
        candidate = _load_candidate(args)
        validate_candidate(candidate)
        provenance, gate = _candidate_provenance(candidate)
        target = _publish_target(candidate, args.bundle_root)
        resolution = DuplicateResolution.NEW_CONCEPT
        materiality = None
        publication = "published"
        if target.exists():
            existing = parse_candidate_text(target.read_text(encoding="utf-8"), target)
            materiality = classify_materiality(existing, candidate)
            if materiality is MaterialityCategory.MATERIAL:
                logger.error("Publicação requer revisão humana")
                return EXIT_BLOCKED
            if existing.render_text() == candidate.render_text():
                resolution = DuplicateResolution.NOOP
                publication = "noop"
            else:
                resolution = DuplicateResolution.REGENERATE
        authorized = guard_legal_bundle_write(
            acting_domain=RouteTarget.LEGAL_KNOWLEDGE,
            target=target,
            legal_bundle_root=args.bundle_root,
        )
        if publication != "noop":
            write_atomic(candidate.render_text(), authorized, authorized.parent,
                         overwrite=args.overwrite or target.exists())
        record = _record(
            record_type="producer.publish", provenance=provenance, gate=gate,
            concept_path=authorized, resolution=resolution, materiality=materiality,
            publication_result=publication,
            extracted_fields=None,
        )
        record_path = _write_record(record, state_dir, f"{provenance}.json")
    except (OSError, UnicodeError, FileNotFoundError) as error:
        logger.error("Falha de entrada: %s", error)
        return EXIT_INPUT
    except (LegalProducerConfigurationError, PermissionError, ValueError, OutputAlreadyExistsError) as error:
        logger.error("Erro de configuração/publicação: %s", error)
        return EXIT_CONFIG
    _emit({"publication_result": publication, "resolution_outcome": resolution.value,
           "concept_path": str(authorized), "record_path": str(record_path)}, args.json)
    return EXIT_OK


def run(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        if args.producer_command == "build":
            return _run_build(args, logger)
        if args.producer_command == "validate":
            return _run_validate(args, logger)
        if args.producer_command == "publish":
            return _run_publish(args, logger)
    except Exception as error:
        logger.error("Falha inesperada no Producer: %s", error)
        return EXIT_UNEXPECTED
    return EXIT_UNEXPECTED
