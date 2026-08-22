# phase1-quality-gate Specification — MODIFIED Requirements

## MODIFIED Requirements

### Requirement: PASS requires complete physical conformance and no active technical warning

The system SHALL return `PASS` only when all of the following hold cumulatively: the source evidence has at least one physical page; the integral Markdown contains exactly one page marker per physical page, in the exact sequence `1..N` with no missing, duplicated, or out-of-order marker; every page has a completed, non-error extraction outcome (report `pages[].errors` empty AND `pages[].method != "erro"`, where an `erro` method is a failed extraction that is fatal independently of the error list); legitimately blank pages remain represented by their marker; there is no empty return on a page not determined genuinely blank; there is no unresolved extraction or parsing error; the Markdown is valid UTF-8 and conforms to the Phase 1 literal contract; the technical report is parseable and contains its minimum required fields; every page record carries the explicit truncation signal `pages[].truncated` with value `false` (no known truncation; a record lacking the mandatory field violates the minimum-field rule — absence of the field is a missing-required-field failure, never equivalent to `false` and never interpreted as "no explicit knowledge"); and there is no active technical warning recorded in the report. The system SHALL NOT assert PASS conditions for which the gate inputs define no observable signal: a "no known semantic alteration or invention" criterion is NOT part of the implemented PASS rule set, because the technical report contract defines no signal for it (recorded as a residual gap, not silently waived — any report-recorded technical condition is handled through the warning/error channel instead). The known-truncation condition (memo §6 criterion 6, §8.2; op-spec §7.1/§7.3; tech spec §8.5 `validate_no_known_truncation`, §17) is a normative FATAL condition whose serialized form this schema defines under the corpus's delegation of serialized field names to the operational schema (op-spec §6 "Os nomes serializados exatos podem ser definidos pelo schema operacional, mas devem permanecer engine-neutral"; memo §3.3 "Os nomes exatos podem ser normalizados pelo schema da Fase 1"), evaluated through the explicit, authoritative per-page truncation signal `pages[].truncated`: a page record with `truncated: true` is known truncation and prevents `PASS`; the gate SHALL NOT infer truncation from any other observable signal (character count, method, warnings, page state, or marker pattern) and SHALL NOT equate it with the empty-return rule, which remains its own deterministic fatal rule.

#### Scenario: Fully conformant artifacts yield PASS

- **WHEN** the artifacts contain exactly `N` page markers `1..N` matching `N >= 1` physical pages, all pages have completed non-error outcomes (`pages[].errors` empty and `pages[].method != "erro"`), every page record carries `pages[].truncated: false`, the Markdown is valid UTF-8, the technical report is parseable with its minimum required fields, and no technical warning is active
- **THEN** the result state is `PASS`

#### Scenario: An active technical warning prevents PASS

- **WHEN** all structural and completeness conditions hold but at least one non-fatal technical warning is active
- **THEN** the result state is not `PASS`
- **AND** the result state is `PASS_WITH_WARNINGS`

### Requirement: PASS_WITH_WARNINGS (human label "PASS WITH WARNINGS") requires complete conformant output plus at least one non-fatal warning

The system SHALL return `PASS_WITH_WARNINGS` (the serialized value whose human label is "PASS WITH WARNINGS") only when all structural and completeness conditions required to proceed are satisfied, no page is in error (report `pages[].method != "erro"` and `pages[].errors` empty), no page was silently omitted, no page record carries the explicit truncation signal `pages[].truncated: true` (known truncation is fatal, never a warning), and at least one non-fatal technical warning is recorded in the technical report's warning representation (`pages[].warnings` of a completed page — the only non-fatal warning representation in the report contract). The system SHALL NOT record a warning for: use of OCR, a legitimately blank page, line-ending normalization required by the contract, slow execution, large file size, or the specific engine used, unless accompanied by a relevant technical condition, and SHALL NOT synthesize warnings from page state or from any marker pattern (no FROZEN baseline defines an illegible-text sentinel).

#### Scenario: Complete output with a non-fatal warning yields PASS_WITH_WARNINGS

- **WHEN** all structural and completeness conditions hold, no page is in error (`pages[].errors` empty and `pages[].method != "erro"`), no page was silently omitted, no page record carries `pages[].truncated: true`, and at least one non-fatal technical warning is recorded in the report's warning representation
- **THEN** the result state is `PASS_WITH_WARNINGS`

#### Scenario: Non-warning conditions do not produce warnings

- **WHEN** the only notable conditions are OCR use, a legitimately blank page, line-ending normalization, slow execution, large file size, or engine identity
- **THEN** no warning is recorded for those conditions
- **AND** the result state is `PASS` when all other PASS conditions hold

### Requirement: FAIL on any unresolved fatal condition

The system SHALL return `FAIL` when any of the following conditions occurs and is not resolved within the evaluation: a marker count different from the physical page count; a missing, duplicated, or out-of-order page marker; a physical page silently ignored; a page whose report record shows unresolved page errors (non-empty `pages[].errors` — the state carrier: any error entry means the page is not completed, and the informational error list is the only error representation); a page whose extraction method is `erro` (`pages[].method == "erro"`), independently of its error list — an inconsistent record combining `method: erro` with an empty `errors` list is still a FAIL (memo §3.3 `error` outcome, §6 criterion 4, §7 criterion 2, §8.2); an empty return for a page not determined to be genuinely blank (`pages[].char_count == 0` with `pages[].method != "vazia"` — the empty-return rule, a fatal rule of its own, NOT a stand-in for a truncation check); a page whose explicit truncation signal is set (`pages[].truncated == true` — known truncation, the already-normative fatal condition made evaluable by the §14.3 report-schema synchronization: memo §3.4 objective condition, §6 criterion 6 "não há truncamento conhecido", §8.2 "truncamento conhecido da saída" under per-page extraction failure; op-spec §7.1/§7.3; tech spec §8.5 `validate_no_known_truncation(report)` and §17 "known truncation causes FAIL"; ESIC §11 condition 4); Markdown that is not valid UTF-8; technical report that is not parseable; presence of NUL bytes or line-ending characters prohibited by the Phase 1 textual contract; presence of technical method/routing comments in the literal Markdown body; incomplete page inventory; or absence of a minimum required field of the technical report (including a missing or non-boolean `pages[].truncated`). The system SHALL record the fatal conditions in the result errors tuple. The gate SHALL NOT infer truncation from any other observable signal, SHALL NOT invent a truncation signal, and SHALL NOT equate it with the empty-return rule, which is its own deterministic fatal rule. A page record with `pages[].truncated: false` never produces `FAIL` from truncation; a missing or non-boolean `pages[].truncated` is a report failure (missing required field) and produces `FAIL` through that rule — it is never treated as equivalent to `false` nor as "no explicit knowledge".

#### Scenario: Missing page marker causes FAIL

- **WHEN** the artifacts represent a document of `N` physical pages whose Markdown contains fewer than `N` page markers
- **THEN** the result state is `FAIL`
- **AND** the marker deficiency is recorded in the result errors tuple

#### Scenario: Duplicated or out-of-order markers cause FAIL

- **WHEN** the Markdown contains a duplicated page number or a page sequence other than `1..N`
- **THEN** the result state is `FAIL`
- **AND** the duplication or ordering violation is recorded in the result errors tuple

#### Scenario: A silently ignored page causes FAIL

- **WHEN** the technical report's page inventory does not cover every physical page of the source evidence
- **THEN** the result state is `FAIL`
- **AND** the inventory deficiency is recorded in the result errors tuple

#### Scenario: A page with unresolved errors causes FAIL

- **WHEN** any page's report record carries a non-empty `pages[].errors` list (the page is not completed)
- **THEN** the result state is `FAIL`
- **AND** the failed page is recorded in the result errors tuple

#### Scenario: A page with erro method fails independently of its error list

- **WHEN** any page's report record carries the extraction method `erro` (`pages[].method == "erro"`), regardless of the record's `pages[].errors` value — including an inconsistent record combining `method: erro` with an empty `errors` list
- **THEN** the result state is `FAIL`
- **AND** the failed page is recorded in the result errors tuple

#### Scenario: Empty return on a page not determined blank causes FAIL

- **WHEN** a page whose extraction method is not blank (`pages[].method != "vazia"`) has no content (`pages[].char_count == 0`)
- **THEN** the result state is `FAIL`
- **AND** the empty return is recorded in the result errors tuple

#### Scenario: An explicit truncation signal causes FAIL

- **WHEN** any page's report record carries the explicit truncation signal `pages[].truncated: true`
- **THEN** the result state is `FAIL`
- **AND** the known truncation is recorded in the result errors tuple

#### Scenario: A false truncation signal never causes FAIL from truncation

- **WHEN** every page's report record carries `pages[].truncated: false` and no other fatal rule is violated
- **THEN** the gate neither infers nor invents a truncation signal, and the result state is not `FAIL` from truncation
- **AND** the empty-return rule remains its own deterministic fatal rule, applied independently

#### Scenario: Textual or structural corruption causes FAIL

- **WHEN** the Markdown cannot be decoded as valid UTF-8, or contains NUL bytes, or contains line-ending characters prohibited by the Phase 1 textual contract, or contains technical method/routing comments in the literal body
- **THEN** the result state is `FAIL`
- **AND** the corruption is recorded in the result errors tuple

### Requirement: Technical report minimum fields are mandatory

The system SHALL require the technical conversion report to be parseable and to contain at least: the input evidence SHA-256 (`input.sha256`), the physical page count (`input.page_count`), and a complete per-page inventory in which every page record identifies its page number (`pages[].page_number`), its extraction method (`pages[].method`, using the report's own engine-neutral method vocabulary where `vazia` marks a genuinely blank page), its character count (`pages[].char_count`), its warning list (`pages[].warnings`), its error list (`pages[].errors` — the state carrier: non-empty means the page is not completed), and its explicit truncation signal (`pages[].truncated`, boolean, `false` = no known truncation; the field is mandatory on every page record — absence of the field is a missing required field and is never interpreted as `false` or as "no explicit knowledge"). The page inventory SHALL be exactly complete: exactly `N` page records whose page numbers are exactly the set `{1..N}` — no missing, duplicated, out-of-range, or extra page numbers. The order in which the page records appear in the inventory is NOT normative: no FROZEN baseline defines it, and the gate SHALL NOT require or fail on a specific record order (page-marker order in the literal Markdown remains governed by the marker rule). The gate SHALL NOT require the `result` block on its input — the recorded gate result is an output of evaluation, written by the pipeline when emitting the final report — and SHALL NOT read the `telemetry` block. Absence or unparseability of any of the required fields SHALL be treated as a report failure and SHALL result in `FAIL`.

#### Scenario: Missing evidence hash causes FAIL

- **WHEN** the technical report is parseable but lacks the input evidence SHA-256 (`input.sha256`)
- **THEN** the result state is `FAIL`
- **AND** the missing field is recorded in the result errors tuple

#### Scenario: Missing page count or incomplete inventory causes FAIL

- **WHEN** the technical report lacks the physical page count (`input.page_count`) or its per-page inventory is incomplete
- **THEN** the result state is `FAIL`
- **AND** the report deficiency is recorded in the result errors tuple

#### Scenario: Unparseable technical report causes FAIL

- **WHEN** the technical report cannot be parsed as valid structured data
- **THEN** the result state is `FAIL`
- **AND** the unparseable report is recorded in the result errors tuple

#### Scenario: Page inventory with numbers other than exactly 1..N causes FAIL

- **WHEN** the technical report's page inventory does not contain exactly `N` page records whose page numbers are exactly the set `{1..N}` — i.e. a page number is missing, duplicated, out of the `1..N` range, or extra
- **THEN** the result state is `FAIL`
- **AND** the inventory deficiency is recorded in the result errors tuple

#### Scenario: Missing or non-boolean truncation signal causes FAIL

- **WHEN** any page record lacks the mandatory `pages[].truncated` field or carries a non-boolean value
- **THEN** the result state is `FAIL`
- **AND** the report deficiency is recorded in the result errors tuple
- **AND** the absence is never interpreted as `false` or as "no explicit knowledge" — it is a missing required field

#### Scenario: Page record order is not normative

- **WHEN** the technical report's page inventory contains exactly `N` records with page numbers exactly `{1..N}` but ordered differently from ascending order
- **THEN** the inventory is not deficient for record order and the gate does not return `FAIL` for record order (page-marker order in the literal Markdown remains governed by the marker rule)

### Requirement: Partial diagnostic output remains FAIL

The system SHALL return `FAIL` for Phase 1 conversion artifacts in which one or more pages lack a conformant physical representation (their report records show a non-empty `pages[].errors` or an `erro` extraction method). `allow_partial` is NEVER itself a FAIL condition and NEVER waives an independently detected fatal condition: the gate SHALL NOT read any partial-output flag recorded in the report, SHALL NOT fail merely because such a flag is present, and SHALL NOT allow such a flag to downgrade, waive, or convert an independently detected fatal condition. A partial artifact SHALL NOT receive `PASS` or `PASS_WITH_WARNINGS`, and the Quality Gate SHALL NOT provide any mechanism to waive or convert a partial artifact into success. To proceed downstream, a new execution must produce artifacts that yield `PASS` or `PASS_WITH_WARNINGS`.

#### Scenario: Partial artifacts yield FAIL

- **WHEN** the artifacts contain at least one page without a conformant physical representation (a report record with non-empty `pages[].errors` or `pages[].method == "erro"`), regardless of any partial-output flag recorded anywhere
- **THEN** the result state is `FAIL`
- **AND** the affected pages are recorded in the result errors tuple

#### Scenario: No path converts partial output into success

- **WHEN** the Quality Gate evaluates artifacts with an unresolved page-level error, regardless of any partial-output flag recorded anywhere
- **THEN** the result state is `FAIL`
- **AND** no warning-only outcome is produced for the unresolved page error

#### Scenario: No other recorded flag decides FAIL by itself

- **WHEN** every page record is completed (`pages[].errors` empty and `pages[].method != "erro"`), no page carries `pages[].truncated: true`, and no fatal rule is violated
- **THEN** the result state is not `FAIL` because of any flag or other recorded signal
- **AND** the gate derives its state solely from the page inventory and the other observable artifact signals

### Requirement: Technical report records the Quality Gate result

The system SHALL record the Quality Gate outcome in the emitted Phase 1 technical report's `result` block: `result.quality_gate` SHALL be the serialized gate state — exactly one of `PASS`, `PASS_WITH_WARNINGS`, `FAIL` (the serialized value whose human label is "PASS WITH WARNINGS"; the label is never a serialized value) — and `result.warnings`/`result.errors` SHALL be the gate result's warning and error tuples. The gate itself SHALL NOT read the `result` block as an input signal — it derives its state solely from the structural fields (`input`, `pages`) and the literal Markdown — and SHALL NOT read the `telemetry` block. The pipeline SHALL evaluate the gate before emitting the final report, and the gate SHALL NOT mutate the report it evaluated (the serialized report passed to the gate SHALL be identical, byte for byte, before and after evaluation).

#### Scenario: Emitted report carries the gate result

- **WHEN** the pipeline emits the final Phase 1 technical report after Quality Gate evaluation
- **THEN** `result.quality_gate` equals the serialized gate state
- **AND** `result.warnings` and `result.errors` equal the gate result's warning and error tuples

#### Scenario: Gate ignores the recorded result and telemetry

- **WHEN** the report passed to the gate contains any `result` or `telemetry` values
- **THEN** the gate derives its state solely from `input`, `pages`, and the literal Markdown
- **AND** the recorded `result` or `telemetry` values never alter the gate's state, warnings, or errors
