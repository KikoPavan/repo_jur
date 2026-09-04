# Proposal: Operational Intake Queue Lifecycle + SHA-256 Registry

## Context
The current pipeline receives documents primarily through ITP envelopes in `var/ingress/inbox`. To support raw PDF intake from `input/`, we need a robust management layer that ensures binary deduplication (SHA-256), atomic state transitions, and a deterministic path from raw PDF to the FROZEN Ingress entry point.

## Objectives
- Transform `input/` into a managed operational entry point with strict concurrency safety.
- Implement a SHA-256 registry for operational deduplication and lifecycle tracking.
- Automate ITP envelope creation (`manifest.json` + `evidence.pdf`) for raw PDFs.
- Use explicit operational classification via subdirectories (`legislacao/`, `jurisprudencia/`, etc.).
- Ensure full recovery and state reconciliation after process interruptions using a strong lease mechanism.
- Maintain Zero-Write isolation from the canonical `bundle/` within the Intake layer, delegating publication to the public Producer API.

## Scope
### In Scope
- Safe "Claim" of PDFs from classified subdirectories.
- Reporting of unclassified PDFs in `input/` root as `SKIP_UNCLASSIFIED`.
- SHA-256 calculation and registry lookup.
- Automatic ITP Envelope Builder (immutable manifest generation per occurrence).
- Coordination of the full flow: Intake -> Ingress -> Phase 1 -> Router -> Semantic Review -> Producer.
- Proper handling of `ProducerRunResult` and `HUMAN_REVIEW` states.
- State transitions: `PROCESSING` → `PRESERVED` → `PUBLISHED`.
- Reconciler for recovery after crash/interruption using execution identity and heartbeat.
- CLI commands: `intake add`, `intake scan`, `intake status`, `intake retry`.

### Out of Scope
- Altering the frozen `itp-ingress-preflight-evidence` specification.
- Direct writes to `bundle/` (delegated to Producer).
- Automatic retries for `FAILED` documents.

## Proposed Behavior
1. **Intake Add/Discovery**:
   - `intake add <file> --type <tipo>`: Copies file to `input/<tipo>/` safely.
   - `intake scan`: Scans classified subdirectories. Warns about PDFs in root.
2. **Claim/Deduplication**:
   - Calculate SHA-256. Consult `var/intake/registry/<sha256>.json`.
   - If `PUBLISHED`: Verify consistency (evidence in storage + concept in bundle). If inconsistent, move to `FAILED`. If consistent, discard duplicate.
   - If `PROCESSING`/`PRESERVED`: Acquire or verify a lease. If active and owned by another `claim_id`, skip.
3. **Flow Execution**:
   - Build ITP.
   - Run Ingress.
   - Run Phase 1 & Quality Gate.
   - Run Domain Router.
   - Run Semantic Review.
   - Run **Public Producer API (`produce`)**.
4. **Completion**:
   - Success (`NEW_CONCEPT`, `REGENERATE`, `NOOP`) -> Mark `PUBLISHED`. Cleanup `processing/`.
   - `HUMAN_REVIEW` -> Mark `PRESERVED` for manual action. Keep copy.
   - Failure -> Mark `FAILED`. Move to `failed/`.

## Success Criteria
- No TOCTOU during file claim.
- Correct mapping of directories to `LegalConceptType`.
- Zero-Write in `bundle/` by Intake code itself.
- Deterministic recovery path surviving crashes.
