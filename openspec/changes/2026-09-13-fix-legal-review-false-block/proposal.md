## Why

Real-corpus validation of Stage 7 (`uv run repo-jur producer build output/Jurisprudencia_Teses_D.P.C._ed.171.md logs/Jurisprudencia_Teses_D.P.C._ed.171.report.json --type TemaJuridico --evidence-resource "input/Jurisprudencia_Teses_D.P.C._ed.171.pdf" --json`) reproduces `Producer bloqueado: review is required for this candidate` for a document that is explicitly `TemaJuridico`, not `Legislacao`. The document only *cites* legislation (`Lei n. 11.636/2007`, `Lei n. 7.347/1985`, `Lei n. 4.717/1965`, `Lei n. 8.429/92`, etc.) as part of jurisprudential theses; it never claims to *be* a piece of legislation.

Root cause 1 — misplaced, type-blind validation: `LegalSemanticReviewEngine.review()` in `legal_semantic_review.py` scans the entire Markdown body for a numbered-act pattern (`LEI|DECRETO|MEDIDA PROVISÓRIA ... Nº`) regardless of the operator's declared `ProducerContext.type`, and forces `ReviewState.REVIEW_REQUIRED` whenever `repo_jur_lei_numero` or `repo_jur_lei_ano` were not extracted. Because the Legal Semantic Review is intentionally engine-neutral and does not receive `ProducerContext` (per the existing spec, "Legal Semantic Review is bounded-context-specific and engine-neutral"), it cannot know the operator's explicit `type` — so it currently guesses based on content, treating *any* legislative citation as if it were the document's own legal identity. This is exactly the content-derived-classification anti-pattern `AGENTS.md` and the `legal-knowledge` spec (`### Requirement: The concept type is explicit operator intent...`, `### Requirement: No silent semantic or LLM classification`) forbid: `type` must remain explicit operator intent, and Legislacao-specific mandatory-field enforcement must occur only when the context is explicitly `Legislacao` — where the Producer already knows `ProducerContext.type`.

Root cause 2 — unsafe positional-identity extraction: `_deterministic_extract()` searches for the first `Tema\s*(?:Repetitivo|de Repercussão Geral)?\s*(?:n[º°.]?)?\s*(\d+)` match anywhere in the document and unconditionally treats it as `repo_jur_tema_numero`. In a thematic compilation document (such as "Jurisprudência em Teses"), dozens of distinct `Tema n. NNN` citations exist as *references to other theses*, not as the document's own identity. Silently picking the first citation risks assigning the wrong Tema number as positional identity for `TemaJuridico` concepts — a direct violation of "Ambiguity routes to REVIEW_REQUIRED and never to silent correction" and of the duplication/identity-precision principles already established for this project.

## What Changes

- Remove the type-blind "numbered act pattern found anywhere in the document" REVIEW_REQUIRED enforcement from `LegalSemanticReviewEngine.review()`. The Legal Semantic Review remains engine-neutral, structural-only, and does not force REVIEW_REQUIRED based on generic legislative citations.
- Re-implement the equivalent Legislacao-specific mandatory-field enforcement inside the Legal Producer (`legal_producer.py::validate_candidate`), gated strictly on `candidate.type is LegalConceptType.Legislacao`: when the candidate body contains a numbered-act citation pattern and neither `repo_jur_lei_numero` nor `repo_jur_lei_ano` was extracted, the Producer blocks with `LegalProducerBlockedError(reason="review_required")`, exactly as before, but only for candidates whose explicit `type` is `Legislacao`.
- Add a reusable, side-effect-free structural detector (e.g. `has_numbered_act_pattern`) in `legal_semantic_review.py` that both the (unchanged) extraction logic and the new Producer-side Legislacao check can share, so the detection regex is defined once.
- Fix `_deterministic_extract()`'s `repo_jur_tema_numero` extraction to require unambiguous structural evidence: collect every distinct `Tema ... N` number cited in the document; if exactly one distinct number is cited, extract it as before (preserves single-Tema documents); if two or more distinct numbers are cited, do not extract `repo_jur_tema_numero` at all (safe absence — `TemaJuridico` already tolerates the field's absence for doctrinal/abstract themes per the existing profile rule).
- Add mandatory regression tests (synthetic fixtures) covering: (1) `TemaJuridico` citing `Lei n. 11.636/2007` builds without REVIEW_REQUIRED; (2) `Jurisprudencia` and `PrecedenteVinculante` citing legislation likewise build without REVIEW_REQUIRED; (3) `Legislacao` explicitly selected with an incomplete numbered act still blocks with REVIEW_REQUIRED; (4) a document citing multiple distinct `Tema n. N` numbers does not silently assign `repo_jur_tema_numero`; (5) a document unambiguously about a single Tema still extracts `repo_jur_tema_numero` deterministically.
- Re-run the real reproduction command (`producer build` against `Jurisprudencia_Teses_D.P.C._ed.171.md`) as validation evidence only — no new OCR, no publication to bundle.

## Out of Scope

- No change to Phase 1 conversion, the Markdown body, or the technical report.
- No LLM-based or inferred classification of any kind.
- No change to `router.py` page-routing semantics or the Domain Router.
- No publication to `bundle/` for the real-corpus document during this change.
- No `git push`, `openspec archive`, or new OCR execution.

## Capabilities

### Modified Capabilities
- `legal-knowledge`: Legislacao-specific numbered-act completeness enforcement moves from the type-blind Legal Semantic Review into the Legal Producer's type-gated validation; `repo_jur_tema_numero` extraction becomes ambiguity-safe (single unambiguous citation only).

## Impact

- **Affected modules:** `src/pipeline_juridico/legal_semantic_review.py`, `src/pipeline_juridico/legal_producer.py`.
- **Affected tests:** `tests/test_legal_semantic_review.py`, `tests/test_legal_producer.py`, `tests/test_legal_producer_cli.py` (as needed for the relocated blocking behavior).
- No new external dependencies. Zero-write guarantees, engine neutrality, and domain isolation are strictly preserved.
