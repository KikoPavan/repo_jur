"""Operational ``repo-jur process`` commands."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
from pathlib import Path
from typing import Mapping

from .config import ensure_outside_canonical_bundle
from .contracts import Phase1Artifacts, RouteTarget
from .domain_router import (
    RoutingDecision, RoutingReasonCode, routing_state_filename,
)
from .process_producer import (
    ProcessConceptCandidate,
    ProcessDuplicateResolution,
    ProcessMaterialityCategory,
    _base_candidate,
    _report,
    classify_process_materiality,
    parse_process_candidate_text,
    validate_process_candidate,
)
from .process_semantic_review import (
    ProcessReviewProfile,
    ProcessSemanticReviewBlockedError,
    ProcessSemanticReviewConfigurationError,
    ProcessSemanticReviewEngine,
    ReviewState,
)
from .process_storage import (
    ProcessConceptType,
    ProcessProducerBlockedError,
    ProcessProducerConfigurationError,
    ProcessProducerContext,
    ensure_outside_process_storage,
    guard_process_write,
    resolve_process_concept_path,
    validate_process_producer_context,
)
from .report import ReportContractError, validate_report_contract
from .validator import OutputAlreadyExistsError, write_atomic


EXIT_OK = 0
EXIT_INPUT = 1
EXIT_UNEXPECTED = 2
EXIT_CONFIG = 3
EXIT_BLOCKED = 5
DEFAULT_STATE_DIR = "var/process/state"
STATE_DIR_ENV = "PROCESS_STATE_DIR"
DEFAULT_PROCESS_ROOT = Path(__file__).resolve().parents[2] / "process"
DEFAULT_BUNDLE_ROOT = Path(__file__).resolve().parents[2] / "bundle"
ROUTING_STATE_DIR_ENV = "ROUTING_STATE_DIR"
DEFAULT_ROUTING_STATE_DIR = "var/routing/state"
_TYPES = tuple(item.value for item in ProcessConceptType)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _common(parser: argparse.ArgumentParser, *, state: bool) -> None:
    parser.add_argument(
        "--process-root", default=str(DEFAULT_PROCESS_ROOT), metavar="DIR"
    )
    if state:
        parser.add_argument("--state-dir", metavar="DIR")
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument("--json", action="store_true")


def build_process_parser(subparsers: argparse._SubParsersAction) -> None:
    process = subparsers.add_parser("process")
    commands = process.add_subparsers(dest="process_command", required=True)
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


def _state_dir(value: str | None, process_root: str | Path) -> Path:
    raw = value or os.environ.get(STATE_DIR_ENV, DEFAULT_STATE_DIR)
    outside_bundle = ensure_outside_canonical_bundle(raw)
    return ensure_outside_process_storage(outside_bundle, process_root)


def _read(path_value: str, label: str) -> str:
    path = Path(path_value)
    if not path.is_file():
        raise FileNotFoundError(f"{label} não encontrado: {path}")
    return path.read_text(encoding="utf-8")


def _load_report(text: str) -> dict[str, object]:
    try:
        payload: object = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProcessProducerConfigurationError(
            "relatório técnico ilegível"
        ) from error
    if not isinstance(payload, dict):
        raise ProcessProducerConfigurationError(
            "relatório técnico deve ser objeto JSON"
        )
    try:
        validate_report_contract(payload)
    except ReportContractError as error:
        raise ProcessProducerConfigurationError(
            "contrato do relatório técnico inválido"
        ) from error
    return payload


def _context(args: argparse.Namespace) -> ProcessProducerContext:
    loaded: dict[str, object] = {}
    if args.context is not None:
        try:
            value: object = json.loads(_read(args.context, "contexto do Producer"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ProcessProducerConfigurationError(
                "contexto do Producer ilegível"
            ) from error
        if not isinstance(value, dict):
            raise ProcessProducerConfigurationError(
                "contexto do Producer deve ser objeto JSON"
            )
        loaded = value
    supplied = {
        "type": args.concept_type,
        "evidence_resource": args.evidence_resource,
    }
    for key, value in supplied.items():
        if value is None:
            continue
        if key in loaded and loaded[key] != value:
            raise ProcessProducerConfigurationError(
                "--context e --type/--evidence-resource discordam"
            )
        loaded[key] = value
    return validate_process_producer_context(loaded)


def _routing_decision(
    report: Mapping[str, object], phase1: Phase1Artifacts,
    logger: logging.Logger,
) -> RoutingDecision:
    del logger
    directory = Path(os.environ.get(
        ROUTING_STATE_DIR_ENV, DEFAULT_ROUTING_STATE_DIR
    )).resolve()
    record_path = directory / routing_state_filename(phase1)
    if not record_path.is_file():
        raise ProcessProducerBlockedError(
            "routing decision record is absent", reason="absent_routing_decision"
        )
    try:
        record: object = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProcessProducerConfigurationError(
            "registro de roteamento ilegível"
        ) from error
    if not isinstance(record, dict):
        raise ProcessProducerConfigurationError("registro de roteamento ilegível")
    if record.get("schema_version") != "1.0":
        raise ProcessProducerConfigurationError(
            "versão do registro de roteamento inválida"
        )
    if record.get("record_type") != "routing":
        raise ProcessProducerConfigurationError(
            "tipo do registro de roteamento inválido"
        )
    provenance = record.get("provenance_sha256")
    report_input = report["input"]
    report_provenance = report_input["sha256"]  # type: ignore[index]
    if (not isinstance(provenance, str) or not _SHA256.match(provenance)
            or provenance != report_provenance):
        raise ProcessProducerConfigurationError(
            "proveniência do registro de roteamento inválida"
        )
    decision, reason = record.get("decision"), record.get("reason")
    try:
        target = RouteTarget(decision) if isinstance(decision, str) else None
        reason_code = RoutingReasonCode(reason) if isinstance(reason, str) else None
    except ValueError as error:
        raise ProcessProducerConfigurationError(
            "registro de roteamento ilegível"
        ) from error
    if target is None or reason_code is None:
        raise ProcessProducerConfigurationError("registro de roteamento ilegível")
    if target is not RouteTarget.JUDICIAL_PROCESS:
        raise ProcessProducerBlockedError(
            "routing decision is not judicial_process", reason="non_process_route"
        )
    return RoutingDecision(target, reason_code)


def _filename(report: Mapping[str, object]) -> str:
    execution_id = report.get("execution_id")
    input_data = report["input"]
    stem = execution_id if isinstance(execution_id, str) and execution_id else input_data["sha256"]  # type: ignore[index]
    safe = "".join(
        char if char.isalnum() or char in "._-" else "_" for char in str(stem)
    )
    return f"{safe}.json"


def _record(
    *, record_type: str, provenance: str, gate: str, concept_path: Path,
    resolution: ProcessDuplicateResolution,
    materiality: ProcessMaterialityCategory | None,
    patch_count: int = 0, review_required: bool = False,
    publication_result: str, verified_action: str = "none",
    generated_at_action: str = "none",
) -> dict[str, object]:
    return {
        "schema_version": "1.0", "record_type": record_type,
        "input": {"sha256": provenance}, "provenance_sha256": provenance,
        "gate": gate, "routing_decision": RouteTarget.JUDICIAL_PROCESS.value,
        "review": {"patch_count": patch_count,
                   "review_required": review_required},
        "resolution_outcome": resolution.value,
        "materiality_category": materiality.value if materiality else None,
        "verified_action": verified_action,
        "verified": {"action": verified_action},
        "publication_result": publication_result,
        "generated_at_action": generated_at_action,
        "generated": {"at": {"action": generated_at_action}},
        "concept_path": str(concept_path),
    }


def _write_record(
    record: Mapping[str, object], state_dir: Path, filename: str
) -> Path:
    destination = state_dir / filename
    write_atomic(
        json.dumps(record, ensure_ascii=False, indent=2), destination,
        state_dir, overwrite=True,
    )
    return destination


def _emit(payload: Mapping[str, object], json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def _blocked_record(
    report: Mapping[str, object], context: ProcessProducerContext,
    process_root: str | Path, state_dir: Path,
) -> None:
    path = resolve_process_concept_path(
        context.type, context.evidence_resource, process_root
    )
    record = _record(
        record_type="process.review_required",
        provenance=report["input"]["sha256"],  # type: ignore[index]
        gate=report["result"]["quality_gate"],  # type: ignore[index]
        concept_path=path, resolution=ProcessDuplicateResolution.HUMAN_REVIEW,
        materiality=None, review_required=True, publication_result="blocked",
    )
    _write_record(record, state_dir, _filename(report))


def _run_build(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        state_dir = _state_dir(args.state_dir, args.process_root)
        markdown = _read(args.markdown, "Markdown da Fase 1")
        report_json = _read(args.report, "relatório técnico")
    except (OSError, UnicodeError) as error:
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
            decision = _routing_decision(report, artifacts, logger)
            review = ProcessSemanticReviewEngine().review(
                artifacts, decision, ProcessReviewProfile("default", "1.0", ())
            )
        except (ProcessProducerBlockedError, ProcessSemanticReviewBlockedError):
            _blocked_record(report, context, args.process_root, state_dir)
            raise
        if review.state is ReviewState.REVIEW_REQUIRED:
            _blocked_record(report, context, args.process_root, state_dir)
            return EXIT_BLOCKED
        candidate = _base_candidate(
            artifacts, _report(artifacts), review, context, args.process_root
        )
        metadata = candidate.frontmatter.get("repo_jur_phase1")
        if isinstance(metadata, dict):
            metadata["quality_gate"] = report["result"]["quality_gate"]  # type: ignore[index]
        validate_process_candidate(candidate)
        record = _record(
            record_type="process.build",
            provenance=report["input"]["sha256"],  # type: ignore[index]
            gate=report["result"]["quality_gate"],  # type: ignore[index]
            concept_path=candidate.path,
            resolution=ProcessDuplicateResolution.NEW_CONCEPT,
            materiality=None, patch_count=len(review.patches),
            publication_result="blocked",
        )
        record_path = _write_record(record, state_dir, _filename(report))
    except (ProcessProducerConfigurationError,
            ProcessSemanticReviewConfigurationError) as error:
        logger.error("Erro de configuração do Producer: %s", error)
        return EXIT_CONFIG
    except (ProcessProducerBlockedError,
            ProcessSemanticReviewBlockedError) as error:
        logger.error("Producer bloqueado: %s", error)
        return EXIT_BLOCKED
    _emit({"candidate": candidate.render_text(),
           "concept_path": str(candidate.path),
           "record_path": str(record_path)}, args.json)
    return EXIT_OK


def _load_candidate(args: argparse.Namespace) -> ProcessConceptCandidate:
    return parse_process_candidate_text(
        _read(args.candidate, "candidato"), args.candidate
    )


def _run_validate(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        candidate = _load_candidate(args)
        validate_process_candidate(candidate)
    except (OSError, UnicodeError) as error:
        logger.error("Falha de entrada: %s", error)
        return EXIT_INPUT
    except ProcessProducerConfigurationError as error:
        logger.error("Candidato inválido: %s", error)
        return EXIT_CONFIG
    _emit({"valid": True, "candidate": str(Path(args.candidate))}, args.json)
    return EXIT_OK


def _candidate_provenance(
    candidate: ProcessConceptCandidate,
) -> tuple[str, str]:
    provenance = candidate.frontmatter.get("repo_jur_evidence_sha256")
    phase1 = candidate.frontmatter.get("repo_jur_phase1")
    if not isinstance(provenance, str) or not _SHA256.match(provenance) or not isinstance(phase1, dict):
        raise ProcessProducerConfigurationError("proveniência do candidato é inválida")
    gate = phase1.get("quality_gate")
    if gate not in ("PASS", "PASS_WITH_WARNINGS"):
        raise ProcessProducerConfigurationError("gate do candidato é inválido")
    return provenance, str(gate)


def _publish_target(
    candidate: ProcessConceptCandidate, process_root: str | Path
) -> Path:
    sources = candidate.frontmatter.get("sources")
    resource = (
        sources[0].get("resource")
        if isinstance(sources, list) and sources
        and isinstance(sources[0], dict) else None
    )
    if not isinstance(resource, str):
        raise ProcessProducerConfigurationError("fonte do candidato é inválida")
    return resolve_process_concept_path(candidate.type, resource, process_root)


def _run_publish(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        state_dir = _state_dir(args.state_dir, args.process_root)
        candidate = _load_candidate(args)
        validate_process_candidate(candidate)
        provenance, gate = _candidate_provenance(candidate)
        target = _publish_target(candidate, args.process_root)
        resolution = ProcessDuplicateResolution.NEW_CONCEPT
        materiality = None
        publication = "published"
        generated_action = "none"
        if target.exists():
            existing = parse_process_candidate_text(
                target.read_text(encoding="utf-8"), target
            )
            materiality = classify_process_materiality(existing, candidate)
            if materiality is ProcessMaterialityCategory.MATERIAL:
                logger.error("Publicação requer revisão humana")
                return EXIT_BLOCKED
            if existing.render_text() == candidate.render_text():
                resolution = ProcessDuplicateResolution.NOOP
                publication = "noop"
                generated_action = (
                    "preserved" if isinstance(existing.frontmatter.get("generated"), dict)
                    and "at" in existing.frontmatter["generated"] else "none"
                )
            else:
                resolution = ProcessDuplicateResolution.REGENERATE
                generated_action = "preserved"
        authorized = guard_process_write(
            acting_domain=RouteTarget.JUDICIAL_PROCESS, target=target,
            process_root=args.process_root, legal_bundle_root=DEFAULT_BUNDLE_ROOT,
        )
        if publication != "noop":
            write_atomic(
                candidate.render_text(), authorized, authorized.parent,
                overwrite=args.overwrite or target.exists(),
            )
        record = _record(
            record_type="process.publish", provenance=provenance, gate=gate,
            concept_path=authorized, resolution=resolution,
            materiality=materiality, publication_result=publication,
            generated_at_action=generated_action,
        )
        record_path = _write_record(record, state_dir, f"{provenance}.json")
    except (OSError, UnicodeError) as error:
        logger.error("Falha de entrada: %s", error)
        return EXIT_INPUT
    except (ProcessProducerConfigurationError, PermissionError, ValueError,
            OutputAlreadyExistsError) as error:
        logger.error("Erro de configuração/publicação: %s", error)
        return EXIT_CONFIG
    except ProcessProducerBlockedError as error:
        logger.error("Producer bloqueado: %s", error)
        return EXIT_BLOCKED
    _emit({"publication_result": publication,
           "resolution_outcome": resolution.value,
           "concept_path": str(authorized),
           "record_path": str(record_path)}, args.json)
    return EXIT_OK


def run(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        if args.process_command == "build":
            return _run_build(args, logger)
        if args.process_command == "validate":
            return _run_validate(args, logger)
        if args.process_command == "publish":
            return _run_publish(args, logger)
    except Exception as error:
        logger.error("Falha inesperada no Producer: %s", error)
        return EXIT_UNEXPECTED
    return EXIT_UNEXPECTED
