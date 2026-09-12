# Proposal: Duplication Context Precision

## Status: BLOCKED — no verified positive control (see Blocked / Evidence Gap)

## Why
The `internal_repetition_detector` (`src/pipeline_juridico/fidelity.py::detect_duplications`) has two known false positives, evidenced against the real corpus without any new OCR:

- `4000153-37.2026.8.26.0136_SP_E001_CONTRSOCIAL8_P001-068`, page 4: a ~163-char repeated span (offsets 847/1078 in the page-local text, per `logs/4000153-37.2026.8.26.0136_SP_E001_CONTRSOCIAL8_P001-068.report.json`) between two lines of a JUCESP checklist form (`[ ] Anexar comprovante ...`). The gap between the two occurrences begins with a new checklist item marker (`[ ]`), i.e. the repetition is the legitimate recurring label of a form, not a duplicated block.
- Same document, page 19: a ~142-char repeated span (offsets 88/420) consisting of a dot-fill leader (`....`) plus the template phrase `"Ltda., no valor de ... R$"`, shared by two distinct itemized list entries (`d2)` / `d3)`) with different numeric values (541,15 vs 39.458,85). The gap begins with a new list item marker (`d3)`).

Both were confirmed against the source PDF (rendered, no new OCR/AI transcription) to be legitimate tabular/form structures repeated across distinct enumerated items, not conversion-introduced duplication. **These remain valid false-positive candidates for a future precision fix**, but per the Blocked / Evidence Gap section below, no suppression rule can be implemented until a genuine true positive exists to validate against.

`E032` (`4000153-37.2026.8.26.0136_SP_E032_DESPADEC1_P001-003`) has no duplication in any of its 3 pages and serves as an additional negative regression case that must remain unaffected.

### ESCRITURA4 p2 — reclassified, no longer a positive fixture
`4000153-37.2026.8.26.0136_SP_E001_ESCRITURA4_P001-008`, page 2 (physical page 2/8) was previously treated as the detector's required true positive: a ~201-char span (offsets 1169/1575) where the Markdown output shows the "Procuração Pública" paragraph printed twice.

Direct re-verification against the source PDF (rendered at 3x, no OCR, no re-transcription) shows this is **not** a conversion defect:
- **source-count = 2** — the source scan (page 2/8, 100% image page, 0 native text chars, 1 embedded image) itself shows the paragraph printed twice, back-to-back, in continuous prose, confirmed by visual transcription of the rendered page (region containing "...neste ato representada por seu bastante procurador Francisco Carlos Pavan... Procuração Pública lavrada...pasta sob nº 03, paginas 13" appears twice verbatim before the next clause "; GILBERTO PAVAN, empresário...").
- **output-count = 2** — `output/4000153-37.2026.8.26.0136_SP_E001_ESCRITURA4_P001-008.md`, page 2 block (offsets 4279–9002), reproduces the same paragraph twice, in the same position, with the same wording as the source.
- **source-count == output-count == 2** → the OCR/conversion faithfully transcribed a duplication that already exists in the notarial instrument itself (an error made by the notary/scrivener when the original document was drawn up), not a defect introduced by this pipeline.

Because the detector's purpose (per `juridical-pdf-conversion` spec, Requirement "Controle de Fidelidade e Incerteza OCR") is to catch repetition the OCR/conversion produces, ESCRITURA4 p2 does not qualify as evidence for that requirement. It is, at most, an example of *correct* fidelity to a source-document defect — the opposite of what this change needs to demonstrate. **ESCRITURA4 p2 MUST NOT be used as a positive fixture for this change.**

## What Changes
No code or test changes are authorized at this stage. This proposal previously described a structural gap-classification rule; that rule was evaluated exploratorily and rejected (see "Rejected candidate rule" below). No implementation may proceed until Blocked / Evidence Gap is resolved.

## Rejected candidate rule
A structural gate was proposed: suppress a duplication candidate whenever the literal gap text between the two matched occurrences starts a line with an enumerated-item marker (checkbox `[ ]`/`[x]`/`[X]`, or a short alphanumeric list label such as `1)`, `a)`, `d3)`), expressed as:

```
MARKER_PATTERN = re.compile(r'(?m)^[ \t]*(?:\[[ xX]?\]|[a-zA-Z0-9]{1,3}\))[ \t]')
```

This rule was tested exploratorily (in-memory only, no repository files changed) against 3 synthetic positive controls (true duplication where the gap coincidentally contains a marker-shaped OCR artifact: a stray floating numeral, an inline clause citation, a garbled stamp fragment) and 3 synthetic negative controls (legitimate two-item lists/checklists sharing a long boilerplate prefix: checkbox list, itemized `d2)/d3)` list, subclause `a)/b)` list), reusing the unmodified match/gap arithmetic from `detect_duplications`.

Result:

```
TP = 0
FP = 2   (checklist-with-identical-labels case; subclause list where the match window truncates the marker before the required space/tab)
TN = 1   (itemized list with differing trailing values)
FN = 3   (all three "OCR artifact coincidentally shaped like a marker inside a genuine duplication" cases)
```

The rule is not robust: it suppresses genuine duplication whenever a stray character sequence in the gap happens to look like a list marker (100% false-negative rate on the positive controls tested), and it fails to suppress legitimate lists whenever the sliding-window match consumes or truncates the marker itself before the gap boundary (2 of 3 false positives on the negative controls tested). **`MARKER_PATTERN` is rejected and MUST NOT remain the proposed solution in `design.md`.** It is retained here only as a record of what was tried and why it does not work.

## Blocked / Evidence Gap
- No case in the corpus currently validated (all pages of ESCRITURA4, all pages of CONTRSOCIAL8, all other `logs/*.report.json` files in `logs/`, `logs/processos_auditoria_corrigidos/`, and `logs/processos_auditoria_final/`) is a demonstrated `source-once → output-twice` duplication, i.e. a case where the source PDF page contains the passage exactly once and the converted Markdown contains it twice. ESCRITURA4 p2 was the only candidate ever proposed for this role, and it is now reclassified as `source-twice → output-twice` (correct fidelity, not a defect).
- Without at least one verified `source-once → output-twice` positive control, it is not possible to demonstrate that any candidate heuristic (marker-based or otherwise) reduces false positives (CONTRSOCIAL8 p4/p19-style cases) without also suppressing true conversion-introduced duplication. The exploratory test above illustrates exactly this risk on synthetic data; without a real positive control there is no way to validate a fix against the actual failure mode this change is meant to address.
- **No implementation may begin until this evidence gap is closed.** The blocking prerequisite is: obtain and verify at least one real `source-once → output-twice` case (comparing the rendered source PDF page against the corresponding Markdown output), using only already-converted corpus artifacts or, if none exists, an explicitly human-approved new conversion — not assumed from existing fixtures.

## Conceptual limitation: repetition observed vs. duplication introduced
`detect_duplications` (and any candidate refinement of it) only ever observes the **converted Markdown text** — it has no access to the source PDF at detection time. It can therefore only detect *repetition observed in the output*. It cannot, by construction, determine whether that repetition was:
- (a) **introduced by the OCR/conversion pipeline** (a genuine defect — the target this detector exists to catch), or
- (b) **already present in the source document** (correct fidelity to a pre-existing defect in the notarial instrument, as ESCRITURA4 p2 turned out to be).

Distinguishing (a) from (b) requires an explicit source-vs-output comparison (page rendering + visual/text inspection), which is outside what the in-Markdown detector can do on its own. Documentation and future design work for this detector must consistently use the terms `repetition observed in output` (what the detector can measure) and `duplication introduced by OCR` (the narrower claim that any suppression/precision rule is actually trying to validate against) rather than treating them as synonyms.

## Scope
### In Scope
- Documentation only, at this stage (`proposal.md`, `design.md`, `tasks.md`). No changes to `src/pipeline_juridico/fidelity.py` or to `tests/` are authorized until the Blocked / Evidence Gap prerequisite is resolved and re-approved.

### Out of Scope
- `entity_consistency_checker`, `monitor_sensitive_tokens`, `detect_visual_uncertainty` — untouched.
- Any OCR re-processing of the evidenced documents.
- Schema/report format changes (schema stays whatever version is current; no new fields).
- Any correction, normalization, or rewriting of Markdown content.

## Success Criteria (deferred — not achievable until unblocked)
The following were the original success criteria for an implementation phase; they cannot be pursued until a verified positive control exists:
- A real `source-once → output-twice` case is identified and verified (source PDF render vs. Markdown output), OR the corpus is exhaustively confirmed to contain none, with that conclusion explicitly recorded.
- CONTRSOCIAL8 pages 4 and 19 produce zero `duplication` issues under a validated (not the rejected `MARKER_PATTERN`) rule.
- E032 (all 3 pages) continues to produce zero `duplication` issues.
- All existing `test_fidelity.py` and `test_ocr_fidelity_precision.py` duplication tests continue to pass unmodified.
- No other page across the two full evidenced documents (8 pages ESCRITURA4, 68 pages CONTRSOCIAL8) changes classification (verified by full-document diff before/after).
