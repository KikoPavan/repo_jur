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

The system SHALL expose the Legal Semantic Review as a seam with an engine interface, consuming the Phase 1 artifacts read-only plus a review profile, and returning a review result. The review SHALL be specific to the Legal Knowledge bounded context: it SHALL NOT import, construct, or reference Judicial-Process schemas, classifiers, or enrichment models, and SHALL NOT depend on any specific conversion engine, OCR provider, OCR model, LLM model, LLM provider, or LLM prompt. The Legal Semantic Review SHALL NOT receive or depend on the operator's explicit `ProducerContext`/concept `type`, and SHALL NOT enforce any type-specific mandatory-field completeness rule (such as Legislacao numbered-act completeness) purely from generic content signals found anywhere in the document; such type-specific enforcement belongs exclusively to the Legal Producer, which alone knows the explicit `type`.

#### Scenario: Review executes through the engine seam

- **WHEN** the Legal Semantic Review executes with Phase 1 artifacts and a review profile
- **THEN** the review result is produced through the engine seam
- **AND** no Judicial-Process schema, classifier, or enrichment model is referenced

#### Scenario: Review implementation is source-inspected for prohibited coupling

- **WHEN** the Legal Semantic Review implementation source is inspected
- **THEN** it references no Judicial-Process schema, no LLM or semantic-model client, no OCR provider, and no conversion engine

#### Scenario: Review does not force REVIEW_REQUIRED from a generic legislative citation

- **WHEN** the Legal Semantic Review executes against Phase 1 artifacts whose body cites one or more numbered legislative acts, regardless of the eventual concept `type`
- **THEN** the review state is not forced to `REVIEW_REQUIRED` merely because a numbered-act citation pattern is present and `repo_jur_lei_numero`/`repo_jur_lei_ano` were not extracted
- **AND** any Legislacao-specific completeness enforcement is left to the Legal Producer

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

The system SHALL render the concept candidate with a valid YAML frontmatter block delimited by `---` and beginning with the key `type`, followed by the Markdown body. The frontmatter SHALL satisfy the Legal OKF Profile v1.3: `generated` with `by` set to `repo_jur_producer/<version>` (the `generated.at` subfield, if present, MUST strictly be an ISO 8601 Datetime String, and `evidence:...` URI syntax is unauthorized); `sources` present when the concept derives from identifiable sources; domain-specific fields applied only for the applicable type (legislation, jurisprudence, theme, or binding-precedent fields); and `verified` present only when a real verification event exists. The body of a PDF-derived concept SHALL preserve the Phase 1 literal content including the canonical page markers `[[Pág. N]]` where applicable.

The system SHALL strictly enforce and validate the domain-specific fields for each concept type as follows:
1. **Legislacao**
   - `repo_jur_lei_numero` (String, Conditional Mandatory): The official number of the law (mandatory only for numbered acts, like Lei 10.406/2002).
   - `repo_jur_lei_ano` (Integer, Conditional Mandatory): The official year of the law (mandatory only for numbered acts, like Lei 10.406/2002).
   - `repo_jur_lei_esfera` (String, Mandatory): The governmental sphere (`federal`, `estadual`, `distrital`, `municipal`).
   - `repo_jur_lei_tipo` (String, Recommended): The type of normative act (e.g., `constituicao`, `complementar`, `ordinaria`, `decreto`, `portaria`, `medida_provisoria`).
2. **Jurisprudencia**
   - `repo_jur_processo_numero` (String, Mandatory): The process identifier (CNJ format is preferentially preferred, but STJ/STF appellate case identifiers like REsp/AREsp/AgInt or register numbers are also valid fallbacks when CNJ is not available; no separate field for court-class identifiers exists in the FROZEN profile).
   - `repo_jur_tribunal` (String, Mandatory): The court acronym in uppercase.
   - `repo_jur_relator` (String, Mandatory): The magistrate relator name.
   - `repo_jur_data_julgamento` (String YYYY-MM-DD, Mandatory): The date of judgment.
   - `repo_jur_ramo_direito` (String, Recommended): The branch of law.
3. **TemaJuridico**
   - `repo_jur_tema_numero` (String, Conditional Mandatory): Mandatory if representing an official numbered theme. This field SHALL be extracted only when the source document presents exactly one distinct, unambiguous Tema-number citation across its entire content; when two or more distinct Tema numbers are cited (e.g. a thematic compilation citing multiple theses, each referencing its own Tema), the system SHALL NOT extract `repo_jur_tema_numero` and SHALL treat the field as safely absent rather than silently selecting any one citation.
   - `repo_jur_tribunal` (String, Conditional Mandatory): Mandatory if representing an official court theme.
4. **PrecedenteVinculante**
   - `repo_jur_precedente_numero` (String, Mandatory): The precedent/sumula number.
   - `repo_jur_precedente_status` (String, Mandatory): The precedent status (`ativo`, `cancelado`, `revisado`).
   - `repo_jur_tribunal` (String, Mandatory): The court acronym.

The system SHALL reject any legacy, un-prefixed, or inappropriate fields including `jurisdicao`, `ambito`, `tipo_norma`, `ementa`, `tema`, `subtema`, `tese_fixada`, `tribunal` (without prefix), and `relator` (without prefix). Under the FROZEN profile, both `title` and `description` are recommended but not mandatory. `title` is permitted/recommended but not guaranteed to have deterministic initial population, and `description` is optional with no initial automation required. Neither field is required to appear in the real-corpus acceptance assertion.

Every automatically extracted metadata field MUST carry physical page references mapped via page_refs matching the [[Pág. N]] markers from which the text was deterministic-extracted. These page references are transient and persisted only in operational logs/JSON reports, never written to the canonical YAML frontmatter. Any cognitive/LLM classification or metadata inference is strictly prohibited. If a mandatory field cannot be deterministic-extracted, the Producer run MUST be aborted with exit code 5 (blocked) and NO publication SHALL occur.

The Legislacao-specific numbered-act completeness check (detecting a numbered-act citation pattern in the candidate body and requiring `repo_jur_lei_numero`/`repo_jur_lei_ano` to have been extracted) SHALL be enforced exclusively by the Legal Producer's candidate validation, gated strictly on the candidate's explicit `type` being `Legislacao`. This check SHALL NOT be enforced by the Legal Semantic Review, and SHALL NOT be applied to `Jurisprudencia`, `TemaJuridico`, or `PrecedenteVinculante` candidates merely because their body cites legislation.

#### Scenario: Candidate carries valid frontmatter and preserved body

- **WHEN** the Producer renders a concept candidate from conformant Phase 1 artifacts
- **THEN** the candidate has a valid YAML frontmatter block with `type` first
- **AND** `generated.by` is `repo_jur_producer/<version>`
- **AND** the body preserves the Phase 1 literal content with page markers where applicable

#### Scenario: Verified is never fabricated

- **WHEN** the Producer renders a concept candidate and no real verification event exists
- **THEN** `verified` is absent from the candidate frontmatter

#### Scenario: Legacy fields are strictly rejected

- **WHEN** the Producer is presented with a candidate containing any legacy fields such as `jurisdicao`, `ambito`, `tipo_norma`, `ementa`, `tema`, `subtema`, `tese_fixada`, `tribunal` (without prefix), or `relator` (without prefix)
- **THEN** the candidate fails validation
- **AND** no publication occurs

#### Scenario: Mandatory metadata absence blocks publication

- **WHEN** a required metadata field (e.g., `repo_jur_lei_numero` for `Legislacao`) is absent and cannot be deterministic-extracted
- **THEN** the Producer aborts the publication run
- **AND** no file is written to the canonical bundle
- **AND** the run status reports a blocked human-review-required state

#### Scenario: Real-corpus complete metadata extraction from L10.406_CC_2002.pdf

- **WHEN** the pipeline processes the real-corpus document `L10.406_CC_2002.pdf` as `Legislacao`
- **THEN** the deterministic extractor successfully populates `repo_jur_lei_numero` with `"10406"`, `repo_jur_lei_ano` with `2002`, `repo_jur_lei_esfera` with `"federal"`, and `repo_jur_lei_tipo` with `"ordinaria"`
- **AND** the resulting concept frontmatter contains exactly these canonical fields, with any optional fields like `title` and `description` or `generated.at` being omitted or formatted strictly per profile rules, and contains no legacy fields

#### Scenario: TemaJuridico citing legislation does not falsely require review

- **WHEN** a `TemaJuridico` candidate body cites a numbered law (e.g. `Lei n. 11.636/2007`) purely as a reference within a thesis, and the candidate's other `TemaJuridico` mandatory-field rules are satisfied
- **THEN** the Producer does not block on the Legislacao-specific numbered-act completeness check
- **AND** the candidate builds successfully

#### Scenario: Jurisprudencia and PrecedenteVinculante citing legislation do not falsely require review

- **WHEN** a `Jurisprudencia` or `PrecedenteVinculante` candidate body cites one or more numbered laws as legal grounding
- **THEN** the Producer does not block on the Legislacao-specific numbered-act completeness check
- **AND** the candidate builds successfully provided its own type-specific mandatory fields are satisfied

#### Scenario: Legislacao with an incomplete numbered act still blocks

- **WHEN** the producer context explicitly selects `type: Legislacao` and the candidate body contains a numbered-act citation pattern (e.g. `LEI COMPLEMENTAR Nº 123`) but `repo_jur_lei_numero` or `repo_jur_lei_ano` could not be deterministic-extracted
- **THEN** the Producer blocks the run with the human-review-required outcome
- **AND** no concept candidate is published

#### Scenario: Ambiguous internal Tema citations do not produce a silent identity

- **WHEN** a `TemaJuridico` candidate body cites two or more distinct `Tema n. N` numbers as internal cross-references (e.g. `Tema n. 434`, `Tema n. 988`, `Tema n. 1089`) without unambiguous structural evidence that the document itself represents exactly one of those themes
- **THEN** `repo_jur_tema_numero` is not extracted and is absent from the candidate frontmatter
- **AND** the Producer does not silently select any one of the cited numbers as positional identity
- **AND** the run does not fail solely because of this omission when `repo_jur_tema_numero` is not otherwise required

#### Scenario: Unambiguous single-Tema document still extracts its Tema number

- **WHEN** a `TemaJuridico` candidate body contains exactly one distinct `Tema n. N` citation across its entire content
- **THEN** `repo_jur_tema_numero` is extracted deterministically with that single value
- **AND** the associated `repo_jur_tribunal` field is populated as today when available

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

### Requirement: Legal Source Segmentation is a deterministic, engine-neutral seam upstream of the Producer

The system SHALL expose a Legal Source Segmentation capability that consumes only the literal Phase 1 Markdown body and a versioned Segmentation Rule Registry, and returns a `SegmentationResult` whose outcome is exactly one of `single`, `segments`, or `ambiguous`. Segmentation SHALL NOT receive, read, or depend on the operator's `ProducerContext`/`type`, the technical conversion report, an LLM, an external semantic model, or any evidence resource, and SHALL NOT mutate the Phase 1 Markdown or technical report. Segmentation SHALL be a pure function: identical Markdown and identical registry version SHALL yield an identical `SegmentationResult` on every evaluation.

#### Scenario: Segmentation executes on Markdown alone

- **WHEN** Legal Source Segmentation executes with a Phase 1 Markdown body and a Segmentation Rule Registry
- **THEN** the result is produced without reading `ProducerContext`, `type`, the technical report, or any evidence resource
- **AND** no LLM or external semantic model is invoked

#### Scenario: Repeated evaluation of identical input is identical

- **WHEN** the same Markdown and the same registry version are segmented twice
- **THEN** the second `SegmentationResult` equals the first

#### Scenario: Segmentation never mutates Phase 1 artifacts

- **WHEN** Legal Source Segmentation executes, regardless of the resulting outcome
- **THEN** the SHA-256 hash of the literal Markdown after execution equals the SHA-256 hash before execution

### Requirement: Mono-concept sources produce exactly one segment with unchanged behavior

When no Segmentation Rule Registry entry produces two or more valid boundary matches in the Markdown, the system SHALL return outcome `single` with exactly one `Segment` whose body equals the entire input Markdown verbatim, including all of its `[[Pág. N]]` markers, and whose `boundary_rule_id` is absent. The Legal Producer SHALL render this segment identically to how it renders the whole-document candidate today, with no observable difference in `producer build` output, exit code, or JSON shape for a `single` outcome.

#### Scenario: Single-unit document yields exactly one segment

- **WHEN** Legal Source Segmentation executes against a Markdown body with no registered boundary rule producing two or more matches
- **THEN** the result outcome is `single`
- **AND** the one segment's body equals the entire input Markdown verbatim

#### Scenario: Existing mono-concept CLI behavior is unchanged

- **WHEN** `producer build` is invoked against a Phase 1 artifact whose segmentation outcome is `single`, without `--segment` or `--all-segments`
- **THEN** the command produces exactly one `candidate` in its output, matching byte-for-byte the candidate that would have been produced before this capability existed
- **AND** the exit code is unchanged for the same review/validation outcome

### Requirement: Structural boundaries are detected only from a versioned, provenance-carrying rule registry

Each Segmentation Rule SHALL carry a rule identifier, a rule version, a structural scope description, a specification source, and a validation-logic version, mirroring the provenance discipline of the existing Legal Semantic Review rule registry. A rule SHALL anchor on a structurally unambiguous, non-repeating unit marker (such as a once-per-unit dated heading or a fixed tabular record header) and SHALL NOT anchor on a bare in-body citation to a number, process, law, súmula, or thesis that also appears as an internal cross-reference elsewhere in the document. The system SHALL NOT derive a boundary from the first occurrence of any content pattern that also recurs as a citation.

A fixed tabular record header's field separators MAY each independently be one of a small, explicitly enumerated set of corpus-evidenced literal forms per field boundary (e.g. two ASCII spaces at a boundary, or a specific single Unicode Private Use Area code point flanked by single ASCII spaces at that same boundary) when real-corpus evidence shows Phase 1 emits that exact separator verbatim at that boundary. Different field boundaries within the same header MAY accept different corpus-evidenced forms (the accepted set is not required to be symmetric across all boundaries of one header). Recognizing an additional corpus-evidenced separator form SHALL NOT alter, normalize, or substitute the separator character anywhere in the Phase 1 Markdown or in any other rule; it SHALL only widen the accepted-literal-forms set of the specific structural anchor's own detection regex at the specific boundary where the evidence applies, and SHALL NOT loosen any boundary to an unrestricted whitespace or wildcard pattern.

#### Scenario: A corpus-evidenced non-ASCII field separator is recognized only within the full structural anchor

- **WHEN** a fixed tabular record header appears in the Markdown using a specific, real, corpus-evidenced Unicode field separator at one field boundary in place of two ASCII spaces, but otherwise satisfies the complete structural anchor shape (record number, all field separators in an accepted corpus-evidenced form, and both fixed field labels, on one physical line)
- **THEN** the boundary is recognized exactly as it would be with the originally specified ASCII-space separators
- **AND** the same separator character occurring outside the complete structural anchor shape (e.g. inside running prose, or accompanying an incomplete header missing a required field, a required separator at the wrong boundary, or a required label) produces no boundary
- **AND** no substitution, normalization, or removal of that separator character occurs anywhere in the Phase 1 Markdown

#### Scenario: Rules require full provenance

- **WHEN** a Segmentation Rule is registered
- **THEN** the rule carries its identifier, version, structural scope, specification source, and validation-logic version
- **AND** a rule missing required provenance is rejected at registration

#### Scenario: Internal citation does not create a boundary

- **WHEN** the Markdown body contains an internal cross-reference to another unit's number (e.g. a `Tema n. N` or `Edição n. N` mention inside running prose, not as the unit's own once-per-unit heading)
- **THEN** no boundary is produced for that occurrence
- **AND** the document's outcome is unaffected by the presence of that citation

#### Scenario: Repeated running header does not itself create additional boundaries

- **WHEN** a unit's own running header repeats verbatim on every physical page belonging to that same unit
- **THEN** the repeated running header produces no additional boundary beyond the one produced by that unit's own non-repeating structural anchor

### Requirement: Two or more unambiguous boundaries produce independent, page-scoped segments

When a Segmentation Rule produces two or more valid, monotonically page-ordered matches and no other registered rule also matches in the same document, the system SHALL return outcome `segments` with one ordered `Segment` per match. Each segment's body SHALL be the contiguous literal slice of the source Markdown from its boundary match to the next boundary match (or end of document for the last segment), preserving every `[[Pág. N]]` marker verbatim and including no content belonging to another segment. Each segment's `page_start`/`page_end` SHALL be derived positionally from a single document-wide map of `[[Pág. N]]` marker offsets (see the page-context requirement below), never solely from markers contained inside that segment's own body slice. Two or more segments MAY legitimately report the same `page_start`/`page_end` when their boundaries fall within the same physical page's span in the source document; this is not itself an ambiguity.

#### Scenario: Multi-unit document produces one segment per boundary

- **WHEN** Legal Source Segmentation executes against a Markdown body where a registered rule matches N ≥ 2 times in page order
- **THEN** the result outcome is `segments`
- **AND** exactly N segments are returned, ordered by document position

#### Scenario: Each segment contains only its own content and page markers

- **WHEN** a `segments` outcome is produced
- **THEN** every `[[Pág. N]]` marker in the source Markdown appears in exactly one segment's body
- **AND** no segment's body contains a `[[Pág. N]]` marker belonging to another segment's page range

#### Scenario: Segment page range is derived positionally, not from its own body's markers alone

- **WHEN** a segment is produced
- **THEN** its recorded `page_start` is the page number of the nearest document-wide marker at or before the segment's own boundary start offset, and `page_end` is the page number of the nearest document-wide marker at or before the segment's own end offset
- **AND** this resolution holds even when the segment's own body slice contains zero `[[Pág. N]]` markers

#### Scenario: Multiple segments sharing one physical page resolve to the same page_start

- **WHEN** two or more segments' boundaries fall between the same two consecutive document-wide page markers (or after the last marker), so that they structurally belong to the same physical source page
- **THEN** each of those segments independently resolves the same `page_start` (and, when applicable, the same `page_end`) from the document-wide marker map
- **AND** none of those segments' `segment_id`, `source_unit_label`, or resolved legal identity is altered by sharing that page

#### Scenario: A segment spanning two physical pages reports a distinct page_start and page_end

- **WHEN** a segment's boundary span crosses at least one document-wide page marker (its own body legitimately contains that marker)
- **THEN** `page_start` is the page active at the segment's own start offset and `page_end` is the page active at the segment's own end offset, and `page_end` may be strictly greater than `page_start`

### Requirement: Page context is a positional property of the whole source document, resolved from a single document-wide marker map

The system SHALL compute page context for every boundary match from one document-wide map of `[[Pág. N]]` marker offsets, built once per `segment_markdown()` evaluation over the entire input Markdown, never per-segment and never from a segment's own already-sliced body in isolation. A position's active page SHALL be the page number of the nearest marker at or before that position. Absence of a `[[Pág. N]]` marker strictly inside one segment's own body slice SHALL NOT, by itself, be treated as an ambiguity: it is the expected and valid shape for a segment whose boundary falls after the page's own marker but before that page's content ends. Page resolution SHALL NOT be derived from the previous segment's resolved page, from assumed sequential counting, from any number appearing in body prose, from the source filename, or from an LLM/OCR step.

#### Scenario: Absence of an in-body marker is not itself an ambiguity

- **WHEN** a segment's own body slice contains no `[[Pág. N]]` marker, but the document-wide marker map resolves a page for that segment's start and end offsets
- **THEN** the segment is produced normally with the resolved `page_start`/`page_end`
- **AND** no `ambiguity_reason` is raised solely because the segment's own body lacks a marker

#### Scenario: Unresolvable page context blocks segmentation

- **WHEN** a boundary match's own start offset precedes every `[[Pág. N]]` marker in the document-wide map, so no page number can be resolved for it
- **THEN** the result outcome is `ambiguous` with reason `unresolved_page_context`
- **AND** no segment is produced

#### Scenario: A regressive page marker sequence blocks segmentation

- **WHEN** the document-wide marker map contains a `[[Pág. N]]` marker whose page number is lower than a preceding marker's page number
- **THEN** the result outcome is `ambiguous` with reason `non_monotonic_page_markers`
- **AND** no segment is produced

### Requirement: Ambiguous structural signals block segmentation and require human review

When boundary detection cannot establish an unambiguous `single` or `segments` outcome — including when two or more distinct registered rules both produce matches in the same document, when matches are not monotonically increasing in page order, when a boundary's page context cannot be resolved from the document-wide marker map (`unresolved_page_context`), or when the document-wide marker map itself contains a regressive page sequence (`non_monotonic_page_markers`) — the system SHALL return outcome `ambiguous` with a specific, non-empty `ambiguity_reason`, SHALL NOT produce any segment, and SHALL NOT allow the Legal Producer to render or publish any concept candidate for that source until the ambiguity is resolved by a human-authorized change (e.g. a corrected or disambiguated registry rule, or explicit manual segment definition supplied through a future authorized extension).

#### Scenario: Conflicting rules block segmentation

- **WHEN** two distinct registered Segmentation Rules each produce at least one match in the same Markdown body
- **THEN** the result outcome is `ambiguous`
- **AND** the `ambiguity_reason` identifies the conflicting rule identifiers

#### Scenario: Ambiguous outcome blocks the Producer

- **WHEN** the Legal Producer or its CLI receives an `ambiguous` segmentation outcome for a source
- **THEN** no concept candidate is built or published for that source
- **AND** the CLI reports a deterministic blocked exit code with the `segmentation_ambiguous` reason

### Requirement: Multi-concept sources are never published as a single collapsed concept

When Legal Source Segmentation returns outcome `segments`, the Legal Producer and its CLI SHALL NOT render or publish a single concept candidate whose body is the entire unsegmented source. The `producer build` command SHALL require the operator to explicitly select one segment (`--segment SEGMENT_ID`) or all segments (`--all-segments`) before rendering any candidate for a `segments` outcome; invoking `build` against a `segments` outcome without one of these selections SHALL block with a deterministic exit code and an explicit `segmentation_multi_concept` reason, and SHALL NOT fall back to whole-document rendering.

#### Scenario: Unselected multi-concept build is blocked

- **WHEN** `producer build` is invoked against a Phase 1 artifact whose segmentation outcome is `segments`, without `--segment` or `--all-segments`
- **THEN** the command blocks with a deterministic exit code
- **AND** no candidate is rendered
- **AND** the block reason is `segmentation_multi_concept`

#### Scenario: Explicit segment selection renders only that segment when identity is resolved

- **WHEN** `producer build --segment SEGMENT_ID` is invoked against a `segments` outcome and that segment's identity resolution status is `resolved`
- **THEN** the rendered candidate's body equals exactly that segment's body
- **AND** no content from any other segment is included

#### Scenario: All-segments build renders one candidate per resolved segment and reports the rest as blocked

- **WHEN** `producer build --all-segments` is invoked against a `segments` outcome
- **THEN** the command renders exactly one candidate for every segment whose identity resolution status is `resolved`
- **AND** every segment whose identity resolution status is not `resolved` is reported as a blocked segment in the same response, with no candidate rendered for it

### Requirement: Source document, source segment, and legal concept are distinct entities with distinct identity rules

The system SHALL distinguish exactly three entities and SHALL NOT conflate their identifiers or identity sources: (1) the **source document**, identified by its PDF provenance (`repo_jur_pdf_hash`/evidence resource) and unchanged by segmentation; (2) the **source segment**, a structural unit produced by Legal Source Segmentation, identified only by a deterministic, position-derived `segment_id` and carrying a `source_unit_label` (the verbatim structural boundary heading) as purely descriptive, operational metadata; and (3) the **legal concept**, the publishable `ConceptCandidate` whose canonical domain-specific identity fields MUST be resolved from the segment's own body content according to the Legal OKF Profile rules for the operator-declared `type`. A segment's `segment_id` and `source_unit_label` SHALL NEVER be written into any canonical domain-specific identity field, and SHALL NEVER be used as a filename, path-slug, or any other fallback that substitutes for an unresolved legal identity.

#### Scenario: Segment identifiers never appear as canonical identity fields

- **WHEN** a concept candidate is rendered from a segment
- **THEN** neither the segment's `segment_id` nor its `source_unit_label` appears in `repo_jur_tema_numero`, `repo_jur_precedente_numero`, `repo_jur_processo_numero`, or any other domain-specific canonical field, regardless of whether that segment's own body independently and unambiguously extracts a value for that field

#### Scenario: Unresolved segment identity never falls back to a structural label as path or identity

- **WHEN** a segment's own body does not yield the canonical identity fields required by the operator-declared `type`
- **THEN** the Producer does not render a publishable candidate for that segment using the segment's label, ordinal, or any positional slug as a substitute identity
- **AND** the segment is reported as blocked with a specific identity-unresolved reason

### Requirement: Segment identity resolution is explicit, auditable, and fail-closed

For every segment of a `segments` outcome, the system SHALL compute an identity resolution whose status is exactly one of `resolved`, `requires_operator_metadata`, or `ambiguous`, derived only from that segment's own body content using the same deterministic extraction and ambiguity-safe rules applied to whole-document candidates today. `producer build` SHALL render a publishable candidate for a segment only when that segment's identity resolution status is `resolved`. A segment whose status is `requires_operator_metadata` or `ambiguous` SHALL block that segment's build with a `LegalProducerBlockedError` carrying reason `identity_unresolved`, and SHALL NOT be published under any fallback identity.

#### Scenario: Resolved identity permits building

- **WHEN** a segment's own body yields all canonical identity fields required by the operator-declared `type`, unambiguously
- **THEN** the segment's identity resolution status is `resolved`
- **AND** `producer build` renders a candidate for that segment

#### Scenario: Missing canonical identity blocks the segment

- **WHEN** a segment's own body does not yield the canonical identity fields required by the operator-declared `type`, and no doctrinal/abstract absence allowance genuinely applies to that segment
- **THEN** the segment's identity resolution status is `requires_operator_metadata`
- **AND** `producer build` blocks that segment with reason `identity_unresolved`, publishing no candidate for it

#### Scenario: Conflicting identity signals block the segment

- **WHEN** a segment's own body yields two or more conflicting values for a canonical identity field that must be singular
- **THEN** the segment's identity resolution status is `ambiguous`
- **AND** `producer build` blocks that segment with reason `identity_unresolved`, publishing no candidate for it

#### Scenario: Ambiguity-safe extraction rules remain scoped per segment

- **WHEN** a segment's own body cites two or more distinct `Tema n. N` numbers as internal cross-references
- **THEN** `repo_jur_tema_numero` is not extracted for that segment
- **AND** that segment's identity resolution status reflects the absence per the applicable conditional-mandatory rule for its type, without inheriting any value computed from a different segment

### Requirement: Editorial-compilation bulletins are not silently treated as official numbered themes

The system SHALL NOT treat an editorial bulletin/collection-issue identifier (such as an "Edição N" heading of a thematic compilation bulletin) as equivalent to a court's official numbered-theme identifier (`repo_jur_tema_numero`). When a segment's own body does not itself establish that the segment represents exactly one official numbered theme or one genuinely abstract/doctrinal theme — for example, because the segment is demonstrably an editorial compilation citing multiple unrelated official theme numbers as grounding — the system SHALL NOT extract `repo_jur_tema_numero` from that segment, SHALL NOT treat the segment as a valid doctrinal/abstract `TemaJuridico` by default, and SHALL resolve that segment's identity status as `requires_operator_metadata` rather than publishing it under a fabricated or borrowed identity.

#### Scenario: Editorial edição segment does not resolve as TemaJuridico by default

- **WHEN** a segment corresponds to an editorial bulletin issue (e.g. an "Edição N" heading) whose body cites multiple unrelated official `Tema n. N` numbers as grounding for distinct theses
- **THEN** `repo_jur_tema_numero` is not extracted for that segment
- **AND** the segment's identity resolution status is `requires_operator_metadata`, not `resolved`
- **AND** `producer build --type TemaJuridico` blocks that segment rather than publishing it

#### Scenario: Genuine official numbered theme still resolves

- **WHEN** a segment's own body is itself the record of exactly one official numbered theme (e.g. a fixed tabular "Tema Repetitivo N" record), independent of any internal cross-reference to other themes
- **THEN** the applicable canonical identity field is extracted and the segment's identity resolution status is `resolved`

### Requirement: Boundary detection and identity extraction for a structural record header share exactly one canonical parser

When a Segmentation Rule's boundary anchor is itself the record's own canonical identity source (e.g. the `precedentes-qualificados-tema-repetitivo-v1` fixed tabular header), the system SHALL define and consume exactly one structural pattern for that header shape from a single location, and SHALL NOT maintain a second, independently authored regex or parser elsewhere that recognizes the same real-world structural fact. Both the Segmentation Rule's `detect()` boundary matcher and `resolve_segment_identity()`'s field extraction for that concept type SHALL derive from this same canonical pattern, so that a corpus-evidenced correction to the accepted structural forms (e.g. widening an accepted field separator) is expressed once and applies identically to both boundary detection and identity extraction.

#### Scenario: A corpus-evidenced header form recognized as a boundary also resolves as identity

- **WHEN** a segment's own body begins with a `Tema Repetitivo` header using any corpus-evidenced accepted separator form (per the field-separator requirement above)
- **THEN** `resolve_segment_identity()` extracts `repo_jur_precedente_numero` from that same header using the same canonical structural pattern that recognized it as a boundary
- **AND** no second, independently defined regex for this header shape exists elsewhere in the codebase

#### Scenario: An internal citation without the full header shape never resolves identity

- **WHEN** a segment's body contains a bare `Tema Repetitivo N` citation in running prose that does not satisfy the canonical pattern's full three-field shape
- **THEN** `resolve_segment_identity()` does not extract `repo_jur_precedente_numero` from that citation
- **AND** that citation does not override or contribute to the segment's own header-derived identity

### Requirement: Shared PDF provenance across multiple concepts from one source is explicit and non-colliding

Two or more concept candidates rendered from segments of the same Phase 1 artifact SHALL each carry the same `repo_jur_pdf_hash` (or, for multi-PDF concepts, the same `repo_jur_pdf_hashes` mapping) identifying the shared physical PDF evidence, without that shared hash causing an identity collision, a duplicate-resolution no-op, or a rejection between the distinct segment-derived concepts. Concept identity and positional path resolution SHALL remain governed by each segment's own canonical fields (or positional fallback), independent of PDF hash equality.

#### Scenario: Two segment candidates share one PDF hash without colliding

- **WHEN** two concept candidates are rendered from two segments of the same PDF-derived Phase 1 artifact
- **THEN** both candidates carry the identical `repo_jur_pdf_hash`
- **AND** they resolve to two distinct concept paths
- **AND** publishing one does not block, overwrite, or no-op the other

### Requirement: The operator can inspect segmentation and identity resolution before building or publishing anything

The system SHALL provide a read-only `producer analyze` command that requires an explicit `--type`, executes Legal Source Segmentation against a Phase 1 Markdown and technical report, and, for each segment, computes and reports its identity resolution. The command SHALL report the segmentation outcome, and for `segments`, each segment's `segment_id`, `source_unit_label`, page range, boundary rule identifier, `identity_status` (`resolved`, `requires_operator_metadata`, or `ambiguous`), the canonical identity fields actually and unambiguously extracted from that segment's own body when `resolved`, and an identity reason when not `resolved`. The `analyze` command SHALL NOT write to the operational state directory, SHALL NOT write to `repo_jur/bundle/`, and SHALL NOT itself constitute or imply a publication decision.

#### Scenario: Analyze reports segmentation outcome and per-segment identity status without side effects

- **WHEN** `producer analyze` is invoked against a Phase 1 Markdown and technical report with an explicit `--type`
- **THEN** the command reports the segmentation outcome and, for `segments`, each segment's `segment_id`, `source_unit_label`, page range, boundary rule identifier, and `identity_status`
- **AND** no file is written under the operational state directory or under `repo_jur/bundle/`

#### Scenario: Analyze reports the ambiguity reason

- **WHEN** `producer analyze` is invoked against a source whose segmentation outcome is `ambiguous`
- **THEN** the command reports the outcome as `ambiguous` and the specific `ambiguity_reason`
- **AND** no segment count or segment list implying a valid split is reported

#### Scenario: Analyze distinguishes resolved from unresolved segment identity

- **WHEN** `producer analyze` reports segments with different identity resolution outcomes
- **THEN** a segment with `identity_status: resolved` is reported together with its extracted canonical identity fields
- **AND** a segment with `identity_status: requires_operator_metadata` or `identity_status: ambiguous` is reported together with its identity reason and no fabricated identity fields

### Requirement: PrecedenteVinculante tribunal identity requires evidence belonging to its own record

For `PrecedenteVinculante`, `repo_jur_tribunal` SHALL identify the court that issued or is institutionally responsible for the official precedent represented by that segment. The fixed `Tema Repetitivo` header SHALL supply its own precedent number/status but SHALL NOT imply STJ by itself. Tribunal resolution SHALL use only the segment's body and SHALL require own evidence: an own-number `Tema N/STJ|STF` self-citation, an explicit self-referential court/theme phrase, or an institutional court organ acting on the own record. A cross-reference, loose court citation, or satellite-process mention SHALL NOT define tribunal alone. Exactly one supported court SHALL resolve, no supported court SHALL require operator metadata, and genuinely conflicting own evidence SHALL be ambiguous.

#### Scenario: Own-number self-citation resolves tribunal

- **GIVEN** a `PrecedenteVinculante` segment whose canonical header resolves number N
- **WHEN** its body contains `Tema N/STJ` or `Tema N/STF` as a self-citation
- **THEN** `repo_jur_tribunal` resolves to that court

#### Scenario: Cross-reference never resolves identity alone

- **GIVEN** a segment containing only a different Tema/court reference, `Vide`, `Repercussão Geral`, `Controvérsia`, or a satellite `Processo STF|STJ` mention
- **WHEN** no own evidence supports a court
- **THEN** identity status is `requires_operator_metadata`
- **AND** textual mention order does not alter that result

#### Scenario: Header alone does not imply STJ

- **GIVEN** a complete `Tema Repetitivo N Situação ... Órgão ...` structural header
- **WHEN** the body contains no separate own tribunal evidence
- **THEN** the header resolves number/status but does not resolve `repo_jur_tribunal`
- **AND** identity status is `requires_operator_metadata`

#### Scenario: Genuine own-evidence conflict is ambiguous

- **GIVEN** one segment with valid own STJ evidence and valid own STF evidence
- **WHEN** its identity is resolved
- **THEN** identity status is `ambiguous`
- **AND** neither court is selected by first occurrence

### Requirement: The Precedentes Qualificados document trailer is not segment content

For `precedentes-qualificados-tema-repetitivo-v1`, the system SHALL exclude the document-wide trailer from the final source segment only when the unique UI action anchor is structurally followed by the institutional NUGEPNAC provenance anchor after the last record boundary. The end boundary SHALL be fail-safe: without the complete two-anchor structure, the final segment SHALL continue to EOF unchanged.

#### Scenario: Complete structural trailer is excluded

- **GIVEN** the last precedent record followed by `Exportar todos Imprimir todos Imprimir selecionados`
- **AND** the action line is followed by the institutional NUGEPNAC/Secretaria de Jurisprudência provenance line
- **WHEN** segmentation runs with the precedent rule
- **THEN** the last `Segment.body` ends immediately before the action line
- **AND** its legitimate update line and record content remain present

#### Scenario: Partial trailer anchor does not cut

- **GIVEN** only one trailer-like anchor or an incomplete pair inside a record
- **WHEN** segmentation runs
- **THEN** no trailer end boundary is applied at that position
- **AND** the last segment continues to EOF when no complete pair exists

#### Scenario: Trailer boundary preserves literal positional semantics

- **GIVEN** a complete trailer after the last precedent
- **WHEN** the end boundary is applied
- **THEN** the retained body is an exact contiguous source substring
- **AND** no synthetic `[[Pág. N]]` marker is inserted
- **AND** `page_end` is the page active at the retained body's final character

