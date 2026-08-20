## Why

Stage 3 now exposes the Shared Conversion Core behind `ConversionEngine.convert(evidence_ref, config) -> Phase1Artifacts`, producing literal Markdown and a technical conversion report without introducing Quality Gate or domain semantics. The FROZEN architecture requires one more non-mutating seam between that boundary and the Phase 1 Quality Gate: a Critical-Data Validation step that detects and signals inconsistencies in critical identifier-like fields (CPF/CNPJ, process number, matrícula, selo/official identifiers, dates, monetary values, document numbers) without ever autocorrecting, repairing, completing, summarizing, paraphrasing, translating, or otherwise inferring OCR/literal Markdown content (`decision-memo-post-ocr-critical-data-validation-seam-v1.1-FROZEN.md`; `technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §3.6, §8A, §17 criteria #29-#30; `implementation-plan-repo-jur-v1.1-FROZEN.md` §6; `phase1-operational-spec-v1.1-FROZEN.md` §"Post-OCR Critical-Data Validation Seam"; `decision-memo-critical-data-validation-runtime-semantics-v1.0-FROZEN.md`).

The runtime-semantics memo (approved 2026-08-20, FROZEN) resolves the seven Stage 4 runtime-semantic blockers and adds the Rule Registry Integrity invariant. This change conforms to all of them: the meaning of `OK`/`findings=[]` (Decision 1), static per-rule `failure_status` (Decision 2), the severity order `OK < WARNING < REVIEW_REQUIRED` with no downgrade (Decision 3), highest-severity aggregation with all findings preserved (Decision 4), per-rule candidate discovery with no universal central extractor (Decision 5), the rule interface contract (Decision 6), the Critical Validation Profile (Decision 7), and Rule Registry Integrity (an `enabled_rule_id` that does not resolve to exactly one registered rule is a configuration error, never a silent `status=OK`).

No FROZEN source embeds a concrete normative specification for any candidate identifier, so the only architecturally correct default is a rule registry that ships with zero pre-populated rules: `findings=[]` and `status=OK`. Adding a fabricated rule (e.g. inventing a CPF check-digit algorithm without a cited specification) would violate the anti-generalization rule and the rule-provenance requirement, both of which are FROZEN.

## What Changes

- Add the Stage 4 Critical-Data Validation Seam contract as a domain-neutral, non-mutating detect-and-signal boundary consuming Stage 3 `Phase1Artifacts` and returning `CriticalValidationResult`.
- Reuse the existing `CriticalValidationStatus` / `CriticalFinding` / `CriticalValidationResult` dataclasses already shaped per FROZEN §Output in `src/pipeline_juridico/contracts.py:88-104`, and the existing `Phase1Artifacts` from `src/pipeline_juridico/conversion_engine.py`; no change to either.
- Create a minimal `CriticalDataValidator` with a deterministic registry lifecycle: it receives the full set of rules at construction, enforces full provenance metadata (`rule_id`, `rule_version`, `applies_to`, `source`/specification reference, `validation_logic_version`, `failure_status` restricted to `WARNING` or `REVIEW_REQUIRED`) and unique `rule_id` as construction-time preconditions, stores the validated rules in an immutable internal mapping keyed by `rule_id`, defaults to an empty registry, and raises a dedicated `CriticalValidationConfigurationError` for invalid registry or profile resolution (Rule Registry Integrity).
- Implement the seven FROZEN runtime-semantic decisions and the Rule Registry Integrity invariant of `decision-memo-critical-data-validation-runtime-semantics-v1.0-FROZEN.md`: static per-rule `failure_status` (only `WARNING` or `REVIEW_REQUIRED`, never invented dynamically, never downgraded), severity order `OK < WARNING < REVIEW_REQUIRED`, highest-severity aggregation with all findings preserved individually, per-rule candidate discovery (no universal central extractor), a Critical Validation Profile (`profile_id`, `profile_version`, `enabled_rule_ids` with no duplicate rule identifiers) that only selects which registered rules are enabled, and explicit configuration-error handling (`CriticalValidationConfigurationError`) for an `enabled_rule_id` that does not resolve to exactly one registered rule, for duplicate `enabled_rule_ids` within a profile, and for invalid registry construction (missing provenance, invalid `failure_status`, duplicate `rule_id`).
- Add the non-mutation invariant as an executable test: `SHA256(markdown_before) == SHA256(markdown_after)` for the `Phase1Artifacts.markdown` value across the validator call.
- Add a domain-neutrality source-inspection test mirroring `tests/test_conversion_engine.py:298-306` (`test_facade_source_avoids_downstream_domain_types`), asserting the new module never constructs, imports, or references `GateState` or `RouteTarget`.
- Do not implement any normative check-digit/format rule for CPF/CNPJ, process number, matrícula, selo, dates, monetary values, or document numbers in this change — no FROZEN source supplies the required rule-provenance metadata for any of them.
- Do not implement intra-document redundant-value consistency comparison (explicitly a separate future capability per the seam decision memo).
- Do not implement any general, rule-independent duty to discover ambiguity or conflicting values; inconsistency detection and signaling occur only through enabled, specification-backed rules acting within their own authorized scope.
- Do not implement Phase 1 Quality Gate (Stage 5), Domain Router (Stage 6), Semantic Review, Producers, canonical publication, or retrieval in this change.
- Do not change the existing converter, OCR provider, routing, cleaning, validation, report generation, or CLI.
- Do not add or change dependencies; no FROZEN requirement makes one unavoidable for a zero-rule registry.

## Capabilities

### New Capabilities

- `critical-data-validation`: Defines the domain-neutral Stage 4 boundary that consumes `Phase1Artifacts` from the Shared Conversion Core, evaluates zero or more provenance-complete, specification-backed rules against critical identifier-like fields, and returns a `CriticalValidationResult` (`OK` / `WARNING` / `REVIEW_REQUIRED` plus findings) without mutating the literal Markdown body and without assigning a Quality Gate or domain-routing decision. Runtime semantics follow `decision-memo-critical-data-validation-runtime-semantics-v1.0-FROZEN.md`: each rule statically declares `failure_status` (restricted to `WARNING` or `REVIEW_REQUIRED`); the global status is the highest severity produced, never downgraded; each rule discovers its own candidates (no central extractor); the Critical Validation Profile selects only which registered rules are enabled (and must not list the same rule twice); detection is scoped to enabled, specification-backed rules (no general duty to discover ambiguity or conflicting values); and an `enabled_rule_id` that fails to resolve to exactly one registered rule, a profile with duplicate `enabled_rule_ids`, or an invalid registry (missing provenance, invalid `failure_status`, duplicate `rule_id`) raises `CriticalValidationConfigurationError`, never a silent `OK`.

### Modified Capabilities

None.

The existing `shared-conversion-core`, `itp-ingress-preflight-evidence`, `contract-harness`, and `juridical-pdf-conversion` requirements are not changed by this proposal.

## Non-Goals

- Implementing any normative check-digit, format, or structure rule for any candidate identifier (CPF/CNPJ, process number, matrícula, selo, dates, monetary values, document numbers).
- Implementing intra-document redundant-value consistency comparison.
- Implementing any general, rule-independent duty to discover ambiguity or conflicting values in the converted content.
- Implementing or assigning Phase 1 Quality Gate (PASS / PASS WITH WARNINGS / FAIL) semantics.
- Implementing Domain Router, Legal Knowledge or Judicial Process schemas, Semantic Review, Producers, canonical publication, or retrieval.
- Designing or implementing a universal central candidate extractor (Decision 5 forbids it).
- Adding routing, classification, legal-truth, provenance-bypass, or severity-override semantics to the Critical Validation Profile — per Decision 7 it only selects which registered rules are enabled.
- Changing the converter, OCR provider, routing thresholds, cleaner, or CLI.
- Adding or changing dependencies.
- Writing to `repo_jur/bundle/`.

## Residual Risks

These gaps exist in the FROZEN corpus itself and are not resolved by invention in this change:

1. **No embedded normative specification for any candidate identifier.** The only partial exception is `legal-okf-profile-v1.3-FROZEN.md` §4.1 (`repo_jur_processo_numero`), which states the CNJ mask `NNNNNNN-DD.AAAA.J.TR.OOOO` applies only "preferencialmente" (soft, non-mandatory language), cites a dangling reference `[206]` to a document (`especificacao-tecnica-fase2-v4.md`) that is not part of the FROZEN corpus, and lives in a domain profile that this domain-neutral seam may not couple to. Consequently this change ships zero rules rather than treating that soft mask as a specification-backed normative rule. Decision 5 of the runtime-semantics memo (per-rule candidate discovery) does not change this: each rule must still be backed by its own cited specification, and none exists for any candidate field.
2. **`technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §16.1 omits a dedicated Critical-Data Validation test category**, despite acceptance criteria #29 and #30 (§17) referencing critical-data-validation behavior. This change adds the tests required by criteria #29/#30 and by the seam decision memo directly, without inventing an additional test-plan section not present in FROZEN.

The former residual risk (untyped `profile`) is closed: `decision-memo-critical-data-validation-runtime-semantics-v1.0-FROZEN.md` Decision 7 types `profile` as a Stage-4-specific Critical Validation Profile (`profile_id`, `profile_version`, `enabled_rule_ids`), and this change implements that shape.

## Impact

- Primary affected code: new `src/pipeline_juridico/critical_data.py` and new `tests/test_critical_data.py`; no existing module is modified.
- `Phase1Artifacts` (Stage 3 output) becomes an accepted upstream input to Stage 4; Stage 3 itself is unchanged and its literal Markdown remains byte-identical before and after Stage 4 evaluation.
- `CriticalValidationResult` / `CriticalValidationStatus` / `CriticalFinding` (already defined in `src/pipeline_juridico/contracts.py`) become the Stage 4 output contract; no change to their shape.
- No new dependency, storage provider, service, database, credential, canonical bundle write, or domain-specific schema is introduced.
- Stage 5 Phase 1 Quality Gate, Stage 6 Domain Router, and later bounded-context pipelines remain out of scope and are not coupled to by this change.
