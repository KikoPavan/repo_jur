## Context

Stage 6 (Domain Router) is closed and archived; its living spec (`openspec/specs/domain-router/spec.md`) and implementation (`src/pipeline_juridico/domain_router.py`, `domain_router_cli.py`) deterministically emit exactly one of `legal_knowledge`, `judicial_process`, `review_required` from conformant Phase 1 artifacts (recorded gate `PASS`/`PASS_WITH_WARNINGS`, critical status `OK`/`WARNING`, and the approved `requested_domain` signal). Stage 7 (Legal Knowledge) is closed and archived; its living spec (`openspec/specs/legal-knowledge/spec.md`) and implementation (`src/pipeline_juridico/legal_semantic_review.py`, `legal_producer.py`, `legal_producer_cli.py`) implement the `legal_knowledge` branch end to end. The FROZEN corpus then requires the `judicial_process` branch to be implemented as the Judicial Process Pipeline: Process Semantic Review / Enrichment → Process Producer → process-domain storage (`implementation-plan-repo-jur-v1.1-FROZEN.md` §10; `technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §3.4/§3.5/§17/§18; `arquitetura-fase2-repo-jur-v15-FROZEN.md` §1.3/§1.4/§2.1A/§8.11/§11; `decision-memo-semantic-review-enrichment-layer-v1.1-FROZEN.md`; `decision-memo-retrieval-bounded-context-scope-v1.0-FROZEN.md`).

Current repository facts (verified 2026-08-22 on this worktree):

- `Phase1Artifacts`, `RouteTarget` (including `JUDICIAL_PROCESS = "judicial_process"`), `CriticalValidationStatus`, `GateState`, `Actor`, `guard_legal_bundle_write` live in `src/pipeline_juridico/contracts.py`; `RoutingDecision`/`RoutingReasonCode` live in `src/pipeline_juridico/domain_router.py`. The Legal guard denies any acting domain other than `legal_knowledge` when the target resolves inside `bundle/` — this is the bundle-boundary enforcement Stage 8 relies on (process writes to `bundle/` are already denied by existing FROZEN contract, no modification needed).
- `config.py::ensure_outside_canonical_bundle(path)` rejects paths inside `bundle/` for operational directories; `validator.py::write_atomic` provides temp-file + fsync + rename publication; `hashing.py` provides `sha256_bytes`/`sha256_file`; `report.py::validate_report_contract` validates the Phase 1 report surface.
- The Phase 1 technical report carries `schema_version`, `execution_id`, `input.{sha256,byte_size,page_count}`, `phase1.{implementation,implementation_version,logical_processing_version,relevant_config_fingerprint}`, `result.{quality_gate,warnings,errors}`, `artifacts.markdown_sha256`, `pages[]`, `telemetry`. It does NOT carry the preserved-evidence resource URI and does NOT carry the Critical-Data Validation status (Stage 8 inherits the Stage 6/7 input shape — the boundary is reached only after the router emitted `judicial_process`).
- The Stage 7 Legal pipeline is the physical precedent for every Stage 8 module: engine seam + `ReviewState`/patch model + provenance-versioned rule registry (`legal_semantic_review.py`); validated producer context, concept candidate render (deterministic YAML subset), `DuplicateResolution` state machine, materiality classification, lifecycle merge, guarded atomic publication (`legal_producer.py`); `repo-jur producer build|validate|publish` CLI registered additively on the `repo-jur` entry (`legal_producer_cli.py` + `domain_router_cli.py`).
- No Process Semantic Review, no process schema/profile, no process-domain storage root, no Process Producer, no process write guard, no `bundle/` directory exist (all verified). The `judicial_process` route value is consumed only by the router and its tests.
- FROZEN gap (verified): no baseline defines the process field inventory, process type vocabulary, enrichment schema, ownership rules, or storage location/format. `legal-okf-profile-v1.3` is explicitly Legal-only; `lifecycle-field-ownership-v1.4`, `decision-memo-duplicate-act-handling-v1.0`, and `decision-memo-verification-history-schema-v1.0` are scoped to `/bundle/` concepts. The corpus defers process governance ("domain-specific, governed separately", "quando definidas") — an absence of authority, not a contradiction (planning backlog `docs/planning/MASTER_IMPLEMENTATION_BACKLOG_stages_6_10.md` §M.1, §M.3).
- The judicial-process document scope is corroborated by the archived diagnostic `audit-judicial-process-pdf-support` (2026-08-12): a 1st-instance court corpus (`input/processos_auditoria/` — Petição Inicial, CONTESTAÇÃO ao Cumprimento de Testamento, DECISÃO, Testamento Publico) with 29/33 pages native text converting integrally and 4 scanned pages blocked under `--no-ocr`, matching the impl plan §10 scope list (petições, contestações, decisões, procurações, testamentos, anexos, demais peças).
- Existing CLI conventions (`tests/test_cli.py`, `tests/test_domain_router_cli.py`, `tests/test_legal_producer_cli.py`): argparse, environment-driven directories, deterministic exit codes (0 success, 1 input, 2 unexpected, 3 config/contract, 4 output conflict, 5 blocked), sanitized logging, atomic writes.
- Test baseline on this worktree (with the gitignored `input/*.pdf` corpus fixtures symlinked from the primary tree, not staged): **808 passed**. `openspec validate --all --strict`: **8 passed, 0 failed**.
- Console scripts today: `converter-juridico = pipeline_juridico.cli:main`, `repo-jur = pipeline_juridico.domain_router_cli:main` (`pyproject.toml`). Runtime: Python ≥3.12, `uv`, `src/` layout.

## Repository Implementation Map (Stage 0 / physical-layout memo)

| Logical capability | Physical implementation found | Decision | Tests covering it | Migration |
| --- | --- | --- | --- | --- |
| Shared contracts (`Phase1Artifacts`, `RouteTarget`, `CriticalValidationStatus`, `GateState`, `Actor`, `guard_legal_bundle_write`) | `src/pipeline_juridico/contracts.py` | **REUSE** as-is; no modification | `tests/test_contracts.py` | none |
| Routing decision (`RoutingDecision`, `RoutingReasonCode`) | `src/pipeline_juridico/domain_router.py` | **REUSE** as-is; consumed, never re-derived | `tests/test_domain_router.py` | none |
| Bundle-boundary enforcement for operational paths | `config.py::ensure_outside_canonical_bundle` | **REUSE** as-is | `tests/test_config.py` | none |
| Atomic file publication | `validator.py::write_atomic` | **REUSE** as-is | `tests/test_validator.py` | none |
| SHA-256 utilities | `hashing.py` | **REUSE** as-is | `tests/test_hashing.py` | none |
| Phase 1 artifacts boundary + recorded gate outcome | `conversion_engine.py` / `report.py` | **REUSE** read-only; Producer re-reads gate outcome from the report | existing Stage 3/5 tests | none |
| Process Semantic Review / Enrichment | none — no process review component exists | **CREATE** `src/pipeline_juridico/process_semantic_review.py` (new module, mirroring the Stage 7 physical precedent; physical-layout memo: create only when no suitable implementation exists) | new `tests/test_process_semantic_review.py` | none |
| Process schema/profile | none — no FROZEN authority defines it | **CREATE** `src/pipeline_juridico/process_storage.py` (profile vocabulary, path resolution, write guard) per the approved HR-3/HR-4/HR-5 decisions (recorded 2026-08-23) | new `tests/test_process_storage.py` | none |
| Process-domain storage + write guard | none — no process storage root exists | **CREATE** `process/` canonical root at repo top level (HR-4) created on first guarded publication; dedicated process write guard defined by Stage 8 (only `judicial_process` writes process storage; process→`bundle/` denied by the existing Legal guard, which remains unchanged and Legal-specific) | new `tests/test_process_storage.py` | none |
| Process Producer (identity/provenance, ownership merge, render, validate, publish) | none — no Process Producer exists | **CREATE** `src/pipeline_juridico/process_producer.py` | new `tests/test_process_producer.py` | none |
| Process operational CLI | none — `repo-jur` has `route` and Legal `producer` only | **CREATE** `src/pipeline_juridico/process_producer_cli.py`; add `process` subcommand group to the existing `repo-jur` entry point (do not modify `cli.py`, do not touch `route` or `producer`) | new `tests/test_process_producer_cli.py` | none |

## Goals / Non-Goals

**Goals:**

- implement the `judicial_process` branch end to end: Process Semantic Review seam → approved process schema/profile + process-domain storage boundary → Process Producer → process-domain storage, consuming only conformant Phase 1 artifacts (gate `PASS`/`PASS_WITH_WARNINGS`, route `judicial_process`) read-only;
- consume the existing Stage 6 `RoutingDecision` (target exactly `judicial_process`) and never re-derive the route from document content; leave Domain Router semantics untouched;
- keep Phase 1 artifacts byte-identical across the whole Stage 8 (Semantic Review never overwrites; Producer never rewrites the body beyond FROZEN-allowed structural patches with full provenance);
- make Process Semantic Review domain-isolated, engine-neutral, deterministic-first (rule-registry-backed), with structured patches (`before`/`after`/`reason`/`confidence`/`page_refs`/`evidence_refs`), REVIEW_REQUIRED on ambiguity, and zero publication authority;
- make the Process Producer the single canonical publisher into process-domain storage through the process write guard, applying the conservative lifecycle/ownership/duplicate disciplines, PDF cardinality, positional concept identity, profile validation, and atomic publication with Git-diff exposure — never writing `bundle/`;
- add the minimal `repo-jur process build|validate|publish` CLI surface with deterministic exit codes and CLI non-regression (existing `converter-juridico`, `repo-jur route`, and `repo-jur producer` untouched);
- prove the boundary invariants with executable tests: input gating, routing-decision consumption, Phase 1 immutability (SHA-256), word preservation on structural patches, REVIEW_REQUIRED on ambiguity, no LLM/silent classification, no Legal coupling (source-inspection), guard-only publication, bundle-denial for the process domain, no automatic `verified`/`status`/`_v2`, deterministic idempotent regeneration, no retrieval behavior, CLI non-regression, observability outside bundle and process storage.

**Non-Goals:**

- Stage 9 (Legal Knowledge Retrieval) and all retrieval/chunking/reranking/search, including any Judicial Process Retrieval (explicitly requires a separate future contract — `decision-memo-retrieval-bounded-context-scope-v1.0-FROZEN.md`);
- Stage 10 (Conformance/Regression);
- modifying Domain Router semantics, `router.py` page routing, the converter, OCR provider, thresholds, cleaner, validator, report generation, Stages 2–6 code, `contracts.py`, `config.py`, any FROZEN authority, or the closed Stage 7 Legal Knowledge pipeline;
- selecting an LLM/semantic model, prompt, or provider for the review engine (design doc §20.5) — the seam stays neutral and the deterministic path is default (HR-2);
- deriving the process `type` from document content or from collector hints (HR-3);
- reusing the Legal OKF Profile, Legal type vocabulary, Legal schema, or Legal enrichment schema for process documents;
- writing process artifacts into `repo_jur/bundle/` or creating any shared Legal/Process index;
- automatic consolidation of physically distinct PDFs into one process concept without safe logical/material equivalence;
- automatic `verified`, `status` mutation, `_v2`/UUID/stable-id creation;
- writing `bundle/` or process-domain storage outside the Producer, or writing derived/runtime data into process-domain storage;
- adding or changing dependencies;
- creating a new FROZEN memo inside this change (proposed as a possible later human decision, HR-4/HR-5 note).

## Decisions

### 1. One OpenSpec change for Stage 8, with C8.1/C8.2/C8.3 as dependent task groups

`stage8-judicial-process` is a single OpenSpec change whose `tasks.md` splits into three dependency-ordered groups: **C8.1 — Process Semantic Review seam** (module, patch model, rule registry, deterministic-first engine, REVIEW_REQUIRED semantics, domain isolation), **C8.2 — process schema/profile + storage boundary** (approved type vocabulary, process frontmatter profile, process-domain storage root, process write guard), and **C8.3 — Process Producer core + storage adapter + operational CLI + observability** (`repo-jur process build|validate|publish`, state records). C8.2 depends on the HR-3/HR-4/HR-5/HR-6 approvals (recorded 2026-08-23); C8.3 depends on C8.1 (Producer consumes the ReviewResult) and C8.2 (Producer writes through the approved storage contract).

**Rationale:** identical to Stage 6 Decision 1 and Stage 7 Decision 1: all three slices are governed by the same FROZEN authorities (tech spec §3.4 lists `process semantic review`, `process schemas`, `process producer` as the three logical sub-capabilities of the single Judicial Process Context; impl plan §10 covers Stage 8 as one stage) and by one capability spec (`judicial-process`); splitting into multiple changes would double-sync the same spec at archive time or create thin capabilities. The pre-Stage-7 planning backlog proposed three separate changes (C8.1/C8.2/C8.3, `docs/planning/MASTER_IMPLEMENTATION_BACKLOG_stages_6_10.md` §E); the implemented Stage 6/7 pattern (one change per stage with C6.x/C7.x task groups) supersedes that granularity for the same evidence — the C8.x numbering is preserved as task groups inside the single change.

### 2. New flat modules `process_semantic_review.py`, `process_storage.py`, `process_producer.py`, `process_producer_cli.py`; reuse every existing contract; never touch Stages 2–7 modules

Physical-layout memo and impl plan §0/§13 mandate REUSE → ADAPT IN PLACE → TEST and forbid parallel trees. No existing implementation satisfies the process capabilities (verified), so new modules under the confirmed physical root `src/pipeline_juridico/` are authorized. The modules are **flat**, mirroring the implemented Stage 7 precedent (`legal_semantic_review.py`, `legal_producer.py`, `legal_producer_cli.py`), rather than a `process/` subpackage (the pre-Stage-7 planning backlog proposed `src/pipeline_juridico/process/`; the implemented Stage 7 chose flat modules, and domain isolation is enforced by source-inspection tests and module boundaries, not by a subdirectory). `contracts.py`, `config.py`, `validator.py`, `hashing.py`, `report.py`, `domain_router.py`, `domain_router_cli.py` are used read-only or as-is, never modified — the sole permitted touch on an existing module is the additive registration of the `process` subcommand group on the `repo-jur` entry point (Decision 10), with no existing behavior, flag, or surface changed.

**Rationale:** the confirmed physical root is `src/pipeline_juridico/` (arquitetura §2.1, impl plan §0); the physical-layout memo authorizes CREATE when no suitable implementation exists; the Stage 7 flat-module precedent is the freshest physical evidence in the repository.

**Alternative considered:** a `src/pipeline_juridico/process/` subpackage. **Rejected because:** it adds a parallel tree for naming symmetry only, which arquitetura §2.1 explicitly prohibits ("criar uma árvore paralela apenas para coincidir com o desenho arquitetural"); the implemented Stage 7 flat precedent is authoritative physical evidence.

### 3. Stage 8 input contract: conformant Phase 1 artifacts + recorded gate + consumed routing decision; never re-derive

The Stage 8 boundary (review seam and Producer) accepts the Stage 3 `Phase1Artifacts` (`markdown: str`, `report_json: str`) strictly read-only, re-reads the recorded Quality Gate outcome from the report's `result.quality_gate` (structural enforcement: only gate-`PASS`/`PASS_WITH_WARNINGS` content enters; phase1-op-spec §14; domain-router spec), and consumes the Stage 6 `RoutingDecision` requiring its target to be exactly `RouteTarget.JUDICIAL_PROCESS`. A `legal_knowledge` or `review_required` decision is a dedicated configuration error (Stage 8 never silently re-routes), and an absent decision stops the run. The route is never derived from the Markdown body, the report content, or collector hints; the router semantics are never re-executed or modified.

**Rationale:** mirrors Stage 6 Decision 3 and Stage 7 Decision 3 — reading the recorded gate from the report makes the post-gate invariant structural, and consuming the routing decision as the Stage 6 output (rather than re-deriving it) is the explicit task invariant "Consume the existing Stage-6 RoutingDecision; never re-derive the route from document content".

### 4. Process Semantic Review: deterministic-first, engine-neutral seam; AI/LLM engine deferred (HR-1, HR-2)

`src/pipeline_juridico/process_semantic_review.py` exposes an engine-neutral seam following tech spec §3.5, with the same result shape the FROZEN semantic-review memo defines:

```python
class ProcessSemanticReviewEngine:
    def review(self, phase1_artifacts, profile) -> ProcessReviewResult:
        ...
```

`ProcessReviewResult` carries: structured patches (`ProcessPatch(before, after, reason, confidence, page_refs, evidence_refs)`), extracted fields, classification suggestions (non-authoritative), warnings, and a review state exactly one of `OK`/`WARNING`/`REVIEW_REQUIRED`. The default engine is **deterministic**: a versioned, registry-backed rule set (mirroring Stage 4 `CriticalValidationRule` and Stage 7 `LegalReviewRule` provenance: rule id/version/scope/spec source/validation-logic version) that only performs structural corrections preserving every original word (automatic word-multiset validation; no summary/paraphrase/translation/invention/inference). Ambiguity → `REVIEW_REQUIRED` (never silent application). No LLM call, no model/provider/prompt selection, no content classification authority in v1 (HR-1/HR-2); the engine interface is the future LLM insertion point and a source-inspection test asserts the process review module contains no LLM/semantic-client reference and no Legal Knowledge module reference.

**Rationale:** the FROZEN memo authorizes the layer and its invariants for every bounded context; the design doc §20.5 explicitly defers model/prompt/provider choice; the corpus discipline (LOOPS.md, critical-data provenance rule) forbids inventing rules without versioned normative evidence; the approved Stage 7 HR-1/HR-2 set the exact precedent.

**Alternative considered:** shipping an LLM-backed engine behind the seam in v1, or importing the Stage 7 `LegalSemanticReviewEngine`/`LegalPatch` types directly. **Rejected because:** design doc §20.5 places model/prompt/provider choice out of scope; silent LLM classification is prohibited; importing Legal review types would couple the process domain to the Legal domain, violating the isolation invariant (shared-conversion-core memo *Prohibited Coupling*) — the process review defines its own domain-named types with the same FROZEN shape.

### 5. Process `type` is explicit operator intent in a validated producer context; approved vocabulary from the FROZEN scope (HR-3)

No FROZEN baseline defines how a `judicial_process`-routed artifact is typed, and Stage 6 denied content-derived routing signals. This change defines the deterministic source: the validated **process producer context** carries the single authoritative `type` signal, supplied explicitly by the operator via `--type`, with the approved vocabulary (HR-3, recorded 2026-08-23) grounded in the FROZEN Stage 8 scope (impl plan §10 lists petições, contestações, decisões, procurações, testamentos, anexos, demais peças):

```text
Peticao | Contestacao | Decisao | Procuracao | Testamento | Anexo | OutraPeca
```

(approved serialized values — HR-3). The Semantic Review layer MAY emit a classification *suggestion* (non-authoritative); a suggestion conflicting with the explicit `type` routes the Producer run to `REVIEW_REQUIRED`. A producer context with an invalid or missing `type` is a dedicated configuration error (never a silent default, never a content-derived guess).

**Rationale:** consistent with the approved Stage 6 pattern (explicit workflow intent as the deterministic signal; `legal_hints`-derived inference denied) and the approved Stage 7 HR-3 (explicit-operator-intent `type` for Legal concepts). The vocabulary is grounded in the FROZEN Stage 8 scope, not invented from document observation.

**Alternative considered:** deriving `type` deterministically from report metadata or from the audit corpus filenames (Petição Inicial, CONTESTAÇÃO, DECISÃO, Testamento Publico). **Rejected because:** no FROZEN baseline authorizes such a rule; it would reintroduce content-derived classification by another name; the HR-3 decision is required precisely because the vocabulary itself is not normative.

### 6. Process-domain storage contract: canonical root, positional paths, atomic publication, dedicated process write guard (HR-4)

The process-domain canonical storage root is approved (HR-4) at the repository top level, outside `repo_jur/bundle/` and outside `var/`:

```text
<repo>/process/
  <type_dir>/
    <slug>.md          # process concept document
    index.md           # optional reserved navigation file (mirrors bundle reserved files)
    log.md             # optional reserved modification log
```

- **Location/format:** `process/` at the repo root is the canonical **Git-tracked** process-domain storage (HR-4) — process storage is canonical/domain storage per arquitetura §11.50, not derived data — never inside `bundle/`, never under `var/` (operational). The type subdirectories are created only by Process Producer publication.
- **Positional identity:** concept path = `process/<type_dir>/<slug>.md` where the slug derives deterministically from the evidence basename or the provenance hash — never from body content (positional identity only; no stable-id/UUID, HR-5 discipline).
- **Write guard:** a **dedicated process write guard defined by Stage 8** authorizes a target only when (a) the acting domain is `judicial_process` and (b) the resolved target lies under the process root. Only `judicial_process` may write process storage; no alternate publication path exists. Any process-domain write targeting `repo_jur/bundle/` is denied — enforced by the existing `guard_legal_bundle_write` semantics (acting domain ≠ `legal_knowledge` targeting bundle → `PermissionError`), which remains unchanged and Legal-specific and which Stage 8 relies on without modification.
- **Atomicity:** publication validates first, then writes a temp file on the same filesystem, flushes/fsyncs, and atomically renames (`validator.py::write_atomic`), with Git-diff exposure and no automatic commit/push.
- **Storage decision provenance:** this contract is the resolution of the mandatory human decision M.1 of the planning backlog. The alternative of `var/process/` (operational, gitignored) is rejected because process storage is canonical/domain storage, not derived/runtime data; the alternative of deferring storage entirely is rejected because the impl plan §10 flow ends at process-domain storage and Stage 8's objective includes the storage boundary.

### 7. Process frontmatter profile: OKF v0.2 base rules + process profile, never the Legal profile (HR-5)

Process concept candidates follow the OKF v0.2 base concept rules (frontmatter `---` block, `type` first, `title`/`sources`/`generated`/`verified`/`status` semantics as generic OKF) with a process-specific profile — never the Legal OKF Profile (`legal-okf-profile-v1.3` is Legal-only; impl plan §10 prohibits using the Legal OKF schema as the process schema). Concretely:

- `type` = one of the approved process vocabulary (HR-3), first key.
- `generated.by` = `repo_jur_process_producer/<version>` (the Actor producer form `<producer>/<version>`; `generated.at` updates only on meaningful change).
- `sources` present when identifiable; PDF cardinality fields `repo_jur_pdf_hash` (1 PDF) / `repo_jur_pdf_hashes` (2+ PDFs, mapping `sources[].id` → SHA-256) mutually exclusive, plus `repo_jur_evidence_sha256` and `repo_jur_phase1` provenance (mirroring the Stage 7 Producer render, which uses the same domain-neutral provenance fields).
- `status` Human-Owned: never inserted or mutated by the Producer; absence = OKF `stable` semantics.
- `verified` only for real verification events; never fabricated; verification history preserved/archived per the conservative policy.
- No `_v2`, no UUID, no stable-id, no Legal profile field, no Legal type value.
- The body preserves the Phase 1 literal content including `[[Pág. N]]` markers.

**Rationale:** OKF v0.2 is the engine-neutral base (arquitetura §3); the Legal profile is explicitly Legal-only; the isolation invariant (shared-conversion-core memo) requires process-owned schemas. Reusing OKF base rules avoids inventing a parallel document format while keeping full domain separation.

**Alternative considered:** a fully custom process schema with no OKF base rules. **Rejected because:** OKF v0.2 base rules are generic and already project-endorsed (arquitetura §3); a fully custom format would add a second document convention with no FROZEN mandate and no benefit. The choice was submitted for approval (HR-5) because no FROZEN authority extends OKF to process storage; approved 2026-08-23.

### 8. Lifecycle/ownership/duplicate/verification rules stated explicitly and self-sufficiently for process storage (HR-6)

The process-domain lifecycle, ownership, duplicate and verification requirements are stated explicitly and self-sufficiently as normative requirements in the `judicial-process` capability spec (HR-6 normative correction). The Legal-bundle-scoped memos (`lifecycle-field-ownership-v1.4` §4, `decision-memo-duplicate-act-handling-v1.0`, `decision-memo-verification-history-schema-v1.0`) do NOT become normative authorities for Judicial Process by analogy; Stage 8 reuses only the conservative *mechanics* proven in Stage 7. Concretely, the Producer loads the existing concept first, resolves identity/provenance, detects technical vs material change, recomputes Producer-Owned fields deterministically, preserves Human-Owned fields and human-curated Shared values, applies the `verified`/history policy (never auto-create; archive only real prior events on material change preserving `by`/`at` and recording `invalidated_by`; omit when no active events remain), applies body ownership (PDF-derived body = Producer-Owned literal with `[[Pág. N]]` markers), validates, and publishes atomically. Duplicate resolution implements the conservative state machine: same physical evidence + equivalent canonical inputs/config/logical version + no meaningful change → NO-OP; meaningful change → controlled update; distinct/autonomous document → distinct concept; material change or ambiguity → HUMAN REVIEW (no write). SHA-256 is physical evidence identity only. No content-based safe-equivalence in v1.

**Rationale:** per the approved HR-6 correction, the judicial-process OpenSpec itself must state the process-domain lifecycle, ownership, duplicate and verification requirements explicitly and self-sufficiently; the Legal-scoped FROZEN memos do not become normative authorities for process storage by analogy. Reusing the Stage 7-proven conservative mechanics (preserve human curation, never fabricate verification, never auto-version, write-block on ambiguity/material uncertainty) is the minimal-risk choice and is exactly what the master backlog §M.1 option 2 delegates to the OpenSpec design with human review at the gate (HR-6). A future process-specific duplicate memo may refine the state machine; it is deferred and does not block v1.

### 9. `sources[].resource` for PDF-derived process concepts comes from the validated producer context, matched against the report hash (HR-7)

Identical to the approved Stage 7 HR-4 decision: the Phase 1 report does not carry the resource URI, so the Process Producer receives the preserved-evidence reference through the validated producer context (`--evidence-resource <uri>`), validates it as a resolvable reference, cross-checks the report's `input.sha256` when the reference is resolvable to bytes, and raises the dedicated configuration error when a PDF-derived concept has no supplied reference (never an invented resource, never silent omission of provenance).

**Rationale:** mirrors the approved Stage 7 HR-4; the report→ingress-state join key is not FROZEN-defined, and the explicit producer-context reference is the minimal, auditable choice.

### 10. Operational CLI: `repo-jur process build|validate|publish`; single write path; non-regression (HR-8)

New console-script wiring mirrors the Stage 7 `producer` registration: `src/pipeline_juridico/process_producer_cli.py` registers a `process` subcommand group on the existing `repo-jur` entry point (`domain_router_cli.py::_build_parser`), dispatched alongside `route` and `producer`; `converter-juridico`, `repo-jur route`, and `repo-jur producer` surfaces remain byte-identical (non-regression proven by the existing CLI suites).

```text
repo-jur process build <markdown.md> <report.json> --type <Tipo> [--evidence-resource <uri>] [--context <process-context.json>] [--process-root <dir>] [--state-dir <dir>] [--log-level <level>] [--json]
repo-jur process validate <concept-candidate.md> [--process-root <dir>] [--log-level <level>] [--json]
repo-jur process publish <concept-candidate.md> [--overwrite] [--process-root <dir>] [--state-dir <dir>] [--log-level <level>] [--json]
```

Semantics: `build` runs the Process Semantic Review seam + Producer render, produces a process concept candidate on stdout or a state file, and writes a review/observability record — **never writes to process-domain storage or `bundle/`**; `validate` validates a candidate against profile + cardinality + ownership without writing; `publish` is the single write path, re-validating, then publishing atomically through the process write guard (acting domain `judicial_process`) into the process root, writing the Producer observability record under a configurable state dir (default `var/process/state/`), outside the bundle and outside process storage. Exit codes extend the existing convention: 0 success; 1 input; 2 unexpected; 3 configuration/contract (invalid `--type`, missing evidence resource for PDF-derived, guard denial misconfigured, unreadable context/report); 5 blocked (gate `FAIL`, non-process routing decision, `REVIEW_REQUIRED`, HUMAN REVIEW required — no write, no publish record). `publish` never performs Git commit/push/merge (HR-8). The process CLI is a distinct surface from the Legal `producer` group (no flag/semantic collision).

### 11. Process Producer observability record: shape and location

One JSON record per Producer run (build and publish), written under a configurable operational directory (default `var/process/state/`), enforced outside the canonical bundle via `config.py::ensure_outside_canonical_bundle` AND outside process-domain storage (new check). Fields (behavioral, per tech spec §15.1): schema version, record type (`process.build` / `process.publish` / `process.review_required`), evidence provenance hash (`input.sha256`), recorded gate outcome, routing decision, review summary (patch count, REVIEW_REQUIRED flag — never patch content), resolution outcome (`new_concept`/`noop`/`regenerate`/`human_review_required`), materiality category when applicable, `verified` action (`preserved`/`none`/`archived`), publication result (`published`/`blocked`/`noop`), `generated.at` action, and the concept path. MUST NOT include: document content, full critical identifier values (process numbers, names, CPF/RG, selos), secrets/tokens/credentials, or patch bodies. Determinism: the concept render is a pure function of the artifacts + context; the record may carry operational metadata (timestamps) as observability.

### 12. Stage boundaries: no retrieval, no shared index, no later-stage behavior; source-inspection enforced

Every Stage 8 module carries source-inspection tests asserting: no retrieval index creation, no shared Legal/Process index, no chunking/reranking/search path, no process-storage write outside the guarded publish path, no `bundle/` write, no Legal module/schema/profile import, no LLM/semantic-model client, no converter/engines/inspector/OCR/evidence module import beyond validation utilities, and no `router.py`/domain-router modification. These mirror the Stage 7 task 1.11/3.15/5.5 source-inspection discipline and make the "do not implement retrieval or any later stage" invariant executable.

## Risks / Trade-offs

- [Process schema/storage contract not FROZEN-defined (HR-3/HR-4/HR-5)] → Mitigation: the contract is fully designed in this change and was approved by human review (HR-3/HR-4/HR-5, recorded 2026-08-23); C8.2/C8.3 implementation tasks remain dependent on a separately authorized Stage-8 implementation task; no agent resolves the gap silently (master backlog §M.1).
- [Process-domain lifecycle/ownership/duplicate/verification rules must be self-sufficient (HR-6)] → Mitigation: the `judicial-process` spec states the process-domain requirements explicitly and normatively, reusing the conservative Stage 7-proven mechanics (write-blocked on ambiguity/material uncertainty, no fabricated `verified`, no auto-version, no content-based safe-equivalence); the Legal-scoped memos are not normative authorities for process storage.
- [Process `type` authority open (HR-3)] → Mitigation: explicit operator intent in the validated producer context; suggestions non-authoritative; conflict → REVIEW_REQUIRED; no content-derived `type`; vocabulary grounded in the FROZEN impl plan §10 scope.
- [Evidence reference not in the report (HR-7)] → Mitigation: producer context carries the reference; cross-checked against `input.sha256`; missing reference for PDF-derived concept is a configuration error, never invented.
- [Process storage does not exist; first publication must create the canonical tree] → Mitigation: `publish` creates `process/<type_dir>/` atomically; tests exercise the process write guard against a real process root; `process/` is Git-tracked (canonical corpus), not gitignored.
- [Duplicate resolution for process documents has no dedicated FROZEN memo] → Mitigation: the conservative state machine is stated explicitly as a process-domain requirement (HR-6), write-blocked on ambiguity/material uncertainty, no hash→no-op reduction, no content-based equivalence in v1; a future process-specific memo may refine it (deferred, non-blocking).
- [Producer observability could capture content or patch bodies] → Mitigation: record contract restricts to counts/statuses/hashes; source-inspection + behavioral tests; process numbers/names/CPF explicitly excluded.
- [CLI surface could drift from FROZEN §14 or regress existing CLIs] → Mitigation: `build`/`validate` are non-writing, `publish` is the single guarded write; existing CLI suites run unchanged (non-regression tests); command naming is Implementation Choice.
- [Accidental Legal-schema coupling] → Mitigation: source-inspection tests assert no Legal module/schema/profile import in every process module; domain-isolated types defined in the process module.

## Migration Plan

No migration of existing data: this change introduces the Judicial Process branch and process-domain storage from scratch (`process/` is created by the first guarded publication). No existing artifact, behavior, module, or spec is modified; the new capability spec becomes a living spec at archive time (`openspec/specs/judicial-process/spec.md`). The `repo-jur process` subcommands are additive; `converter-juridico`, `repo-jur route`, and `repo-jur producer` remain byte-identical.

## Resolved Human-Review Decisions (approved 2026-08-23)

- HR-1 APPROVED: deterministic-first Process Semantic Review v1; no LLM engine in this change.
- HR-2 APPROVED: no LLM engine, model, provider, prompt, or semantic-AI invocation in Stage 8 v1; any future LLM engine requires a separately authorized change.
- HR-3 APPROVED: explicit validated operator intent is the sole `type` authority; approved vocabulary exactly `Peticao | Contestacao | Decisao | Procuracao | Testamento | Anexo | OutraPeca`; a conflicting non-authoritative suggestion routes to `REVIEW_REQUIRED`; no content-derived type.
- HR-4 APPROVED: process-domain storage contract — canonical root `<repo>/process/` (Git-tracked, outside `bundle/` and outside `var/`), positional paths, atomic publication, dedicated process write guard (only `judicial_process` may write process storage); `guard_legal_bundle_write` remains unchanged and Legal-specific — resolves the planning backlog's mandatory human decision M.1.
- HR-5 APPROVED: process frontmatter profile (OKF v0.2 base rules + process-specific profile, never the Legal profile); `status` Human-Owned; `verified` never fabricated; `generated.at` meaningful-change semantics; no `_v2`/UUID/stable-id.
- HR-6 APPROVED WITH NORMATIVE CORRECTION: lifecycle/ownership/duplicate/verification mechanics may reuse Stage 7-proven behavior, but the Legal-scoped FROZEN memos are NOT normative authorities for Judicial Process by analogy; the judicial-process OpenSpec states the process-domain rules explicitly and self-sufficiently.
- HR-7 APPROVED: producer-context `sources[].resource` threading, cross-checked against report `input.sha256`, never invented; missing evidence reference for PDF-derived content is a configuration error.
- HR-8 APPROVED: `repo-jur process build|validate|publish` surface; `build`/`validate` never write; `publish` is the single guarded write path; no automatic Git commit/push.

## Open Questions (future, non-blocking)

- (a) whether a future change may authorize an LLM review engine and under which provenance/confidence rules; (b) whether a future change should draft a process-specific FROZEN memo (schema/storage/duplicate) once the process corpus grows; (c) whether a future report-schema change should record the critical-data status so downstream stages read it from the report; (d) deterministic redundant-value comparison remains a future capability (arquitetura §1.6).
