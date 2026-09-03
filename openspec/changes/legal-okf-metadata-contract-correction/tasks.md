## 1. Clean Up and Schema Definitions

- [x] 1.1 Update `LegalConceptType` and `PROFILE_FIELDS` in `src/pipeline_juridico/legal_producer.py` to match the canonical fields from Legal OKF Profile v1.3.
- [x] 1.2 Remove non-authorized base/shared fields (such as `aliases` and `related`) from any canonical field lists, and confirm that `PROFILE_FIELDS` only defines the canonical keys:
  - **Legislacao:** `repo_jur_lei_numero`, `repo_jur_lei_ano`, `repo_jur_lei_esfera`, `repo_jur_lei_tipo`
  - **Jurisprudencia:** `repo_jur_processo_numero`, `repo_jur_tribunal`, `repo_jur_relator`, `repo_jur_data_julgamento`, `repo_jur_ramo_direito`
  - **TemaJuridico:** `repo_jur_tema_numero`, `repo_jur_tribunal`
  - **PrecedenteVinculante:** `repo_jur_precedente_numero`, `repo_jur_precedente_status`, `repo_jur_tribunal`
- [x] 1.3 Implement candidate validation in `validate_candidate` to universally reject any legacy/un-prefixed keys (`jurisdicao`, `ambito`, `tipo_norma`, `ementa`, `tema`, `subtema`, `tese_fixada`, `tribunal` without prefix, `relator` without prefix).
- [x] 1.4 Add safe upgrade-merge logic when loading existing concepts: the Producer must parse the file and filter out/strip any legacy/deprecated keys so that the regenerated file passes validation and is successfully upgraded.

## 2. Deterministic Extraction and Rule Support

- [x] 2.1 Implement deterministic extraction rules in **Legal Semantic Review** as the sole extraction component (the Producer is prohibited from parsing legal text or performing extraction, and must read fields from the `ReviewResult.extracted_fields` list):
  - **Legislacao:** Extract `repo_jur_lei_numero` and `repo_jur_lei_ano` (mandatory only for numbered acts), `repo_jur_lei_esfera`, and `repo_jur_lei_tipo`. State normalization for Lei 10.406/2002 to value `"ordinaria"`.
  - **Jurisprudencia:** Extract `repo_jur_processo_numero` (preferring CNJ format but accepting STJ/STF appellate case identifiers like REsp/AREsp/AgInt or register numbers as valid fallbacks when no CNJ format is available, ensuring no separate class field is invented), `repo_jur_tribunal`, `repo_jur_relator`, `repo_jur_data_julgamento`, and `repo_jur_ramo_direito`.
  - **TemaJuridico / PrecedenteVinculante:** Extract relevant canonical fields strictly from the source.
- [x] 2.2 Implement page and evidence reference tracing inside Semantic Review to populate `page_refs` on `ExtractedField` / `LegalPatch` based on `[[Pág. N]]` markers. Clarify that these page references are transient evidence and must be persisted only in operational logs/reports (never written to the canonical YAML frontmatter).
- [x] 2.3 Implement strict failure and blocked behavior: if a `Mandatory` or `Conditional Mandatory` field is missing and cannot be extracted deterministic-first, the run must abort with exit code `5` (blocked) and publish no concept. No operator-supplied canonical fields are permitted since `ProducerContext` only accepts `type` and `evidence_resource`.
- [x] 2.4 Align `generated` object: ensure `generated.by` is always `repo_jur_producer/<version>`, and verify that if `generated.at` is populated, it is strictly formatted as an ISO 8601 Datetime String, completely removing any legacy `evidence:...` format from expected YAML outputs, schemas, and planning.

## 3. Storage and Safe Curation Preservation

- [x] 3.1 Implement safe merge rules to preserve human-curated values of Shared and Human-Owned fields (`title`, `description`, `tags`, `stale_after`, `verified`), verifying that `title` is not guaranteed deterministic initial population, and `description` is optional with no initial automation required.
- [x] 3.2 Implement status field restrictions: the Producer is strictly prohibited from injecting default status values (such as `status: stable` or `status: draft`). If `status` has not been human-populated, the key must be entirely omitted from frontmatter (implicit default `stable` on absence).
- [x] 3.3 Ensure `repo_jur_pdf_hash` and `repo_jur_pdf_hashes` cardinality and mutual exclusivity are completely enforced.

## 4. Test Alignment and Real-Corpus Scenarios

- [x] 4.1 Update all unit and integration tests in `tests/test_legal_producer.py`, `tests/test_legal_producer_cli.py`, and `tests/test_legal_semantic_review.py` to use canonical fields instead of legacy fields.
- [x] 4.2 Verify Stage 9 search and filter compatibility: prove that existing Stage 9 index and configuration code (`src/pipeline_juridico/retrieval/index.py` and `src/pipeline_juridico/config.py`) already uses the canonical `repo_jur_*` keys and requires no modifications.
- [x] 4.3 Implement two real-corpus testing strategies:
  - **CI-Safe Golden-File Tests:** Create unit/integration tests that load pre-converted `tests/test_conformance/golden/L10.406_CC_2002.md` and `L10.406_CC_2002.json` assets as `Phase1Artifacts`, verifying that the correct canonical fields (including `repo_jur_lei_tipo: "ordinaria"`) are successfully populated. This must be 100% fast, deterministic, and CI-safe without requiring Gemini API or local raw PDF files.
  - **Opt-In Real-Corpus Acceptance Tests:** Create integration tests using the actual `input/L10.406_CC_2002.pdf` file, decorated with `pytest.mark.skipif` checking for the file's absence.
- [x] 4.4 Validate exit codes across the CLI command surfaces to ensure complete alignment with established conventions: `0` (success), `1` (input), `2` (unexpected), `3` (configuration/contract), `5` (blocked).
- [x] 4.5 Validate the entire OpenSpec repository using `openspec validate --all --strict`.
