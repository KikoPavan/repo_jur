## ADDED Requirements

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
