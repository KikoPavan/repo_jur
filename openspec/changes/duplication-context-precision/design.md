# Design: Duplication Context Precision

## Status: CLOSED WITHOUT IMPLEMENTATION — see `proposal.md` § Status. No implementation authorized, and none will be pursued under this change (see `tasks.md`).

## Cross-reference note (added by `duplication-issue-semantic-neutrality`, documentation only)
As of `duplication-issue-semantic-neutrality`, the persisted `issue_type` value emitted by
`detect_duplications` for Schema 1.1 reports is `duplication` (legacy). Starting with Schema 1.2, the
neutral persisted name is `internal_repetition`. This rename is purely semantic/naming — it does not
change `min_len`, the sliding-window match/extension logic, the `gap <= 1.5 * match_len` acceptance
window, or any other detection behavior, and it does NOT resolve or unblock this change. Every
`duplication` reference below (including the Structural Evidence table) refers to the legacy
(pre-rename) value name as of when this text was written. This change remains BLOCKED for lack of a
verified `source-once → output-twice` positive control.

## Architecture (Current)
`detect_duplications` (`src/pipeline_juridico/fidelity.py:60-107`) uses a sliding-window match over whitespace-normalized text (`_get_norm_map`). On finding a repeated 120+ char window, it extends the match forward, maps back to source offsets, computes `gap = source_i - source_match_end`, and accepts the candidate as a `duplication` issue whenever `match_len >= 120` and `0 <= gap <= 1.5 * match_len`. It has no notion of what structurally lies inside the gap, and — critically — **it only ever sees the converted Markdown text; it has no access to the source PDF**. See "Conceptual limitation" in `proposal.md` for why this matters.

No "New" architecture section is proposed here. The previously proposed structural gap-classification rule (`MARKER_PATTERN`) was tested exploratorily and rejected; it is not a candidate design any more (see `proposal.md` § Rejected candidate rule). This document intentionally does not propose a replacement mechanism until the evidence gap is closed.

## Structural Evidence (from real corpus, no new OCR) — corrected

| Case | match_len | offsets (page-local) | gap text (verbatim, source) | Classification |
|---|---|---|---|---|
| ESCRITURA4 p2 (RECLASSIFIED — no longer a positive fixture) | 201 | 1169 / 1575 | `"neste ato\nrepresentada por seu bastante procurador Francisco Carlos Pavan, acima\nqualificado, nos termos da Procuração Pública lavrada no Oficial de Registro\nCivil das Pessoas Naturais do 37º Subdistrito -"` | Re-verified directly against the rendered source PDF (page 2/8, image-only page, no new OCR): the paragraph is printed **twice** in the source scan itself (source-count = 2), and twice in the Markdown output (output-count = 2). Since source-count == output-count, this is faithful transcription of a pre-existing source defect, NOT a duplication introduced by conversion. It must not be used to justify a suppression rule, and it must not be treated as a case that "must stay flagged" for the purpose of validating a precision fix. |
| CONTRSOCIAL8 p4 (false positive, confirmed; suppression rule NOT yet authorized) | 163 | 847 / 1078 | `"\n[ ] Anexar comprovante de pagamento complementar do preço do serviç"` | Gap begins with a new checklist marker `[ ]` → recurring form label, not duplication, per source PDF inspection. Remains a valid false-positive candidate, but no fix may be implemented against it alone (see Blocked / Evidence Gap). |
| CONTRSOCIAL8 p19 (false positive, confirmed; suppression rule NOT yet authorized) | 142 | 88 / 420 | `"541,15.\n\nd3) 39.458,85 quotas integralizadas, pela incorporação de bens imóveis constantes do Anexo \"C\" , parte integrante e inseparável deste instrumento, provenientes da cisão, advindas da"` | Gap begins with a new list item marker `d3)` → distinct tabular line item, not duplication. Verified visually: two list entries (`d2`/`d3`) with different R$ values. Remains a valid false-positive candidate, but no fix may be implemented against it alone (see Blocked / Evidence Gap). |

Offsets for CONTRSOCIAL8 above were re-read directly from `logs/4000153-37.2026.8.26.0136_SP_E001_CONTRSOCIAL8_P001-068.report.json` (page 4: `related_offsets = [847, 1078]`, size 163; page 19: `related_offsets = [88, 420]`, size 142) to keep this table consistent with the current persisted report artifact.

## Rejected candidate rule (see `proposal.md` for full TP/FP/TN/FN evidence)

```
MARKER_PATTERN = re.compile(r'(?m)^[ \t]*(?:\[[ xX]?\]|[a-zA-Z0-9]{1,3}\))[ \t]')
```

Exploratory testing (in-memory synthetic controls, no repository files changed) produced:

```
TP = 0
FP = 2
TN = 1
FN = 3
```

This rule is REJECTED as a design solution. It is documented here only so the rejection and its evidence are not lost; it must not be re-proposed without addressing why it fails (marker-shaped OCR noise inside a genuine duplication gap causes false negatives; the sliding-window match can truncate a real marker before the gap boundary, causing false positives).

## Why no replacement design is proposed
Any structural or heuristic rule for suppressing duplication false positives needs to be validated against at least one confirmed true positive — a case where the source PDF contains a passage once and the Markdown output contains it twice (conversion-introduced duplication). No such case currently exists in the corpus (see `proposal.md` § Blocked / Evidence Gap and the corpus sweep recorded below). Proposing a new mechanism without that validation target would repeat the same mistake as the rejected `MARKER_PATTERN`: a plausible-looking rule with no real positive to test it against.

## Corpus sweep for a source-once → output-twice candidate (no new OCR, no new conversions)
Searched every `*.report.json` under `logs/`, `logs/processos_auditoria_corrigidos/`, and `logs/processos_auditoria_final/` for `issue_type == "duplication"`. Only two files contain any duplication issues:
- `logs/4000153-37.2026.8.26.0136_SP_E001_ESCRITURA4_P001-008.report.json` — 1 issue (page 2, now reclassified as source-twice → output-twice, not a positive control).
- `logs/4000153-37.2026.8.26.0136_SP_E001_CONTRSOCIAL8_P001-068.report.json` — 2 issues (pages 4 and 19, both confirmed false positives, not positive controls).

No other already-converted document in the corpus produced a `duplication` issue at all, so none is even a candidate to check against its source PDF. **Result: NO VERIFIED POSITIVE CONTROL exists anywhere in the currently converted corpus.**

## Non-Goals (unchanged)
- No change to `min_len`, the `1.5 * match_len` gap ratio, or the sliding-window/extension algorithm — none of this is in scope while blocked.
- No new detector, no new issue type, no new schema field.
- No OCR re-processing.
