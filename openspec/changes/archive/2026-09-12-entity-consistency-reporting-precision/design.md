# Design: Entity Consistency Reporting Precision

## Architecture (Current → New)
- **Current**: Desynchronized offsets in `entity_consistency_checker`; potential contract violation by mixing objects in `result.warnings` (though not merged, it was proposed).
- **New**: 
  - `result.warnings` is strictly preserved as `list[str]`.
  - A new document-level `fidelity_audit` object is added to the root of the Report schema to house cross-page aggregated issues.

## Documental Location (JSON Layout)
We will introduce a top-level `fidelity_audit` object alongside `input`, `phase1`, `result`, etc.
Page-level audits (`pages[i].fidelity_audit`) remain strictly for page-local issues.

**Current JSON (1.0)**:
```json
{
  "schema_version": "1.0",
  "execution_id": "...",
  "result": {
    "warnings": ["string1", "string2"]
  },
  "pages": [
    {
      "fidelity_audit": {
        "issues": [
          {"issue_type": "entity_inconsistency", "offset_start": 100, ...}
        ]
      }
    }
  ]
}
```

**Proposed JSON**:
```json
{
  "schema_version": "1.1",
  "execution_id": "...",
  "fidelity_audit": {
    "issues": [
      {
        "issue_id": "uuid4",
        "issue_type": "entity_inconsistency",
        "detector": "entity_consistency_checker",
        "resolution": "flagged",
        "groups": [
          {
            "group": 0,
            "occurrences": [
              {"page_number": 1, "offset_start": 100, "offset_end": 120, "size": 20}
            ]
          },
          {
            "group": 1,
            "occurrences": [
              {"page_number": 8, "offset_start": 1099, "offset_end": 1121, "size": 22}
            ]
          }
        ]
      }
    ]
  },
  "result": {
    "warnings": ["string1", "string2"]
  }
}
```

## Privacy-Safe Contract
The aggregated document-level issue will **only** contain numeric coordinates. 
No string values, snippets, tokens, or text keys used internally for aggregation will be saved. 
- Technical enums (`issue_type`, `detector`, `resolution`) are allowed.
- `groups` are technical non-semantic containers indicating which occurrences correspond to the conflicting variants.

## Schema Versioning (Evidence & Decision)
**Analysis**: Inspection of `tests/test_report.py`, `tests/test_models.py`, and `src/pipeline_juridico/report.py` shows that consumers perform strict set-based key validation (`assert set(data) == {"schema_version", "execution_id", "input", "phase1", "result", "artifacts", "pages", "telemetry"}`). Adding `fidelity_audit` as a top-level key fundamentally alters the dictionary keys emitted by `asdict(Relatorio)`.
**Decision**: Because this structural addition breaks strict key validation in consumers, this change **MUST bump `schema_version` to "1.1"** to signal contractual evolution, unless we implement custom serialization that dynamically strips the field. Bumping to **1.1** is the transparent and correct architectural decision.

## Scope Limits
The `internal_repetition_detector` and its context precision (p4/p19) are strictly excluded from this change and deferred to a future `duplication-context-precision` change.
