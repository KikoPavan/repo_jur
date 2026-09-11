# phase1-quality-gate Specification Delta

## MODIFIED Requirements

### Requirement: Quality Gate result contains only state, warnings, and errors
The system SHALL return a Quality Gate result containing a state value, an immutable ordered tuple of warnings (`tuple[str, ...]`), an immutable ordered tuple of errors, and optional non-authoritative diagnostics. The state SHALL be exactly one of the three `GateState` members — `PASS`, `PASS_WITH_WARNINGS`, `FAIL`.

#### Scenario: PASS_WITH_WARNINGS includes privacy-safe fidelity issues
- **WHEN** the Quality Gate evaluates artifacts with non-fatal fidelity issues
- **THEN** the issues are recorded in the technical report's `fidelity_audit`
- **AND** the issues MUST NOT contain any text snippets or content-derived fingerprints
- **AND** the result state is `PASS_WITH_WARNINGS`

## ADDED Requirements

### Requirement: Privacy-safe Fidelity Audit Contract
The system SHALL ensure the `fidelity_audit` section of the technical report is strictly privacy-safe. It SHALL NOT store any plaintext content, names, words, snippets, or fingerprints derived from the source document (such as content hashes).

#### Scenario: Fidelity issue contains only structural metadata
- **WHEN** an OCR fidelity issue is detected (duplication, entity inconsistency, or uncertainty)
- **THEN** the recorded issue contains only: `issue_id` (non-content-derived), `detector`, `issue_type`, `page_number`, `offset_start`, `offset_end`, `size`, and optionally `related_offsets`
- **AND** it contains zero bytes of content-derived data
