## Architecture

`ingest` is a thin orchestration layer added to `domain_router_cli.py` (the `repo-jur` entrypoint
that already hosts `route`, `producer`, `process`, `retrieval`, `intake`, `test conformance`). It is
implemented as a **new module** `ingest_orchestrator.py` (pure orchestration, no new business rules)
plus a **new subparser** wired into `domain_router_cli._build_parser()`, mirroring how
`build_producer_parser`/`build_intake_parser` are wired today.

```
repo-jur ingest
      │
      ▼
 discover input/leis_jurisprudencia/*.pdf   (config.py: new IngestConfig)
      │  exact name ".gitkeep" ────────────────────────────► excluded from discovery entirely
      │  (repository sentinel; never classified, never reported, never counted)
      ▼
 classify_by_prefix(filename)                (ingest_router.py — NEW, pure function)
      │  BLOCKED (invalid/missing prefix) ──────────────► record + continue
      ▼
 per file, per existing public APIs, IN ORDER:
   1. converter.convert_document()            (existing; same call cli.main() makes)
   2. quality_gate.evaluate() + report.attach_gate_result()   (existing; same as cli.main())
   3. legal_source_segmentation.segment_markdown()            (existing; same as producer analyze)
      legal_segment_identity.resolve_segment_identity()       (existing; same as producer analyze)
   4. legal_semantic_review.LegalSemanticReviewEngine().review()  (existing; same as producer build)
      legal_producer._base_candidate() / validate_candidate()      (existing; same as producer build)
   5. legal_producer.validate_candidate() (re-run)           (existing; same as producer validate)
      │
      ▼
 write candidate(s) -> var/producer/candidates/*.md   (NEW destination; write_atomic, existing util)
 write per-file record -> var/producer/state/*.json   (existing producer.build record shape, reused)
      │
      ▼
 aggregate summary (stdout / --json)
```

No new PDF conversion, OCR, segmentation, identity, review, gate, or bundle-authorization logic is
written. `ingest_orchestrator.py` imports and sequences existing functions exactly as
`legal_producer_cli._run_build()` and `pipeline_juridico.cli.main()` already do internally — it does
not reimplement their bodies. Where `_run_build()`/`_run_analyze()` are private helpers
(`legal_producer_cli._run_build`, `_context`, `_record`, `_write_record`, `_filename`), `ingest`
either (a) calls the already-public underlying functions those helpers call
(`legal_source_segmentation.segment_markdown`, `legal_segment_identity.resolve_segment_identity`,
`legal_semantic_review.LegalSemanticReviewEngine`, `legal_producer._base_candidate`,
`legal_producer.validate_candidate`, `legal_producer.validate_producer_context`), or (b) is granted
narrow, explicit reuse of those specific private helpers via a same-package import (`from
.legal_producer_cli import _run_build_for_context` — see "Reuse Decision" below) rather than
duplicating their control flow. The implementer (Codex) must not fork/copy the segmentation,
identity-gating, or `--all-segments` loop logic; if reuse requires a small signature-preserving
extraction (e.g. splitting `_run_build`'s core loop into an internal helper callable by both the CLI
handler and `ingest_orchestrator`), that extraction is in scope for T1 and must not change any
existing observable behavior of `producer build` (verified by the full existing
`test_legal_producer_cli.py` suite passing unchanged).

### Reuse Decision (mandatory)

Before writing any new orchestration code, the implementer must attempt, in order:
1. Call the existing public function directly (no wrapper).
2. If only a private helper contains the needed logic (e.g. the segment-loop inside
   `_run_build`), extract that inner loop into a new **private, testable function** in
   `legal_producer.py` (not `legal_producer_cli.py`, to keep it CLI-argparse-free) with an explicit
   signature (`markdown, report_json, context, bundle_root, *, all_segments: bool, segment_id: str
   | None`), have `legal_producer_cli._run_build` call it (proving byte-identical CLI behavior via
   existing tests), and have `ingest_orchestrator` call the same function.
3. Only write new code in `ingest_orchestrator.py`/`ingest_router.py` for genuinely new concerns:
   discovery, prefix classification, per-file status aggregation, candidate persistence to
   `var/producer/candidates/`.

## Directory Structure

New/changed paths (all under existing `input/` and `var/` roots; nothing under `bundle/`):

```
input/
  leis_jurisprudencia/        # NEW — operational input root for this change
    .gitkeep
  processo/                   # NEW — reserved, unscanned placeholder (distinct from existing
    .gitkeep                  #        input/processos_auditoria/ audit fixtures, untouched)

var/
  producer/
    candidates/                # EXISTING dir, currently manually populated; ingest now writes here
      <slug-or-execution-id>[-segment-XXXX].md
    state/                     # EXISTING; ingest reuses the existing producer.build/analyze record
      <execution-id-or-hash>[-segment-XXXX].json    shape (record_type: "producer.build", etc.)
  ingest/                      # NEW — ingest's own per-run operational summary (not touched by
    reports/                   #        producer/router/intake)
      <run-id>.json

src/pipeline_juridico/
  ingest_router.py             # NEW — pure classify_by_prefix(filename) -> ClassificationResult
  ingest_orchestrator.py       # NEW — orchestration: discover, run pipeline, build summary
  domain_router_cli.py         # MODIFIED — new `ingest` subparser + dispatch
  config.py                    # MODIFIED — new IngestConfig (input_dir, candidates_dir, reports_dir)
  legal_producer.py            # POSSIBLY MODIFIED — extract shared build-loop helper (see Reuse
                                #   Decision); no change to segmentation/identity/materiality rules
```

## Schema

### Prefix classification (pure function, `ingest_router.py`)

```python
PREFIX_MAP: dict[str, LegalConceptType] = {
    "LEG_": LegalConceptType.Legislacao,
    "JUR_": LegalConceptType.Jurisprudencia,
    "PRE_": LegalConceptType.PrecedenteVinculante,
    "TEM_": LegalConceptType.TemaJuridico,
}

@dataclass(frozen=True)
class ClassificationResult:
    path: Path
    concept_type: LegalConceptType | None   # None only when blocked
    blocked: bool
    blocked_reason: str | None              # "unsupported_media_type" | "invalid_or_missing_prefix"
```

Rule, applied to every regular file discovered directly inside `input/leis_jurisprudencia/` (no
file is ever silently skipped from the report):
1. If the filename does not have an exact, case-sensitive `.pdf` extension, the result is
   `blocked=True`, `blocked_reason="unsupported_media_type"`, `concept_type=None`. The file is
   never opened.
2. Otherwise, `filename[:4]` is compared, exact-match and case-sensitive, against `PREFIX_MAP`
   keys, anchored at the start of the basename (not anywhere else in the name). A file matching no
   key is `blocked=True`, `blocked_reason="invalid_or_missing_prefix"`, `concept_type=None`. Any
   variation — wrong case (`leg_`), prefix appearing later in the name, or a near-miss string — is
   treated as no match, never coerced to the closest valid prefix.
3. The remainder of the filename after a matched 4-char prefix is never parsed or validated by this
   function — it is free text, exactly as the proposal specifies.

### Per-file ingest record (`var/ingest/reports/<run-id>.json`, `files[]` entries)

```json
{
  "schema_version": "1.0",
  "run_id": "2026-09-15T12:00:00Z-<uuid4>",
  "input_dir": "input/leis_jurisprudencia",
  "files": [
    {
      "filename": "LEG_L13.105_CPC_2015.pdf",
      "prefix": "LEG_",
      "concept_type": "Legislacao",
      "status": "READY_TO_PUBLISH",
      "reason": null,
      "quality_gate": "PASS",
      "segmentation_outcome": "SINGLE",
      "candidates": [
        {"segment_id": null, "candidate_path": "var/producer/candidates/....md",
         "record_path": "var/producer/state/....json"}
      ],
      "blocked_segments": []
    }
  ],
  "summary": {
    "total": 1, "READY_TO_PUBLISH": 1, "REVIEW_REQUIRED": 0, "BLOCKED": 0, "ERROR": 0
  }
}
```

`status` is one of the fixed vocabulary `READY_TO_PUBLISH | REVIEW_REQUIRED | BLOCKED | ERROR`
(new, `ingest`-local enum; does not extend or alias `GateState`/`DuplicateResolution`, which keep
their existing meanings unchanged). `READY_TO_PUBLISH` is strictly an operational, human-facing
signal that the candidate(s) passed every automated check and are fit for a human reviewer to
publish via the existing `producer publish` command — it carries no publication authorization and
`ingest` never acts on it beyond reporting.

## State Machine

Per file, a strict linear pipeline with fail-closed short-circuits — no state is ever skipped or
inferred:

```
DISCOVERED
   │
   ├─(non-.pdf regular file)───────────────────────────► BLOCKED (terminal, unsupported_media_type)
   ├─(invalid/missing prefix)──────────────────────────► BLOCKED (terminal, invalid_or_missing_prefix)
   │
   ▼ (valid prefix)
CONVERTED (Phase 1 markdown+report obtained)
   │
   ├─(conversion/OCR raises)───────────────────────────► ERROR (terminal)
   ▼
GATE_EVALUATED
   │
   ├─(recorded gate == FAIL)───────────────────────────► ERROR (terminal, reason=quality_gate_fail)
   ▼
SEGMENTED
   │
   ├─(outcome == AMBIGUOUS)────────────────────────────► REVIEW_REQUIRED (terminal)
   ▼
BUILT (0..N candidates constructed; segmentation SEGMENTS may yield partial blocked_segments)
   │
   ├─(semantic review == review_required, SINGLE outcome)──► REVIEW_REQUIRED (terminal)
   ├─(SINGLE outcome, identity_unresolved)──────────────► REVIEW_REQUIRED (terminal)
   ├─(0 candidates built, all segments blocked)─────────► REVIEW_REQUIRED (terminal)
   ├─(unexpected exception at any BUILT step)───────────► ERROR (terminal)
   ▼
VALIDATED (each candidate independently re-validated via validate_candidate())
   │
   ├─(validate_candidate raises for any candidate)──────► ERROR (terminal)
   ▼
   ├─(>=1 candidate built AND >=1 blocked_segments)──────► REVIEW_REQUIRED (terminal, partial)
   └─(all built candidates valid, 0 blocked_segments)────► READY_TO_PUBLISH (terminal)
```

This state machine is a pure reporting/aggregation layer over the *existing* return values/
exceptions of `segment_markdown`, `resolve_segment_identity`, `LegalSemanticReviewEngine.review`,
`validate_candidate`, and `quality_gate.evaluate` — it introduces no new decision inside those
functions.

## CLI Interface

```
uv run repo-jur ingest
    [--input-dir DIR]        default: input/leis_jurisprudencia (must resolve outside bundle/)
    [--bundle-root DIR]      default: bundle/  (read-only: used only to detect existing-concept
                                                 conflicts for REVIEW_REQUIRED reporting; NEVER
                                                 written to — see "Bundle read-only guarantee" risk)
    [--state-dir DIR]        default: var/producer/state (same contract as `producer build/analyze`)
    [--candidates-dir DIR]   default: var/producer/candidates (NEW default output location)
    [--reports-dir DIR]      default: var/ingest/reports
    [--log-level LEVEL]      existing convention (DEBUG|INFO|WARNING|ERROR|CRITICAL)
    [--json]                 machine-readable per-file + summary JSON to stdout
```

Exit codes (new, local to `ingest`, following the existing narrow-exit-code convention in this
CLI):
- `0`: run completed, zero files in `ERROR`. (`BLOCKED`/`REVIEW_REQUIRED` files do not fail the
  run — they are legitimate operational states, matching the proposal's requirement that conflicts
  and multi-concept blocks "continue to require human review" rather than fail the whole batch.)
- `1`: input error (input dir missing/unreadable).
- `2`: unexpected/unhandled error during orchestration setup (before any per-file loop starts).
- `6` (new, distinct from existing `EXIT_BLOCKED=5` which means "this single command's operation is
  blocked"): reserved but **not used** in v1 — a run exits `0` even with `ERROR` file entries
  present in the report, because `ingest` processes a batch and one file's technical failure must
  not mask the successful classification of every other file in the same run. (Explicit decision,
  see Risks.)

## Risks and Mitigations

- **Risk: silently publishing.** Mitigation: `ingest` never imports or calls
  `legal_producer.produce()`, `legal_producer_cli._run_publish()`, `guard_legal_bundle_write()` in a
  write-capable way, or `retrieval_cli`. A dedicated test asserts zero bytes are written under
  `bundle/` for a full mixed-fixture run (mtime + content hash comparison before/after).
- **Risk: reusing `_run_build`'s private control flow diverges from `producer build`'s real
  behavior over time.** Mitigation: the Reuse Decision mandates extracting a single shared helper
  in `legal_producer.py` that both the CLI and `ingest_orchestrator` call — one code path, not two
  synchronized copies (same principle as the shared-boundary-regex lesson from a prior change in
  this repo).
- **Risk: rerun corrupts state (`write_atomic` collisions / partial writes).** Mitigation: `ingest`
  reuses `validator.write_atomic()` with `overwrite=True` for its own deterministic-filename
  outputs (same idempotent-overwrite pattern `producer build` already uses for `var/producer/
  state/`), and a dedicated test runs `ingest` twice over the same fixtures, asserting byte-identical
  outputs and no `OutputAlreadyExistsError`.
- **Risk: `TEM_`/`PRE_` multi-segment handling silently diverges from `--all-segments`.**
  Mitigation: the shared-helper reuse (above) makes divergence structurally impossible; a
  regression test additionally asserts `ingest`'s per-segment JSON output for a `PRE_`/`TEM_`
  fixture is field-for-field consistent with directly invoking `producer build --all-segments
  --json` on the same Phase 1 artifacts.
- **Risk: concurrent/duplicate runs over the same PDF.** Out of scope for v1 — `ingest` does not
  implement `intake`'s claim/lease locking (it never moves or exclusively claims source files); the
  design accepts that two concurrent `ingest` runs over the same file will both succeed and
  idempotently overwrite the same deterministic output paths (no corruption, per the rerun
  mitigation above), but is not safe against concurrent read of a PDF a human is simultaneously
  editing/replacing. Documented, not solved, in this change.
- **Risk: `--bundle-root` read leaks a write.** Mitigation: `ingest` opens the bundle root only via
  read-only `Path.exists()`/`Path.read_text()` calls used purely to compute `REVIEW_REQUIRED` when
  an existing published concept already occupies the candidate's target path (informational only,
  mirroring what `producer publish` would need to decide — but `ingest` never calls
  `guard_legal_bundle_write` or `write_atomic` against any path under `bundle_root`). A test asserts
  `bundle_root` is never passed to `write_atomic`/`guard_legal_bundle_write` by grepping
  `ingest_orchestrator.py`'s own source for those symbols outside of read-only helper calls, in
  addition to the empty-diff runtime test above.
- **Risk: exit-code `0` masking real per-file errors from automation.** Mitigation: `--json` output
  always includes `summary.ERROR` count; documented in this design as the operator's contract for
  automation (check `summary.ERROR == 0`, not the process exit code alone, if the batch must be
  all-or-nothing). This mirrors the existing `test conformance` command's own `--json-report`
  pattern of separating the process exit code from the full itemized failure list.
