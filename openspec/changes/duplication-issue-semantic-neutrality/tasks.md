# Tasks: Duplication Issue Semantic Neutrality

## Status: IMPLEMENTED — verified by orchestrator (Claude) on diff + test re-run; NOT archived, NOT committed

Implementation was executed by Codex per orchestrator-authorized scope (two bounded delegations: initial
scope + one narrow follow-up fix to `tests/test_models.py`, both explicitly authorized by the
orchestrator, not a requirements change). The orchestrator independently re-reviewed the full diff and
re-ran all verification commands before marking any item below `[x]`. The cross-reference note (Task 4)
has now been added directly to `duplication-context-precision`'s `proposal.md`/`design.md` as a
documentation-only, pre-archive step (does not require this change's own archival). The published-spec
delta application (formerly framed as Task 3) is NOT a pending implementation task — it is the standard,
inherent effect of running `openspec archive` once this change is approved, and is tracked below as an
operational post-approval step rather than as a checklist item that could ever be checked off before
archive. No commit/push/archive has been performed.

## Task 1: Rename persisted `issue_type` value in the detector and bump schema_version — DONE (verified)
- **Description**: In `src/pipeline_juridico/fidelity.py::detect_duplications`, change
  `issue_type="duplication"` (line 93) to `issue_type="internal_repetition"`. No other line in
  `detect_duplications` changes (`min_len`, sliding-window logic, gap ratio, `detector` field value
  `"internal_repetition_detector"` all remain byte-for-byte unchanged).
- **Also update**: the comment on `src/pipeline_juridico/models.py:24` listing known `issue_type` values,
  replacing `duplication` with `internal_repetition` in the enumeration comment.
- **Schema version bump**: change `Relatorio.schema_version` default from `"1.1"` to `"1.2"`
  (`src/pipeline_juridico/models.py:138`). In `src/pipeline_juridico/report.py::validate_report_contract`,
  extend the `schema_version` allow-list (currently `"1.0"` / `"1.1"`, lines 143, 150, 276) to admit
  `"1.2"`, applying the identical `fidelity_audit`-required branch to `"1.2"` that currently applies to
  `"1.1"`. No other structural or type validation changes. Per `design.md` § Schema Version Decision,
  Schema 1.1 remains a valid, documented legacy contract — do not remove or reject `"1.1"` reports.
- **Constraint**: Do not touch other `report.py` or `quality_gate.py` logic beyond the `schema_version`
  allow-list extension described above — per `design.md` § Consumer Inventory, neither performs
  literal-value matching against `"duplication"` for `issue_type`; only the `schema_version` allow-list
  itself needs to change.
- **Verification (orchestrator, diff review + independent re-run)**: `git diff` confirms exactly one
  literal-string change in `fidelity.py` (line 93, `issue_type` only); `models.py` shows the comment
  update and `schema_version: str = "1.2"`; `report.py` shows both `== "1.1"` checks widened to
  `in {"1.1", "1.2"}`, with the `elif ... != "1.0"` rejection path unchanged. No other line in any of the
  three files differs from the pre-implementation baseline.

## Task 2: Migrate test assertions — DONE (verified)
- **Description**: Update every test assertion currently matching the literal string `"duplication"` to
  `"internal_repetition"`, without changing test logic, input fixtures, or expected pass/fail outcomes.
  Per `design.md` § Consumer Inventory, the known sites are:
  - `tests/test_fidelity.py` — direct `issue_type == "duplication"` / `.issue_type == "duplication"`
    assertions (multiple sites, e.g. line 35).
  - `tests/test_ocr_fidelity_precision.py` — list-comprehension filters
    `[i for i in audit.issues if i.issue_type == "duplication"]` (multiple sites, e.g. lines 29, 41, 141,
    152), and the stale causal comment on line 22 (`# Positive: True substantial duplication (ESCRITURA4
    Page 2 equivalent)`) must be corrected to remove the causal framing (e.g. rephrase to describe the
    synthetic structural shape being tested, without implying it proves OCR caused a real document's
    repetition).
  - `tests/test_e2e_fidelity.py` — fixture dict literal `"issue_type": "duplication"` (line 71). Also
    verify the fixture's `schema_version` value and update/add coverage for `"1.2"` if the fixture asserts
    a specific `schema_version` string.
  - `tests/test_report.py` — verify during implementation whether any literal `"duplication"` value
    assertion exists (inspection at proposal time found none, only field-name/type checks). Add/update
    coverage for the `schema_version` allow-list to assert that `"1.2"` reports validate successfully
    (with `fidelity_audit` required, mirroring the existing `"1.1"` case) and that `"1.1"` reports remain
    valid and unaffected (legacy contract, no regression).
- **Constraint**: No test's assertion *target* (pass/fail expectation, offsets, counts) changes — only the
  literal string value being matched and the stale comment.
- **Verification**: `tests/test_fidelity.py`, `tests/test_ocr_fidelity_precision.py` (including the
  corrected comment), `tests/test_e2e_fidelity.py` all migrated as specified. `tests/test_report.py`
  received two new tests (`test_schema_1_2_with_document_fidelity_audit_is_valid`,
  `test_legacy_schema_versions_remain_valid`) plus the `schema_version` literal update in
  `test_minimum_layout_and_page_wire_shape`; no pass/fail target changed on any pre-existing test, and
  `tests/test_models.py::test_relatorio_defaults` (outside the original file list, added under a
  narrowly-scoped orchestrator follow-up authorization) was updated to expect the new `"1.2"` default —
  a direct, mechanical consequence of Task 1's approved bump, not a scope/requirements change.

## Operational step (post-approval/archive, not an implementation task): Apply spec deltas via `openspec archive`
- **Description**: The two spec deltas in this change (`specs/juridical-pdf-conversion/spec.md`,
  `specs/phase1-quality-gate/spec.md`) will be applied to the corresponding published specs
  (`openspec/specs/juridical-pdf-conversion/spec.md`, `openspec/specs/phase1-quality-gate/spec.md`) by the
  standard `openspec archive` command itself, once this change is approved. This is not an implementation
  task that Codex or the orchestrator performs by hand-editing files, and it is intentionally excluded
  from the Acceptance Criteria checklist below — it cannot be completed, partially completed, or checked
  off before archive runs, and pretending otherwise would misrepresent pre-archive state. Do not hand-edit
  the published specs directly.
- **Constraint**: Only the two scenarios identified in `design.md` § Spec Language Correction change.
  No other scenario in either spec file is touched. The Requirement title "Controle de Fidelidade e
  Incerteza OCR" is NOT renamed.

## Task 4: Cross-reference note in `duplication-context-precision` — DONE (verified)
- **Description**: Added a short note near the top of
  `openspec/changes/duplication-context-precision/proposal.md` and
  `openspec/changes/duplication-context-precision/design.md` stating that `issue_type` has been renamed
  from `duplication` to `internal_repetition` by `duplication-issue-semantic-neutrality`, and that all
  `duplication` references in that change's existing text refer to the legacy (pre-rename) value name as
  of when they were written — not to any change in the blocked detection heuristic.
- **Constraint**: This task does NOT reopen, unblock, or modify the heuristic content of
  `duplication-context-precision`. It adds a pointer only.
- **Verification**: `git diff --stat` shows only additive "Cross-reference note" sections inserted
  immediately after the existing `## Status:` line in both `proposal.md` and `design.md`; no other line in
  either file changed. `duplication-context-precision/tasks.md` and its `Status: BLOCKED` line remain
  untouched — the blocking Task 1 (verified positive control) is still NOT STARTED.

## Task 5: Verification — DONE (re-run by orchestrator, independent of Codex's own run)
- **Description**: Run `uv run pytest`, `uv run ruff check`, `git diff --check`, `uv run openspec validate
  duplication-issue-semantic-neutrality --strict`, and `uv run openspec validate --all --strict`. No
  commit/push/archive without explicit orchestrator (Claude) approval after diff review, as always.
- **Result**: `uv run pytest -q` → `1072 passed, 2 warnings` (baseline before this change: 1070 passed;
  +2 accounts for the two new schema-version tests). `uv run repo-jur test conformance` → exit 0.
  `git diff --check` → exit 0 (no trailing whitespace). `openspec validate
  duplication-issue-semantic-neutrality --strict` → valid. `openspec validate --all --strict` → 14/14
  passed. `ruff check` was NOT run: `ruff` is not installed in this environment and is not declared as a
  dependency anywhere in `pyproject.toml` (`dependencies` or `[dependency-groups].dev`) — this is an
  environment/tooling gap, not a project quality-gate configured for this repo, and not a code defect.

## Acceptance Criteria
- [x] No normative scenario in `juridical-pdf-conversion/spec.md` or `phase1-quality-gate/spec.md`
      asserts that OCR caused the repetition based solely on the internal-repetition detector's output.
      (Verified in the change's own spec deltas, `specs/juridical-pdf-conversion/spec.md` and
      `specs/phase1-quality-gate/spec.md`; the published specs are not yet updated because the
      `openspec archive` operational step (see above) has not run — that is expected pre-archive state,
      not a defect.)
- [x] The persisted `issue_type` value emitted by `detect_duplications` is `internal_repetition` (not
      `duplication`), and it is emitted under `schema_version: "1.2"` (default `Relatorio.schema_version`
      confirmed `"1.2"` in `models.py:138`).
- [x] `Relatorio.schema_version` default is `"1.2"`; `report.py::validate_report_contract` accepts
      `"1.0"`, `"1.1"`, and `"1.2"`, applying the `fidelity_audit`-required rule to both `"1.1"` and
      `"1.2"` identically. `"1.1"` reports (with `issue_type == "duplication"`) remain valid and are not
      rejected — Schema 1.1 is a supported legacy contract, not a removed one. Confirmed by
      `tests/test_report.py::test_legacy_schema_versions_remain_valid` and
      `test_schema_1_2_with_document_fidelity_audit_is_valid`, both passing.
- [x] `min_len`, the sliding-window match algorithm, match extension, gap computation, and the
      `gap <= 1.5 * match_len` threshold in `detect_duplications` are byte-for-byte unchanged. Confirmed
      by direct line-range diff of `fidelity.py:60-109` against the pre-implementation baseline: the only
      difference is the `issue_type` literal on the `FidelityIssue` construction line.
- [x] `result.warnings` structure and the privacy-safe contract (numeric offsets only, UUID4 `issue_id`,
      no content-derived data) are unchanged. Confirmed: no diff touches `result.warnings` handling or the
      `FidelityIssue`/`DocumentFidelityIssue` field set in `models.py`; existing privacy-contract tests
      (e.g. `test_result_warnings_remains_strictly_list_of_strings`,
      `test_document_fidelity_contract_accepts_only_numeric_occurrences`) still pass unmodified.
- [x] No `logs/*.report.json` historical artifact is rewritten or modified. No automatic migration tool
      from Schema 1.1 to 1.2 is implemented or required. Confirmed: `git status`/`git diff --stat` show
      zero changes under `logs/`; no migration code was added anywhere in the diff.
- [x] All test sites asserting on the literal string `"duplication"` are identified (Task 2 list) and
      migrated to `internal_repetition` with no change to pass/fail expectations.
- [x] The schema-version bump decision (1.1 legacy vs. 1.2 current) is documented in `design.md` with
      supporting normative rationale (done at proposal time; re-verified at implementation time — no new
      consideration emerged that would change the decision).
- [x] `uv run openspec validate duplication-issue-semantic-neutrality --strict` passes.
- [x] `uv run openspec validate --all --strict` passes.
- [~] `uv run pytest`, `uv run ruff check`, and `git diff --check` pass. `pytest` and `git diff --check`
      pass; `ruff check` could not run because `ruff` is absent from this environment/`pyproject.toml` —
      recorded as a known tooling gap, not treated as a failure of this change.

## Explicit Non-Goals (repeated from proposal.md for implementer visibility)
- No change to `entity_consistency_checker`, `monitor_sensitive_tokens`, `detect_visual_uncertainty`.
- No reopening or heuristic change to `duplication-context-precision`.
- No OCR reprocessing.
- No rewriting of historical `logs/*.report.json` artifacts.
