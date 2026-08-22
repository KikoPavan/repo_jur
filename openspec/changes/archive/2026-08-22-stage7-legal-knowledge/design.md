## Context

Stage 6 (Domain Router) is closed and archived; its living spec (`openspec/specs/domain-router/spec.md`) and implementation (`src/pipeline_juridico/domain_router.py`, `domain_router_cli.py`) deterministically emit exactly one of `legal_knowledge`, `judicial_process`, `review_required` from conformant Phase 1 artifacts (recorded gate `PASS`/`PASS_WITH_WARNINGS`, critical status `OK`/`WARNING`, and the approved `requested_domain` signal). The FROZEN corpus then requires the `legal_knowledge` branch to be implemented as the Legal Knowledge Pipeline: Legal Semantic Review / Enrichment → Legal Producer → `repo_jur/bundle/` (`implementation-plan-repo-jur-v1.1-FROZEN.md` §9; `technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §3.3/§3.5/§8C/§9/§18; `arquitetura-fase2-repo-jur-v15-FROZEN.md` §1.2/§1.4/§4/§8.11; `decision-memo-semantic-review-enrichment-layer-v1.1-FROZEN.md`).

Current repository facts (verified 2026-08-22 on this worktree):

- `Phase1Artifacts`, `RouteTarget`, `CriticalValidationStatus`, `GateState`, `Actor`, `guard_legal_bundle_write` live in `src/pipeline_juridico/contracts.py`; `Phase1Artifacts` is re-exported by `conversion_engine.py`. The guard is currently consumed only by its own tests (`tests/test_contracts.py::test_zero_write_guard_*`) — the Stage 7 Producer is its first production consumer.
- `config.py::ensure_outside_canonical_bundle(path)` rejects paths inside `bundle/` for operational directories; `validator.py::write_atomic` provides temp-file + fsync + rename publication; `hashing.py` provides `sha256_bytes`/`sha256_file`.
- The Phase 1 technical report (`report.py::validate_report_contract`) carries `schema_version`, `execution_id`, `input.{sha256,byte_size,page_count}`, `phase1.{implementation,implementation_version,logical_processing_version,relevant_config_fingerprint}`, `result.{quality_gate,warnings,errors}`, `artifacts.markdown_sha256`, `pages[]`, `telemetry`. It does NOT carry the preserved-evidence resource URI (the ingress state record does — `ingress.py::_write_state` stores `result` = evidence reference) and does NOT carry the Critical-Data Validation status.
- The Stage 6 router reads the gate outcome from the report (`result.quality_gate`), requires `PASS`/`PASS_WITH_WARNINGS` to proceed, and its observability record is stored under a configurable state dir (default `var/routing/state/`), outside the bundle.
- No Semantic Review, no Producer, no OKF/YAML handling, no bundle-write path, no `bundle/` directory exists (all verified).
- Existing CLI conventions (`tests/test_cli.py`, `tests/test_domain_router_cli.py`): argparse, environment-driven directories, deterministic exit codes (0 success, 1 input, 2 unexpected, 3 config/contract, 4 output conflict, 5 blocked), sanitized logging, atomic writes.
- Test baseline on this worktree (with the gitignored `input/*.pdf` corpus fixtures symlinked from the primary tree, not staged): **739 passed**. `openspec validate --all --strict`: **7 passed, 0 failed**.
- Console scripts today: `converter-juridico = pipeline_juridico.cli:main`, `repo-jur = pipeline_juridico.domain_router_cli:main` (`pyproject.toml`). Runtime: Python 3.12, `uv`, `src/` layout.

## Repository Implementation Map (Stage 0 / physical-layout memo)

| Logical capability | Physical implementation found | Decision | Tests covering it | Migration |
| --- | --- | --- | --- | --- |
| Shared contracts (`Phase1Artifacts`, `RouteTarget`, `CriticalValidationStatus`, `GateState`, `Actor`, `guard_legal_bundle_write`) | `src/pipeline_juridico/contracts.py` (guard consumed by its own tests only) | **REUSE** as-is; no modification | `tests/test_contracts.py` | none |
| Bundle-boundary enforcement for operational paths | `config.py::ensure_outside_canonical_bundle` | **REUSE** as-is | `tests/test_config.py` | none |
| Atomic file publication | `validator.py::write_atomic` | **REUSE** as-is | `tests/test_validator.py` | none |
| SHA-256 utilities | `hashing.py` | **REUSE** as-is | `tests/test_hashing.py` | none |
| Phase 1 artifacts boundary + recorded gate outcome | `conversion_engine.py` / `report.py` (report contract carries `result.quality_gate`) | **REUSE** read-only; Producer re-reads gate outcome from the report | existing Stage 3/5 tests | none |
| Legal Semantic Review / Enrichment | none — no semantic-review component exists | **CREATE** `src/pipeline_juridico/legal_semantic_review.py` (new module, physical-layout memo: create only when no suitable implementation exists) | new `tests/test_legal_semantic_review.py` | none |
| Legal Producer (identity/provenance, ownership merge, OKF render, validate, publish) | none — no Producer exists | **CREATE** `src/pipeline_juridico/legal_producer.py` | new `tests/test_legal_producer.py` | none |
| Producer operational CLI | none — `repo-jur` has only `route` | **CREATE** `src/pipeline_juridico/legal_producer_cli.py`; add `producer` subcommand to the existing `repo-jur` entry point (do not modify `cli.py`, do not touch `route`) | new `tests/test_legal_producer_cli.py` | none |
| Canonical bundle tree | none — `bundle/` absent | **CREATE** on first Producer publication: `bundle/{legislacao,jurisprudencia,temas,precedentes}/` | new producer tests exercise the guard against a real bundle root | none |

## Goals / Non-Goals

**Goals:**

- implement the `legal_knowledge` branch end to end: Legal Semantic Review seam → Legal Producer → `repo_jur/bundle/`, consuming only conformant Phase 1 artifacts (gate `PASS`/`PASS_WITH_WARNINGS`, route `legal_knowledge`) read-only;
- keep Phase 1 artifacts byte-identical across the whole Stage 7 (Semantic Review never overwrites; Producer never rewrites the body beyond FROZEN-allowed structural patches with full provenance);
- make Semantic Review domain-isolated, engine-neutral, deterministic-first (rule-registry-backed), with structured patches (`before`/`after`/`reason`/`confidence`/`page_refs`/`evidence_refs`), REVIEW_REQUIRED on ambiguity, and zero publication authority;
- make the Legal Producer the single canonical publisher through `guard_legal_bundle_write`, following the 10-step lifecycle/ownership merge, conservative Duplicate Act Handling, PDF cardinality, positional concept identity, OKF + Legal Profile validation, and atomic publication with Git-diff exposure;
- add the minimal FROZEN-recommended `repo-jur producer build|validate|publish` CLI surface with deterministic exit codes and CLI non-regression (existing `converter-juridico` and `repo-jur route` untouched);
- prove the boundary invariants with executable tests: input gating, Phase 1 immutability (SHA-256), word preservation on structural patches, REVIEW_REQUIRED on ambiguity, no LLM/silent classification, guard-only publication, no automatic `verified`/`status`/`_v2`, deterministic idempotent regeneration, no Judicial-Process behavior, CLI non-regression, observability outside the bundle.

**Non-Goals:**

- Stage 8 (Judicial Process Semantic Review / Producer / storage) — `judicial_process`-routed artifacts never enter the Stage 7 boundary;
- Stage 9 (Legal Knowledge Retrieval) and all retrieval/chunking/reranking;
- modifying Domain Router semantics, `router.py` page routing, the converter, OCR provider, thresholds, cleaner, validator, report generation, Stages 2–6 code, `contracts.py`, `config.py`, or any FROZEN authority;
- selecting an LLM/semantic model, prompt, or provider for the review engine (design doc §20.5) — the seam stays neutral and the deterministic path is default (HR-2);
- deriving the OKF `type` from document content or from `legal_hints` (Stage 6 HR-1 authority preserved) — `type` is explicit operator intent in the producer context (HR-3);
- automatic consolidation of physically distinct PDFs into one concept without safe logical/material equivalence (Duplicate Act Handling CLOSED);
- automatic `verified`, `status` mutation, `_v2`/UUID/stable-id creation;
- YAML/enrichment schema reuse across bounded contexts;
- writing `bundle/` outside the Producer, or writing any derived/runtime data into `bundle/`;
- adding or changing dependencies.

## Decisions

### 1. One OpenSpec change for Stage 7, with C7.1/C7.2/C7.3 as dependent task groups

`stage7-legal-knowledge` is a single OpenSpec change whose `tasks.md` splits into three dependency-ordered groups: **C7.1 — Legal Semantic Review seam** (module, patch model, rule registry, deterministic-first engine, REVIEW_REQUIRED semantics), **C7.2 — Legal Producer core** (identity/provenance resolution, ownership/lifecycle merge, OKF render + validation, guard-gated atomic publication), and **C7.3 — operational producer CLI + observability** (`repo-jur producer build|validate|publish`, state records). C7.2 depends on C7.1 (Producer consumes the ReviewResult); C7.3 depends on C7.2 (CLI drives the core).

**Rationale:** identical to Stage 6 Decision 1: both slices are governed by the same FROZEN authorities (tech spec §8C/§9/§14/§15, impl plan §9) and one capability spec (`legal-knowledge`); splitting into two changes would double-sync the same spec at archive time or create a second thin capability. The C7.x numbering is grounded in the FROZEN sub-capabilities (tech spec §3.3 lists `legal semantic review`, `legal schemas`, `legal producer` as logical sub-capabilities of the Legal Knowledge Context; impl plan §9 has a Semantic Review section and a Producer section).

### 2. New modules `legal_semantic_review.py`, `legal_producer.py`, `legal_producer_cli.py`; reuse every existing contract; never touch Stages 2–6 modules

Physical-layout memo and impl plan §0/§13 mandate REUSE → ADAPT IN PLACE → TEST and forbid parallel trees. No existing implementation satisfies the review or producer capabilities (verified), so new modules under the confirmed physical root `src/pipeline_juridico/` are authorized. `contracts.py`, `config.py`, `validator.py`, `hashing.py`, `conversion_engine.py`, `report.py`, `domain_router.py`, `domain_router_cli.py` are used read-only or as-is, never modified — the sole permitted touch on an existing module is the additive registration of the `producer` subcommand group on the `repo-jur` entry point (Decision 9), with no existing behavior, flag, or surface changed.

**Rationale:** the confirmed physical root is `src/pipeline_juridico/` (arquitetura §2.1, impl plan §0); the physical-layout memo authorizes CREATE when no suitable implementation exists.

### 3. Stage 7 input contract: conformant Phase 1 artifacts + recorded gate + routing decision; read gate outcome from the report

The Stage 7 boundary (both the review seam and the Producer) accepts the Stage 3 `Phase1Artifacts` (`markdown: str`, `report_json: str`) strictly read-only and re-reads the recorded Quality Gate outcome from the report's `result.quality_gate`, structurally enforcing "only gate-`PASS`/`PASS_WITH_WARNINGS` content enters" (phase1-op-spec §14; domain-router spec). The Producer additionally requires the routing decision to be exactly `RouteTarget.LEGAL_KNOWLEDGE` (the router's `RoutingDecision` or the serialized decision value): a `judicial_process` decision is a domain error (dedicated configuration error — Stage 7 never silently re-routes), and a `review_required` decision means no Stage 7 run. The gate outcome is read from the report, never from a caller-supplied override.

**Rationale:** mirrors Stage 6 Decision 3 — reading the recorded gate from the report makes the post-gate invariant structural; the routing decision is consumed as the Stage 6 output, not re-derived.

### 4. Legal Semantic Review: deterministic-first, engine-neutral seam; AI/LLM engine deferred (HR-1, HR-2)

`src/pipeline_juridico/legal_semantic_review.py` exposes an engine-neutral seam following tech spec §3.5:

```python
class LegalSemanticReviewEngine:
    def review(self, phase1_artifacts: Phase1Artifacts, profile: LegalReviewProfile) -> ReviewResult:
        ...
```

`ReviewResult` carries: structured patches (`LegalPatch(before, after, reason, confidence, page_refs, evidence_refs)`), extracted fields, classification suggestions (non-authoritative), warnings, and a `REVIEW_REQUIRED` flag. The default engine is **deterministic**: a versioned, registry-backed rule set (mirroring Stage 4 `CriticalValidationRule` provenance: `rule_id`, `rule_version`, `source/specification`, `validation_logic_version`) that only performs structural corrections preserving every original word (validated automatically — the word-multiset of `after` ⊇ `before` for structural patches; no summary/paraphrase/translation/invention/inference). Ambiguity that cannot be resolved without inference → `REVIEW_REQUIRED` (never silent application). No LLM call, no model/provider/prompt selection, no content classification authority in v1 (HR-1/HR-2); the engine interface is the future LLM insertion point and a source-inspection test asserts the review module contains no LLM/semantic-client reference.

**Rationale:** the FROZEN memo authorizes the layer and its invariants; the design doc §20.5 explicitly defers model/prompt/provider choice; the corpus discipline (LOOPS.md, critical-data provenance rule) forbids inventing rules without versioned normative evidence. Deterministic-first honors "distinguish deterministic processing from AI/semantic processing" and "do not silently introduce semantic/LLM classification".

**Alternative considered:** shipping an LLM-backed engine behind the seam in v1.
**Rejected because:** design doc §20.5 explicitly places model/prompt/provider choice out of scope; no FROZEN authority selects an engine; silent LLM classification is prohibited by the task invariants; the deterministic path is the corpus-approved default (HR-1/HR-2 for human confirmation).

### 5. OKF `type` is explicit operator intent in a validated producer context; semantic suggestions never decide it (HR-3)

The OKF profile requires `type` ∈ {`Legislacao`, `Jurisprudencia`, `TemaJuridico`, `PrecedenteVinculante`} (legal-okf-profile §1.1). No FROZEN baseline defines how a `legal_knowledge`-routed artifact is typed, and Stage 6 denied `legal_hints` routing authority. This change defines the deterministic source: the validated **producer context** carries the single authoritative `type` signal, supplied explicitly by the operator via `--type` (mapping onto the context), with values exactly the four profile types. The Semantic Review layer MAY emit a classification *suggestion* (non-authoritative); a suggestion conflicting with the explicit `type` routes the Producer run to `REVIEW_REQUIRED` (the operator signal is never silently overridden, and the suggestion is never silently applied). A producer context with an invalid or missing `type` is a dedicated configuration error (never a silent default, never a content-derived guess).

**Rationale:** consistent with Stage 6's approved pattern (explicit workflow intent as the deterministic signal; `legal_hints`-derived content inference denied) and with "no silent semantic classification".

**Alternative considered:** deriving `type` deterministically from report metadata (e.g. presence of `repo_jur_processo_numero` → `Jurisprudencia`).
**Rejected because:** no FROZEN baseline authorizes such a rule; it would reintroduce content-derived classification by another name; Stage 6 HR-1 explicitly deferred any such grant to a future change with normative authority.

### 6. `sources[].resource` for PDF-derived concepts comes from the validated producer context, matched against the report hash (HR-4)

The OKF profile requires `sources[].resource` to identify the preserved evidence used by the pipeline, and arquitetura §8.1 requires a stable resolvable reference; the Phase 1 report does not carry the resource URI (only `input.sha256` + `execution_id`). The Producer therefore receives the preserved-evidence reference through the validated producer context (`--evidence-resource <uri>`), validates it as a resolvable reference (reusing `resolve_safe_path`/`resolve_evidence_reference`-style checks where applicable or a plain validated URI), and cross-checks the report's `input.sha256` when the reference is resolvable to bytes. When the concept is PDF-derived and no resource is supplied, the run is a configuration error (never an invented resource, never silent omission of provenance). `repo_jur_pdf_hash` (1 PDF) / `repo_jur_pdf_hashes` (2+ PDFs, mapping `sources[].id` → SHA-256) follow the CLOSED cardinality rules with mutual exclusivity.

**Alternative considered:** deriving the resource from the ingress state record by `execution_id`.
**Rejected because:** the report→ingress-state join key is not FROZEN-defined and the ingress state record does not carry `execution_id` (only `handoff_id` + official hash); a deterministic join would invent a contract. The explicit producer-context reference is the minimal, auditable choice (HR-4 for confirmation).

### 7. Duplicate resolution implements the FROZEN state machine, conservative, write-blocked on ambiguity (HR-5)

`legal_producer.py` implements the `decision-memo-duplicate-act-handling-v1.0` deterministic flow: official SHA-256 from the report → candidate concept path (positional, per `concept-identity-physical-structure-v1.3` §1/§3/§5) → if no existing concept → NEW CONCEPT; if same physical evidence and equivalent canonical inputs/config/logical version and no meaningful change → NO-OP (no write, no `generated.at` bump); same evidence with meaningful change → REGENERATE/UPDATE (lifecycle merge); additional distinct-but-equivalent PDF → ADD SOURCE/UPDATE CARDINALITY (singular→plural only after the plural mapping is complete and validated); distinct/autonomous act → NEW CONCEPT; material change or ambiguity → HUMAN REVIEW (no write; Producer observability records `human_review_required`). Hash is physical evidence identity only — never logical identity, never a `_v2` suffix, never automatic `status` mutation.

**Rationale:** tech spec §9.2 and the CLOSED memo require exactly these resolution categories; the safe-equivalence judgment is deliberately conservative in v1 (no content-based equivalence inference — HR-5).

### 8. Lifecycle/ownership merge and OKF render follow the 10-step FROZEN workflow, with `verified`/`status`/`generated` policies enforced

`legal_producer.py` follows `lifecycle-field-ownership-v1.4` §4 exactly: load existing concept (frontmatter + body) → resolve identity/provenance → detect technical vs material change → recompute Producer-Owned fields → merge Shared/Human-Owned (human-curated values preserved) → apply `verified`/`repo_jur_verification_history` policy (never auto-create `verified`; archive only real prior events on material change, preserving `by`/`at`, recording `invalidated_by`; omit `verified` when no active events remain) → apply body ownership (PDF-derived body = Producer-Owned literal with `[[Pág. N]]` markers preserved; abstract body = Human/Shared — never fabricated) → validate OKF + Legal OKF Profile + cardinality + `sources` mapping → atomic publication (temp file on same filesystem, fsync, rename, Git diff exposed; no automatic commit/push). `status` is never inserted/changed by the Producer (absent = OKF `stable` semantics); `generated.by` = `repo_jur_producer/<version>`; `generated.at` updates only on meaningful change (deterministic meaningful-change predicate tested).

### 9. Operational CLI: `repo-jur producer build|validate|publish`; single write path; non-regression (HR-6)

New console-script wiring: the existing `repo-jur` entry point (`domain_router_cli.py`) gains a `producer` subcommand group (or `legal_producer_cli.py` registers `repo-jur producer` via the same entry module — implementation detail); `converter-juridico` and `repo-jur route` surfaces remain byte-identical (non-regression proven by the existing CLI test suites).

```text
repo-jur producer build <markdown.md> <report.json> --type <Tipo> [--evidence-resource <uri>] [--context <producer-context.json>] [--bundle-root <dir>] [--state-dir <dir>] [--log-level <level>] [--json]
repo-jur producer validate <concept-candidate.md> [--bundle-root <dir>] [--log-level <level>] [--json]
repo-jur producer publish <concept-candidate.md> [--overwrite] [--bundle-root <dir>] [--state-dir <dir>] [--log-level <level>] [--json]
```

Semantics: `build` runs the Semantic Review seam + Producer render, produces a concept candidate (frontmatter + body) on stdout or a state file, and writes a review/observability record — **never writes to `bundle/`**; `validate` validates a candidate against OKF + profile + cardinality + ownership without writing; `publish` is the single write path, re-validating, then publishing atomically through `guard_legal_bundle_write` (acting domain `LEGAL_KNOWLEDGE`) into `bundle/`, writing the Producer observability record (resolution outcome, materiality category, human-review requirement, publication result — tech spec §15.1) under a configurable state dir (default `var/producer/state/`), outside the bundle. Exit codes extend the existing convention: 0 success; 1 input; 2 unexpected; 3 configuration/contract (invalid `--type`, missing evidence resource for PDF-derived, guard denial misconfigured, unreadable context/report); 5 blocked (gate `FAIL`, `review_required` decision, HUMAN REVIEW required — no write, no publish record). `publish` never performs Git commit/push/merge (HR-6).

### 10. Producer observability record: shape and location

One JSON record per Producer run (build and publish), written under a configurable operational directory (default `var/producer/state/`), enforced outside the canonical bundle via `config.py::ensure_outside_canonical_bundle`. Fields (behavioral, per tech spec §15.1): schema version, record type (`producer.build` / `producer.publish` / `producer.review_required`), evidence provenance hash (`input.sha256`), recorded gate outcome, routing decision, review summary (patch count, REVIEW_REQUIRED flag — never patch content), resolution outcome (`new_concept`/`noop`/`regenerate`/`add_source`/`human_review_required`), materiality category when applicable, `verified` action (`preserved`/`none`/`archived`), publication result (`published`/`blocked`/`noop`), `generated.at` action, and the concept path. MUST NOT include: document content, full critical identifier values, secrets/tokens/credentials, or patch bodies. Determinism: the concept render is a pure function of the artifacts + context; the record may carry operational metadata (timestamps) as observability.

## Risks / Trade-offs

- [Semantic review engine open (HR-1/HR-2)] → Mitigation: seam is engine-neutral; v1 is deterministic-first; any LLM engine is a future, explicitly authorized change constrained by the same invariants.
- [`type` authority not FROZEN-defined (HR-3)] → Mitigation: explicit operator intent in the validated producer context; suggestions non-authoritative; conflict → REVIEW_REQUIRED; no content-derived `type`.
- [Preserved-evidence reference not in the report (HR-4)] → Mitigation: producer context carries the reference; cross-checked against `input.sha256`; missing reference for PDF-derived concept is a configuration error, never invented.
- [Bundle does not exist; first publication must create the canonical tree] → Mitigation: `publish` creates `bundle/<type-dir>/` atomically; tests exercise the guard against a real bundle root; `bundle/` is Git-tracked (canonical corpus), not gitignored.
- [Duplicate resolution risk (HR-5)] → Mitigation: full FROZEN state machine, write-blocked on ambiguity, no hash→no-op reduction, no content-based equivalence in v1.
- [`generated.at` meaningful-change predicate] → Mitigation: deterministic predicate (content bytes, ownership-affecting fields, cardinality, provenance) tested for both update and no-op cases; timestamp-only diffs forbidden.
- [Producer observability could capture content or patch bodies] → Mitigation: record contract restricts to counts/statuses/hashes; source-inspection + behavioral tests.
- [CLI surface could drift from FROZEN §14 or regress existing CLIs] → Mitigation: `build`/`validate` are non-writing, `publish` is the single guarded write; existing CLI suites run unchanged (non-regression tests); command naming is Implementation Choice.

## Migration Plan

No migration of existing data: this change introduces the Legal Knowledge branch and the canonical bundle from scratch (`bundle/` is created by the first publication). No existing artifact, behavior, module, or spec is modified; the new capability spec becomes a living spec at archive time (`openspec/specs/legal-knowledge/spec.md`). The `repo-jur producer` subcommands are additive; `converter-juridico` and `repo-jur route` remain byte-identical.

## Open Questions

- HR-1/HR-2: confirm deterministic-first v1 and no LLM engine in this change.
- HR-3: confirm explicit-operator-intent `type` authority (no content-derived `type`).
- HR-4: confirm producer-context `sources[].resource` threading (vs. future ingress-state join).
- HR-5: confirm conservative duplicate-resolution boundary (no content-based safe-equivalence in v1).
- HR-6: confirm `repo-jur producer build|validate|publish` surface and no-auto-commit semantics.
- Future (non-blocking): (a) whether a future change may authorize an LLM review engine and under which provenance/confidence rules; (b) whether a future report-schema change should record the critical-data status so downstream stages read it from the report; (c) whether a future change may derive `type` from deterministic `legal_hints` rules with normative authority; (d) deterministic redundant-value comparison remains a future capability (arquitetura §1.6).
