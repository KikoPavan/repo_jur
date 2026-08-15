# DECISION MEMO — POST-OCR CRITICAL-DATA VALIDATION SEAM

**Versão:** 1.1  
**Data:** 15 de agosto de 2026  
**Status:** APPROVED — CLOSED — FROZEN  
**Supersedes:** `decision-memo-post-ocr-critical-data-validation-seam-v1.0-FROZEN.md`

## Decision

Preserve the non-mutating post-OCR critical-data validation seam.

The seam may detect and signal inconsistency but never autocorrect OCR content.

## Candidate fields

Configurable examples:

- CPF/CNPJ;
- process number;
- matrícula;
- selo/official identifiers;
- dates;
- monetary values;
- document numbers.

## Rule provenance requirement

A deterministic validation rule for format, length, check digit or identifier structure may be implemented only when supported by a **reliable, versioned technical or normative specification** appropriate to that identifier.

Each rule must record at least:

```text
rule_id
rule_version
applies_to
source/specification reference
validation logic version
```

## Anti-generalization rule

Never infer a universal format/length rule from:

- one observed document;
- one court sample;
- one OCR result;
- one local convention without authoritative specification.

This rule is especially important for digital seals and registry identifiers.

## Behavior

Allowed:

- format validation backed by specification;
- check-digit validation backed by specification;
- warning;
- `REVIEW_REQUIRED`;
- technical finding.

Forbidden:

- replacing OCR text;
- inventing digits;
- inferring missing characters;
- choosing silently between conflicting values;
- promoting a format-valid value to legal truth.

## Output

```json
{
  "status": "OK | WARNING | REVIEW_REQUIRED",
  "findings": []
}
```

## Future boundary

Deterministic comparison of redundant values distributed through the same document remains a separate future capability.

**Decision Status: APPROVED — CLOSED — FROZEN**
