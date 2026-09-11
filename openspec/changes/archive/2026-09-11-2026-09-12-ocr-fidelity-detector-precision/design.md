# Design: OCR Fidelity Detector Precision and Privacy Correction

## Detector Refinement Logic

### 1. Duplication Detector (Contextual)
- **Current**: 100-char sliding window.
- **Improved**:
    - Preserve the 100-char threshold.
    - Add context check: If the repetition matches a "boilerplate" pattern (e.g., repeating property descriptions in Page 5 of ESCRITURA4, or notary headers in Page 8), it should be suppressed UNLESS it shows structural corruption (e.g., fragments of the same text overimposed).
    - Use distance check: Legitimate boilerplate usually has a significant distance or clear structural separation (different paragraphs).
    - Synthetic Fixtures: Reproduce ESCRITURA4 pages 5, 6, 8 as negatives and Page 2 as a positive.

### 2. Entity Inconsistency (Contextual)
- **Current**: 1-char edit distance variations.
- **Improved**:
    - Only extract potential entities from specific contexts:
        - Sequences of Title Case words (e.g., "Fulano de Tal").
        - Sequences of ALL CAPS (e.g., "EMPRESA LTDA").
        - Structured codes (e.g., "JKMG/JKMQ").
    - Reject common lexical variants: "PESSOA/PESSOAS", "TERCEIRA/TERCEIRO".
    - Reject short common words.

### 3. Visual Uncertainty (Contextual)
- **Current**: High density of noise/mixed tokens.
- **Improved**:
    - Do not flag structured codes that follow a pattern (e.g., `ESCRITURA4`, `E032`).
    - Focus on truly anomalous alphanumeric corruption (random-looking strings that are not identifiers).

## Privacy-Safe Reporting
- **Fingerprint Removal**: Delete `get_fingerprint` from `fidelity.py`.
- **Correlation ID**: Introduce `issue_id` (UUID or incremental within report) to link related occurrences (e.g., the two parts of a duplication).
- **Metadata-Only Logging**:
    - `detector`: Name of the detector.
    - `issue_type`: Category.
    - `page_number`: Page where it occurred.
    - `offset_start`, `offset_end`: Location in the Markdown.
    - `size`: Length of the issue.
    - `related_occurrences`: List of offsets for related snippets (for duplication/inconsistency).
- **Zero Content Storage**: No snippets, no hashes of snippets.

## Documentation Cleanup
- Search and destroy `double_checked` and `[[ilegível]]` references in `openspec/specs/`.
- Ensure the `juridical-pdf-conversion` spec reflects that no automatic correction occurs in Phase 1.
