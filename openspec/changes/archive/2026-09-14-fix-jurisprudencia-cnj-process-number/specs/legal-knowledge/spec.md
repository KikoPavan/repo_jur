# Spec Delta: legal-knowledge

## MODIFIED Requirements

### Requirement: Producer renders a conformant Legal OKF concept candidate

The system SHALL render the concept candidate with a valid YAML frontmatter block delimited by `---` and beginning with the key `type`, followed by the Markdown body. The frontmatter SHALL satisfy the Legal OKF Profile v1.3: `generated` with `by` set to `repo_jur_producer/<version>` (the `generated.at` subfield, if present, MUST strictly be an ISO 8601 Datetime String, and `evidence:...` URI syntax is unauthorized); `sources` present when the concept derives from identifiable sources; domain-specific fields applied only for the applicable type (legislation, jurisprudence, theme, or binding-precedent fields); and `verified` present only when a real verification event exists. The body of a PDF-derived concept SHALL preserve the Phase 1 literal content including the canonical page markers `[[Pág. N]]` where applicable.

The system SHALL strictly enforce and validate the domain-specific fields for each concept type as follows:
1. **Legislacao**
   - `repo_jur_lei_numero` (String, Conditional Mandatory): The official number of the law (mandatory only for numbered acts, like Lei 10.406/2002).
   - `repo_jur_lei_ano` (Integer, Conditional Mandatory): The official year of the law (mandatory only for numbered acts, like Lei 10.406/2002).
   - `repo_jur_lei_esfera` (String, Mandatory): The governmental sphere (`federal`, `estadual`, `distrital`, `municipal`).
   - `repo_jur_lei_tipo` (String, Recommended): The type of normative act (e.g., `constituicao`, `complementar`, `ordinaria`, `decreto`, `portaria`, `medida_provisoria`).
2. **Jurisprudencia**
   - `repo_jur_processo_numero` (String, Mandatory): The unique CNJ (Conselho Nacional de Justiça) national-standard process number, canonical format `NNNNNNN-DD.AAAA.J.TR.OOOO`. The system SHALL accept only a value that is either found verbatim in this canonical punctuated form, or deterministically normalized from a standalone 20-digit unpunctuated source token, in both cases only after the CNJ mod-97 check digits validate. The system SHALL NEVER accept, as this field's value or as a fallback when no valid CNJ exists, an appellate/recursal case identifier (court-class label plus recourse number, e.g. `AgInt no RECURSO ESPECIAL Nº 1833684 - SC`, `REsp 1.833.684/SC`), an internal court register/autuação number (e.g. `2019/0251395-0`), or any other non-CNJ representation of the case — the superior-recourse identifier and the court's internal register number are distinct concepts from the CNJ process number and are never conflated with it. If the source document contains two or more structurally distinct, checksum-valid CNJ candidates with no deterministic basis for selecting the record's own base process, or if no checksum-valid CNJ is recoverable at all, the system SHALL NOT extract `repo_jur_processo_numero` (fail-closed) and SHALL NOT substitute any appellate or register identifier in its place.
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

#### Scenario: Canonical punctuated CNJ is preserved verbatim

- **WHEN** a `Jurisprudencia` candidate body contains the canonical punctuated CNJ `0311049-09.2016.8.24.0018`
- **THEN** `repo_jur_processo_numero` is extracted as `0311049-09.2016.8.24.0018` unchanged

#### Scenario: Unpunctuated 20-digit CNJ is normalized only when checksum-valid

- **WHEN** a `Jurisprudencia` candidate body contains only the unpunctuated digit run `03110490920168240018` as a standalone 20-digit token, and its CNJ mod-97 check digits validate
- **THEN** `repo_jur_processo_numero` is extracted as the normalized canonical form `0311049-09.2016.8.24.0018`

#### Scenario: A checksum-valid CNJ is chosen over a co-present appellate header

- **WHEN** a `Jurisprudencia` candidate body contains both an appellate/recursal header (e.g. `AgInt no RECURSO ESPECIAL Nº 1833684 - SC`) and a checksum-valid CNJ candidate elsewhere in the document (e.g. under `Número de Origem`)
- **THEN** `repo_jur_processo_numero` is extracted as the checksum-valid CNJ
- **AND** the appellate header value is never written to `repo_jur_processo_numero`

#### Scenario: Appellate header alone never populates the process number

- **WHEN** a `Jurisprudencia` candidate body contains only an appellate/recursal case identifier such as `AgInt no REsp 1.833.684/SC` and no checksum-valid CNJ anywhere in the document
- **THEN** `repo_jur_processo_numero` is not extracted and is absent from the candidate frontmatter

#### Scenario: Internal court register number alone never populates the process number

- **WHEN** a `Jurisprudencia` candidate body contains only an internal court register/autuação number such as `2019/0251395-0` and no checksum-valid CNJ anywhere in the document
- **THEN** `repo_jur_processo_numero` is not extracted and is absent from the candidate frontmatter

#### Scenario: Conflicting distinct CNJ candidates block automatic selection

- **WHEN** a `Jurisprudencia` candidate body contains two or more structurally distinct, checksum-valid CNJ candidates with no deterministic basis for selecting the record's own base process
- **THEN** `repo_jur_processo_numero` is not extracted and is absent from the candidate frontmatter
- **AND** the Producer does not silently select any one of the candidates

#### Scenario: A CNJ-shaped value with an invalid check digit is rejected

- **WHEN** a `Jurisprudencia` candidate body contains a CNJ-shaped value (canonical punctuation or standalone 20-digit token) whose mod-97 check digits do not validate
- **THEN** the value is not treated as a valid CNJ candidate
- **AND** it does not populate `repo_jur_processo_numero`
