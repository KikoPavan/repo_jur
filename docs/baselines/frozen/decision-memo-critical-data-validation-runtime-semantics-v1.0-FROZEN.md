# DECISION MEMO — STAGE 4 CRITICAL-DATA VALIDATION RUNTIME SEMANTICS

**Versão:** 1.0
**Data:** 20 de agosto de 2026
**Status:** APPROVED — FROZEN — STAGE 4 BASELINE (accepted as normative by human review 2026-08-20)
**Supersedes:** none (new memo)
**References:**

- `decision-memo-post-ocr-critical-data-validation-seam-v1.1-FROZEN.md`
- `technical-implementation-spec-repo-jur-v1.2-FROZEN.md`
- `implementation-plan-repo-jur-v1.1-FROZEN.md`
- `phase1-operational-spec-v1.1-FROZEN.md`
- `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`
- `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md`
- `decision-memo-physical-layout-logical-capability-mapping-v1.0-FROZEN.md`
- `legal-okf-profile-v1.3-FROZEN.md`
- `arquitetura-fase2-repo-jur-v15-FROZEN.md`

---

## 1. Problem Statement

Stage 4 (Post-OCR Critical-Data Validation Seam) planning was blocked because the Stage 4 re-audit identified seven runtime-semantic decisions that the existing FROZEN corpus left open:

1. What `status=OK` / `findings=[]` actually asserts (zero-rules/zero-findings semantics).
2. Whether `WARNING` vs `REVIEW_REQUIRED` is chosen dynamically by the validator or declared statically by each rule.
3. Whether the three severities form an ordered scale, and whether a rule's declared severity can be downgraded.
4. How the global `CriticalValidationResult.status` is computed when multiple findings of different severities exist.
5. Whether candidate-field discovery is centralized (a shared extractor) or delegated to each rule.
6. What a rule implementation must minimally declare and is forbidden from doing.
7. What the `profile` argument of `CriticalDataValidator.validate(self, phase1_artifacts, profile)` actually is.

The existing FROZEN authorities (the seam memo, tech spec §3.6/§8A, the implementation plan's Stage 4 section) establish the seam's non-mutating boundary and its allowed outcomes, but do not resolve these seven runtime-mechanics questions. Without them, OpenSpec design for Stage 4 could not proceed without inventing behavior — which is prohibited by the corpus's anti-generalization and no-new-architectural-decision rules.

A human architectural decision, issued 2026-08-20 (board card t_0b27302d, superseding an earlier truncated comment in full), resolves all seven. This memo records those decisions, reconciles them against the FROZEN corpus, checks for contradictions, and states whether Stage 4 planning is now unblocked.

---

## 2. Approved Decisions 1–7

Each decision below is normative text as approved, labelled **[HUMAN DECISION 2026-08-20]**, source: board card t_0b27302d human comment (superseding the earlier truncated comment in full).

### Decision 1 — Zero Rules / Zero Findings

**[HUMAN DECISION 2026-08-20]**

`status=OK` and `findings=[]`.

`OK` means only: no inconsistency was detected by applicable rules executed in this run. `OK` does **not** mean complete validation, authenticity, legal correctness, legal verification, or that every candidate field was checked.

### Decision 2 — WARNING vs REVIEW_REQUIRED

**[HUMAN DECISION 2026-08-20]**

Each registered rule declaratively defines `failure_status` as `WARNING` or `REVIEW_REQUIRED`. The validator must not invent severity dynamically. `failure_status` belongs to the versioned rule definition.

### Decision 3 — Severity Order

**[HUMAN DECISION 2026-08-20]**

`OK < WARNING < REVIEW_REQUIRED`. The validator must never downgrade a rule's declared `failure_status`.

### Decision 4 — Aggregation

**[HUMAN DECISION 2026-08-20]**

Global status is the highest severity produced:

- zero findings ⇒ `OK`
- `WARNING` finding(s), no `REVIEW_REQUIRED` ⇒ `WARNING`
- any `REVIEW_REQUIRED` finding ⇒ `REVIEW_REQUIRED`

All findings remain preserved individually.

### Decision 5 — Candidate Discovery

**[HUMAN DECISION 2026-08-20]**

No universal central extractor is authorized. Each rule deterministically discovers its own candidates from `Phase1Artifacts`. Candidate-discovery logic belongs to that rule's implementation/version/provenance and is read-only. It must not infer, repair, complete, silently normalize, or modify literal Markdown.

### Decision 6 — Rule Interface

**[HUMAN DECISION 2026-08-20]**

Each rule must declare at least:

```text
rule_id
rule_version
applies_to / identifier_type
source/specification
validation_logic_version
failure_status
```

`applies_to / identifier_type` denotes one conceptual applicability field, not two runtime aliases and not an either-or choice between two fields. The canonical concrete field name is deliberately left as an OpenSpec design choice (see below).

A rule receives `Phase1Artifacts` read-only, discovers/evaluates only candidates authorized by its specification, and returns zero or more `CriticalFinding` objects. A rule must not mutate `Phase1Artifacts` or Markdown; construct `GateState` or `RouteTarget`; route; publish; or perform Semantic Review. The exact minimal Python representation may be decided in OpenSpec design while preserving these constraints.

### Decision 7 — Profile

**[HUMAN DECISION 2026-08-20]**

The `profile` argument of `CriticalDataValidator.validate(self, phase1_artifacts, profile)` is a Stage-4-specific **Critical Validation Profile**, not the Legal OKF Profile and not a Judicial Process profile.

Minimum responsibilities/fields:

```text
profile_id
profile_version
enabled_rule_ids
```

It only selects which registered rules are enabled. It must not route domains, classify semantically, define legal truth, bypass provenance, or override rule `failure_status`.

### Rule Registry Integrity

**[HUMAN REVIEW 2026-08-20 — CHANGES_REQUIRED]**

Within one validation run, the registry may contain at most one registered version for each `rule_id`; duplicate `rule_id` registrations are invalid.

Every `enabled_rule_id` in `CriticalValidationProfile` must resolve exactly one registered rule.

A missing `enabled_rule_id` is a configuration error and must never be silently converted to `status=OK`.

This invariant is distinct from Decision 1. Decision 1 governs the case where no rule is applicable or enabled (a legitimate zero-rule profile ⇒ `status=OK`, `findings=[]`). This invariant governs the case where the profile configures an `enabled_rule_id` that does not resolve to exactly one registered rule — that is a configuration error, never a silent `OK`.

---

## 3. Unchanged Invariants

The following invariants are explicitly unchanged by the seven decisions above, each already stated in the cited FROZEN authority:

| Invariant | FROZEN source |
|---|---|
| Stage 4 remains non-mutating detect-and-signal | Seam memo — *Decision*; tech spec §3.6 ("It never mutates `text_content`"); impl plan §6 *Objetivo* |
| `SHA256(markdown_before) == SHA256(markdown_after)` | Impl plan §6 *Teste invariável* |
| Findings stay outside literal Markdown | Tech spec §8A ("Findings remain outside literal Markdown"); Phase1 operational spec §0A *Post-OCR Critical-Data Validation Seam* |
| No OCR autocorrection or inferred completion | Seam memo — *Behavior: Forbidden*; impl plan §6 *Forbidden* |
| No silent choice between conflicting values | Seam memo — *Behavior: Forbidden* ("choosing silently between conflicting values"); impl plan §6 *Forbidden* ("escolher valor") |
| Formal validity is not legal truth | Seam memo — *Behavior: Forbidden* ("promoting a format-valid value to legal truth"); impl plan §6 *Forbidden* ("converter 'válido formalmente' em 'verdade jurídica'") |
| Redundant-value comparison remains out of scope | Seam memo — *Future boundary*; tech spec §8A; impl plan §6 *Future boundary* |
| Stage 4 remains independent from Stage 5 Quality Gate | Impl plan §7 *Independence* (`physical = PASS`, `critical = REVIEW_REQUIRED` ⇒ downstream `review_required`, not `FAIL`); decision-memo-phase1-quality-gate-v1.0-FROZEN §1 |
| Stage 4 remains domain-neutral and separate from Stage 6 Router | Tech spec §8B (only PASS/PASS WITH WARNINGS may enter routing; routing does not alter Phase 1 body); shared-conversion-core memo — *Prohibited Coupling* |
| No `/bundle/` publication | Tech spec §9.1 (Producer-only publication authority); shared-conversion-core memo — *Invariants* #7 |
| No converter/OCR/provider/routing/dependency changes | Tech spec §19 *Implementation Choices*; §20.2 *Non-Goals* |

---

## 4. Reconciliation with FROZEN Authorities

### Decision 1 — Zero-rule/zero-findings semantics

The seam memo's *Output* section already gives the exact wire shape (`{"status": "OK|WARNING|REVIEW_REQUIRED", "findings": []}`) without defining what `OK` asserts epistemically. Decision 1's explicit disclaimer ("`OK` does NOT mean complete validation, authenticity, legal correctness...") is **NEW normative content**: it closes a gap the corpus left open, and it is consistent with the corpus's general posture that formal validity ≠ legal truth (seam memo *Behavior: Forbidden*) and that the Quality Gate itself "não avalia mérito jurídico" (decision-memo-phase1-quality-gate-v1.0-FROZEN §1). No FROZEN text asserts the opposite (that `OK` implies completeness or legal correctness), so this is a clarifying addition, not a reversal.

### Decision 2/3 — Severity vs aggregation

Tech spec §8A lists "Allowed outcomes: `OK`, `WARNING`, `REVIEW_REQUIRED`" as a menu without specifying who assigns severity to a given rule or whether it forms an ordered scale. The seam memo's *Rule provenance requirement* enumerates required rule metadata (`rule_id`, `rule_version`, `applies_to`, `source/specification reference`, `validation logic version`) but does **not** include a severity field. Decision 2 (`failure_status` declared per-rule, static, not invented at runtime) and Decision 3 (ordered severity, no downgrade) are **NEW normative content** that extends the rule metadata schema — formalized structurally by Decision 6. Nothing in the FROZEN corpus assigned severity dynamically or asserted an unordered/flat outcome model, so this addition does not contradict prior text; it fills the gap the outcome menu left open.

### Decision 4 — Aggregation

No FROZEN authority previously specified how multiple findings combine into a single `CriticalValidationResult.status`. Decision 4's "highest severity wins, all findings preserved individually" is **NEW normative content**, directly compatible with the single-result `Output` shape in the seam memo (one `status`, one `findings` array) and with impl plan §6's interface `CriticalValidationResult(status=..., findings=[...])`.

### Decision 5 — Candidate discovery vs "Candidate fields"

The seam memo's *Candidate fields* section lists "Configurable examples" (CPF/CNPJ, process number, matrícula, selo/official identifiers, dates, monetary values, document numbers) without specifying a discovery mechanism. Decision 5's "no universal central extractor authorized; each rule discovers its own candidates" is **NEW normative content**, but it does not contradict the seam memo: the memo never mandated a shared extractor, and the *Anti-generalization rule* ("never infer a universal format/length rule from one observed document... local convention without authoritative specification") is naturally read as reinforcing per-rule, specification-scoped discovery rather than a shared/central one. Decision 5 forecloses an implementation reading (central extractor) that the corpus left ambiguous; it does not reverse anything FROZEN.

### Decision 6 — Rule interface

Decision 6 merges and extends three partially divergent FROZEN metadata lists:

- Seam memo *Rule provenance requirement*: `rule_id`, `rule_version`, `applies_to`, `source/specification reference`, `validation logic version`.
- Impl plan §6 *Rule registry*: `rule_id`, `rule_version`, `identifier_type`, `source/specification`, `validation_logic_version`.
- Tech spec §8A rule-metadata list: `rule_id`, `rule_version`, `source/specification`, `validation_logic_version` (omits `applies_to`/`identifier_type` entirely).

Decision 6's field list (`rule_id`, `rule_version`, `applies_to / identifier_type`, `source/specification`, `validation_logic_version`, `failure_status`) is a **[HUMAN DECISION] normative addition** that (a) names one conceptual applicability field — carried under two names in the FROZEN corpus (`applies_to` in the seam memo, `identifier_type` in the implementation plan; omitted entirely by tech spec §8A) — and fixes it as a single conceptual field whose canonical concrete field name is left as an OpenSpec design choice, explicitly resolving the tech spec §8A omission rather than leaving it ambiguous, and (b) adds `failure_status` per Decision 2. The behavioral constraints on a rule (read-only `Phase1Artifacts`, no mutation, no `GateState`/`RouteTarget` construction, no routing, no publication, no Semantic Review) are **NEW normative content** at the individual-rule granularity, but they are a direct specialization of already-FROZEN seam-level and stage-level boundaries: tech spec §3.6 ("It never mutates `text_content`"), tech spec §8B (routing is a separate stage, occurs only after the Quality Gate), and decision-memo-phase1-quality-gate-v1.0-FROZEN §1 (Quality Gate, not Critical-Data Validation, decides gate state) and impl plan §7 (Stage 4 output is independent of Stage 5 Quality Gate state construction). No contradiction; Decision 6 pushes an existing seam-level prohibition down to rule-level granularity, which the "exact minimal Python representation may be decided in OpenSpec design" clause explicitly leaves as an implementation-design question, not a new architectural question.

### Decision 7 — Profile

Tech spec §3.6 already declares the `CriticalDataValidator.validate(self, phase1_artifacts, profile)` signature but leaves `profile`'s type undefined. Decision 7 types it as a Stage-4-specific Critical Validation Profile with `profile_id`, `profile_version`, `enabled_rule_ids`, and explicitly excludes it from being the Legal OKF Profile or a Judicial Process profile. This directly reconciles with:

- `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md` — *Prohibited Coupling*, which forbids coupling domain-specific YAML schemas/semantic extraction schemas/domain classifications into the shared, domain-neutral core;
- `legal-okf-profile-v1.3-FROZEN.md` §4.1 `repo_jur_processo_numero`, which shows the Legal OKF Profile is a **domain profile** (jurisprudence-specific fields, producer-owned, bundle-bound) — structurally incompatible with a domain-neutral seam that runs before domain routing (tech spec §8B: only Phase 1 results with PASS/PASS WITH WARNINGS enter routing; Critical-Data Validation runs inside the Shared Conversion Core, upstream of the Domain Router per arquitetura-fase2 §1 pipeline diagram and §1.1).

Decision 7 is **NEW normative content** (the profile's shape was previously unspecified) but is fully consistent with, and required by, the domain-neutrality invariant already FROZEN for the Shared Conversion Core.

### Rule Registry Integrity

The three FROZEN authorities that define rule/profile metadata were each re-read for this reconciliation:

- Seam memo *Rule provenance requirement* (`rule_id`, `rule_version`, `applies_to`, `source/specification reference`, `validation logic version`);
- Implementation plan §6 *Rule registry* (`rule_id`, `rule_version`, `identifier_type`, `source/specification`, `validation_logic_version`);
- Tech spec §8A rule-metadata list (`rule_id`, `rule_version`, `source/specification`, `validation_logic_version`).

None of the three defines registry uniqueness per `rule_id`, or specifies how an `enabled_rule_id` that fails to resolve to exactly one registered rule must be handled. The Rule Registry Integrity invariant is therefore **NEW normative content**, gap-filling rather than reversing: it is consistent with, and a direct extension of, the *Rule provenance requirement*'s premise that each rule is a distinct, versioned, identifiable unit, and it does not alter Decision 1 or Decision 7 — it only forecloses a silent-`OK` implementation reading that neither decision addressed.

### Stage 5 / Stage 6 separation

All seven decisions preserve the FROZEN separation of Stage 4 from Stage 5 (Quality Gate) and Stage 6 (Domain Router): tech spec §8B (routing occurs only after the gate, on PASS/PASS WITH WARNINGS results, and does not alter the Phase 1 body), decision-memo-phase1-quality-gate-v1.0-FROZEN §1 (gate evaluates physical conversion quality, not legal merit, and does not decide identity/routing), and impl plan §7 *Independence* (critical-data status and gate state are distinct; `REVIEW_REQUIRED` routes downstream to `review_required`, not to gate `FAIL`). Decision 6's explicit rule-level prohibition on constructing `GateState`/`RouteTarget` or performing routing/publication/Semantic Review is a direct, non-contradictory reinforcement of this existing separation.

---

## 5. Contradiction Analysis

**None of the seven decisions contradicts any FROZEN authority.**

Per decision:

1. **Zero rules/zero findings** — clarifies what `OK` does not mean; no FROZEN text claims `OK` implies completeness or legal truth. No contradiction.
2. **WARNING vs REVIEW_REQUIRED** — no FROZEN text specifies dynamic severity assignment; static, per-rule declaration is a gap-filling addition. No contradiction.
3. **Severity order** — no FROZEN text asserts a flat/unordered outcome model or permits downgrading; ordering and no-downgrade are additions, not reversals. No contradiction.
4. **Aggregation** — no FROZEN text specifies an aggregation rule; "highest severity wins, all findings preserved" is consistent with the single-`status`/array-`findings` Output shape already FROZEN. No contradiction.
5. **Candidate discovery** — no FROZEN text mandates a central extractor; per-rule discovery is compatible with the *Anti-generalization rule* and *Candidate fields* being described as "configurable examples" rather than a shared schema. No contradiction.
6. **Rule interface** — extends, rather than overrides, three overlapping FROZEN metadata lists; rule-level behavioral prohibitions specialize already-FROZEN seam-level and stage-separation invariants. No contradiction.
7. **Profile** — types a previously-untyped parameter in a way required by the already-FROZEN domain-neutrality/Prohibited Coupling rule. No contradiction.
8. **Rule Registry Integrity** — no FROZEN text specifies registry uniqueness per `rule_id` or `enabled_rule_id` resolution; this is a gap-filling addition, consistent with the *Rule provenance requirement* and with Decisions 1 and 7. No contradiction.

**Observations (not contradictions) — minor corpus inconsistencies:**

- Tech spec §8A's rule-metadata list omits the applicability field, while the seam memo (`applies_to`) and the implementation plan (`identifier_type`) both include it, under different names. The FROZEN corpus thus names one conceptual applicability field under two names (`applies_to` in the seam memo, `identifier_type` in the implementation plan; omitted by tech spec §8A). Decision 6 resolves this by defining it as a single conceptual applicability field — not two runtime aliases, not an either-or choice — whose canonical concrete field name is left as an OpenSpec design choice, and by adding `failure_status`, which none of the three prior lists had. This is recorded here as a documented inconsistency in the pre-decision corpus, now closed by Decision 6, not as a conflict the human decision creates.

---

## 6. Unblock Assessment

All seven Stage 4 runtime-semantic blockers identified by the re-audit are resolved:

1. Zero rules/zero findings semantics — **resolved** (Decision 1).
2. WARNING vs REVIEW_REQUIRED assignment — **resolved** (Decision 2).
3. Severity order / no-downgrade — **resolved** (Decision 3).
4. Aggregation rule — **resolved** (Decision 4).
5. Candidate discovery ownership — **resolved** (Decision 5).
6. Rule interface minimum contract and prohibitions — **resolved** (Decision 6).
7. Profile identity and scope — **resolved** (Decision 7).

**7/7 resolved.** No architectural decision remains open for Stage 4 planning as a result of this human decision.

The Rule Registry Integrity invariant added by the 2026-08-20 human review (CHANGES_REQUIRED) does not change this count or reopen any of the seven blockers: it closes registry-integrity and profile-resolution edge cases (duplicate `rule_id` registration; an `enabled_rule_id` that fails to resolve) that the seven decisions left unaddressed, without introducing an eighth architectural decision — it is gap-filling detail within the scope Decision 6 and Decision 7 already established (rule identity/registration and profile-to-rule selection), not a new axis of design freedom.

What remains for Stage 4 planning is design, not a new architectural decision: per Decision 6, "the exact minimal Python representation may be decided in OpenSpec design while preserving these constraints" — i.e., OpenSpec design may choose concrete dataclass/protocol shapes, module placement within `src/pipeline_juridico/` (per `decision-memo-physical-layout-logical-capability-mapping-v1.0-FROZEN.md`), and rule-registry mechanics, but must not reopen any of the seven approved semantics (severity source, aggregation rule, discovery ownership, profile scope, or the rule-level behavioral prohibitions), and must implement the Rule Registry Integrity invariant as stated.

---

## 7. Status

**Status: APPROVED — FROZEN — STAGE 4 BASELINE.**

This memo is an accepted FROZEN baseline (normative Stage 4 runtime-semantics baseline, approved by human review 2026-08-20). It records and reconciles the seven approved runtime-semantic decisions issued 2026-08-20, and finds no contradiction with the existing FROZEN corpus. This revision responds to the human review's CHANGES_REQUIRED verdict of 2026-08-20, correcting the `applies_to`/`identifier_type` characterization and adding the Rule Registry Integrity invariant. Registration of this memo as FROZEN is now complete via the 2026-08-20 approval; any consequent update to the Stage 4 OpenSpec change, `technical-implementation-spec-repo-jur-v1.2-FROZEN.md`, `implementation-plan-repo-jur-v1.1-FROZEN.md`, or `arquitetura-fase2-repo-jur-v15-FROZEN.md` remains a separate future act not authorized by this memo.

No implementation, test, or OpenSpec artifact is authorized by this memo.
