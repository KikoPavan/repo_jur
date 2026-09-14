## ADDED Requirements

### Requirement: Deterministic Filename-Prefix Classification
The system SHALL classify every PDF discovered in `input/leis_jurisprudencia/` exclusively by the
first four characters of its filename, using a fixed vocabulary, and SHALL NOT consult document
content, regex over extracted text, AI/LLM inference, or any fallback heuristic to determine or
override that classification.

- **Vocabulary**: `LEG_` → `Legislacao`; `JUR_` → `Jurisprudencia`; `PRE_` → `PrecedenteVinculante`;
  `TEM_` → `TemaJuridico`. Matching is exact, case-sensitive, and anchored strictly at the start of
  the basename.
- **No variation accepted**: any deviation from an exact prefix match — different case (e.g.
  `leg_`), the prefix occurring elsewhere in the filename instead of at the start, or a near-miss
  string that is not one of the four literal prefixes — SHALL be treated identically to a missing
  prefix: the file is `BLOCKED`, never coerced to the closest valid type.
- **Free suffix**: the remainder of the filename after a matched 4-character prefix is not parsed,
  validated, or used as an identity signal by the classifier.
- **No content access before classification**: the classifier SHALL determine `blocked`/
  `concept_type` from the filename alone, without opening or reading the PDF's bytes.

#### Scenario: LEG_ prefix classifies as Legislacao
- **GIVEN** `input/leis_jurisprudencia/LEG_L13.105_CPC_2015.pdf` exists
- **WHEN** `repo-jur ingest` runs
- **THEN** the file is classified `concept_type=Legislacao` and is not blocked

#### Scenario: JUR_ prefix classifies as Jurisprudencia
- **GIVEN** `input/leis_jurisprudencia/JUR_REsp_1704551-SP.pdf` exists
- **WHEN** `repo-jur ingest` runs
- **THEN** the file is classified `concept_type=Jurisprudencia` and is not blocked

#### Scenario: PRE_ prefix classifies as PrecedenteVinculante
- **GIVEN** `input/leis_jurisprudencia/PRE_STJ_Precedentes_Qualificados.pdf` exists
- **WHEN** `repo-jur ingest` runs
- **THEN** the file is classified `concept_type=PrecedenteVinculante` and is not blocked

#### Scenario: TEM_ prefix classifies as TemaJuridico
- **GIVEN** `input/leis_jurisprudencia/TEM_Jurisprudencia_Teses_ed171.pdf` exists
- **WHEN** `repo-jur ingest` runs
- **THEN** the file is classified `concept_type=TemaJuridico` and is not blocked

#### Scenario: Invalid or missing prefix is blocked, never guessed
- **GIVEN** `input/leis_jurisprudencia/relatorio_anual.pdf` exists (no recognized prefix)
- **WHEN** `repo-jur ingest` runs
- **THEN** the file's operational status is `BLOCKED` with reason `invalid_or_missing_prefix`
- **AND** the file is never converted, segmented, or built as any concept type

#### Scenario: Lowercase or misplaced prefix variant is blocked, never coerced
- **GIVEN** `input/leis_jurisprudencia/leg_lei_ordinaria.pdf` exists (lowercase `leg_`)
- **WHEN** `repo-jur ingest` runs
- **THEN** the file's operational status is `BLOCKED` with reason `invalid_or_missing_prefix`
- **AND** the file is never treated as `Legislacao` or any other type

#### Scenario: Non-PDF regular file is reported as BLOCKED, never silently skipped
- **GIVEN** `input/leis_jurisprudencia/LEG_readme.txt` exists alongside valid PDFs
- **WHEN** `repo-jur ingest` runs
- **THEN** the file appears in the run's file list with status `BLOCKED` and reason
  `unsupported_media_type`
- **AND** the file is never opened or treated as any concept type

### Requirement: The `.gitkeep` Repository Sentinel Is Never Discovered
`repo-jur ingest` SHALL treat a regular file named exactly `.gitkeep` directly inside
`input/leis_jurisprudencia/` as an internal repository sentinel used solely to version the
otherwise-empty directory, and SHALL exclude it from discovery entirely: it SHALL NOT appear in the
run's file list, SHALL NOT be classified, and SHALL NOT be counted in the aggregate summary
(including `total`). This exclusion is exact-name-only (`.gitkeep`) and SHALL NOT be generalized to
any other dotfile or non-PDF regular file — every other file, including any other file starting
with `.`, remains subject to the existing `unsupported_media_type` /
`invalid_or_missing_prefix` classification and reporting rules above.

#### Scenario: .gitkeep sentinel is excluded from discovery, report, and totals
- **GIVEN** `input/leis_jurisprudencia/.gitkeep` exists alongside one valid `LEG_` PDF
- **WHEN** `repo-jur ingest` runs
- **THEN** the run's file list contains only the `LEG_` PDF's entry
- **AND** the summary's `total` and per-status counts reflect only the `LEG_` PDF
- **AND** `.gitkeep` never appears in the file list under any status

#### Scenario: A dotfile other than .gitkeep is still reported as BLOCKED
- **GIVEN** `input/leis_jurisprudencia/.hidden_notes.pdf` exists alongside valid PDFs
- **WHEN** `repo-jur ingest` runs
- **THEN** the file appears in the run's file list with status `BLOCKED` and reason
  `invalid_or_missing_prefix`
- **AND** it is counted in the aggregate summary like any other blocked file

### Requirement: Reserved, Unscanned `input/processo/`
The system SHALL create `input/processo/` as a reserved operational input root and SHALL NOT scan,
classify, or process any file placed inside it as part of `repo-jur ingest` or any other command
introduced by this change.

#### Scenario: input/processo/ is never scanned by ingest
- **GIVEN** `input/processo/` contains one or more PDF files
- **WHEN** `repo-jur ingest` runs against `input/leis_jurisprudencia/`
- **THEN** none of the files under `input/processo/` appear in the run's file list or summary

### Requirement: Single Operational Ingestion Command
The system SHALL provide `repo-jur ingest` as the single entrypoint that discovers PDFs in
`input/leis_jurisprudencia/`, classifies them deterministically, and drives each valid file through
Phase 1 conversion, the Quality Gate, `producer analyze`-equivalent segmentation/identity
resolution, `producer build`-equivalent candidate construction, and `producer validate`-equivalent
re-validation, reusing the existing implementations of each stage without duplicating their logic.

#### Scenario: A valid Legislacao PDF is converted, gated, and built into a validated candidate
- **GIVEN** `input/leis_jurisprudencia/LEG_<...>.pdf` is a well-formed native-text PDF
- **WHEN** `repo-jur ingest` runs
- **THEN** a Phase 1 Markdown/report pair is produced via the existing conversion pipeline
- **AND** the recorded Quality Gate outcome is `PASS` or `PASS_WITH_WARNINGS`
- **AND** exactly one candidate is built, independently re-validated, and written under
  `var/producer/candidates/`

### Requirement: Multi-Concept Precedente Handling Preserved
For `PRE_`-classified sources whose segmentation outcome is `SEGMENTS`, `repo-jur ingest` SHALL
build a candidate for every segment whose identity resolves, using the same selection and exclusion
semantics as `producer build --all-segments`, without any type-specific branch that diverges from
the shared `--all-segments` code path used for any other type.

#### Scenario: Multi-precedent source yields one candidate per resolvable segment
- **GIVEN** `input/leis_jurisprudencia/PRE_STJ_Precedentes_Qualificados.pdf` segments into 10
  distinct "Tema Repetitivo" records, all with resolvable identity
- **WHEN** `repo-jur ingest` runs
- **THEN** 10 candidates are built, one per segment, each independently validated
- **AND** the file's aggregate status is `READY_TO_PUBLISH`

### Requirement: TemaJuridico Unresolved-Identity Segments Remain Blocked
For `TEM_`-classified sources, `repo-jur ingest` SHALL exclude any segment whose identity status is
`identity_unresolved` from the built candidates and SHALL report it as a blocked segment, never
inventing, guessing, or falling back to a non-canonical identity value for it.

#### Scenario: A TemaJuridico segment with unresolved identity is excluded and reported
- **GIVEN** a `TEM_`-classified source segments into 3 units, one of which has no resolvable
  `repo_jur_tema_numero`
- **WHEN** `repo-jur ingest` runs
- **THEN** 2 candidates are built for the 2 resolvable segments
- **AND** the third segment appears in `blocked_segments` with reason `identity_unresolved`
- **AND** the file's aggregate status is `REVIEW_REQUIRED`

### Requirement: No Automatic Publication or Retrieval Sync
`repo-jur ingest` SHALL NOT write to `bundle/`, SHALL NOT invoke `producer publish` or
`guard_legal_bundle_write` in a write-capable way, and SHALL NOT invoke `retrieval sync` or any
retrieval indexing command, under any file status — including `READY_TO_PUBLISH`, which SHALL be
interpreted strictly as "validated candidate, fit for human review/publication" and never as an
authorization for automatic publication.

#### Scenario: A fully ready file is not published to bundle/
- **GIVEN** a `LEG_` source that resolves to `READY_TO_PUBLISH`
- **WHEN** `repo-jur ingest` runs
- **THEN** no file under `bundle/` is created, modified, or deleted as a result
- **AND** no retrieval index artifact under `var/retrieval/` is created, modified, or deleted
- **AND** the candidate remains solely under `var/producer/candidates/`, awaiting a human-run
  `producer publish` invocation

### Requirement: Existing Concept Conflicts Require Human Review
When a built candidate's resolved target path already exists as a published concept in `bundle/`
and the two are materially different, `repo-jur ingest` SHALL report that file's status as
`REVIEW_REQUIRED` and SHALL NOT overwrite, merge, or otherwise resolve the conflict automatically.

#### Scenario: Conflicting existing concept forces human review
- **GIVEN** a candidate's resolved target path already exists in `bundle/` with materially
  different content
- **WHEN** `repo-jur ingest` runs
- **THEN** the file's status is `REVIEW_REQUIRED`
- **AND** `bundle/` is not modified

### Requirement: Source PDFs and Phase 1 Artifact Contracts Remain Untouched
`repo-jur ingest` SHALL NOT move, rename, delete, or mutate the source PDF files in
`input/leis_jurisprudencia/`, and SHALL write Phase 1 artifacts (Markdown, technical report) using
the same directory/contract conventions the existing `converter-juridico` CLI already uses.

#### Scenario: Source PDF is unchanged after ingest
- **GIVEN** a valid `JUR_` PDF exists in `input/leis_jurisprudencia/`
- **WHEN** `repo-jur ingest` runs
- **THEN** the PDF's path, bytes, and SHA-256 are unchanged after the run

### Requirement: Safe Rerun Without Artifact Corruption
Running `repo-jur ingest` more than once over an unchanged `input/leis_jurisprudencia/` SHALL
produce equivalent, non-corrupted operational outputs (candidates, state records, run reports)
without raising an unhandled write conflict.

#### Scenario: Rerun produces idempotent outputs
- **GIVEN** `repo-jur ingest` has already run once over a fixed input set
- **WHEN** `repo-jur ingest` runs again over the same, unchanged input set
- **THEN** the second run completes without raising `OutputAlreadyExistsError` or any unhandled
  exception
- **AND** the resulting candidate Markdown files are byte-identical to the first run's output

### Requirement: Aggregate and Per-File Operational Reporting
`repo-jur ingest` SHALL report, for each discovered PDF, one of the statuses `READY_TO_PUBLISH`,
`REVIEW_REQUIRED`, `BLOCKED`, or `ERROR`, and SHALL report an aggregate count per status for the
whole run.

#### Scenario: A run with mixed outcomes reports correct aggregate counts
- **GIVEN** one `LEG_` file that fully succeeds, one file with an invalid prefix, and one `JUR_`
  file whose Quality Gate outcome is recorded as `FAIL`
- **WHEN** `repo-jur ingest --json` runs
- **THEN** the summary reports `READY_TO_PUBLISH: 1`, `BLOCKED: 1`, `ERROR: 1`, `REVIEW_REQUIRED: 0`
