## Why

Future Legal Knowledge and Judicial Process stages need a small set of shared contracts and filesystem guards before domain-specific schemas or runtime behavior are introduced. The repository currently has Phase 1 conversion artifact types, but no common Actor validation, safe evidence-path primitive, canonical gate/critical/routing types, or guard preventing Process writes into the Legal bundle.

## What Changes

- Add a standalone common-contracts module for Actor parsing and validation.
- Add a reusable safe relative-path resolver that rejects absolute paths, traversal, and resolution outside an allowed root.
- Define the canonical Quality Gate, critical-validation, and route-target value contracts without wiring them into the current pipeline.
- Add a Zero-Write guard that allows only the Legal Knowledge domain (`legal_knowledge`) to target the Legal Knowledge bundle root; every other acting domain is rejected.
- Add focused tests proving contract shape, path safety, domain isolation, and absence of Legal/Process schema coupling.
- Preserve all existing PDF-to-Markdown behavior and dependencies.

## Capabilities

### New Capabilities

- `contract-harness`: Cross-domain types and guards required by later pipeline stages.

### Modified Capabilities

- None.

## Impact

The change is purely additive: one production module, one test module, and OpenSpec artifacts. Existing conversion modules, tests, dependencies, prompts, and frozen documentation remain unchanged. ITP ingestion, evidence storage, critical-data rules, Quality Gate behavior, domain routing, producers, domain schemas, and retrieval remain deferred to later stages.
