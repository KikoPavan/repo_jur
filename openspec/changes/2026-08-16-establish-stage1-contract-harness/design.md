## Context

The current package already owns shared PDF conversion code and Phase 1 artifact models. Stage 1 needs only the genuinely absent cross-domain contract layer. These contracts must be usable by later Legal Knowledge and Judicial Process capabilities without importing either domain's schema and without changing the established conversion pipeline.

## Goals / Non-Goals

**Goals:**

- Represent canonical Actor, gate, critical-validation, and route-target values.
- Resolve evidence references safely beneath a caller-provided root.
- Reserve the Legal bundle root for the Legal Knowledge domain only (allowlist).
- Keep the implementation dependency-free, deterministic, and independently testable.

**Non-Goals:**

- Parse ITP manifests or ZIP files, preserve evidence, or integrate object storage.
- Implement critical-data rules, Quality Gate decisions, or domain routing behavior.
- Add Legal or Process schemas, producers, storage, retrieval, or OCR behavior.
- Wire new contracts into existing conversion modules.

## Decisions

### Dedicated common-contracts module

The contracts live in `pipeline_juridico.contracts`. Existing `models.py` remains the Phase 1 artifact model and is reused unchanged. A dedicated module avoids coupling future cross-domain consumers to conversion report details or overloading the page-method router.

### String-valued enums and immutable Actor values

Canonical states and route targets use string-valued enums so their normative serialized values are direct and unambiguous. Actor parsing returns an immutable value that retains the original representation and separates its kind, identifier, and optional producer version.

### Resolve paths before authorization

The safe-path primitive first rejects absolute and explicit traversal references, then resolves both the allowed root and candidate and verifies containment. This also catches existing symlinks that escape the root. The Zero-Write guard uses resolved containment so aliases cannot bypass domain isolation.

### Unwired contracts

The new types are deliberately not imported by the CLI, converter, page router, validator, report, or existing models. Behavioral adoption belongs to later staged changes and would alter current conversion semantics.

## Risks / Trade-offs

- Actor validation is structural only: components must be non-empty and free of the grammar's structural separators (`:` and `/`); no character whitelist is imposed, so accents and other identifier characters are accepted. Later ITP work may tighten identifiers only if a normative contract requires it.
- Resolution can only detect symlink escape for filesystem components that exist at validation time. Callers that write later must retain controlled-root ownership and avoid time-of-check/time-of-use races.
- The critical finding payload is intentionally minimal; later rule-registry work may add optional fields without changing the canonical result status contract.

## Validation

- Run focused contract tests.
- Run the complete pre-existing test suite plus the new tests.
- Validate every OpenSpec artifact in strict mode.
- Inspect Git status to confirm that only explicitly allowed additive files exist.
