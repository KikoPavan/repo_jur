## Why

Real-corpus validation of Stage 7 exposed an architectural gap, not a bug in one rule. Running:

`uv run repo-jur producer build output/Jurisprudencia_Teses_D.P.C._ed.171.md logs/Jurisprudencia_Teses_D.P.C._ed.171.report.json --type TemaJuridico --evidence-resource "input/Jurisprudencia_Teses_D.P.C._ed.171.pdf" --json`

returns exit 0 and renders exactly **one** `TemaJuridico` candidate whose body is the entire 16-edition "Jurisprudência em Teses" bulletin (Edições 171, 172, 173, 182, 183, 189, 190, 191, 192, 255, 258, 272, 273, 276, 277, 278). That is semantically wrong: the PDF is a compilation of 16 independent legal units, each with its own title, publication date, page range, and set of theses. `input/STJ - Precedentes Qualificados.pdf` has the same shape for `PrecedenteVinculante` (10 distinct "Tema Repetitivo" records).

Root cause: every Stage 7 component — `Phase1Artifacts`, `ProducerContext`, `_base_candidate()`, `resolve_concept_path()`, the `producer build` CLI — assumes **1 Phase 1 artifact → 1 concept candidate**. There is no concept of a "segment" or "unit" between the raw Phase 1 Markdown (the whole PDF's literal conversion) and the rendered `ConceptCandidate`. `_base_candidate()` always copies `artifacts.markdown` verbatim into `candidate.body`, so any multi-unit source is published — or would be published — as a single oversized, semantically incoherent concept. The `build` CLI has no way to express "N candidates from one source", so the smallest possible fix (silently building one candidate per PDF) is precisely what already happened and is exactly the bug being reported.

This is a real Stage 7 boundary problem, not a regex/extraction defect: it must be fixed by introducing a new, strictly upstream, deterministic **segmentation** capability, not by teaching the Legal Semantic Review or the Producer to guess document type/boundaries from content.

## What Changes

- Introduce a new, source-inspectable, engine-neutral **Legal Source Segmentation** capability (new module `legal_source_segmentation.py`) that sits between Phase 1 artifacts and the Legal Producer. It is a pure function of the literal Phase 1 Markdown: `segment(markdown) -> SegmentationResult`. It never reads `ProducerContext`/`type`, never invokes an LLM, and never mutates Phase 1 artifacts.
- The segmentation result is one of three deterministic outcomes:
  - `SINGLE` — no unambiguous internal boundary found; the whole document is one segment (today's behavior, preserved byte-for-byte).
  - `SEGMENTS` — two or more unambiguous structural boundaries found; the document is split into N ordered segments, each carrying its own title, contiguous body slice (including its own `[[Pág. N]]` markers, unmodified), and page range.
  - `AMBIGUOUS` — structural signals exist but do not meet the unambiguity bar (e.g., a partial/inconsistent header sequence); segmentation stops, no split is attempted, and Stage 7 requires human review before any concept is built for the affected units.
- Boundary detection is driven by a small, versioned **Segmentation Rule Registry** (same provenance discipline as the existing `LegalReviewRule` registry: rule id, version, specification source, validation-logic version). A rule declares a structural anchor pattern that must appear as a genuine record/unit header (own line, own recurring "running header" or fixed tabular record shape) — never a bare in-body citation. Two built-in rules are added and documented with real evidence:
  - `jurisprudencia-em-teses-edicao-v1`: anchors on the once-per-unit "Edição n. NNN Brasília, DATA" line (distinct from the all-caps running header that repeats on every page of the same edition, and distinct from internal `Tema n. NNN` / `Lei n. NNN` citations, which never appear in that exact date-bearing shape).
  - `precedentes-qualificados-tema-repetitivo-v1`: anchors on the fixed tabular record header `Tema Repetitivo NNN  Situação ...  Órgão ...`, which never occurs as a bare citation (the corpus's own internal cross-reference, `Tema em IRDR n. 11/TJSP`, does not match this shape and correctly produces no boundary).
  A source that matches zero registry rules stays `SINGLE`. A source with inconsistent/partial matches of a rule is `AMBIGUOUS`, not silently split.
- Extend the Producer CLI additively:
  - New read-only `repo-jur producer analyze` command: given Markdown + report (+ optional `--type`), runs segmentation only, prints the outcome, the number of segments, each segment's title/page range/boundary rule id, and (best-effort, non-authoritative) a per-segment identity preview. Never writes state or bundle files.
  - `producer build` gains `--segment N` (build exactly one segment as today's single candidate, scoped to that segment's body/pages) and `--all-segments` (emit `candidates[]`, one per segment, in one JSON response; still writes only operational state, never the bundle).
  - Backward compatibility: when segmentation outcome is `SINGLE`, `producer build` behaves identically to today (same single `candidate` field, same exit codes) — the acórdão `AIRESP-1833684-2020-02-12` case is unaffected.
  - When outcome is `SEGMENTS` and neither `--segment` nor `--all-segments` is given, `build` fails closed with `EXIT_BLOCKED` and an explicit `segmentation_multi_concept` reason — it never silently renders the whole multi-unit source as one candidate.
  - When outcome is `AMBIGUOUS`, `build` fails closed with `EXIT_BLOCKED` and reason `segmentation_ambiguous`, regardless of flags.
- Each segment candidate carries the same PDF provenance as today (`repo_jur_pdf_hash`/`sources`) — segmentation does not duplicate the PDF per concept, it slices the shared Markdown. Multiple concepts from the same source legitimately share one `repo_jur_pdf_hash`; this is explicitly allowed by the existing `legal-knowledge` provenance rules and by Stage 9 retrieval, which already keys everything off `concept_id` (path), not PDF hash uniqueness.
- Three tiers are explicit and never conflated: **source document** (the whole Phase 1 artifact), **source segment** (a structural unit with `segment_id`, `source_unit_label`, page range, and boundary provenance — purely operational metadata, never legal identity), and **legal concept** (a `ConceptCandidate` whose identity is resolved from the segment's own body per the OKF Legal Profile). `resolve_concept_path()`/`_resolve_legal_identity()` are unchanged for the whole-document (`single`) case; for a `segments` outcome, a segment is built into a candidate only when its own body yields the type's required canonical identity fields (`IdentityStatus.RESOLVED`) — a segment's `source_unit_label` or ordinal is never used, directly or as a filename/path fallback, to stand in for an unresolved legal identity.
- No change to `router.py`, `Phase1Artifacts`, the Legal Semantic Review's engine-neutral contract, or `guard_legal_bundle_write`. Segmentation happens strictly before candidate rendering; the (unchanged) Legal Semantic Review then runs per-segment, scoped to that segment's body only.

## Out of Scope

- No OCR, no PDF re-processing, no rewriting of `output/*.md` or `logs/*.report.json` — Phase 1 remains byte-for-byte immutable.
- No LLM, embeddings, or content-based type classification of any kind, in segmentation or elsewhere.
- No publication to `bundle/` for the real-corpus documents in this change — `analyze` and `build` (never `publish`) are the only commands exercised against real corpus data.
- No new OKF Legal Profile field is invented to force "Edição N" (a bulletin/collection entry number in "Jurisprudência em Teses") into `repo_jur_tema_numero`. Real-corpus analysis in this change concludes each "Edição" is an editorial compilation of multiple unrelated official themes, not itself an official numbered theme — under the current profile, individual Edições are **not** sound `TemaJuridico` concepts, and this change does not fabricate an identity to force that fit. Extending the OKF profile with a dedicated editorial-collection field/type is left to a future, separately authorized change.
- No change to the status-field extraction heuristics for `PrecedenteVinculante` beyond what is required to prove segmentation itself (title/page-range/identity preview only); full field-completeness for that type is not a requirement of this change since no publication occurs.

## Capabilities

### Modified Capabilities
- `legal-knowledge`: Stage 7 gains a segmentation boundary strictly upstream of the Legal Producer: 1 Phase 1 artifact may now yield 0 (ambiguous/blocked), 1 (mono-concept, unchanged), or N (multi-concept) `ConceptCandidate`s, each independently validated, resolved, and publishable. The Producer CLI (`build`) gains `--segment`/`--all-segments`/`analyze` while remaining additive and non-regressive for existing callers.

## Impact

- **Affected modules:** new `src/pipeline_juridico/legal_source_segmentation.py`; `src/pipeline_juridico/legal_producer.py` (segment-scoped `_base_candidate`, identity fallback); `src/pipeline_juridico/legal_producer_cli.py` (`analyze`, `--segment`, `--all-segments`).
- **Affected tests:** new `tests/test_legal_source_segmentation.py`; updates to `tests/test_legal_producer.py`, `tests/test_legal_producer_cli.py`.
- No new external dependencies. Zero-write guarantees over Phase 1 and the bundle, engine neutrality, and explicit-`type`-only semantics are strictly preserved.
