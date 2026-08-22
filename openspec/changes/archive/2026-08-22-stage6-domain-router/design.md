## Context

Stage 3 established the Shared Conversion Core: `ConversionEngine.convert(evidence_ref, config) -> Phase1Artifacts`, where `Phase1Artifacts` carries the literal Markdown (method comments normalized out, canonical `[[Pág. N]]` markers preserved) plus a serialized, contract-validated technical report (`src/pipeline_juridico/conversion_engine.py`). Stage 4 added the non-mutating Critical-Data Validation seam (`CriticalDataValidator.validate(phase1_artifacts, profile) -> CriticalValidationResult`, `src/pipeline_juridico/critical_data.py`) with an explicit independence contract from the Quality Gate. Stage 5 added the deterministic Phase 1 Quality Gate (`src/pipeline_juridico/quality_gate.py`, `evaluate(phase1_artifacts) -> QualityGateResult`) and wired it into the shared boundary output, so a conformant Phase 1 technical report now carries `result.quality_gate` ∈ {`PASS`, `PASS_WITH_WARNINGS`, `FAIL`} (`report.py::attach_gate_result`; `conversion_engine.py`). The FROZEN architecture now requires the Stage 6 seam itself: the deterministic Domain Router that selects exactly one of `legal_knowledge`, `judicial_process`, `review_required` strictly after the Quality Gate, without hidden semantic classification (`technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §3.2, §8B, §18 Stage 6; `implementation-plan-repo-jur-v1.1-FROZEN.md` §8; `arquitetura-fase2-repo-jur-v15-FROZEN.md` §1; `implementation-plan-correction-impact-v1.0-FROZEN.md` §4).

The Stage 6 decision memo does not exist as a standalone FROZEN memo; Stage 6 is governed by the tech spec §3.2/§8B, the impl plan §8, and the boundary statements in the Stage 4/5 specs and memos. Human review decisions (2026-08-22, task t_4bfbe485 comment thread) resolved the Stage 6 design-time choices that the corpus left open:

- **HR-1**: `legal_hints` is NOT authorized as a routing authority in Stage 6 v1; no domain route may be derived from it. A future change may authorize deterministic `legal_hints` rules only if normative authority is established.
- **HR-2**: workflow context IS approved and MUST be instantiated as the initial explicit routing signal: `requested_domain = legal_knowledge | judicial_process`, with the approved fixed precedence (Decision 6). This is explicit workflow/operator intent, not semantic inference from document content.
- **HR-3**: a contract-violating routing context is a configuration error (`RoutingConfigurationError`), never `review_required`; `review_required` is for valid input with no authorized decisive signal or other permitted ambiguity.

The remaining design work is the same class as Stage 4/5: choose the minimal Python representation and module placement that preserve every approved constraint, resolve the routing-signal contract per the human decisions, and prove the boundary invariants with executable tests.

Current repository facts (verified 2026-08-22):

- `RouteTarget` exists in `src/pipeline_juridico/contracts.py:113-116` with exactly `legal_knowledge`, `judicial_process`, `review_required` and is consumed only by `guard_legal_bundle_write` (`contracts.py:119-136`) and `tests/test_contracts.py::test_route_target_values`. It is the FROZEN three-target contract waiting for its routing consumer — this change provides it.
- `guard_legal_bundle_write(acting_domain: RouteTarget, target, legal_bundle_root)` authorizes a write target, reserving the Legal bundle for `legal_knowledge` only. It is a **write-authorization** guard for the Stage 7/8 producer boundary; the router never writes and therefore never invokes it.
- `router.py` is the **page-level** routing seam (`route_page(page, config) -> Metodo` classifying each PDF page as `texto_nativo`/`ocr_integral`/`hibrido`/`vazia`/`erro`). It is a different routing concept (physical page method vs. domain destination) under a different contract; the task and the FROZEN corpus require it to remain untouched.
- `Phase1Artifacts` (conversion_engine.py) carries `markdown` + `report_json`; the report always carries `result.quality_gate` after Stage 5 wiring, and `report.py::validate_report_contract` enforces it.
- The Critical-Data Validation status is **not** recorded in the Phase 1 report (Stage 4 seam is not wired into the report; the report's `result` block carries only `quality_gate`/`warnings`/`errors`). The router therefore receives the critical status as an explicit pipeline parameter.
- `legal_hints` is parsed and validated by Stage 2 (`src/pipeline_juridico/itp.py:29,45,63-64,156-175`; `openspec/specs/itp-ingress-preflight-evidence/spec.md`) as an optional mapping "sem autoridade canônica" (ITP §7.7, ESIC §4.3), but it is not threaded into `Phase1Artifacts` and has no routing consumer. HR-1 keeps it that way.
- The term `requested_domain` appears nowhere in the FROZEN corpus, living specs, or source (verified 2026-08-22): it is introduced here solely as the approved initial routing signal contract (HR-2) — no collision with any existing concept.
- No domain-routing module, no routing observability, no route CLI exist. Console scripts: `converter-juridico = pipeline_juridico.cli:main` (`pyproject.toml`).
- Existing CLI conventions (verified in `tests/test_cli.py` and `src/pipeline_juridico/cli.py`): argparse-based single-purpose CLI, environment-driven directories (`OUTPUT_DIR`/`LOGS_DIR`/`TEMP_DIR`), deterministic exit codes (0 success, 1 input/config, 2 unexpected, 3 validation, 4 output conflict), sanitized/redacted logging (`_sanitize_log_message`), atomic writes via `validator.py::write_atomic`.

Runtime: the project declares `requires-python = ">=3.12"`, managed with `uv` under `src/pipeline_juridico/`. This change adds no dependency.

## Repository Implementation Map (Stage 0 / physical-layout memo)

| Logical capability | Physical implementation found | Decision | Tests covering it | Migration |
| --- | --- | --- | --- | --- |
| Route targets | `RouteTarget` in `src/pipeline_juridico/contracts.py:113-116` (unused by any routing component) | **REUSE** as-is; shared contract per `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md` ("RouteTarget domain outcomes" listed as shared) | `tests/test_contracts.py::test_route_target_values` | none |
| Phase 1 artifacts boundary | `Phase1Artifacts` in `src/pipeline_juridico/conversion_engine.py` (imported from `contracts.py`) | **REUSE** as-is as the read-only routing input | existing Stage 3/4/5 tests | none |
| Domain routing decision | none — no component produces a domain-routing decision; `router.py` is page-level routing under a different contract and is out of scope | **CREATE** minimal `src/pipeline_juridico/domain_router.py` | new `tests/test_domain_router.py` | none |
| Routing signal carrier (workflow context) | none — `requested_domain` introduced by HR-2; no FROZEN schema exists | **CREATE** a validated routing-context carrier whose permitted vocabulary is exactly the single key `requested_domain` ∈ {`legal_knowledge`, `judicial_process`} (Decision 4) | new `tests/test_domain_router.py` | none |
| Routing observability record | none | **CREATE** record builder + storage under a configurable operational directory (default `var/routing/state/`), enforced outside the canonical bundle via `config.py::ensure_outside_canonical_bundle` | new `tests/test_domain_router.py` | none |
| Operational route CLI | none; existing `converter-juridico` is conversion-scoped | **CREATE** new console script `repo-jur` (`src/pipeline_juridico/domain_router_cli.py`); do not modify `cli.py` | new `tests/test_domain_router_cli.py` | none |
| Bundle write guard | `guard_legal_bundle_write` in `contracts.py:119-136` | **NOT INVOKED by the router**; remains the Stage 7/8 producer-boundary guard; the router's `RouteTarget` is the `acting_domain` input that Stage 7/8 producers will pass | existing `tests/test_contracts.py::test_zero_write_guard_*` | none |

## Goals / Non-Goals

**Goals:**

- expose a pure, stateless routing entry point over the Stage 3/5 boundary — consuming `Phase1Artifacts` (read-only), the Critical-Data Validation status, and a validated routing context, and returning exactly one of the three `RouteTarget` outcomes — following the approved precedence (Decision 6): recorded gate `FAIL` → stop; critical `REVIEW_REQUIRED` → `review_required`; `requested_domain == legal_knowledge` → `legal_knowledge`; `requested_domain == judicial_process` → `judicial_process`; `requested_domain` absent → `review_required`;
- reuse `RouteTarget` and `Phase1Artifacts` from the shared contracts without modification, and reuse `config.py::ensure_outside_canonical_bundle` for the observability path;
- define the initial permitted routing signal contract per HR-2: a validated routing-context carrier whose permitted signal vocabulary is exactly the single key `requested_domain` (values `legal_knowledge` or `judicial_process`), carrying explicit workflow/operator intent and never derived from document content; `legal_hints` excluded per HR-1 with citations (ITP §7.7, ESIC §4.3);
- define the routing observability record as an operational/technical artifact outside the canonical bundle and outside Phase 1 content, with content/secret-safe fields (tech spec §3.2, §8B, §15; AGENTS.md logging rule) recording signal presence (keys) only;
- add the minimal operational `repo-jur route` CLI (C6.2) following FROZEN §14 and existing CLI conventions, with an explicit `--domain legal_knowledge|judicial_process` flag mapping onto `requested_domain`, and CLI non-regression proven (the `converter-juridico` surface is untouched);
- prove with executable tests: determinism (identical inputs → identical decision), precedence (the exact approved order, including `FAIL` → blocked/no decision and `REVIEW_REQUIRED` → `review_required` before any signal), signal selection (`requested_domain` selects the corresponding domain), ambiguity handling (`requested_domain` absent → `review_required`), configuration-error contract (context violating the fixed vocabulary → dedicated error, never a silent route — HR-3), no document-content inference (identical Markdown bodies with different signals route only by signal), no Phase 1 body mutation (SHA-256 of the Markdown unchanged; report byte-identical), no semantic-classifier/LLM/enrichment/Producer/publication coupling (source-inspection test), no bundle/process-storage write, no `guard_legal_bundle_write` invocation, and CLI non-regression.

**Non-Goals:**

- approving any routing signal beyond `requested_domain` (legal_hints-derived rules per HR-1, additional workflow-context fields) — future, separate changes;
- implementing Stage 7/8 Semantic Review or Producers, any canonical/process-storage write, or any use of `guard_legal_bundle_write`;
- implementing Stage 9 retrieval;
- creating Legal OKF / Process YAML or enrichment schemas or coupling the router to any domain schema (shared-conversion-core memo *Prohibited Coupling*);
- modifying `router.py` page-routing semantics, the converter, OCR provider, routing thresholds, cleaner, validator, report generation, Stage 4/5 code, the `converter-juridico` CLI, `contracts.py`, or `config.py`;
- adding or changing dependencies;
- writing to `repo_jur/bundle/` or process-domain storage.

## Decisions

### 1. One OpenSpec change for Stage 6, with C6.1/C6.2 as dependent task groups

`stage6-domain-router` is a single OpenSpec change whose `tasks.md` splits into two dependency-ordered groups: **C6.1 — Domain Router core** (`domain_router.py`, decision semantics, observability record) and **C6.2 — minimal operational CLI + routing observability surface** (`repo-jur route` console script). The C6.2 group is explicitly marked dependent on C6.1 completion. Approved by human review (2026-08-22).

**Rationale:** both slices are governed by the same FROZEN authorities (tech spec §3.2/§8B/§14/§15, impl plan §8) and the same capability area (`domain-router`); the observability record is produced by the core and merely surfaced by the CLI, so C6.2 cannot be implemented before C6.1; the repository archives one change per capability area (Stage 5 itself used two *sequential* changes — the gate, then its residual report-schema sync — but here C6.1 and C6.2 share one capability spec, so a second change would double-sync the same `domain-router` spec at archive time). Dependency clarity is preserved by task numbering and the explicit C6.1→C6.2 ordering.

**Alternative considered:** two OpenSpec changes (`stage6-domain-router`, `stage6-domain-router-cli`).
**Rejected because:** the second change would either create a second capability spec for a thin CLI surface (no authority basis) or amend the same `domain-router` capability (two archives syncing one spec); and the strict core→CLI dependency would force the CLI change to sit blocked until the core change archives, adding ceremony without adding clarity. **Reversibility:** the C6.2 task group maps 1:1 onto a future `stage6-domain-router-cli` change if the reviewer prefers a split — no rework.

### 2. New module `domain_router.py`; reuse `RouteTarget`; never touch `router.py`

A new module `src/pipeline_juridico/domain_router.py` owns the routing seam. It reuses `RouteTarget` from `src/pipeline_juridico/contracts.py` (already the exact three-target contract; shared-contract authority: shared-conversion-core memo) and `Phase1Artifacts` (from `conversion_engine.py`) without modification. `router.py` (page-level routing) is not imported, modified, or consulted. Approved by human review (2026-08-22).

**Repository Implementation Map rationale:** no existing implementation produces a domain-routing decision; `router.py` operates on a different contract (per-page physical `Metodo` classification from PyMuPDF signals) and the task explicitly forbids modifying its page-routing semantics. The physical-layout memo permits a new module when no suitable implementation exists.

**Alternative considered:** folding domain routing into `router.py` (renaming it as "the router").
**Rejected because:** it would couple two distinct FROZEN concepts (page-level physical method vs. post-gate domain destination) in one module and require modifying a stabilized, extensively tested page-router — explicitly out of scope.

### 3. Input contract: `Phase1Artifacts` (read-only) + Critical-Data Validation status + validated routing context; gate outcome read from the report

The routing entry point accepts:

- the Stage 3 `Phase1Artifacts` (`markdown: str`, `report_json: str`) — strictly read-only; the recorded Quality Gate outcome is read from the report's `result.quality_gate` (the authoritative Phase 1 technical artifact; `report.py` contract enforces its presence), which structurally enforces "routing occurs strictly after the Quality Gate": an artifact whose report does not record a gate outcome cannot be routed and routing is blocked;
- the Critical-Data Validation status (exactly one of `OK`, `WARNING`, `REVIEW_REQUIRED`) — an explicit parameter, because the Stage 4 seam result is not recorded in the Phase 1 report (proposal Residual Risk 3);
- a validated routing context (Decision 4) — the carrier of the `requested_domain` signal.

The router never resolves evidence, never invokes conversion or OCR, and never reads the Markdown body beyond what the decision requires (in fact the decision requires no body read at all — the body is carried only so the boundary contract matches the Stage 3/4/5 seams and so non-mutation can be proven).

**Rationale:** reading the gate outcome from the report (rather than as a second parameter) makes the "after the gate" invariant structural and keeps the routing inputs artifact-anchored and deterministic; the critical status must be a parameter because no FROZEN authority or current contract records it in the report.

**Alternative considered:** passing both gate state and critical status as explicit parameters, ignoring the report's recorded result.
**Rejected because:** it would allow routing an artifact whose recorded gate outcome is `FAIL` (a caller error would silently bypass the FROZEN stop rule); reading the authoritative recorded outcome closes that hole.

### 4. Routing signal contract: exactly one permitted signal — `requested_domain` — carried in a validated routing context (HR-2); `legal_hints` excluded (HR-1)

The optional routing context is a caller-supplied, schema-validated technical artifact carrying explicit routing signals. The schema is fixed: a mapping whose permitted signal keys are the **finite, explicitly enumerated vocabulary** `{requested_domain}`, where `requested_domain` SHALL be exactly one of the two serialized route-target values `legal_knowledge` or `judicial_process`. This is the approved HR-2 contract: explicit workflow/operator intent, never semantic inference from document content. Validation rules:

- no context supplied → `requested_domain` absent → `review_required` (Decision 6 step 5);
- context supplied with an empty signal set (`{}`) → `requested_domain` absent → `review_required`;
- context with `requested_domain == legal_knowledge` → selects `legal_knowledge`;
- context with `requested_domain == judicial_process` → selects `judicial_process`;
- context with a key outside the permitted vocabulary (any key other than `requested_domain`, including a `legal_hints`-derived key) → dedicated configuration error (`RoutingConfigurationError`), never silently `review_required`, never a domain route (Decision 5 / HR-3);
- context with `requested_domain` set to any value other than the two permitted values, or structurally invalid (wrong type, malformed JSON at the CLI) → configuration error (HR-3).

`legal_hints` (ITP §7.7, ESIC §4.3) is **not** part of the permitted vocabulary and SHALL NOT select a domain route in Stage 6 v1 (HR-1): the corpus defines hints as candidates "sem autoridade canônica" that "não criam identity", "não decidem Duplicate Act Handling", "não definem filename/slug", and "não têm autoridade de frontmatter" — no routing authority is granted. A future change may authorize deterministic `legal_hints` rules only if normative authority is established (HR-1). The carrier exists so that the evaluation procedure, the CLI, and the observability record are fully implementable and testable today, and so that a future change can approve additional signals without reshaping the seam.

**Rationale:** HR-2 approved workflow context as the initial explicit signal because it is operator intent, not content inference — the minimal `requested_domain` contract is exactly that; the single-signal vocabulary keeps the conservative posture ("only explicitly permitted deterministic routing signals may select legal_knowledge or judicial_process") while making domain selection actually reachable and executable.

**Alternative considered:** keeping the permitted vocabulary empty (the pre-review design), so no domain was ever selectable.
**Rejected because:** human review explicitly approved instantiating workflow context as `requested_domain`; an empty vocabulary would ignore that decision and make the CLI's `--domain` surface meaningless.

**Alternative considered:** granting `legal_hints.process_number` presence a `judicial_process` route immediately.
**Rejected because:** HR-1 explicitly denies `legal_hints` routing authority in Stage 6 v1; approving such a rule is a new normative grant that the sources do not support.

### 5. Configuration errors use a dedicated contract; never a silent route (HR-3)

A routing context that violates the fixed schema (unknown/unapproved signal key such as a `legal_hints` key, `requested_domain` with an invalid value, malformed payload) raises a dedicated `RoutingConfigurationError`, mirroring the Stage 4 pattern (`CriticalValidationConfigurationError`: "a configuration error is raised and never converted to OK"). The router never converts a malformed context into `review_required` (which would hide caller bugs) and never into a domain route. Confirmed by human review (HR-3, 2026-08-22): "review_required is for valid input with no authorized decisive signal or other permitted ambiguity."

**Rationale:** the FROZEN corpus specifies routing outcomes for missing/ambiguous *signals* but not for a *contract-violating context*; the Stage 4 configuration-error contract is the closest approved pattern and keeps the error model consistent across seams (error ≠ outcome).

**Alternative considered:** malformed/unknown-key context → `review_required` (fold into the ambiguity rule).
**Rejected because:** it would silently treat caller misuse as a document-routing state, obscuring configuration bugs; HR-3 approved the configuration-error choice.

### 6. Precedence, conflict, and ambiguity semantics (approved order)

The routing decision follows exactly the approved precedence (human decision HR-2; consistent with `implementation-plan-repo-jur-v1.1-FROZEN.md` §8):

```text
1. read recorded gate outcome from the report;
   - missing/unparseable report or missing recorded gate outcome  → RoutingBlockedError (no routing)
   - gate == FAIL                                                → RoutingBlockedError (stop; no decision)
   - gate ∈ {PASS, PASS_WITH_WARNINGS}                            → continue
2. critical == REVIEW_REQUIRED                                   → review_required (before any signal)
3. requested_domain == legal_knowledge                           → legal_knowledge
4. requested_domain == judicial_process                          → judicial_process
5. requested_domain absent (no context, empty context)           → review_required
```

`RoutingBlockedError` is the deterministic representation of "stop": the pipeline halts routing and no routing decision exists. The decision envelope (`RoutingDecision`) is produced only for the three `RouteTarget` outcomes and carries a deterministic reason code from a fixed vocabulary — `critical_review_required`, `requested_domain_legal_knowledge`, `requested_domain_judicial_process`, `missing_routing_signal`, `signal_conflict` — consumed by the observability record. The conflict rule (two or more permitted signals selecting different domains → `review_required`) is stated normatively in the spec per the task invariant "missing, conflicting, or ambiguous routing signals route to `review_required`", but with the single-signal vocabulary it is unreachable; it becomes executable when a future change approves a second signal (proposal Residual Risk 5).

**Rationale:** every reachable state is deterministic and artifact-anchored; the reason code keeps the decision auditable without leaking document content; the approved order makes step 2 (critical) and steps 3–4 (signal) strictly sequential, so a `REVIEW_REQUIRED` critical status wins over any operator signal.

**Alternative considered:** a signal could override a critical `REVIEW_REQUIRED` status.
**Rejected because:** the approved precedence and the Stage 4/5 independence memos place critical-data review ahead of any routing signal; a signal overriding it would let operator intent mask a critical-data problem.

### 7. The router is a pure decision function; observability is a separate builder

`route(...)` performs no I/O: it returns the decision envelope. A separate record builder assembles the observability payload from the decision inputs and outcome; the CLI/orchestrator persists it atomically (reusing `validator.py::write_atomic`). This keeps the decision function pure, idempotent, and unit-testable without filesystem setup, mirroring how the gate result is attached by the pipeline rather than by the gate.

**Rationale:** matches the Stage 5 seam pattern (gate computes; pipeline records `result.quality_gate`), and keeps "routing metadata belongs to operational/technical artifacts" a *separation* concern rather than an in-band mutation.

### 8. Routing observability record: shape and location

One JSON record per routing execution, written to a configurable operational directory (default `var/routing/state/`; environment override e.g. `ROUTING_STATE_DIR`), validated by `config.py::ensure_outside_canonical_bundle` (never inside `bundle/`). Content rules (behavioral, per tech spec §3.2/§8B/§15 and AGENTS.md logging rule):

- MUST include: schema version, the evidence SHA-256 from the report (`input.sha256` — a provenance hash, not arbitrarily redacted per §15.3), the recorded gate outcome, the critical-data status, the routing-context summary (**signal keys only, never values** — e.g. the presence of the `requested_domain` key, never its value; the selected domain is already carried by the `decision` field), the decision (`legal_knowledge`/`judicial_process`/`review_required`), the deterministic reason code, and the Phase-1 execution id when present in the report (traceability).
- MUST NOT include: any document content, any full critical identifier value, any routing-signal value (even though the `requested_domain` value equals the decision when a domain is selected, the record does not redundantly store it), secrets, tokens, or credentials.
- Determinism note: the *decision* is a pure function; the *record* may carry operational metadata (e.g. a timestamp) as observability per §15, without affecting the decision.

**Rationale:** the Phase 1 technical report is a Phase 1 artifact — appending routing metadata to it would violate the Stage 5 byte-identical-report invariant and the "routing metadata belongs to operational/technical artifacts" rule; a separate operational record under `var/` follows the existing `IngressConfig` convention and the §15.2 configurable-location requirement.

**Alternative considered:** recording the route in the Phase 1 report `result` block.
**Rejected because:** the report is the Phase 1 technical artifact; the Stage 5 spec requires it byte-identical across gate evaluation, and §3.2/§8B confine routing metadata to operational/technical artifacts — the report is not an operational artifact of Stage 6.

### 9. Minimal operational CLI: `repo-jur route` with an explicit `--domain` flag

New console script `repo-jur` (registered in `pyproject.toml`, entry `pipeline_juridico.domain_router_cli:main`) with a single subcommand for Stage 6 (approved by human review, including the `--domain` surface):

```text
repo-jur route <markdown.md> <report.json> [--domain legal_knowledge|judicial_process] [--context <context.json>] [--state-dir <dir>] [--log-level <level>] [--json]
```

Behavior (behavioral contract in the spec; concrete details here):

- reads the two Phase 1 artifact files and the optional context file (no conversion, no OCR, no engine imports);
- the `--domain` flag maps onto the approved `requested_domain` signal: `--domain legal_knowledge` → context `{"requested_domain": "legal_knowledge"}`; `--domain judicial_process` → context `{"requested_domain": "judicial_process"}`;
- `--context <context.json>` supplies the same validated carrier schema directly (`{"requested_domain": "legal_knowledge"}` or `{"requested_domain": "judicial_process"}`; empty object allowed — absent signal; any other key or invalid value → `RoutingConfigurationError`);
- when both `--domain` and `--context` are supplied, the effective context is validated as a whole: `requested_domain` values that disagree between the two sources are a caller-side contract violation → `RoutingConfigurationError` (HR-3 logic); a single source, or two agreeing sources, is valid; `--context` with an unknown key is a `RoutingConfigurationError` even when `--domain` is present;
- validates the report contract surface the router reads, computes the decision deterministically, writes the observability record atomically under the state directory (default `var/routing/state/`, env-overridable, bundle-guarded), prints the decision (`review_required`, `legal_knowledge`, `judicial_process`, or `blocked: <reason>` — machine-readable with `--json`);
- exit codes follow the existing convention: `0` decision recorded; `3` contract/configuration error (invalid report contract surface, `RoutingConfigurationError`, unreadable context); `5` routing blocked (recorded gate `FAIL` — no decision, no record); `2` unexpected error; `1` input error. The `repo-jur` codes are documented in the CLI help and tests; they extend, not change, the `converter-juridico` surface.

**Rationale:** FROZEN §14 recommends the `repo-jur <verb>` operational surface ("Command naming is Implementation Choice") and names routing among the operational CLI concerns; human review approved the explicit `--domain` flag "where consistent with the approved requested_domain contract". The existing `converter-juridico` is the conversion CLI and adding a subcommand to it would alter its positional contract and risk non-regression. A separate entry point keeps `converter-juridico` byte-identical and its test suite untouched.

**Alternative considered:** `converter-juridico route` subcommand or `converter-juridico --route` flag.
**Rejected because:** it changes the existing CLI's parsing contract (positional `pdf_path`), risks non-regression in `tests/test_cli.py`, and diverges from the FROZEN-recommended `repo-jur` surface.

### 10. Boundary with `guard_legal_bundle_write` and Stages 7/8

The router never writes: it never invokes `guard_legal_bundle_write`, never touches `bundle/` or process storage, and never behaves as a Producer. Its output — the `RouteTarget` — is precisely the `acting_domain` value that Stage 7/8 producers will pass to `guard_legal_bundle_write` when they write (`legal_knowledge` → Legal Producer → bundle, via the guard; `judicial_process` → process storage, outside the Legal bundle, per tech spec §3.4; `review_required` → no write). The Stage 6 spec states this boundary as a requirement: the router SHALL NOT perform any write and SHALL NOT invoke the bundle guard; the existing guard tests keep passing unchanged. Approved by human review (no Stage 7/8 implementation).

**Rationale:** the FROZEN producer-only publication rule (tech spec §9.1) and the guard's existing tests define the write boundary; the router's only contract with it is producing the domain value the guard consumes at Stage 7/8.

## Risks / Trade-offs

- [Conservative routing: only one approved signal (`requested_domain`) can select a domain; `legal_hints` and any other signal are barred] → Mitigation: this is the FROZEN-prescribed posture ("Domain Router conservador"; "only explicitly permitted deterministic routing signals may select legal_knowledge or judicial_process") plus the HR-1/HR-2 human decisions; every selectable outcome maps to an approved signal or an approved FROZEN rule.
- [The `requested_domain` signal is trusted operator intent; a caller could derive it from document content before calling the router] → Mitigation: the router only reads the validated context/CLI flag and never the Markdown body; the spec forbids content-derived signals; a source-inspection test asserts no content-analysis path exists in the routing implementation; detection of a misbehaving *caller* is outside this capability's authority (proposal Residual Risk 1).
- [Config-error path could surprise callers who expected review_required for unknown keys] → Mitigation: documented in Decision 5 and confirmed by HR-3; `review_required` is reserved for valid input with no authorized decisive signal.
- [Router reads the recorded gate outcome from the report; a forged/misbuilt report could mislead it] → Mitigation: the router verifies the field's presence and membership; a report without a recorded gate outcome is blocked (no routing). Fabricating a conformant report with a false gate result is a pipeline-integrity problem outside the router's authority (the gate evaluation itself remains the authoritative producer of that field).
- [Observability record could accidentally capture document content, signal values, or critical values] → Mitigation: the record contract (Decision 8) restricts content to keys/presence and provenance hashes; a source-inspection and behavioral test asserts no content/value fields are written.
- [Future signal approvals must not disturb the seam] → Mitigation: signals are vocabulary-driven (Decision 4); approving an additional signal is a spec/delta change adding keys to the permitted vocabulary, with no router-shape change.

## Migration Plan

No migration: this change introduces a new seam and a new CLI; no existing behavior, artifact, or stored data is modified. The new capability spec becomes a living spec at archive time (`openspec/specs/domain-router/spec.md`). The `repo-jur` console script is additive; `converter-juridico` and all existing tests remain byte-identical.

## Open Questions

- No blocking open questions remain: HR-1, HR-2, and HR-3 were resolved by human review (2026-08-22) and are incorporated into Decisions 4, 5, 6, and 9.
- Future (non-blocking): (a) whether a future change may approve `legal_hints`-derived deterministic rules and under which key/validation constraints (HR-1 leaves this open for future normative authority); (b) whether the routing-context carrier should gain additional workflow-context fields beyond `requested_domain`; (c) whether a future report-schema change should record the critical-data status so the router can read it from the report instead of a parameter (proposal Residual Risk 3).
