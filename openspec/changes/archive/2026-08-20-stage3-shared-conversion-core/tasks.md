## 1. Focused Stage 3 tests (TDD — red first)

- [x] 1.1 Write failing tests for `resolve_evidence_reference()`: valid `file://` URI resolves to a readable local path; missing or unreadable target raises `EvidenceReferenceError`; malformed reference raises `EvidenceReferenceError`.
- [x] 1.2 Write failing tests for `ConversionConfig` and `Phase1Artifacts` construction (dataclass shape, frozen immutability, defaults mirroring `convert_document` keyword arguments).
- [x] 1.3 Write failing facade equivalence tests: for the same PDF evidence and equivalent configuration, `ConversionEngine.convert()` literal Markdown equals the direct `convert_document()` literal Markdown across textual, scanned (OCR-required), mixed and blank-page PDFs, including OCR fallback behavior, modulo the single FROZEN-required removal of the canonical `<!-- método: ... -->` method comments from the facade Markdown body.
- [x] 1.4 Write failing tests that technical routing/method metadata never remains inside the literal Markdown body exposed by the facade: for representative page methods (`texto_nativo`, `ocr_integral`, `hibrido`, `vazia`, `erro`), the facade Markdown contains no `<!-- método: ... -->` comment (and no equivalent technical routing comment) while preserving all literal source content and the canonical `[[Pág. N]]` marker sequence; the per-page method remains recorded in the technical report.
- [x] 1.5 Write failing test that an unresolvable evidence reference produces no successful-execution artifact and no write under `repo_jur/bundle/`.

## 2. Minimal implementation

- [x] 2.1 Implement `src/pipeline_juridico/conversion_engine.py` with `EvidenceReferenceError`, `resolve_evidence_reference()` (local `file://` support as an implementation choice), `ConversionConfig`, `Phase1Artifacts` and the thin `ConversionEngine` facade.
- [x] 2.2 The facade delegates entirely to the existing `convert_document()` (reusing routing, engines, cleaner, validator, report serializer) and serializes/validates the technical report through the existing `build_report_json` / `validate_report_contract`; `output_path` is passed as a synthetic label derived from the resolved evidence, never as a publish target.
- [x] 2.3 The facade normalizes the converter's returned Markdown at the boundary: it removes exactly the canonical `<!-- método: ... -->` comments immediately following `[[Pág. N]]` markers (preserving marker sequence and literal source content, applying no other transformation) before exposing `Phase1Artifacts.markdown`; `convert_document()` and the CLI remain unchanged.
- [x] 2.4 Keep the facade domain-neutral: it must not construct, import or assign `GateState`, `RouteTarget` or `CriticalValidationResult`, and must not write to `repo_jur/bundle/`.

## 3. Stage 2 → Stage 3 integration

- [x] 3.1 Add an integration test that runs the Stage 2 `preflight_envelope()` (with `LocalFilesystemObjectStorageGateway`) and feeds the resulting `PreflightResult.evidence_reference` into `ConversionEngine.convert()`, asserting equivalent Markdown and a contract-valid report with correct SHA-256 / byte size / page count traceability.

## 4. Validation

- [x] 4.1 Run focused Stage 3 tests (`uv run pytest tests/test_conversion_engine.py -v`) — all green.
- [x] 4.2 Run the full regression suite (`uv run pytest tests/`) — all 486 existing tests plus new Stage 3 tests pass with no converter behavioral regression.
- [x] 4.3 Run OpenSpec strict validation (`openspec validate stage3-shared-conversion-core --strict` and `openspec validate --all --strict`) — all passed, 0 failed.
- [x] 4.4 Confirm no FROZEN baseline modification, no `bundle/` write, no Stage 4+ implementation and no dependency change in the final diff.
