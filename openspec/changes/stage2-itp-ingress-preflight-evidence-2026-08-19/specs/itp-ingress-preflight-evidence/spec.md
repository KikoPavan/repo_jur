## ADDED Requirements

### Requirement: ITP/1.0 envelopes are single-evidence ZIP packages

The system SHALL accept an ITP/1.0 envelope as a ZIP archive containing exactly two regular, non-encrypted members at the archive root: `manifest.json` and `evidence.pdf`. Envelopes with any additional member, missing member, duplicate member name, directory member, symlink/hardlink/special member, absolute-path member, parent-traversal member, normalized-name collision, encrypted archive/member, or unsupported compression method SHALL be rejected during preflight.

#### Scenario: Canonical two-member envelope is accepted

- **WHEN** a ZIP archive contains exactly `manifest.json` and `evidence.pdf` as regular root members
- **THEN** preflight proceeds past container and member validation

#### Scenario: Extra or missing members are rejected

- **WHEN** a ZIP archive contains any member other than `manifest.json` and `evidence.pdf`, or is missing either one
- **THEN** the envelope is rejected before extraction

#### Scenario: Duplicate member names are rejected

- **WHEN** a ZIP archive contains two members with the same name
- **THEN** the envelope is rejected

#### Scenario: Unsafe member paths are rejected

- **WHEN** a member name is absolute, contains a parent traversal segment, or normalizes to a collision
- **THEN** the envelope is rejected before extraction

#### Scenario: Links and special members are rejected

- **WHEN** a member is a directory, symlink, hardlink, or other special member type
- **THEN** the envelope is rejected

#### Scenario: Encrypted or unsupported-compression archives are rejected

- **WHEN** the archive or a member is encrypted, or uses a compression method the implementation does not support
- **THEN** the envelope is rejected

### Requirement: Configurable preflight resource limits

The system SHALL enforce configurable limits on compressed archive size, total uncompressed size, compression ratio, and manifest size. No global numeric limit is FROZEN; every limit SHALL be configurable and its value SHALL be an explicitly documented Implementation Choice.

#### Scenario: Configured size limits are enforced

- **WHEN** the compressed archive size, total uncompressed size, or manifest size exceeds its configured limit
- **THEN** the envelope is rejected

#### Scenario: Compression-ratio limit is enforced

- **WHEN** the uncompressed-to-compressed ratio exceeds the configured limit
- **THEN** the envelope is rejected as a suspected decompression bomb

### Requirement: Manifest is validated as strict UTF-8 ITP/1.0 JSON

The system SHALL read `manifest.json` under the configured size bound, decode it as strict UTF-8, parse it as JSON, and validate it against the ITP/1.0 schema: required fields `protocol_version` (`"1.0"`), `handoff_id` (opaque non-empty, retry-stable), `evidence_reference` (exactly `"evidence.pdf"`), `source_origin` (non-empty locator, not required to be a URI), `retrieved_at` (ISO-8601 with timezone), `collector` (Actor), `media_type` (exactly `"application/pdf"`), `byte_size` (positive integer); optional fields `last_modified` (ISO-8601 date or date-time), `candidate_sha256` (64 lowercase hex), `legal_hints` (mapping without canonical authority). Unsupported protocol versions, malformed UTF-8, malformed JSON, missing required fields, and invalid field values SHALL be rejected.

#### Scenario: Valid full manifest is accepted

- **WHEN** a manifest carries all required fields and well-formed optional fields
- **THEN** it parses into the validated ITP/1.0 manifest representation

#### Scenario: Malformed manifest is rejected

- **WHEN** the manifest is not valid UTF-8, is not valid JSON, is missing a required field, has an unsupported `protocol_version`, or has an invalid field value
- **THEN** the envelope is rejected

#### Scenario: Candidate SHA-256 mismatch is rejected

- **WHEN** `candidate_sha256` is present and differs from the official SHA-256 computed by the receiver
- **THEN** the envelope is rejected as a physical handoff inconsistency

### Requirement: Collector is validated with the shared Actor grammar

The system SHALL validate the manifest `collector` field through the Stage 1 shared Actor grammar (`human:<id>`, `process:<id>`, `<producer>/<version>`) and SHALL NOT introduce a second Actor grammar. Malformed Actor references SHALL cause manifest rejection.

#### Scenario: All canonical Actor forms are accepted

- **WHEN** `collector` is a valid `human:<id>`, `process:<id>`, or `<producer>/<version>` reference
- **THEN** the manifest is accepted with the canonical Actor representation

#### Scenario: Malformed Actor is rejected

- **WHEN** `collector` does not match the shared Actor grammar
- **THEN** the manifest is rejected

### Requirement: Official receiver SHA-256 over exact accepted bytes

The system SHALL compute the official SHA-256 over the exact accepted bytes of `evidence.pdf` (streamed or bounded, per the FROZEN streaming rule), SHALL verify the manifest `byte_size` against the actual evidence size, and SHALL treat SHA-256 strictly as byte integrity — never as legal identity, legal authenticity, or concept identity. A known hash SHALL NOT cause automatic rejection, canonical No-Op, or concept fusion at preflight.

#### Scenario: Official SHA matches the accepted bytes

- **WHEN** preflight hashes the accepted evidence bytes
- **THEN** the reported official SHA-256 equals the SHA-256 of exactly those bytes

#### Scenario: Byte-size inconsistency is rejected

- **WHEN** the manifest `byte_size` does not match the actual evidence size
- **THEN** the envelope is rejected

#### Scenario: Known hash neither rejects nor fuses

- **WHEN** the computed official SHA-256 is already known from a prior handoff
- **THEN** preflight neither rejects the envelope for that reason alone nor declares a canonical No-Op or concept fusion

### Requirement: Structural PDF validation without executing content

The system SHALL validate `evidence.pdf` by structure/content through a safe open/parse route that does not execute scripts, macros, attachments, or embedded active content. `%PDF-` magic bytes alone SHALL NOT be sufficient. The validation SHALL reuse the existing structural PDF open route (`inspector.open_pdf`) and its rejection semantics for encrypted, empty, and invalid PDFs.

#### Scenario: Structurally valid PDF is accepted

- **WHEN** the evidence is a PDF that opens through the safe structural route with pages
- **THEN** the evidence passes the structural validation step

#### Scenario: Invalid, encrypted, or empty PDF is rejected

- **WHEN** the evidence cannot be opened as a PDF, is encrypted, or has no pages
- **THEN** the envelope is rejected with the corresponding structural-PDF error

### Requirement: Accepted evidence is preserved before Phase 1

The system SHALL preserve accepted evidence bytes exactly (no rewriting, no semantic correction, no summarization, no enrichment) to Object Storage through an `ObjectStorageGateway` seam that produces a stable, resolvable reference, and SHALL do so after physical validations and before any Phase 1 conversion. The storage provider, bucket, URI scheme, object key, and physical filename are Implementation Choices and SHALL NOT be presented as FROZEN. Preservation SHALL use noncanonical, non-bundle storage (outside `/bundle/` and outside Git).

#### Scenario: Accepted evidence is preserved with a stable reference

- **WHEN** an envelope has passed preflight
- **THEN** the exact accepted bytes are stored through the gateway and a stable, resolvable reference is returned

#### Scenario: Preserved bytes and hash are identical to the accepted bytes

- **WHEN** preserved evidence is read back
- **THEN** its bytes and SHA-256 equal the accepted evidence bytes and official SHA-256

#### Scenario: No bundle write occurs during preservation

- **WHEN** the Stage 2 flow runs end to end
- **THEN** no write occurs anywhere under `repo_jur/bundle/`

### Requirement: Ingress completion protocol and retry idempotency

The system SHALL observe only finalized envelope names (`<handoff_id>.zip`) in the configurable filesystem inbox and SHALL ignore temporary names (`<handoff_id>.partial`). The system SHALL keep ingress operational state outside `/bundle/` keyed by `handoff_id`; a retry with the same `handoff_id`, a semantically equivalent manifest, and the same official evidence SHA-256 SHALL reuse the prior result without duplicate execution; the same `handoff_id` with semantically different manifest or evidence SHALL be rejected as a handoff conflict. The ZIP hash SHALL NOT be used as a normative idempotency key. `handoff_id` SHALL NOT be converted into canonical legal metadata.

#### Scenario: Partial files are never eligible

- **WHEN** an inbox contains `<handoff_id>.partial` files
- **THEN** only finalized `.zip` names are considered eligible envelopes

#### Scenario: Equivalent retry reuses the prior result

- **WHEN** the same `handoff_id`, semantically equivalent manifest, and same official evidence SHA-256 are presented again
- **THEN** the prior ingress result is reused without re-execution

#### Scenario: Conflicting retry is rejected

- **WHEN** the same `handoff_id` is presented with semantically different manifest or evidence
- **THEN** the envelope is rejected as a handoff conflict
