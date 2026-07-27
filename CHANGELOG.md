# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-27

### Added

- Project foundation with `uv` dependency management, `pipeline_juridico` package, and `converter-juridico` CLI entry point.
- Operational directories (`input/`, `output/`, `logs/`, `var/tmp/`) with `.gitkeep` placeholders.
- Environment template (`.env.example`) with pipeline configuration variables.
- Full PDF-to-Markdown conversion pipeline: input inspection and page isolation, per-page routing (`texto_nativo`/`ocr_integral`/`hibrido`/`vazia`/`erro`), native and OCR conversion engines (OCR via Gemini's OpenAI-compatible endpoint), Markdown composition and conservative cleanup, multi-layer validation, atomic output writing, a versioned JSON report, and the `converter-juridico` CLI (`--overwrite`, `--allow-partial`, `--no-ocr`, `--keep-temp`, `--log-level`) with documented exit codes.

### Test suite

- 185 tests passing (`uv run pytest tests/ -v`), covering every module plus end-to-end acceptance scenarios (fully-digital, fully-scanned, and mixed PDFs) and a real, credential-backed OCR call verified manually against a 29-page legal PDF.
