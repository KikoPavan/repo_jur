# Tasks: Post-OCR Markdown Normalization ✨

## Phase 1: OpenSpec & Design 📝
- [x] T1: Audit proposal and design
- [x] T2: Create delta specs
- [x] T3: Validate OpenSpec artifacts: `openspec validate --all --strict`

## Phase 2: Tests (RED) 🔴
- [x] T4: Create unit tests for `normalize_technical_artifacts` in `tests/test_cleaner_artifacts.py`
- [x] T5: Update Quality Gate tests to check for new forbidden artifacts in `tests/test_quality_gate_artifacts.py`
- [x] T6: Create E2E test scenario with mixed native/OCR content containing residues

## Phase 3: Implementation (GREEN) 🟢
- [x] T7: Implement `normalize_technical_artifacts` in `src/pipeline_juridico/cleaner.py`
- [x] T8: Integrate normalizer into `src/pipeline_juridico/converter.py`
- [x] T9: Update `src/pipeline_juridico/quality_gate.py` to fail on new forbidden artifacts

## Phase 4: Validation (REFACTOR) 🔵
- [x] T10: Run all tests: `uv run pytest tests/`
- [x] T11: Verify conformance: `repo-jur test conformance` (if available)
- [x] T12: Final OpenSpec validation: `openspec validate --all --strict`
- [x] T13: Git check: `git diff --check`

## Phase 5: Closure 🏁
- [x] T14: Update operational documentation
- [x] T15: Archive change: `openspec archive post-ocr-markdown-normalization`
- [x] T16: Final report and push
