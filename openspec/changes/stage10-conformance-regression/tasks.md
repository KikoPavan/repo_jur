## 0. Gating note

HR-1..HR-5 are **APPROVED** and incorporated into the plan:
- CLI command exactly `repo-jur test conformance` (HR-1).
- Conformance runner invokes pytest through the active Python interpreter using `sys.executable -m pytest` with two explicit bounded executions over `tests/test_conformance/`: (1) `sys.executable -m pytest -m conformance tests/test_conformance/`, and (2) `sys.executable -m pytest -m regression tests/test_conformance/` (HR-2).
- Real-corpus golden expected artifacts are stored as git-tracked lightweight text/JSON/SHA-256 assets under `tests/test_conformance/golden/`, while raw PDFs remain gitignored and local (HR-3). The reproducible gate MUST NOT depend on live nondeterministic external OCR/LLM output.
- Structured report written by default to `var/conformance/report.json` (overridden via `--json-report <path>`), which is derived, non-canonical, never written inside bundle/ or process-storage, and distinguishes at minimum `CONFORMANCE_FAILURE`, `REGRESSION_FAILURE`, and `ENVIRONMENT_CONFIGURATION_ERROR` (HR-4).
- The default Stage-10 acceptance gate is completely deterministic and offline with respect to external model/service/OCR/LLM inference, using frozen intermediate/golden assets or deterministic test adapters, still verifying downstream contract behavior and canonical immutability (HR-5).
- "Dual-bounded-context end-to-end" MUST NOT imply Judicial Process Retrieval, which is explicitly OUT OF SCOPE. Judicial Process conformance ends at the authorized Judicial Process producer/canonical process-storage boundary.

No Stage-10 production or test code is implemented inside this planning change; implementation is a separately authorized task.

## 1. C10.1 — Conformance verification: focused tests (TDD — red first)

- [x] 1.1 Write failing tests for ZIP preflight conformance: verify that ingress correctly rejects encrypted, malformed, or invalid ZIP packages, and that accepted files are preserved before conversion.
- [x] 1.2 Write failing tests for SHA preservation conformance: verify that the preserved file hash matches the exact accepted bytes in the receiver log, and any mismatch is blocked.
- [x] 1.3 Write failing tests for page record and marker conformance: verify that conversion produces exactly one page record per physical page, and page markers are strictly canonical `[[Pág. N]]` and sequentially numbered `1..N`.
- [x] 1.4 Write failing tests for Quality Gate and Producer conformance: verify that Quality Gate states are strictly limited to PASS, PASS_WITH_WARNINGS, and FAIL, and that a FAIL state is blocked from entering any Producer.
- [x] 1.5 Write failing tests for storage boundary isolation: verify that executing the Judicial Process pipeline writes strictly to separate process storage and never writes under `repo_jur/bundle/`.
- [x] 1.6 Write failing tests for retrieval zero-write and isolation conformance: verify that retrieval sync, rebuild, and search paths perform zero writes to the Legal bundle, and never access Judicial Process storage, symbols, or retrieval mechanisms (with Judicial Process Retrieval remaining explicitly out of scope).

## 2. C10.1 — Conformance verification: minimal implementation

- [x] 2.1 Create the conformance test suite file structure under `tests/test_conformance/` to implement the contract check matrix.
- [x] 2.2 Implement the synthetic fixture package generator that produces invalid, malformed, and valid ZIP packages to run against the ingress pipeline.
- [x] 2.3 Implement the storage mutation watcher within the test harness that asserts absolutely zero writes are made to `repo_jur/bundle/` during Judicial Process and retrieval runs.
- [x] 2.4 Implement the schema validator wrapper that checks the exact Quality Gate status outputs and routes conformantly.

## 3. C10.2 — Regression validation: focused tests (TDD — red first)

- [x] 3.1 Write failing tests for real corpus citation preservation: verify that cleaning rules do not alter, remove, or modify any legal citation tokens (such as Article or Paragraph numbers) in `L10.406_CC_2002.pdf`.
- [x] 3.2 Write failing tests for real corpus reading order: verify that multi-column and editorial layouts in `AINTARESP_1462304-PA.pdf` and `Inf0024E.pdf` maintain correct, human-readable paragraph reading order.
- [x] 3.3 Write failing tests for real corpus heading and repetitive element cleanup: verify that repetitive footers, headers, url strings, page counters, and signature blocks are successfully removed in `REsp_1704551-SP.pdf` and `CC_2002.pdf` without modifying the core legal text.
- [x] 3.4 Write failing tests for golden-file assertions: compare the full output of real-corpus PDF conversions against the git-tracked golden markdown/JSON/SHA-256 files stored under `tests/test_conformance/golden/`, asserting normalized-content identity after whitespace and line-ending normalization in a completely offline, deterministic manner without live model dependencies.

## 4. C10.2 — Regression validation: minimal implementation

- [x] 4.1 Create the golden markdown files under `tests/test_conformance/golden/` for each of the four real-corpus PDFs by taking the approved, fully cleaned historical outputs.
- [x] 4.2 Implement the whitespace-insensitive and line-ending-normalized offline deterministic comparison engine in the regression test suite.
- [x] 4.3 Create the environment-check fixture that validates the existence of the gitignored raw PDFs and fails fast with actionable instructions if the local worktree is missing the files.

## 5. C10.3 — Tooling and CLI Integration: focused tests (TDD — red first)

- [x] 5.1 Write failing tests for the `repo-jur test conformance` CLI interface: assert it accepts the `--json-report` and `--verbose` arguments and parses them correctly.
- [x] 5.2 Write failing tests for CLI exit codes and structured report categories: assert it returns `0` on 100% test pass, `1` on any conformance or regression failure, and `2` on configuration/workspace/environment errors, and compiles structured report outcomes into `CONFORMANCE_FAILURE`, `REGRESSION_FAILURE`, or `ENVIRONMENT_CONFIGURATION_ERROR`.
- [x] 5.3 Write failing tests for source-inspection checks: assert that a python static check verifies `src/pipeline_juridico/contracts.py` remains free of prohibited imports from domain-specific modules.
- [x] 5.4 Write failing tests for no-vector-infrastructure invariants: assert that a script checks that no vector DB, embedding model, or neural reranking package is loaded or imported in the virtualenv.

## 6. C10.3 — Tooling and CLI Integration: minimal implementation

- [x] 6.1 Register the `test` subcommand and `conformance` action under the existing `repo-jur` CLI entrypoint in `src/pipeline_juridico/domain_router_cli.py`.
- [x] 6.2 Implement the CLI runner in `pipeline_juridico/domain_router_cli.py` that invokes pytest through the active Python interpreter using `sys.executable -m pytest` with two explicit bounded executions: (1) `sys.executable -m pytest -m conformance tests/test_conformance/` and (2) `sys.executable -m pytest -m regression tests/test_conformance/`.
- [x] 6.3 Implement the JSON report writer that parses pytest terminal outcomes, groups them into `CONFORMANCE_FAILURE`, `REGRESSION_FAILURE`, and `ENVIRONMENT_CONFIGURATION_ERROR` categories, and saves them by default to `var/conformance/report.json`, or overridden location.
- [x] 6.4 Implement the static source-inspection import validator and the no-vector-infrastructure environment verifier inside the CLI command execution.
- [x] 6.5 Run `openspec validate --all --strict` and ensure 100% of specifications and the Stage 10 change are fully valid.
