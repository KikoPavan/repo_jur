## ADDED Requirements

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
