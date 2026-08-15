# DECISION MEMO — SEMANTIC REVIEW / ENRICHMENT LAYER

**Versão:** 1.1  
**Data:** 15 de agosto de 2026  
**Status:** APPROVED — CLOSED — FROZEN  
**Supersedes:** `decision-memo-semantic-review-enrichment-layer-v1.0-FROZEN.md`

## Decision

Semantic Review / Enrichment remains post-Quality-Gate, bounded-context-specific and pre-Producer.

It may correct **structure, classification and enrichment artifacts**, but it has no authority to freely rewrite legal content.

## Immutable source rule

The original Phase 1 Markdown is immutable input evidence for Semantic Review.

It is never overwritten.

## Allowed operations

Semantic Review may:

- classify a document;
- identify structural boundaries;
- separate or associate structural fields;
- prepare domain YAML/enrichment candidates;
- create structured patches;
- attach metadata/provenance;
- signal ambiguity;
- request human review.

Examples such as a boundary problem between `Papel` and `Nome` belong here rather than in the deterministic converter.

## Content preservation

When the operation is structural:

- preserve every original word;
- do not summarize;
- do not paraphrase;
- do not translate;
- do not invent;
- do not fill missing text by inference.

## Structured patches

Prefer patch records containing:

```json
{
  "before": "...",
  "after": "...",
  "reason": "...",
  "confidence": 0.0,
  "page_refs": [],
  "evidence_refs": []
}
```

`after` may reorganize structure, but cannot introduce unsupported legal content.

## Traceability

Each material semantic/structural change must remain traceable to:

- original Phase 1 artifact;
- page/evidence when available;
- before;
- after;
- reason;
- confidence or equivalent review signal.

## Ambiguity

If a structural correction cannot be made without inference:

`REVIEW_REQUIRED`

## Publication

Semantic Review never publishes canonical storage.

Only the appropriate bounded-context Producer may publish.

## Domain separation

Legal Knowledge and Judicial Process maintain separate:

- YAML schemas;
- semantic enrichment schemas;
- classifiers;
- Producer candidates.

Only truly common execution contracts may be shared.

## Invariants

1. Phase 1 Markdown is never overwritten.
2. Structural correction must preserve source words when no semantic rewrite is authorized.
3. No unsupported summary/paraphrase/translation/invention.
4. Patches are preferred over destructive rewriting.
5. Before/after/reason/confidence are recorded for reviewable changes.
6. Page/evidence traceability is preserved where supported.
7. Ambiguity becomes `REVIEW_REQUIRED`.
8. Semantic Review never publishes.
9. `Papel/Nome`-style structural boundary issues belong to Semantic Review, not deterministic conversion.
10. Domain schemas/enrichment remain isolated.

**Decision Status: APPROVED — CLOSED — FROZEN**
