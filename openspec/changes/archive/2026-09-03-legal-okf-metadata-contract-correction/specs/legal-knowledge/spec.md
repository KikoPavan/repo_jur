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
   - `repo_jur_processo_numero` (String, Mandatory): The process identifier (CNJ format is preferentially preferred, but STJ/STF appellate case identifiers like REsp/AREsp/AgInt or register numbers are also valid fallbacks when CNJ is not available; no separate field for court-class identifiers exists in the FROZEN profile).
   - `repo_jur_tribunal` (String, Mandatory): The court acronym in uppercase.
   - `repo_jur_relator` (String, Mandatory): The magistrate relator name.
   - `repo_jur_data_julgamento` (String YYYY-MM-DD, Mandatory): The date of judgment.
   - `repo_jur_ramo_direito` (String, Recommended): The branch of law.
3. **TemaJuridico**
   - `repo_jur_tema_numero` (String, Conditional Mandatory): Mandatory if representing an official numbered theme.
   - `repo_jur_tribunal` (String, Conditional Mandatory): Mandatory if representing an official court theme.
4. **PrecedenteVinculante**
   - `repo_jur_precedente_numero` (String, Mandatory): The precedent/sumula number.
   - `repo_jur_precedente_status` (String, Mandatory): The precedent status (`ativo`, `cancelado`, `revisado`).
   - `repo_jur_tribunal` (String, Mandatory): The court acronym.

The system SHALL reject any legacy, un-prefixed, or inappropriate fields including `jurisdicao`, `ambito`, `tipo_norma`, `ementa`, `tema`, `subtema`, `tese_fixada`, `tribunal` (without prefix), and `relator` (without prefix). Under the FROZEN profile, both `title` and `description` are recommended but not mandatory. `title` is permitted/recommended but not guaranteed to have deterministic initial population, and `description` is optional with no initial automation required. Neither field is required to appear in the real-corpus acceptance assertion.

Every automatically extracted metadata field MUST carry physical page references mapped via page_refs matching the [[Pág. N]] markers from which the text was deterministic-extracted. These page references are transient and persisted only in operational logs/JSON reports, never written to the canonical YAML frontmatter. Any cognitive/LLM classification or metadata inference is strictly prohibited. If a mandatory field cannot be deterministic-extracted, the Producer run MUST be aborted with exit code 5 (blocked) and NO publication SHALL occur.

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
