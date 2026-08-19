## Why

Stage 1 established the shared contract harness (Actor grammar, safe-path primitive, Zero-Write guard). The FROZEN baselines (Technical Spec §18 "Stage 2"; ITP decision memo) require the ingress chain — ITP/Ingress → Preflight → official receiver SHA-256 → Evidence Preservation — before Phase 1 conversion can consume preserved evidence. Today the repository has no ITP/1.0 envelope parser, no archive-security preflight, no ingress state store, and no Object Storage preservation seam: a PDF reaches the converter only through the raw CLI path with no evidence-preservation chain.

## What Changes

- Add `itp.py`: ITP/1.0 manifest parsing/validation (strict UTF-8, JSON, schema, Actor delegation).
- Add `ingress.py`: filesystem inbox discovery, completion-protocol awareness, 13-step preflight per Technical Spec §7.2, archive security per §7.3, bounded/streaming evidence read per §7.4, official SHA-256 + `candidate_sha256` comparison, retry/idempotency state keyed by `handoff_id`.
- Add `evidence.py`: `ObjectStorageGateway` protocol seam (`put(bytes) -> stable resolvable reference`) with a local filesystem adapter behind it; preservation strictly after physical validations and before Phase 1.
- Extend `config.py` with `IngressConfig`/`PreflightLimits` following the existing frozen-dataclass + `from_env()` convention; all numeric/path values are documented Implementation Choices (no FROZEN numeric constants exist).
- Reuse Stage 1 contracts: `contracts.validate_actor`/`parse_actor` for `collector`, `contracts.resolve_safe_path` for member-name safety, `hashing.sha256_file`, `inspector.open_pdf` for structural PDF validation. No second Actor grammar, no second safe-path primitive, no duplicate PDF-open route.
- Add focused tests covering the FROZEN-authorized positive and hostile/malformed cases (Technical Spec §16.1 ingress list), an integration fixture (§16.2), and a no-bundle-write compliance test (§16.3).
- Add a `.gitignore` entry for the local object-storage root (mirroring the existing `var/tmp/*` pattern) so preserved evidence stays outside Git and outside `/bundle/`.

No conversion behavior, OCR, MarkItDown, Gemini, report schema, Quality Gate, router, producer, retrieval, or FROZEN document changes are made. No write path to `repo_jur/bundle/` is introduced. The CLI Phase-1 invocation path is not rewired (that is Stage 3).

## Capabilities

### New Capabilities

- `itp-ingress-preflight-evidence`: ITP/1.0 envelope ingestion, archive-security preflight, official receiver SHA-256, retry-idempotent ingress state, and evidence preservation behind an Object Storage seam.

### Modified Capabilities

- None. (`config.py` gains Stage 2 configuration without changing existing `RoutingConfig` semantics.)

## Impact

Purely additive: three new production modules (`itp.py`, `ingress.py`, `evidence.py`), an in-place `config.py` extension, focused tests, one `.gitignore` entry, and OpenSpec artifacts. Existing conversion modules, tests, dependencies, prompts, and FROZEN baselines remain unchanged. Stage 3+ (Shared Conversion Core wiring, Critical-Data Validation, Quality Gate, Domain Router, producers, retrieval, indexing) is explicitly not started.
