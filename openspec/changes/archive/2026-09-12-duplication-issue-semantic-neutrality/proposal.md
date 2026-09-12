# Proposal: Duplication Issue Semantic Neutrality

## Status: PROPOSED — documentation only, no implementation authorized yet

## Why
`internal_repetition_detector` (`src/pipeline_juridico/fidelity.py::detect_duplications`) receives only
the converted Markdown and page number, with no source PDF access at runtime. It can only measure
repetition observed in the output — it cannot tell whether that repetition was introduced by conversion
or already present in the source.

Despite this, the contract uses causal language: the spec scenario "Duplicação suspeita é sinalizada
conservadoramente" says `**WHEN** o OCR produz repetição substancial interna...`, and the persisted
`issue_type` value `"duplication"` implies the pipeline duplicated something. A test comment repeats the
same stale framing. The blocked change `duplication-context-precision` found a case labeled "true
duplication" was actually a faithful transcription of a source repetition, reinforcing that this
detector cannot support causal attribution.

This is a semantic/contract precision problem, independent of `duplication-context-precision`.

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
