# shared-conversion-core Specification

## Purpose
TBD - created by archiving change stage3-shared-conversion-core. Update Purpose after archive.
## Requirements
### Requirement: Preserved evidence is the Shared Conversion Core input

The system SHALL begin Shared Conversion Core processing from a stable, resolvable evidence reference produced after conformant evidence preservation. The Stage 3 boundary SHALL NOT treat the transport envelope or an arbitrary unpreserved caller path as its evidence contract.

#### Scenario: Preserved evidence reference is accepted

- **WHEN** the Shared Conversion Core receives a resolvable reference to PDF evidence that has completed conformant ingress and preservation
- **THEN** the referenced PDF bytes are made available to the conversion behavior
- **AND** conversion operates on that preserved evidence

#### Scenario: Evidence reference cannot be resolved

- **WHEN** the supplied preserved-evidence reference cannot be resolved to readable PDF evidence
- **THEN** conversion does not proceed as a successful execution
- **AND** no canonical bundle artifact is written

### Requirement: Existing conversion behavior is reused without duplication

For the same PDF evidence and equivalent conversion configuration, the Shared Conversion Core SHALL preserve the observable PDF-to-Markdown behavior already established by the juridical PDF conversion capability. Introduction of the shared boundary SHALL NOT create an independent second conversion behavior or silently replace the configured conversion or OCR engine. Preserving the existing behavior does not preclude the single, FROZEN-required boundary normalization defined by the Literal Markdown and technical information remain separate requirement.

#### Scenario: Shared boundary and direct conversion receive equivalent input

- **WHEN** the same PDF evidence is processed through the Shared Conversion Core and through the existing direct conversion behavior with equivalent configuration
- **THEN** both executions produce equivalent page-level conversion outcomes, equivalent literal source content and an equivalent canonical page-marker sequence
- **AND** the only permitted Markdown difference is the FROZEN-required removal of technical routing/method comments from the literal body exposed by the shared boundary, plus legitimate per-run telemetry

#### Scenario: Existing direct conversion remains available

- **WHEN** the Shared Conversion Core capability is introduced
- **THEN** the pre-existing direct conversion behavior remains available without a breaking behavioral change

### Requirement: Literal Markdown and technical information remain separate

The Shared Conversion Core SHALL expose the literal Markdown and the technical conversion report as separate artifacts. Technical routing information, OCR provider or model identity, warnings, errors, timing telemetry, and other operational metadata SHALL NOT be introduced into the Markdown body by the shared boundary. Technical routing/method comments emitted by the existing converter (e.g. `<!-- método: ... -->`) SHALL NOT remain in the literal Markdown body exposed by the shared boundary; the boundary SHALL normalize them out while preserving the literal source content and the canonical page-marker sequence, and the per-page method SHALL remain recorded in the technical conversion report.

#### Scenario: Successful conversion produces separate artifacts

- **WHEN** preserved PDF evidence is converted successfully
- **THEN** the result exposes the literal Markdown separately from the technical conversion report
- **AND** technical metadata remains outside the Markdown body
- **AND** no technical routing/method comment (e.g. `<!-- método: ... -->`) remains in the exposed Markdown body

#### Scenario: Page markers remain part of the literal artifact

- **WHEN** the converted PDF contains N physical pages
- **THEN** the Markdown preserves the canonical page-marker sequence for those pages
- **AND** the shared boundary does not remove, duplicate, reorder, or renumber those markers
- **AND** the per-page method continues to be recorded in the technical conversion report rather than in the Markdown body

### Requirement: Conversion result remains traceable to the resolved evidence

The technical conversion result SHALL retain sufficient physical traceability to identify the exact evidence processed, including its SHA-256, byte size, physical page count, and page-level conversion outcomes.

#### Scenario: Traceability identifies converted evidence

- **WHEN** preserved evidence is processed
- **THEN** the technical result identifies the processed evidence by SHA-256 and byte size
- **AND** records its physical page count and page-level outcomes

#### Scenario: Evidence bytes differ

- **WHEN** two resolved evidence objects contain different bytes
- **THEN** their technical traceability SHALL NOT represent them as the same physical evidence hash

### Requirement: Shared boundary remains storage-provider and engine neutral

The Shared Conversion Core contract SHALL NOT require a specific storage provider, bucket, URI scheme, conversion provider, OCR provider, OCR model, or compatibility client as an architectural dependency. Concrete resolution and conversion mechanisms remain implementation choices behind the shared boundary.

#### Scenario: Current local evidence storage is used

- **WHEN** preserved evidence is supplied by the currently configured local storage implementation
- **THEN** the Shared Conversion Core can process the resolvable reference
- **AND** the local representation is not promoted to a mandatory architectural storage scheme

#### Scenario: Conversion implementation metadata is recorded

- **WHEN** a concrete conversion or OCR implementation is used
- **THEN** implementation-specific information may be recorded in the technical artifact
- **AND** it is not injected into the literal Markdown body or treated as a domain rule

### Requirement: Stage 3 introduces no downstream domain decision

The Shared Conversion Core SHALL remain domain-neutral. It SHALL NOT assign a Phase 1 Quality Gate result, select a Legal Knowledge or Judicial Process route, apply domain schemas, perform semantic review or enrichment, invoke a Producer, publish canonical bundle content, or perform retrieval.

#### Scenario: Conversion completes successfully

- **WHEN** the Shared Conversion Core completes conversion of preserved evidence
- **THEN** it returns only the conversion artifacts owned by Stage 3
- **AND** no Quality Gate or bounded-context decision is assigned by this capability

#### Scenario: Conversion fails

- **WHEN** evidence resolution or PDF conversion fails
- **THEN** the failure remains a conversion-stage outcome
- **AND** no downstream routing, production, canonical publication, or retrieval operation is performed
