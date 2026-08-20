## Why

Stage 2 now preserves accepted PDF evidence and returns a stable evidence reference before Phase 1, but the existing converter is still exposed only through its direct local-path entry point. The FROZEN architecture requires that this already-stabilized converter be reused behind a domain-neutral `ConversionEngine` boundary so both future bounded contexts consume one Shared Conversion Core without rewriting or duplicating conversion behavior.

## What Changes

- Add the Stage 3 Shared Conversion Core contract around the existing `src/pipeline_juridico/` implementation.
- Add a minimal engine-neutral `ConversionEngine` facade exposing the logical operation `convert(evidence_ref, config) -> Phase1Artifacts`.
- Add the minimal `Phase1Artifacts` boundary needed to return literal Markdown and the existing technical conversion report without introducing Quality Gate semantics.
- Adapt the current implementation path so the `evidence_reference` produced by conformant Stage 2 preservation can be consumed by the current local Object Storage implementation and delegated to the existing `convert_document()` converter.
- Reuse the existing converter, routing, MarkItDown/OCR implementation, cleaning, validation, page markers and report generation; no converter rewrite, duplicate conversion stack, physical relocation or silent engine/provider swap is introduced.
- Normalize the shared-boundary Markdown so the technical routing/method comments emitted by the existing converter (e.g. `<!-- método: ... -->`) do not remain in the literal Markdown body exposed by the Shared Conversion Core, while preserving the literal source content and the canonical `[[Pág. N]]` marker sequence; the existing converter and CLI remain unchanged and the per-page method stays recorded in the technical report.
- Add focused facade/integration tests and regression coverage proving that the Shared Conversion Core preserves existing conversion behavior for textual, scanned, mixed and blank-page PDFs, OCR fallback, marker sequence, and absence of technical routing/method metadata leakage into the literal body.
- Keep conversion/OCR provider and storage-reference representation as Implementation Choices rather than architectural dependencies.
- Do not implement post-OCR critical-data validation, Phase 1 Quality Gate, Domain Router, domain schemas, Semantic Review, Producers, canonical publication or retrieval in this change.

No breaking change is intended to the existing CLI or `convert_document()` entry point.

## Capabilities

### New Capabilities

- `shared-conversion-core`: Defines the domain-neutral Stage 3 boundary that consumes preserved evidence references, delegates PDF-to-literal-Markdown conversion to the existing converter through `ConversionEngine`, and returns Phase 1 conversion artifacts without introducing downstream Quality Gate or domain semantics.

### Modified Capabilities

None.

The existing `juridical-pdf-conversion`, `itp-ingress-preflight-evidence`, and `contract-harness` requirements are not changed by this proposal. Any pre-existing mismatch between older conversion requirements and later FROZEN Phase 1 / Quality Gate baselines remains outside Stage 3 and must be handled by its owning stage or a separately scoped OpenSpec change.

## Impact

- Primary affected code: `src/pipeline_juridico/`, reusing the existing converter in place and adding only the minimal facade/artifact boundary needed for `ConversionEngine`.
- Stage 2 `PreflightResult.evidence_reference` becomes an accepted upstream input to the Shared Conversion Core.
- Existing CLI behavior and direct `convert_document()` usage remain available and are not replaced by this change.
- Existing MarkItDown / markitdown-ocr / Gemini-compatible OCR behavior remains an Implementation Choice and is not changed architecturally.
- No new dependency, storage provider, URI scheme, service, database, credential, canonical bundle write, or domain-specific schema is introduced.
- Stage 4 critical-data validation, Stage 5 Quality Gate, Stage 6 Domain Router, and later bounded-context pipelines remain out of scope.
