## Context

Stage 2 sits between external handoff and the shared conversion core:

```text
ITP / Ingress
    → Preflight
    → official receiver SHA-256
    → Evidence Preservation
    → Shared Conversion Core
```

This restores, inside `repo_jur`, the chain that the FROZEN baselines require before any conversion work happens: a collector delivers an ITP/1.0 envelope through the filesystem ingress inbox (Decision Memo — Ingress Transport Protocol v1.0 §5.2, §9.1); Stage 2 preflights the envelope's transport and physical evidence in the FROZEN order (Technical Spec §7.2); it recomputes the official SHA-256 over the exact accepted bytes (Decision Memo §2.4, §8.3); and, only after physical validations pass, it preserves the accepted evidence through the `ObjectStorageGateway` seam before Phase 1 (Decision Memo §11.1, Technical Spec §7.6).

Stage 2 has no authority to publish canonical content into `repo_jur/bundle/`. The chain it restores stops at "evidence preserved, reference resolvable" — it does not produce OKF frontmatter, does not decide `verified`/`status`, does not resolve Duplicate Act Handling, and does not invoke Phase 1 conversion. `juridico-cli` and other collectors retain zero direct write to `/bundle/` (Decision Memo §2.1, Invariant 15), and Stage 2's own operational paths (inbox, quarantine, object storage, ingress state) are guarded outside `/bundle/` by the same Zero-Write boundary (`config.ensure_outside_canonical_bundle`).

## Goals / Non-Goals

### Goals

- Receive ITP/1.0 filesystem handoffs through the configurable inbox and completion protocol.
- Validate transport and physical evidence safely, in the FROZEN preflight order, without executing embedded content.
- Compute the official receiver SHA-256 over the exact accepted evidence bytes.
- Preserve accepted evidence before Phase 1, through the `ObjectStorageGateway` seam.
- Maintain retry/idempotency state outside `bundle/`, keyed by `handoff_id`.
- Reuse Stage 1 shared contracts (`contracts.validate_actor`, `contracts.resolve_safe_path`, `hashing.sha256_file`) rather than duplicating them.
- Preserve Zero-Write isolation: no Stage 2 operational path or write targets `repo_jur/bundle/`.

### Non-Goals

- Stage 3 Shared Conversion Core.
- Conversion.
- MarkItDown implementation work.
- OCR/Gemini behavior.
- Post-OCR critical-data validation.
- Phase 1 Quality Gate.
- Domain Router.
- Legal Knowledge Producer.
- Judicial Process Pipeline.
- Semantic Review.
- YAML/frontmatter.
- OKF canonical production.
- Retrieval/indexing/chunking/reranking.
- Stable Concept Identity changes.

Conversion and OCR are mentioned only to state that they are out of scope for this design: Phase 1 remains engine-neutral with respect to Stage 2 (Decision Memo §2.14), and no MarkItDown/OCR/Gemini behavior is introduced or altered here.

## Decisions

### 1. ITP/1.0 uses a single-evidence ZIP envelope with exactly `manifest.json` and `evidence.pdf`

The envelope format is FROZEN as a versioned ZIP containing exactly two root members (Decision Memo §5.1, §6.1). `itp.py`/`ingress.py` implement this literally: `_EXPECTED_MEMBERS = {"manifest.json", "evidence.pdf"}` and `_validate_member_names` rejects any archive whose member set differs. Single-evidence-per-envelope is a deliberate FROZEN constraint (Decision Memo §6.3) that keeps transport cardinality separate from concept cardinality; no alternative multi-evidence envelope was considered in this design, because the baseline already closed that question.

### 2. Filesystem ingress is configurable and outside `bundle/`, using the partial→rename completion protocol

The delivery channel is the FROZEN "filesystem ingress inbox, local, configurable, outside `/bundle/`" (Decision Memo §5.2). The completion protocol — `<inbox>/<handoff_id>.partial` → complete close → same-filesystem atomic rename → `<inbox>/<handoff_id>.zip` — is FROZEN (Technical Spec §7.1, Decision Memo §9.1) because ZIP format alone does not guarantee atomicity (Decision Memo §9.1, §15.3). `IngressConfig.inbox_dir` (config.py) is configurable via `from_env()`; `discover_ready_envelopes` only lists `.zip` suffixed files and therefore never observes `.partial` names. No absolute inbox path is architecturally required (Technical Spec §7.1), consistent with `inbox_dir`'s default being a relative, overridable path.

### 3. Preflight follows the FROZEN ordered 13-step sequence from Technical Spec §7.2

`ingress.preflight_envelope` executes the steps in the exact FROZEN order: ZIP container validation and central-directory inspection (steps 1–2), member-name validation (step 3, `_validate_member_names`), encryption/special-member validation and configurable size/ratio limits (steps 4–5, `_validate_member_metadata`), bounded manifest read and strict UTF-8/JSON/ITP-schema parse (steps 6–8, `_bounded_read` + `itp.parse_manifest`), bounded/streaming evidence read (step 9, `_stream_to_temporary`), official receiver SHA-256 (step 10, `hashing.sha256_file`), candidate hash comparison (step 11), structural PDF compatibility validation (step 12, `inspector.open_pdf`), and accepted evidence preservation (step 13, `storage.put`). The implementation's inline numbered comments mirror this order directly; no reordering or step substitution was introduced.

### 4. Stage 1 contracts are reused for Actor validation and safe-path resolution

`itp.parse_manifest` delegates `collector` to `contracts.validate_actor`, and `ingress._validate_member_names` delegates member-name safety to `contracts.resolve_safe_path`, per the contract-harness spec's canonical Actor forms (`human:<id>`, `process:<id>`, `<producer>/<version>`) and safe-evidence-reference guard. This avoids a second Actor grammar or safe-path implementation, matching both the proposal's stated constraint and the Stage 1 contract-harness spec's requirement that shared primitives be reused by future stages.

### 5. Archive security rejects the FROZEN prohibited cases with configurable numeric limits

`_validate_member_names` and `_validate_member_metadata` reject every case enumerated in Technical Spec §7.3 and Decision Memo §6.1/§10: invalid ZIP, encrypted members, non-`{manifest.json, evidence.pdf}` members, duplicate names, normalized-name collisions, absolute paths and traversal (via `resolve_safe_path`), directories, symlinks/hardlinks/special members, unsupported compression methods, and configured compressed-size, uncompressed-size, compression-ratio, and manifest-size violations. `PreflightLimits` (config.py) carries these four limits as `dataclass(frozen=True)` fields with `from_env()` overrides; the numeric defaults (e.g., `max_compressed_bytes=268_435_456`) are Implementation Choices, not FROZEN values — the baseline explicitly declines to freeze a global size constant such as 100 MB (Decision Memo §10.9, Technical Spec §7.3).

### 6. Evidence processing is bounded/streaming, with quarantine outside `bundle/`

Per Technical Spec §7.4 and Decision Memo §10.10, whole-file reads are avoided where streaming is feasible: `_bounded_read` caps the manifest read at `limits.max_manifest_bytes`, and `_stream_to_temporary` streams `evidence.pdf` in `_CHUNK_SIZE` increments into a `tempfile.mkstemp`-created file under `config.quarantine_dir`, enforcing `max_uncompressed_bytes` as it streams and failing closed if the limit is exceeded. The temporary file is unlinked in `preflight_envelope`'s `finally` block regardless of outcome, matching the FROZEN requirement that quarantine artifacts stay outside `/bundle/` and are cleaned up (Decision Memo §10.13, Technical Spec §7.4).

### 7. The official SHA-256 is recalculated by repo_jur over the exact accepted bytes

`official_sha256 = sha256_file(temporary_path)` is computed by the receiver over the bytes actually streamed to quarantine, per Decision Memo §2.4/§8.3/Invariant 6. `candidate_sha256`, when present, is compared only after the official hash is known (step 11) and a mismatch is rejected as a physical handoff inconsistency (Decision Memo §7.6, spec.md "Candidate SHA-256 mismatch is rejected"); its absence proceeds. A known official hash does not cause rejection or automatic canonical No-Op/concept fusion — `_reuse_or_conflict` only compares hash and manifest semantic fingerprint against this Stage 2's own prior ingress state, never against unrelated concepts, matching Decision Memo §8.4/Invariant 7 that hash identity is physical, not legal/concept identity.

### 8. Existing `inspector.open_pdf` is reused for structural PDF validation

Step 12 calls `inspector.open_pdf(temporary_path)` and relies on its existing `PdfInspectionError` semantics for encrypted, empty, and invalid PDFs, rather than adding a second PDF-open route. This satisfies Technical Spec §7.5 (`%PDF-` magic bytes alone are insufficient; validation must use a safe structural open/parse route that does not execute scripts, macros, attachments, or embedded active content) by reusing a route that already meets that bar, per the proposal's explicit "no duplicate PDF-open route" constraint.

### 9. Evidence Preservation occurs only after physical validations and before Phase 1

Preservation (step 13, `storage.put(accepted_bytes, content_type=manifest.media_type)`) is the last preflight step, executed only after container, member, manifest, hash, and structural-PDF validations succeed, and only for evidence not already preserved for an equivalent prior handoff. This matches the FROZEN ordering "accepted exact bytes → `ObjectStorageGateway.put(...)` → stable resolvable reference" occurring "after necessary physical validations" (Technical Spec §7.6, Decision Memo §11.1) and before any Phase 1 conversion.

### 10. `ObjectStorageGateway` is the architectural seam; the local filesystem adapter is a current Implementation Choice

`evidence.py` defines `ObjectStorageGateway` as a `Protocol` with a single `put(data: bytes, *, content_type: str) -> str` method, and `LocalFilesystemObjectStorageGateway` as one adapter behind it, using content-addressed filenames under a configurable, gitignored root (`IngressConfig.object_storage_root`) with an mkstemp + `os.replace` atomic write. Per Decision Memo §11.2/Invariant 13 and Technical Spec §7.6, provider, bucket, URI scheme, object key, and physical filename are explicitly not FROZEN; the local adapter is a substitutable implementation behind the seam, not an architectural commitment. No alternative Object Storage backend was implemented in this stage — none is required by the FROZEN sources at this point, and the proposal scopes Stage 2 to the seam plus one adapter.

### 11. Ingress operational state remains outside `bundle/`, keyed by `handoff_id`, with semantic-fingerprint + official-SHA retry equivalence

`_state_path`/`_load_prior`/`_write_state` persist state under `config.ingress_state_dir` (outside `bundle/`, guarded by `ensure_outside_canonical_bundle`), keyed by a SHA-256 of `handoff_id`. `_reuse_or_conflict` treats a retry as equivalent only when both `manifest_semantic_fingerprint` (from `ITPManifest.semantic_fingerprint`, a canonical JSON hash over the manifest's normative fields) and `official_evidence_sha256` match the prior record; an equivalent retry returns the prior `evidence_reference` (`reused=True`) without re-executing preservation, while any mismatch raises `HandoffConflictError`. This matches Decision Memo §9.2/Invariant 5: `handoff_id` identifies transport/retry, not concept identity, and idempotency requires handoff_id + unchanged manifest + unchanged official SHA, never the ZIP container hash (Decision Memo §9.3/Invariant explicitly excludes ZIP-hash as a normative idempotency key — no ZIP-level hash is computed or stored by this implementation).

### 12. Zero-Write protection prevents Stage 2 operational paths from targeting `repo_jur/bundle/`

`config.ensure_outside_canonical_bundle` resolves a candidate path and raises `ValueError` if it equals or is nested under the repository's `bundle/` directory; `IngressConfig.__post_init__` applies this guard to every one of its four directory fields, and `LocalFilesystemObjectStorageGateway.__init__` applies it again to its storage root. This directly implements the FROZEN Zero-Write requirement that collectors and Stage 2 mechanisms never write to `/bundle/` (Decision Memo §2.1/§10.15/Invariant 15; contract-harness spec "Only the Legal Knowledge domain may target the Legal bundle").

### 13. Accepted evidence is preserved byte-for-byte without rewriting, semantic correction, summarization, or enrichment

`preflight_envelope` reads `accepted_bytes = temporary_path.read_bytes()` — the exact bytes streamed and hashed in prior steps — and passes them unmodified to `storage.put`. No transformation, normalization, or content inspection occurs between hashing and preservation. This matches the FROZEN requirement that the storage layer preserve exactly what was accepted (Decision Memo §11.1, spec.md "Preserved bytes and hash are identical to the accepted bytes").

## Risks / Trade-offs

- **Whole-PDF memory pressure at the final preservation boundary.** `ObjectStorageGateway.put` accepts `bytes`, so `preflight_envelope` calls `temporary_path.read_bytes()` before calling `storage.put`, loading the full accepted evidence into memory at that one boundary even though earlier steps (manifest read, evidence streaming, hashing) are bounded/streaming. Mitigation: this is bounded by `limits.max_uncompressed_bytes`, the same configured ingress limit that bounds streaming earlier in the same preflight run, so the in-memory size is capped by policy even though the interface itself is bytes-based. This remains a known implementation trade-off of the current `ObjectStorageGateway.put` signature.

- **Local filesystem Object Storage adapter is not an architectural dependency.** `LocalFilesystemObjectStorageGateway` is one adapter behind the `ObjectStorageGateway` protocol. Mitigation: the seam (`put(bytes) -> str`) is the only contract `ingress.py` depends on; a different adapter (any provider, bucket, URI scheme, or object-key convention) can replace it without changing `ingress.py`, per Decision Memo §11.2.

- **Ingress state is operational, not canonical, and must never leak transport metadata into OKF metadata.** The persisted state (`handoff_id`, manifest semantic fingerprint, official SHA-256, stored evidence reference, timestamp) lives under `ingress_state_dir`, outside `bundle/`, and nothing in `ingress.py` writes it into any canonical/frontmatter structure. Mitigation: Zero-Write guard (`ensure_outside_canonical_bundle`) applies to `ingress_state_dir` itself, and `handoff_id`/transport result codes are, per FROZEN Invariant 18, never automatically converted into OKF canonical metadata — no code path in Stage 2 performs such a conversion.

- **Physical hash equality must never be treated automatically as legal identity or canonical duplicate resolution.** `_reuse_or_conflict` uses official SHA-256 equality only to decide transport-level retry reuse for the *same* `handoff_id`; it never compares a new handoff's hash against other handoffs' evidence or existing concepts, and it never triggers a canonical No-Op or concept fusion. Mitigation: this scope limitation is structural — the only state consulted is the single prior record for that `handoff_id`, per Decision Memo §8.4.

- **Filesystem completion atomicity depends on same-filesystem rename.** The `.partial` → `.zip` completion protocol (Technical Spec §7.1) is only atomic when the producer's rename occurs on the same filesystem as the inbox; `ingress.py` does not (and per the FROZEN decision, need not) enforce this on the producer side, since Stage 2 only observes finalized `.zip` names. Mitigation: `discover_ready_envelopes` only lists `.zip`-suffixed files, so a `.partial` file left by a non-atomic or interrupted write is never treated as ready regardless of the producer's rename guarantee.

## Migration Plan

Stage 2 is purely additive: `itp.py`, `ingress.py`, and `evidence.py` are new production modules, and `config.py` gains `IngressConfig`/`PreflightLimits` alongside the existing `RoutingConfig` without changing `RoutingConfig`'s semantics. No existing Phase 1 conversion behavior changes — the CLI's Phase-1 invocation path is not rewired by this stage. No new dependency was added; the implementation uses only the stdlib `zipfile`/`json`/`hashlib`/`tempfile` plus existing Stage 1 modules (`contracts`, `hashing`, `inspector`). No canonical `bundle/` content is migrated, created, or touched. No FROZEN document is modified by this change. Stage 3 (Shared Conversion Core) will later consume the preserved evidence reference returned by `PreflightResult.evidence_reference`; wiring that consumption is explicitly out of scope here.

## Open Questions

No new Stage 2 architectural decision is opened by this design. This document records decisions already made and implemented; it does not raise or resolve any FROZEN Open Decision.

The following remain identified Implementation Choices, not open architecture blockers: the Object Storage provider, bucket, URI scheme, and object-key convention (currently the local filesystem, content-addressed adapter in `evidence.py`, replaceable behind the `ObjectStorageGateway` seam per Decision Memo §11.2); the specific numeric values of `PreflightLimits` and the default paths in `IngressConfig` (both explicitly non-FROZEN per Decision Memo §10.9 and Technical Spec §7.3). The current consolidated FROZEN architecture records the Phase 1 Quality Gate as CLOSED; this Stage 2 design does not reopen it or any other closed architectural decision.
