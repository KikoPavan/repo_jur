# Design: Operational Intake Queue Lifecycle

## Architecture
The Intake layer is the operational gateway. It transforms raw PDFs from classified directories into ITP envelopes and orchestrates the full pipeline using public APIs.

### Directory Structure
```text
input/
├── legislacao/        # → LegalConceptType.Legislacao
├── jurisprudencia/    # → LegalConceptType.Jurisprudencia
├── temas/             # → LegalConceptType.TemaJuridico
└── precedentes/       # → LegalConceptType.PrecedenteVinculante

var/intake/
├── registry/          # <sha256>.json (Metadata + State + Strong Lease)
├── processing/        # <sha256>.pdf (Working copy)
└── failed/            # <sha256>.pdf (Failure preservation)
```

### State Machine & Registry
**States:**
1. **PROCESSING**: PDF claimed, hash recorded. Lease acquired. File moved to `var/intake/processing/`.
2. **PRESERVED**: ITP built, Ingress passed, or `HUMAN_REVIEW` required by Producer.
3. **FAILED**: Explicit failure or inconsistent publication.
4. **PUBLISHED**: Success result from public Producer API (`NEW_CONCEPT`, `REGENERATE`, `NOOP`).

### Flow Orchestration
`Router → LegalSemanticReviewEngine.review(...) → legal_producer.produce(...)`
- The `okf_type` is determined by the input subdirectory.
- The `produce()` API is the only authority for bundle writes and duplicate resolution.

### Strong Lease & Heartbeat
- **Identity**: `claim_id` (UUID) ensures that even if a PID is reused, the new process cannot interfere with a valid lease.
- **Heartbeat**: The `heartbeat_at` is updated at each major stage of orchestration.
- **Enforcement**: Any state transition must verify the `claim_id` against the registry.

### Reconciler
On `intake scan`:
1. Detect stale leases (expired heartbeat or dead owner).
2. For `PROCESSING` or `PRESERVED`: Re-enter `process_entry` with a new `claim_id`.
3. Check for existing artifacts (ZIP, evidence) to avoid redundant work.

### CLI Interface
- `intake add <path> --type <tipo>`: Classified copy.
- `intake scan`: Orquestrated full flow.
- `intake status [--sha <sha>]`: Audit registry.
- `intake retry <sha>`: Manual move from `failed/` back to classified input for re-scan.
