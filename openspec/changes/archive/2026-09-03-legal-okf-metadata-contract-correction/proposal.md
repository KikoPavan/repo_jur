## Why

A real-corpus acceptance test with input/L10.406_CC_2002.pdf demonstrated that the Legal Producer is currently emitting only structural/provenance metadata and no substantive Legal Knowledge metadata. An authoritative audit (t_1b2fe501) identified a mismatch between the legacy profile fields in code and the FROZEN Legal OKF Profile v1.3, resulting in non-canonical metadata fields like "jurisdicao", "ambito", "tipo_norma", "ementa", "tema", "subtema" and "tese_fixada" being defined while official, canonical keys like "repo_jur_lei_numero", "repo_jur_processo_numero", and "repo_jur_tribunal" are absent, and existing tests validate technical boundaries but not semantic completeness.

## What Changes

- Align `PROFILE_FIELDS` in `legal_producer.py` with the FROZEN Legal OKF Profile v1.3, removing legacy non-canonical fields and introducing official canonical fields for all four concept types (`Legislacao`, `Jurisprudencia`, `TemaJuridico`, `PrecedenteVinculante`).
- Reject legacy frontmatter keys where required: reject `jurisdicao`, `ambito`, `tipo_norma` (for Legislacao), `ementa`, `tema`, `subtema` (for TemaJuridico), `tese_fixada` (for PrecedenteVinculante), and un-prefixed fields `tribunal` and `relator`.
- Reconcile Stage 9 retrieval filter keys with the canonical metadata profile. Ensure the Stage 9 public search filters map deterministically to the stripped-prefix version of the canonical fields.
- Add deterministic extraction architecture definitions: specify exact allowed sources (strictly deterministic extraction from Phase 1 Markdown headers/content), component ownership, and safe initial-population/regeneration behavior.
- Prohibit silent LLM/cognitive inference for extraction or classification, and define failure/blocked behavior to route to `REVIEW_REQUIRED` when mandatory fields cannot be extracted or verified without inference.
- Define page/evidence provenance requirements for extracted metadata (e.g. mapping of extracted fields to their respective physical pages in the source PDF).
- Establish real-corpus acceptance scenarios using `L10.406_CC_2002.pdf` to prove semantic completeness without checking heavy PDF files into Git as canonical fixtures.

## Capabilities

### New Capabilities
None.

### Modified Capabilities
- `legal-knowledge`: Align domain-specific frontmatter fields with Legal OKF Profile v1.3. Define deterministic extraction and validation rules for canonical keys (`repo_jur_lei_numero`, `repo_jur_lei_ano`, `repo_jur_lei_esfera`, `repo_jur_lei_tipo`, `repo_jur_processo_numero`, `repo_jur_tribunal`, `repo_jur_relator`, `repo_jur_data_julgamento`, `repo_jur_ramo_direito`, `repo_jur_tema_numero`, `repo_jur_precedente_numero`, `repo_jur_precedente_status`).
- `legal-knowledge-retrieval`: Maintain the retrieval filter keys aligned with the newly corrected canonical metadata profile.

## Impact

- **Affected modules:** `src/pipeline_juridico/legal_producer.py` (specifically `PROFILE_FIELDS`), `src/pipeline_juridico/legal_producer_cli.py`, `src/pipeline_juridico/legal_semantic_review.py`.
- **Affected tests:** `tests/test_legal_producer.py`, `tests/test_legal_producer_cli.py`, `tests/test_legal_semantic_review.py`.
- No new external dependencies. Zero-write guarantees and domain isolation are strictly preserved.
