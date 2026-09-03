## Context

The Stage 7 Legal Knowledge Pipeline currently utilizes legacy, non-canonical frontmatter metadata keys in code (e.g. `jurisdicao`, `ambito`, `tipo_norma` in `Legislacao`; `ementa`, `tema`, `subtema` in `TemaJuridico`; and `tese_fixada` in `PrecedenteVinculante`). These keys do not align with the FROZEN Legal OKF Profile v1.3. A real-corpus acceptance test with `input/L10.406_CC_2002.pdf` revealed that the Legal Producer emits only structural/provenance metadata, missing substantive Legal Knowledge metadata altogether.

We must correct the contract alignment, specify exactly how every canonical field is populated and validated, reconcile Stage 9 retrieval filters, remove the legacy keys, and establish real-corpus acceptance scenarios to ensure semantic completeness without introducing silent LLM inference.

## Goals / Non-Goals

**Goals:**
- Formulate a precise, corrective metadata plan and spec delta aligned with FROZEN Legal OKF Profile v1.3.
- Map out every canonical field with its data type, requirement status, ownership, and allowed source of value.
- Explicitly prohibit silent LLM inference and define clear failure/blocked behaviors routing to `REVIEW_REQUIRED`.
- Specify page/evidence provenance rules and safe merge policies for shared/human-owned fields.
- Reconcile the Stage 9 retrieval filters to map directly onto stripped-prefix versions of the canonical fields.
- Provide a robust test plan including a real-corpus acceptance scenario for `L10.406_CC_2002.pdf`.
- Maintain all existing bounded-context isolation, zero-write, and idempotency guarantees.

**Non-Goals:**
- Modify production code or execute implementation in this planning phase.
- Modify or redesign Judicial Process (Stage 8) or unrelated stages.
- Introduce heavy PDF binaries as git fixtures.

## Decisions

### 1. Canonical Field Matrix and Key Mapping
We define the exact canonical fields, data types, requirement status, component ownership, and allowed sources for each concept type under the FROZEN Legal OKF Profile v1.3:

| Concept Type | Canonical YAML Key | Data Type | Status | Population Component | Allowed Value Source |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **All Types** | `type` | String | Mandatory | Producer-Owned | Explicit operator context (`ProducerContext.type`) / workflow intent |
| | `title` | String | Recommended | Shared | Deterministic Phase 1 extraction or human curation (not guaranteed deterministic initial population) |
| | `description` | String | Recommended | Shared | Deterministic Phase 1 extraction or human curation (optional with no initial automation required) |
| | `resource` | String (URI) | Recommended | Producer-Owned | Explicit operator context (`ProducerContext.evidence_resource`) / workflow intent |
| | `tags` | List of Strings | Recommended | Shared | Deterministic extraction or human curation |
| | `sources` | List of Objects | Conditional | Producer-Owned | Deterministic source/provenance data |
| | `generated` | Object | Mandatory | Producer-Owned | Automatically injected by Producer |
| | `verified` | List of Objects | Conditional | Human-Owned | Human verification / independent audit only; prohibited from auto-population |
| | `status` | String | Optional | Human-Owned | Human curation only; prohibited from auto-population (implicit default `stable` on absence) |
| | `stale_after` | Date String | Optional | Shared | Human curation / statutory expiration rules |
| | `repo_jur_pdf_hash` | String | Conditional | Producer-Owned | Deterministic SHA-256 of source file (1 PDF only) |
| | `repo_jur_pdf_hashes`| Map | Conditional | Producer-Owned | Deterministic `id` -> SHA-256 mapping (2+ PDFs only) |
| | `repo_jur_verification_history`| List of Objects| Conditional| Producer-Owned | Automatically archived `verified` events on material change |
| **Legislacao** | `repo_jur_lei_numero` | String | Conditional Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (mandatory for numbered acts) |
| | `repo_jur_lei_ano` | Integer | Conditional Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (mandatory for numbered acts) |
| | `repo_jur_lei_esfera` | String | Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (`federal`, `estadual`, `distrital`, `municipal`) |
| | `repo_jur_lei_tipo` | String | Recommended | Shared | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review or human curation (`constituicao`, `complementar`, `ordinaria`, `decreto`, etc.) |
| **Jurisprudencia**| `repo_jur_processo_numero`| String | Mandatory | Producer-Owned | Deterministic extraction by Legal Semantic Review (CNJ pattern preferred; also accepts STJ/STF appellate case/register identifiers like REsp/AREsp/AgInt) |
| | `repo_jur_tribunal` | String | Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (Upper case acronym, e.g., `STF`, `STJ`) |
| | `repo_jur_relator` | String | Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (magistrate name) |
| | `repo_jur_data_julgamento`| Date String | Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (YYYY-MM-DD) |
| | `repo_jur_ramo_direito` | String | Recommended | Shared | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review or human curation |
| **TemaJuridico** | `repo_jur_tema_numero` | String | Conditional Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (mandatory for official numbered themes) |
| | `repo_jur_tribunal` | String | Conditional Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review (mandatory for official court themes) |
| **PrecedenteVinculante**| `repo_jur_precedente_numero`| String | Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review |
| | `repo_jur_precedente_status`| String | Mandatory | Shared | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review or human curation (`ativo`, `cancelado`, `revisado`) |
| | `repo_jur_tribunal` | String | Mandatory | Producer-Owned | Deterministic extraction from Phase 1 Markdown by Legal Semantic Review |

### 2. Elimination of Legacy/Non-Canonical Fields
The following legacy, un-prefixed, or inappropriate fields identified during the audit are completely removed from `PROFILE_FIELDS` and explicitly rejected during validation:
- `jurisdicao`, `ambito`, `tipo_norma` (formerly used under `Legislacao`)
- `ementa`, `tema`, `subtema` (formerly used under `TemaJuridico`)
- `tese_fixada` (formerly used under `PrecedenteVinculante`)
- `tribunal`, `relator` (un-prefixed variants formerly used under `Jurisprudencia` / `PrecedenteVinculante`)

*Rationale:* Prevents directory/concept metadata pollution, satisfies the strictness of Legal OKF Profile v1.3, and prevents conflicting representations.

### 3. Extraction Architecture and Cognitive/LLM Prohibition
- **No Silent LLM Inference:** Cognitive or LLM inference is strictly prohibited from executing automatically in Stage 7 for the purpose of extraction, classification, or metadata population. All automatic extraction MUST be purely deterministic.
- **Deterministic Extraction Owner:** The **Legal Semantic Review** is the sole component authorized to perform parsing and deterministic extraction of metadata fields, producing `ExtractedField` candidates inside `ReviewResult`. The **Legal Producer** is purely a publishing/validation agent and is prohibited from parsing legal text or extracting metadata itself. It reads the fields strictly from the `ReviewResult.extracted_fields` list.
- **Allowed Source Rules for Extraction:**
  - `repo_jur_lei_numero`, `repo_jur_lei_ano`, `repo_jur_lei_esfera`, `repo_jur_lei_tipo`: Extracted via regex and structural rule matching on Phase 1 Markdown headings (e.g., `# LEI Nº 10.406, DE 10 DE JANEIRO DE 2002`).
  - `repo_jur_processo_numero`: Extracted on the Phase 1 Markdown. While the CNJ pattern (`\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b`) is preferentially preferred, STJ/STF appellate case identifiers (such as REsp, AREsp, AgInt numbers) and register numbers (such as `YYYY/NNNNNNN-N`) are also valid values and must be extracted when no CNJ-formatted number is available. This guarantees that valid jurisprudence assets with no CNJ-formatted number (such as golden assets `REsp_1704551-SP` and `AINTARESP_1462304-PA`) are executable and successfully extracted without failing. No separate field for court-class identifiers exists in the FROZEN profile, and none is invented.
  - `repo_jur_tribunal`: Extracted from known patterns in headings, footers, or the technical report metadata.
  - `repo_jur_relator`: Extracted from signature/relator structures matching `Relator[a]?:\s*([A-Z\s]+)`.
  - `repo_jur_data_julgamento`: Extracted from date patterns near the conclusion or signatures matching YYYY-MM-DD or standard Portuguese textual dates.
- **Legislacao Type Normalization:** The expected value for `repo_jur_lei_tipo` of Lei 10.406/2002 is `"ordinaria"` (since it is an ordinary law, and `"ordinaria"` is part of the FROZEN suggested values; general value `"lei"` is not in the FROZEN suggested vocabulary).
- **Required vs Conditional Fields:** `repo_jur_lei_numero` and `repo_jur_lei_ano` are strictly conditional mandatory, meaning they are mandatory only for numbered acts (like Lei 10.406/2002) and should be omitted otherwise (e.g., for non-numbered constitutional acts).
- **Failure / Blocked Behavior:** If a `Mandatory` or `Conditional Mandatory` field cannot be extracted deterministic-first by the Semantic Review, the run MUST be aborted with a deterministic exit code (5 / `blocked`). Since `ProducerContext` strictly permits only `type` and `evidence_resource`, no operator-supplied canonical fields are allowed. The Producer run MUST be aborted, publishing NO concept document, and reporting a `REVIEW_REQUIRED` state in the observability record so that a human can curation-populate it.
- **Generated Object Schema (`generated.at`):** The `generated.at` field is recommended in the FROZEN profile and its allowed type is strictly a **Datetime String (ISO 8601)** indicating the last meaningful change of content. The `evidence:...` URI syntax is NOT explicitly authorized under the FROZEN profile. Thus, all `evidence:...` formatting is completely removed from expected YAML outputs, schemas, and planning. If used, `generated.at` must represent a valid ISO 8601 Datetime String, or be omitted from the minimum expected output YAML entirely.
- **Title and Description Automation Expectations:** Under the FROZEN profile, both `title` and `description` are recommended but not mandatory.
  - `title` is not guaranteed deterministic initial population, but merely permitted/recommended.
  - `description` is optional with no initial automation required (the method of production is not prescribed by the profile).
  - Consequently, neither `title` nor `description` is required to appear in the real-corpus acceptance assertion (for Lei 10.406/2002 or other concepts), and they are completely removed from the normative minimum expected-output example for Lei 10.406/2002 to avoid introducing unsupported automation constraints.

### 4. Page/Evidence Provenance for Extracted Metadata
- **Transient Evidence Provenance:** Physical page references (`page_refs` on `ExtractedField` / `LegalPatch` dataclasses) are transient Semantic Review evidence. They are **persisted only in the operational records** (the technical execution reports/observability JSON logs) and are **strictly prohibited from being written as fields in the canonical YAML frontmatter** of concept documents inside `/bundle/`. This satisfies the strictness of Legal OKF Profile v1.3 and prevents introducing unauthorized canonical YAML structures.

### 5. Authorized Base and Shared Field Merge Rules
- **Authorized Base Fields:** The canonical concept frontmatter contains exactly and only the authorized base/shared fields from the FROZEN `legal-okf-profile-v1.3`: `type` (Producer-Owned), `title` (Shared), `description` (Shared), `resource` (Producer-Owned), `tags` (Shared), `sources` (Producer-Owned), `generated` (Producer-Owned), `verified` (Human-Owned), `status` (Human-Owned), and `stale_after` (Shared). Non-profile fields like `aliases` and `related` are completely omitted from the authorized base field matrix.
- **Initial Population:** The Producer can propose a default `title` (e.g. from the base filename or the primary heading of the Phase 1 markdown) and an empty list for `tags` when first creating the concept.
- **Status Ownership:** The `status` field is strictly Human-Owned. The Producer is **strictly prohibited from automatically populating or injecting defaults** (such as `status: stable` or `status: draft`) during creation or regeneration. If `status` has not been curation-populated by a human, the field MUST be completely omitted from the YAML frontmatter. According to OKF v0.2, consumers interpret the absence of the key as implicitly equivalent to `status: stable`.
- **Safe Regeneration / Merge:** When regenerating an existing concept, the Producer must load the existing file, parse the frontmatter, and completely preserve any human-customized values for `title`, `description`, `tags`, `stale_after`, `status`, and `verified`. The Producer MUST NOT overwrite them with deterministic defaults.

### 6. Legacy Key Rejection and Upgrade Merges
- **Universal Rejection on Candidates:** During final candidate validation (`validate_candidate`), any legacy, un-prefixed, or inappropriate fields (such as `jurisdicao`, `ambito`, `tipo_norma`, `ementa`, `tema`, `subtema`, `tese_fixada`, `tribunal`, `relator`) are rejected universally anywhere in the frontmatter, blocking publication.
- **Safe Upgrade on Merging Existing Concepts:** To ensure no conflict with the safe regeneration of existing human-curated concepts, when loading an existing concept document, the Producer **automatically filters out and strips** any legacy/deprecated keys from the parsed frontmatter. The resulting merged candidate is clean of legacy keys and passes validation successfully, upgrading the file seamlessly.

### 7. Reconciling Stage 9 Retrieval Filter Keys
The Stage 9 Retrieval Contract maps its public filter keys directly to the stripped-prefix versions of the canonical fields. Our alignment guarantees zero drift:
- `lei_numero` maps to `repo_jur_lei_numero`
- `lei_ano` maps to `repo_jur_lei_ano`
- `lei_esfera` maps to `repo_jur_lei_esfera`
- `lei_tipo` maps to `repo_jur_lei_tipo`
- `processo_numero` maps to `repo_jur_processo_numero`
- `tribunal` maps to `repo_jur_tribunal`
- `relator` maps to `repo_jur_relator`
- `data_julgamento` maps to `repo_jur_data_julgamento`
- `ramo_direito` maps to `repo_jur_ramo_direito`
- `precedente_numero` maps to `repo_jur_precedente_numero`
- `precedente_status` maps to `repo_jur_precedente_status`
- `tema_numero` maps to `repo_jur_tema_numero`

**Stage 9 Verification:** The existing Stage 9 index and configuration code (`src/pipeline_juridico/retrieval/index.py` and `src/pipeline_juridico/config.py`) already uses the canonical `repo_jur_*` keys and provides the exact mappings for stripped filters. No code change is necessary for Stage 9.

### 8. Testing Strategy
- **CI-Safe Golden-File Testing:** To ensure the test suite is deterministic, fast, and does not depend on gitignored heavy PDF binaries or external OCR API calls, unit and integration tests reuse the pre-converted golden Markdown and technical JSON report assets under `tests/test_conformance/golden/` (e.g. `L10.406_CC_2002.md` and `L10.406_CC_2002.json`) as `Phase1Artifacts`.
- **Opt-In Real-Corpus Acceptance Testing:** Local real-corpus acceptance tests running the actual PDF conversion are decorated with `pytest.mark.skipif` checking for the absence of `input/L10.406_CC_2002.pdf`, ensuring they only run when the raw PDF is locally present.
- **Exit Codes:** The Producer CLI commands build, validate, and publish follow existing authoritative conventions: `0` (success), `1` (input error), `2` (unexpected error), `3` (configuration/contract error), and `5` (blocked / review required).

### 9. Implementation Choice
- **Deterministic-only extraction:** For the current implementation, extraction is restricted to strictly deterministic logic as an Implementation Choice of this version, without transforming this choice into a frozen global architectural rule for future versions.
