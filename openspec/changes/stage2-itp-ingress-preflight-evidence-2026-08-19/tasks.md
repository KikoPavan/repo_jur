## 1. ITP manifest schema (itp.py)

- [x] 1.1 Add failing tests: valid full manifest parses; required-fields-only manifest parses; each missing required field rejected; wrong `protocol_version` rejected; wrong `evidence_reference` rejected; `media_type` != `application/pdf` rejected; non-positive `byte_size` rejected; malformed `candidate_sha256` rejected; `collector` delegation rejects malformed Actors and accepts all canonical Actor forms (reusing Stage 1 Actor vectors).
- [x] 1.2 Add failing tests: malformed UTF-8 manifest rejected; malformed JSON rejected; oversized manifest rejected.
- [x] 1.3 Implement `itp.py` minimal schema validation delegating `collector` to `contracts.validate_actor`.

## 2. Archive security and preflight (ingress.py)

- [x] 2.1 Add failing tests for archive security (Technical Spec §16.1 ingress list): exact two-member ZIP accepted; duplicate names rejected; extra member rejected; missing member rejected; encrypted member rejected; traversal member rejected; absolute-path member rejected; directory member rejected; symlink member rejected; unsupported compression method rejected; compressed-size over limit rejected; uncompressed-size over limit rejected; compression-ratio over limit rejected; manifest-size over limit rejected. Member-name safety reuses `contracts.resolve_safe_path`.
- [x] 2.2 Add failing tests: official SHA-256 equals hash of exact accepted bytes; `byte_size` mismatch rejected; `candidate_sha256` mismatch rejected; `candidate_sha256` absent proceeds.
- [x] 2.3 Add failing tests: invalid/encrypted/empty PDF rejected via existing `inspector.open_pdf` semantics (no duplicated PDF-open logic).
- [x] 2.4 Implement `ingress.py` 13-step preflight per Technical Spec §7.2 order using stdlib `zipfile` with bounded/streaming evidence handling (§7.4).

## 3. Evidence preservation (evidence.py)

- [x] 3.1 Add failing tests: `ObjectStorageGateway.put` returns a stable resolvable reference; preserved bytes/hash equal accepted bytes/hash; write is atomic (no partial artifact visible at final name); storage root is outside `/bundle/` and noncanonical (test uses temporary/noncanonical storage only).
- [x] 3.2 Implement `evidence.py` with the gateway protocol seam and a local filesystem adapter (atomic write via the mkstemp + `os.replace` pattern), storage root configurable and gitignored.

## 4. Ingress state and idempotency (ingress.py)

- [x] 4.1 Add failing tests: `.partial` files ignored by discovery; equivalent retry (same `handoff_id` + semantically equivalent manifest + same official SHA) reuses prior result without re-execution; conflicting retry raises handoff-conflict rejection; ingress state lives outside `/bundle/`.
- [x] 4.2 Implement retry/idempotency state keyed by `handoff_id` with semantic fingerprint + official SHA equivalence.

## 5. Integration and compliance

- [x] 5.1 Add an end-to-end deterministic fixture: ITP ZIP → preflight → official SHA-256 → evidence preservation → stable reference (Technical Spec §16.2), asserting byte/hash equality and no `/bundle/` writes (Technical Spec §16.3).
- [x] 5.2 Add a compliance test proving no write occurs under `repo_jur/bundle/` at any point in the flow.

## 6. Verification

- [x] 6.1 Run focused Stage 2 tests (itp/ingress/evidence) and confirm they pass.
- [x] 6.2 Run the complete test suite (421-test baseline + new Stage 2 tests) and confirm no pre-existing behavior regressed.
- [x] 6.3 Run `openspec validate --all --strict` and confirm the Stage 2 change validates.
- [x] 6.4 Confirm FROZEN documents, `var/ocr_final/`, and `bundle/` are untouched; confirm no new dependencies were added.
