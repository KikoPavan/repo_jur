## ADDED Requirements

### Requirement: Phase 1 conversion artifacts are the Critical-Data Validation input

The system SHALL begin Critical-Data Validation processing from the Shared Conversion Core output (Phase 1 conversion artifacts containing literal Markdown and a technical conversion report). The Stage 4 boundary SHALL NOT treat an unconverted evidence reference or an arbitrary caller-supplied document as its input contract.

#### Scenario: Phase 1 conversion artifacts are accepted

- **WHEN** Critical-Data Validation receives Phase 1 conversion artifacts produced by the Shared Conversion Core
- **THEN** the literal Markdown and technical conversion report are made available to the validation behavior
- **AND** validation operates on that already-converted content without requesting or performing further conversion

### Requirement: Critical-Data Validation never mutates the literal Markdown body

The system SHALL NOT modify, rewrite, autocorrect, complete, paraphrase, translate, or otherwise alter the literal Markdown body of the Phase 1 conversion artifacts as part of Critical-Data Validation. The literal Markdown content SHALL be identical, byte for byte, before and after Critical-Data Validation executes.

#### Scenario: Markdown is unchanged after validation

- **WHEN** Critical-Data Validation executes against Phase 1 conversion artifacts, regardless of whether any finding is produced
- **THEN** the SHA-256 hash of the literal Markdown body after validation equals the SHA-256 hash of the literal Markdown body before validation

#### Scenario: A detected inconsistency does not trigger correction

- **WHEN** Critical-Data Validation detects a format or check-digit inconsistency in a critical field
- **THEN** the literal Markdown value for that field remains exactly as produced by conversion
- **AND** no digit, character, or value is invented, completed, or substituted to resolve the inconsistency

### Requirement: Critical-Data Validation result contains only status and findings

The system SHALL return a Critical-Data Validation result containing exactly a status value and a list of findings. The status SHALL be exactly one of `OK`, `WARNING`, or `REVIEW_REQUIRED`. Findings SHALL exist only in the technical layer and SHALL NOT be introduced into the literal Markdown body.

#### Scenario: Zero-rule default produces OK with no findings

- **WHEN** Critical-Data Validation executes with an empty rule registry (no rules supplied at validator construction)
- **THEN** the result status is `OK`
- **AND** the result findings list is empty

#### Scenario: OK asserts only that no inconsistency was detected

- **WHEN** the Critical-Data Validation result status is `OK`
- **THEN** the status asserts only that no inconsistency was detected by the applicable rules executed in this run
- **AND** the status does not assert complete validation, authenticity, legal correctness, legal verification, or that every candidate field was checked

#### Scenario: A registered rule detects an inconsistency

- **WHEN** a provenance-complete rule registered for a critical field detects a format or check-digit inconsistency
- **THEN** the result status is `WARNING` or `REVIEW_REQUIRED`
- **AND** the inconsistency is recorded as a finding in the result
- **AND** the finding does not appear as literal text inside the Markdown body

### Requirement: A validation rule requires full provenance metadata

The system SHALL NOT evaluate or register a deterministic format, length, check-digit, or structure validation rule for any critical identifier field unless the rule declares all of: a rule identifier, a rule version, a single conceptual applicability field (the identifier field(s) the rule applies to), a source or specification reference, a validation-logic version, and a declared failure severity (`failure_status`) of `WARNING` or `REVIEW_REQUIRED`. The system SHALL NOT generalize a rule for one critical field from a single observed document, single court sample, single OCR result, or a local convention lacking an authoritative, versioned specification.

#### Scenario: A rule missing provenance metadata is rejected

- **WHEN** a validation rule that omits the rule identifier, rule version, applicable field(s), source/specification reference, validation-logic version, or declared failure severity is supplied at validator construction
- **THEN** construction fails with the configuration error
- **AND** the rule is never stored in the registry or evaluated during Critical-Data Validation

#### Scenario: A rule declaring an invalid failure severity is rejected

- **WHEN** a validation rule supplied at validator construction declares a failure severity other than `WARNING` or `REVIEW_REQUIRED` (for example `OK`)
- **THEN** construction fails with the configuration error
- **AND** the rule is never stored in the registry or evaluated during Critical-Data Validation

#### Scenario: No normative rule ships by default

- **WHEN** Critical-Data Validation is introduced by this capability
- **THEN** the rule registry contains zero pre-populated rules
- **AND** every field is treated as unvalidated rather than inferring a rule from an unspecified convention

### Requirement: Rule failure severity is declared statically and never downgraded

Each validation rule SHALL declare its failure severity (`failure_status`, `WARNING` or `REVIEW_REQUIRED`) in its versioned rule definition, and the system SHALL NOT invent or reassign severity dynamically at validation time. Severity SHALL be ordered `OK < WARNING < REVIEW_REQUIRED`, and the system SHALL NOT return a result status lower than the declared failure severity of a finding it reports.

#### Scenario: Declared severity is honored

- **WHEN** a rule with declared failure severity `REVIEW_REQUIRED` detects an inconsistency
- **THEN** the result status is `REVIEW_REQUIRED`
- **AND** the result status is not lowered to `WARNING` or `OK` because of that finding

#### Scenario: Severity is not invented dynamically

- **WHEN** a rule with declared failure severity `WARNING` detects an inconsistency
- **THEN** the result status is `WARNING`
- **AND** the validator does not escalate that finding to `REVIEW_REQUIRED` on its own initiative

### Requirement: Global result status is the highest severity produced

The system SHALL compute the Critical-Data Validation result status as the highest severity produced by the findings of the enabled rules executed in the run: zero findings SHALL yield `OK`; findings of severity `WARNING` with no `REVIEW_REQUIRED` finding SHALL yield `WARNING`; any `REVIEW_REQUIRED` finding SHALL yield `REVIEW_REQUIRED`. All findings SHALL be preserved individually in the result.

#### Scenario: Only WARNING findings are produced

- **WHEN** the run produces one or more `WARNING` findings and no `REVIEW_REQUIRED` finding
- **THEN** the result status is `WARNING`
- **AND** every produced finding is present in the result findings list

#### Scenario: A REVIEW_REQUIRED finding dominates

- **WHEN** the run produces at least one `REVIEW_REQUIRED` finding alongside findings of any other severity
- **THEN** the result status is `REVIEW_REQUIRED`
- **AND** all findings, including the `WARNING` ones, are preserved in the result findings list

#### Scenario: Zero findings yield OK

- **WHEN** the run produces no findings
- **THEN** the result status is `OK`
- **AND** the result findings list is empty

### Requirement: Each rule discovers its own candidate fields

The system SHALL NOT use a universal central candidate extractor. Each validation rule SHALL deterministically discover its own candidate fields from the Phase 1 conversion artifacts, scoped by its applicability field and its own specification. Candidate discovery SHALL be read-only and SHALL NOT infer, repair, complete, silently normalize, or modify literal Markdown.

#### Scenario: Rule discovery does not modify Markdown

- **WHEN** an enabled rule discovers candidate fields in the Phase 1 conversion artifacts
- **THEN** the discovery reads the artifacts without modifying them
- **AND** the literal Markdown remains byte-identical after discovery and evaluation

#### Scenario: No central extractor is used

- **WHEN** Critical-Data Validation executes an enabled rule
- **THEN** the rule discovers its own candidates from the artifacts
- **AND** no shared candidate-extraction component outside the rule produces the candidates it evaluates

### Requirement: Critical Validation Profile selects enabled rules

The `profile` argument of the validator SHALL be a Critical Validation Profile declaring at least a profile identifier, a profile version, and the identifiers of the enabled rules. The profile SHALL select which registered rules are enabled and SHALL NOT route domains, classify semantically, define legal truth, bypass provenance, or override a rule's declared failure severity. The profile SHALL NOT declare the same enabled rule identifier more than once.

#### Scenario: Profile enables only the named rules

- **WHEN** a Critical Validation Profile names a rule identifier in its enabled rules
- **THEN** that rule is evaluated during Critical-Data Validation
- **AND** rules whose identifiers are not named are not evaluated

#### Scenario: Profile with no enabled rules is a zero-rule run

- **WHEN** a Critical Validation Profile declares no enabled rules
- **THEN** the result status is `OK`
- **AND** the result findings list is empty

#### Scenario: Profile does not alter declared severity

- **WHEN** a rule with declared failure severity `REVIEW_REQUIRED` detects an inconsistency while enabled by a profile
- **THEN** the result status is `REVIEW_REQUIRED`
- **AND** the profile does not change the rule's declared failure severity

### Requirement: Rule Registry Integrity

Within one validation run, the system SHALL allow at most one registered version for each rule identifier; duplicate rule-identifier registrations SHALL be invalid and SHALL be rejected at validator construction. Every enabled rule identifier in the Critical Validation Profile SHALL resolve to exactly one registered rule. An enabled rule identifier that does not resolve to exactly one registered rule SHALL be treated as a configuration error, surfaced through the dedicated configuration-error contract, and SHALL NOT be silently converted to a result status of `OK`. The Critical Validation Profile SHALL NOT declare the same enabled rule identifier more than once; duplicate enabled rule identifiers within a profile SHALL be treated as a configuration error before any rule executes.

#### Scenario: Duplicate rule registration is rejected at construction

- **WHEN** the rules supplied at validator construction include more than one registration of the same rule identifier
- **THEN** construction fails with the configuration error
- **AND** the registry never contains more than one version of that rule identifier

#### Scenario: Unresolvable enabled rule is a configuration error

- **WHEN** a Critical Validation Profile names an enabled rule identifier that does not resolve to exactly one registered rule
- **THEN** the configuration error is raised
- **AND** validation does not complete as a successful zero-finding run
- **AND** the configuration error is never converted to `status=OK`

#### Scenario: Duplicate enabled rule identifiers in a profile are a configuration error

- **WHEN** a Critical Validation Profile declares the same enabled rule identifier more than once
- **THEN** the configuration error is raised before any rule executes
- **AND** the rule is not executed more than once and no duplicate findings are produced

#### Scenario: Zero enabled rules remain distinct from a misconfiguration

- **WHEN** a Critical Validation Profile declares no enabled rules at all
- **THEN** the result status is `OK` with no findings
- **AND** this zero-rule outcome is not treated as an error

### Requirement: Configuration errors are surfaced through a dedicated error contract

Invalid registry or profile resolution SHALL be surfaced through a dedicated configuration-error contract, `CriticalValidationConfigurationError`: a rule supplied at validator construction that omits required provenance metadata; a rule supplied at validator construction that declares an invalid required metadata value — specifically a failure severity other than `WARNING` or `REVIEW_REQUIRED`; more than one registration of the same rule identifier; an enabled rule identifier in the Critical Validation Profile that does not resolve to exactly one registered rule; or duplicate enabled rule identifiers within a Critical Validation Profile. A configuration error SHALL NOT be converted into a successful result status, including `OK`.

#### Scenario: A configuration error is raised and never converted to OK

- **WHEN** validator construction or profile resolution encounters missing required provenance, an invalid declared failure severity, a duplicate rule identifier, an unresolvable enabled rule identifier, or duplicate enabled rule identifiers in a profile
- **THEN** the dedicated configuration error is raised
- **AND** no `OK` result status is produced for that run

### Requirement: The rule registry lifecycle is deterministic

The system SHALL receive the full set of validation rules at validator construction, validate required provenance metadata and unique rule identifiers at that point, store the validated rules in an immutable internal registry keyed by rule identifier, and default to an empty registry when no rules are supplied.

#### Scenario: Construction with no rules yields an empty registry

- **WHEN** the validator is constructed without rules
- **THEN** the internal registry is empty
- **AND** validation behaves as a zero-rule run (`OK`, no findings)

#### Scenario: Rules are validated and stored immutably at construction

- **WHEN** the validator is constructed with provenance-complete rules having unique rule identifiers
- **THEN** each rule is stored in the immutable internal registry keyed by its rule identifier
- **AND** the registry cannot be added to, removed from, or replaced after construction

#### Scenario: Construction with an invalid rule fails

- **WHEN** a rule supplied at construction omits required provenance or duplicates a rule identifier
- **THEN** construction fails with the configuration error
- **AND** the validator is not created with those rules

### Requirement: Inconsistency detection is scoped to enabled, specification-backed rules

The system SHALL NOT maintain a general duty to discover ambiguity or conflicting values in the converted content. The system SHALL detect and signal an inconsistency only through an enabled, specification-backed rule acting within its own authorized scope. When an enabled rule signals an inconsistency, ambiguity, or uncertainty in a critical field, the system SHALL represent it exclusively by escalating the result status to `WARNING` or `REVIEW_REQUIRED` and recording a corresponding finding. The system SHALL NOT silently choose between conflicting values, SHALL NOT promote a format-valid value to legal truth, and SHALL NOT expose any separate "absence" or "unknown" status outside the three defined status values.

#### Scenario: A rule signals a conflict only within its authorized scope

- **WHEN** an enabled, specification-backed rule signals that a critical field within its authorized scope could hold more than one value
- **THEN** Critical-Data Validation does not select one value as authoritative
- **AND** the signal is represented only through a `WARNING` or `REVIEW_REQUIRED` status with an associated finding

#### Scenario: No ambiguity-scanning duty outside an authorized rule scope

- **WHEN** no enabled rule's specification authorizes detection of ambiguity or conflicting values for a critical field
- **THEN** Critical-Data Validation performs no such detection for that field
- **AND** the absence of a finding does not assert that no ambiguity or conflict exists

#### Scenario: A format-valid value is not treated as legally authoritative

- **WHEN** a critical field passes a registered format or check-digit rule
- **THEN** the result reflects only that the format check passed
- **AND** the result does not assert or imply that the value is legally correct or verified

### Requirement: Critical-Data Validation status is independent of the Phase 1 Quality Gate

The system SHALL keep the Critical-Data Validation result independent of the Phase 1 Quality Gate decision. Critical-Data Validation SHALL NOT construct, import, or assign a Quality Gate state. A `REVIEW_REQUIRED` critical-data status combined with a passing physical Quality Gate outcome SHALL NOT be treated by this capability as a Quality Gate failure.

#### Scenario: Critical-data status does not alter physical gate semantics

- **WHEN** Critical-Data Validation returns `REVIEW_REQUIRED` for content whose physical conversion outcome is otherwise sound
- **THEN** Critical-Data Validation itself assigns no PASS, PASS WITH WARNINGS, or FAIL outcome
- **AND** no Quality Gate state type is constructed, imported, or referenced by this capability

### Requirement: Critical-Data Validation introduces no domain-routing decision

The system SHALL remain domain-neutral. Critical-Data Validation SHALL NOT select a Legal Knowledge or Judicial Process route, SHALL NOT construct or import a domain-routing target type, and SHALL NOT apply a domain-specific schema.

#### Scenario: Validation completes without routing

- **WHEN** Critical-Data Validation completes for Phase 1 conversion artifacts
- **THEN** the result exposes only the status and findings owned by this capability
- **AND** no Legal Knowledge, Judicial Process, or review-required routing decision is assigned by this capability

#### Scenario: Domain-routing types are absent from the implementation

- **WHEN** the Critical-Data Validation implementation source is inspected
- **THEN** it contains no construction of, import of, or reference to a domain-routing target type

### Requirement: Critical-Data Validation excludes intra-document redundant-value comparison

The system SHALL NOT perform deterministic comparison of redundant values distributed across the same document as part of this capability. That comparison remains a separate, future capability.

#### Scenario: Redundant values are not cross-checked

- **WHEN** the same critical value appears more than once within a single document's converted content
- **THEN** Critical-Data Validation does not compare those occurrences against each other as part of this capability

### Requirement: Critical-Data Validation prohibits canonical publication and unrelated pipeline changes

The system SHALL NOT write to canonical bundle storage as part of Critical-Data Validation, and SHALL NOT change the existing converter, OCR provider, page-routing thresholds, cleaning behavior, report generation, or CLI as part of introducing this capability.

#### Scenario: No canonical write occurs

- **WHEN** Critical-Data Validation executes, regardless of the resulting status
- **THEN** no artifact is written to canonical bundle storage by this capability

#### Scenario: Upstream conversion behavior is unaffected

- **WHEN** Critical-Data Validation is introduced
- **THEN** the pre-existing Shared Conversion Core, converter, OCR, routing, cleaning, validation, report generation, and CLI behavior remain unchanged
