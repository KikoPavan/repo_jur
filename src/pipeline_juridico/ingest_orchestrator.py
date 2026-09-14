"""Non-publishing operational legal-knowledge ingestion."""

from __future__ import annotations

import datetime
import json
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import IngestConfig, RoutingConfig
from .contracts import GateState, Phase1Artifacts
from .converter import convert_document
from .ingest_router import classify_by_prefix
from .legal_producer import (
    DuplicateResolution,
    LegalProducerBlockedError,
    MaterialityCategory,
    build_candidates,
    classify_materiality,
    parse_candidate_text,
    validate_candidate,
    validate_producer_context,
)
from .legal_producer_cli import _filename, _record, _write_record
from .legal_semantic_review import LegalSemanticReviewBlockedError
from .legal_source_segmentation import SegmentationOutcome
from .quality_gate import evaluate
from .report import (
    attach_gate_result,
    build_candidate_report_json,
    build_report_json,
    strip_technical_routing_metadata,
)
from .validator import write_atomic

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class IngestFileRecord:
    filename: str
    prefix: str | None
    concept_type: str | None
    status: str
    reason: str | None
    quality_gate: str | None
    segmentation_outcome: str | None
    candidates: list[dict[str, object]]
    blocked_segments: list[dict[str, object]]


@dataclass(frozen=True)
class IngestRunReport:
    schema_version: str
    run_id: str
    input_dir: str
    files: list[IngestFileRecord]
    summary: dict[str, int]
    report_path: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload.pop("report_path", None)
        return payload


def discover_pdfs(input_dir: str | Path) -> tuple[Path, ...]:
    """Return direct regular files except .gitkeep in stable basename order."""
    root = Path(input_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"input directory does not exist: {root}")
    return tuple(sorted(
        (
            item for item in root.iterdir()
            if item.is_file() and item.name != ".gitkeep"
        ),
        key=lambda item: item.name,
    ))


def _run_id() -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    return f"{now.isoformat().replace('+00:00', 'Z')}-{uuid.uuid4()}"


def _blocked(path: Path, reason: str) -> IngestFileRecord:
    return IngestFileRecord(
        path.name, None, None, "BLOCKED", reason, None, None, [], []
    )


def _candidate_conflicts(candidate) -> bool:
    if not candidate.path.exists():
        return False
    existing = parse_candidate_text(
        candidate.path.read_text(encoding="utf-8"), candidate.path
    )
    return classify_materiality(existing, candidate) is MaterialityCategory.MATERIAL


def _process_file(path: Path, config: IngestConfig) -> IngestFileRecord:
    classification = classify_by_prefix(path.name)
    if classification.blocked:
        return _blocked(path, classification.blocked_reason or "blocked")
    concept_type = classification.concept_type
    assert concept_type is not None
    prefix = path.name[:4]
    output_path = Path("output") / f"{path.stem}.md"
    report_path = Path("logs") / f"{path.stem}.report.json"
    temp_root = Path("temp")
    try:
        markdown, raw_report = convert_document(
            pdf_path=path,
            output_path=output_path,
            temp_root=temp_root,
            use_ocr=True,
            ocr_prompt_path=PROJECT_ROOT / "prompts/ocr_literal_ptbr.txt",
            routing_config=RoutingConfig.from_env(),
        )
        literal = strip_technical_routing_metadata(markdown)
        candidate_report = build_candidate_report_json(raw_report)
        gate = evaluate(Phase1Artifacts(literal, candidate_report))
        final_report = attach_gate_result(
            raw_report,
            quality_gate=gate.state.value,
            warnings=gate.warnings,
            errors=gate.errors,
        )
        report_json = build_report_json(final_report)
        write_atomic(literal, output_path, temp_root, overwrite=True)
        write_atomic(report_json, report_path, temp_root, overwrite=True)
        if gate.state is GateState.FAIL:
            return IngestFileRecord(
                path.name, prefix, concept_type.value, "ERROR",
                "quality_gate_fail", gate.state.value, None, [], [],
            )

        artifacts = Phase1Artifacts(literal, report_json)
        context = validate_producer_context({
            "type": concept_type.value,
            "evidence_resource": str(path),
        })
        segmentation = None
        try:
            # Batch ingestion selects every segment whenever segmentation says
            # the source is multi-concept. The shared helper owns all details.
            from .legal_source_segmentation import (
                DEFAULT_SEGMENTATION_REGISTRY,
                segment_markdown,
            )
            segmentation = segment_markdown(
                literal, DEFAULT_SEGMENTATION_REGISTRY
            )
            if segmentation.outcome is SegmentationOutcome.AMBIGUOUS:
                return IngestFileRecord(
                    path.name, prefix, concept_type.value, "REVIEW_REQUIRED",
                    "segmentation_ambiguous", gate.state.value,
                    segmentation.outcome.name, [], [],
                )
            outcome = build_candidates(
                artifacts,
                context,
                config.bundle_root,
                all_segments=(
                    segmentation.outcome is SegmentationOutcome.SEGMENTS
                ),
                segment_id=None,
            )
        except (LegalProducerBlockedError, LegalSemanticReviewBlockedError) as exc:
            return IngestFileRecord(
                path.name, prefix, concept_type.value, "REVIEW_REQUIRED",
                getattr(exc, "reason", "review_required"), gate.state.value,
                segmentation.outcome.name if segmentation else None, [], [],
            )

        candidates: list[dict[str, object]] = []
        conflict = False
        report = json.loads(report_json)
        extracted = [
            {"name": field.name, "value": field.value,
             "page_refs": list(field.page_refs)}
            for field in outcome.review.extracted_fields
        ]
        for segment, candidate in outcome.built:
            validate_candidate(candidate)
            rendered = candidate.render_text()
            parsed = parse_candidate_text(rendered, candidate.path)
            validate_candidate(parsed)
            conflict = conflict or _candidate_conflicts(candidate)
            suffix = f"-{segment.segment_id}" if segment is not None else ""
            candidate_path = config.candidates_dir / f"{path.stem}{suffix}.md"
            state_name = _filename(report)
            if segment is not None:
                state_name = f"{Path(state_name).stem}-{segment.segment_id}.json"
            record = _record(
                record_type="producer.build",
                provenance=report["input"]["sha256"],
                gate=report["result"]["quality_gate"],
                concept_path=candidate.path,
                resolution=DuplicateResolution.NEW_CONCEPT,
                materiality=None,
                patch_count=len(outcome.review.patches),
                review_required=False,
                publication_result="blocked",
                extracted_fields=extracted,
            )
            record_path = _write_record(record, config.state_dir, state_name)
            write_atomic(
                rendered, candidate_path, config.candidates_dir, overwrite=True
            )
            candidates.append({
                "segment_id": segment.segment_id if segment else None,
                "candidate_path": str(candidate_path),
                "record_path": str(record_path),
            })
        review_required = bool(outcome.blocked_segments) or not candidates or conflict
        return IngestFileRecord(
            path.name, prefix, concept_type.value,
            "REVIEW_REQUIRED" if review_required else "READY_TO_PUBLISH",
            "existing_concept_conflict" if conflict else None,
            gate.state.value, outcome.segmentation.outcome.name,
            candidates, outcome.blocked_segments,
        )
    except Exception as exc:
        return IngestFileRecord(
            path.name, prefix, concept_type.value, "ERROR",
            type(exc).__name__, None, None, [], [],
        )


def run_ingest(config: IngestConfig) -> IngestRunReport:
    """Run the complete non-publishing batch and persist its report."""
    paths = discover_pdfs(config.input_dir)
    records = [_process_file(path, config) for path in paths]
    summary = {name: 0 for name in (
        "READY_TO_PUBLISH", "REVIEW_REQUIRED", "BLOCKED", "ERROR"
    )}
    for record in records:
        summary[record.status] += 1
    summary = {"total": len(records), **summary}
    run_id = _run_id()
    result = IngestRunReport(
        "1.0", run_id, str(config.input_dir), records, summary
    )
    destination = config.reports_dir / f"{run_id}.json"
    write_atomic(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        destination,
        config.reports_dir,
        overwrite=True,
    )
    return IngestRunReport(
        result.schema_version, result.run_id, result.input_dir,
        result.files, result.summary, str(destination),
    )
