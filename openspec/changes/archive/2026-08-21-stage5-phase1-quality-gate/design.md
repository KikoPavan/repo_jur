## Context

Stage 3 established the Shared Conversion Core: `ConversionEngine.convert(evidence_ref, config) -> Phase1Artifacts`, where `Phase1Artifacts` carries the literal Markdown (method comments normalized out, canonical `[[Pág. N]]` markers preserved) plus a serialized, contract-validated technical report (`src/pipeline_juridico/conversion_engine.py`). Stage 4 added the non-mutating Critical-Data Validation seam over the same artifacts, with an explicit independence contract from the physical Quality Gate (`decision-memo-critical-data-validation-runtime-semantics-v1.0-FROZEN.md`; `implementation-plan-repo-jur-v1.1-FROZEN.md` §7 *Independence*). The FROZEN architecture now requires the Stage 5 seam itself: the deterministic, engine-neutral Phase 1 Quality Gate with exactly three normative states (`decision-memo-phase1-quality-gate-v1.0-FROZEN.md`; `phase1-operational-spec-v1.1-FROZEN.md` §7–§16; `technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §6.3, §8.5, §18 Stage 5; `external-source-ingestion-contract-v1.6-FROZEN.md` §6.6; `arquitetura-fase2-repo-jur-v15-FROZEN.md` §8.9).

The Quality Gate decision memo closes all architectural questions about the gate: three normative states (§5.1), no normative score (§5.2), PASS/PASS_WITH_WARNINGS/FAIL criteria (§6–§8), page integrity rules (§9), OCR and partial-processing semantics (§10), technical report minimum (§11), retry/idempotency (§12), and 20 invariants (§13). The remaining design work is the same class as Stage 4's: choose the minimal Python representation and the module placement that preserve every approved constraint, and prove the boundary invariants with executable tests.

Current repository facts (verified 2026-08-20):

- `GateState` exists in `src/pipeline_juridico/contracts.py:82-85` with exactly `PASS`, `PASS_WITH_WARNINGS`, `FAIL` and is currently unused by any module — it is the FROZEN three-state contract waiting for a consumer. The shared-conversion-core memo lists "Quality Gate states" among the shared contracts.
- The converter's internal validation (`src/pipeline_juridico/validator.py`) raises `MarkdownValidationError` against the **raw** converter output, where markers are adjacent to `<!-- método: ... -->` comments (`_PAGE_WITH_METHOD_PATTERN`). The Stage 3 boundary literal has markers only — the two textual contracts differ.
- `report.determine_final_status` computes `StatusExecucao` (`sucesso`/`incompleto`/`falha`) — an execution-status concept, not a gate state, and it is entangled with `allow_partial`.
- The current Phase 1 technical report (`Relatorio`) does not implement the FROZEN §6.3 minimum block layout (see Residual Risks in `proposal.md`); Stage 4 already REUSED its schema read-only.

Runtime: the project declares `requires-python = ">=3.12"`, managed with `uv` under `src/pipeline_juridico/`. This change adds no dependency.

## Repository Implementation Map (Stage 0 / physical-layout memo)

| Logical capability | Physical implementation found | Decision | Tests covering it | Migration |
| --- | --- | --- | --- | --- |
| Quality Gate states | `GateState` in `src/pipeline_juridico/contracts.py:82-85` (unused) | **REUSE** as-is; shared contract per shared-conversion-core memo | none today (unused) | none |
| Quality Gate evaluation | none — no component produces a gate state; `validator.py` raise-checks are embedded in the converter under a different textual contract (markers + method comments); `report.determine_final_status` returns `StatusExecucao` | **CREATE** minimal `src/pipeline_juridico/quality_gate.py` | new `tests/test_quality_gate.py` | none |
| Existing `validator.py` marker helpers | `validate_page_markers` / `_PAGE_WITH_METHOD_PATTERN` require `[[Pág. N]]\n<!-- método: ... -->` | **NOT REUSED** — different textual contract; the boundary literal carries markers only; reuse would reject conformant boundary output | existing `tests/test_validator.py` unchanged | none |

## Goals / Non-Goals

**Goals:**

- expose a pure, stateless evaluation entry point over the Stage 3 boundary — `evaluate(phase1_artifacts) -> QualityGateResult` — matching the tech spec §8.5 conceptual sequence (`validate_page_inventory`, `validate_page_markers`, `validate_no_unresolved_page_errors`, `validate_no_known_truncation`, `validate_markdown_artifact`, `validate_technical_report`, then FAIL / PASS_WITH_WARNINGS / PASS); `validate_no_known_truncation` is the §8.5 placeholder for the signal-dependent rule, which on the current report contract (no truncation field) is not evaluable — an already-normative deferred-evaluability requirement: the gate implements no check, never infers truncation, an explicit authoritative truncation signal is fatal per memo §8.2, and the §14.3 report-schema synchronization must add the executable check once the contract carries the signal;
- reuse `GateState` from `contracts.py` without modification, and reuse `Phase1Artifacts` from the Shared Conversion Core without modification;
- implement exactly three normative states and the deterministic rule set of the Quality Gate memo §5–§8 and the operational spec §7, with zero score/confidence authority;
- implement the warnings taxonomy: non-fatal warnings come exclusively from the report's warning representation (`pages[].warnings` of completed pages); OCR use alone and legitimately blank pages are never warnings (memo §7, §10.1; op-spec §7.1); no marker-based warning rule (no FROZEN sentinel exists — memo §16.10, tech spec §8.4);
- implement partial-mode semantics: `allow_partial` is never itself a FAIL condition and never waives an independently detected fatal condition — `FAIL` derives solely from the underlying unresolved page-level errors, which remain `FAIL` under any partial mode (memo §10.3; op-spec §8);
- prove the non-mutation invariants with executable tests: `SHA256(markdown_before) == SHA256(markdown_after)` and byte-identical serialized report across the call;
- prove strict independence from Stage 4 with a source-inspection test (mirroring the Stage 4 pattern) and a behavioral test (`REVIEW_REQUIRED` critical status + sound physical outcome ⇒ gate still reports its physical state);
- prove no coupling to Stage 6 (no routing target), no production authority (no canonical bundle write), no `verified`/OKF `status` mutation;
- prove determinism: repeated evaluation of identical artifacts yields identical state/warnings/errors; the result carries no execution id, timestamp, or duration.

**Non-Goals:**

- implementing the downstream combination mapping (`physical = PASS`, `critical = REVIEW_REQUIRED` ⇒ `review_required`) — Stage 6 Domain Router responsibility per impl plan §8 *Precedence*;
- implementing Stage 6 Domain Router, Semantic Review, Producers, canonical publication, or retrieval;
- changing the converter, OCR provider, routing thresholds, cleaner, validator, report generation, or CLI;
- rewriting the Phase 1 technical report schema to the §6.3 block layout (separate tracked residual; see Risks / Trade-offs and `proposal.md` Residual Risks);
- introducing any heuristic threshold as a fatal rule (memo §8.5);
- adding or changing dependencies;
- constructing, importing, or referencing Critical-Data Validation types, `RouteTarget`, or bundle storage.

## Decisions

### 1. New module `quality_gate.py`; reuse `GateState` from `contracts.py`

A new module `src/pipeline_juridico/quality_gate.py` owns the gate seam. It reuses `GateState` from `src/pipeline_juridico/contracts.py` (already the exact three-state contract; shared-contract authority: `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md`). It defines the gate-owned result type and the pure evaluation entry point. No existing module is modified.

**Repository Implementation Map rationale:** no existing implementation produces gate states; `validator.py`'s checks operate on the raw converter text (markers + method comments) and raise exceptions — a different textual contract and a different error model (exception vs. `FAIL` result). Reusing them would either reject conformant boundary output (markers-only) or convert the gate's deterministic result semantics into exceptions. The physical-layout memo permits a new module when no suitable implementation exists.

**Rationale:** `GateState` is already the canonical shared state enum; duplicating it would violate the REUSE rule and the shared-contracts memo.

**Alternative considered:** move `GateState` usage into the converter's final status.
**Rejected because:** `StatusExecucao` and `GateState` are distinct concepts (execution status vs. physical quality state); fusing them would modify the converter (out of scope) and conflate two FROZEN contracts.

### 2. Input contract: `Phase1Artifacts`, read-only

The evaluation entry point accepts the Stage 3 `Phase1Artifacts` dataclass (`markdown: str`, `report_json: str`) and treats both fields strictly read-only. This mirrors the Stage 4 seam (`validate(phase1_artifacts, profile)`) and the pipeline flow "Markdown literal + JSON técnico → Quality Gate" (op-spec §1; tech spec §8.5 `evaluate_phase1(markdown, report)`). The gate never resolves evidence, never invokes conversion, and never requests OCR.

**Rationale:** the boundary input requirement (spec Requirement "Phase 1 conversion artifacts are the Quality Gate input") is enforced structurally: the only accepted input type is the artifacts pair; there is no evidence-resolution path in the module (proven by source inspection).

**Alternative considered:** a raw `evaluate_phase1(markdown: str, report: dict)` signature per the §8.5 pseudo-code.
**Rejected because:** the §8.5 snippet is a conceptual sequence, not a wire contract; the canonical stage input in this repository is `Phase1Artifacts` (Stage 3 output), and passing the pair as one object keeps the boundary testable and prevents mixing artifacts from different runs.

### 3. Result shape: frozen `QualityGateResult` with state, warnings, errors, optional diagnostics

```python
@dataclass(frozen=True)
class QualityGateResult:
    state: GateState
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    diagnostics: dict[str, object] = field(default_factory=dict)
```

The state is exactly one of the three `GateState` members, whose serialized values are `PASS`, `PASS_WITH_WARNINGS`, and `FAIL` (verified in `tests/test_contracts.py::test_gate_state_values` and used by the FROZEN op-spec §14 producer boundary `quality_gate ∈ { PASS, PASS_WITH_WARNINGS }`). Throughout this change, the human label "PASS WITH WARNINGS" (with spaces) refers to the concept and is never a serialized value; the serialized value `PASS_WITH_WARNINGS` (with underscore) is never used as a human label. `warnings` and `errors` are deterministic, artifact-derived immutable ordered tuples (`tuple[str, ...]`), ordered as the underlying report entries appear. `diagnostics` is optional, non-authoritative observability (e.g. marker count, page count, per-page method summary) that never participates in the normative decision (memo §5.2). The result carries no execution id, timestamps, or duration — those are per-run telemetry of the Phase 1 report (memo §12.2), not gate output; the result must be a pure function of the artifacts (spec Requirement "Quality Gate evaluation is deterministic and engine-neutral").

**Rationale:** mirrors the Stage 4 placement rule (stage-owned types live in the stage module; only truly shared contracts live in `contracts.py`) while keeping the serialized state values exactly `PASS` / `PASS_WITH_WARNINGS` / `FAIL` per tech spec §6.3 (`GateState` already serializes that way).

**Alternative considered:** adding `QualityGateResult` to `contracts.py`.
**Rejected because:** `contracts.py` was not extended by Stage 4 (its critical-validation types pre-existed); adding a stage-owned result envelope there would expand the shared surface without a shared-contract citation. The memo lists "Quality Gate states" (the enum) as shared, not the gate result envelope.

### 4. Marker evaluation on the boundary literal

The gate parses the boundary literal with a markers-only pattern (`[[Pág. N]]`), independent of any method comment. Evaluation: the multiset of marker numbers must equal exactly `{1..N}` where `N` is the report's physical page count; any missing, duplicated, or out-of-order number, or a count different from `N`, is fatal (memo §6.2, §8.1; op-spec §7.1, §7.3). A marker count of zero, or `N < 1` (no physical pages), is fatal (memo §6 criterion 1).

**Rationale:** the Stage 3 boundary normalizes method comments out of the literal; `validator.py`'s comment-adjacent pattern is therefore the wrong tool for this seam. The gate's own marker regex is the minimal, deterministic re-implementation for the boundary textual contract.

**Alternative considered:** reuse `validate_page_markers` from `validator.py`.
**Rejected because:** it requires `<!-- método: ... -->` adjacency and would reject every conformant boundary artifact (Stage 3 strips the comments).

### 5. Presence of technical method comments in the literal body is fatal

If the literal body contains a canonical technical method/routing comment (`<!-- método: ... -->`), the gate reports `FAIL` as a structural-conformance violation (op-spec invariant 5 "Método de extração pertence ao JSON técnico"; memo §3.2 "ausência de corrupção estrutural"; tech spec §8.4 "technical comments stay out of body"). This doubles as wrong-artifact detection: feeding the gate the raw converter output (comments still present) instead of the boundary output must not silently pass.

**Rationale:** the check is deterministic, cheap, and directly cited; it prevents a class of integration mistakes from being blessed by a false `PASS`.

### 6. Extraction and empty-return rules, with the deterministic page-state mapping

The gate establishes each page's state from the actual `Relatorio` page records (verified in `src/pipeline_juridico/models.py`, `report.py`, and `converter.py`), with no inference:

| Gate concept | Deterministic field and value in the current report contract |
| --- | --- |
| Physical page count `N` | `source.pages` (int) |
| Evidence SHA-256 | `source.sha256` (str) |
| Page number | `pages[].number` (int) |
| **Page inventory integrity** | exactly `source.pages` records whose `pages[].number` values are exactly the set `{1..N}` — no missing, duplicated, out-of-range, or extra page numbers; the order of the records in the inventory is NOT normative (no FROZEN baseline defines it) |
| Extraction method | `pages[].method` ∈ `texto_nativo` / `ocr_integral` / `hibrido` / `vazia` / `erro` (`Metodo` values; memo §3.3 allows the Phase 1 schema's own names, so no mapping to `native_text`/`ocr`/`hybrid`/`blank`/`error` is performed); **`erro` is FATAL independently of `status`** (memo §3.3 `error` outcome, §6 criterion 4 "não `error`", §7 criterion 2, §8.2 "página com conteúdo que termina em estado `error`") — an inconsistent record with `method: erro` and `status: sucesso` is still a FAIL |
| **Completed state** | `pages[].status == "sucesso"` (`StatusExecucao.sucesso`) — the state carrier |
| **Error / not-completed state** | `pages[].status != "sucesso"` (i.e. `"falha"` or `"incompleto"`) — fatal; the current converter emits only `sucesso`/`falha` per page (`falha` iff `method == erro`, `converter.py:609-613`), but the contract allows `incompleto` per page and the gate treats any non-`sucesso` status as not completed. Independently, `pages[].method == "erro"` is fatal regardless of `status` (see Extraction method row): an inconsistent record with `method: erro` and `status: sucesso` FAILs |
| **`pages[].error` role** | informational error message, `str` or `null`; the current converter always writes `null` (`converter.py:625`), so `error` is NOT a state carrier — the gate reads `status` and treats `error` as non-authoritative |
| **Blank state** | `pages[].method == "vazia"` — genuinely blank; conformant with empty content, keeps its marker, never a warning (memo §6.5, §9.2) |
| **Empty-return fatal rule** | `pages[].characters == 0` AND `pages[].method != "vazia"` — "retorno vazio quando a página não foi determinada como realmente vazia" (memo §8.2, §9.3; op-spec §7.3 "página não vazia sem representação válida"); this is its own deterministic fatal rule |
| **Warning representation** | `pages[].warnings` — list of strings, the only non-fatal warning representation in the current contract (report.py validates it as a list); the gate aggregates non-empty entries of completed pages, never synthesizing warnings from page state |

The gate never reads the top-level `report.status` (`StatusExecucao` sucesso/incompleto/falha) to decide gate state: that field is the execution-status concept (distinct from `GateState`), and `incompleto` merely records that partial mode produced failed pages — the gate's FAIL derives from those pages' own records, not from the flag.

**Known-truncation note:** `truncamento conhecido` (memo §8.2, §3.4; op-spec §7.1/§7.3; tech spec §17 "known truncation causes FAIL") is a **normative fatal condition**: an explicit, authoritative truncation signal in the report produces `FAIL`. The current `Relatorio` schema defines no such field, so no artifact on the current contract can present one and the condition **cannot be evaluated today**; the gate therefore implements no known-truncation check, SHALL NOT infer truncation from any other observable signal, and does **not** conflate it with the empty-return rule, which stands alone as its own deterministic fatal rule. This is an **already-normative deferred-evaluability requirement**: the rule is fatal and remains normative (proposal.md Residual Risk 2 — a documented residual, **not a blocker and not a waiver**), and the §14.3 report-schema synchronization **must add the executable check** — an explicit frozen truncation signal added to the report contract is then consumed by the gate as a fatal signal without architectural change.

**Rationale:** empty-on-non-blank is the deterministic reading of §9.3's "página aparentemente vazia" and the only extraction-outcome signal available without inventing a new report field.

### 7. Warning aggregation taxonomy

The gate records a non-fatal warning **only** for non-fatal warnings actually present in the report's warning representation: each non-empty string in `pages[].warnings` of a completed page (`pages[].status == "sucesso"`) is a non-fatal technical warning ("engine emitiu warning não fatal preservado no relatório" — memo §7 admissible example; the report is the only warning source per ESIC §6.4 and op-spec invariant 5, since warnings belong to the JSON técnico). Aggregation collects these entries into the immutable ordered tuple `warnings` in the order they appear in the report (deterministic; no ordering requirement is invented). The gate SHALL NOT synthesize warnings from page state and SHALL NOT warn for: use of OCR, a legitimately blank page, line-ending normalization, slow execution, large file size, or engine identity (memo §7 "Não são warnings por si só"). There is **no marker-based warning rule**: no FROZEN baseline defines an illegible-text sentinel (memo §16.10 removed `[[TEXTO ILEGÍVEL]]` as a memo-created mandatory sentinel; tech spec §8.4: "This specification does not create a mandatory `[ilegível]` sentinel"), and source illegibility is already registered deterministically through the page's report record (`method: erro` / `status` not completed / `warnings`), which the extraction-outcome fatal rule handles.

**Rationale:** the taxonomy is entirely sourced: admissible warning examples and the explicit non-warning list are memo §7; the report is the only channel that can carry an engine-registered condition (including a suspected semantic alteration — such a registered condition is a non-fatal warning unless a fatal rule applies), so the gate never invents warnings from unobservable signals.

**Alternative considered:** warn on any page whose method used OCR.
**Rejected because:** memo §10.1/§7 and op-spec §7.1 explicitly forbid OCR-use warnings.

### 8. Report minimum fields and report-failure handling

The gate requires the serialized report to parse (as JSON with the field types the contract validator enforces, `report.py:validate_report_contract`) and to contain: input evidence SHA-256 (`source.sha256`), physical page count (`source.pages`), and a complete per-page inventory where every page record carries its page number (`pages[].number`), extraction method (`pages[].method`), and completed/error state (`pages[].status`) — the deterministic field mapping is Decision 6. The inventory SHALL contain exactly `source.pages` records whose page numbers are exactly the set `{1..N}` (no missing, duplicated, out-of-range, or extra page numbers); record order is NOT normative (no FROZEN baseline defines it) and is not checked. Any absence or violation → `FAIL` with the deficiency recorded in `errors` (memo §8.4; op-spec §9). The gate does NOT require the FROZEN §6.3 block layout (`execution_id`/`input`/`phase1`/`result`/`artifacts`/`telemetry`), which the current `Relatorio` schema does not implement (residual 1); the isolated mapping reads only the fields that exist:

| FROZEN §6.3 / op-spec §9 concept | Current `Relatorio` field | Role at the gate |
| --- | --- | --- |
| `input.sha256` | `source.sha256` | required — report-failure fatal if absent |
| `input.page_count` | `source.pages` | required — physical page count `N` for marker coverage and inventory checks |
| `pages[].page_number` | `pages[].number` | required — page identity |
| `pages[].method` | `pages[].method` | required — existing `Metodo` values; `vazia` = blank, `erro` = extraction error |
| `pages[].char_count` | `pages[].characters` | empty-return fatal rule input (`characters == 0` ∧ `method != vazia`) |
| `pages[].status` (completed/error) | `pages[].status` (`StatusExecucao`: `sucesso`/`falha`/`incompleto`) | required — completed = `sucesso`; anything else = fatal not-completed |
| `pages[].errors` | `pages[].error` (str or null) | informational only; NOT the state carrier (converter always emits null today) |
| `pages[].warnings` | `pages[].warnings` (list of str) | the warning representation; non-empty entries of completed pages drive `PASS_WITH_WARNINGS` |

The gate does NOT compare hashes (no `markdown_sha256` verification): the existing `output.sha256` hashes the raw converter output while the boundary literal is normalized (comments stripped), so comparison would false-FAIL conformant output; the report synchronization (residual risk 1/3 in `proposal.md`) must redefine the markdown hash over the boundary output first. The gate never reads `report.status` (`StatusExecucao`) for its decision (Decision 6).

**Rationale:** required fields are the ones the gate actually needs to evaluate coverage and outcomes; §8.4 makes their absence fatal. The mapping is isolated so a future §6.3 report adoption changes one function, not the rules.

### 9. Strict independence from Stage 4, enforced by source inspection and behavior

`quality_gate.py` never constructs, imports, or references `CriticalValidationResult`, `CriticalValidationStatus`, `CriticalFinding`, `CriticalDataValidator`, or any other Critical-Data Validation type (spec Requirement "Quality Gate is independent of Critical-Data Validation"). A source-inspection test reads the module text and asserts none of those names appear — the exact mirror of the Stage 4 domain-neutrality test (`tests/test_critical_data.py`, which asserts no `GateState`/`RouteTarget` in `critical_data.py`). A behavioral test runs a test-only critical rule that returns `REVIEW_REQUIRED` while the gate reports `PASS` on the same sound artifacts, proving the two seams compose without influencing each other (impl plan §7 *Independence*; runtime-semantics memo independence row).

**Rationale:** the independence contract is bidirectional in FROZEN (Stage 4 spec "Critical-Data Validation status is independent of the Phase 1 Quality Gate"; impl plan §7). Enforcing both directions by source inspection makes the boundary structural, not just behavioral.

### 10. No Stage 6 or Producer coupling

`quality_gate.py` never constructs, imports, or references `RouteTarget` or any domain-routing type, never writes to `repo_jur/bundle/`, never creates `verified`, and never mutates an OKF `status` (spec Requirements "Quality Gate introduces no domain-routing decision" and "Quality Gate introduces no production or lifecycle decision"). The eligibility invariant (only `PASS`/`PASS_WITH_WARNINGS` may proceed) is stated in the spec and enforced at the gate by construction: the gate returns a state; it performs no handoff. The Stage 6 router consumes eligible states later.

### 11. Partial mode requires no gate parameter

The gate takes no `allow_partial` flag and reads no partial-output flag from the report. `allow_partial` is NEVER itself a FAIL condition and NEVER waives an independently detected fatal condition: a partial-mode artifact is `FAIL` only because its underlying pages lack a conformant representation (their report records show `status != "sucesso"`), which the extraction rule already turns into `FAIL` (memo §10.3: `allow_partial` não modifica a decisão normativa; op-spec §8: não converte FAIL em `PASS_WITH_WARNINGS`; tech spec §8.5: "allow_partial never converts FAIL into success"). A parameter would be redundant and could be misread as an authority to downgrade `FAIL`; the gate exposes no waiver mechanism of any kind.

**Rationale:** the gate decides from the artifacts alone; partial mode is a Phase 1 execution mode, not a gate input, and the memo explicitly forbids any mechanism that converts partial output into success.

### 12. Determinism and idempotency proven by double evaluation

The gate is a pure function; the result carries no execution id, timestamps, or duration. A test evaluates identical artifacts twice and asserts identical state, warnings, and errors (memo §12.1: same bytes + same logical processing version + same config ⇒ same deterministic gate result).

**Rationale:** the memo's idempotency requirement applies to the gate result; removing telemetry from the result is the minimal way to make the result itself reproducible.

### 13. Diagnostics are non-authoritative by construction

If `diagnostics` is populated (e.g. marker count, page count, per-page method summary), a test asserts that mutating/removing diagnostics never changes the state, warnings, or errors — no score, confidence, or metric participates in the normative decision (memo §5.2, §8.5; op-spec invariant 7).

## Risks / Trade-offs

- **[Risk] A future contributor could turn the gate into the "score authority"** and let a diagnostic metric decide acceptance.
  → Mitigation: spec Requirement "Quality Gate evaluation is deterministic and engine-neutral" + "No implicit heuristic threshold is fatal"; design Decision 13; a test pins diagnostics to non-authoritative status.
- **[Risk] A future contributor could couple the gate to the Stage 4 result** to implement the `PASS + REVIEW_REQUIRED ⇒ review_required` combination early.
  → Mitigation: the independence source-inspection test fails any such import; the combination mapping is explicitly a Stage 6 non-goal with citation.
- **[Risk] Feeding the gate the raw converter output instead of the boundary output** (method comments still present) could silently pass.
  → Mitigation: Decision 5 makes comment presence fatal; the wrong-artifact case is covered by a dedicated test.
- **[Risk] The §6.3 report synchronization (residual) could later rename fields and break the gate's mapping.**
  → Mitigation: all report access is isolated in one mapping function (Decision 8); the sync change would update one function and re-run the gate suite.
- **[Trade-off] The gate cannot verify `artifacts.markdown_sha256` today** because the existing report hash covers the pre-normalization body (residual risk 3). This keeps the gate correct on the current contract at the cost of one integrity check that must wait for the report sync.
- **[Trade-off] No known-truncation check is implemented because the current report contract defines no truncation signal** (residual risk 2; Decision 6). The memo's `truncamento conhecido` criterion is already normative — an authoritative truncation signal is fatal — but it is not evaluable on the current contract, which defines no such signal; the gate therefore implements no check, never infers truncation, and never equates it with the empty-return rule, which remains its own deterministic fatal rule. The §14.3 report sync must add the executable check: an explicit frozen truncation flag added there makes the already-normative condition evaluable without changing the gate's architecture. This is a documented corpus gap, not a blocker and not a waiver: every observable rule is implemented deterministically.
- **[Trade-off] No marker-based illegible-text warning exists** (residual risk 5): no FROZEN baseline defines an illegible sentinel, and source illegibility is already handled by the extraction-outcome fatal rule via the page report record. Removing the vacuous rule keeps the gate strictly within the corpus.

## Migration Plan

1. Add tests for the Stage 5 contract before implementation (TDD, red first): boundary input contract; three-state semantics (`PASS` / `PASS_WITH_WARNINGS` / `FAIL`); marker coverage (exact `1..N`, missing, duplicate, out-of-order, zero pages); extraction outcomes (error page, empty-return-on-non-blank, blank page); structural conformance (UTF-8, NUL, CR, method-comment-in-body, unparseable report, missing hash/page-count/inventory integrity — exactly N records numbered `1..N`, record order not normative); warnings taxonomy (non-fatal page warning ⇒ `PASS_WITH_WARNINGS`; OCR/blank never warn); partial artifacts ⇒ FAIL; non-mutation invariants (markdown SHA-256 equality, byte-identical report); determinism (double evaluation); diagnostics non-authority; independence source inspection (no Critical-Data Validation references in the gate module) and behavior (gate `PASS` + critical `REVIEW_REQUIRED` compose independently); no `RouteTarget`/bundle references (source inspection).
2. Add `src/pipeline_juridico/quality_gate.py` with the frozen `QualityGateResult`, the markers-only parser, the isolated report-field mapping, the fatal-rule evaluation, the warning aggregation, and the pure `evaluate(phase1_artifacts) -> QualityGateResult` entry point, reusing `GateState` from `contracts.py` and `Phase1Artifacts` from `conversion_engine.py` without modification.
3. Run focused Stage 5 tests.
4. Run the full existing regression suite to prove no behavioral change to Stage 1–4 (the corpus integration suite requires the gitignored `input/*.pdf` fixtures to be present in the worktree, as for every stage).
5. Run OpenSpec strict validation (`openspec validate --all --strict`).
6. Do not modify or publish `repo_jur/bundle/`.

Rollback is limited to removal of the new `quality_gate.py` module and its tests; no other module is touched by this change.

## Open Questions

No blocking architectural question remains for Stage 5. The Quality Gate memo closed the gate's architectural decisions; this design resolves the two OpenSpec-level choices the corpus leaves open — the minimal Python representation (frozen `QualityGateResult` + pure `evaluate` function, per tech spec §8.5) and module placement (new `quality_gate.py` reusing `GateState`, per the physical-layout memo) — while preserving every FROZEN constraint. The residual gaps recorded in `proposal.md` (report schema divergence from §6.3, absent truncation signal, unverifiable markdown hash at the boundary, non-canonical illegible sentinel) are FROZEN-corpus/current-implementation gaps, not open Stage 5 design questions, and are not resolved by invention in this change; the truncation and sentinel gaps were explicitly determined **not to be blockers** (Decision 6, Residual Risks 2 and 5).
