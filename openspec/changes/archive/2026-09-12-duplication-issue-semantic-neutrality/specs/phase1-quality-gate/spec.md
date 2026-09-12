# phase1-quality-gate Specification Delta

<!--
STATUS: PROPOSED — documentation only. NOT AUTHORIZED FOR IMPLEMENTATION.
This delta corrects the reference to the `issue_type` value used by the
internal-repetition detector (renamed from `duplication` to
`internal_repetition`, emitted under the new `schema_version` "1.2"; the
legacy `schema_version` "1.1" retains `duplication` — see ../../design.md §
Schema Version Decision) in the scenario describing structural metadata for
fidelity issues, and clarifies that "OCR fidelity issue" is a category label,
not a causal claim. It does not change the Quality Gate's actual validation
logic (`src/pipeline_juridico/quality_gate.py`), which already treats
`issue_type` generically (type-only, no literal-value branching — see
../../design.md § Consumer Inventory). Codex must not implement against this
delta until the orchestrator (Claude) explicitly authorizes an implementation
phase for this change.

NOTE: This delta targets the Requirement "Privacy-safe Fidelity Audit
Contract" in the current published spec (openspec/specs/phase1-quality-gate/
spec.md:40-47). It is unrelated to the differently-named Requirement
"Validação de Auditoria de Fidelidade" used by the still-BLOCKED
duplication-context-precision change's own (not-authorized) delta file; that
other delta is untouched by this change.
-->

## MODIFIED Requirements

### Requirement: Privacy-safe Fidelity Audit Contract

The system SHALL ensure the `fidelity_audit` section of the technical report is strictly privacy-safe.
It SHALL NOT store any plaintext content, names, words, snippets, or fingerprints derived from the source
document (such as content hashes).

#### Scenario: Fidelity issue contains only structural metadata
- **WHEN** a fidelity issue is detected (internal repetition, entity inconsistency, or uncertainty)
- **THEN** the recorded issue contains only: `issue_id` (non-content-derived), `detector`, `issue_type`,
  `resolution`, `groups` (which must be strictly numeric coordinates), `page_number` (if page-local),
  `offset_start`, `offset_end`, `size`, and optionally `related_offsets`
- **AND** it contains zero bytes of content-derived data
- **AND** for the internal-repetition detector specifically, `issue_type` is recorded, under
  `schema_version` `1.2`, as `internal_repetition` (under the legacy `schema_version` `1.1`, it is
  recorded as `duplication`) — a neutral label describing repetition observed in the converted Markdown;
  it does not assert that OCR or conversion caused the repetition
