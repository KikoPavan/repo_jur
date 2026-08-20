## Context

Stage 3 established the Shared Conversion Core: `ConversionEngine.convert(evidence_ref, config) -> Phase1Artifacts`, where `Phase1Artifacts` carries literal Markdown plus a serialized, contract-validated technical report (`src/pipeline_juridico/conversion_engine.py`). The FROZEN architecture requires one further seam before the Phase 1 Quality Gate: Post-OCR Critical-Data Validation (`technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §3.6, §8A; `decision-memo-post-ocr-critical-data-validation-seam-v1.1-FROZEN.md`; `implementation-plan-repo-jur-v1.1-FROZEN.md` §6; `phase1-operational-spec-v1.1-FROZEN.md` §"Post-OCR Critical-Data Validation Seam").

This seam is explicitly non-mutating: it never rewrites, autocorrects, completes, or infers content in the literal Markdown body. It only detects and signals inconsistencies in a configurable set of critical identifier-like fields (CPF/CNPJ, process number, matrícula, selo/official identifiers, dates, monetary values, document numbers) using deterministic, specification-backed format and check-digit validation. No such specification is embedded in the FROZEN corpus for any of these fields today, so the correct default implementation is a rule registry that is architecturally capable of holding provenance-complete rules but starts, and in this change remains, empty.

The Stage 4 runtime mechanics are no longer open design questions: `decision-memo-critical-data-validation-runtime-semantics-v1.0-FROZEN.md` (approved 2026-08-20, normative) resolves seven runtime-semantic decisions and adds the Rule Registry Integrity invariant. This design implements those decisions without reopening them. Per Decision 6, only the exact minimal Python representation of a rule, module placement, and rule-registry mechanics remain design choices; this document makes them while preserving every approved constraint.

The repository already contains the exact output shape required by FROZEN §Output: `CriticalValidationStatus`, `CriticalFinding`, and `CriticalValidationResult` in `src/pipeline_juridico/contracts.py:88-104`. These were added ahead of Stage 4 (evidently during earlier contract-harness work) and match the FROZEN interface verbatim; Stage 4 reuses them without modification.

Runtime: the project declares `requires-python = ">=3.12"`, managed with `uv` under `src/pipeline_juridico/`. This change adds no dependency.

## Goals / Non-Goals

**Goals:**

- expose a `CriticalDataValidator.validate(self, phase1_artifacts, profile) -> CriticalValidationResult` matching the FROZEN §3.6 interface exactly;
- reuse the existing `CriticalValidationStatus` / `CriticalFinding` / `CriticalValidationResult` contracts without modification;
- reuse `Phase1Artifacts` from the Shared Conversion Core as the sole conversion-side input, without modifying Stage 3;
- introduce a deterministic registry lifecycle: `CriticalDataValidator` receives the full set of rules at construction, validates required provenance metadata (`rule_id`, `rule_version`, `applies_to`, source/specification reference, `validation_logic_version`, `failure_status`) and unique `rule_id` at that point, stores the validated rules in an immutable internal mapping keyed by `rule_id`, and defaults to an empty registry (Decision 6; Rule Registry Integrity);
- reject invalid required metadata values at construction: a rule declaring a `failure_status` other than `WARNING` or `REVIEW_REQUIRED` (for example `OK`) raises `CriticalValidationConfigurationError` (Decision 2);
- ship the registry with zero pre-populated rules, so the default, FROZEN-compliant behavior is `findings=[]` / `status=OK` (Decision 1);
- implement static severity: each rule declares `failure_status`; the validator never invents severity dynamically and never downgrades (Decisions 2 and 3);
- implement aggregation: the global status is the highest severity produced, with all findings preserved individually (Decision 4);
- implement per-rule candidate discovery: each rule deterministically discovers its own candidates from `Phase1Artifacts`; no universal central extractor (Decision 5);
- type `profile` as a Stage-4-specific Critical Validation Profile (`profile_id`, `profile_version`, `enabled_rule_ids`) that only selects which registered rules are enabled (Decision 7);
- implement Rule Registry Integrity: every `enabled_rule_id` must resolve exactly one registered rule; an unresolvable `enabled_rule_id`, a duplicate `enabled_rule_id` within a profile, or an invalid registry (missing provenance, invalid `failure_status` value, duplicate `rule_id`) raises `CriticalValidationConfigurationError`, never a silent `status=OK`;
- implement rule-scoped detection only: Stage 4 has no general duty to discover ambiguity or conflicting values; only an enabled, specification-backed rule may detect and signal an inconsistency within its own authorized scope (2026-08-20 human review correction);
- prove the non-mutation invariant (`SHA256(markdown_before) == SHA256(markdown_after)`) with an executable test;
- prove domain-neutrality with a source-inspection test mirroring the Stage 3 pattern;
- keep findings entirely inside the technical layer, never inside the literal Markdown body.

**Non-Goals:**

- implementing any concrete normative check-digit/format rule for CPF/CNPJ, process number, matrícula, selo, dates, monetary values, or document numbers;
- implementing intra-document redundant-value consistency comparison (explicit future capability per the decision memo's "Future boundary");
- implementing any general, rule-independent duty to discover ambiguity or conflicting values (inconsistency detection is scoped to enabled, specification-backed rules);
- designing or implementing a universal central candidate extractor (Decision 5 forbids it);
- adding routing, classification, legal-truth, provenance-bypass, or severity-override semantics to the Critical Validation Profile (Decision 7);
- assigning or influencing the Phase 1 Quality Gate (PASS / PASS WITH WARNINGS / FAIL);
- constructing, importing, or referencing `GateState` or `RouteTarget`;
- implementing Domain Router, Legal Knowledge / Judicial Process schemas, Semantic Review, Producers, canonical publication, or retrieval;
- changing the converter, OCR provider, routing thresholds, cleaner, validator, report generation, or CLI;
- adding or changing dependencies.

## Decisions

### 1. Zero-rule registry as the only FROZEN-compliant default

`critical_data.py` will define a deterministic registry lifecycle: `CriticalDataValidator` receives the full set of rules at construction (constructor argument, defaulting to no rules), validates presence of `rule_id`, `rule_version`, `applies_to`, a source/specification reference, `validation_logic_version`, and `failure_status` plus uniqueness of `rule_id` at that point, rejecting any rule missing one of these fields, declaring a `failure_status` other than `WARNING` or `REVIEW_REQUIRED` (for example `OK`), or duplicating a `rule_id`, and stores the validated rules in an immutable internal mapping keyed by `rule_id`. The registry shipped by this change contains no registered rules.

`status=OK` / `findings=[]` is the legitimate zero-rule outcome (Decision 1): it asserts only that no inconsistency was detected by applicable rules executed in this run — not complete validation, authenticity, legal correctness, legal verification, or that every candidate field was checked.

**Rationale:** the decision memo and §8A both state a rule "may be implemented only when supported by a reliable, versioned technical or normative specification appropriate to that identifier," and no FROZEN source supplies one for any candidate field. `legal-okf-profile-v1.3-FROZEN.md` §4.1 is the closest candidate (CNJ process-number mask) but is explicitly soft ("preferencialmente"), carries a dangling external citation `[206]`, and belongs to a domain profile this domain-neutral seam must not couple to. Populating even one rule from it would violate the anti-generalization rule by promoting a soft, domain-scoped convention to a hard, domain-neutral architectural rule. Decision 1 confirms `OK` does not assert completeness, so an empty registry is not a correctness gap.

**Alternative considered:** implement the CNJ process-number mask as a first rule, citing `legal-okf-profile-v1.3-FROZEN.md` §4.1.

**Rejected because:** the mask is non-mandatory in its own source ("preferencialmente"), its own citation `[206]` is dangling within the FROZEN corpus, and it is a Legal Knowledge domain-profile concern, not a Stage 4 architectural contract — coupling Stage 4 to it would be a premature domain dependency.

**Alternative considered:** leave the registry mechanism unimplemented until a first real rule exists.

**Rejected because:** the provenance-governance mechanism itself is required scaffolding independent of whether any rule currently satisfies it, and FROZEN acceptance criteria #29/#30 require the seam to exist and be tested now, ahead of Stage 5.

### 2. Rule interface: the six required declarations and the canonical applicability field (Decision 6)

Each rule must declare, in its versioned definition: `rule_id`, `rule_version`, `applies_to`, a source/specification reference, `validation_logic_version`, and `failure_status`. `applies_to` is this design's canonical concrete name for the single conceptual applicability field of Decision 6. The FROZEN corpus carries that one conceptual field under two names (`applies_to` in the seam memo, `identifier_type` in the implementation plan; omitted by tech spec §8A); Decision 6 fixes it as one conceptual applicability field — not two runtime aliases, not an either-or choice between two fields — and leaves the canonical concrete field name as an OpenSpec design choice. This design chooses `applies_to` (the seam memo's name, from the primary authority for this seam) and records that choice here.

A rule receives `Phase1Artifacts` read-only, discovers/evaluates only candidates authorized by its specification, and returns zero or more `CriticalFinding` objects. A rule must not mutate `Phase1Artifacts` or Markdown; construct `GateState` or `RouteTarget`; route; publish; or perform Semantic Review (Decision 6).

**Minimal Python representation (design choice, preserving Decision 6 constraints):** a frozen dataclass `CriticalValidationRule`:

```python
@dataclass(frozen=True)
class CriticalValidationRule:
    rule_id: str
    rule_version: str
    applies_to: str            # single conceptual applicability field (Decision 6)
    source: str                # source/specification reference
    validation_logic_version: str
    failure_status: CriticalValidationStatus  # WARNING or REVIEW_REQUIRED (Decision 2)
    evaluate: Callable[[Phase1Artifacts], list[CriticalFinding]]  # read-only, spec-scoped
```

`evaluate` is the rule's deterministic candidate-discovery and evaluation entry point: it discovers the rule's own candidates from `Phase1Artifacts` and returns findings for the ones its specification authorizes it to evaluate. The validator treats it as read-only; the rule implementation itself is prohibited from mutating `Phase1Artifacts` or Markdown (Decision 6).

**Rationale:** the memo explicitly delegates the exact minimal Python representation to OpenSpec design while preserving the constraints; this shape is the smallest one that carries the six required declarations and the read-only, spec-scoped evaluation entry point.

**Alternative considered:** a `Protocol`-based structural interface instead of a dataclass.

**Rejected because:** a frozen dataclass makes the six required declarations structurally mandatory at construction time (the registry rejects a rule missing any field without inspecting behavior), which is the point of Decision 6's provenance requirement; a Protocol would defer enforcement to runtime evaluation.

### 3. Rule severity is static and never downgraded (Decisions 2 and 3)

`failure_status` belongs to the versioned rule definition and is `WARNING` or `REVIEW_REQUIRED`; any other value (for example `OK`) is invalid required metadata and is rejected at validator construction with `CriticalValidationConfigurationError`. The validator must not invent severity dynamically. Severity is ordered `OK < WARNING < REVIEW_REQUIRED`, and the validator must never return a status lower than the declared `failure_status` of a finding it reports.

**Rationale:** Decisions 2 and 3 close the outcome-menu ambiguity of tech spec §8A: severity is provenance data, not runtime judgment.

**Alternative considered:** a heuristic that escalates `WARNING` findings to `REVIEW_REQUIRED` when multiple warnings accumulate.

**Rejected because:** Decision 3 forbids any behavior that implies dynamic severity or downgrade; aggregation is specified exactly by Decision 4 and nothing may be layered on top.

### 4. Aggregation: highest severity wins, all findings preserved (Decision 4)

The validator computes the global status as the highest severity produced by the findings of the enabled rules executed in this run: zero findings ⇒ `OK`; only `WARNING` findings ⇒ `WARNING`; any `REVIEW_REQUIRED` finding ⇒ `REVIEW_REQUIRED`. Every finding is preserved individually in `CriticalValidationResult.findings`.

**Rationale:** Decision 4 is the only aggregation rule; it is directly compatible with the single-`status`/array-`findings` output shape in the seam memo and with `CriticalValidationResult(status=..., findings=[...])`.

**Alternative considered:** aggregating by rule rather than by finding (one status per rule, then combining).

**Rejected because:** the FROZEN output shape is a single `status` plus a findings array; Decision 4's "highest severity produced" is defined over findings, and per-rule intermediate statuses are not part of the approved contract.

### 5. Candidate discovery is per-rule, read-only (Decision 5)

No universal central extractor is authorized. Each rule deterministically discovers its own candidates from `Phase1Artifacts` (via its `evaluate` entry point, scoped by `applies_to` and its own specification). Candidate-discovery logic belongs to that rule's implementation/version/provenance and is read-only: it must not infer, repair, complete, silently normalize, or modify literal Markdown.

**Rationale:** Decision 5 forecloses the central-extractor reading that the seam memo's "Candidate fields" list left ambiguous, and reinforces the anti-generalization rule: discovery is specification-scoped, never a shared schema.

**Alternative considered:** a shared `extract_candidates(phase1_artifacts, identifier_type)` helper used by all rules.

**Rejected because:** Decision 5 explicitly forbids a universal central extractor; a shared extractor would become exactly the coupling the decision prohibits.

### 6. `profile` is a Critical Validation Profile (Decision 7)

`CriticalDataValidator.validate(self, phase1_artifacts, profile)` accepts a Stage-4-specific Critical Validation Profile — not the Legal OKF Profile and not a Judicial Process profile. Minimal shape (frozen dataclass):

```python
@dataclass(frozen=True)
class CriticalValidationProfile:
    profile_id: str
    profile_version: str
    enabled_rule_ids: tuple[str, ...]
```

The profile only selects which registered rules are enabled. It must not route domains, classify semantically, define legal truth, bypass provenance, or override rule `failure_status`. `enabled_rule_ids` must not contain duplicates: a profile listing the same `rule_id` more than once is a configuration error (`CriticalValidationConfigurationError`) raised by profile resolution before any rule executes, preventing duplicate rule execution and duplicate findings.

**Rationale:** Decision 7 types the previously-untyped §3.6 parameter in the way the FROZEN domain-neutrality rule requires; `enabled_rule_ids` is the only behavioral input, keeping the profile a pure selector.

**Alternative considered:** treating `profile` as the Legal OKF Profile (`legal-okf-profile-v1.3-FROZEN.md`).

**Rejected because:** Decision 7 explicitly excludes it, and `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md` *Prohibited Coupling* forbids coupling domain profiles into the domain-neutral core.

### 7. Rule Registry Integrity (Rule Registry Integrity invariant)

Within one validation run, the registry may contain at most one registered version for each `rule_id`; duplicate `rule_id` registrations are invalid and rejected at validator construction. Every `enabled_rule_id` in the `CriticalValidationProfile` must resolve exactly one registered rule; a profile `enabled_rule_id` that fails to resolve is a configuration error raised as `CriticalValidationConfigurationError`, never silently converted to `status=OK`. A profile that lists the same `enabled_rule_id` more than once is likewise a configuration error (`CriticalValidationConfigurationError`) raised by profile resolution before any rule executes.

This is distinct from Decision 1: a profile with zero `enabled_rule_ids` (a legitimate zero-rule profile) yields `status=OK`, `findings=[]`; a profile that names a rule which does not exist is a configuration error (`CriticalValidationConfigurationError`), never a silent `OK`.

**Rationale:** the invariant closes the registry-integrity and profile-resolution edge cases left open by the seven decisions, and preserves the epistemic honesty of Decision 1: `OK` must never be produced by swallowing a misconfiguration.

**Alternative considered:** ignoring unresolvable `enabled_rule_id` values and continuing with the resolvable ones.

**Rejected because:** the invariant explicitly forbids silent conversion to `OK`; failing fast as a configuration error is the only conformant behavior.

### 8. Domain-neutrality enforced by source inspection, mirroring Stage 3

A test will read `src/pipeline_juridico/critical_data.py` as text and assert the strings `GateState` and `RouteTarget` never appear, mirroring `tests/test_conversion_engine.py:298-306` (`test_facade_source_avoids_downstream_domain_types`). `CriticalValidationResult`/`CriticalValidationStatus`/`CriticalFinding` are expected and excluded from this check since they are the module's own reused output contract.

**Rationale:** proves at the source level, not just by unit-testing observable behavior, that Stage 4 cannot construct a Quality Gate or routing decision — consistent with the "Stage 4 must remain domain-neutral" requirement and the Stage 3 precedent for enforcing this class of boundary.

### 9. Non-mutation proven by hash equality across the call boundary

A test will compute `SHA256` of `phase1_artifacts.markdown` before calling `validate()` and again after, for representative artifacts (rule-free path, and — if any test-only rule is registered purely for test purposes — a path that produces `WARNING`/`REVIEW_REQUIRED` findings), and assert equality in every case.

**Rationale:** directly implements the FROZEN "Teste invariável" (`implementation-plan-repo-jur-v1.1-FROZEN.md` §6): `SHA256(markdown_before) == SHA256(markdown_after)`.

### 10. Findings never appear in the literal Markdown body

Because `validate()` never returns or mutates a `Phase1Artifacts`, and `CriticalFinding` objects live only inside `CriticalValidationResult`, there is no code path by which a finding can reach the Markdown body. A test will assert that no substring of any finding's `message` or `code` appears in `phase1_artifacts.markdown` for a scenario with a test-only rule producing findings.

**Rationale:** directly implements FROZEN §8A "Findings remain outside literal Markdown" and the Stage 4 output boundary (`{status, findings}` only).

### 11. No coupling to Stage 5 Quality Gate or Stage 6 Domain Router

`critical_data.py` does not construct, import, or branch on `GateState` or `RouteTarget`. `CriticalValidationResult.status` is returned as data; this change does not implement any function that maps `CriticalValidationStatus` to `GateState` or to a routing decision — that mapping and the independence rule ("physical = PASS, critical = REVIEW_REQUIRED ⇒ downstream review_required, not FAIL") belong to Stage 5 and are explicitly out of scope here.

**Rationale:** matches `implementation-plan-repo-jur-v1.1-FROZEN.md` §7 "Independence" and keeps Stage 4 a pure detect-and-signal seam.

### 12. Registry lifecycle is deterministic and immutable (2026-08-20 human review correction)

`CriticalDataValidator` receives the full set of rules at construction (`CriticalDataValidator(rules: Iterable[CriticalValidationRule] = ())`). Construction validates required provenance and unique `rule_id` for every supplied rule, then stores the validated rules in an immutable internal mapping keyed by `rule_id` (e.g. `types.MappingProxyType` over an ordinary `dict`). Construction with no rules yields an empty registry. After construction the registry cannot be added to, removed from, or replaced; there is no public registration method on the validator.

**Rationale:** the human review (2026-08-20) requires the lifecycle to be deterministic: rules arrive at construction, are validated then, and the registry is immutable thereafter. This makes the registry state a function of construction alone, so Rule Registry Integrity cannot be violated by later mutation, and the validator can safely be shared across runs.

**Alternative considered:** a mutable registry with a public `register()` method, rules added incrementally after construction.

**Rejected because:** a mutable registry would allow post-construction mutation, making registry state dependent on call order and reopening the duplicate-`rule_id` window the review asked to close; construction-time validation with an immutable mapping removes that window entirely.

### 13. `CriticalValidationConfigurationError` is the explicit configuration-error contract (2026-08-20 human review correction)

`critical_data.py` defines `CriticalValidationConfigurationError(Exception)` as the single, explicit contract for invalid registry or profile resolution. It is raised exactly when: (a) a rule supplied at construction is missing required provenance (one of the six Decision-6 fields); (b) a rule supplied at construction declares an invalid required metadata value — specifically a `failure_status` other than `WARNING` or `REVIEW_REQUIRED` (for example `OK`); (c) rules supplied at construction include a duplicate `rule_id`; (d) a `CriticalValidationProfile.enabled_rule_id` does not resolve to exactly one registered rule; or (e) a `CriticalValidationProfile.enabled_rule_ids` contains a duplicate rule identifier. It is never caught or converted into a result — in particular never into `status=OK` — and it is not raised for the legitimate zero-rule case (Decision 1).

**Rationale:** the human review (2026-08-20) asks for the configuration-error path to be an explicit named contract rather than an implicit behavior, so callers can distinguish misconfiguration (error) from a legitimate zero-rule run (`OK`) and so the invariant is testable by name.

**Alternative considered:** reusing a generic built-in exception (e.g. `ValueError`) for all invalid-registry/profile cases.

**Rejected because:** a generic exception does not make the configuration-error contract explicit or distinguishable from unrelated programming errors; the named contract is what the review requires.

### 14. No general duty to discover ambiguity or conflicting values (2026-08-20 human review correction)

Stage 4 has no general duty to discover ambiguity or conflicting values in the converted content. Detection and signaling occur only through an enabled, specification-backed rule acting within its own authorized scope. The FROZEN "no silent choice between conflicting values" prohibition remains a rule-level behavior constraint — when a rule does signal an inconsistency, the validator must not silently choose a value and must represent the signal only via `WARNING` / `REVIEW_REQUIRED` escalation with a finding. Absent an enabled rule authorized for a field, validation performs no ambiguity/conflict detection for it, and the absence of a finding does not assert that no ambiguity exists. Intra-document redundant-value comparison remains a separate future capability (Decision memo "Future boundary").

**Rationale:** the human review (2026-08-20) clarifies that "no silent choice" is a prohibition on resolution behavior, not a mandate to actively scan for conflicts; a general scanning duty would duplicate the redundant-value comparison capability that FROZEN explicitly defers, and would push Stage 4 beyond detect-and-signal into inference.

**Alternative considered:** a validator-level cross-field scan that flags any field whose value appears more than once with different values (a general conflict-detection duty).

**Rejected because:** it would reintroduce the redundant-value comparison explicitly deferred by the seam memo ("Future boundary") and would give Stage 4 a detection duty independent of any registered rule's specification, which the review forbids.

## Risks / Trade-offs

- **[Risk] A future contributor could be tempted to hardcode a "reasonable-looking" CPF/CNPJ or CNJ check-digit rule without a cited specification.**
  → Mitigation: validator construction rejects any rule lacking full provenance metadata (including `failure_status`) or duplicating a `rule_id` (structural enforcement, not just review discipline); the domain-neutrality and non-mutation tests do not depend on any rule being registered, so they stay green whether or not rules are ever added.

- **[Risk] The zero-rule default could be mistaken for "the feature is unfinished" rather than "this is the FROZEN-correct state absent a specification."**
  → Mitigation: `proposal.md` documents this explicitly as the default-safe FROZEN-compliant state (Decision 1: `OK` asserts only that no inconsistency was detected), and this design records why the one near-candidate rule (CNJ mask) was deliberately not implemented.

- **[Risk] A future contributor could treat an unresolvable `enabled_rule_id` as "no rules ⇒ OK" and silently swallow a misconfiguration.**
  → Mitigation: Decision 7 + Rule Registry Integrity make the distinction normative; the implementation raises `CriticalValidationConfigurationError` for unresolvable `enabled_rule_id` values (and for invalid registry construction), and a test asserts it is never silently converted to `status=OK`.

- **[Risk] A future contributor could introduce a central candidate extractor to "share" discovery logic.**
  → Mitigation: Decision 5 forbids a universal central extractor; per-rule discovery is enforced by design (each rule's `evaluate` owns its discovery) and documented in Decision 5 above.

- **[Risk] A future contributor could add a heuristic that escalates or downgrades severities.**
  → Mitigation: Decisions 2 and 3 fix severity as declared, ordered, and non-downgradable; tests cover the no-downgrade property.

- **[Trade-off] Reading `phase1_artifacts.report_json` inside `validate()` requires `json.loads`, coupling Stage 4 to the existing technical-report JSON shape.**
  → Mitigation: no existing report field is renamed, removed, or reinterpreted; Stage 4 only reads it, matching the REUSE decision for `report.py`/`validator.py`'s Technical JSON schema.

## Migration Plan

1. Add tests for the Stage 4 contract before implementation (TDD, red first): construction-time registry lifecycle (six provenance fields including `failure_status`, invalid-`failure_status`-value rejection, duplicate-`rule_id` rejection, empty default), `CriticalValidationConfigurationError` contract (missing provenance, invalid `failure_status` value, duplicate `rule_id`, unresolvable `enabled_rule_id`, duplicate profile `enabled_rule_ids`), zero-rule default (`OK`/`findings=[]`), profile-based rule selection, severity no-downgrade, highest-severity aggregation, non-mutation invariant, findings-outside-Markdown invariant, rule-scoped detection (no general ambiguity/conflict duty), domain-neutrality source inspection.
2. Add `src/pipeline_juridico/critical_data.py` with the rule/profile/error representations (`CriticalValidationRule`, `CriticalValidationProfile`, `CriticalValidationConfigurationError`) and `CriticalDataValidator` (construction-time registry validation into an immutable `rule_id`-keyed mapping, profile resolution, per-rule evaluation, highest-severity aggregation), reusing `CriticalValidationStatus` / `CriticalFinding` / `CriticalValidationResult` from `contracts.py` and `Phase1Artifacts` from `conversion_engine.py` without modification.
3. Run focused Stage 4 tests.
4. Run the full existing regression suite to prove no behavioral change to Stage 1-3.
5. Run OpenSpec strict validation.
6. Do not modify or publish `repo_jur/bundle/`.

Rollback is limited to removal of the new `critical_data.py` module and its tests; no other module is touched by this change.

## Open Questions

No blocking architectural question remains for Stage 4. The runtime-semantics memo resolves 7/7 blockers and adds the Rule Registry Integrity invariant. This design makes the two remaining design choices the memo explicitly delegates: the canonical concrete name of the single applicability field (Decision 6) — chosen as `applies_to` — and the minimal Python representation of a rule — chosen as the frozen `CriticalValidationRule` dataclass with `evaluate`. The 2026-08-20 human review corrections are encoded as Decisions 12 (deterministic immutable registry lifecycle), 13 (`CriticalValidationConfigurationError` contract), and 14 (rule-scoped detection, no general ambiguity/conflict duty). The 2026-08-20 final human review corrections are encoded within Decisions 3 and 13 (a `failure_status` other than `WARNING` or `REVIEW_REQUIRED` is invalid required metadata rejected at construction) and Decisions 6, 7, and 13 (duplicate `enabled_rule_ids` within a profile are a configuration error raised before any rule executes). The two residual gaps recorded in `proposal.md` (no embedded normative specification for any candidate identifier; missing §16.1 test-category entry) are FROZEN-corpus gaps, not open Stage 4 design questions, and are not resolved by invention in this change.
