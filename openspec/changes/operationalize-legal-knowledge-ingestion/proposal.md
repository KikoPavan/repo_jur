## Why

Legal Knowledge ingestion today has two disconnected paths and neither is an operator-usable,
deterministic bulk pipeline for `leis_jurisprudencia`:

1. `repo-jur intake scan` (`intake_manager.py` / `intake_orchestrator.py`) classifies by
   **subdirectory name** (`legislacao/`, `jurisprudencia/`, `temas/`, `precedentes/`), **claims and
   moves** the source PDF into `var/intake/processing/`, and **auto-publishes** straight into
   `bundle/` via `legal_producer.produce()`. It has no concept of `PrecedenteVinculante`
   multi-segment `--all-segments` handling or `TemaJuridico` `identity_unresolved` per-segment
   blocking (`legal_producer.produce()` only ever builds a single, whole-document candidate — see
   `intake_orchestrator.py:238`), and it never leaves a human-reviewable candidate for operator
   approval before writing to the canonical bundle.
2. `repo-jur producer analyze|build|validate|publish` (`legal_producer_cli.py`) is the fully
   capable, segmentation-aware, human-gated toolchain — including the `--all-segments` /
   `identity_unresolved` behavior added by the `multi-concept-legal-source-segmentation` change —
   but it is a set of **single-file, single-invocation commands**. There is no discovery step, no
   deterministic type classification, and no aggregate operational reporting: an operator must
   already know the PDF's type and manually run four commands per file.

There is no single command that (a) discovers PDFs from a fixed input location, (b) classifies them
deterministically without any content inspection, (c) drives them through the already-validated
Phase 1 → Quality Gate → Producer analyze/build/validate chain, and (d) reports a clear operational
outcome per file and in aggregate — without ever touching `bundle/`, without moving or mutating the
source PDFs, and without regressing the segmentation/identity rules the `2026-09-14` change already
established.

## What Changes

- Add a new operational input root `input/leis_jurisprudencia/` with a strictly deterministic
  **filename-prefix** classifier (`LEG_` → `Legislacao`, `JUR_` → `Jurisprudencia`, `PRE_` →
  `PrecedenteVinculante`, `TEM_` → `TemaJuridico`); no other classification signal (content, regex
  over text, AI/LLM inference, or fallback heuristic) is ever consulted. Matching is exact,
  case-sensitive, and anchored at the start of the basename — any variation (wrong case, prefix not
  at the start, extra/different characters, or no recognized prefix at all) is `BLOCKED`. See
  `## Proposed Behavior` and `design.md` for the exact algorithm.
- Every regular file discovered directly inside `input/leis_jurisprudencia/` is reported — none are
  silently skipped. A file whose name does not have an exact `.pdf` extension is `BLOCKED` with the
  explicit reason `unsupported_media_type`, distinct from `invalid_or_missing_prefix` (which applies
  only to `.pdf` files with an unrecognized prefix).
- Reserve `input/processo/` as a placeholder input root that this change creates but never scans or
  processes (judicial-process ingestion stays fully out of scope, distinct from the unrelated
  existing `input/processos_auditoria/` audit fixtures).
- Add one new operational command, `repo-jur ingest` (`uv run repo-jur ingest`), that discovers
  every `*.pdf` in `input/leis_jurisprudencia/` and, per valid file, drives the existing pipeline in
  order: Phase 1 conversion → Quality Gate → `producer analyze` (segmentation + identity) →
  `producer build` → `producer validate` — reusing the exact functions the `converter-juridico` CLI
  and `producer` CLI already call, not re-implementing any conversion, segmentation, identity,
  review, or validation logic.
- Preserve, byte-for-byte, the existing multi-concept rules from the `2026-09-14` change:
  `PRE_` sources whose segmentation outcome is `SEGMENTS` are built with the `--all-segments`
  semantics (one candidate per resolvable segment); `TEM_` sources continue to have any segment
  whose identity is `identity_unresolved` excluded from candidates and reported, never silently
  coerced or dropped without a trace.
- `ingest` never writes to `bundle/`, never calls `producer publish`, never calls `retrieval sync`,
  and never claims/moves/deletes the source PDF (unlike `intake scan`). It only writes Phase 1
  artifacts to the existing `output/`/`logs/` contract, producer state to `var/producer/state/`,
  and now also the rendered, validated Markdown candidate(s) to `var/producer/candidates/` — the
  first component to populate that already-existing-but-so-far-manually-populated directory.
- `ingest` produces a per-file operational status (`READY_TO_PUBLISH`, `REVIEW_REQUIRED`,
  `BLOCKED`, `ERROR`) and an aggregate summary across the run; an operator decides publication
  separately via the existing `producer publish` command.
- No change to `router.py`, `legal_producer.py`'s identity/segmentation/materiality logic,
  `legal_semantic_review.py`, `quality_gate.py`, or any OKF/CNJ rule. This is a wiring/orchestration
  change only.

## Objectives

- One operator command drives the entire validated-candidate pipeline for
  `input/leis_jurisprudencia/`, with zero content-based type inference.
- Deterministic, auditable per-file and aggregate reporting that distinguishes files that are safe
  to hand to `producer publish` from files that require human review, were never eligible, or
  failed technically.
- Zero regression of the existing segmentation/identity/quality-gate/review contracts; zero new
  auto-publish surface.

## Scope

### In Scope
- New deterministic filename-prefix classifier for `input/leis_jurisprudencia/`.
- New `repo-jur ingest` command (discovery, classification, orchestration, reporting).
- New persistence of validated candidate Markdown under `var/producer/candidates/`.
- `input/processo/` created as a reserved, unscanned placeholder directory.
- Tests covering all four prefixes, invalid/missing prefix, non-PDF files, `input/processo/`
  exclusion, multi-concept precedent handling, `identity_unresolved` blocking preservation, no
  auto-publish, and safe rerun.

### Out of Scope
- Any change to judicial-process ingestion or `input/processo/` processing.
- Any change to `repo-jur intake` (folder-based classifier, lease/claim lifecycle, auto-publish).
- Any change to segmentation rules, identity resolution rules, CNJ validation, Legal OKF metadata,
  semantic review heuristics, or bundle publication/materiality logic.
- Automatic or batch `producer publish` / `retrieval sync` execution.
- Real OCR execution against new fixtures beyond what is already exercised by existing tests
  (tests use synthetic/fixture Phase 1 artifacts or existing real-corpus files already present
  under `input/`).

## Proposed Behavior

1. Operator runs `uv run repo-jur ingest [--input-dir DIR] [--bundle-root DIR] [--state-dir DIR]
   [--candidates-dir DIR] [--json]`.
2. The command lists every regular file directly inside `input/leis_jurisprudencia/`
   (non-recursive, deterministic sort order); subdirectories are not descended into. For each
   discovered regular file: if its name does not have an exact, case-sensitive `.pdf` extension, it
   is classified `BLOCKED` with reason `unsupported_media_type` and never opened. Otherwise, if its
   basename does not start with one of the four exact, case-sensitive prefixes, it is classified
   `BLOCKED` with reason `invalid_or_missing_prefix` and is never opened, hashed for conversion, or
   otherwise processed as any other type. Every discovered file appears in the run's file list —
   none are silently skipped.
3. For each classified file, in discovery order:
   a. **Phase 1 conversion** — call `converter.convert_document()` (the same function
      `pipeline_juridico.cli.main()` calls) to get literal Markdown + technical report.
   b. **Quality Gate** — call `quality_gate.evaluate()` and `report.attach_gate_result()` the same
      way `cli.main()` composes the final technical report; a recorded `FAIL` gate stops this file
      with status `ERROR` and reason `quality_gate_fail`.
   c. **`producer analyze`** — call `legal_source_segmentation.segment_markdown()` and
      `legal_segment_identity.resolve_segment_identity()` (the same calls
      `legal_producer_cli._run_analyze()` makes) to obtain the segmentation outcome and, for
      `SEGMENTS`, per-segment identity status.
   d. **`producer build`** — call the same build logic `legal_producer_cli._run_build()` uses
      (validated context construction, semantic review, per-segment identity gating,
      `validate_candidate()`), with the `--all-segments` equivalent automatically selected whenever
      segmentation outcome is `SEGMENTS` (this generalizes uniformly — it is not a `PRE_`-only or
      `TEM_`-only special case in the code path; segments that are `identity_unresolved` are
      excluded from candidates and listed, exactly as `--all-segments` already does today for any
      type).
   e. **`producer validate`** — re-parse and re-validate the just-written candidate Markdown via
      `validate_candidate()`, exactly as the standalone `producer validate` command does, before
      writing it to `var/producer/candidates/`.
4. `ingest` classifies the file's outcome:
   - `READY_TO_PUBLISH` — every produced candidate passed Quality Gate (`PASS` or
     `PASS_WITH_WARNINGS`), segmentation, identity resolution, semantic review, and standalone
     validation, with zero blocked segments. This status means only that the candidate(s) are
     validated and fit for human review/publication — it is never itself an authorization to
     publish, and `ingest` never publishes automatically regardless of this status.
   - `REVIEW_REQUIRED` — semantic review flagged `review_required`, segmentation outcome is
     `AMBIGUOUS`, a `SINGLE`-outcome source has `identity_unresolved`, a `SEGMENTS` outcome
     produced at least one blocked segment alongside at least one built candidate (partial
     success), or a built candidate's target path collides with a materially different existing
     published concept in `bundle/`.
   - `BLOCKED` — invalid/missing filename prefix (`invalid_or_missing_prefix`) or a non-PDF regular
     file (`unsupported_media_type`); the file is never processed further.
   - `ERROR` — any technical failure: conversion/OCR error, Quality Gate `FAIL`, unreadable/corrupt
     PDF, or any unexpected exception.
5. `ingest` prints a per-file record and an aggregate summary (counts per status) and exits `0`
   only if no file resulted in `ERROR`; `BLOCKED` and `REVIEW_REQUIRED` do not by themselves fail
   the command (they are legitimate, reportable operational states), matching the existing CLI
   convention of narrow, category-specific exit codes elsewhere in this codebase.
6. Nothing in this flow touches `bundle/`, calls `producer publish`, calls `retrieval sync`, or
   moves/renames/deletes the source PDF.

## Success Criteria

- `uv run repo-jur ingest --json` run twice in a row over the same `input/leis_jurisprudencia/`
  contents produces byte-identical `var/producer/candidates/*.md` and equivalent (idempotent)
  `var/producer/state/*.json` records, with the source PDFs unchanged (`git status` / hash
  comparison) both times.
- A `PRE_` fixture with multiple internal "Tema Repetitivo" records yields one `READY_TO_PUBLISH`
  (or `REVIEW_REQUIRED`, if any segment is unresolved) entry per resolvable segment, matching what
  `producer build --all-segments` already produces for the same source today.
- A `TEM_` fixture with at least one `identity_unresolved` segment reports that segment as blocked
  in the operational summary without ever inventing or guessing its identity.
- No test, fixture, or real-corpus run in this change writes to `bundle/`.
- `openspec validate --all --strict` passes.
