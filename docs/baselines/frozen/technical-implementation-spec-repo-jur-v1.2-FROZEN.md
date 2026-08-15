# ESPECIFICAÇÃO DE IMPLEMENTAÇÃO TÉCNICA: `repo_jur`

**Versão:** 1.2 (Baseline corrigida e congelada)  
**Data:** 15 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v15-FROZEN.md`, `external-source-ingestion-contract-v1.6-FROZEN.md`, `legal-okf-profile-v1.3-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `retrieval-contract-v2.8-FROZEN.md`, `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`, `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`, `decision-memo-search-execution-path-v1.0-FROZEN.md`, `decision-memo-chunking-strategy-v1.0-FROZEN.md`, `decision-memo-reranking-pipeline-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md`, `decision-memo-verification-history-schema-v1.0-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md`, `decision-memo-semantic-review-enrichment-layer-v1.1-FROZEN.md`, `decision-memo-post-ocr-critical-data-validation-seam-v1.1-FROZEN.md` e `phase1-operational-spec-v1.1-FROZEN.md`, `decision-memo-physical-layout-logical-capability-mapping-v1.0-FROZEN.md`, `decision-memo-retrieval-bounded-context-scope-v1.0-FROZEN.md`.

---


## 0. Controlled Reconciliation v1.1

Esta versão sucede `technical-implementation-spec-repo-jur-v1.0-FROZEN.md`.

Mudanças controladas:

1. introdução do Shared Conversion Core;
2. split Legal Knowledge / Judicial Process após Quality Gate;
3. Semantic Review / Enrichment pré-Producer em cada domínio;
4. post-OCR critical-data validation seam sem autocorreção;
5. reutilização do conversor já implementado atrás de `ConversionEngine`;
6. registro da implementação atual MarkItDown/markitdown-ocr + Gemini-compatible client apenas como Implementation Choice;
7. separação de schemas YAML e enrichment por domínio;
8. preservação integral das decisões FROZEN de retrieval, lifecycle, identity e publication.

Nenhuma mudança desta versão autoriza Judicial Process a publicar em `repo_jur/bundle/`.

---

## 0A. Controlled Correction v1.2

Esta versão sucede `technical-implementation-spec-repo-jur-v1.1-FROZEN.md`.

Correções:

1. restaura Ingress/Preflight/official SHA/Evidence Preservation explicitamente antes de Shared Conversion;
2. trata package paths como logical targets;
3. reconhece `src/pipeline_juridico/` como implementação física existente do conversor;
4. fortalece invariantes de Semantic Review;
5. restringe Retrieval atual a Legal Knowledge;
6. adiciona provenance/versioning obrigatório para regras de critical-data validation.

Nenhuma mudança exige reorganização física do repositório.

---

## 1. Scope

Esta especificação traduz as baselines FROZEN do `repo_jur` em contratos de software implementáveis.

Ela define:

- componentes;
- interfaces;
- schemas técnicos derivados;
- fluxo de execução;
- regras de sincronização;
- comandos operacionais;
- testes;
- critérios de aceite;
- sequência de implementação.

Ela **não cria novas decisões arquiteturais**.

### 1.1 In Scope

- ITP/1.0 ingress;
- preflight;
- preservação da evidência;
- Phase 1;
- Phase 1 Quality Gate;
- Producer OKF;
- atomic publication;
- lexical retrieval;
- canonical materialization;
- chunking derivado;
- reranking seam;
- sync/rebuild/invalidation;
- observability;
- CLI operacional interno do `repo_jur`;
- testes e acceptance criteria.

### 1.2 Out of Scope

Esta especificação não seleciona:

- vector DB;
- embedding model;
- ANN/HNSW;
- semantic retrieval engine;
- reranker específico;
- Cross-Encoder específico;
- LLM reranker;
- provider de API;
- GPU;
- Object Storage provider.

Também não:

- cria Stable Concept ID;
- cria Stable Chunk ID;
- altera schemas canônicos sem baseline controlada;
- migra bases legadas;
- move o código do sistema externo `juridico-cli` para dentro do `repo_jur`.

---

## 2. Frozen Architecture Mapping

| Área | Baseline FROZEN | Regra de implementação |
|---|---|---|
| Bundle | Arquitetura v13 | `/bundle/` é corpus canônico; código/runtime/cache ficam fora |
| Ingress | ITP/1.0 | envelope ZIP single-evidence + manifest; filesystem inbox |
| Evidence | ESIC / ITP | PDF aceito preservado em Object Storage antes da Phase 1 |
| Phase 1 | Phase1 Operational Spec | Markdown literal + JSON técnico engine-neutral |
| Quality Gate | QG memo | PASS / PASS WITH WARNINGS / FAIL |
| Producer | Architecture / Lifecycle | único publicador canônico |
| Identity | Stable Concept Identity | `concept_id` posicional |
| Duplicate | Duplicate Act Handling | hash físico não equivale a identidade jurídica |
| Retrieval | Retrieval Contract v2.7 | Zero-Write; canonical materialization |
| Search | Search Execution Path | Lexical-First, Hybrid-Ready |
| Chunking | Chunking Strategy | Structural Block-First, Page-Aware, Size-Profiled |
| Reranking | Reranking Pipeline | Optional, Conditional, Profile-Governed, Fail-Open |
| Trust | Retrieval / Verification | relevance e trust separados |

### 2.1 Boundary — `juridico-cli`

`juridico-cli` permanece **sistema externo consumidor/coletor/orquestrador**.

Ele pode:

- descobrir;
- coletar;
- empacotar ITP;
- entregar handoffs;
- consumir retrieval.

Ele **não** reside como aplicação cliente dentro do `repo_jur` e **não escreve diretamente em `/bundle/`**.

O `repo_jur` pode possuir um **CLI operacional interno próprio** para administração do pipeline.

---

## 3. Component Model

```text
[ External Collector / juridico-cli ]
               |
               v
[ ITP / Ingress ]
               |
               v
[ Preflight + official SHA-256 ]
               |
               v
[ Evidence Preservation ]
               |
               v
[ SHARED CONVERSION CORE ]
   ├─ ConversionEngine
   ├─ OCR Adapter
   ├─ Literal Markdown
   ├─ Technical JSON
   ├─ Critical-Data Validation Seam
   └─ Quality Gate
               |
               v
[ DOMAIN ROUTER ]
      ┌────────┴────────┐
      v                 v
[ LEGAL KNOWLEDGE ] [ JUDICIAL PROCESS ]
      |                 |
      v                 v
[ Semantic Review ] [ Semantic Review ]
      |                 |
      v                 v
[ Legal Producer ]   [ Process Producer ]
      |                 |
      v                 v
repo_jur/bundle/      Process Storage
      |
      v
[ Legal Retrieval Zero-Write ]
```

### 3.1 Shared Conversion Core

This is a **logical capability boundary**, not a mandatory package path.

Confirmed physical implementation to inspect/reuse first:

```text
src/pipeline_juridico/
```

Responsibilities:

- receive evidence reference;
- invoke `ConversionEngine`;
- preserve literal page markers;
- emit Technical JSON;
- expose OCR adapter seam;
- execute critical-data validation seam;
- execute Quality Gate.

It contains no Legal Knowledge schema and no Judicial Process schema.

### 3.2 Domain Router

The router receives only conformant Phase 1 artifacts.

Allowed routing targets:

```text
legal_knowledge
judicial_process
review_required
```

Routing metadata belongs to operational/technical artifacts, not Phase 1 body.

### 3.3 Legal Knowledge Context

Logical sub-capabilities:

```text
legal semantic review
legal schemas
legal producer
```

Their physical location is resolved from the Repository Implementation Map.

Publishes exclusively through Legal Producer to:

```text
repo_jur/bundle/
```

### 3.4 Judicial Process Context

Logical sub-capabilities:

```text
process semantic review
process schemas
process producer
```

Their physical location is resolved from the Repository Implementation Map.

Publishes to domain-specific process storage outside the Legal Knowledge bundle.

### 3.5 Semantic Review Layer

Each context owns its semantic enrichment schemas.

Interface:

```python
class SemanticReviewEngine:
    def review(self, phase1_artifacts, domain_profile) -> ReviewResult:
        ...
```

`ReviewResult` may contain:

- extracted fields;
- classification;
- provenance;
- warnings;
- `REVIEW_REQUIRED`.

It cannot write canonical storage.

### 3.6 Critical-Data Validation Seam

Interface:

```python
class CriticalDataValidator:
    def validate(self, phase1_artifacts, profile) -> CriticalValidationResult:
        ...
```

Result:

```text
OK
WARNING
REVIEW_REQUIRED
```

It never mutates `text_content`.

---

## 4. Logical Capability / Physical Implementation Boundary

Package maps in this specification are logical capability maps.

The implementation must begin with a Repository Implementation Map.

Confirmed existing implementation:

```text
src/pipeline_juridico/
```

The converter stabilized there is reused/adapted in place when it satisfies `ConversionEngine` responsibilities.

Reference logical capabilities:

```text
common contracts
ingress/preflight
evidence preservation
shared conversion
critical-data validation
quality gate
domain routing
legal semantic review
legal producer
process semantic review
process producer
legal retrieval
```

Physical file location is resolved from the real repository.

Rule:

```text
REUSE → ADAPT IN PLACE → TEST
```

Create a new module only when no suitable implementation exists.

Do not create parallel `pipeline/` or `producer/` trees merely to match documentation.

---

## 5. Interfaces and Data Flow

### 5.1 Ingress

```text
final eligible <handoff_id>.zip
        ↓
preflight
        ↓
official receiver SHA-256
        ↓
evidence preservation
        ↓
Phase 1
```

### 5.2 Production

```text
Phase 1 Markdown + Technical JSON
        ↓
Quality Gate
        ├─ FAIL → diagnostic/reprocess only
        └─ PASS/PASS_WITH_WARNINGS
                     ↓
              Producer OKF
                     ↓
             duplicate resolution
                     ↓
           ownership/lifecycle merge
                     ↓
             canonical validation
                     ↓
              atomic publish
```

### 5.3 Retrieval

```text
query + explicit filters
        ↓
candidate discovery
        ↓
structured filtering
        ↓
reranking decision seam
        ├─ bypass
        └─ optional reranker
                ↓
canonical materialization
        ↓
Retrieval Contract result
```

Chunking is a derived representation available to retrieval implementations; it does not automatically replace the concept-level lexical index.

---

## 6. Technical Schemas

Schemas técnicos são derivados e versionados fora `/bundle/`.

### 6.1 ITP/1.0 Manifest

Required:

```json
{
  "protocol_version": "1.0",
  "handoff_id": "<opaque-non-empty-id>",
  "evidence_reference": "evidence.pdf",
  "source_origin": "<non-empty-origin>",
  "retrieved_at": "<ISO-8601-with-timezone>",
  "collector": "<Actor>",
  "media_type": "application/pdf",
  "byte_size": 1
}
```

Optional:

```json
{
  "last_modified": "<ISO-8601-date-or-date-time>",
  "candidate_sha256": "<64-lowercase-hex>",
  "legal_hints": {}
}
```

#### `handoff_id`

Implementation validation must accept an opaque non-empty identifier.

UUID v4 lowercase is **recommended**, not mandatory.

#### `collector`

Application-level Actor validation must accept:

```text
human:<id>
process:<id>
<producer>/<version>
```

Do not encode a regex that accidentally excludes the producer/version form.

### 6.2 Ingress State

Operational state outside `/bundle/`:

```json
{
  "handoff_id": "<opaque>",
  "manifest_semantic_fingerprint": "<derived>",
  "official_evidence_sha256": "<sha256>",
  "result": "<operational-result>",
  "updated_at": "<timestamp>"
}
```

Retry equivalence requires:

- same `handoff_id`;
- semantically equivalent manifest;
- same official evidence SHA.

### 6.3 Phase 1 Technical Report

Minimum shape follows the FROZEN operational specification:

```json
{
  "schema_version": "1.0",
  "execution_id": "<opaque-run-id>",
  "input": {
    "sha256": "<64-lowercase-hex>",
    "byte_size": 0,
    "page_count": 0
  },
  "phase1": {
    "implementation": "<implementation-id>",
    "implementation_version": "<version>",
    "logical_processing_version": "<version>",
    "relevant_config_fingerprint": "<opaque-fingerprint>"
  },
  "result": {
    "quality_gate": "PASS",
    "warnings": [],
    "errors": []
  },
  "artifacts": {
    "markdown_sha256": "<64-lowercase-hex>"
  },
  "pages": [
    {
      "page_number": 1,
      "method": "native_text",
      "char_count": 0,
      "warnings": [],
      "errors": []
    }
  ],
  "telemetry": {}
}
```

Serialized quality gate values:

```text
PASS
PASS_WITH_WARNINGS
FAIL
```

Human-readable normative labels remain:

```text
PASS
PASS WITH WARNINGS
FAIL
```

### 6.4 Derived Lexical Index Metadata

Each persistent index record/set must permit stale detection using at least:

```json
{
  "concept_id": "<canonical-positional-id>",
  "content_fingerprint": "<derived>",
  "index_schema_version": "<version>",
  "indexer_logical_version": "<version>",
  "index_config_fingerprint": "<derived>"
}
```

`content_fingerprint` must cover the indexed body and retrieval-relevant canonical metadata.

### 6.5 Chunking Profile

```yaml
profile_version: "..."
measurement_unit: "..."
soft_limit: ...
hard_limit: ...
forced_split_overlap: ...
```

No numeric value is FROZEN by this specification.

### 6.6 Derived Chunk Record

```json
{
  "concept_id": "jurisprudencia/exemplo",
  "chunk_set_fingerprint": "<derived>",
  "chunk_ordinal": 1,
  "text_content": "<literal-contiguous-span>",
  "body_range": {
    "start": 0,
    "end": 100
  },
  "page_refs": [1],
  "source_refs": [],
  "section_path": [],
  "warnings": []
}
```

Required:

- `concept_id`;
- chunk set fingerprint;
- ordinal;
- literal `text_content`;
- deterministic body range.

Conditional:

- `page_refs`;
- `source_refs`.

### 6.7 Reranking Profile

```yaml
profile_version: "..."
enabled: false

trigger_policy:
  mode: "..."

candidate_policy:
  limit: "..."

execution_policy:
  timeout: "..."
  failure_behavior: "preserve_primary_order"

implementation:
  type: "..."
  implementation_id: "..."
  configuration_fingerprint: "..."
```

No exact classifier, Cross-Encoder, provider, API, threshold, timeout or candidate count is mandatory.

### 6.8 Verification History

Canonical conditional extension remains exactly governed by its FROZEN memo:

```yaml
repo_jur_verification_history:
  - by: "human:original-reviewer"
    at: "2026-08-10T14:32:00Z"
    invalidated_at: "2026-08-14T06:31:00Z"
    invalidated_by: "human:decision-actor"
    reason: "material_content_change"
```

`invalidated_by` is the Actor that **decided or authorized** the invalidation, not automatically the software that wrote the file.

---

## 7. Ingress Implementation

### 7.1 Completion Protocol

The sender writes the temporary and final names on the **same filesystem**:

```text
<inbox>/<handoff_id>.partial
        ↓ close completely
same-filesystem atomic rename
        ↓
<inbox>/<handoff_id>.zip
```

Inbox path is configurable.

No `/data/inbox` or `/data/staging` absolute path is architecturally required.

### 7.2 Preflight Order

```text
1. ZIP container validation
2. central-directory inspection
3. member-name validation
4. encryption/special-member validation
5. configurable size/ratio limits
6. manifest bounded read
7. strict UTF-8 + JSON parse
8. ITP schema validation
9. bounded/streaming evidence read
10. official receiver SHA-256
11. candidate hash comparison if present
12. structural PDF compatibility validation
13. accepted evidence preservation
```

### 7.3 Archive Security

Reject:

- invalid ZIP;
- encrypted members;
- any member other than root `manifest.json` and `evidence.pdf`;
- duplicate member names;
- normalized-name collisions;
- absolute paths;
- `..`;
- directories;
- symlinks/hardlinks/special members;
- unsupported compression methods;
- configured compressed-size violation;
- configured uncompressed-size violation;
- configured compression-ratio violation;
- configured manifest-size violation.

No global `100 MB` constant is FROZEN.

### 7.4 Streaming

Do not use whole-file `archive.read("evidence.pdf")` when bounded/streaming processing is feasible.

Conceptual implementation:

```python
with archive.open("evidence.pdf", "r") as stream:
    sha256 = hash_stream(stream, limits=preflight_limits)
```

If validation requires a temporary file, place it in quarantine outside `/bundle/`, with bounded size and cleanup.

### 7.5 PDF Validation

`%PDF-` magic bytes alone are insufficient.

Validation must include a safe structural open/parse route that does not execute:

- scripts;
- macros;
- attachments;
- embedded active content.

### 7.6 Object Storage

After necessary physical validations:

```text
accepted exact bytes
      ↓
ObjectStorageGateway.put(...)
      ↓
stable resolvable reference
```

Provider, bucket, URI scheme and object key are Implementation Choices.

---

## 8. Phase 1 Implementation

### 8.1 Conversion Engine Boundary

Required interface:

```python
class ConversionEngine:
    def convert(self, evidence_ref, config) -> Phase1Artifacts:
        ...
```

Architecture remains engine-neutral.

### 8.2 Current Implementation Choice

The existing operational converter is reused behind `ConversionEngine`. The current implementation may use **MarkItDown / markitdown-ocr with Gemini through an OpenAI-compatible client**. This remains an Implementation Choice and does not freeze Gemini, MarkItDown or the compatibility client as architectural dependencies.

This is an **Implementation Choice**, not a FROZEN architecture dependency.

An OCR fallback may be attached behind an engine-neutral adapter when required.

This specification does **not** replace that choice silently with `pypdf + Tesseract`.

### 8.3 OCR Routing

OCR routing may use implementation/calibration signals, but this specification does not freeze:

- `<10 characters`;
- OCR confidence threshold;
- specific OCR provider;
- specific OCR model;
- retry count.

### 8.4 Literal Body

For each physical page:

```text
[[Pág. N]]
<literal representation>
```

Rules:

- exactly one marker per physical page;
- order 1..N;
- blank page keeps marker;
- no summary;
- no translation;
- no semantic correction;
- no inferred completion;
- technical comments stay out of body.

This specification does not create a mandatory `[ilegível]` sentinel.

### 8.5 Quality Gate

The gate must evaluate all FROZEN conditions, not only marker count.

Conceptual sequence:

```python
def evaluate_phase1(markdown, report):
    validate_page_inventory(report)
    validate_page_markers(markdown, report.input.page_count)
    validate_no_unresolved_page_errors(report)
    validate_no_known_truncation(report)
    validate_markdown_artifact(markdown)
    validate_technical_report(report)

    if fatal_errors:
        return FAIL

    if nonfatal_warnings:
        return PASS_WITH_WARNINGS

    return PASS
```

OCR use alone and legitimate blank pages do not create warnings.

`allow_partial` never converts FAIL into success.

---

## 8A. Post-OCR Critical-Data Validation

This seam remains non-mutating.

A rule for identifier format, length, check digit or structure may be implemented only with a reliable and versioned technical/normative specification.

Rule metadata must identify:

```text
rule_id
rule_version
source/specification
validation_logic_version
```

Never generalize a universal rule from one observed document, especially for digital seals or registry identifiers.

Allowed outcomes:

```text
OK
WARNING
REVIEW_REQUIRED
```

Findings remain outside literal Markdown.

Deterministic comparison of redundant values across the same document remains out of scope.

---

## 8B. Domain Routing

Only Phase 1 results with:

```text
PASS
PASS WITH WARNINGS
```

may enter domain routing.

The router selects:

```text
legal_knowledge
judicial_process
review_required
```

Routing does not alter the Phase 1 body.

---

## 8C. Semantic Review / Enrichment

Semantic Review receives immutable Phase 1 Markdown.

It may correct structure, classification and enrichment artifacts but cannot freely rewrite legal content.

Required invariants:

- never overwrite Phase 1 Markdown;
- no summary, paraphrase, translation, invention or inferred completion;
- structural operations preserve all original words;
- prefer structured patches;
- record `before`, `after`, `reason`, `confidence`;
- preserve page/evidence traceability when supported;
- ambiguity → `REVIEW_REQUIRED`;
- Semantic Review never publishes.

`Papel/Nome`-style boundary problems belong here, not in deterministic conversion.

Legal and Process YAML/enrichment schemas remain separate.

---

## 9. Producer / Publication

### 9.1 Producer Boundary

The Producer is the only component authorized to publish concepts into `/bundle/`.

### 9.2 Duplicate Resolution

Do not reduce Duplicate Act Handling to `same hash → no-op`.

Required resolution categories:

```text
physical evidence known?
        ↓
legal/logical act resolution
        ↓
same act + equivalent canonical inputs/config + no new canonical provenance + no meaningful change
        → NO-OP

same act + safely equivalent new evidence/provenance
        → controlled update candidate

distinct/autonomous act
        → distinct concept candidate

material change or ambiguity
        → HUMAN REVIEW
```

Hash is only physical evidence identity.

No automatic `_v2`.

No automatic `status: deprecated`.

### 9.3 Concept ID

Duplicate resolution does not invent a “unique concept_id” by suffix.

`concept_id` is positional.

Collision or unresolved naming ambiguity must follow controlled producer/human governance.

### 9.4 Lifecycle / Ownership Merge

Implementation must follow the ordered FROZEN workflow:

```text
1. load existing concept
2. parse frontmatter + body
3. resolve identity/provenance
4. detect technical vs material change
5. recompute Producer-Owned fields
6. merge Shared/Human-Owned fields
7. apply verified/history policy
8. apply body ownership
9. validate OKF/Profile/cardinality
10. atomic publication
```

The implementation must preserve:

- Human-Owned fields;
- human-curated Shared Ownership values;
- valid active `verified`;
- `repo_jur_verification_history`;
- unknown/extension keys when applicable;
- body ownership.

### 9.5 `status`

`status` is Human-Owned.

If absent, OKF semantics already interpret the concept as stable.

The Producer must not insert/change `status` merely to materialize that default semantic value.

### 9.6 `generated`

`generated.at` changes only on meaningful change to current content.

A re-run without meaningful canonical change must not create timestamp-only diffs.

### 9.7 `verified`

Never auto-create `verified`.

A materiality decision governs preservation/invalidation.

If invalidated:

- archive only a real prior event;
- preserve original `by` + `at`;
- record decision Actor in `invalidated_by`;
- omit `verified` when no active events remain.

### 9.8 Atomic Publication

Publication sequence:

```text
render complete candidate
        ↓
validate YAML + OKF + Legal Profile + ownership/cardinality
        ↓
write temp file on same filesystem
        ↓
fsync/close as implementation requires
        ↓
atomic replace/rename
        ↓
expose Git diff for review
```

This specification does not require automatic Git commit/push.

---

## 10. Legal Knowledge Retrieval Implementation

This section applies only to Legal Knowledge and `repo_jur/bundle/`.

Judicial Process Retrieval is out of scope and requires a future separate contract.

No shared index may mix Legal Knowledge and process documents.


### 10.1 Lexical Backend Interface

```python
class LexicalIndexBackend:
    def build(self, concepts, config): ...
    def sync(self, concepts, config): ...
    def search(self, query, filters, limit): ...
```

### 10.2 Implementation Choice — SQLite FTS5

SQLite FTS5 is a valid **reference implementation choice** for the initial local lexical backend.

It is not an architecture requirement.

Suggested derived storage:

```text
<derived_data_root>/retrieval/...
```

If `<derived_data_root>` is inside the Git worktree, it must be gitignored.

No absolute `/data/retrieval_cache/` path is required.

### 10.3 Direct Filesystem Fallback

Normative fallback capability:

```text
Direct Read-Only Filesystem Search
```

Implementation may use Python traversal/search or another deterministic local mechanism.

### 10.4 Structured Filters

At minimum, retrieval can expose explicitly retrieval-relevant:

- `type`;
- `status`;
- `tags`.

No automatic status boost/demotion/exclusion is introduced.

### 10.5 Canonical Materializer

The materializer must:

1. receive candidate `concept_id`;
2. confirm current path exists;
3. read current canonical frontmatter/body;
4. validate required provenance/materialization;
5. reject stale candidate text as authority.

If a candidate is stale/missing:

- do not silently present it;
- record operational stale condition;
- sync/re-query or degrade to direct filesystem search when necessary.

---

## 11. Chunking Implementation

### 11.1 Input

Only the current canonical concept body is chunked.

Frontmatter is parsed separately.

### 11.2 Structural Parser

Use a Markdown structural parser/AST or deterministic equivalent capable of identifying:

- headings;
- paragraphs;
- lists;
- blockquotes;
- tables;
- fenced code blocks.

Library selection is Implementation Choice.

### 11.3 Chunk Algorithm

```text
canonical body
     ↓
page interval map
     ↓
structural blocks
     ↓
contiguous grouping under Chunking Profile
     ↓
forced split only when needed
     ↓
derived chunk records
```

### 11.4 Size Profile

The engine consumes:

- measurement unit;
- soft limit;
- hard limit;
- forced-split overlap.

No default numeric value is FROZEN here.

### 11.5 Literal Contiguity

`text_content` must always be a contiguous literal span of the canonical body.

Do not inject repeated:

- headings;
- table headers;
- synthesized context.

Context may be separate derived metadata.

### 11.6 Page Mapping

Construct physical page intervals first.

For each chunk:

```text
page_refs = ordered union of page intervals intersecting body_range
```

No active page before the first marker may be invented.

No page→source mapping may be invented for multi-source concepts.

### 11.7 Chunk Set Validity

Chunk set validity depends on:

- canonical content;
- `concept_id`;
- Chunking Profile version/fingerprint;
- chunker logical version.

Any change invalidates affected derived chunks.

---

## 12. Reranking Seam

### 12.1 Interface

```python
def should_rerank(query, candidates, profile):
    ...

def rerank(query, candidates, profile):
    ...
```

### 12.2 Default Implementation Choice

Initial safe implementation:

```text
reranking.enabled = false
```

The seam is implemented and testable, but no neural reranker is required before an evaluation dataset demonstrates benefit.

### 12.3 No Mandatory Intent Classifier

Do not require `QueryClassifier(Exact vs Conceptual)`.

A trigger policy may later consider:

- query shape;
- candidate ambiguity;
- budget;
- reranker availability.

Exact-identifier bypass is allowed as an implementation optimization, not universal architecture.

### 12.4 No Trust Blending

Prohibited automatic relevance multipliers:

- human-reviewed boost;
- stable-status boost;
- deprecated demotion;
- temporal decay;
- verification-history boost.

### 12.5 Fail-Open

On error/timeout/unavailability:

```text
discard partial reranker output
        ↓
preserve primary valid order
        ↓
record failed_fallback
        ↓
continue canonical materialization
```

No heuristic reranker fallback is mandatory.

---

## 13. Sync / Rebuild / Invalidation

### 13.1 Lexical Index Sync Key

Index validity depends on:

```text
concept_id
content_fingerprint
index_schema_version
indexer_logical_version
index_config_fingerprint
```

### 13.2 Operations

```text
CREATE
CONTENT UPDATE
RENAME/MOVE
DELETE
CONFIG/SCHEMA/VERSION CHANGE
```

#### CREATE
Insert derived record.

#### CONTENT UPDATE
Reindex concept.

#### RENAME/MOVE
Remove old `concept_id`; insert new positional ID.

#### DELETE
Purge/invalidate derived entry.

#### Config/Schema/Version
Rebuild affected records or full index.

### 13.3 Chunk Sync

Chunk sets use independent version/profile validity.

Changing Chunking Profile or chunker logical version triggers chunk rebuild even when concept content is unchanged.

### 13.4 Reranking Profiles

Profile changes do not alter bundle or lexical content.

They affect runtime only.

### 13.5 Full Rebuild

A full retrieval rebuild:

1. discards derived lexical/chunk state;
2. traverses current bundle;
3. recreates derived data;
4. never writes into `/bundle/`.

---

## 14. CLI Commands

The repo-local CLI is an **operational `repo_jur` tool**, not the external `juridico-cli`.

Command naming is Implementation Choice.

Recommended command surface:

```bash
repo-jur ingress run --inbox <path>
repo-jur handoff process <handoff.zip>

repo-jur phase1 run <evidence-ref>
repo-jur phase1 validate <run-ref>

repo-jur producer build <run-ref>
repo-jur producer validate <concept-candidate>
repo-jur producer publish <concept-candidate>

repo-jur retrieval sync
repo-jur retrieval rebuild
repo-jur search "<query>"
repo-jur search-diagnose "<query>"

repo-jur test conformance
```

Publication commands must preserve Producer-only authority.

---

## 15. Observability

Operational data stays outside `/bundle/`.

### 15.1 Required Events

Ingress:

- handoff accepted/rejected/conflict;
- preflight failure category;
- official evidence hash;
- storage preservation result.

Phase 1:

- execution ID;
- page method/outcome;
- warnings/errors;
- gate result;
- timing telemetry.

Producer:

- resolution outcome;
- human-review requirement;
- materiality decision category;
- publication result.

Retrieval:

- index fresh/stale/degraded;
- sync/rebuild;
- reranking `disabled|bypassed|applied|failed_fallback`;
- canonical materialization stale/missing candidate.

### 15.2 Storage

Log location is configurable outside the bundle.

No fixed `/data/audit/` path is required.

### 15.3 Secrets

Never log:

- API keys;
- tokens;
- passwords;
- cookies;
- authorization headers;
- equivalent credentials.

Required provenance hashes should not be arbitrarily redacted when they are necessary for integrity/audit.

---

## 16. Testing Strategy

### 16.1 Unit Tests

Ingress:

- exact two-member ZIP;
- duplicate names;
- encrypted member;
- traversal;
- absolute path;
- link/special member;
- unsupported compression;
- ratio/size limits;
- malformed UTF-8 manifest;
- invalid Actor;
- optional candidate SHA mismatch.

Phase 1:

- one marker per page;
- blank page;
- OCR success can PASS;
- OCR alone does not warn;
- unresolved page error causes FAIL;
- known truncation causes FAIL;
- `allow_partial` remains FAIL.

Producer:

- single ↔ plural PDF hash cardinality;
- `sources[].id` mapping;
- Shared/Human ownership;
- generated.at semantic-change behavior;
- verified preservation/invalidation/history;
- unknown extension preservation;
- duplicate ambiguity → HUMAN REVIEW.

Retrieval:

- concept-level lexical discovery;
- Zero-Write;
- stale index;
- rename/move;
- delete;
- config fingerprint change;
- filesystem fallback;
- canonical materialization.

Chunking:

- contiguous literal spans;
- soft/hard profile behavior;
- forced split;
- overlap;
- page interval mapping;
- table/header derived context;
- no invented page/source.

Reranking:

- disabled;
- bypass;
- applied through a fake adapter;
- timeout;
- exception;
- preserve primary order;
- observability.

### 16.2 Integration Tests

Required end-to-end fixtures:

```text
ITP ZIP
 → preflight
 → evidence preservation
 → Phase 1
 → Quality Gate
 → Producer
 → canonical publish
 → retrieval
 → materialization
```

Use deterministic controlled fixtures before large real-corpus regression.

### 16.3 Compliance Tests

Must prove:

- no retrieval write under `/bundle/`;
- only Producer publication path writes concepts;
- no Stable IDs introduced;
- no automatic `_v2`;
- no automatic status mutation;
- no trust/relevance blending;
- FAIL never reaches Producer;
- canonical result comes from current bundle.

---

## 17. Acceptance Criteria

Implementation is accepted only if all are true:

1. ITP preflight passes the complete security/contract test matrix.
2. Accepted evidence is preserved before Phase 1.
3. Official receiver SHA matches exact accepted bytes.
4. Phase 1 produces one page record per physical page.
5. Page markers are exactly `1..N`.
6. Quality Gate exposes exactly PASS/PASS_WITH_WARNINGS/FAIL.
7. FAIL cannot enter Producer.
8. Producer preserves field ownership.
9. `verified` and verification history obey materiality rules.
10. PDF singular/plural hash fields are mutually exclusive.
11. Multi-PDF hash mapping exactly matches PDF source IDs.
12. Ambiguous duplicate resolution stops for HUMAN REVIEW.
13. Publication is validated and atomic.
14. Retrieval is Zero-Write.
15. Lexical index is rebuildable and stale-detectable.
16. Filesystem fallback works when index is unavailable.
17. Chunk text is literal contiguous canonical body.
18. Page refs are interval-derived and not invented.
19. Reranking disabled mode works.
20. Reranking failure preserves valid primary order.
21. Relevance never mutates trust/lifecycle.
22. Canonical materialization prevents stale derived text from becoming final evidence.
23. Full derived rebuild leaves `/bundle/` unchanged.
24. Shared Conversion Core is reused by both bounded contexts.
25. Domain routing occurs only after Quality Gate.
26. Judicial Process artifacts cannot be published to `repo_jur/bundle/`.
27. Legal and process schemas/enrichment are isolated.
28. Semantic Review cannot publish canonical storage.
29. Critical-data validation never mutates literal OCR/Markdown.
30. Technical OCR method/routing/warnings remain outside the body.
31. Existing converter is reused behind `ConversionEngine` without rewrite requirement.


No arbitrary requirement such as “50 real PDFs” or a specific `250 ms` timeout is part of architectural acceptance.

Corpus-scale regression sizes belong to the test plan/profile.

---

## 18. Implementation Sequence

### Stage 0 — Repository Implementation Map
Inspect the real repository before creating or moving code.

### Stage 1 — Contract Harness
Reuse existing common contracts and guards.

### Stage 2 — ITP / Ingress / Preflight / Evidence Preservation
Implement/reconcile the FROZEN ingress path:

```text
ITP/Ingress
→ Preflight
→ official SHA-256
→ Evidence Preservation
```

Reuse existing ITP/ESIC contracts; do not redesign them.

### Stage 3 — Shared Conversion Core
Wrap the existing `src/pipeline_juridico/` converter behind `ConversionEngine` without forced relocation.

### Stage 4 — Critical-Data Validation Seam
Add non-mutating, specification-backed validation rules.

### Stage 5 — Phase 1 Quality Gate
Preserve PASS / PASS WITH WARNINGS / FAIL.

### Stage 6 — Domain Router
Route legal/process/review without hidden semantic classification.

### Stage 7 — Legal Knowledge Semantic Review / Producer
Preserve original Phase 1 artifact and use traceable structural/enrichment patches.

### Stage 8 — Judicial Process Semantic Review / Producer
Keep schemas/storage isolated from Legal Knowledge.

### Stage 9 — Legal Knowledge Retrieval
Preserve Retrieval Contract v2.8; no Judicial Process index.

### Stage 10 — Conformance / Regression
Run both bounded-context flows and prove bundle isolation.

---

## 19. Implementation Choices

| Component | Current / Recommended Choice | Status |
|---|---|---|
| Dependency management | `uv` | Implementation Choice |
| Phase 1 conversion | Existing MarkItDown/markitdown-ocr adapter behind `ConversionEngine`; Gemini-compatible client may be used by current OCR implementation | Current Implementation Choice |
| OCR fallback | adapter seam; engine not selected here | Implementation Choice |
| Lexical backend | SQLite FTS5 reference backend is acceptable | Implementation Choice |
| Direct fallback | Python read-only traversal/search is acceptable | Implementation Choice |
| Markdown structural parser | not selected here | Implementation Choice |
| Object Storage provider | not selected here | Implementation Choice |
| Reranker | disabled by default; adapter seam only | Implementation Choice |
| Reranking engine/model | not selected | Implementation Choice |
| Derived-data root | configurable outside `/bundle/` | Implementation Choice |

Changing an Implementation Choice does not modify architecture when all FROZEN interfaces/invariants remain satisfied.

---

## 20. Risks / Non-Goals

### 20.1 Risks

#### Silent architecture drift
Mitigation: every implementation PR must map changed behavior to this specification and its FROZEN source.

#### Oversimplified duplicate merge
Mitigation: use explicit resolution state machine and HUMAN REVIEW branch.

#### Whole-PDF memory pressure
Mitigation: bounded/streaming ingress and configurable limits.

#### Stale retrieval artifacts
Mitigation: fingerprints, schema/config/logical versions and canonical materialization.

#### Chunk profile drift
Mitigation: profile version/fingerprint participates in chunk-set validity.

#### Reranking overreach
Mitigation: disabled default, relevance/trust separation and fail-open.

#### Converter substitution
Mitigation: conversion engine remains adapter-based; changing the current MarkItDown implementation choice requires an explicit implementation change, not silent replacement.

### 20.2 Non-Goals

This specification does not:

- migrate old corpora;
- choose semantic/vector infrastructure;
- select reranking model;
- certify legal correctness of source content;
- reproduce exact PDF visual layout;
- automate Git push;
- grant external collectors bundle-write authority.

---

## 21. Technical Review Corrections

The technical review corrected the proposal in the following material areas:

1. corrected the stale reference from `decision-memo-reranking-pipeline-v1.0.md` to the FROZEN memo;
2. removed the false rule that exact queries must always bypass reranking;
3. removed “silent degradation”; reranking failure is fail-open **and observable**;
4. removed mandatory `Exact vs Conceptual` classifier;
5. removed mandatory Cross-Encoder seam/implementation;
6. removed automatic `trust_tier` relevance boost;
7. removed automatic temporal decay;
8. removed status-based boost/demotion;
9. removed fixed `250 ms` timeout and candidate-count constants;
10. kept Reranking Profile generic and versioned;
11. restored `juridico-cli` as an external consumer/collector, not code inside `repo_jur`;
12. replaced the invented repo-internal `juridico-cli` CLI with a repo-local operational CLI boundary;
13. removed mandatory UUID-v4 validation for `handoff_id`; UUID v4 is only recommended;
14. corrected `collector` to the full Actor Convention;
15. allowed `last_modified` to be date or date-time;
16. replaced unsafe fixed `/data/staging → /data/inbox` rename with same-filesystem configurable inbox completion;
17. removed hard-coded `100 MB` preflight limit;
18. restored configurable compressed/uncompressed/ratio/manifest limits;
19. added encrypted/special-member/duplicate-name/compression-method validations;
20. replaced whole-PDF archive reads with bounded/streaming behavior;
21. removed magic-header-only PDF validation as sufficient;
22. restored Object Storage preservation before Phase 1;
23. replaced the flattened Phase 1 report with the FROZEN nested report shape;
24. removed the hard-coded `<10 characters` OCR trigger;
25. removed unapproved `pypdf + Tesseract` replacement and retained MarkItDown as the current implementation choice behind an adapter;
26. removed mandatory `[ilegível]` sentinel;
27. replaced the incomplete marker-only Quality Gate pseudo-code with the complete FROZEN gate responsibilities;
28. corrected PASS/WARNING terminology to PASS/PASS WITH WARNINGS/FAIL;
29. removed the oversimplified `same signals → NO-OP` duplicate rule;
30. restored the full NO-OP conditions and HUMAN REVIEW branch;
31. removed automatic “unique concept_id” generation implications;
32. replaced the destructive/incomplete frontmatter merge pseudo-code with the FROZEN ownership workflow;
33. restored `generated.at`, `verified`, verification history and body ownership semantics;
34. removed automatic insertion of `status: stable`;
35. required validation before atomic publication;
36. kept SQLite FTS5 only as an Implementation Choice/reference backend;
37. removed fixed derived-data paths;
38. added index schema/logical/config fingerprints to synchronization;
39. required stale/missing materialization to be observable rather than silently dropped;
40. added the missing Chunking Profile and forced-split rules;
41. preserved literal contiguous chunk text and interval-based page refs;
42. added profile/chunker-version chunk invalidation;
43. removed Cross-Encoder-specific tests and implementation sequence;
44. removed arbitrary `50 PDFs` acceptance threshold;
45. removed arbitrary `500/250 ms` reranking tests;
46. made reranking disabled-by-default the safest initial implementation;
47. preserved all FROZEN architectural decisions without opening a new architectural decision.

---

**Specification Status: APPROVED — CLOSED — FROZEN (CORRECTED v1.2)**
