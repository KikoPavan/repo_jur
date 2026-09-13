## 1. Regression fixtures — false-block on legislation citations

- [x] 1.1 Add a synthetic fixture/test in `tests/test_legal_producer.py` (or `tests/test_legal_producer_cli.py` as appropriate) proving a `TemaJuridico` candidate whose body cites `Lei n. 11.636/2007` (and satisfies TemaJuridico's own field rules, or intentionally omits the conditional-mandatory pair to prove it's not blocked by Legislacao logic) builds successfully — i.e. `produce()`/CLI build does not raise `review_required` due to the legislative citation.
- [x] 1.2 Add equivalent regressions for `Jurisprudencia` and `PrecedenteVinculante` candidates whose bodies cite numbered legislation (e.g. `Lei n. 7.347/1985`, `Lei n. 8.429/92`), proving they build successfully when their own type-specific mandatory fields are satisfied.
- [x] 1.3 Add/keep a regression proving `Legislacao` explicitly selected with an incomplete numbered act (e.g. `LEI COMPLEMENTAR Nº 123` with no year) still blocks with `review_required` — relocate/update `test_semantic_review_incomplete_numbered_act_review_required` (or add an equivalent Producer-level test) to assert the check now happens at the Producer/`validate_candidate` layer while preserving the same operator-visible outcome (exit code 5, `review_required`).

## 2. Regression fixtures — ambiguous Tema identity

- [x] 2.1 Add a synthetic fixture/test proving a document citing two or more distinct `Tema n. N` numbers (e.g. `Tema n. 434`, `Tema n. 988`, `Tema n. 1089`) does not populate `repo_jur_tema_numero` in `_deterministic_extract()` output, and that a `TemaJuridico` candidate built from it does not silently carry any one of those numbers as identity.
- [x] 2.2 Add/keep a regression proving a document with exactly one distinct `Tema n. N` citation still extracts `repo_jur_tema_numero` deterministically (preserve existing single-Tema behavior, e.g. via the existing `TemaJuridico` fixture in `tests/test_legal_producer.py`).

## 3. Implementation — relocate Legislacao numbered-act check

- [x] 3.1 In `legal_semantic_review.py`, extract the numbered-act detection regex into a small shared, side-effect-free helper (e.g. `_has_numbered_act_pattern(markdown: str) -> bool`), and remove the `REVIEW_REQUIRED`-forcing branch from `LegalSemanticReviewEngine.review()` that currently sets `state = ReviewState.REVIEW_REQUIRED` when `has_numbered_act_pattern` is true and `repo_jur_lei_numero`/`repo_jur_lei_ano` are missing from `extracted_names`. Leave the rest of `_deterministic_extract()`'s Legislacao field extraction (`repo_jur_lei_tipo/numero/ano/esfera`) unchanged.
- [x] 3.2 In `legal_producer.py::validate_candidate`, add a Legislacao-only branch (inside `if candidate.type is LegalConceptType.Legislacao:`) that calls the shared helper against `candidate.body`; if a numbered-act pattern is detected and `repo_jur_lei_numero` or `repo_jur_lei_ano` is absent from `candidate.frontmatter`, raise `LegalProducerBlockedError("missing conditional mandatory field repo_jur_lei_numero or repo_jur_lei_ano", reason="review_required")` (reuse the existing message/reason for operator-visible continuity).
- [x] 3.3 Confirm `legal_producer_cli.py::_run_build` still records `producer.review_required` correctly for this relocated check (it already catches both `LegalSemanticReviewBlockedError` and `LegalProducerBlockedError` identically) — update only if a gap is found. (Verified: no gap found; no CLI change needed.)

## 4. Implementation — ambiguity-safe Tema extraction

- [x] 4.1 In `_deterministic_extract()`, change the `Tema` extraction loop to collect every distinct captured number (as a set, across all pages) instead of stopping at the first match. If the set has exactly one element, extract `repo_jur_tema_numero` with that value and the page reference of its first occurrence (preserving current `page_refs`/`repo_jur_tribunal` pairing behavior). If the set has two or more elements, do not append `repo_jur_tema_numero` (or the associated tribunal duplication for that field) to `extracted`.
- [x] 4.2 Verify no other extracted field or behavior (e.g. `repo_jur_tribunal` extraction used elsewhere) regresses when the Tema pattern matches multiple times.

## 5. Verification

- [x] 5.1 Run targeted tests: `uv run pytest -q tests/test_legal_semantic_review.py tests/test_legal_producer.py tests/test_legal_producer_cli.py tests/test_conformance/test_metadata_contract.py`. Result: 94 passed, 1 skipped.
- [x] 5.2 Run `uv run pytest -q` (full suite) and compare the pass/fail/skip/warning counts against the pre-existing baseline (documented separately by the orchestrator before implementation) — any change in counts beyond the newly added regression tests must be justified. Result: 1044 passed, 29 failed, 1 skipped, 2 warnings, 4 errors — same 33 pre-existing failures/errors (missing gitignored raw PDF fixtures), +6 net new passing tests from the regressions added in sections 1-2.
- [x] 5.3 Run `uv run repo-jur test conformance` (or the equivalent conformance marker/suite invocation) and confirm no regression. Result: same pre-existing 4 errors (missing raw PDF fixtures), unrelated to this change.
- [x] 5.4 Run markers for `regression`/`conformance` if such pytest markers exist in this project; otherwise confirm via targeted file selection above. Result: `-m conformance` → 10 passed; `-m regression` → 4 errors, same pre-existing missing-fixture cause.
- [x] 5.5 Run `openspec validate --all --strict` and `openspec validate 2026-09-13-fix-legal-review-false-block --strict`. Result: 13/13 passed including this change.
- [x] 5.6 Run `git diff --check` to catch trailing whitespace / merge artifacts. Result: clean, no output.
- [x] 5.7 Re-run the exact real reproduction command against `Jurisprudencia_Teses_D.P.C._ed.171.md` / its report JSON with `--type TemaJuridico --evidence-resource input/Jurisprudencia_Teses_D.P.C._ed.171.pdf --json` and confirm the Producer no longer blocks with `review is required for this candidate`; inspect exactly which fields would be produced. Do not run `producer publish` and do not write to `bundle/`. Result: exit code 0, candidate produced with `type: TemaJuridico`, `repo_jur_tribunal: STJ`; `repo_jur_tema_numero` correctly absent (multiple distinct Tema citations). No bundle write occurred (build only writes the operational state record).

## 6. Orchestrator-only follow-up (not part of Codex's implementation scope)

- [ ] 6.1 Claude reviews the full diff, independently re-runs all verification commands, and confirms the Legislacao true-positive block (Requirement scenario "Legislacao with an incomplete numbered act still blocks") still functions correctly.
- [ ] 6.2 Claude prepares the final report (root cause, before/after, test counts, reproduction result, residual risks, `git status --short`, READY/NOT READY decision) for human review. No commit, archive, or push without explicit human authorization.
