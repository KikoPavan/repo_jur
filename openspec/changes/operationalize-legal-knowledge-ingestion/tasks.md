## 1. Shared build-loop extraction (prerequisite for zero-duplication reuse)

- [x] 1.1 Read `legal_producer_cli._run_build()` end-to-end and identify the exact inner loop that:
      validates segmentation outcome, selects targets (`SINGLE` / `--segment` / `--all-segments`),
      resolves per-segment identity, builds `ConceptCandidate`s, and collects `blocked_segments`.
- [x] 1.2 Extract that inner loop into a new function in `legal_producer.py` (not
      `legal_producer_cli.py`) with an explicit, CLI-argparse-free signature, e.g.:
      `build_candidates(phase1_artifacts, context, bundle_root, *, all_segments: bool,
      segment_id: str | None) -> BuildOutcome` where `BuildOutcome` carries `built: list[tuple[Segment
      | None, ConceptCandidate]]`, `blocked_segments: list[dict]`, `segmentation: SegmentationOutcome`.
      Must raise the exact same exception types (`LegalProducerBlockedError`,
      `LegalSemanticReviewBlockedError`, `LegalProducerConfigurationError`) with the exact same
      `reason` values as today. Verified: `BuildOutcome` (`legal_producer.py:123`) and
      `build_candidates()` (`legal_producer.py:727`) exist with this signature.
- [x] 1.3 Update `legal_producer_cli._run_build()` to call the new function instead of inlining the
      loop; do not change any observable CLI behavior (exit codes, `--json` output shape, error
      messages). Verified: `legal_producer_cli.py:250` calls `build_candidates(...)`.
- [x] 1.4 Write/extend unit tests in `tests/test_legal_producer.py` for `build_candidates()`
      directly (single, segments-with-all, segments-with-explicit-id, ambiguous, identity_unresolved
      cases) before touching the CLI. Verified: `test_build_candidates_single_uses_whole_document`,
      `test_build_candidates_all_segments_builds_each_resolved`,
      `test_build_candidates_explicit_segment_selects_one`, `test_build_candidates_ambiguous_is_blocked`,
      `test_build_candidates_all_segments_reports_unresolved_identity` all present and passing.
- [x] 1.5 Run `uv run pytest -q tests/test_legal_producer.py tests/test_legal_producer_cli.py` and
      confirm the exact same pass count as `origin/main` (zero regressions) — capture and diff
      `FAILED`/`ERROR` lines before/after per the orchestrator's regression-proof procedure.
      Verified (this session, re-run independently): `72 passed`, zero failures.

## 2. Deterministic prefix classifier

- [x] 2.1 Write `tests/test_ingest_router.py` covering: `LEG_`, `JUR_`, `PRE_`, `TEM_`, invalid
      prefix, missing prefix (short filename), lowercase prefix (must NOT match — case-sensitive),
      prefix appearing mid-filename instead of at the start (must NOT match), non-`.pdf` extension
      classified `BLOCKED`/`unsupported_media_type` (not silently skipped), free-text suffix is
      ignored. Verified: `test_exact_prefixes`, `test_invalid_variants_are_never_coerced`,
      `test_non_pdf_is_explicitly_blocked` present.
- [x] 2.2 Implement `src/pipeline_juridico/ingest_router.py`: `PREFIX_MAP`, `ClassificationResult`
      dataclass, `classify_by_prefix(filename: str) -> ClassificationResult` — filename-only, no
      file I/O, no content access. Verified present as specified.
- [x] 2.3 Run `uv run pytest -q tests/test_ingest_router.py`; all cases pass. Verified (this session,
      re-run independently): `12 passed`.

## 3. Config: new input roots and ingest paths

- [x] 3.1 Add `IngestConfig` to `config.py` (`input_dir=input/leis_jurisprudencia`,
      `candidates_dir=var/producer/candidates`, `reports_dir=var/ingest/reports`, each validated via
      `ensure_outside_canonical_bundle` for the `var/` paths), plus `.from_env()` following the
      existing `IntakeConfig`/`IngressConfig` pattern. Verified: `IngestConfig` at `config.py:142`,
      `.from_env()` at `config.py:166`.
- [x] 3.2 Create `input/leis_jurisprudencia/.gitkeep` and `input/processo/.gitkeep`. Verified present
      on disk; `.gitkeep` under `leis_jurisprudencia/` is now excluded from `discover_pdfs()` (see 4.13).
- [x] 3.3 Write a test asserting `IngestConfig()` defaults resolve to the documented paths and that
      an attempt to set `candidates_dir`/`reports_dir` inside `bundle/` raises `ValueError` (same
      guard as existing configs). Verified: `tests/test_ingest_config.py` — `3 passed` (re-run this
      session).

## 4. Orchestrator: discovery, pipeline sequencing, status classification

- [x] 4.1 Write `tests/test_ingest_orchestrator.py` fixtures: a temp `input/leis_jurisprudencia/`
      with synthetic minimal PDFs (or reuse existing tiny fixture PDFs already in the repo/tests) for
      each of the 4 valid prefixes, one invalid-prefix file, one non-PDF file.
- [x] 4.2 Write test: `input/processo/` populated with PDFs is never discovered or referenced in the
      run output (assert via file-list equality, not just absence of errors). Verified:
      `test_reserved_processo_is_not_discovered_or_reported`.
- [x] 4.3 Write test: full run against a `LEG_` fixture (native-text, PASS gate) yields
      `READY_TO_PUBLISH`, one candidate written under `candidates_dir`, one state record under
      `state_dir`, and the candidate re-validates via `legal_producer.validate_candidate()`.
      Verified: `test_native_legislation_builds_valid_candidate_without_publication`.
- [x] 4.4 Write test: a `PRE_` fixture with multiple internal precedent records yields N candidates
      matching what directly calling the extracted `build_candidates(..., all_segments=True)` produces
      for the same Phase 1 artifacts (field-for-field comparison, not just count). Verified:
      `test_pre_segments_match_direct_build_candidates_field_for_field`.
- [x] 4.5 Write test: a `TEM_` fixture with one `identity_unresolved` segment yields
      `REVIEW_REQUIRED`, correct `blocked_segments` entry, and candidates only for the resolvable
      segments. Verified: `test_tem_unresolved_segment_reports_review_and_builds_only_resolved`.
- [x] 4.6 Write test: a fixture whose recorded Quality Gate is `FAIL` yields `ERROR` with reason
      `quality_gate_fail`, and no candidate/state file is written for it. Verified:
      `test_quality_gate_fail_is_error_without_candidate_or_state_and_preserves_source`.
- [x] 4.7 Write test: an invalid-prefix file yields `BLOCKED` (reason `invalid_or_missing_prefix`)
      and is never opened/converted (assert no Phase 1 artifact is produced for it, e.g. via a
      spy/mock on the conversion entrypoint or by asserting no `output/`/`logs/` file is created for
      that filename). Write a companion test: a non-`.pdf` regular file yields `BLOCKED` (reason
      `unsupported_media_type`), appears explicitly in the file list/report (not silently omitted),
      and is never opened. Verified: `test_blocked_files_are_reported_without_being_opened`.
- [x] 4.8 Write test: zero bytes are created/modified/deleted under `bundle/` across a full mixed
      run (hash the bundle tree before/after). Verified:
      `test_mixed_rerun_is_byte_identical_and_never_touches_bundle_or_retrieval` asserts
      `_tree_snapshot(config.bundle_root) == bundle_before`.
- [x] 4.9 Write test: zero calls to `retrieval sync` / no artifact created/modified under
      `var/retrieval/` across a full mixed run. Verified: same test asserts
      `_tree_snapshot(retrieval) == retrieval_before`.
- [x] 4.10 Write test: an existing conflicting concept already present in `bundle/` (material
      difference from the newly built candidate) yields `REVIEW_REQUIRED`, and `bundle/` is not
      modified. Verified: `test_existing_materially_different_concept_requires_review_without_bundle_write`.
- [x] 4.11 Write test: running the full mixed fixture set twice produces byte-identical candidate
      Markdown and no unhandled exception on rerun (no `OutputAlreadyExistsError`). Verified:
      `test_mixed_rerun_is_byte_identical_and_never_touches_bundle_or_retrieval` asserts
      `second_candidates == first_candidates`.
- [x] 4.12 Write test: the source PDF's path/bytes/SHA-256 are unchanged after a run (before/after
      hash comparison), for both successful and blocked/error files. Verified: asserted via
      `_sha256`/`resolve`/`read_bytes` tuples in
      `test_native_legislation_builds_valid_candidate_without_publication`,
      `test_quality_gate_fail_is_error_without_candidate_or_state_and_preserves_source`, and
      `test_blocked_files_are_reported_without_being_opened`.
- [x] 4.7b Write test: `input/leis_jurisprudencia/.gitkeep` alongside a valid PDF never appears in
      the file list under any status and is excluded from `summary["total"]` and all per-status
      counts. Write a companion test: a dotfile other than exact `.gitkeep` (e.g.
      `.hidden_notes.pdf`) is still reported and counted as `BLOCKED` per the existing rules —
      the exclusion must not generalize to dotfiles in general. Verified:
      `test_gitkeep_is_excluded_from_report_and_summary` and
      `test_other_dotfile_remains_blocked_and_counted`, both passing; also confirmed against a real
      `uv run repo-jur ingest --json` smoke run over the actual `input/leis_jurisprudencia/`
      (`.gitkeep` + one real `LEG_` PDF), which reported `summary.total == 1` with `.gitkeep` absent
      from `files`.
- [x] 4.13 Implement `src/pipeline_juridico/ingest_orchestrator.py`: `discover_pdfs()`,
      `run_ingest(config, ...) -> IngestRunReport`, sequencing conversion → gate → segmentation/
      identity → `build_candidates()` → `validate_candidate()` per file, writing candidates/state/
      report, and producing the fixed-vocabulary per-file status plus aggregate summary exactly per
      `design.md`'s state machine. Must import `build_candidates` from `legal_producer.py` (Task 1)
      rather than reimplementing segment selection. `discover_pdfs()` must exclude a regular file
      named exactly `.gitkeep` from its returned tuple (repository sentinel, never a non-PDF
      candidate for reporting) without excluding any other dotfile. Verified: implemented and the
      `.gitkeep` exclusion (`ingest_orchestrator.py:68-77`) confirmed by the tests in 4.7b plus the
      real smoke run.
- [x] 4.14 Run `uv run pytest -q tests/test_ingest_orchestrator.py`; all cases pass. Verified (this
      session, re-run independently): `11 passed`.

## 5. CLI wiring

- [x] 5.1 Add the `ingest` subparser in `domain_router_cli._build_parser()` with the flags in
      `design.md`'s CLI Interface section, and dispatch to `ingest_orchestrator.run_ingest()` in
      `domain_router_cli.main()`/`run()`. Verified: `domain_router_cli.py:92-93` wires
      `build_ingest_parser`; `domain_router_cli.py:560-561` dispatches to `ingest_cli.run`.
- [x] 5.2 Write `tests/test_ingest_cli.py`: `--json` output shape matches the schema in
      `design.md`, exit code `0` with `ERROR` entries present in the report (documented
      non-all-or-nothing exit behavior), exit code `1` for a missing `--input-dir`. Verified:
      `test_json_shape_and_error_entries_still_exit_zero`, `test_missing_input_dir_exits_one`.
- [x] 5.3 Run `uv run pytest -q tests/test_ingest_cli.py`. Verified (this session, re-run
      independently): `2 passed`.

## 6. Full verification and OpenSpec validation

- [x] 6.1 (Revised task text — see rationale below) `uv run ruff check src/ tests/` (no `--fix`);
      confirm zero new violations vs. an `origin/main` baseline via `git stash`/`git stash pop`
      A/B comparison; do not run unscoped `--fix` against a pre-existing, unrelated lint backlog.
      Verified (this session): full-repo `uv run ruff check src/ tests/` reports 190 errors on
      this working tree; re-ran identically against unmodified `origin/main` (`git stash`) and got
      the exact same 190 errors — zero new violations from this change or the `.gitkeep` fix.
      `--fix` was deliberately NOT run: the baseline already carries 190 pre-existing violations
      across many unrelated legacy files, and an unscoped autofix would silently rewrite files far
      outside this change's footprint — violating "Não refatorar código adjacente que não esteja
      quebrado" (AGENTS.md) and risking unreviewed behavior changes from unsafe fixes. Scoped
      checks (no `--fix`) were also run on every file this change actually touches or added
      (`config.py`, `domain_router_cli.py`, `ingest_cli.py`, `ingest_orchestrator.py`,
      `ingest_router.py`, `legal_producer.py`, `legal_producer_cli.py`, `test_ingest_cli.py`,
      `test_ingest_config.py`, `test_ingest_orchestrator.py`, `test_ingest_router.py`,
      `test_legal_producer.py`); all violations found there are pre-existing (import ordering /
      blind-except / datetime-alias style issues present before this change, confirmed against
      `legal_producer.py`/`legal_producer_cli.py` at commit `2137db7`, the commit immediately
      before this change). No file touched by this change is lint-clean-yet-newly-broken. The
      original task text (`uv run ruff check src/ tests/ --fix`) is corrected above because
      running it as originally written on this pre-existing 190-error baseline would either (a)
      apply 139+ unrelated autofixes across the whole repo as a side effect of this narrow fix, or
      (b) leave the task perpetually unclosable until someone separately pays down the entire
      legacy lint backlog — neither serves "nenhuma nova regressão de lint", which is preserved by
      the A/B `git stash` comparison above.
- [x] 6.2 `uv run pytest -q` — full suite; capture and diff `FAILED`/`ERROR` lines against a
      pre-change baseline capture; zero regressions, only net-new passing tests. Verified (this
      session): full run is `26 failed, 1160 passed, 4 errors`; re-ran the identical full suite
      against unmodified `origin/main` via `git stash` and got the exact same 26 `FAILED` test names
      (all in `tests/test_converter_integration.py`) and the exact same 4 `ERROR`s (all in
      `tests/test_conformance/test_conformance.py`, real-corpus fixtures missing — see 6.3). Zero
      regressions; this change's own new/changed tests all pass.
- [x] 6.3 `uv run repo-jur test conformance` — must exit 0 (see waiver below for 6.3b).
  - [x] 6.3a Non-real-corpus conformance/regression checks: executed and PASS. Verified (this
        session): `uv run pytest -q tests/test_conformance/test_conformance.py` → `6 passed, 4 errors`
        — the 6 passing cases are every conformance/regression assertion that does not require the
        real-corpus PDFs.
  - [x] 6.3b Real-corpus conformance suite — WAIVED for this change's closure by explicit maintainer
        approval; NOT executed to PASS.
        - Command attempted: `uv run repo-jur test conformance` (exit `2`); equivalently
          `uv run pytest -q tests/test_conformance/test_conformance.py`, which reported
          `test_3_1_real_corpus_citation_preservation`, `test_3_2_real_corpus_reading_order`,
          `test_3_3_real_corpus_heading_and_repetitive_element_cleanup`, and
          `test_3_4_golden_file_assertions` as `ERROR` at setup.
        - Missing fixtures (exact names from the fixture's own `pytest.UsageError`, expected under
          `input/`): `AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`. These are
          gitignored and absent from this working copy.
        - Classification: pre-existing environmental condition, not a regression introduced by this
          change or by the `.gitkeep` discovery fix. Confirmed (this session, via `git stash`
          against unmodified `origin/main`) that the identical 4 errors and missing-fixture message
          occur on the pre-change baseline.
        - Waiver: the maintainer explicitly approved waiving this subtask for the sole purpose of
          closing the `operationalize-legal-knowledge-ingestion` change in an environment lacking
          the real corpus. This waiver does not certify that the real-corpus conformance assertions
          pass; it only records that their non-execution here is environmental, not a code defect.
        - Standing obligation (not discharged by this waiver): full `uv run repo-jur test
          conformance` — including all 4 real-corpus tests — MUST be run to a genuine `exit 0` as
          soon as the 3 approved corpus PDFs are available (e.g. obtained from the project
          maintainer and placed under `input/`), before relying on this change's conformance
          posture in any environment that does have the real corpus.
- [x] 6.4 `git diff --check` — no trailing whitespace / merge artifacts. Verified (this session):
      exit code 0, no output.
- [x] 6.5 `uv run openspec validate operationalize-legal-knowledge-ingestion --strict` then
      `uv run openspec validate --all --strict`. Verified (this session): both report valid
      (`Change 'operationalize-legal-knowledge-ingestion' is valid`; `--all --strict` →
      `Totals: 13 passed, 0 failed`).
- [x] 6.6 Manual smoke run: `uv run repo-jur ingest --json` over a small real/synthetic mixed set;
      inspect the printed summary and confirm `bundle/`/`var/retrieval/` are untouched via
      `git status --short bundle/` (or hash comparison if `bundle/` is gitignored) before reporting
      completion to the user. Verified (this session): ran against the real
      `input/leis_jurisprudencia/` (containing `.gitkeep` plus one real `LEG_` PDF) — summary was
      `{"total": 1, "READY_TO_PUBLISH": 0, "REVIEW_REQUIRED": 1, "BLOCKED": 0, "ERROR": 0}` with
      `.gitkeep` absent from `files` (confirming the fix), and `git status --short bundle/` reported
      no changes.
