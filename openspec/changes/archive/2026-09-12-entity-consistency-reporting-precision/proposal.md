# Proposal: Entity Consistency Reporting Precision

## Why
The `entity_consistency_checker` has structural offset/indexation bugs. A programmatic verification over 88 entity issues showed 15 occurrences where `offset_start` or `related_offsets` are out-of-bounds relative to the page's character count or incompatible with the span `size`. `result.warnings` has an existing contract as `list[str]`, and structured fidelity issues must not be introduced into that field.

## What Changes
1. **Offset Correctness**: Fix exact calculation of indexation to ensure validity.
2. **Schema 1.1 & Document-level Audits**: Introduce a top-level container for aggregated document conflicts, distinctly separated from the strictly page-level `pages[i].fidelity_audit.issues`.
3. **Privacy-Safe Contract**: Aggregated issues must NOT persist any derived string content, tokens, or hashes from the legal document, maintaining privacy boundaries.
4. **Result Warnings Preservation**: Maintain `result.warnings` exclusively as `list[str]`.
5. **Out of Scope**: The `internal_repetition_detector` is not modified by this change. Its false-positive behavior observed in repeated boilerplate/tabular content remains deferred to the future change `duplication-context-precision`.

## Goal
Fix the offset calculation of `entity_consistency_checker`, prove its determinism, and implement a privacy-safe, document-level consolidated reporting of fidelity issues without breaking the schema contract.
