# Proposal: Duplication Issue Semantic Neutrality

## Status: PROPOSED — documentation only, no implementation authorized yet

## Why
`internal_repetition_detector` (`src/pipeline_juridico/fidelity.py::detect_duplications`) receives only
the already-converted Markdown text and the page number. It has no access to the source PDF at
detection/runtime. It can therefore only ever measure `repetition observed in the converted Markdown
output` — a structural, purely textual fact. It cannot, by construction, determine whether that
repetition was introduced by the OCR/conversion pipeline (a genuine defect) or already present in the
source document (correct fidelity to a pre-existing defect).

Despite this, the current contract uses causal language that asserts the former:
- `openspec/specs/juridical-pdf-conversion/spec.md`, Requirement "Controle de Fidelidade e Incerteza
  OCR" (line 657) and its scenario "Duplicação suspeita é sinalizada conservadoramente" (line 662):
  `**WHEN** o OCR produz repetição substancial interna...` — asserts OCR as the cause of the repetition,
  which the detector cannot verify.
- The persisted `issue_type` value `"duplication"` itself asserts that something was duplicated (a
  causal/procedural claim), rather than describing what was actually measured (a repeated span observed
  in the output).
- `tests/test_ocr_fidelity_precision.py::test_duplication_precision_real_values`, comment on line 22:
  `# Positive: True substantial duplication (ESCRITURA4 Page 2 equivalent)` — this framing is stale.
  The blocked change `duplication-context-precision` (see `../duplication-context-precision/proposal.md`
  § "ESCRITURA4 p2 — reclassified, no longer a positive fixture") directly re-verified against the
  rendered source PDF that this exact case is `source-count == output-count == 2`: a faithful
  transcription of a duplication that already existed in the notarial instrument, not one introduced by
  conversion. The test's own synthetic data doesn't reference a real document, but its comment
  perpetuates the same causal confusion that the blocked change identified as the root conceptual issue.

This is purely a semantic/contract precision problem: what the system *claims* about what it detected
does not match what the detector can actually prove. It is independent of, and does not require
resolving, the evidence gap blocking `duplication-context-precision` (no positive control is needed to
fix mislabeled causality — only to change detection *heuristics*, which this change does not touch).

## What Changes
- Rename the persisted `issue_type` value from `"duplication"` to `internal_repetition` everywhere it is
  emitted, validated, and asserted against (`fidelity.py`, `models.py` comment, `report.py` if it
  literal-matches the value, `quality_gate.py` if it literal-matches the value, and all tests that assert
  `issue_type == "duplication"`).
- Rewrite the causal scenario language in `openspec/specs/juridical-pdf-conversion/spec.md` (the
  "Duplicação suspeita..." scenario) and any equivalent phrasing in
  `openspec/specs/phase1-quality-gate/spec.md`, from "o OCR produz repetição substancial interna" to
  "o sistema detecta repetição substancial interna no Markdown convertido", and add an explicit normative
  note that this issue type does NOT assert or imply that OCR/conversion caused the repetition.
- Update the stale/causally-worded comment in `tests/test_ocr_fidelity_precision.py`.
- Bump `schema_version` from `"1.1"` to `"1.2"`: Schema 1.1 becomes the legacy contract retaining
  `issue_type == "duplication"`; Schema 1.2 is the new contract that emits `internal_repetition` (see
  `design.md` § Schema Version Decision for the full rationale, consumer-agnostic bump criteria, and
  implementation impact on `models.py`/`report.py`). Historical `logs/*.report.json` artifacts persisted
  under Schema 1.1 are not rewritten and are not automatically migrated; no automatic migration tool is
  required. Consumers must interpret `issue_type` according to each report's own `schema_version`.
- Add a cross-reference note (as an implementation task, not applied now) instructing that
  `duplication-context-precision`'s documentation receive a pointer noting that `issue_type` has been
  renamed, so a future reader resuming that blocked change is not confused by the now-legacy `duplication`
  string still used throughout its text.

## Out of Scope (explicitly)
- No change to `detect_duplications`' detection heuristic: `min_len` (120), the sliding-window match/
  extension algorithm, the `gap <= 1.5 * match_len` acceptance window, and the overall structural logic
  remain byte-for-byte unchanged.
- No change to `entity_consistency_checker`, `monitor_sensitive_tokens`, `detect_visual_uncertainty`, or
  their `issue_type` values (`entity_inconsistency`, `sensitive_token_uncertainty`, `visual_uncertainty`)
  — only the `duplication` value is in scope.
- No requirement to rename the internal function `detect_duplications` or the detector name string
  `"internal_repetition_detector"` (already neutral) — renaming the function is optional and only if it
  does not expand scope; the function name is an internal implementation detail, not a persisted
  contract value, and is explicitly distinguished from the persisted `issue_type` string in this change.
- No renaming of the full Requirement "Controle de Fidelidade e Incerteza OCR" in
  `juridical-pdf-conversion/spec.md` — that Requirement covers multiple detectors (duplication, entity
  inconsistency, sensitive token uncertainty, visual uncertainty) beyond the one in scope here; only the
  specific scenario text asserting OCR causation for repetition is corrected.
- No reopening, modification, or unblocking of `duplication-context-precision`. That change remains
  BLOCKED and its detection heuristic is untouched. Historical documentation there that still says
  `duplication` remains valid as a reference to the (now legacy) value name as of when it was written.
- No rewriting of already-persisted `logs/*.report.json` artifacts. Historical reports keep the literal
  string `"duplication"` as they were generated; this change affects only future report generation and the
  specs/tests describing current/future behavior.
- No OCR re-processing, no code implementation, no test implementation. This change authorizes
  documentation only; Codex may not act on it in this state.

## Impact
- **Specs**: `juridical-pdf-conversion/spec.md` (scenario language), `phase1-quality-gate/spec.md`
  (scenario language, if it references OCR-causal wording for duplication).
- **Code (future implementation phase, not now)**: `src/pipeline_juridico/fidelity.py`,
  `src/pipeline_juridico/models.py` (comment and `Relatorio.schema_version` default `"1.1"` → `"1.2"`),
  `src/pipeline_juridico/report.py` (extend the `schema_version` allow-list to admit `"1.2"` with the same
  `fidelity_audit`-required rule as `"1.1"`) and `src/pipeline_juridico/quality_gate.py` only if it
  contains literal string matches against `"duplication"` (see `design.md` § Consumer Inventory —
  inspection found none beyond generic `issue_type` field validation, which is type-only, not
  value-literal).
- **Tests (future implementation phase, not now)**: `tests/test_fidelity.py`,
  `tests/test_ocr_fidelity_precision.py`, `tests/test_e2e_fidelity.py` — see `design.md` § Consumer
  Inventory for the exact list of assertions that must migrate.
- **Schema version**: bump from `"1.1"` to `"1.2"` (see `design.md` § Schema Version Decision). Schema 1.1
  is retained as a documented legacy contract; no code path removes support for reading/validating 1.1
  reports.
- **Persisted artifacts**: none rewritten. New reports use `schema_version: "1.2"` and
  `internal_repetition`; old reports keep `schema_version: "1.1"` and `duplication` permanently as
  historical record. No automatic migration of historical logs is provided or required.
