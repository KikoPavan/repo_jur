# phase1-quality-gate Specification

## MODIFIED Requirements
### Requirement: Privacy-safe Fidelity Audit Contract

The system SHALL ensure the `fidelity_audit` section of the technical report is strictly privacy-safe. It SHALL NOT store any plaintext content, names, words, snippets, or fingerprints derived from the source document (such as content hashes).

#### Scenario: Fidelity issue contains only structural metadata
- **WHEN** an OCR fidelity issue is detected (duplication, entity inconsistency, or uncertainty)
- **THEN** the recorded issue contains only: `issue_id` (non-content-derived), `detector`, `issue_type`, `resolution`, `groups` (which must be strictly numeric coordinates), `page_number` (if page-local), `offset_start`, `offset_end`, `size`, and optionally `related_offsets`
- **AND** it contains zero bytes of content-derived data

## ADDED Requirements
### Requirement: Document-level fidelity audit for cross-page issues

The system SHALL maintain a document-level `fidelity_audit.issues` object at the root of the Schema 1.1 report for cross-page aggregated issues. Cross-page `entity_inconsistency` issues MUST belong EXCLUSIVELY to this document-level `fidelity_audit.issues` array and SHALL NOT be duplicated in `pages[i].fidelity_audit.issues`. Page-level audits SHALL be used exclusively for strictly page-local issue types.

#### Scenario: Cross-page conflict resolution
- **WHEN** a logical conflict is repeated across `N` multiple pages
- **THEN** there is exactly 1 document-level issue recorded in the root `fidelity_audit.issues`
- **AND** there are `N` numeric occurrences distributed in the corresponding groups of that single issue
- **AND** there are no copies of the same `entity_inconsistency` issue in the page-level audits (`pages[i].fidelity_audit.issues`)