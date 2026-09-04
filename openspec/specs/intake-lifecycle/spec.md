# intake-lifecycle Specification

## Purpose
TBD - created by archiving change 2026-09-04-operational-intake-lifecycle. Update Purpose after archive.
## Requirements
### Requirement: Mandatory Operational Classification
The system SHALL only process raw PDFs located in recognized subdirectories of `input/`.
- **Mapping**: `legislacao/`, `jurisprudencia/`, `temas/`, `precedentes/` MUST map to their respective OKF types.
- **Root Files**: PDFs located in the root of `input/` SHALL NOT be processed and SHALL be reported as `SKIP_UNCLASSIFIED`.

#### Scenario: PDF in jurisprudencia/ is correctly classified
- **GIVEN** `input/jurisprudencia/doc.pdf` exists
- **WHEN** the intake scan runs
- **THEN** the entry is created with `okf_type: Jurisprudencia`

### Requirement: Pipeline Orchestration via Public APIs
The system SHALL orchestrate the full processing flow using established public APIs for Phase 1, Router, Semantic Review, and Producer.
- **Sequence**: `Ingress → Phase 1 → Router → Semantic Review → Producer.produce()`.
- **Producer Authority**: The system SHALL NOT bypass `produce()` for bundle writes or materiality checks.

#### Scenario: Semantic Review occurs before Publication
- **GIVEN** a PDF is preserved in Object Storage
- **WHEN** the orchestrator runs the flow
- **THEN** it executes `LegalSemanticReviewEngine.review()`
- **AND** passes the result to `legal_producer.produce()`

### Requirement: Durable Strong Lease with Heartbeat
The system SHALL maintain execution ownership using a `claim_id` (UUID) and a periodically updated `heartbeat_at` timestamp.
- **Heartbeat**: SHALL be updated after each major pipeline stage.
- **Enforcement**: State updates SHALL fail if the current process `claim_id` does not match the registry owner.

#### Scenario: Stale lease takeover requires new claim_id
- **GIVEN** a stale registry entry with `claim_id: A`
- **WHEN** a new process takes over
- **THEN** it issues a new `claim_id: B`
- **AND** the old process with `claim_id: A` is blocked from any further updates.

### Requirement: Safe Duplicate Discarding
The system SHALL only discard a duplicate of a `PUBLISHED` document if the original artifacts (Object Storage and Bundle) are verified as present and consistent.

#### Scenario: Duplicated PDF is preserved if original Concept is missing
- **GIVEN** SHA-256 `X` is marked `PUBLISHED`
- **AND** the concept file in `bundle/` was manually deleted
- **WHEN** a new copy of `X` arrives
- **THEN** the system marks the entry as `FAILED`
- **AND** preserves the new PDF copy in `failed/`.

