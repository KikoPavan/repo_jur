# Design: Duplication Issue Semantic Neutrality

## Status: PROPOSED — documentation only, no implementation authorized yet

## Objective
Correct the contractual *semantics* of the internal-repetition detector without touching its heuristic:

1. The detector observes repetition inside the already-converted Markdown; it does not, and cannot at
   runtime, demonstrate that OCR/conversion caused that repetition.
2. `source-once → output-twice` causal attribution requires an explicit source-vs-output comparison
   (page render + visual/text inspection), which is outside the detector's inputs and is not performed at
   runtime today. It was only ever done manually, offline, by the blocked change
   `duplication-context-precision` (see its `proposal.md` § "Source Verification Without New OCR"
   equivalent analysis).
3. Correcting this is a naming/documentation problem, not a detection-accuracy problem, and is therefore
   independent of the evidence gap blocking `duplication-context-precision`.

## Current Architecture (unchanged by this proposal)
`detect_duplications` (`src/pipeline_juridico/fidelity.py:60-107`):
- Input: page-local Markdown text (`text: str`) and `page_number: int`. No PDF, no OCR metadata, no
  source comparison of any kind.
- Algorithm: normalize whitespace (`_get_norm_map`), sliding-window match over 120+ char windows, extend
  match, map back to source offsets, compute `gap = source_i - source_match_end`, emit a `FidelityIssue`
  with `issue_type="duplication"` when `match_len >= 120` and `0 <= gap <= 1.5 * match_len`.
- This proposal changes only the literal string assigned to `issue_type` (line 93) and, if adopted, the
  in-code comment on `models.py:24`. `min_len`, the window/extension logic, and the gap ratio are not
  touched.

## `issue_type` Rename Decision
- **New persisted value: `internal_repetition`.** This is the preferred name per the approved scope:
  it describes exactly what is measured (a repeated span observed inside the document's own converted
  text), with no causal claim about origin.
- Inspection found no existing conflicting use of the string `internal_repetition` as an `issue_type`,
  detector name, or schema field anywhere in `src/`, `tests/`, or `openspec/specs/` — the only existing
  use of the word "repetition" in the codebase is the detector's own name string
  `"internal_repetition_detector"` (`fidelity.py:94`), which is a `detector` field value (distinct field
  from `issue_type`) and remains unchanged. No technical conflict was found; `internal_repetition` is
  adopted without a fallback alternative.
- `duplication` is retained in this document and in all historical/blocked-change documentation as the
  **legacy name**: causally ambiguous, because it implies an event of duplication (introduced by
  something) rather than a neutral structural observation. It must not be reused as a new value anywhere
  in this pipeline going forward.
- `internal_repetition` is the **neutral structural name**: it asserts only "this span appears more than
  once, close together, in the converted output" — exactly what `detect_duplications` proves, and no
  more.
- The detector's internal function name `detect_duplications` and the `detector` field value
  `"internal_repetition_detector"` are **API-internal, not persisted contract**. Renaming the function is
  optional in a future implementation phase and is explicitly out of scope here if it would expand the
  diff unnecessarily; only the persisted `issue_type` string is a contractual value bound by
  `report.py`'s schema validation and by external consumers of `logs/*.report.json`.

## Spec Language Correction
The Requirement `Controle de Fidelidade e Incerteza OCR`
(`openspec/specs/juridical-pdf-conversion/spec.md:657`) is NOT renamed — it legitimately covers four
detectors (duplication/internal-repetition, entity inconsistency, sensitive token uncertainty, visual
uncertainty), and a title-level rename would create unnecessary scope and diff noise across scenarios
this change does not touch.

Only the specific scenario asserting OCR causation is corrected:

Current (line 661-665):
```
#### Scenario: Duplicação suspeita é sinalizada conservadoramente
- **WHEN** o OCR produz repetição substancial interna (acima de 100 caracteres) na mesma página
- **AND** a repetição não corresponde a padrões de boilerplate legítimos (como descrições repetidas de imóveis ou identificação cartorária recorrente)
- **THEN** o sistema registra a ocorrência no relatório JSON como `duplication`
- **AND** preserva o conteúdo original sinalizado no Markdown
```

Corrected (proposed delta, see `specs/juridical-pdf-conversion/spec.md` in this change):
```
#### Scenario: Repetição interna substancial é sinalizada conservadoramente
- **WHEN** o sistema detecta repetição substancial interna (acima de 100 caracteres) no Markdown convertido, na mesma página
- **AND** a repetição não corresponde a padrões de boilerplate legítimos (como descrições repetidas de imóveis ou identificação cartorária recorrente)
- **THEN** o sistema registra a ocorrência no relatório JSON como `internal_repetition`
- **AND** preserva o conteúdo original sinalizado no Markdown
- **AND** esta sinalização NÃO afirma nem implica que o OCR ou a conversão introduziu a repetição; ela descreve exclusivamente o que foi observado no Markdown de saída. Atribuição causal (se a repetição já existia na fonte ou foi introduzida pela conversão) exige comparação explícita fonte-vs-saída, que este detector não realiza em tempo de execução.
```

The neighboring scenario "Legitimate boilerplate is not flagged as duplication" (line 667-669) is
corrected only for the `issue_type` value reference (`duplication` → `internal_repetition`); its WHEN/THEN
logic already describes detector behavior neutrally and needs no causal-language fix.

`openspec/specs/phase1-quality-gate/spec.md` line 45 (`#### Scenario: Fidelity issue contains only
structural metadata`, `**WHEN** an OCR fidelity issue is detected (duplication, entity inconsistency, or
uncertainty)`) uses "OCR fidelity issue" generically as a category label, not as a causal claim about a
specific `issue_type`; it is corrected only to replace the word `duplication` with `internal repetition`
for consistency, without altering its normative meaning (it was already not asserting causation).

## Consumer Inventory (evidence for the Schema Version Decision)

Full text-search of `src/` and `tests/` for literal `issue_type` value matching against `"duplication"`:

| File | Line(s) | Nature of match | Literal-value dependent? |
|---|---|---|---|
| `src/pipeline_juridico/fidelity.py` | 93 | Assignment `issue_type="duplication"` (the producer) | N/A — this is the value being renamed |
| `src/pipeline_juridico/models.py` | 24 | Comment only, documents allowed values | No — comment, not code logic |
| `src/pipeline_juridico/report.py` | 69-83, 228-249 | Validates `issue_type` is `type str` and, for `DocumentFidelityAudit` issues only, that `detector == "entity_consistency_checker"` AND `issue_type == "entity_inconsistency"` together (line 82-85) | No, for `issue_type` value matching — validation is type-only for `issue_type` in general; the one literal-value check present (`entity_inconsistency`) is for a different, unrelated `issue_type` and unaffected by this change. No literal match on `"duplication"` exists in `report.py`. **However**, `validate_report_contract` (lines 143, 150, 276) enumerates the *allowed set* of `schema_version` values (`"1.0"`, `"1.1"`) and raises `ReportContractError` for anything else — this allow-list is a separate, distinct dependency from `issue_type` matching, and per the Schema Version Decision below it **does** require a code change to admit `"1.2"` (future implementation phase, not now). |
| `src/pipeline_juridico/quality_gate.py` | 131-134 | Reads `issue.get("issue_type")` only to interpolate into a free-text warning string (`f"Fidelity issue in {label}: {issue.get('issue_type')} detected by..."`) | No — passthrough/formatting only, no comparison against `"duplication"` |
| `tests/test_fidelity.py` | 19 assertion sites matching `issue_type` | Direct asserts `issue.issue_type == "duplication"` and `assert issues[0].issue_type == "duplication"` (e.g. line 35) | **Yes** — must migrate to `"internal_repetition"` |
| `tests/test_ocr_fidelity_precision.py` | 7 assertion sites (lines 29, 41, 141, 152, and others of the same pattern) | Direct filters `[i for i in audit.issues if i.issue_type == "duplication"]` | **Yes** — must migrate to `"internal_repetition"` |
| `tests/test_e2e_fidelity.py` | 1 site (line 71) | Fixture dict literal `"issue_type": "duplication"` used to build a synthetic report for an E2E assertion | **Yes** — must migrate to `"internal_repetition"` (verify the E2E assertion doesn't itself assert on the string `"duplication"` elsewhere in the same test) |
| `tests/test_report.py` | matches on `"issue_type"` field name (schema validation tests) | Only field-name/type presence, not value-literal, per grep of `"issue_type"` occurrences | Needs confirmation during implementation, but current inspection found no literal `"duplication"` value assertions in this file (only in the three files above) |

**No production code path (`fidelity.py` excluded, as it's the producer being changed) performs a literal
string comparison against `"duplication"`.** `report.py`'s schema validator checks `issue_type` is `str`
generically; it does not enumerate or restrict to a fixed set of `issue_type` values other than the one
unrelated `entity_inconsistency` check for `DocumentFidelityAudit` issues. `quality_gate.py` only
interpolates the value into free text; it never branches on it.

## Schema Version Decision

**Decision: bump schema_version from `"1.1"` to `"1.2"`. Schema 1.1 becomes a legacy contract; new reports
are emitted under Schema 1.2, which emits `internal_repetition` as the `issue_type` value produced by the
internal-repetition detector.**

**Normative rationale (why the earlier "no bump" analysis is overridden):**
- `issue_type` is a persisted, observable value in `.report.json`. It is part of the contract's *data*
  surface, not merely its structural/type surface. Renaming a persisted literal value that any external
  consumer could reasonably match on (`"duplication"` → `"internal_repetition"`) is a semantic break in
  the contract even though no *currently known, in-repository* consumer performs that literal-value match.
- The absence of a strict-enumeration check in `report.py` (see Consumer Inventory above) proves only that
  the *validator* would not reject the new value — it does not prove that no consumer depends on the old
  value. `report.py` validating `issue_type` as `type str` is a structural permissiveness, not evidence of
  semantic compatibility for downstream readers. A version bump exists precisely to signal such changes to
  consumers outside the validator's own reach (external tooling, dashboards, log-scraping, alerting rules
  built against `.report.json`).
- Per the project's own schema-versioning rule (see `legal-ocr-fidelity` skill, "Schema Versioning
  Evidence"), a version bump is required when a change is not backward-compatible for existing strict
  consumers. This decision treats "backward-compatible" conservatively: it is not limited to whether
  in-repo code branches on the literal value, but whether the *meaning* of a persisted field changes in a
  way an external, unobserved consumer could reasonably rely on. That is the case here.

**Contract of the two schema versions going forward:**
- **Schema 1.1 (legacy)**: `fidelity_audit` is a required top-level field (unchanged validation rule);
  the internal-repetition detector's `issue_type` value under this version is `duplication`. Historical
  reports already persisted in `logs/*.report.json` under `schema_version: "1.1"` are NOT rewritten and
  remain valid 1.1 artifacts with the literal string `duplication`. No automatic migration of historical
  logs is provided or required.
- **Schema 1.2 (current)**: identical structural contract to 1.1 (`fidelity_audit` remains a required
  top-level field; no other field, type, or validation rule changes) except that the internal-repetition
  detector's `issue_type` value is `internal_repetition` instead of `duplication`. This is the only
  semantic difference between 1.1 and 1.2.
- **Consumer responsibility**: consumers of `.report.json` MUST interpret `issue_type` according to the
  report's own `schema_version` field: `duplication` under `schema_version: "1.1"`, `internal_repetition`
  under `schema_version: "1.2"`. A consumer that matches literally on `"duplication"` without checking
  `schema_version` will silently stop matching internal-repetition issues in 1.2 reports; this is the
  expected, signaled behavior of the version bump, not a defect.

**Implementation impact (future phase, not authorized now):**
- `Relatorio.schema_version` default changes from `"1.1"` to `"1.2"` (`models.py:138`).
- `report.py::validate_report_contract`'s `schema_version` allow-list (lines 143, 150, 276) must admit
  `"1.2"` alongside `"1.0"` and `"1.1"`, and apply the same `fidelity_audit`-required branch to `"1.2"` as
  it currently does to `"1.1"` (the structural rule is identical between the two; only the literal
  `issue_type` value differs, which `report.py` does not enumerate).
- No other structural, type, or validation change to the schema.

**Non-goals of this version bump:**
- No migration tool or automatic rewriting of historical `logs/*.report.json` artifacts. They remain
  valid, permanent 1.1 records under the pre-rename value.
- No change to any other field, detector, or `issue_type` value (`entity_inconsistency`,
  `sensitive_token_uncertainty`, `visual_uncertainty` are unaffected and remain under whatever
  `schema_version` they were already emitted under).


## Cross-Reference Task for `duplication-context-precision`
Not applied now (per approval scope: "If a cross reference is needed in the blocked change, leave it as
an implementation task; do not modify those files now"). Recorded here as a task in `tasks.md` for a
future implementation phase: add a short note near the top of
`openspec/changes/duplication-context-precision/proposal.md` and `design.md` stating that `issue_type`
has been renamed to `internal_repetition` by this change, and that all `duplication` references in that
change's text refer to the legacy (pre-rename) value name as of when it was written, not to any change in
the blocked heuristic itself.

## Non-Goals
- No change to `min_len`, the sliding-window match/extension algorithm, or the `gap <= 1.5 * match_len`
  acceptance window.
- No change to `entity_inconsistency`, `sensitive_token_uncertainty`, or `visual_uncertainty` issue
  types.
- No unblocking, reopening, or heuristic modification of `duplication-context-precision`.
- No rewriting of `logs/*.report.json` historical artifacts.
- No OCR reprocessing.
- No `result.warnings` structural change and no change to the privacy-safe contract (numeric offsets
  only, UUID4 `issue_id`, no content-derived data) — only the `issue_type` string value and scenario
  wording change.
