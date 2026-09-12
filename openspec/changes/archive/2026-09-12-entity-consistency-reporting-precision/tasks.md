# Tasks: Entity Consistency Reporting Precision

## Acceptance Criteria
- [x] No offset or `related_offsets` falls out-of-bounds relative to its page `char_count`.
- [x] Every coordinate resolves exactly to the candidate span that the checker compared.
- [x] Case, accentuation, and line break variations that are considered equivalent do not generate noise.
- [x] A logical conflict repeated across multiple pages generates a single consolidated documental issue.
- [x] The `groups`/`occurrences` structure in the consolidated issue contains exclusively numeric coordinates (page, offset, size).
- [x] No legal content, token, or derived hash is present in the `fidelity_audit` JSON.
- [x] `result.warnings` remains exclusively `list[str]`.
- [x] Schema 1.1 is implemented for the new structure to satisfy strict key consumers.
- [x] Regressions for previous bugs (E032 and ESCRITURA4) continue passing.
- [x] Complete test suite, conformance suite, and `openspec validate --all --strict` pass.

## Task 1: Offset Calculation Correctness
- **Description**: Fix `entity_consistency_checker` indexation mapping. Ensure `offset_start`, `offset_end`, and `related_offsets` accurately point to the exact string spans being compared, respecting the boundaries of the string segment given to the checker.
- **Constraints**: No document aggregation yet. Add strict unit tests proving coordinates resolve identically to the target spans and never exceed `len(text)`.

## Task 2: Schema 1.1 and Document-Level Container
- **Description**: Add `fidelity_audit` at the root of `Relatorio` (`src/pipeline_juridico/models.py`). Create `DocumentFidelityAudit` and `DocumentFidelityIssue` containing the privacy-safe `groups` schema. Update `validate_report_contract` and test fixtures to expect/validate Schema 1.1 when this field is present.
- **Constraints**: Ensure `result.warnings` remains typed and validated strictly as `list[str]`. 

## Task 3: Privacy-Safe Consolidation Logic
- **Description**: Implement the consolidation of page-level entity issues into the top-level `fidelity_audit.issues`. Group them numerically without persisting text keys. The consolidated `entity_inconsistency` issues MUST belong EXCLUSIVELY to the document-level `fidelity_audit.issues`. Do NOT keep the same inconsistencies in `pages[i].fidelity_audit.issues` to prevent report duplication. Page-level audits remain only for strictly page-local issue types. Add a regression test proving that for a conflict distributed across N pages: 1) there is exactly 1 document-level issue, 2) there are N numeric occurrences distributed in the corresponding groups, 3) there are no copies of the same `entity_inconsistency` in the page audits.
- **Constraints**: No textual snippets or hashes in the output. `issue_id` must be random UUID4.
