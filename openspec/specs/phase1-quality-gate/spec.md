# phase1-quality-gate Specification

## Purpose
TBD - created by archiving change stage5-phase1-quality-gate. Update Purpose after archive.
## Requirements
### Requirement: Phase 1 conversion artifacts are the Quality Gate input

The system SHALL begin Phase 1 Quality Gate evaluation from the Shared Conversion Core output (Phase 1 conversion artifacts containing literal Markdown and a technical conversion report). The Stage 5 boundary SHALL NOT treat an unconverted evidence reference or an arbitrary caller-supplied document as its input contract, and SHALL NOT request or perform any further conversion.

#### Scenario: Phase 1 conversion artifacts are accepted

- **WHEN** the Phase 1 Quality Gate receives Phase 1 conversion artifacts produced by the Shared Conversion Core
- **THEN** the literal Markdown and the technical conversion report are made available to the gate evaluation
- **AND** the gate evaluates that already-converted content without requesting or performing further conversion

### Requirement: Quality Gate never mutates the literal Markdown body

The system SHALL NOT modify, rewrite, autocorrect, complete, paraphrase, translate, or otherwise alter the literal Markdown body of the Phase 1 conversion artifacts as part of Quality Gate evaluation. The literal Markdown content SHALL be identical, byte for byte, before and after the Quality Gate executes.

#### Scenario: Markdown is unchanged after evaluation

- **WHEN** the Quality Gate executes against Phase 1 conversion artifacts, regardless of the resulting gate state
- **THEN** the SHA-256 hash of the literal Markdown body after evaluation equals the SHA-256 hash of the literal Markdown body before evaluation

#### Scenario: A detected condition does not trigger correction

- **WHEN** the Quality Gate detects a physical or structural non-conformance in the converted content
- **THEN** the literal Markdown value remains exactly as produced by conversion
- **AND** no text is invented, completed, or substituted to resolve the condition

### Requirement: Quality Gate never mutates the technical conversion report

The system SHALL NOT mutate, rename, or reorder any serialized field of the technical conversion report as part of Quality Gate evaluation, and SHALL NOT alter the serialized report bytes. Read-only semantic field mapping — reading report fields to evaluate the gate rules — is permitted and is not a mutation, rename, or reorder. The serialized technical report SHALL be identical, byte for byte, before and after the Quality Gate executes.

#### Scenario: Technical report is unchanged after evaluation

- **WHEN** the Quality Gate executes against Phase 1 conversion artifacts, regardless of the resulting gate state
- **THEN** the serialized technical report after evaluation equals the serialized technical report before evaluation

### Requirement: Quality Gate result contains only state, warnings, and errors

The system SHALL return a Quality Gate result containing a state value, an immutable ordered tuple of warnings (`tuple[str, ...]`), an immutable ordered tuple of errors, and optional non-authoritative diagnostics. The state SHALL be exactly one of the three `GateState` members — `PASS`, `PASS_WITH_WARNINGS`, `FAIL` — where `PASS_WITH_WARNINGS` is the serialized value whose human label is "PASS WITH WARNINGS" (the label is never a serialized value). Warnings and errors SHALL exist only in the technical layer of the result and SHALL NOT be introduced into the literal Markdown body.

#### Scenario: PASS result carries no errors and no warnings

- **WHEN** the Quality Gate evaluates fully conformant artifacts with no active technical warning
- **THEN** the result state is `PASS`
- **AND** the result errors tuple is empty
- **AND** the result warnings tuple is empty

#### Scenario: FAIL result records errors only in the result

- **WHEN** the Quality Gate evaluates artifacts that violate a fatal rule
- **THEN** the result state is `FAIL`
- **AND** the fatal conditions are recorded in the result errors tuple
- **AND** no error or warning text appears inside the literal Markdown body

### Requirement: Quality Gate evaluation is deterministic and engine-neutral

The system SHALL compute the Quality Gate result as a pure deterministic function of the Phase 1 conversion artifacts: identical artifacts SHALL yield identical state, warnings, and errors on every evaluation. The gate SHALL NOT depend on any conversion engine, OCR provider, OCR model, conversion/OCR/engine-specific parser, or per-run telemetry, and SHALL NOT introduce execution identifiers, timestamps, or duration into the result. JSON parsing of the technical report and page-marker parsing of the literal Markdown, as required by the gate rules, remain allowed.

#### Scenario: Repeated evaluation of identical artifacts is identical

- **WHEN** the same Phase 1 conversion artifacts are evaluated twice
- **THEN** the second result state, warnings, and errors equal the first result state, warnings, and errors

#### Scenario: Evaluation does not depend on engine identity

- **WHEN** the technical report records any engine, provider, or model identity
- **THEN** the gate result does not change because of that identity
- **AND** the gate result contains no engine, provider, or model requirement or preference

### Requirement: PASS requires complete physical conformance and no active technical warning

The system SHALL return `PASS` only when all of the following hold cumulatively: the source evidence has at least one physical page; the integral Markdown contains exactly one page marker per physical page, in the exact sequence `1..N` with no missing, duplicated, or out-of-order marker; every page has a completed, non-error extraction outcome (report `pages[].status == "sucesso"` AND `pages[].method != "erro"`, where an `erro` method is a failed extraction that is fatal independently of `status`); legitimately blank pages remain represented by their marker; there is no empty return on a page not determined genuinely blank; there is no unresolved extraction or parsing error; the Markdown is valid UTF-8 and conforms to the Phase 1 literal contract; the technical report is parseable and contains its minimum required fields; and there is no active technical warning recorded in the report. The system SHALL NOT assert PASS conditions for which the gate inputs define no observable signal: a "no known semantic alteration or invention" criterion is NOT part of the implemented PASS rule set, because the current technical report contract defines no signal for it (recorded as a residual gap, not silently waived — any report-recorded technical condition is handled through the warning/error channel instead). The memo's known-truncation condition (memo §6 criterion 6, §8.2; op-spec §7.1/§7.3; tech spec §17) is a normative FATAL condition — an explicit authoritative truncation signal produces `FAIL` — but the current technical report contract defines no truncation signal, so it cannot be evaluated on the current contract; the gate SHALL NOT infer truncation from any other observable signal and SHALL NOT equate it with the empty-return rule.

#### Scenario: Fully conformant artifacts yield PASS

- **WHEN** the artifacts contain exactly `N` page markers `1..N` matching `N >= 1` physical pages, all pages have completed non-error outcomes, the Markdown is valid UTF-8, the technical report is parseable with its minimum required fields, and no technical warning is active
- **THEN** the result state is `PASS`

#### Scenario: An active technical warning prevents PASS

- **WHEN** all structural and completeness conditions hold but at least one non-fatal technical warning is active
- **THEN** the result state is not `PASS`
- **AND** the result state is `PASS_WITH_WARNINGS`

### Requirement: Successful OCR is compatible with PASS

The system SHALL NOT treat successful OCR use as a failure and SHALL NOT treat OCR use alone as a warning. A document whose pages were converted with OCR SHALL be eligible for `PASS` when the output is otherwise conformant, and the gate result SHALL NOT record a warning solely because OCR was used.

#### Scenario: OCR-converted pages can yield PASS

- **WHEN** the artifacts represent a document whose pages used OCR, all extraction outcomes are completed and non-error, and all other PASS conditions hold
- **THEN** the result state is `PASS`
- **AND** no warning is recorded solely for the use of OCR

#### Scenario: Mixed native and OCR pages can yield PASS

- **WHEN** the artifacts mix native-text and OCR-converted pages with conformant output and no warning
- **THEN** the result state is `PASS`
- **AND** the per-page method remains recorded in the technical layer, not in the Markdown body

### Requirement: A legitimately blank page is not a warning

The system SHALL represent a page genuinely determined to be blank by its page marker in the integral Markdown and SHALL NOT require a technical comment inside the Markdown body for it. A legitimately blank page SHALL NOT produce a warning by itself.

#### Scenario: Blank page keeps its marker and yields no warning

- **WHEN** the artifacts contain a page determined to be genuinely blank
- **THEN** that page remains represented by its marker in the Markdown
- **AND** the blank page produces no warning
- **AND** the blank page does not prevent `PASS` when all other PASS conditions hold

### Requirement: PASS_WITH_WARNINGS (human label "PASS WITH WARNINGS") requires complete conformant output plus at least one non-fatal warning

The system SHALL return `PASS_WITH_WARNINGS` (the serialized value whose human label is "PASS WITH WARNINGS") only when all structural and completeness conditions required to proceed are satisfied, no page is in error (report `pages[].method != "erro"` and `pages[].status == "sucesso"`), no page was silently omitted, and at least one non-fatal technical warning is recorded in the technical report's warning representation (`pages[].warnings` of a completed page — the only non-fatal warning representation in the current report contract). The system SHALL NOT record a warning for: use of OCR, a legitimately blank page, line-ending normalization required by the contract, slow execution, large file size, or the specific engine used, unless accompanied by a relevant technical condition, and SHALL NOT synthesize warnings from page state or from any marker pattern (no FROZEN baseline defines an illegible-text sentinel).

#### Scenario: Complete output with a non-fatal warning yields PASS_WITH_WARNINGS

- **WHEN** all structural and completeness conditions hold, no page is in error, no page was silently omitted, and at least one non-fatal technical warning is recorded in the report's warning representation
- **THEN** the result state is `PASS_WITH_WARNINGS`

#### Scenario: Non-warning conditions do not produce warnings

- **WHEN** the only notable conditions are OCR use, a legitimately blank page, line-ending normalization, slow execution, large file size, or engine identity
- **THEN** no warning is recorded for those conditions
- **AND** the result state is `PASS` when all other PASS conditions hold

### Requirement: FAIL on any unresolved fatal condition

The system SHALL return `FAIL` when any of the following conditions occurs and is not resolved within the evaluation: a marker count different from the physical page count; a missing, duplicated, or out-of-order page marker; a physical page silently ignored; a page whose report record shows a not-completed status (the state carrier `pages[].status` is not `sucesso`, which covers the error state `falha` and any incomplete state); a page whose extraction method is `erro` (`pages[].method == "erro"`), independently of its `pages[].status` — an inconsistent record combining `method: erro` with `status: sucesso` is still a FAIL (memo §3.3 `error` outcome, §6 criterion 4, §7 criterion 2, §8.2); an empty return for a page not determined to be genuinely blank (`pages[].characters == 0` with `pages[].method != "vazia"` — the empty-return rule, a fatal rule of its own, NOT a stand-in for a truncation check); Markdown that is not valid UTF-8; technical report that is not parseable; presence of NUL bytes or line-ending characters prohibited by the Phase 1 textual contract; presence of technical method/routing comments in the literal Markdown body; incomplete page inventory; or absence of a minimum required field of the technical report. The system SHALL record the fatal conditions in the result errors tuple. The memo's `truncamento conhecido` rule remains normative and fatal as an already-normative deferred-evaluability requirement: an explicit, authoritative truncation signal in the technical report SHALL produce `FAIL` (memo §8.2/§3.4; op-spec §7.1/§7.3; tech spec §17). The current technical report contract defines no truncation signal, so no artifact produced under the current contract can present one and this implementation cannot evaluate the condition; it implements no truncation check, and the report-schema synchronization (memo §14.3) must add the executable check once the report contract carries the signal. The gate SHALL NOT infer truncation from any other observable signal, SHALL NOT invent a truncation signal, and SHALL NOT equate it with the empty-return rule, which is its own deterministic fatal rule.

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

#### Scenario: A page in extraction error state causes FAIL

- **WHEN** any page's report record shows a not-completed status (its `pages[].status` value is not `sucesso`, i.e. the error state `falha` or any incomplete state) or the page was not completed
- **THEN** the result state is `FAIL`
- **AND** the failed page is recorded in the result errors tuple

#### Scenario: A page with erro method fails independently of its status

- **WHEN** any page's report record carries the extraction method `erro` (`pages[].method == "erro"`), regardless of the record's `pages[].status` value — including an inconsistent record combining `method: erro` with `status: sucesso`
- **THEN** the result state is `FAIL`
- **AND** the failed page is recorded in the result errors tuple

#### Scenario: Empty return on a page not determined blank causes FAIL

- **WHEN** a page whose extraction method is not blank (`pages[].method != "vazia"`) has no content (`pages[].characters == 0`)
- **THEN** the result state is `FAIL`
- **AND** the empty return is recorded in the result errors tuple

#### Scenario: No truncation signal is inferred or invented

- **WHEN** the technical report contains no truncation signal (the current report contract defines no truncation field) and no other fatal rule is violated
- **THEN** the gate neither infers nor invents a truncation signal, and the result state is not `FAIL` from truncation
- **AND** the empty-return rule remains its own deterministic fatal rule, applied independently

#### Scenario: Textual or structural corruption causes FAIL

- **WHEN** the Markdown cannot be decoded as valid UTF-8, or contains NUL bytes, or contains line-ending characters prohibited by the Phase 1 textual contract, or contains technical method/routing comments in the literal body
- **THEN** the result state is `FAIL`
- **AND** the corruption is recorded in the result errors tuple

### Requirement: Technical report minimum fields are mandatory

The system SHALL require the technical conversion report to be parseable and to contain at least: the input evidence SHA-256 (`source.sha256`), the physical page count (`source.pages`), and a complete per-page inventory in which every page record identifies its page number (`pages[].number`), its extraction method (`pages[].method`, using the report's own `Metodo` vocabulary where `vazia` marks a genuinely blank page), and its completed or error state via the state-carrier field (`pages[].status`: `sucesso` = completed; `falha` or any other value = not completed/error). The page inventory SHALL be exactly complete: exactly `N` page records whose page numbers are exactly the set `{1..N}` — no missing, duplicated, out-of-range, or extra page numbers. The order in which the page records appear in the inventory is NOT normative: no FROZEN baseline defines it, and the gate SHALL NOT require or fail on a specific record order (page-marker order in the literal Markdown remains governed by the marker rule). The informational `pages[].error` field SHALL NOT be used as the state carrier, and the warning representation SHALL be the `pages[].warnings` list. Absence or unparseability of any of the required fields SHALL be treated as a report failure and SHALL result in `FAIL`.

#### Scenario: Missing evidence hash causes FAIL

- **WHEN** the technical report is parseable but lacks the input evidence SHA-256
- **THEN** the result state is `FAIL`
- **AND** the missing field is recorded in the result errors tuple

#### Scenario: Missing page count or incomplete inventory causes FAIL

- **WHEN** the technical report lacks the physical page count or its per-page inventory is incomplete
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

#### Scenario: Page record order is not normative

- **WHEN** the technical report's page inventory contains exactly `N` records with page numbers exactly `{1..N}` but ordered differently from ascending order
- **THEN** the inventory is not deficient for record order and the gate does not return `FAIL` for record order (page-marker order in the literal Markdown remains governed by the marker rule)

### Requirement: No implicit heuristic threshold is fatal

The system SHALL NOT turn a heuristic signal — such as a high proportion of unusual characters, watermark presence, confidence values, or engine-specific observability thresholds — into `FAIL` unless an approved deterministic rule defines that specific signal as a fatal violation. Heuristic signals SHALL remain non-authoritative diagnostics at most.

#### Scenario: Unusual-character proportion does not decide FAIL by itself

- **WHEN** the artifacts contain a high proportion of unusual characters but no approved deterministic rule classifies that proportion as fatal and no other fatal rule is violated
- **THEN** the result state is not `FAIL` because of that proportion
- **AND** any such signal, if recorded, is non-authoritative diagnostic data

### Requirement: Partial diagnostic output remains FAIL

The system SHALL return `FAIL` for Phase 1 conversion artifacts in which one or more pages lack a conformant physical representation (their report records show a not-completed `pages[].status`). `allow_partial` is NEVER itself a FAIL condition and NEVER waives an independently detected fatal condition: the gate SHALL NOT read any partial-output flag recorded in the report, SHALL NOT fail merely because such a flag is present, and SHALL NOT allow such a flag to downgrade, waive, or convert an independently detected fatal condition. A partial artifact SHALL NOT receive `PASS` or `PASS_WITH_WARNINGS`, and the Quality Gate SHALL NOT provide any mechanism to waive or convert a partial artifact into success. To proceed downstream, a new execution must produce artifacts that yield `PASS` or `PASS_WITH_WARNINGS`.

#### Scenario: Partial artifacts yield FAIL

- **WHEN** the artifacts contain at least one page without a conformant physical representation (a report record with not-completed `pages[].status`), regardless of any partial-output flag recorded anywhere
- **THEN** the result state is `FAIL`
- **AND** the affected pages are recorded in the result errors tuple

#### Scenario: No path converts partial output into success

- **WHEN** the Quality Gate evaluates artifacts with an unresolved page-level error, regardless of any partial-output flag recorded anywhere
- **THEN** the result state is `FAIL`
- **AND** no warning-only outcome is produced for the unresolved page error

#### Scenario: A partial-output flag alone never decides FAIL

- **WHEN** the technical report records a partial/execution status such as `incompleto` at the top level but every page record is completed (`pages[].status == "sucesso"`) and no fatal rule is violated
- **THEN** the result state is not `FAIL` because of the flag
- **AND** the gate derives its state solely from the page inventory and the other observable artifact signals

### Requirement: Quality Gate is independent of Critical-Data Validation

The system SHALL keep the Quality Gate result independent of the Critical-Data Validation result. The Quality Gate SHALL NOT construct, import, or assign a Critical-Data Validation status or finding. A `REVIEW_REQUIRED` critical-data status combined with a sound physical conversion outcome SHALL NOT be treated by this capability as a Quality Gate failure.

#### Scenario: Critical-data status does not alter physical gate semantics

- **WHEN** Critical-Data Validation returns `REVIEW_REQUIRED` for content whose physical conversion outcome is otherwise sound
- **THEN** the Quality Gate reports the physical outcome without modification, including `PASS` when the physical conditions hold
- **AND** no Critical-Data Validation status or finding type is constructed, imported, or referenced by this capability

#### Scenario: Combination mapping is not implemented here

- **WHEN** both a physical gate state and a critical-data status are available for the same artifacts
- **THEN** this capability produces only the physical gate state
- **AND** no combined or routed outcome such as a review-required routing decision is produced by this capability

### Requirement: Quality Gate introduces no domain-routing decision

The system SHALL remain domain-neutral. The Quality Gate SHALL NOT select a Legal Knowledge or Judicial Process route, SHALL NOT construct or import a domain-routing target type, and SHALL NOT apply a domain-specific schema. The downstream invariant that only `PASS` and `PASS_WITH_WARNINGS` outcomes may proceed to routing and to the OKF Producer SHALL be stated by this capability without being implemented as a routing or production action.

#### Scenario: Evaluation completes without routing

- **WHEN** the Quality Gate completes for Phase 1 conversion artifacts
- **THEN** the result exposes only the gate-owned state, warnings, errors, and non-authoritative diagnostics
- **AND** no Legal Knowledge, Judicial Process, or review-required routing decision is assigned by this capability

#### Scenario: Domain-routing types are absent from the implementation

- **WHEN** the Quality Gate implementation source is inspected
- **THEN** it contains no construction of, import of, or reference to a domain-routing target type

### Requirement: Quality Gate introduces no production or lifecycle decision

The system SHALL NOT write to canonical bundle storage as part of Quality Gate evaluation, SHALL NOT create a `verified` mark, SHALL NOT alter an OKF `status`, and SHALL NOT decide legal identity. A `PASS` or `PASS_WITH_WARNINGS` outcome SHALL mean only that the output is eligible to proceed to the Producer; it SHALL NOT mean incorporation or automatic publication.

#### Scenario: No canonical write occurs

- **WHEN** the Quality Gate executes, regardless of the resulting state
- **THEN** no artifact is written to canonical bundle storage by this capability

#### Scenario: PASS does not imply publication

- **WHEN** the Quality Gate result state is `PASS` or `PASS_WITH_WARNINGS`
- **THEN** the result asserts only eligibility to proceed
- **AND** no publication, incorporation, or lifecycle mutation is performed or implied by this capability

