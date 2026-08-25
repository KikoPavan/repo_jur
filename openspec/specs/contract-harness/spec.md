# contract-harness Specification

## Purpose
Define schema-independent shared types and safety guards used by future Legal Knowledge and Judicial Process pipeline stages.
## Requirements
### Requirement: Actor references use canonical forms

The system SHALL accept Actor references in the syntactic forms `human:<id>`, `process:<id>`, and `<producer>/<version>`, with every component non-empty and free of the grammar's structural separators (`:` for the principal kind, `/` for the producer/version form). No identifier character whitelist is imposed. The system SHALL reject malformed references.

#### Scenario: Canonical Actors are accepted

- **WHEN** a caller validates `human:operator-1`, `process:ingress-1`, or `collector/1.0`
- **THEN** the Actor reference is accepted
- **AND** its kind and components remain available to the caller

#### Scenario: Malformed Actor is rejected

- **WHEN** an Actor has an empty component, a component containing a structural separator, or mixes incompatible forms
- **THEN** validation fails before the Actor is used

### Requirement: Evidence references remain under an allowed root

The system SHALL accept only relative evidence paths that resolve beneath a caller-provided allowed root and SHALL reject absolute paths, traversal segments, and normalization or symlink escapes.

#### Scenario: Safe evidence reference is resolved

- **WHEN** a caller validates a relative nested path beneath the allowed root
- **THEN** the system returns its resolved path beneath that root

#### Scenario: Escaping evidence reference is rejected

- **WHEN** a reference is absolute, contains a parent traversal segment, or resolves through a symlink outside the allowed root
- **THEN** validation fails before the path is read or written

### Requirement: Canonical shared result states are available

The system SHALL expose Quality Gate states serialized exactly as `PASS`, `PASS_WITH_WARNINGS`, and `FAIL`; critical-validation states serialized exactly as `OK`, `WARNING`, and `REVIEW_REQUIRED`; and route targets serialized exactly as `legal_knowledge`, `judicial_process`, and `review_required`.

#### Scenario: Shared states serialize canonically

- **WHEN** a caller serializes a gate state, critical-validation status, or route target
- **THEN** the emitted value exactly matches its canonical vocabulary

#### Scenario: Critical validation has no findings by default

- **WHEN** a critical-validation result is created with a valid status and no findings
- **THEN** its findings collection is empty and independent from other result instances

### Requirement: Only the Legal Knowledge domain may target the Legal bundle

The system SHALL permit a write target that resolves at or beneath the configured Legal Knowledge bundle root only when the acting domain is `legal_knowledge`, and SHALL reject every other acting domain — including `judicial_process` and `review_required`.

#### Scenario: Non-Legal target in Legal bundle is rejected

- **WHEN** the acting domain is `judicial_process` or `review_required` and the target resolves beneath the Legal bundle root
- **THEN** authorization fails before any write occurs

#### Scenario: Legal target in Legal bundle is allowed

- **WHEN** the acting domain is `legal_knowledge` and the target resolves beneath the Legal bundle root
- **THEN** the guard accepts the resolved target

### Requirement: Common contracts remain domain-schema independent

The common contract layer SHALL NOT import or embed Legal Knowledge schema fields or Judicial Process schema fields.

#### Scenario: Contract module is inspected for coupling

- **WHEN** the common contract source and imports are inspected
- **THEN** no Legal or Process schema module or schema symbol is referenced

### Requirement: Bounded-context conformance and regression verification

The system SHALL provide an automated, local operational mechanism to verify conformance and regression across both Legal Knowledge and Judicial Process bounded-context flows, proving that the canonical Legal bundle remains strictly isolated and that all Stage 1–9 contracts and invariants are satisfied.

#### Scenario: End-to-end pipeline flows run conformantly

- **WHEN** the conformance runner executes both the Legal Knowledge and Judicial Process pipeline flows end-to-end using controlled, deterministic synthetic fixtures
- **THEN** all individual stages (Ingress, Preflight, SHA validation, Preservation, Conversion, Critical-data validation, Quality Gate, Domain Routing, Semantic Review, and Producer publication) execute successfully
- **AND** all shared and domain-specific contract schemas are satisfied
- **AND** the Judicial Process conformance flow ends strictly at the authorized Judicial Process producer and canonical process-storage boundary, never implying or invoking Judicial Process Retrieval (which remains out of scope)

#### Scenario: Bounded-context storage is strictly isolated

- **WHEN** the Judicial Process pipeline flow runs end-to-end and publishes process candidates
- **THEN** all resulting process artifacts are written exclusively to isolated process storage
- **AND** the canonical Legal bundle remains completely untouched (zero writes under the Legal bundle root)

#### Scenario: Legal Knowledge Retrieval remains Zero-Write and isolated

- **WHEN** the retrieval sync, rebuild, and search paths are executed
- **THEN** they operate strictly in read-only mode over the canonical Legal bundle (Zero-Write)
- **AND** they never access, index, or reference Judicial Process storage, symbols, or retrieval mechanisms

#### Scenario: Real-corpus regression tests are executed successfully

- **WHEN** the regression test runner executes the test suite over frozen real-corpus PDF fixtures (such as `AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, and `L10.406_CC_2002.pdf`)
- **THEN** all assertions on reading order preservation, repetitive header/footer removal, signature blocks, and legal citations pass against lightweight git-tracked goldens in `tests/test_conformance/golden/`
- **AND** the default acceptance gate runs offline and deterministically, never depending on live nondeterministic external OCR/LLM output
- **AND** no existing functional capabilities are broken

#### Scenario: Source-inspection validates domain-schema independence

- **WHEN** static source-inspection checks are executed over the codebase
- **THEN** no prohibited coupling or import of domain-specific schemas is found in the common contract layer
- **AND** the core conversion package remains completely independent of domain-specific producers

#### Scenario: Conformance CLI command executes successfully

- **WHEN** the operator invokes the local CLI command `repo-jur test conformance`
- **THEN** the runner invokes pytest through the active Python interpreter using `sys.executable -m pytest` with two explicit bounded executions over `tests/test_conformance/` (one for conformance, one for regression)
- **AND** a structured non-canonical derived report is produced at `var/conformance/report.json` (or overridden location) distinguishing `CONFORMANCE_FAILURE`, `REGRESSION_FAILURE`, and `ENVIRONMENT_CONFIGURATION_ERROR`
- **AND** returns exit code 0 on success, or a deterministic non-zero exit code on failure

