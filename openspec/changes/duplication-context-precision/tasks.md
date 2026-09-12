# Tasks: Duplication Context Precision

## Status: BLOCKED

This change cannot proceed to implementation. Task 1 below is the blocking prerequisite and must be completed and human-approved before any of the previously-planned implementation tasks (structural gap classification, regression tests) may be scoped or started.

## Task 1 (BLOCKING): Obtain and verify at least one real positive control
- **Description**: Identify at least one case in the corpus, or via an explicitly human-approved new conversion, where the source PDF page contains a passage exactly once and the corresponding Markdown output contains it twice (`source-once → output-twice`). Verify it the same way ESCRITURA4 p2 was re-verified: render the source PDF page directly (no OCR/AI transcription), transcribe/compare visually against the Markdown output, and record source-count vs output-count explicitly.
- **Status**: NOT STARTED. A full sweep of `logs/*.report.json` (including `logs/processos_auditoria_corrigidos/` and `logs/processos_auditoria_final/`) found only two files with any `duplication` issue at all (ESCRITURA4 p2 — reclassified as source-twice → output-twice, not a positive; CONTRSOCIAL8 p4/p19 — both confirmed false positives). No verified positive control currently exists anywhere in the already-converted corpus.
- **Constraints**: No OCR re-processing without explicit human approval. Do not reuse ESCRITURA4 p2 as a positive control — it has been reclassified (see `proposal.md`).
- **Exit condition**: Either (a) a genuine `source-once → output-twice` case is found and documented with source-count/output-count evidence, or (b) the corpus is exhaustively confirmed to contain none and that conclusion is explicitly recorded as a project decision (which may mean this change is closed without implementation).

## Task 2 (BLOCKED on Task 1): Structural gap classification in `detect_duplications`
- **Description**: Deferred. No candidate rule is currently proposed — the previously proposed `MARKER_PATTERN` was tested exploratorily and rejected (TP=0, FP=2, TN=1, FN=3; see `design.md`). Any future candidate rule must be validated against a real positive control obtained in Task 1, not only against the known false positives (CONTRSOCIAL8 p4/p19).
- **Constraints**: Not to be started until Task 1's exit condition (a) is met and the orchestrator has re-approved this task with a concrete design.

## Task 3 (BLOCKED on Task 1 and Task 2): Regression and precision tests
- **Description**: Deferred. Cannot be scoped until a validated design exists for Task 2.

## Task 4 (BLOCKED on Task 1, Task 2, and Task 3): Verification
- **Description**: Deferred. `uv run pytest`, `uv run ruff check`, `git diff --check`, and `uv run openspec validate duplication-context-precision --strict` will be run once implementation is authorized and completed. No commit/push/archive without explicit orchestrator (Claude) approval after diff review, as always.

## Acceptance Criteria (deferred, restated from the original proposal for when unblocked)
- [ ] A verified `source-once → output-twice` positive control exists and is documented (Task 1 exit condition).
- [ ] CONTRSOCIAL8 page 4 and page 19 (`4000153-37.2026.8.26.0136_SP_E001_CONTRSOCIAL8_P001-068`) produce zero `duplication` issues under a validated (non-rejected) rule.
- [ ] E032 (`4000153-37.2026.8.26.0136_SP_E032_DESPADEC1_P001-003`, all 3 pages) continues to produce zero `duplication` issues.
- [ ] No other page of the two full evidenced documents (8 pages ESCRITURA4, 68 pages CONTRSOCIAL8) changes classification relative to current behavior, except where explicitly intended by the validated rule.
- [ ] `min_len`, the sliding-window match/extension logic, and the `gap <= 1.5 * match_len` acceptance window remain untouched, unless a future design explicitly justifies changing them (not currently proposed).
- [ ] No mutation of Markdown content; `FidelityIssue` schema and privacy-safe contract (numeric offsets only, UUID4 `issue_id`) unchanged.
- [ ] All existing duplication-related tests in `tests/test_fidelity.py` and `tests/test_ocr_fidelity_precision.py` pass unmodified.
- [ ] New unit tests reproduce the real positive control's structural shape (once obtained) plus the known false-positive shapes, without persisting real document snippets in the test fixtures beyond what is already used by existing tests in the same style.
- [ ] Full test suite, `ruff check`, `git diff --check`, and `openspec validate duplication-context-precision --strict` pass.
