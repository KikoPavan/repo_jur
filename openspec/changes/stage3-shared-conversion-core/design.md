## Context

Stage 2 established the conformant ingress chain through evidence preservation and now returns a stable, resolvable `evidence_reference`. The repository already contains a stabilized PDF-to-Markdown implementation under `src/pipeline_juridico/`, centered on the existing direct conversion entry point and its supporting routing, extraction, OCR, cleaning, validation, reporting and CLI behavior.

The FROZEN architecture requires Stage 3 to expose that implementation as one domain-neutral Shared Conversion Core behind a `ConversionEngine` boundary. It explicitly does not require a converter rewrite, duplicate package tree, physical relocation or engine replacement.

The current preserved-evidence implementation returns a stable local `file://` URI, while the architectural contract deliberately does not freeze a storage provider, bucket, URI scheme or object-key convention. The Stage 3 design therefore needs to consume the current implementation without promoting its local URI representation to an architectural requirement.

The current converter returns Markdown plus the existing technical report model. The CLI serializes that report to JSON and validates the existing report contract. Stage 3 must expose literal Markdown and technical information separately while leaving post-OCR critical-data validation, the complete Phase 1 Quality Gate and domain routing to their later owning stages.

Runtime: the project declares `requires-python = ">=3.12"` and is managed with `uv` under the existing `src/pipeline_juridico/` layout; the worktree validation environment executes under Python 3.13.11, which satisfies the declared constraint. MarkItDown / markitdown-ocr and the current Gemini-compatible OCR client remain implementation choices rather than architectural dependencies.

## Goals / Non-Goals

**Goals:**

- expose the existing converter through one minimal `ConversionEngine` facade;
- consume a preserved evidence reference rather than treating an arbitrary caller PDF path as the Shared Conversion Core contract;
- reuse the existing `convert_document()` behavior in place;
- provide a minimal engine-neutral `Phase1Artifacts` result containing literal Markdown and the existing serialized technical report;
- preserve canonical page markers and all existing conversion/OCR behavior;
- keep technical routing, OCR provider/model information, warnings, errors and telemetry outside the Markdown body;
- retain physical traceability to the exact resolved evidence;
- allow evidence-reference resolution to vary independently from conversion-engine behavior;
- preserve the current direct CLI/converter path without a breaking change;
- add focused Stage 3 tests plus regression coverage over the stabilized converter.

**Non-Goals:**

- rewriting or relocating the converter;
- creating a parallel `pipeline/shared_conversion/` implementation;
- changing MarkItDown, markitdown-ocr, Gemini-compatible OCR behavior or routing thresholds;
- changing cleaner behavior or existing textual reconstruction rules;
- redesigning ITP, Preflight, Evidence Preservation or Object Storage;
- defining a universal Object Storage URI scheme or provider;
- implementing post-OCR critical-data validation;
- implementing or assigning PASS / PASS WITH WARNINGS / FAIL Quality Gate semantics;
- correcting older `juridical-pdf-conversion` requirements owned by later Phase 1 / Quality Gate reconciliation;
- implementing Domain Router, Legal Knowledge or Judicial Process schemas;
- implementing Semantic Review, Producer, canonical publication or retrieval;
- writing anything to `/bundle/`.

## Decisions

### 1. Reuse the current converter behind a thin facade

Stage 3 will keep the existing conversion implementation in `src/pipeline_juridico/` and introduce only a thin facade that satisfies the logical `ConversionEngine` boundary.

The facade delegates conversion to the existing direct converter instead of copying its routing, OCR, cleaning, validation or report-generation logic.

**Rationale:** this preserves the already-tested converter as the single implementation of PDF-to-Markdown behavior and satisfies the FROZEN `REUSE → ADAPT IN PLACE → TEST` rule.

**Alternative considered:** create a new shared-conversion package and migrate conversion logic into it.

**Rejected because:** it would duplicate or relocate stabilized behavior solely to satisfy an architectural name, increasing regression risk without adding capability.

### 2. Keep evidence-reference resolution separate from conversion

`ConversionEngine` will receive an evidence reference and use a plain module-level `resolve_evidence_reference()` function (in the facade module) to obtain a readable local PDF path for the existing converter.

The Stage 3 implementation will support the stable `file://` reference produced by the current local evidence-storage adapter. That support is an implementation choice, not part of the architectural contract.

The converter itself will continue to operate on a local PDF path after resolution; it will not become responsible for Object Storage transport or provider-specific retrieval.

**Rationale:** evidence location/resolution and PDF conversion are separate responsibilities. This permits the current local adapter to work immediately while leaving future storage implementations free to provide another resolver without modifying conversion behavior.

**Alternative considered:** parse `file://` directly inside `convert_document()`.

**Rejected because:** that would couple the stabilized converter to the current storage representation and promote a local implementation choice into conversion logic.

**Alternative considered:** define a universal provider/URI abstraction in Stage 3.

**Rejected because:** provider, bucket, URI scheme and object key are explicitly unfrozen implementation choices; Stage 3 has no authority to select them.

### 3. Introduce a minimal conversion configuration object

The facade will receive one conversion configuration value that packages the operational arguments already required by the existing converter, including temporary-output configuration, OCR enablement/configuration, routing configuration and other current execution options.

The facade will pass these values through without redefining their existing semantics.

`convert_document()` requires the `output_path` keyword argument, but Stage 3 does not publish or write output: `output_path` is used only as the `SaidaInfo.path` metadata label inside the technical report and is never read or written by the converter. The facade SHALL synthesize that label from the resolved evidence reference (e.g. the resolved evidence path with a `.md` suffix) and SHALL NOT treat it as a real publish target or derive it from legacy CLI output directories.

In particular, any existing `allow_partial` behavior remains a legacy converter configuration concern in Stage 3 and SHALL NOT be interpreted by the facade as the future Phase 1 Quality Gate contract.

**Rationale:** the FROZEN logical boundary requires `convert(evidence_ref, config)` and a typed configuration avoids expanding the facade into a long list of implementation-specific parameters.

**Alternative considered:** expose every existing converter keyword argument directly on the facade.

**Rejected because:** that would make the architectural boundary unnecessarily mirror the concrete function signature and make later implementation substitution harder.

### 4. Make `Phase1Artifacts` a minimal engine-neutral result

The Stage 3 result will contain:

- literal Markdown;
- serialized technical JSON produced through the existing report serializer and validated through the existing report contract.

It will not contain a Stage 4 critical-validation result, Stage 5 Quality Gate state, bounded-context route, domain schema, Producer result or canonical publication reference.

The facade will not expose the existing concrete report dataclass as the architectural result type.

**Rationale:** Markdown plus JSON preserves the required separation between body and technical information while avoiding coupling downstream stages to the current in-memory report implementation.

**Alternative considered:** return the existing report dataclass directly.

**Rejected because:** it would unnecessarily couple the Shared Conversion Core boundary to one concrete implementation model.

**Alternative considered:** redesign the report now to the complete final FROZEN Phase 1 Technical JSON shape.

**Rejected because:** Stage 3 is responsible for the shared conversion boundary. Full Quality Gate semantics and remaining Phase 1 reconciliation belong to their owning later stage and must not be pulled forward implicitly.

### 5. Normalize technical routing/method metadata at the shared boundary

The existing converter embeds a technical routing/method comment after every canonical page marker (`[[Pág. N]]\n<!-- método: <método> -->`) because the converter's own internal validation (`validate_page_markers`, `validate_markdown_matches_report`) requires that comment. The FROZEN Stage 3 contract requires technical routing/method metadata to stay outside the literal body. Therefore the facade SHALL normalize the converter's returned Markdown at the boundary: it SHALL remove exactly the canonical `<!-- método: ... -->` comments that immediately follow `[[Pág. N]]` markers, preserving the marker sequence and all literal source content, and SHALL NOT apply any other transformation.

The per-page method continues to be recorded in the technical conversion report (`report["pages"][i]["method"]`), so no conversion information is lost. The existing converter and CLI remain unchanged: adapter-only normalization satisfies the FROZEN contract, so `convert_document()` and the CLI are not modified.

The normalization SHALL be implemented as a small, targeted function in the facade module with its own focused tests, including representative page methods (`texto_nativo`, `ocr_integral`, `hibrido`, `vazia`, `erro`).

**Rationale:** the FROZEN contract separates literal body from technical metadata; removing the method comment at the boundary keeps the stabilized converter (whose validator requires the comment) untouched and preserves the direct CLI/converter compatibility invariant.

**Alternative considered:** modify `convert_document()`/`compose_document()` to stop emitting the comment.
**Rejected because:** the comment is part of the existing converter's validated output contract; changing the converter or CLI would violate the "no unrelated converter refactor" exclusion and break existing regression/validation behavior that relies on the comment.

**Alternative considered:** return the raw converter Markdown including the comment and document it as technical metadata.
**Rejected because:** the FROZEN contract explicitly requires technical routing/method metadata outside the literal body; leaving it inside would be a conformance defect.

### 6. Preserve existing conversion behavior as the regression oracle

The Stage 3 facade will not implement page routing, OCR fallback, page-marker construction, cleaning or validation itself. Tests will compare facade results against the existing direct conversion behavior using equivalent inputs and configuration.

Regression coverage will include controlled cases for:

- textual PDF;
- scanned/OCR-required PDF;
- mixed PDF;
- blank page;
- OCR fallback behavior;
- marker ordering;
- absence of technical routing/method metadata in the facade Markdown body (equivalence is asserted modulo the single FROZEN-required method-comment normalization).

Existing deterministic conversion tests remain authoritative for the converter internals.

**Rationale:** Stage 3 is an integration boundary change, not a conversion-algorithm change.

**Alternative considered:** recreate selected conversion logic inside facade-level tests/mocks.

**Rejected because:** duplicating expected implementation logic in the facade would weaken the guarantee that there remains only one Shared Conversion Core.

### 7. Keep CLI compatibility during Stage 3

The existing CLI will remain functional and its direct `convert_document()` usage will not be removed in this change.

Stage 3 may add integration coverage proving that the new facade can consume Stage 2 output, but it will not require a breaking CLI migration as a condition of introducing the Shared Conversion Core.

A later deliberate change may choose to route production orchestration through the facade once downstream Phase 1 stages are complete.

**Rationale:** the architectural requirement is to expose the existing implementation behind `ConversionEngine`, not to break or prematurely replace the stabilized operator interface.

**Alternative considered:** immediately rewrite the CLI to require Stage 2 handoff input.

**Rejected because:** that would mix Stage 3 boundary work with operator-interface and pipeline-orchestration changes outside the minimum required scope.

### 8. Preserve module responsibility boundaries

The existing separation remains:

- conversion orchestration stays with the converter implementation;
- page routing stays in the routing layer;
- extraction/OCR engines stay behind their current engine abstractions;
- cleaning stays in the cleaner;
- validation stays in validation code;
- report serialization/validation stays in reporting code;
- CLI remains the operator-facing adapter.

Stage 3 adds a facade/result/configuration boundary around these existing responsibilities rather than merging them.

**Rationale:** this minimizes code movement and keeps changes independently testable.

## Risks / Trade-offs

- **[Risk] The current `file://` resolver could be mistaken for the architectural storage contract.**
  → Mitigation: keep evidence resolution in a dedicated module-level function and document local URI support explicitly as an implementation choice; future providers may add resolvers without changing the conversion facade contract.

- **[Risk] Boundary normalization could accidentally alter literal source content or page markers.**
  → Mitigation: the normalization is a single targeted function that removes only the canonical `<!-- método: ... -->` comment lines immediately following `[[Pág. N]]` markers and applies no other transformation; focused tests cover representative page methods and marker preservation, and facade/direct equivalence is asserted modulo exactly this normalization.

- **[Risk] Wrapping the converter could accidentally change Markdown or page outcomes.**
  → Mitigation: delegate directly to the existing converter and compare facade/direct results under equivalent configuration.

- **[Risk] The current technical JSON is not yet the complete final Phase 1 / Quality Gate contract described by later FROZEN baselines.**
  → Mitigation: preserve and expose the existing validated technical report in Stage 3; do not invent missing Quality Gate fields or states. Reconciliation remains with the owning later stage.

- **[Risk] Existing `allow_partial` behavior could be confused with future Quality Gate success semantics.**
  → Mitigation: Stage 3 treats it only as pass-through legacy conversion configuration and does not map it to PASS / PASS WITH WARNINGS / FAIL.

- **[Risk] An evidence reference may resolve to missing or unreadable content.**
  → Mitigation: fail before successful conversion and perform no canonical publication or downstream routing.

- **[Risk] A future non-local Object Storage implementation cannot supply a local path directly.**
  → Mitigation: keep reference resolution as a dedicated module-level resolver so another resolver can materialize or otherwise provide the local readable evidence required by the current converter without changing the conversion facade contract.

- **[Trade-off] Keeping the existing direct CLI path temporarily means two invocation paths can reach the same converter.**
  → Mitigation: both paths delegate to the same implementation; Stage 3 introduces no second conversion algorithm.

- **[Trade-off] Returning serialized JSON instead of the concrete report object adds serialization at the boundary.**
  → Mitigation: reuse the existing serializer and report-contract validator, producing a representation that is less coupled to the current implementation model.

## Migration Plan

1. Add tests for the new Shared Conversion Core contract before implementation.
2. Add the minimal configuration, artifact and evidence-resolution boundary required by the facade.
3. Add the thin facade that delegates to the existing converter and normalizes the converter's technical routing/method comments out of the exposed literal Markdown at the boundary.
4. Reuse existing technical-report serialization and validation.
5. Add Stage 2 → Stage 3 integration coverage using preserved evidence from the current local storage adapter.
6. Run focused Stage 3 tests.
7. Run the full existing regression suite to prove no converter behavioral regression.
8. Run OpenSpec strict validation.
9. Reconvert the canonical regression corpus with the established no-OCR path when converter-facing behavior is affected and inspect diffs.
10. Do not modify or publish `/bundle/`.

Rollback is limited to removal of the new facade/configuration/artifact/resolution additions because the existing direct converter and CLI remain intact throughout Stage 3.

## Open Questions

No blocking architectural question remains for Stage 3.

Future Object Storage implementations may require a different evidence-reference resolver or materialization mechanism. That is intentionally supported through the dedicated module-level resolver and does not require selecting a provider, URI scheme or transport mechanism in this change.

The final complete Phase 1 Technical JSON / Quality Gate reconciliation remains intentionally deferred to its owning later stage and is not an unresolved Stage 3 decision.
