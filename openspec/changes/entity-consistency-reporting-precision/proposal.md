# Proposal: Entity Consistency Reporting Precision

## Problem
The `entity_consistency_checker` has structural offset/indexation bugs. A programmatic verification over 88 entity issues showed 15 occurrences where `offset_start` or `related_offsets` are out-of-bounds relative to the page's character count or incompatible with the span `size`. Additionally, the previous attempt to consolidate these issues tried to inject structured objects into `result.warnings`, which breaks the contract since it is strictly a `list[str]`.

## Rationale
To guarantee architectural compliance and precision:
1. **Offset Correctness is the primary blocker**: No aggregation can mask issues with invalid coordinates. The exact calculation of indexation must be fixed and proven by tests first.
2. **Document-level unequivocally**: Aggregated conflicts spanning multiple pages must live in a top-level container, distinctly separated from the strictly page-level `pages[i].fidelity_audit.issues`.
3. **Privacy-Safe Contract**: Aggregated issues must NOT persist any derived string content, tokens, or hashes from the legal document, maintaining the privacy boundaries.
4. **Result Warnings Preservation**: `result.warnings` must remain exactly `list[str]`.

## Goal
Fix the offset calculation of `entity_consistency_checker`, prove its determinism, and implement a privacy-safe, document-level consolidated reporting of fidelity issues without breaking the schema contract.
