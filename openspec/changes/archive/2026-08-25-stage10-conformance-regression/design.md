# Technical Design: Stage 10 — Conformance and Regression

## 1. Conformance Matrix

This matrix maps each Stage 1–9 spec requirement to executable checks in Stage 10:

| ID | Stage / Spec | Requirement | Executable Check |
|---|---|---|---|
| CM-01 | Ingress | Secure ZIP preflight validation | Synthetic test verifies encrypted/malformed/invalid files are blocked |
| CM-02 | Ingress | Official SHA matches exact accepted bytes | Check preserved file hash against receiver log and original SHA |
| CM-03 | Conversion | One page record per physical page | Check generated markdown has exactly `1..N` page markers |
| CM-04 | Conversion | Canonical page markers `[[Pág. N]]` | Regex checks on page marker syntactic structure and method comment |
| CM-05 | Conversion | OCR routing configuration limits | Verify OCR fallback triggers correctly on configured thresholds |
| CM-06 | Quality Gate | Expose PASS, PASS_WITH_WARNINGS, FAIL | Assert Quality Gate outputs strictly use this vocabulary |
| CM-07 | Quality Gate | FAIL cannot enter Producer | Assert that a FAIL state throws an exception when passing to any Producer |
| CM-08 | Router | Route only after Quality Gate | Verify that Domain Router refuses unvalidated Quality Gate states |
| CM-09 | Producer | Preserve field ownership and metadata | Assert that Producer updates metadata but never overwrites locked fields |
| CM-10 | Isolation | Process storage separate from Legal | Assert running Process flow never writes to `repo_jur/bundle/` |
| CM-11 | Isolation | Legal index excludes Process storage | Assert retrieval sync/rebuild ignores all Process files |
| CM-12 | Retrieval | Retrieval remains Zero-Write over bundle | Assert sync, rebuild, and search make absolutely no writes to `bundle/` |
| CM-13 | Retrieval | No Stable IDs introduced | Confirm `concept_id` positional identity; no stable chunk/item IDs |
| CM-14 | Retrieval | Canonical materialization against current bundle | Verify stale index candidates are rejected; raw content is retrieved from current bundle |
| CM-15 | Coupling | Domain-schema independence | Source-inspection checks that common contracts do not import domain schemas |

## 2. Regression Corpus / Fixture Strategy

The verification strategy is split into two distinct boundaries:

### 2.1 Synthetic Fixture Boundary (Fast Conformance)
- **Goal**: Fast, deterministic, isolated execution of all design contract constraints.
- **Implementation**: Hand-crafted, lightweight PDF files and synthetic ZIP packages that represent edge cases (e.g., malformed actors, absolute paths, traversal paths, special ZIP members, empty streams).
- **Location**: Generated programmatically at test runtime using `pytest` fixtures, or stored under `tests/test_conformance/fixtures/`.

### 2.2 Real-Corpus Fixture Boundary (Regression Testing)
- **Goal**: Full-fidelity validation of the conversion pipeline over the canonical real-corpus PDFs without external dependencies.
- **Implementation**: Executes the full conversion, cleaning, and validation pipeline on the four frozen PDF files:
  1. `AINTARESP_1462304-PA.pdf` (STJ judgment, native text, legal headers, paragraph order).
  2. `REsp_1704551-SP.pdf` (STJ judgment, native tables, repetitive counters, signature blocks).
  3. `Inf0024E.pdf` (Informativo de Jurisprudência, editorial layout, cover separation, repetitive footers).
  4. `L10.406_CC_2002.pdf` (Código Civil, large legislative file, index sections, paragraph recomposition).
- **Verification**: Lightweight golden expected artifacts are Git-tracked under `tests/test_conformance/golden/`. Heavy source PDFs remain gitignored/local. Goldens may be deterministic text/JSON or SHA-256 expectations as appropriate, but must remain reviewable and version-controlled.
- **Model / OCR Nondeterminism Mitigation**: A reproducible Stage-10 gate MUST NOT depend on live nondeterministic external OCR/LLM output. Whitespace normalization alone is not an acceptable mitigation for model nondeterminism. The default Stage-10 acceptance gate is completely deterministic and offline with respect to external model/service inference. For a path whose production implementation normally requires OCR/LLM/network inference, Stage-10 default conformance/regression MUST use an already-frozen deterministic intermediate/golden or an existing deterministic test adapter, while still verifying downstream contract behavior and canonical immutability. Any live external OCR/LLM/provider execution is an explicitly opt-in integration check and is NOT required for the reproducible Stage-10 acceptance gate, unless an existing FROZEN authority explicitly mandates live execution.

## 3. Dual-Pipeline Bounded-Context Architecture

The repository enforces complete separation of the two primary workflows:

```text
=============================================================================
1. LEGAL KNOWLEDGE FLOW (Strictly isolated to /bundle/)
ITP ZIP -> Preflight -> SHA -> Preservation -> Conversion -> Quality Gate ->
Domain Router (legal_knowledge) -> Semantic Review -> Legal Producer -> /bundle/
=============================================================================
2. JUDICIAL PROCESS FLOW (Strictly isolated to process-storage)
ITP ZIP -> Preflight -> SHA -> Preservation -> Conversion -> Quality Gate ->
Domain Router (judicial_process) -> Semantic Review -> Process Producer -> var/process/
=============================================================================
```

- **MANDATORY BOUNDED-CONTEXT BOUNDS**: "Dual-bounded-context end-to-end" MUST NOT imply Judicial Process Retrieval. Legal Knowledge conformance may run through Legal Knowledge Retrieval, but Judicial Process conformance ends at the authorized Judicial Process producer/canonical process-storage boundary. Judicial Process Retrieval remains explicitly OUT OF SCOPE and requires its separate future contract.
- **Domain Router**: Sole gateway routing items. It uses `RouteTarget` classification and passes the intermediate artifacts to domain-specific Semantic Reviews and Producers.
- **Storage Isolation**: Legal Producer writes strictly under `/bundle/`. Process Producer writes strictly under a configured directory (e.g. `var/process/` or `/process-storage/`) that is completely outside the Legal bundle root.
- **Retrieval Separation**: Legal Retrieval queries `index.db` (containing data parsed exclusively from `/bundle/`) and materializes candidates directly from `/bundle/`. It remains completely unaware of any Process files.

## 4. CLI End-to-End Command Specification

The operational local command is registered on the `repo-jur` entrypoint:

```bash
repo-jur test conformance [--json-report <path>] [--verbose]
```

### 4.1 CLI Behavior and Design Decisions
- **Decision 1: Integration with `repo-jur`**: Add a new parser for the `test` subcommand and a `conformance` action under `pipeline_juridico.domain_router_cli`.
- **Decision 2: Subprocess Execution**: Under the hood, the conformance runner in `repo-jur test conformance` MUST NOT invoke a bare `pytest` executable from PATH. It MUST invoke pytest through the active Python interpreter using `sys.executable -m pytest`. It executes two explicit bounded executions over `tests/test_conformance/`:
  1. `sys.executable -m pytest -m conformance tests/test_conformance/`
  2. `sys.executable -m pytest -m regression tests/test_conformance/`
  This ensures we reuse the entire pytest assertions matrix and test report output under a strictly consistent execution contract.
- **Decision 3: Exit Codes**:
  - `0`: Conformance and regression validation passed successfully.
  - `1`: Test execution failed or a regression/conformance violation was found.
  - `2`: Configuration or workspace error (such as missing virtualenv, missing pytest, or missing PDF fixtures) — corresponding to `ENVIRONMENT_CONFIGURATION_ERROR`.
- **Decision 4: JSON Report Output**: Every `repo-jur test conformance` execution produces a structured derived report by default at `var/conformance/report.json`. `--json-report <path>` overrides the report destination. The report is derived/non-canonical, must never be written inside bundle/ or canonical process storage, and must distinguish at minimum:
  - `CONFORMANCE_FAILURE`
  - `REGRESSION_FAILURE`
  - `ENVIRONMENT_CONFIGURATION_ERROR`
  Exit behavior remains completely deterministic and consistent with these categories.

## 5. Source-Inspection and Invariant Checks

Stage 10 introduces automated static-analysis checks on the codebase layout:
- **Prohibited Imports Check**: Scans `src/pipeline_juridico/contracts.py` and asserts it never imports from `src/pipeline_juridico/retrieval/`, `src/pipeline_juridico/legal_producer.py`, `src/pipeline_juridico/process_producer.py`, or any domain-specific schemas.
- **No Stable Chunk/Item IDs Check**: Scans retrieval files and verifies that chunk and item identification relies entirely on deterministic, positional `concept_id` + offset/ordinals.
- **No Embeddings/Vector Libraries Check**: Scans the virtual environment imports/dependencies and asserts no vector/embeddings/semantic-reranking packages are added.

## 6. Expected Failure Categories and Diagnostics

The test framework categorizes failures to enable fast resolution:

- `CONFORMANCE_FAILURE: BUNDLE_CONTAMINATION`: A component (like Process pipeline) attempted to write inside `/bundle/`.
- `CONFORMANCE_FAILURE: CONTRACT_VIOLATION`: An invalid Actor reference or an absolute path was accepted, or a FAIL quality-gate state was processed by a Producer.
- `REGRESSION_FAILURE: CITATION_MODIFICATION`: Cleaned output altered legal citation tokens (e.g., Article numbers).
- `REGRESSION_FAILURE: READING_ORDER_FLIP`: Reading order in multi-column PDF or heading unification was altered.
- `ENVIRONMENT_CONFIGURATION_ERROR: CONFIG_OR_WORKSPACE_FAULT`: Early failure because required PDF files under `input/` are absent, pytest is not installed, or the environment configuration is invalid.
