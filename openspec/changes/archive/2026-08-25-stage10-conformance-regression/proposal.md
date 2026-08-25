# Proposal: Stage 10 — Conformance and Regression Planning

## Why

Stages 1–9 are closed and archived. The repository now has complete implementation of all pipeline phases: Ingress, Preflight, SHA, Preservation, Conversion, Critical-data validation, Quality Gate, Domain Routing, Semantic Review, Producers, and Legal Knowledge Retrieval. To ensure the complete codebase is unified, safe, and strictly conformant to all frozen specifications, Stage 10 must establish the authoritative **Conformance / Regression** capability (`implementation-plan-repo-jur-v1.1-FROZEN.md` §12, §13; `technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §10.5, §16.3, §17, §18 Stage 10). This capability runs both bounded-context flows end-to-end (clarifying that Legal Knowledge conformance may run through Legal Knowledge Retrieval, but Judicial Process conformance ends at the authorized Judicial Process producer/canonical process-storage boundary, with Judicial Process Retrieval remaining explicitly out of scope), enforces strict filesystem and logical boundaries, and ensures no regressions occur on existing features.

This is an autonomous planning task. No production or test code will be implemented or modified during this planning change; we produce the complete planning artifacts (proposal, design, task list, spec delta) for subsequent human review and approval.

## What Changes

- **Modify `contract-harness` specification** to formally integrate Conformance and Regression requirements: establish normative requirements for Dual-bounded context end-to-end flows (where Legal Knowledge conformance may run through Legal Knowledge Retrieval, but Judicial Process conformance ends at the authorized Judicial Process producer/canonical process-storage boundary, with Judicial Process Retrieval explicitly out of scope), Bounded-context storage isolation, Retrieval zero-write and isolation constraints, Real-corpus regression checks, and Source-inspection couplings.
- **Define local operational CLI command surface** `repo-jur test conformance` (tech-spec §14) as a diagnostic tool that executes the entire conformance and regression validation matrix and reports structured outcomes.
- **Define Conformance Matrix** mapping Stage 1–9 specifications and invariants directly to executable checks.
- **Formulate Regression Corpus strategy** to run deterministic synthetic tests alongside real-corpus PDF golden-file assertions (reproducibility and normalized-content identity checks).
- **Incorporate complete planning artifacts** in the active OpenSpec change `stage10-conformance-regression`.

## Capabilities

### New Capabilities

None. Stage 10 is test-only and tooling-based; no new core pipeline capabilities are introduced.

### Modified Capabilities

- `contract-harness`: Modified to formally declare the Conformance & Regression requirements and scenarios that prove dual-bounded context safety, storage isolation, and zero regression across the repository.

## Impact

- **Primary affected code (planned)**: Additive subcommand `repo-jur test conformance` registered in `src/pipeline_juridico/domain_router_cli.py`, a new conformance test orchestrator module `src/pipeline_juridico/conformance_runner.py` (or integrated in CLI), and a comprehensive conformance and regression test suite under `tests/test_conformance/`. Zero changes are made to existing production or test code during this planning phase.
- **Inputs consumed**: Existing synthetic fixtures and gitignored real-corpus PDFs in `input/` (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, and `L10.406_CC_2002.pdf`) as well as current codebase sources for source-inspection.
- **Invariants validated**: Absolute zero-write over `repo_jur/bundle/` by retrieval and process pipelines; correct RouteTarget routing; correct GateState; domain-schema independence; no Stable IDs; no vector/embedding infrastructure; and no automatic status or metadata mutations.

## Non-Goals

- Modifying the semantics of any closed Stage 1–9 pipeline component.
- Introducing new runtime or pipeline behavior (e.g., embeddings, vector DBs, LLM rerankers).
- Introducing Judicial Process Retrieval (which remains out of scope).
- Adding canonical fields or changing the Domain Router schema.
- Automatic git commits, merges, or pushes.
- Mutating any canonical artifacts or historical outputs.

## Residual Risks

1. **Missing Gitignored PDF Fixtures in fresh worktrees**: Freshly cloned worktrees do not carry the raw PDF files. *Mitigation*: The planning design mandates linking/copying from `/home/kiko/devops/repo_jur/input` to the local worktree `input/` directory, and failing gracefully with clear environment instructions if the source directory is unavailable.
2. **Pytest Runtime dependency in CLI command**: Running `repo-jur test conformance` requires pytest. *Mitigation*: The design ensures the command runs pytest within the active virtualenv (`.venv`) via `sys.executable -m pytest` or alerts the operator with a detailed diagnostic if pytest is not installed.
3. **Flaky OCR assertions**: Real corpus regression could theoretically suffer from model nondeterminism in live execution. *Mitigation*: This risk is completely eliminated. HR-5 mandates that the default Stage-10 acceptance gate is completely deterministic and offline, using frozen expected goldens or adapters, and never running live nondeterministic models.

## Approved Human Review Decisions (HR-1..HR-5)

- **HR-1 — CLI Command Naming and Structure (APPROVED)**: The Stage-10 operational CLI is exactly `repo-jur test conformance`, integrated additively into the existing `repo-jur` entrypoint (`domain_router_cli.py`), keeping command surfaces uniform and isolated.
- **HR-2 — Subprocess-based Pytest Execution (APPROVED WITH PRECISION)**: Do not invoke a bare `pytest` executable from PATH. The conformance runner MUST invoke pytest through the active Python interpreter using `sys.executable -m pytest`. Use two explicit bounded executions over `tests/test_conformance/`:
  1. `sys.executable -m pytest -m conformance tests/test_conformance/`
  2. `sys.executable -m pytest -m regression tests/test_conformance/`
  Proposal, design, normative spec and tasks MUST express one consistent execution contract. Do not retain contradictory language such as subprocess.run(["pytest", ...]).
- **HR-3 — Real Corpus Golden Artifacts Storage (APPROVED WITH PRECISION)**: Lightweight golden expected artifacts are Git-tracked under `tests/test_conformance/golden/`. Heavy source PDFs remain gitignored/local. Goldens may be deterministic text/JSON or SHA-256 expectations as appropriate, but must remain reviewable and version-controlled. A reproducible Stage-10 gate MUST NOT depend on live nondeterministic external OCR/LLM output. Whitespace normalization alone is not an acceptable mitigation for model nondeterminism.
- **HR-4 — Failure Classification Diagnostic Report (APPROVED WITH PRECISION)**: Every `repo-jur test conformance` execution produces a structured derived report by default at `var/conformance/report.json`. `--json-report <path>` overrides the report destination. The report is derived/non-canonical, must never be written inside bundle/ or canonical process storage, and must distinguish at minimum:
  - CONFORMANCE_FAILURE
  - REGRESSION_FAILURE
  - ENVIRONMENT_CONFIGURATION_ERROR
  Exit behavior must remain deterministic and consistent with these categories.
- **HR-5 — Deterministic Offline Default Acceptance Gate (APPROVED)**: The default Stage-10 acceptance gate is deterministic and offline with respect to external model/service inference. For a path whose production implementation normally requires OCR/LLM/network inference, Stage-10 default conformance/regression MUST use an already-frozen deterministic intermediate/golden or an existing deterministic test adapter, while still verifying downstream contract behavior and canonical immutability. Any live external OCR/LLM/provider execution is an explicitly opt-in integration check and is NOT required for the reproducible Stage-10 acceptance gate, unless an existing FROZEN authority explicitly mandates live execution. If such a contrary authority exists, stop and report the exact authority rather than overriding it.
