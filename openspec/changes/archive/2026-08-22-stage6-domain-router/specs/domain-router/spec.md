# domain-router Specification

## Purpose
Define the Stage 6 boundary that deterministically selects exactly one of the three route targets — `legal_knowledge`, `judicial_process`, `review_required` — strictly after the Phase 1 Quality Gate, from conformant Phase 1 artifacts plus the Critical-Data Validation status and a validated routing context carrying the approved initial routing signal `requested_domain` (explicit workflow/operator intent), without hidden semantic classification, document-content inference, enrichment, YAML generation, Producer behavior, publication, Phase 1 body mutation, or any write to canonical bundle or process storage, and with routing metadata confined to an operational/technical observability record and a minimal operational route command.

## ADDED Requirements

### Requirement: Domain routing consumes only conformant Phase 1 artifacts

The system SHALL begin domain routing from Phase 1 artifacts produced by the Shared Conversion Core and the Phase 1 Quality Gate (literal Markdown and a technical conversion report that records the Quality Gate outcome). The Stage 6 boundary SHALL NOT treat an unconverted evidence reference, an arbitrary caller-supplied document, or a raw PDF as its input contract, SHALL NOT request or perform any further conversion, SHALL NOT resolve evidence, and SHALL NOT invoke OCR.

#### Scenario: Conformant Phase 1 artifacts are accepted

- **WHEN** domain routing receives Phase 1 artifacts (literal Markdown and technical conversion report) produced by the Shared Conversion Core and Quality Gate
- **THEN** routing evaluates that already-converted content without requesting or performing further conversion, resolving evidence, or invoking OCR

#### Scenario: Unconverted input cannot reach routing

- **WHEN** an unconverted evidence reference, raw PDF, or arbitrary caller-supplied document is presented to the routing boundary
- **THEN** routing does not proceed as a successful execution
- **AND** no routing decision or routing observability record is produced

### Requirement: Routing occurs strictly after the Phase 1 Quality Gate

The system SHALL route only Phase 1 artifacts whose technical conversion report records a Quality Gate outcome of `PASS` or `PASS_WITH_WARNINGS` (the serialized values). When the recorded gate outcome is `FAIL`, the system SHALL stop: no domain routing occurs and no routing decision is produced. When the technical report is unparseable or does not record a Quality Gate outcome, the system SHALL NOT route and SHALL NOT produce a routing decision.

#### Scenario: PASS outcome is eligible for routing

- **WHEN** the technical report records the Quality Gate outcome `PASS`
- **THEN** routing proceeds to the Critical-Data Validation and routing-signal evaluation steps

#### Scenario: PASS WITH WARNINGS outcome is eligible for routing

- **WHEN** the technical report records the Quality Gate outcome `PASS_WITH_WARNINGS`
- **THEN** routing proceeds to the Critical-Data Validation and routing-signal evaluation steps

#### Scenario: FAIL outcome stops routing

- **WHEN** the technical report records the Quality Gate outcome `FAIL`
- **THEN** domain routing stops
- **AND** no routing decision is produced
- **AND** no `legal_knowledge`, `judicial_process`, or `review_required` outcome is emitted

#### Scenario: Absent gate outcome blocks routing

- **WHEN** the technical report does not record a Quality Gate outcome or cannot be parsed
- **THEN** domain routing does not proceed
- **AND** no routing decision is produced

### Requirement: Critical-Data Validation REVIEW_REQUIRED routes to review_required before any signal

The system SHALL route to `review_required` whenever the Critical-Data Validation status supplied with the Phase 1 artifacts is `REVIEW_REQUIRED`, regardless of any routing context, and SHALL perform this routing before evaluating any routing signal. A Critical-Data Validation status of `OK` or `WARNING` SHALL NOT, by itself, select a domain route and SHALL NOT route to `review_required`; routing then proceeds to the routing-signal evaluation step.

#### Scenario: REVIEW_REQUIRED critical status selects review_required

- **WHEN** the Critical-Data Validation status is `REVIEW_REQUIRED` and the recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS`
- **THEN** the routing decision is `review_required`
- **AND** the decision is made before any routing signal is evaluated

#### Scenario: OK critical status does not decide the route

- **WHEN** the Critical-Data Validation status is `OK` and the recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS`
- **THEN** routing proceeds to the routing-signal evaluation step
- **AND** the `OK` status does not by itself select `legal_knowledge`, `judicial_process`, or `review_required`

### Requirement: The initial permitted routing signal is requested_domain

The system SHALL select `legal_knowledge` or `judicial_process` only through the single permitted routing signal `requested_domain`, carried in a validated routing context that represents explicit workflow/operator intent. The value of `requested_domain` SHALL be exactly one of `legal_knowledge` or `judicial_process` (the serialized route-target values). The system SHALL NOT derive `requested_domain`, or any routing signal, from the content of the literal Markdown or the technical report, and SHALL NOT accept any routing signal other than `requested_domain` in this capability. Collector-provided candidate hints without canonical authority (such as the legal hints of the ingress transport contract, defined as candidates that do not create identity, do not decide Duplicate Act Handling, do not define filename/slug, and have no frontmatter authority) SHALL NOT select a domain route in this capability.

#### Scenario: requested_domain selects legal_knowledge

- **WHEN** the validated routing context carries `requested_domain` with value `legal_knowledge`, and the recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS` and the Critical-Data Validation status is `OK` or `WARNING`
- **THEN** the routing decision is `legal_knowledge`

#### Scenario: requested_domain selects judicial_process

- **WHEN** the validated routing context carries `requested_domain` with value `judicial_process`, and the recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS` and the Critical-Data Validation status is `OK` or `WARNING`
- **THEN** the routing decision is `judicial_process`

#### Scenario: Candidate hints never select a domain

- **WHEN** a routing context is evaluated and no `requested_domain` signal is present, or a candidate hint key without canonical authority is referenced
- **THEN** no hint selects `legal_knowledge` or `judicial_process`
- **AND** any signal key other than `requested_domain` is outside the permitted vocabulary

#### Scenario: Signal is never derived from document content

- **WHEN** domain routing evaluates Phase 1 artifacts whose literal Markdown or report content is inspected
- **THEN** the routing decision is derived solely from the recorded Quality Gate outcome, the Critical-Data Validation status, and the validated routing context
- **AND** no `requested_domain` value is inferred, guessed, or defaulted from document content

### Requirement: Routing follows the approved fixed precedence

The system SHALL evaluate the routing decision in exactly the following fixed order: (1) a recorded Quality Gate outcome of `FAIL` stops routing and produces no routing decision; (2) a Critical-Data Validation status of `REVIEW_REQUIRED` produces the routing decision `review_required` before any routing signal is evaluated; (3) `requested_domain` with value `legal_knowledge` produces the routing decision `legal_knowledge`; (4) `requested_domain` with value `judicial_process` produces the routing decision `judicial_process`; (5) `requested_domain` absent produces the routing decision `review_required`.

#### Scenario: FAIL stops before any signal

- **WHEN** the recorded Quality Gate outcome is `FAIL` and any routing context is supplied
- **THEN** routing stops
- **AND** no routing decision is produced

#### Scenario: Critical REVIEW_REQUIRED precedes the signal

- **WHEN** the Critical-Data Validation status is `REVIEW_REQUIRED` and the validated routing context carries `requested_domain` with value `legal_knowledge` or `judicial_process`
- **THEN** the routing decision is `review_required`
- **AND** the signal value does not change the decision

#### Scenario: Signal selects the domain when earlier steps pass

- **WHEN** the recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS`, the Critical-Data Validation status is `OK` or `WARNING`, and `requested_domain` is present
- **THEN** the routing decision is the domain named by `requested_domain`

#### Scenario: Absent requested_domain routes to review_required

- **WHEN** the recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS`, the Critical-Data Validation status is `OK` or `WARNING`, and `requested_domain` is absent
- **THEN** the routing decision is `review_required`

### Requirement: Missing, conflicting, or ambiguous routing signals route to review_required

The system SHALL route to `review_required` when no routing signal is supplied, when the supplied routing context carries no permitted signal (including an empty context), when two or more permitted signals select different domains (conflict), or when the routing signals are otherwise ambiguous. The system SHALL NOT invent, infer, or default a domain selection from any missing, conflicting, or ambiguous signal state.

#### Scenario: No routing context is supplied

- **WHEN** domain routing runs without a routing context and no other rule selects a different outcome
- **THEN** the routing decision is `review_required`

#### Scenario: Routing context carries no permitted signal

- **WHEN** a routing context is supplied but contains no `requested_domain` signal and no other rule selects a different outcome
- **THEN** the routing decision is `review_required`

#### Scenario: Permitted signals conflict

- **WHEN** two or more permitted routing signals select different domains
- **THEN** the routing decision is `review_required`
- **AND** no domain is invented or defaulted from the conflicting signals

### Requirement: Configuration errors are surfaced through a dedicated contract

The system SHALL treat a routing context that violates the fixed routing-context contract — a signal key outside the permitted vocabulary, a `requested_domain` value that is not exactly `legal_knowledge` or `judicial_process`, a malformed value, or a structurally invalid context — as a configuration error surfaced through a dedicated configuration-error contract, and SHALL NOT convert such an error into a routing decision, including `review_required`, and SHALL NOT select a domain route. The `review_required` outcome is reserved for valid input with no authorized decisive signal or other permitted ambiguity.

#### Scenario: Unrecognized signal key is a configuration error

- **WHEN** a routing context contains a signal key outside the permitted vocabulary (any key other than `requested_domain`)
- **THEN** the dedicated configuration error is raised
- **AND** no `legal_knowledge`, `judicial_process`, or `review_required` routing decision is produced for that execution

#### Scenario: Invalid requested_domain value is a configuration error

- **WHEN** a routing context carries `requested_domain` with a value other than exactly `legal_knowledge` or `judicial_process`
- **THEN** the dedicated configuration error is raised
- **AND** no routing decision is produced for that execution

#### Scenario: Malformed routing context is a configuration error

- **WHEN** a routing context is structurally invalid or contains a signal value of the wrong shape
- **THEN** the dedicated configuration error is raised
- **AND** no routing decision is produced for that execution

### Requirement: Routing never mutates Phase 1 artifacts

The system SHALL NOT modify, rewrite, autocorrect, complete, paraphrase, translate, or otherwise alter the literal Markdown body or the technical conversion report of the Phase 1 artifacts as part of domain routing. The literal Markdown content SHALL be identical, byte for byte, before and after routing, and the serialized technical report SHALL be identical, byte for byte, before and after routing.

#### Scenario: Markdown is unchanged after routing

- **WHEN** domain routing executes against Phase 1 artifacts, regardless of the resulting decision
- **THEN** the SHA-256 hash of the literal Markdown after routing equals the SHA-256 hash of the literal Markdown before routing

#### Scenario: Technical report is unchanged after routing

- **WHEN** domain routing executes against Phase 1 artifacts, regardless of the resulting decision
- **THEN** the serialized technical report after routing equals the serialized technical report before routing

### Requirement: Routing performs no semantic classification or hidden processing

The system SHALL NOT perform semantic classification of document content, SHALL NOT infer or derive any routing signal from document content, SHALL NOT invoke any LLM or semantic model, SHALL NOT perform enrichment, SHALL NOT generate YAML, SHALL NOT behave as a Producer, SHALL NOT publish, and SHALL NOT apply a domain-specific schema as part of domain routing. When the routing implementation source is inspected, it SHALL contain no reference to a semantic classifier, an LLM or semantic model client, an enrichment engine, a Producer, or a domain schema.

#### Scenario: No hidden classification selects a route

- **WHEN** domain routing executes
- **THEN** the decision is derived solely from the recorded Quality Gate outcome, the Critical-Data Validation status, and the validated routing context
- **AND** no content classification, content-derived signal, LLM call, enrichment, YAML generation, or domain-schema application occurs

#### Scenario: Routing implementation is source-inspected for prohibited coupling

- **WHEN** the domain routing implementation source is inspected
- **THEN** it references no semantic classifier, no LLM or semantic model client, no enrichment engine, no Producer component, no domain schema, and no canonical publication path

### Requirement: Routing performs no write and no bundle-guard invocation

The system SHALL NOT write to canonical bundle storage, SHALL NOT write to judicial-process storage, and SHALL NOT invoke the Legal bundle write guard as part of domain routing. The routing decision is the domain value that downstream producer stages pass to the Legal bundle write guard when they write; routing itself SHALL perform no write of any kind.

#### Scenario: No canonical or process-storage write occurs

- **WHEN** domain routing executes, regardless of the resulting decision
- **THEN** no artifact is written to canonical bundle storage or to judicial-process storage by this capability

#### Scenario: The bundle write guard is not invoked by routing

- **WHEN** domain routing executes
- **THEN** the Legal bundle write guard is not invoked
- **AND** the routing decision remains available for downstream producer stages to consume

### Requirement: Routing is deterministic

The system SHALL compute the routing decision as a pure deterministic function of the Phase 1 artifacts, the Critical-Data Validation status, and the validated routing context: identical inputs SHALL yield the identical routing decision on every evaluation, and the decision SHALL NOT depend on execution order, per-run identifiers, timestamps, durations, or any non-deterministic source.

#### Scenario: Repeated evaluation of identical inputs is identical

- **WHEN** the same Phase 1 artifacts, Critical-Data Validation status, and routing context are evaluated twice
- **THEN** the second routing decision equals the first routing decision

### Requirement: Routing respects the exact route-target domain outcomes

The system SHALL produce a routing decision that is exactly one of the three route-target values — `legal_knowledge`, `judicial_process`, `review_required` — with serialized values matching the canonical route-target vocabulary. No other routing outcome SHALL be produced by this capability.

#### Scenario: Every decision is one of the three canonical targets

- **WHEN** domain routing produces a decision
- **THEN** the decision serializes exactly as `legal_knowledge`, `judicial_process`, or `review_required`

### Requirement: Routing metadata belongs only to operational/technical artifacts

The system SHALL confine routing metadata — the routing decision, its inputs, and its reason — to operational/technical artifacts: a routing observability record written outside the canonical bundle and outside the Phase 1 artifacts, and the operational route command's output. Routing metadata SHALL NOT be introduced into the literal Markdown body or into the Phase 1 technical report. The routing observability record SHALL NOT contain document content, SHALL NOT contain full critical identifier values, and SHALL NOT contain routing-signal values; it SHALL reference the processed evidence by its provenance hash and SHALL record routing-signal presence (keys) rather than signal values.

#### Scenario: Routing metadata does not enter Phase 1 artifacts

- **WHEN** domain routing executes
- **THEN** the routing decision and reason appear only in the operational/technical routing observability record and the operational route command output
- **AND** neither the literal Markdown body nor the Phase 1 technical report contains routing metadata

#### Scenario: Observability record is content-safe and located outside the bundle

- **WHEN** a routing observability record is written
- **THEN** the record is stored outside the canonical bundle and outside the Phase 1 artifacts
- **AND** the record contains no document content, no full critical identifier value, and no routing-signal value
- **AND** the record identifies the processed evidence by its provenance hash and records routing-signal presence without signal values

### Requirement: Domain routing is independent of page-level routing semantics

The system SHALL keep the domain routing capability independent of the page-level routing semantics of the conversion pipeline. Domain routing SHALL NOT alter, consult, or depend on page-level routing behavior, and the page-level routing implementation SHALL remain unchanged by this capability.

#### Scenario: Page-level routing is untouched

- **WHEN** the domain routing capability is introduced
- **THEN** the page-level routing semantics of the conversion pipeline remain unchanged
- **AND** domain routing decisions do not depend on page-level routing outputs

### Requirement: Operational route command computes and records the decision

The system SHALL provide a minimal operational route command that accepts the Phase 1 artifacts (literal Markdown file and technical report file), an optional `requested_domain` value supplied explicitly as workflow/operator intent, and an optional validated routing context file, computes the routing decision deterministically, writes the routing observability record, and reports the outcome. The command SHALL NOT modify the Phase 1 artifacts, SHALL NOT invoke conversion or OCR, SHALL exit with a non-zero status and SHALL NOT emit a routing decision when the recorded Quality Gate outcome is `FAIL`, and SHALL preserve the behavior of the existing conversion command unchanged.

#### Scenario: Route command records the decision

- **WHEN** the route command is invoked with conformant Phase 1 artifact files and an explicit `requested_domain` value of `legal_knowledge` or `judicial_process`
- **THEN** the command computes the deterministic routing decision
- **AND** writes the routing observability record outside the canonical bundle and outside the Phase 1 artifacts
- **AND** reports the decision in its output

#### Scenario: Route command never mutates the artifacts

- **WHEN** the route command is invoked with Phase 1 artifact files
- **THEN** the literal Markdown file and the technical report file are unchanged after the command completes

#### Scenario: Route command stops on a FAIL gate

- **WHEN** the route command is invoked with a technical report whose recorded Quality Gate outcome is `FAIL`
- **THEN** the command exits with a non-zero status
- **AND** emits no routing decision
- **AND** writes no routing decision record

#### Scenario: Existing conversion command behavior is preserved

- **WHEN** the operational route command is introduced
- **THEN** the pre-existing conversion command surface and behavior remain unchanged
