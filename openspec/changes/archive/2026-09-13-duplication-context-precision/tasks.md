# Tasks: Duplication Context Precision

## Status: CLOSED WITHOUT IMPLEMENTATION — Task 1 exit condition (b) met (re-verified 2026-09-13)

This change is closed without implementation. Task 1's exit condition (b) — exhaustive corpus
confirmation that no real positive control exists — has been met and independently re-verified.
No implementation task below may ever be started under this change; a future change would need a
newly obtained positive control (e.g. from a human-approved new conversion) to reopen this line of
work.

## Task 1 (BLOCKING): Obtain and verify at least one real positive control
- **Description**: Identify at least one case in the corpus, or via an explicitly human-approved new conversion, where the source PDF page contains a passage exactly once and the corresponding Markdown output contains it twice (`source-once → output-twice`). Verify it the same way ESCRITURA4 p2 was re-verified: render the source PDF page directly (no OCR/AI transcription), transcribe/compare visually against the Markdown output, and record source-count vs output-count explicitly.
- **Status**: COMPLETE — exit condition (b) met. Original full sweep of `logs/*.report.json` (including `logs/processos_auditoria_corrigidos/` and `logs/processos_auditoria_final/`) found only two files with any `duplication` issue at all (ESCRITURA4 p2 — reclassified as source-twice → output-twice, not a positive; CONTRSOCIAL8 p4/p19 — both confirmed false positives). **Independently re-verified 2026-09-13** by the orchestrator (Claude), scanning the full current corpus (105 `*.report.json` files across `logs/`, `logs/processos_auditoria_corrigidos/`, `logs/processos_auditoria_final/`) for `"issue_type": "duplication"` or `"issue_type": "internal_repetition"`: identical result — exactly the same 2 files (ESCRITURA4, CONTRSOCIAL8), 3 issues total, no new candidate. **No verified `source-once → output-twice` positive control exists anywhere in the already-converted corpus.** Per exit condition (b), this is a final project decision, not a pending item: this change is closed without implementation. Reopening requires a newly obtained positive control (e.g. a human-approved new conversion producing a genuine `source-once → output-twice` case), not a re-sweep of the same static corpus.
- **Constraints**: No OCR re-processing without explicit human approval. Do not reuse ESCRITURA4 p2 as a positive control — it has been reclassified (see `proposal.md`).
- **Exit condition**: Either (a) a genuine `source-once → output-twice` case is found and documented with source-count/output-count evidence, or (b) the corpus is exhaustively confirmed to contain none and that conclusion is explicitly recorded as a project decision (which may mean this change is closed without implementation). **(b) MET.**

## Task 2 (BLOCKED on Task 1): Structural gap classification in `detect_duplications`
- **Description**: Deferred. No candidate rule is currently proposed — the previously proposed `MARKER_PATTERN` was tested exploratorily and rejected (TP=0, FP=2, TN=1, FN=3; see `design.md`). Any future candidate rule must be validated against a real positive control obtained in Task 1, not only against the known false positives (CONTRSOCIAL8 p4/p19).
- **Constraints**: Not to be started until Task 1's exit condition (a) is met and the orchestrator has re-approved this task with a concrete design.

## Task 3 (BLOCKED on Task 1 and Task 2): Regression and precision tests
- **Description**: Deferred. Cannot be scoped until a validated design exists for Task 2.

## Task 4 (BLOCKED on Task 1, Task 2, and Task 3): Verification
- **Description**: Deferred. `uv run pytest`, `uv run ruff check`, `git diff --check`, and `uv run openspec validate duplication-context-precision --strict` will be run once implementation is authorized and completed. No commit/push/archive without explicit orchestrator (Claude) approval after diff review, as always.

## Acceptance Criteria — CLOSED WITHOUT IMPLEMENTATION (evaluated against the "closed" outcome, not the deferred implementation outcome)
- [x] A verified `source-once → output-twice` positive control was searched for exhaustively; NONE exists in the corpus (Task 1 exit condition (b), re-verified 2026-09-13: 105/105 report files swept, identical result to the original sweep).
- [x] No detector code change was made (nothing to regress): `detect_duplications` in `src/pipeline_juridico/fidelity.py` is untouched; CONTRSOCIAL8 p4/p19 remain classified exactly as documented (still known false positives, unresolved, no suppression rule implemented — this is the accepted cost of closing without implementation).
- [x] E032 (`4000153-37.2026.8.26.0136_SP_E032_DESPADEC1_P001-003`, all 3 pages) continues to produce zero `duplication` issues (unchanged, no code touched).
- [x] No page of the corpus changes classification — no code was modified.
- [x] `min_len`, the sliding-window match/extension logic, and the `gap <= 1.5 * match_len` acceptance window remain untouched (unmodified by this change).
- [x] No mutation of Markdown content; `FidelityIssue` schema and privacy-safe contract (numeric offsets only, UUID4 `issue_id`) unchanged (unmodified by this change).
- [x] All existing duplication-related tests in `tests/test_fidelity.py` (31 tests) and `tests/test_ocr_fidelity_precision.py` (10 tests) pass unmodified — verified as part of the full suite run (1072 passed, 2 warnings).
- [x] No new unit tests were added for a suppression rule (none is being implemented); this criterion is N/A for the "closed without implementation" outcome.
- [x] Full test suite (1072 passed, 2 warnings — see verification report), `git diff --check` (clean), and `openspec validate duplication-context-precision --strict` (`Change 'duplication-context-precision' is valid`) pass. `ruff` is not installed/declared in this project and is intentionally not a gate (per `AGENTS.md`/orchestrator instruction).
