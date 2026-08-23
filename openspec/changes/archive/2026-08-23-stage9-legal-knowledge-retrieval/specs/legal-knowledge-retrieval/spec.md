# legal-knowledge-retrieval Specification

## Purpose

Define the Stage 9 Legal Knowledge Retrieval capability — the read-only consumer of the canonical Legal Knowledge bundle `repo_jur/bundle/`. The capability provides a concept-level lexical candidate index (SQLite FTS5 as a reference implementation choice, never an architecture requirement) with synchronization, rebuild and fingerprint-based stale detection; a Lexical-First, Hybrid-Ready search execution path (candidate discovery → structured filters → canonical materialization → Retrieval Contract result envelope) with the normative Direct Read-Only Filesystem Search fallback; a Structural Block-First, Page-Aware, Size-Profiled derived chunking representation governed by a versioned Chunking Profile; and an Optional, Conditional, Profile-Governed, Fail-Open reranking seam disabled by default. The capability indexes only canonical concept documents under `repo_jur/bundle/` produced by the closed Stage 7 Legal Producer, never mutates the bundle or Phase-1 artifacts, never touches Judicial-Process storage, never introduces embeddings, vector infrastructure, LLM rerankers or Stable IDs, and keeps relevance and trust as separate dimensions. Judicial Process Retrieval is out of scope and requires a separate future contract.

## ADDED Requirements

### Requirement: Retrieval is bounded to the Legal Knowledge canonical bundle

The system SHALL operate retrieval exclusively over concept documents under `repo_jur/bundle/` — the canonical Legal Knowledge storage produced by the closed Stage 7 Legal Producer — covering the `legislacao/`, `jurisprudencia/`, `temas/` and `precedentes/` type trees. The system SHALL NOT index, search, or traverse Judicial-Process storage, Phase-1 artifacts, technical conversion reports, or any intermediate output, and SHALL NOT create any shared index mixing Legal Knowledge and process documents.

#### Scenario: Bundle concepts are the only retrieval source

- **WHEN** retrieval synchronization or a search query executes against a repository containing a canonical bundle
- **THEN** only non-reserved Markdown concept documents under `repo_jur/bundle/` are indexed or searched
- **AND** no process-domain artifact and no Phase-1 artifact is read as retrieval source

#### Scenario: Process storage is never traversed

- **WHEN** the retrieval implementation source or the derived index is inspected
- **THEN** no path resolves into process-domain storage
- **AND** no shared Legal/Process index exists

### Requirement: Retrieval never mutates canonical artifacts

The system SHALL operate under Zero-Write over `repo_jur/bundle/`: no retrieval capability — indexing, synchronization, rebuild, search, materialization, chunking, or reranking — SHALL create, modify, delete, or rename any file under the bundle tree. The bundle SHALL be byte-identical before and after any retrieval operation.

#### Scenario: Bundle is byte-identical after synchronization

- **WHEN** a full retrieval synchronization or rebuild executes against a bundle
- **THEN** the SHA-256 hash of every file under the bundle after the operation equals the hash before the operation

#### Scenario: Search never writes to the bundle

- **WHEN** a search query executes, including fallback and degraded modes
- **THEN** no file under the bundle is created, modified, or deleted

### Requirement: Indexing eligibility follows canonical publication authority

The system SHALL index only canonical concept documents explicitly authorized by the repository contracts: non-reserved `.md` files under `repo_jur/bundle/` published by the Legal Producer through the exclusive bundle write guard. Reserved files (`index.md`, `log.md`) and non-Markdown files under the bundle SHALL NOT be indexed as concepts. Retrieval SHALL NOT become an alternate Producer or publication path.

#### Scenario: Only canonical concepts are indexed

- **WHEN** the indexer scans the bundle
- **THEN** every indexed unit is a non-reserved Markdown concept document under the bundle
- **AND** reserved and non-Markdown files produce no index record

#### Scenario: Retrieval has no publication authority

- **WHEN** a retrieval component attempts any write, including to derived storage resolving inside the bundle
- **THEN** the write is rejected
- **AND** the canonical bundle remains unchanged

### Requirement: Concept identity is the positional canonical join key

The system SHALL derive each concept's identity (`concept_id`) deterministically from the relative path of its Markdown file from the bundle root, removing the `.md` suffix, and SHALL use it as the canonical reference and join key for all derived data. The system SHALL NOT duplicate `concept_id` into frontmatter, SHALL NOT introduce a Stable Concept ID, UUID, or `_v2` suffix, and SHALL treat rename/move as a change of identity.

#### Scenario: Concept identity derives from the current path

- **WHEN** a concept document is indexed or materialized
- **THEN** its identity is the relative path without the `.md` suffix
- **AND** no frontmatter field duplicates that identity

#### Scenario: Rename or move changes identity

- **WHEN** a concept document is renamed or moved within the bundle
- **THEN** the derived records associated with the old path are removed or invalidated
- **AND** new derived records are associated with the new positional identity

### Requirement: The lexical candidate index is concept-level and backend-neutral

The system SHALL maintain a derived lexical candidate index whose initial unit is the concept document and whose join key is `concept_id`. The index SHALL be bound to a backend interface, not to a specific product: SQLite FTS5 is an acceptable reference implementation but not an architectural requirement, and replacing the backend SHALL NOT alter the bundle, the canonical schemas, `concept_id`, the Retrieval Contract, or the result interface.

#### Scenario: Index unit is the concept document

- **WHEN** the lexical index is built or synchronized
- **THEN** each derived record is associated with exactly one `concept_id`
- **AND** the record stores the indexable text, retrieval-relevant fields, and synchronization fingerprint

#### Scenario: Backend substitution preserves contracts

- **WHEN** an alternative lexical backend is configured in place of the reference implementation
- **THEN** the bundle, canonical schemas, `concept_id` derivation, and result envelope remain unchanged

### Requirement: Synchronization supports the full derived lifecycle

The system SHALL synchronize the derived index from the real state of the bundle, supporting CREATE, CONTENT UPDATE, RENAME/MOVE, DELETE, and CONFIG/SCHEMA/VERSION CHANGE operations. Synchronization SHALL NOT depend exclusively on file modification times, Git hooks, or the execution of any producer command for correctness.

#### Scenario: New concept is indexed

- **WHEN** a new concept document appears in the bundle
- **THEN** synchronization inserts a derived record for its `concept_id`

#### Scenario: Updated content is reindexed

- **WHEN** an existing concept document's content changes
- **THEN** synchronization reindexes the record for that `concept_id`

#### Scenario: Deleted concept is purged

- **WHEN** a concept document is removed from the bundle
- **THEN** synchronization purges or invalidates the derived record for that `concept_id`

### Requirement: Stale detection uses versioned fingerprints

The system SHALL detect staleness of persistent derived data using, at minimum, per-concept `content_fingerprint` plus `index_schema_version`, `indexer_logical_version`, and `index_config_fingerprint`, where the content fingerprint covers the indexed body and the retrieval-relevant canonical metadata. The system SHALL expose an observable fresh/stale/degraded state for the index.

#### Scenario: Content change is detected as stale

- **WHEN** a concept's canonical content changes and the derived fingerprint no longer matches
- **THEN** the derived record is classified stale
- **AND** the runtime does not serve stale text as canonical authority

#### Scenario: Configuration change invalidates records

- **WHEN** the index schema version, indexer logical version, or index configuration fingerprint changes
- **THEN** affected derived records are rebuilt or the full index is rebuilt

### Requirement: Full rebuild is derived-only and never touches the bundle

The system SHALL provide a full rebuild operation that discards the derived lexical and chunk state, traverses the current bundle, recreates derived data from the canonical concepts, and never writes into `repo_jur/bundle/`. Derived data residing inside the Git worktree SHALL be covered by `.gitignore` entries.

#### Scenario: Rebuild recreates derived data from the bundle

- **WHEN** a full rebuild executes
- **THEN** the derived index and chunk state are recreated from the current bundle content
- **AND** the bundle is byte-identical after the rebuild

#### Scenario: Derived data outside the bundle is gitignored

- **WHEN** the derived-data root resolves inside the Git worktree
- **THEN** the root is declared in `.gitignore`
- **AND** no derived file appears in the tracked Git tree

### Requirement: Structured filters are limited to explicitly retrieval-relevant fields

The system SHALL support structured filters on exactly the public Stage-9 v1 filter vocabulary: `type`, `status`, `tags`, `lei_numero`, `lei_ano`, `lei_esfera`, `lei_tipo`, `processo_numero`, `tribunal`, `relator`, `data_julgamento`, `ramo_direito`, `precedente_numero`, `precedente_status`, and `tema_numero`, declared retrieval-relevant in a versioned retrieval schema or configuration. The system SHALL map each public filter key deterministically to its canonical Legal OKF Profile frontmatter field — for the 12 retrieval-relevant profile fields the public key is the canonical field name with the `repo_jur_` prefix stripped (`lei_numero` → `repo_jur_lei_numero`, `tribunal` → `repo_jur_tribunal`), and `type`, `status`, and `tags` map to the identically-named canonical keys — and SHALL NOT accept `repo_jur_*` spellings as public filter keys or aliases. The system SHALL NOT make every `repo_jur_*` field automatically filterable, SHALL NOT derive filter values from document content, and SHALL NOT apply any automatic boost, demotion, or exclusion based on `status`, `draft`, `deprecated`, `trust_tier`, `verified`, or verification history.

#### Scenario: Public filter vocabulary is exact and mapped deterministically

- **WHEN** the versioned retrieval schema or configuration is inspected
- **THEN** the public filter keys are exactly `type`, `status`, `tags`, `lei_numero`, `lei_ano`, `lei_esfera`, `lei_tipo`, `processo_numero`, `tribunal`, `relator`, `data_julgamento`, `ramo_direito`, `precedente_numero`, `precedente_status`, and `tema_numero`
- **AND** each public key maps to exactly one canonical frontmatter field, and no `repo_jur_*` spelling is accepted as a public filter key or alias

#### Scenario: Minimum filters are supported

- **WHEN** a search query requests filters on `type`, `status`, or `tags`
- **THEN** the results honor the requested filters
- **AND** results include concepts whose canonical fields satisfy the filters

#### Scenario: Unauthorized filter keys are rejected

- **WHEN** a search query requests a filter on a field not declared retrieval-relevant, including a `repo_jur_*` spelling supplied as a public filter key
- **THEN** the request is rejected as a configuration error
- **AND** no results are silently computed ignoring the filter

#### Scenario: No automatic status policy

- **WHEN** a search query executes without an explicit `status` filter
- **THEN** no concept is automatically boosted, demoted, or excluded because of its `status`

### Requirement: Canonical materialization precedes every delivered result

The system SHALL, before delivering any result to the consumer, confirm that the candidate `concept_id` still exists in the current bundle, read the current canonical frontmatter and body, and validate the applicable provenance. The system SHALL reject stale derived text as authority, SHALL NOT silently present a missing or stale candidate, SHALL record the stale condition operationally, and SHALL re-query, synchronize, or degrade to direct filesystem search when necessary.

#### Scenario: Results are materialized from the current bundle

- **WHEN** a search query returns candidates
- **THEN** every delivered `text_content` and provenance field is materialized from, or validated against, the current canonical bundle content

#### Scenario: Missing candidate is not silently served

- **WHEN** a candidate identified by the index no longer exists in the bundle
- **THEN** the candidate is not delivered as grounded result
- **AND** the runtime records the missing condition operationally

### Requirement: Direct Read-Only Filesystem Search is the normative fallback

The system SHALL provide a Direct Read-Only Filesystem Search fallback that operates when the index is absent, incompatible, stale without immediate synchronization, corrupt, unavailable during rebuild, or failing initialization. The fallback SHALL read the bundle files directly, derive `concept_id` from the current path, read frontmatter from the concept, and follow the Retrieval Contract provenance rules. The runtime SHALL signal degraded mode observably and SHALL NOT promise index-level ranking or performance equivalence in fallback.

#### Scenario: Index unavailable triggers fallback

- **WHEN** a search query executes and the lexical index is absent, corrupt, or incompatible
- **THEN** the query is served by direct read-only filesystem search
- **AND** the runtime records the degraded condition

#### Scenario: Fallback preserves canonical correctness

- **WHEN** the fallback executes
- **THEN** the bundle remains read-only
- **AND** every result carries `concept_id` from the current path and provenance per the Retrieval Contract

### Requirement: The result envelope preserves full provenance

The system SHALL deliver every recovered fragment with the universal fields `concept_id` and `text_content`, and SHALL add conditional provenance fields exactly as sustained by the canonical concept: `source_refs` when the concept declares sources (per-fragment attribution only when explicitly represented); `page_refs` only when the physical page association is explicit and unambiguous, preserving all related pages when a fragment crosses pages; for exactly one PDF, `source_pdf` plus `repo_jur_pdf_hash`; for two or more PDFs, `repo_jur_pdf_hashes` mapping each PDF `sources[].id` to its SHA-256. `repo_jur_pdf_hash` and `repo_jur_pdf_hashes` SHALL NEVER coexist, and the system SHALL NOT invent any fragment-to-source or page-to-source association.

#### Scenario: Single-PDF provenance is exact

- **WHEN** a delivered fragment derives from a concept with exactly one PDF evidence
- **THEN** the envelope carries `source_pdf` and `repo_jur_pdf_hash`
- **AND** no plural hash mapping is present

#### Scenario: Multi-PDF provenance is exact

- **WHEN** a delivered fragment derives from a concept with two or more PDF evidences
- **THEN** the envelope carries `repo_jur_pdf_hashes` mapping each PDF `sources[].id` to its SHA-256
- **AND** no singular hash field is present

#### Scenario: Page references are never invented

- **WHEN** a fragment has no explicit and unambiguous physical page association
- **THEN** `page_refs` is omitted
- **AND** no page reference is fabricated from any other signal

### Requirement: Chunking is Structural Block-First, Page-Aware, Size-Profiled

The system SHALL generate derived chunks exclusively from the current canonical concept body materialized from the bundle, with frontmatter parsed separately and never included in `text_content`. Chunking SHALL prefer Markdown structural block boundaries (headings, paragraphs, lists, blockquotes, tables, fenced code blocks), preserve literal contiguous spans, allow chunks to cross physical pages, and perform a deterministic forced split only when a single structural unit exceeds the hard limit. The Stage 9 v1 Chunking Profile defaults SHALL be `measurement_unit=characters`, `soft_limit=6000`, `hard_limit=12000`, and `forced_split_overlap=200`; these SHALL be versioned, configurable profile defaults — not permanently frozen constants — and any future numeric change SHALL introduce a new Chunking Profile version and/or configuration fingerprint and SHALL invalidate or rebuild the affected derived chunk and index state. The system SHALL NOT rewrite, reorder, synthesize, or correct text, SHALL NOT duplicate headings or table headers inside `text_content`, and SHALL expose derived structural context (such as section path or table header context) separately from the text.

#### Scenario: Chunks preserve literal contiguous spans

- **WHEN** a concept body is chunked
- **THEN** every chunk `text_content` is a contiguous literal span of the canonical body
- **AND** no heading or table header is artificially repeated inside the span

#### Scenario: Page references derive from interval mapping

- **WHEN** a chunk spans physical page intervals explicitly represented in the concept
- **THEN** `page_refs` is the ordered union of the intersecting page intervals
- **AND** no page reference is invented when no explicit association exists

#### Scenario: Forced split is deterministic and lossless

- **WHEN** a single structural unit exceeds the hard limit
- **THEN** the unit is split deterministically at a safe boundary without losing or reordering characters
- **AND** every resulting chunk remains a contiguous span

#### Scenario: Chunking Profile v1 defaults are versioned, not frozen

- **WHEN** the versioned Chunking Profile is inspected or a numeric value changes
- **THEN** the v1 defaults are `measurement_unit=characters`, `soft_limit=6000`, `hard_limit=12000`, and `forced_split_overlap=200`
- **AND** any future numeric change requires a new profile version and/or configuration fingerprint and invalidates or rebuilds the affected derived chunk and index state

### Requirement: Chunk identity is derived and chunk sets are invalidatable

The system SHALL NOT create a Stable Chunk ID. Each chunk set SHALL be identifiable by a derived `chunk_set_fingerprint` computed from at least the canonical concept identity and content, the Chunking Profile version, the Chunking Profile configuration fingerprint, and the chunker logical version; each chunk SHALL carry a deterministic `chunk_ordinal` within its set and a derived body range. The system SHALL invalidate or rebuild chunk sets when the canonical content, `concept_id`, Chunking Profile version, Chunking Profile configuration fingerprint, or chunker logical version changes, and SHALL keep `concept_id` as the canonical join key.

#### Scenario: Chunk sets are fingerprint-identified

- **WHEN** a chunk set is generated
- **THEN** the set carries a derived fingerprint and each chunk carries a deterministic ordinal and body range
- **AND** no canonical chunk identifier is persisted

#### Scenario: Profile change invalidates chunk sets

- **WHEN** the Chunking Profile version, the Chunking Profile configuration fingerprint, or the chunker logical version changes
- **THEN** the affected chunk sets are invalidated or rebuilt
- **AND** the canonical bundle is not modified

### Requirement: Reranking is optional, conditional, profile-governed, and fail-open

The system SHALL expose a reranking seam that is disabled by default (`enabled: false`), whose enablement, trigger policy, candidate limits, timeout, implementation, and observability are governed by a versioned Reranking Profile. When disabled, the pipeline SHALL proceed from candidate discovery through structured filtering to canonical materialization without reranking. When enabled and triggered, any failure, timeout, or unavailability SHALL discard partial or invalid reranker output, preserve the previous valid order, record a `failed_fallback` state, and continue to canonical materialization. The system SHALL NOT require any specific reranker implementation, model, provider, classifier, or threshold.

#### Scenario: Disabled default bypasses reranking

- **WHEN** the Reranking Profile has `enabled: false` or is absent
- **THEN** no reranking occurs
- **AND** results are ordered by the valid order produced by candidate discovery and filtering

#### Scenario: Reranker failure preserves the valid order

- **WHEN** a triggered reranker fails, times out, or is unavailable
- **THEN** the partial or invalid reranker order is discarded
- **AND** the previously valid order is preserved
- **AND** canonical materialization proceeds and the failure is recorded operationally

### Requirement: Relevance and trust remain separate dimensions

The system SHALL rank results strictly by relevance of the query to the candidate and SHALL NOT apply automatic relevance multipliers derived from `trust_tier`, `verified`, `status`, `repo_jur_verification_history`, or temporal decay. The system SHALL NOT exclude, deprecate, or remove concepts from the index or bundle because of low relevance, and SHALL NOT merge relevance and trust into a single score that implies relevance proves legal reliability. `trust_tier` may be exposed as an optional derived signal and `repo_jur_verification_history` as audit-only information, never as active trust or ranking input.

#### Scenario: Trust signals never affect ordering

- **WHEN** a search query returns candidates and any candidate carries `verified`, `status`, or verification history
- **THEN** the ordering is determined only by query-to-candidate relevance
- **AND** no trust signal changes the order

#### Scenario: Low relevance does not erase evidence

- **WHEN** a candidate receives a low relevance score
- **THEN** the candidate is not deleted from the index or the bundle
- **AND** no canonical validity threshold is created

### Requirement: The query interface enforces validated result limits

The system SHALL expose a structured, read-only retrieval interface that enforces validated result limits, preventing unbounded raw text return to protect the consumer context window. The v1 default limit SHALL be 10 and the v1 maximum limit SHALL be 50, both validated configuration values; a request exceeding the maximum SHALL be rejected or clamped to the configured maximum, never silently unlimited. Pagination, cursors, page tokens, offset-based paging, and snapshot-paging semantics SHALL NOT be part of Stage 9 v1 and SHALL be deferred to a future authorized change; the v1 interface SHALL expose no pagination surface.

#### Scenario: Result limit is enforced

- **WHEN** a search request specifies a result limit
- **THEN** the response contains at most that many results (v1 default 10, maximum 50)
- **AND** a limit above the configured maximum is rejected or clamped to the maximum

#### Scenario: Pagination is not exposed in v1

- **WHEN** a search request or the retrieval interface is inspected
- **THEN** no cursor, page token, offset-based paging, or snapshot-paging surface exists
- **AND** result retrieval is bounded only by the validated result limit

### Requirement: Retrieval observability is content-safe and located outside the bundle

The system SHALL record retrieval execution in operational/technical artifacts only, stored outside `repo_jur/bundle/` and outside Phase-1 artifacts under a configurable derived-data root, covering at least: index fresh/stale/degraded state, synchronization and rebuild events, reranking states (`disabled`, `bypassed`, `applied`, `failed_fallback`), and canonical-materialization stale or missing conditions. Records SHALL NOT contain document content, full critical identifier values, secrets, tokens, or credentials, and SHALL reference processed evidence by provenance hash where applicable.

#### Scenario: Retrieval records are written outside the bundle

- **WHEN** a retrieval synchronization, rebuild, or search-diagnose run completes
- **THEN** an operational record is written under the configurable derived-data root
- **AND** the root is rejected when it resolves inside the canonical bundle

#### Scenario: Retrieval records are content-safe

- **WHEN** a retrieval record is inspected
- **THEN** it contains state and outcome information
- **AND** it contains no document content, no full critical identifier value, and no secret or token

### Requirement: The operational retrieval CLI is additive and non-regressive

The system SHALL provide operational commands for index synchronization, full rebuild, search, and search diagnosis, registered additively on the existing `repo-jur` entry point, following the existing CLI conventions (argparse, environment-driven directories, deterministic exit codes, sanitized logging, atomic writes). The commands SHALL NOT write to `repo_jur/bundle/`, SHALL NOT modify Phase-1 artifacts, and SHALL leave the pre-existing conversion, routing, producer, and process command surfaces unchanged.

#### Scenario: Sync and rebuild never write to the bundle

- **WHEN** the synchronization or rebuild command is invoked
- **THEN** no file is written under `repo_jur/bundle/`
- **AND** the command reports the outcome with a deterministic exit code

#### Scenario: Search returns provenance-carrying results

- **WHEN** the search command is invoked with a query and optional filters
- **THEN** the output reports results carrying `concept_id`, `text_content`, and applicable provenance
- **AND** no Phase-1 artifact or bundle file is modified

#### Scenario: Existing CLI surfaces are preserved

- **WHEN** the retrieval commands are introduced
- **THEN** the pre-existing conversion command surface, routing command surface, producer surface, and process surface remain unchanged

### Requirement: Retrieval is deterministic, rebuildable, and technology-neutral

The system SHALL compute index records, chunk spans, and results as deterministic functions of the canonical bundle content, the applicable profiles, and the logical versions of the components, such that identical inputs with identical profiles and versions yield deterministically equivalent derived data and ordering. The system SHALL NOT require byte-identical index binaries or scores across engines, SHALL NOT introduce embeddings, vector databases, ANN/HNSW, fusion algorithms, or external semantic services, and SHALL keep all derived data discardable and fully rebuildable from the canonical corpus.

#### Scenario: Deterministic regeneration

- **WHEN** the same canonical bundle, Chunking Profile, and logical versions are processed twice
- **THEN** the second run produces deterministically equivalent chunk spans and index records

#### Scenario: No semantic infrastructure is introduced

- **WHEN** the retrieval implementation source is inspected
- **THEN** it contains no embedding model client, vector database, ANN/HNSW, fusion, or external semantic service reference

### Requirement: Stage 9 does not implement later stages or Judicial Process retrieval

The system SHALL NOT implement Stage 10 (Conformance/Regression) or any later stage, SHALL NOT implement any Judicial Process retrieval, SHALL NOT write to judicial-process storage, SHALL NOT create a shared Legal/Process index, and SHALL NOT alter the Domain Router semantics, the page-level routing semantics of the conversion pipeline, or the closed Stage-7 and Stage-8 producer semantics. Retrieval SHALL remain downstream of canonical publication and never become an alternate Producer or publication path.

#### Scenario: No later-stage behavior is introduced

- **WHEN** the Stage 9 implementation source is inspected
- **THEN** it contains no Stage-10 conformance harness, no process-retrieval path, no process-storage write path, and no shared index creation
- **AND** Domain Router semantics and page-level routing semantics remain unchanged

#### Scenario: Retrieval never alters producer authority

- **WHEN** any Stage 9 capability executes
- **THEN** the Legal Producer remains the only component authorized to publish to `repo_jur/bundle/`
- **AND** no retrieval component emits, suggests, or writes a canonical publication
