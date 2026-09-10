# Identity and Portability

## ADDED Requirements

### Requirement: Positional legal concept identity

The system SHALL derive `concept_id` exclusively from the Markdown path relative to `bundle/`, without the `.md` extension.

The `concept_id` SHALL be positional and SHALL NOT be persisted as a frontmatter field.

All Producer-generated filename and slug components SHALL:
- use lowercase letters;
- transliterate accents to ASCII;
- use only `[a-z0-9_]`;
- use `_` as the logical separator;
- avoid inventing unavailable metadata;
- end in `.md` when referring to physical Markdown files.

#### Scenario: Moving a concept changes its positional identity

- **WHEN** a concept Markdown file is moved or renamed inside `bundle/`
- **THEN** its `concept_id` changes to the new relative path without `.md`
- **AND** no Stable ID, UUID, logical hash, or persisted `concept_id` is introduced automatically.

### Requirement: Canonical Legal Knowledge trees

The system SHALL preserve the four mandatory canonical trees:
- `bundle/legislacao/`
- `bundle/jurisprudencia/`
- `bundle/temas/`
- `bundle/precedentes/`

The system SHALL NOT introduce mandatory physical taxonomies for `Jurisprudencia`, `TemaJuridico`, or `PrecedenteVinculante` by tribunal, branch of law, or institutional body without a separate normative decision.

#### Scenario: Jurisprudence remains in the canonical top-level tree

- **WHEN** a `Jurisprudencia` concept is published
- **THEN** it is published under `bundle/jurisprudencia/`
- **AND** the Producer does not create a mandatory tribunal or branch-of-law subdirectory solely from metadata.

### Requirement: Legislation physical organization by primary branch

For `Legislacao`, the system SHALL organize numbered normative acts as:

`legislacao/{ramo_principal}/{tipo_norma}_{numero_norma}_{ano}.md`

The sphere SHALL remain represented by `repo_jur_lei_esfera` and SHALL NOT determine the physical directory.

The filename SHALL use only normative metadata actually available and SHALL apply deterministic fallback behavior without inventing unavailable identifiers.

#### Scenario: Código Civil receives the approved positional path

- **WHEN** the reviewed legislation is Lei nº 10.406/2002
- **AND** the operational publication branch is unambiguously `direito_civil`
- **THEN** the canonical path is `bundle/legislacao/direito_civil/lei_10406_2002.md`.

### Requirement: Legislation branch ambiguity requires Human Review

`publication_ramo_principal` SHALL be an operational publication signal and SHALL NOT be persisted in Legal OKF frontmatter.

It SHALL be used only to determine the physical subdirectory of `Legislacao`.

Its value SHALL be supported unambiguously by semantic review or HUMAN curation and normalized using the canonical slug rules.

`repo_jur_ramo_direito` SHALL NOT be automatically reused as `publication_ramo_principal`.

#### Scenario: Ambiguous primary branch blocks automatic publication

- **WHEN** `publication_ramo_principal` is absent or ambiguous for a legislation concept
- **THEN** automatic publication is blocked
- **AND** the outcome requires HUMAN REVIEW
- **AND** no `desconhecido` branch directory is created.

### Requirement: Deterministic filenames for other legal concept types

For `Jurisprudencia`, filenames SHALL identify the judicial act deterministically using only official metadata actually available.

When tribunal, procedural class, document type, and official number are available, a filename MAY follow:

`{tipo_documento}_{tribunal}_{classe}_{numero}.md`

For official numbered `TemaJuridico`, a filename MAY follow:

`tema_{tribunal}_{numero_tema}.md`

For `PrecedenteVinculante`, the filename SHALL reflect the actual precedent species and available official identifiers. A numbered súmula MAY follow:

`sumula_{classe_precedente}_{tribunal}_{numero}.md`

The system SHALL NOT invent tribunal, number, class, document type, or precedent species.

#### Scenario: Missing judicial metadata uses deterministic fallback

- **WHEN** one or more recommended filename components are unavailable
- **THEN** the Producer uses only available official identifiers or a deterministic fallback
- **AND** it does not invent missing metadata.

### Requirement: Evidence and provenance remain separate from legal identity

Original PDFs SHALL remain outside Git and outside `bundle/`, preserved in external Object Storage.

For concepts derived from identifiable PDF evidence:
- `sources` SHALL record the evidence actually used;
- each `sources[].resource` SHALL be stable and resolvable;
- this change SHALL NOT mandate a specific URI scheme;
- `evidence://` SHALL NOT be introduced or required by this change;
- `source_origin` SHALL NOT automatically become `sources[].resource`.

The top-level OKF `resource`, when applicable, SHALL identify the underlying real-world asset of the concept and SHALL NOT automatically duplicate `sources[].resource`.

SHA-256 SHALL identify physical evidence bytes and SHALL NOT define legal concept identity.

#### Scenario: Single PDF provenance uses the source reference

- **WHEN** one PDF is the evidence for a generated concept
- **THEN** `sources[].resource` contains the stable resolvable evidence reference
- **AND** `repo_jur_pdf_hash` records the PDF SHA-256
- **AND** no `evidence://` URI is synthesized solely for publication.

### Requirement: PDF cardinality metadata

For exactly one PDF, the system SHALL use `repo_jur_pdf_hash` and SHALL omit `repo_jur_pdf_hashes`.

For two or more PDFs, the system SHALL omit singular `repo_jur_pdf_hash` and SHALL use `repo_jur_pdf_hashes`.

For multi-PDF concepts, every PDF source SHALL have a `sources[].id` that maps exactly to one entry in `repo_jur_pdf_hashes`.

#### Scenario: Multi-PDF provenance maps source IDs to hashes

- **WHEN** a concept is derived from two or more PDFs
- **THEN** each PDF has a unique `sources[].id`
- **AND** each source ID has exactly one corresponding SHA-256 entry in `repo_jur_pdf_hashes`
- **AND** singular `repo_jur_pdf_hash` is omitted.

### Requirement: Canonical Legal OKF frontmatter

The system SHALL render conventional readable YAML mappings.

For pipeline-produced concepts:
- `type` SHALL be present;
- `generated` SHALL be present;
- `sources` SHALL be present when identifiable sources exist;
- each `sources[].resource` SHALL be present for a source;
- `title` is recommended but not mandatory;
- top-level `resource` is recommended only when an identifiable underlying asset exists;
- `status` is optional and Human-Owned;
- existing Human-Owned fields SHALL NOT be overwritten autonomously by the Producer;
- there SHALL be no normative requirement for alphabetical YAML key ordering;
- mappings SHALL NOT be serialized as JSON strings.

Technical Phase 1 execution metadata SHALL remain in technical JSON and SHALL NOT be required in canonical Legal OKF frontmatter.

#### Scenario: Technical Phase 1 drift does not mutate the concept

- **WHEN** only technical Phase 1 execution metadata changes
- **AND** legal body, evidence provenance, type, and canonical legal metadata are unchanged
- **THEN** the canonical concept remains a NOOP
- **AND** technical execution metadata is not copied into Legal OKF frontmatter.

### Requirement: Structured relations to legislation

`Jurisprudencia`, `TemaJuridico`, and `PrecedenteVinculante` MAY record structured normative relations through `repo_jur_normas_referenciadas`.

Each relation SHALL use a valid `Legislacao` `concept_id`.

Article numbers SHALL be populated only when supported by the source.

The system SHALL NOT invent a normative relation or article number solely from semantic similarity.

#### Scenario: Supported legislation relation is recorded structurally

- **WHEN** a source explicitly supports a relation to `legislacao/direito_civil/lei_10406_2002`
- **AND** supports articles `421` and `422`
- **THEN** the relation MAY record that concept and those article numbers
- **AND** unsupported article numbers are not added.

### Requirement: Controlled evolution of branch-of-law metadata

`repo_jur_ramo_direito` SHALL evolve only through a controlled compatibility-preserving migration toward multivalued representation.

The migration SHALL:
- preserve existing singular values;
- preserve Human-curated classifications;
- not reorganize `Jurisprudencia`, `TemaJuridico`, or `PrecedenteVinculante` physically by branch of law;
- not use `repo_jur_ramo_direito` automatically as the Legislation publication branch.

#### Scenario: Existing singular branch value remains valid during migration

- **WHEN** an existing legal concept contains a singular `repo_jur_ramo_direito`
- **THEN** the migration preserves that value
- **AND** does not move the concept solely because of that metadata.

### Requirement: Controlled positional migration

When a canonical path changes because of this architectural correction, the system SHALL detect an existing logically equivalent concept at an older path before publishing a second positional identity.

Automatic publication SHALL be blocked for HUMAN-approved migration when such a collision is detected.

The migration itself SHALL NOT occur as part of this change unless separately validated and approved by HUMAN.

#### Scenario: Existing SHA-named concept blocks duplicate canonical publication

- **WHEN** the same logical legislation concept already exists under an older SHA-based path
- **AND** the new canonical target path does not yet exist
- **THEN** publication is blocked for controlled migration
- **AND** no duplicate concept is written
- **AND** the existing file is not moved automatically.
