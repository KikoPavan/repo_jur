# legal-knowledge Specification

## Purpose
TBD - created by archiving change stage7-legal-knowledge. Update Purpose after archive.
## Requirements
### Requirement: Legal Knowledge consumes only conformant Phase 1 artifacts routed to legal_knowledge

The system SHALL begin the Stage 7 Legal Knowledge pipeline from Phase 1 artifacts produced by the Shared Conversion Core and the Phase 1 Quality Gate (literal Markdown and a technical conversion report that records the Quality Gate outcome) whose recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS` (the serialized values) and whose routing decision is exactly `legal_knowledge`. The Stage 7 boundary SHALL NOT treat an unconverted evidence reference, an arbitrary caller-supplied document, a raw PDF, or an artifact whose routing decision is `judicial_process` or `review_required` as its input contract, SHALL NOT request or perform any further conversion, SHALL NOT resolve evidence, and SHALL NOT invoke OCR.

#### Scenario: Conformant routed artifacts are accepted

- **WHEN** Stage 7 receives Phase 1 artifacts (literal Markdown and technical conversion report) whose recorded gate outcome is `PASS` or `PASS_WITH_WARNINGS` and whose routing decision is `legal_knowledge`
- **THEN** the Legal Semantic Review and Legal Producer evaluate that already-converted, already-routed content without requesting or performing further conversion, resolving evidence, or invoking OCR

#### Scenario: Unconverted or un-routed input cannot enter Stage 7

- **WHEN** an unconverted evidence reference, raw PDF, arbitrary caller-supplied document, or an artifact whose routing decision is `judicial_process` or `review_required` is presented to the Stage 7 boundary
- **THEN** Stage 7 does not proceed as a successful execution
- **AND** no Stage 7 review result, concept candidate, or publication is produced

### Requirement: The recorded Quality Gate outcome gates every Stage 7 capability

The system SHALL re-read the Quality Gate outcome from the technical report's recorded `result.quality_gate` as part of every Stage 7 capability (Semantic Review and Producer) and SHALL NOT accept a caller-supplied override. When the recorded outcome is `FAIL`, or the report is unparseable or does not record a valid Quality Gate outcome, the system SHALL stop: no Stage 7 review, no concept candidate, and no publication occurs.

#### Scenario: PASS outcome proceeds

- **WHEN** the technical report records the Quality Gate outcome `PASS`
- **THEN** the Stage 7 capability proceeds on the conformant artifacts

#### Scenario: PASS WITH WARNINGS outcome proceeds

- **WHEN** the technical report records the Quality Gate outcome `PASS_WITH_WARNINGS`
- **THEN** the Stage 7 capability proceeds on the conformant artifacts

#### Scenario: FAIL outcome stops Stage 7

- **WHEN** the technical report records the Quality Gate outcome `FAIL`
- **THEN** Stage 7 stops
- **AND** no review result, concept candidate, or publication is produced

#### Scenario: Absent or invalid gate outcome blocks Stage 7

- **WHEN** the technical report does not record a Quality Gate outcome, records an invalid value, or cannot be parsed
- **THEN** Stage 7 does not proceed
- **AND** no review result, concept candidate, or publication is produced

### Requirement: Stage 7 never mutates Phase 1 artifacts

The system SHALL NOT modify, rewrite, autocorrect, complete, paraphrase, translate, or otherwise alter the literal Markdown body or the technical conversion report of the Phase 1 artifacts as part of any Stage 7 capability. The literal Markdown content SHALL be identical, byte for byte, before and after the Legal Semantic Review executes and before and after the Legal Producer executes, and the serialized technical report SHALL be identical, byte for byte, before and after both capabilities.

#### Scenario: Markdown is unchanged after Stage 7 executes

- **WHEN** the Legal Semantic Review and the Legal Producer execute against Phase 1 artifacts, regardless of the resulting review state or publication outcome
- **THEN** the SHA-256 hash of the literal Markdown after execution equals the SHA-256 hash of the literal Markdown before execution

#### Scenario: Technical report is unchanged after Stage 7 executes

- **WHEN** the Legal Semantic Review and the Legal Producer execute against Phase 1 artifacts
- **THEN** the serialized technical report after execution equals the serialized technical report before execution

### Requirement: Legal Semantic Review is bounded-context-specific and engine-neutral

The system SHALL expose the Legal Semantic Review as a seam with an engine interface, consuming the Phase 1 artifacts read-only plus a review profile, and returning a review result. The review SHALL be specific to the Legal Knowledge bounded context: it SHALL NOT import, construct, or reference Judicial-Process schemas, classifiers, or enrichment models, and SHALL NOT depend on any specific conversion engine, OCR provider, OCR model, LLM model, LLM provider, or LLM prompt.

#### Scenario: Review executes through the engine seam

- **WHEN** the Legal Semantic Review executes with Phase 1 artifacts and a review profile
- **THEN** the review result is produced through the engine seam
- **AND** no Judicial-Process schema, classifier, or enrichment model is referenced

#### Scenario: Review implementation is source-inspected for prohibited coupling

- **WHEN** the Legal Semantic Review implementation source is inspected
- **THEN** it references no Judicial-Process schema, no LLM or semantic-model client, no OCR provider, and no conversion engine

### Requirement: Legal Semantic Review result carries structured review output only

The system SHALL return a review result containing structured patches, extracted fields, non-authoritative classification suggestions, an immutable ordered tuple of warnings, and a review state. The review state SHALL be exactly one of `OK`, `WARNING`, or `REVIEW_REQUIRED`. Warnings and review state SHALL exist only in the review result and SHALL NOT be introduced into the literal Markdown body or the technical report.

#### Scenario: Review result exposes structured output

- **WHEN** the Legal Semantic Review completes
- **THEN** the result exposes the patches, extracted fields, suggestions, warnings, and review state
- **AND** none of that review output appears inside the literal Markdown body or the technical report

#### Scenario: REVIEW_REQUIRED state is returned without applying changes

- **WHEN** the review determines it cannot make a structural correction without inference
- **THEN** the review state is `REVIEW_REQUIRED`
- **AND** no ambiguous correction is applied silently

### Requirement: Structural review operations preserve every original word

When the Legal Semantic Review performs a structural operation (separating, associating, or reordering structural fields), the system SHALL preserve every original word of the Phase 1 content: no word SHALL be added, removed, summarized, paraphrased, translated, or invented by inference, and no missing text SHALL be completed. The system SHALL validate this preservation automatically for every structural patch.

#### Scenario: A structural correction preserves all original words

- **WHEN** the review applies a structural correction that changes only boundaries or field association
- **THEN** every original word of the affected content is preserved in the patch output
- **AND** no word is added, removed, summarized, paraphrased, translated, or invented

#### Scenario: A non-structural rewrite is not performed

- **WHEN** the review considers an operation that would rewrite, summarize, paraphrase, translate, or invent legal content
- **THEN** the operation is not performed
- **AND** the review state becomes `REVIEW_REQUIRED` when the ambiguity cannot be resolved structurally

### Requirement: Structured patches carry full provenance

The system SHALL represent every review-applicable change as a structured patch record containing the before value, the after value, the reason, a confidence or equivalent review signal, page references when a physical page association is supported, and evidence references when available. The system SHALL prefer structured patches over full-document rewriting.

#### Scenario: A patch records before, after, reason, and confidence

- **WHEN** the review produces a structural patch
- **THEN** the patch carries the before value, the after value, the reason, and a confidence signal
- **AND** the patch carries page and evidence references when supported

### Requirement: Ambiguity routes to REVIEW_REQUIRED and never to silent correction

If a structural correction cannot be made without inference, the system SHALL mark the review result `REVIEW_REQUIRED` and SHALL NOT apply the correction, SHALL NOT invent text, and SHALL NOT complete missing text. A `REVIEW_REQUIRED` review result SHALL block Producer publication.

#### Scenario: Ambiguous correction is not applied

- **WHEN** the review determines that a structural correction requires inference
- **THEN** the review state is `REVIEW_REQUIRED`
- **AND** the correction is not applied
- **AND** no text is invented or completed

#### Scenario: REVIEW_REQUIRED blocks publication

- **WHEN** a Producer run consumes a review result whose state is `REVIEW_REQUIRED`
- **THEN** no concept is published
- **AND** the Producer observability record reports the human-review requirement

### Requirement: Legal Semantic Review never publishes

The system SHALL NOT write to canonical bundle storage, SHALL NOT create, modify, or delete any file under `repo_jur/bundle/`, and SHALL NOT invoke `guard_legal_bundle_write` as part of the Legal Semantic Review. Only the Legal Producer may invoke the bundle write guard.

#### Scenario: Review performs no canonical write

- **WHEN** the Legal Semantic Review executes, regardless of the resulting review state
- **THEN** no artifact is written to canonical bundle storage by the review
- **AND** the bundle write guard is not invoked by the review

### Requirement: Deterministic review rules are registry-backed and provenance-versioned

Deterministic structural review rules SHALL be registered in a versioned rule registry; each rule SHALL carry a rule identifier, a rule version, the applicable identifier or structural scope, a versioned specification source, and a validation-logic version. The registry SHALL be received at engine construction, validated for required provenance, stored immutably, and default to an empty registry when no rules are supplied. A configuration error in the registry or profile SHALL be surfaced through a dedicated configuration-error contract and SHALL NOT be converted into a successful review state.

#### Scenario: Rules require full provenance

- **WHEN** a deterministic review rule is registered
- **THEN** the rule carries its identifier, version, scope, specification source, and validation-logic version
- **AND** a rule missing required provenance is rejected at registration

#### Scenario: Empty registry is valid

- **WHEN** the review engine is constructed without rules
- **THEN** the internal registry is empty
- **AND** review executes as a zero-rule run without structural modifications

### Requirement: No silent semantic or LLM classification

The system SHALL NOT invoke an LLM or any external semantic model as part of any Stage 7 capability, SHALL NOT classify or type document content from the literal Markdown or the technical report, and SHALL NOT derive any classification signal from document content. Any classification suggestion is non-authoritative and SHALL NOT decide the concept type or any routing decision. When the Stage 7 implementation source is inspected, it SHALL contain no reference to an LLM or semantic-model client.

#### Scenario: No content-derived classification

- **WHEN** Stage 7 executes against Phase 1 artifacts whose Markdown body or report content is inspected
- **THEN** no LLM or semantic model is invoked
- **AND** no classification or type is derived from document content
- **AND** no routing decision is derived or altered by Stage 7

#### Scenario: Implementation is source-inspected for LLM coupling

- **WHEN** the Stage 7 implementation source is inspected
- **THEN** it contains no reference to an LLM client, a semantic-model client, or an external classification service

### Requirement: The concept type is explicit operator intent carried in a validated producer context

The system SHALL determine the OKF concept `type` exclusively from the validated producer context, where the operator supplies exactly one of the Legal OKF Profile types — `Legislacao`, `Jurisprudencia`, `TemaJuridico`, `PrecedenteVinculante` (the serialized values) — as explicit workflow/operator intent. The system SHALL NOT derive `type` from the literal Markdown, the technical report, collector candidate hints, or any content signal. A producer context that is absent, invalid, or carries a `type` value outside the four allowed values SHALL be surfaced through a dedicated configuration-error contract and SHALL NOT produce a concept candidate or publication. A non-authoritative classification suggestion that conflicts with the explicit `type` SHALL route the Producer run to `REVIEW_REQUIRED`.

#### Scenario: Explicit type selects the concept type

- **WHEN** the validated producer context carries `type` with value `Legislacao`, `Jurisprudencia`, `TemaJuridico`, or `PrecedenteVinculante`
- **THEN** the concept candidate is rendered with exactly that type
- **AND** no content-derived type is computed

#### Scenario: Invalid or absent type is a configuration error

- **WHEN** the producer context is absent, invalid, or carries a `type` outside the four allowed values
- **THEN** the dedicated configuration error is raised
- **AND** no concept candidate or publication is produced

#### Scenario: Conflicting suggestion routes to REVIEW_REQUIRED

- **WHEN** the review emits a classification suggestion whose value conflicts with the explicit `type` in the producer context
- **THEN** the Producer run does not publish
- **AND** the run records `REVIEW_REQUIRED`

### Requirement: PDF provenance fields obey the closed cardinality rules

For concepts derived from PDF evidence, the system SHALL render exactly one of the mutually exclusive provenance fields: `repo_jur_pdf_hash` (a lowercase 64-hex SHA-256) when the concept derives from exactly one PDF, or `repo_jur_pdf_hashes` (a mapping of `sources[].id` → lowercase 64-hex SHA-256) when the concept derives from two or more PDFs. `repo_jur_pdf_hash` and `repo_jur_pdf_hashes` SHALL NEVER coexist. For a multi-PDF concept, every PDF source in `sources` SHALL carry an `id` and SHALL have exactly one corresponding entry in `repo_jur_pdf_hashes`; non-PDF sources SHALL remain in `sources` but SHALL NOT appear in `repo_jur_pdf_hashes`. The SHA-256 identifies the bytes of the PDF evidence; it is not concept identity and not proof of legal authenticity.

#### Scenario: Single-PDF concept uses the singular field

- **WHEN** a concept derives from exactly one PDF evidence
- **THEN** the candidate carries `repo_jur_pdf_hash` with the evidence SHA-256
- **AND** `repo_jur_pdf_hashes` is absent

#### Scenario: Multi-PDF concept uses the plural mapping

- **WHEN** a concept derives from two or more PDF evidences
- **THEN** the candidate carries `repo_jur_pdf_hashes` mapping each PDF `sources[].id` to its SHA-256
- **AND** `repo_jur_pdf_hash` is absent
- **AND** every PDF source has an `id` present in the mapping

#### Scenario: Both fields together are invalid

- **WHEN** a rendered candidate would contain both `repo_jur_pdf_hash` and `repo_jur_pdf_hashes`
- **THEN** the candidate fails validation
- **AND** no publication occurs

### Requirement: The preserved evidence reference is never invented

For concepts derived from PDF evidence, the system SHALL carry the preserved-evidence reference through the validated producer context and SHALL NOT invent, guess, or fabricate a resource reference. When the concept is PDF-derived and the producer context supplies no evidence reference, the system SHALL raise the dedicated configuration error and SHALL NOT publish. When the evidence reference is resolvable, the system SHALL cross-check the report's recorded input SHA-256 against the referenced evidence where feasible.

#### Scenario: PDF-derived concept without evidence reference fails

- **WHEN** the concept is PDF-derived and the producer context supplies no evidence reference
- **THEN** the dedicated configuration error is raised
- **AND** no concept candidate or publication is produced

#### Scenario: Evidence reference is recorded in sources

- **WHEN** the concept is PDF-derived and the producer context supplies the preserved-evidence reference
- **THEN** `sources[].resource` records that reference
- **AND** the recorded input SHA-256 is preserved in the provenance fields

### Requirement: Producer renders a conformant Legal OKF concept candidate

The system SHALL render the concept candidate with a valid YAML frontmatter block delimited by `---` and beginning with the key `type`, followed by the Markdown body. The frontmatter SHALL satisfy the Legal OKF Profile: `generated` with `by` set to `repo_jur_producer/<version>`; `sources` present when the concept derives from identifiable sources; domain-specific fields applied only for the applicable type (legislation, jurisprudence, theme, or binding-precedent fields); and `verified` present only when a real verification event exists. The body of a PDF-derived concept SHALL preserve the Phase 1 literal content including the canonical page markers `[[Pág. N]]` where applicable.

#### Scenario: Candidate carries valid frontmatter and preserved body

- **WHEN** the Producer renders a concept candidate from conformant Phase 1 artifacts
- **THEN** the candidate has a valid YAML frontmatter block with `type` first
- **AND** `generated.by` is `repo_jur_producer/<version>`
- **AND** the body preserves the Phase 1 literal content with page markers where applicable

#### Scenario: Verified is never fabricated

- **WHEN** the Producer renders a concept candidate and no real verification event exists
- **THEN** `verified` is absent from the candidate frontmatter

### Requirement: Producer never mutates lifecycle fields it does not own

The system SHALL NOT insert or change the OKF `status` field, SHALL NOT create a `_v2` suffix, UUID, or stable identifier, and SHALL NOT fabricate `verified` events. `status` absence SHALL be preserved (OKF semantics interpret absence as `stable`); any explicit `status` value SHALL be preserved as Human-Owned. `generated.at` SHALL be updated only when the current run changes the concept meaningfully, and SHALL NOT be updated merely because the Producer executed again.

#### Scenario: Status is neither inserted nor mutated

- **WHEN** the Producer renders or regenerates a concept
- **THEN** an absent `status` remains absent
- **AND** an existing `status` value is preserved unchanged

#### Scenario: No automatic versioning artifact

- **WHEN** the Producer resolves an existing concept or a duplicate
- **THEN** no `_v2` suffix, UUID, or stable identifier is created

#### Scenario: generated.at changes only on meaningful change

- **WHEN** a Producer run does not change the concept's meaningful content, ownership, or provenance
- **THEN** `generated.at` is not updated
- **AND** a re-run with equivalent inputs produces no timestamp-only diff

### Requirement: Producer preserves human-owned and shared-ownership values

When regenerating or updating an existing concept, the system SHALL load the existing concept first, recompute Producer-Owned fields, and preserve Human-Owned fields and human-curated values of Shared Ownership fields. The system SHALL NOT silently overwrite or delete valid human-owned values, valid human curation, active `verified` events that remain applicable, `repo_jur_verification_history` entries, or unknown extension keys.

#### Scenario: Human-owned values survive regeneration

- **WHEN** the Producer regenerates an existing concept whose frontmatter contains human-owned or human-curated values
- **THEN** those values are preserved in the regenerated candidate
- **AND** the Producer-Owned fields are recomputed deterministically

#### Scenario: Verification history is preserved

- **WHEN** the Producer regenerates an existing concept carrying `repo_jur_verification_history`
- **THEN** the history entries are preserved with their original `by` and `at` values

### Requirement: Duplicate resolution is conservative and write-blocked on ambiguity

The system SHALL resolve the candidate concept against existing bundle content following the closed Duplicate Act Handling decision: SHA-256 is physical evidence identity only; the same hash is never a no-op by itself and never a rejection; physically distinct PDFs are consolidated into one concept only when logical and material equivalence are safe; a material change or unresolved ambiguity SHALL stop the automatic write and require human review. The system SHALL NOT alter `status`, SHALL NOT create `_v2`, and SHALL NOT silently choose between conflicting values.

#### Scenario: Same evidence with equivalent inputs is a no-op

- **WHEN** an existing concept represents the same legal act with the same physical evidence and equivalent canonical inputs, configuration, and logical processing version, and no meaningful change exists
- **THEN** the Producer performs no write
- **AND** the observability record reports the no-op resolution

#### Scenario: Material change or ambiguity blocks the write

- **WHEN** resolution detects a material change or cannot establish safe equivalence
- **THEN** the Producer does not write
- **AND** the observability record reports human review required

#### Scenario: Distinct autonomous act creates a distinct concept

- **WHEN** the candidate represents a legally distinct or autonomous act
- **THEN** the Producer renders a distinct concept candidate under its own positional path

### Requirement: Canonical publication is atomic and exclusively through the write guard

The system SHALL publish a concept document only after full validation (YAML parse, OKF conformance, Legal OKF Profile fields, cardinality exclusivity, `sources` mapping, ownership rules) and SHALL perform the write atomically (temporary file on the same filesystem, flush/fsync, atomic rename). The write SHALL be authorized exclusively through `guard_legal_bundle_write` with acting domain `legal_knowledge`, targeting `repo_jur/bundle/`. The system SHALL NOT provide any alternate publication path, SHALL NOT write derived or runtime data into `bundle/`, and SHALL NOT perform an automatic Git commit, push, or merge as part of publication.

#### Scenario: Validated candidate publishes atomically through the guard

- **WHEN** a validated concept candidate is published
- **THEN** the write is authorized by `guard_legal_bundle_write` with acting domain `legal_knowledge`
- **AND** the write is performed atomically into the positional bundle path
- **AND** no Git commit, push, or merge is performed

#### Scenario: Non-legal domain cannot publish to the bundle

- **WHEN** a write targeting `repo_jur/bundle/` is attempted with any acting domain other than `legal_knowledge`
- **THEN** the write guard denies the authorization
- **AND** no file is written to the bundle

#### Scenario: Invalid candidate is never published

- **WHEN** a concept candidate fails OKF, profile, cardinality, sources-mapping, or ownership validation
- **THEN** the candidate is not published
- **AND** no partial file remains

### Requirement: Producer observability is content-safe and located outside the bundle

The system SHALL record Producer execution in operational/technical artifacts only: one JSON record per build and per publish, stored outside the canonical bundle and outside the Phase 1 artifacts, under a configurable operational directory. The record SHALL include the resolution outcome, the human-review requirement when applicable, the materiality decision category when applicable, and the publication result. The record SHALL NOT contain document content, full critical identifier values, patch bodies, review patch content, secrets, tokens, or credentials; it SHALL reference the processed evidence by its provenance hash.

#### Scenario: Producer record is written outside the bundle

- **WHEN** a Producer build or publish completes
- **THEN** a JSON record is written under the configurable operational state directory
- **AND** the state directory is rejected when it resolves inside the canonical bundle

#### Scenario: Producer record is content-safe

- **WHEN** the Producer record is inspected
- **THEN** it contains the resolution outcome, materiality category, human-review requirement, and publication result
- **AND** it contains no document content, no full critical identifier value, no patch body, and no secret or token

### Requirement: Stage 7 is deterministic and idempotent

The system SHALL compute the review result and the rendered concept candidate as pure deterministic functions of the Phase 1 artifacts, the review profile, and the validated producer context: identical inputs SHALL yield identical review results and identical candidate bytes on every evaluation, and the decision SHALL NOT depend on execution order, per-run identifiers, timestamps, or durations. Publication SHALL NOT create spurious diffs when inputs are equivalent.

#### Scenario: Repeated evaluation of identical inputs is identical

- **WHEN** the same Phase 1 artifacts, review profile, and producer context are evaluated twice
- **THEN** the second review result and rendered candidate equal the first

#### Scenario: Equivalent re-run does not mutate the bundle

- **WHEN** the Producer runs twice with equivalent inputs against the same existing concept
- **THEN** the second run produces no canonical diff beyond the first

### Requirement: Stage 7 does not implement later stages or Judicial Process behavior

The system SHALL NOT implement Stage 8 (Judicial Process Semantic Review, Producer, or storage), Stage 9 (Legal Knowledge Retrieval), or any later stage as part of this capability. The system SHALL NOT write to judicial-process storage, SHALL NOT create a shared Legal/Process index, SHALL NOT reuse Legal schemas for process documents, and SHALL NOT couple the Stage 7 implementation to any Judicial-Process schema. The page-level routing semantics of the conversion pipeline and the Domain Router semantics SHALL remain unchanged.

#### Scenario: No Judicial Process behavior is introduced

- **WHEN** the Stage 7 implementation source is inspected
- **THEN** it contains no Judicial-Process schema, no process-storage write path, and no shared index creation
- **AND** `router.py` page-routing semantics and Domain Router semantics are unchanged

### Requirement: Operational producer CLI is additive and non-regressive

The system SHALL provide an operational producer CLI whose `build` and `validate` commands never write to the canonical bundle, whose `publish` command is the single write path authorized through the write guard, and whose behavior follows the existing CLI conventions (deterministic exit codes, environment-driven directories, sanitized logging, atomic writes). The pre-existing conversion command surface and the pre-existing routing command surface SHALL remain unchanged.

#### Scenario: Build and validate never write to the bundle

- **WHEN** the producer CLI `build` or `validate` command is invoked
- **THEN** no file is written under `repo_jur/bundle/`
- **AND** the command reports the review/validation outcome with a deterministic exit code

#### Scenario: Publish is the single write path

- **WHEN** the producer CLI `publish` command is invoked with a validated candidate
- **THEN** the candidate is published atomically through the write guard
- **AND** the publication result is recorded in the observability record

#### Scenario: Existing CLI surfaces are preserved

- **WHEN** the producer CLI commands are introduced
- **THEN** the pre-existing conversion command surface and the pre-existing routing command surface remain unchanged

