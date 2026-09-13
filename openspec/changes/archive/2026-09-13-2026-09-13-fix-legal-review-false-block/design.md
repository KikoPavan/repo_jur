## Context

Real-corpus reproduction: `Jurisprudencia_Teses_D.P.C._ed.171.md` is a "Jurisprudência em Teses" compilation. Its `ProducerContext.type` is explicitly `TemaJuridico` (operator intent). The body cites `Lei n. 11.636/2007`, `Lei n. 7.347/1985`, `Lei n. 4.717/1965`, `Lei n. 8.429/92`, and many internal `Tema n. NNN` cross-references (e.g. `Tema n. 434`, `Tema n. 988`, `Tema n. 1000`, `Tema n. 1089`, `TEMA 1.267`, etc.) as part of the theses' legal grounding — none of these establish the document's own Legislacao identity or its own Tema identity.

Two independent, unrelated bugs currently make Stage 7 misbehave on this input:

1. `LegalSemanticReviewEngine.review()` scans the *entire* Markdown for `LEI|DECRETO|MEDIDA PROVISÓRIA ... Nº` and forces `REVIEW_REQUIRED` if `repo_jur_lei_numero`/`repo_jur_lei_ano` are missing — with no awareness of `ProducerContext.type`, because the Review engine intentionally never receives it (see `legal-knowledge` spec: "Legal Semantic Review is bounded-context-specific and engine-neutral"). This causes any citation of a numbered law, in *any* concept type, to falsely block publication.
2. `_deterministic_extract()`'s `repo_jur_tema_numero` logic takes the first `Tema ... N` regex match found anywhere in the document, with no distinction between "this document's own Tema identity" and "an internal citation to a different Tema". In a thematic compilation, dozens of theses exist, each citing its own Tema number; today the code would silently pick whichever comes first in reading order.

## Goals / Non-Goals

**Goals**
- Preserve `type` as pure explicit operator intent (already established, must not regress).
- Move Legislacao-specific numbered-act completeness enforcement to the layer that actually knows the explicit type: the Legal Producer (`ProducerContext`/`validate_candidate`), not the generic Legal Semantic Review.
- Make `repo_jur_tema_numero` extraction ambiguity-safe: a document must present unambiguous, exactly-one-candidate structural evidence before this field is extracted as positional identity; otherwise the field is safely absent (never REVIEW_REQUIRED, never a guess — `TemaJuridico` already treats absence of `repo_jur_tema_numero` as valid for non-numbered/doctrinal themes).
- Keep this a **detection-only, deterministic, regex/structural** fix — no LLM, no content-based type classification.

**Non-Goals**
- Not building a general normative-citation extractor/index (e.g. `repo_jur_normas_referenciadas` already exists for Código Civil references and is untouched by this change).
- Not attempting to disambiguate which of several cited Tema numbers is "most relevant" — ambiguity always means "extract nothing", never a heuristic pick.
- Not changing Phase 1 Markdown/report content, and not changing any other concept type's mandatory-field rules.

## Decisions

### Decision 1 — Relocate Legislacao numbered-act completeness check
- **What:** Delete the generic `has_numbered_act_pattern` REVIEW_REQUIRED branch from `LegalSemanticReviewEngine.review()`. Add an equivalent check inside `legal_producer.py::validate_candidate`, executed only when `candidate.type is LegalConceptType.Legislacao`. The check inspects `candidate.body` (the same literal Phase 1 Markdown, now type-scoped by the caller) for the numbered-act pattern; if found and `repo_jur_lei_numero`/`repo_jur_lei_ano` are absent from `candidate.frontmatter`, raise `LegalProducerBlockedError(reason="review_required")`.
- **Why:** The Producer is the only Stage 7 component that receives `ProducerContext` (hence the explicit `type`). The Legal Semantic Review must remain engine-neutral and must not infer a document's category from content, per the "No silent semantic or LLM classification" requirement, and it must not become the enforcement point for a type-specific rule.
- **Alternatives considered:** Passing `ProducerContext.type` into `LegalSemanticReviewEngine.review()` — rejected, because it would break the established engine-neutral, bounded-context-specific contract for the Review seam (`### Requirement: Legal Semantic Review is bounded-context-specific and engine-neutral`) and open the door to progressively coupling Review to type-specific logic for every concept type.
- The detection regex itself (the literal pattern used to recognize a numbered act) is extracted as a small shared helper function in `legal_semantic_review.py` (e.g. `_has_numbered_act_pattern(markdown: str) -> bool`) so both the Producer's new Legislacao-only check and any future review rule reuse one definition; the regex logic is not duplicated or reinterpreted.

### Decision 2 — Ambiguity-safe `repo_jur_tema_numero` extraction
- **What:** In `_deterministic_extract()`, replace "first match wins" with "collect all distinct Tema numbers cited across all pages; extract `repo_jur_tema_numero` (and the paired `repo_jur_tribunal` field, as today) only if exactly one distinct number was found across the whole document; otherwise omit the field entirely (no exception raised, no REVIEW_REQUIRED forced by extraction itself)."
- **Why:** A single-Tema source document (the typical case validated today, e.g. a court's official Tema decision PDF) still yields exactly one distinct citation and is unaffected. A thematic compilation citing many `Tema n. N` references as internal cross-references is the ambiguous case; silent selection of the first one is the exact "silent choice on ambiguity" pattern the spec's "Ambiguity routes to REVIEW_REQUIRED and never to silent correction" requirement forbids for *structural corrections* — for extraction, the safe analogue is **safe absence**, since `TemaJuridico`'s conditional-mandatory rule already treats missing `repo_jur_tema_numero` as valid when the document does not represent an official numbered theme (this is the existing rule in `validate_candidate`: `repo_jur_tema_numero` required only paired with `repo_jur_tribunal`, and both are optional for doctrinal/abstract `TemaJuridico`).
- **Alternatives considered:** Raising `REVIEW_REQUIRED` on ambiguity for the Tema field specifically — rejected as unnecessarily strict: `TemaJuridico` already supports omission of this pair of fields, so the correct behavior on ambiguity is the same as "this document is not itself pinned to one official numbered theme", not a hard block.
- Scope of "distinct number": string-compare the captured digit group after the existing normalization (the same `\d+` capture used today); no numeric equivalence heuristics (e.g. `1089` vs `1.089`) are added in this change, since the existing regex already strips separators before capture is unaffected. Confirm during implementation that the digit capture already excludes non-digit separators (the current regex `(\d+)` operates on the sanitized substring) — if `1.267` appears with a literal internal dot in some formats (`TEMA 1.267`), verify the existing capture group behavior and keep it unchanged unless a genuine defect is found; do not fix unrelated formatting bugs in this change.

## Risks / Trade-offs

- **Risk:** Moving the Legislacao completeness check to the Producer changes the failure surface slightly (which module raises the `review_required` reason) — mitigated because the CLI (`legal_producer_cli.py::_run_build`) already catches both `LegalSemanticReviewBlockedError` and `LegalProducerBlockedError` identically and records the same `producer.review_required` operational record; the operator-visible behavior (`review is required for this candidate`, exit code 5) is preserved for genuine Legislacao incompleteness.
- **Risk:** A document that is genuinely a numbered-act-formatted `Legislacao` PDF but happens not to trigger the pattern (e.g. no "Nº"/"N." literal near the act name) could now escape both old and new checks — this was equally true before; behavior for true Legislacao inputs is unchanged, only the layer moved.
- **Trade-off:** Ambiguous-Tema documents now silently omit `repo_jur_tema_numero` rather than blocking; a human reviewing the resulting concept candidate must notice the missing field if they expected one. This mirrors the existing, already-accepted behavior for doctrinal/abstract `TemaJuridico` concepts and is the deliberate outcome requested by the user (never silently choose the first number).

## Migration Plan

No data migration. No existing bundle concepts are affected (validated against synthetic fixtures and the reproduction real-corpus case only; no publication occurs as part of this change). Existing tests referencing the relocated Legislacao check are updated to assert the new call site (`validate_candidate`/`produce`) instead of `LegalSemanticReviewEngine.review()`.

## Open Questions

None — scope confirmed by the user's reproduction report and explicit acceptance criteria.
