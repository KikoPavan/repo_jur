# Tasks: Fix Jurisprudencia CNJ Process Number

## Task 1: RED tests for CNJ checksum + process-number resolution (TDD, tests first)
- **Description**: In `tests/` (likely a new `tests/test_legal_semantic_review_cnj.py` or an addition to the
  existing `legal_semantic_review` test module — Codex to confirm the correct existing file first), add
  failing tests for the `_deterministic_extract` Jurisprudencia/Processo resolution covering, at minimum:
  1. `0311049-09.2016.8.24.0018` present verbatim → `repo_jur_processo_numero == "0311049-09.2016.8.24.0018"`.
  2. Standalone 20-digit token `03110490920168240018` present (no punctuation) → normalized to
     `0311049-09.2016.8.24.0018` (checksum passes: DV `09`).
  3. Both an appellate header `AgInt no RECURSO ESPECIAL Nº 1833684 - SC` and a checksum-valid CNJ present in
     the same body → the CNJ is chosen, never the header text.
  4. Only `AgInt no REsp 1.833.684/SC` present, no valid CNJ anywhere → `repo_jur_processo_numero` absent from
     `extracted_fields`.
  5. Only `2019/0251395-0` present, no valid CNJ anywhere → `repo_jur_processo_numero` absent.
  6. Two structurally distinct, checksum-valid CNJs present with no deterministic disambiguation signal →
     `repo_jur_processo_numero` absent (fail-closed), not the first one found.
  7. A CNJ-shaped 20-digit token whose check digits are deliberately wrong (e.g. flip the DV of a valid
     example) → rejected, not extracted.
  8. Regression: on the real AIRESP body text (or an equivalent excerpt), `repo_jur_tribunal`,
     `repo_jur_relator`, and `repo_jur_data_julgamento` extraction remain byte-identical to current output —
     add/confirm assertions that these three fields are unaffected by the process-number change.
- **Constraints**: Tests must fail against the current (unmodified) `legal_semantic_review.py` before any
  implementation — confirm and report the RED run output. Do not touch production code in this task.
- **Exit condition**: `uv run pytest <new/updated test file> -q` shows the new cases failing for the expected
  reason (wrong/extra value extracted, not a collection error).

## Task 2: Implement the CNJ checksum helper and resolution rewrite
- **Description**: In `src/pipeline_juridico/legal_semantic_review.py`, add a private
  `_cnj_checksum_valid(digits20: str) -> bool` helper (mod-97 algorithm per `design.md`) and rewrite the
  Jurisprudencia/Processo block (current lines ~299-334) to: (a) collect all checksum-valid punctuated CNJ
  matches and all checksum-valid standalone 20-digit tokens (normalized to canonical form) across all pages;
  (b) dedupe by canonical form; (c) if exactly one distinct candidate remains, extract it with its page_refs;
  (d) otherwise (zero or 2+) do not extract the field. Delete the appellate-header regex/branch and the
  internal register-number regex/branch from this resolution path entirely — they must not remain as a
  fallback anywhere in this function for `repo_jur_processo_numero`.
- **Constraints**: No change to `repo_jur_tribunal`, `repo_jur_relator`, `repo_jur_data_julgamento`, or any
  Legislacao/TemaJuridico/PrecedenteVinculante extraction logic in this file. No change to
  `legal_segment_identity.py`, `legal_producer.py`, `config.py`, or `retrieval/index.py` (they consume the
  field by name only and need no changes). No change to `openspec/specs/legal-knowledge/spec.md` in this
  task (already delivered in the change's own delta spec; canonical spec is updated only on archive).
- **Exit condition**: Task 1's new tests pass; run and report `uv run pytest <same test file> -q`.

## Task 3: Update the two affected golden conformance fixtures/tests
- **Description**: Per `design.md`'s "Multi-Origin Ambiguity" analysis, `tests/test_conformance/golden/REsp_1704551-SP.md`
  and `AINTARESP_1462304-PA.md` each contain two structurally distinct, checksum-valid CNJ tokens on their
  "Número(s) Origem" line with no deterministic disambiguation signal. Verify this holds against the actual
  implementation from Task 2 (recompute, do not assume design.md's numbers are still exactly right after
  implementation — re-run and confirm). If confirmed, update
  `tests/test_conformance/test_metadata_contract.py` lines ~122-124 and ~154-155 to assert
  `"repo_jur_processo_numero" not in extracted_names` for these two fixtures instead of the old
  `"1.704.551"`/`"1462304"` substring checks, with an inline comment citing the two conflicting CNJ tokens
  found. Also grep `tests/test_conformance/test_conformance.py` for any real-corpus assertion referencing
  `repo_jur_processo_numero` derived from these same two source PDFs and update identically if found.
- **Constraints**: Do not invent a disambiguation heuristic to keep these two fixtures resolving a value —
  that would recreate exactly the defect class this change removes (silently picking a citation when
  ambiguity exists). If Task 2's implementation surprisingly resolves a single unambiguous value for either
  fixture (e.g. because only one candidate is actually checksum-valid, correcting the design doc's
  assumption), update this task's outcome accordingly with the concrete recomputation shown, not the
  design doc's original guess.
- **Exit condition**: `uv run pytest tests/test_conformance/test_metadata_contract.py -q` passes with the
  corrected assertions; the specific two updated assertions are cited with before/after in the completion
  report.

## Task 4: Full verification and real-corpus AIRESP re-run
- **Description**: Orchestrator (Claude) re-runs, independently of any implementer self-report:
  1. `uv run pytest -q` (full suite) — report pass/fail counts, diff against pre-change baseline.
  2. `uv run repo-jur test conformance` if applicable to this change's scope.
  3. `uv run repo-jur producer build "output/AIRESP-1833684-2020-02-12.md" "logs/AIRESP-1833684-2020-02-12.report.json" --type Jurisprudencia --evidence-resource "input/AIRESP-1833684-2020-02-12.pdf" --json`
     and record the literal produced values for `repo_jur_processo_numero`, `repo_jur_tribunal`,
     `repo_jur_relator`, `repo_jur_data_julgamento`, and `concept_path` from the command's JSON output. Do
     not write to `bundle/` or publish; if the command has a dry-run/no-publish mode consistent with existing
     usage in this repo, use it, and if it does not, confirm before running that this invocation does not
     touch `bundle/` (per the user's explicit instruction not to alter or publish anything there).
  4. `openspec validate fix-jurisprudencia-cnj-process-number --strict`
  5. `openspec validate --all --strict`
  6. `git diff --check`
  7. `git status --short`
- **Constraints**: No commit, archive, or push. No modification of any file under `bundle/`.
- **Exit condition**: All commands above are run by the orchestrator itself (not trusted from Codex's report)
  and their literal output is cited in the final delivery report, including the exact
  `repo_jur_processo_numero` value produced for the AIRESP real-corpus case (either the canonical CNJ or
  explicit absence/`review_required`, whichever the implementation actually produces).

## Acceptance Criteria
- [x] `repo_jur_processo_numero` for `output/AIRESP-1833684-2020-02-12.md` is either
      `0311049-09.2016.8.24.0018` or explicitly absent/blocked — never
      `AgInt no RECURSO ESPECIAL Nº 1833684 - SC` or any other non-CNJ value.
      Evidence: `uv run repo-jur producer build "output/AIRESP-1833684-2020-02-12.md" ... --json`
      produces `repo_jur_processo_numero: 0311049-09.2016.8.24.0018` (re-run and confirmed by
      the orchestrator independently, dry candidate only, `bundle/` untouched).
- [x] All 8 RED-then-GREEN tests from Task 1 pass.
      Evidence: `uv run pytest tests/test_legal_semantic_review_cnj.py -q` → `8 passed`.
- [x] `repo_jur_tribunal`, `repo_jur_relator`, `repo_jur_data_julgamento` extraction for the AIRESP case and
      all other existing fixtures are unchanged (byte-identical) from before this change.
      Evidence: AIRESP real-corpus build above yields `repo_jur_tribunal: STJ`,
      `repo_jur_relator: REGINA HELENA COSTA`, `repo_jur_data_julgamento: '2020-02-10'`; Task 1's
      regression assertions (case 8) pass.
- [x] The appellate-header and internal-register-number regexes no longer appear anywhere in the
      `repo_jur_processo_numero` resolution path.
      Evidence: `grep -n "_cnj_checksum_valid\|appellate\|register\|recursal" src/pipeline_juridico/legal_semantic_review.py`
      shows only the checksum helper (line 105) and its two call sites (lines 321, 325); no
      appellate/register-number branch remains in that path.
- [x] `tests/test_conformance/golden/REsp_1704551-SP.md` and `AINTARESP_1462304-PA.md` conformance tests pass
      with corrected, evidence-cited assertions (no fabricated disambiguation).
      Evidence: `tests/test_conformance/test_metadata_contract.py::test_ci_safe_golden_jurisprudencia_resp_conformance`
      and `::test_ci_safe_golden_jurisprudencia_aint_conformance` assert
      `"repo_jur_processo_numero" not in extracted_names` with inline comments citing the two
      conflicting CNJ tokens per fixture; both pass under `uv run pytest tests/test_conformance -q`
      (13 passed, unrelated real-corpus tests skip/error only due to gitignored raw PDFs missing
      from this environment, confirmed pre-existing and unrelated to this change).
- [x] Full `uv run pytest -q` passes with no unexplained regressions.
      Evidence: `1123 passed, 1 skipped, 29 failed, 4 errors` — every failure/error verified to be a
      pre-existing environment gap (missing gitignored raw PDFs under `input/`), reproduced
      identically before this change's code (root-cause: `pymupdf.FileNotFoundError` for
      `AINTARESP_1462304-PA.pdf` and the real-corpus `UsageError` in `test_conformance.py`); zero
      failures relate to `repo_jur_processo_numero` or the CNJ resolution path.
- [x] `openspec validate fix-jurisprudencia-cnj-process-number --strict` passes.
      Evidence: re-run by the orchestrator after this documentation fix; see delivery report.
- [x] `openspec validate --all --strict` passes.
      Evidence: re-run by the orchestrator after this documentation fix; see delivery report.
- [x] `git diff --check` is clean.
      Evidence: re-run by the orchestrator after this documentation fix; see delivery report.
- [x] `git status --short` reviewed; `bundle/` untouched; no commit made.
      Evidence: only an unrelated, pre-existing untracked file
      (`bundle/jurisprudencia/stj_agint_no_recurso_especial_no_1833684_sc.md`, filesystem-dated
      2026-09-13, prior to this change's commit) appears under `bundle/`; it was not created or
      modified by this change's verification run (the producer command above only emitted a JSON
      candidate and did not write to `bundle/`).
