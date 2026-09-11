# Proposal: OCR Fidelity Detector Precision and Privacy Correction

## Why
The current OCR fidelity detectors are producing false positives in legitimate legal scenarios (boilerplate repetition, common lexical variants, structured document codes). Additionally, the audit report contract uses fingerprints derived directly from content (SHA-256 of text snippets), which poses a privacy risk as low-entropy tokens can be reversed via dictionary attacks. Some documentation still refers to obsolete concepts like `double_checked` or `[[ilegível]]`.

## What Changes
1. **Refine Detectors**:
    - **Duplication**: Require structural evidence to distinguish accidental repetition from legitimate boilerplate (ESCRITURA4 pages 5, 6, 8).
    - **Entities**: Contextual extraction of proper names/entities (Title Case, ALL CAPS names/signatures) to avoid flagging common lexical variants (PESSOA/PESSOAS).
    - **Visual Uncertainty**: Avoid flagging legitimate structured codes (ESCRITURA4) or technical identifiers.
2. **Privacy Patch**:
    - Remove content-derived fingerprints.
    - Replace with non-derived `issue_id`/correlation IDs.
    - Log minimal metadata: detector, type, page, offsets, size, and related occurrence offsets.
3. **Audit & Alignment**:
    - Remove obsolete references from canonical specs (`double_checked`, `[[ilegível]]`).
    - Align specs with the strictly detect-only behavior.

## Impact
- Reduced noise in fidelity reports.
- Enhanced privacy compliance.
- Documentation consistency.
