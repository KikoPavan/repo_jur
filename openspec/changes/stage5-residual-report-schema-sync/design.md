# stage5-residual-report-schema-sync — Design

## Context

Stage 5 archived the Phase 1 Quality Gate with three explicitly documented residuals (`openspec/changes/archive/2026-08-21-stage5-phase1-quality-gate/proposal.md` Residual Risks 1–3): (1) the Phase 1 technical report does not implement the FROZEN §6.3 minimum block layout, (2) no frozen known-truncation signal exists in the report contract, so the normative fatal rule is not evaluable, and (3) `output.sha256` hashes the raw converter output (with method comments) while the boundary literal is normalized, making any markdown-hash comparison false-FAIL. The Quality Gate memo §14.3 mandates the synchronization ("regras do gate; page inventory; JSON técnico mínimo; partial diagnostic mode; retry bounded/configurável; separação entre campos determinísticos e telemetria"), and the archived design records that the §14.3 sync "must add the executable check — an explicit frozen truncation flag". The master backlog tracks this as **R1 — `stage5-residual-report-schema-sync`** (MEDIUM, 4 task groups, first in the ordered roadmap) because Stages 7–9 consume the report shape for provenance, index fingerprints, and producer consumption.

Repository facts verified 2026-08-21 at `main @ 24e2e01` (worktree `wt/r1-stage5-report-schema-sync`, clean):

- `src/pipeline_juridico/models.py` `Relatorio`: `schema_version`, `run_id`, `status` (`StatusExecucao`: `sucesso`/`incompleto`/`falha`), `source` (`FonteInfo`: `path`/`size_bytes`/`sha256`/`pages`), `output` (`SaidaInfo`: `path`/`sha256`), `runtime` (`RuntimeInfo`), `ocr` (`OcrInfo`), `timing` (`TimingInfo`), `pages` (`ResultadoPagina`: `number`/`method`/`status`/`characters`/`duration_ms`/`warnings`/`error`). JSON serialization is `json.dumps(asdict(relatorio))` — dataclass field names ARE the wire field names.
- `src/pipeline_juridico/report.py` `validate_report_contract` enforces the current shape (top-level `status` in `StatusExecucao`, `source`/`output`/`runtime`/`ocr`/`timing` objects, per-page `number`/`method`/`status`/`characters`/`warnings`/`error`); `build_report_json` serializes; `determine_final_status` computes the execution status entangled with `allow_partial`.
- `src/pipeline_juridico/quality_gate.py` `evaluate(phase1_artifacts)` reads, via an isolated read-only mapping, `source.sha256`, `source.pages`, and per-page `number`/`method`/`status`/`characters`/`warnings`/`error`; implements no known-truncation check (deferred-evaluability decision, Stage 5 Decision 6); never mutates the artifacts.
- `src/pipeline_juridico/converter.py` constructs the `Relatorio`; `src/pipeline_juridico/conversion_engine.py` `ConversionEngine.convert` builds `report_json`, validates it, and returns `Phase1Artifacts(markdown=normalized_literal, report_json)`; `src/pipeline_juridico/cli.py` writes the report file after `convert_document` (its Markdown file keeps the raw converter output with method comments — direct-conversion behavior, preserved by the shared-conversion-core requirement).
- `src/pipeline_juridico/validator.py:115` consumes `page.number`/`page.method` of the per-page records (`validate_markdown_matches_report`) — a rename consumer to migrate.
- Tests locking the current shape: `tests/test_report.py` (contract fixtures), `tests/test_quality_gate.py` (report fixtures + field mapping), `tests/test_cli.py` (asserts `report["status"] == "sucesso"` / `"incompleto"`), `tests/test_models.py`, `tests/test_validator.py`, `tests/test_acceptance.py`.
- OpenSpec baseline `openspec validate --all --strict`: 6 passed, 0 failed (2026-08-21, before this change).

FROZEN authorities (all read; internally consistent; no contradiction found):

- `technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §6.3 (report minimum block layout + serialized gate values), §8.5 (`evaluate_phase1` conceptual sequence incl. `validate_no_known_truncation(report)`), §17 ("known truncation causes FAIL").
- `decision-memo-phase1-quality-gate-v1.0-FROZEN.md` §3.4 (objective conditions incl. "truncamento conhecido"), §8.2 (extraction failure incl. "truncamento conhecido da saída"), §11.2–§11.5 (report minimum core, rules, engine-specific details as optional extensions, secrets prohibition), §14.3 (required sync), §8.5 (no implicit heuristic threshold is fatal).
- `phase1-operational-spec-v1.1-FROZEN.md` §3 (outputs: Markdown literal + JSON técnico "relatório de conversão, page inventory, warnings/errors, configuração relevante e resultado do gate"), §4.2 (no technical comments in the literal body), §6 (page inventory: `page_number`, normalized method/state, char count or equivalent, warnings, errors), §7.1/§7.3 (truncation as PASS/FAIL condition), §8 (partial diagnostic mode).
- `external-source-ingestion-contract-v1.6-FROZEN.md` §11 condition 4 (Phase 1 Quality Gate = FAIL includes "truncamento conhecido ou relatório técnico inválido").

Normative conclusion on the truncation signal (review point 1): the per-page boolean `pages[].truncated` is derived, not invented — the corpus defines the concept ("truncamento conhecido") and its fatal consequence (memo §3.4/§6 c.6/§8.2; op-spec §7.1/§7.3; tech-spec §8.5/§17; ESIC §11 c.4), assigns it to the page (memo §8.2 under "Falha de extração"), wires the check to the report (`validate_no_known_truncation(report)`, tech-spec §8.5), and delegates the exact serialized field names to the operational schema (op-spec §6 "Os nomes serializados exatos podem ser definidos pelo schema operacional"; memo §3.3 "Os nomes exatos podem ser normalizados pelo schema da Fase 1"). The §14.3 sync that fixes the serialized form is mandatory. Full chain in Decision 2.

## Repository Implementation Map

| Logical capability | Physical implementation found | Decision | Tests covering it | Migration |
| --- | --- | --- | --- | --- |
| Report model (wire shape) | `Relatorio` in `src/pipeline_juridico/models.py` (`run_id`, flat `source`, `output`, `runtime`, `ocr`, `timing`, top-level `status`, per-page `number`/`status`/`characters`/`error`) | **ADAPT IN PLACE** — reshape dataclasses to the §6.3 blocks (`execution_id`, `input`, `phase1`, `result`, `artifacts`, `pages` with `page_number`/`char_count`/`errors`/`truncated`, `telemetry`) | `tests/test_report.py`, `tests/test_models.py`, `tests/test_cli.py` (status assertions), `tests/test_acceptance.py` | rename fields; move `runtime`/`ocr`/`timing`/paths/durations into `telemetry`; add `phase1`/`result`/`artifacts`; per-page `truncated` |
| Report contract validation | `validate_report_contract` in `src/pipeline_juridico/report.py` | **ADAPT IN PLACE** — enforce the §6.3 block layout; keep `ReportContractError`; gate-result values `PASS`/`PASS_WITH_WARNINGS`/`FAIL` | `tests/test_report.py` | new field paths/types; `result.quality_gate` vocabulary; `truncated` bool mandatory |
| Report emission (deterministic vs. telemetry separation) | `build_report_json` (single-phase) used by `conversion_engine.py` and `cli.py` | **ADAPT IN PLACE** — two-phase emission: candidate report → gate evaluation → final report with `result` block (helper in `report.py`); full-contract validation on the emitted report only | `tests/test_conversion_engine.py`, `tests/test_cli.py` | add emission helper; wire into both emission sites |
| Quality Gate field mapping | `quality_gate.py` reads `source.sha256`/`source.pages`/`pages[].number|status|characters|warnings|error` | **ADAPT IN PLACE** — read `input.sha256`/`input.page_count`/`pages[].page_number|method|char_count|warnings|errors|truncated`; state carrier moves from `pages[].status` to `pages[].errors` + `method`; never read `result`/`telemetry` | `tests/test_quality_gate.py` | rewrite mapping + scenarios; keep all Stage 5 invariants |
| Known-truncation check | none — not evaluable (no signal in contract) | **CREATE within gate** — `validate_no_known_truncation` equivalent: any page `truncated == true` ⇒ `FAIL`; never inferred | new `tests/test_quality_gate.py` truncation cases | none (field now mandatory) |
| Direct-conversion Markdown artifact | CLI writes raw converter output (with method comments) | **NOT CHANGED** — direct conversion remains available without a breaking behavioral change (shared-conversion-core requirement); only the report contract changes | `tests/test_cli.py` (existing marker assertions stay) | none |
| Method vocabulary | `Metodo` (`texto_nativo`/`ocr_integral`/`hibrido`/`vazia`/`erro`) | **REUSE as-is** — engine-neutral, schema-defined per op-spec §3.3/§6 | `tests/test_models.py`, `tests/test_report.py` | none |

## Goals / Non-Goals

**Goals:**

- synchronize the Phase 1 technical report to the FROZEN §6.3 minimum block layout (all eight blocks, §6.3/§11.2) with the deterministic/telemetry separation (§14.3);
- add the explicit, authoritative known-truncation signal as the mandatory per-page boolean `truncated` and implement the now-evaluable fatal gate check (`validate_no_known_truncation`, tech-spec §8.5; memo §8.2; op-spec §7.1/§7.3; ESIC §11 condition 4);
- update the gate's read-only field mapping to the synchronized contract, preserving every Stage 5 invariant: three states, determinism, engine-neutrality, non-mutation of the artifacts, independence from Critical-Data Validation, no routing, no production authority, no heuristic-threshold fatal rule;
- emit the report with the serialized gate result recorded (`result.quality_gate` ∈ {`PASS`, `PASS_WITH_WARNINGS`, `FAIL`}; human label "PASS WITH WARNINGS" never serialized) while keeping the gate pure and non-mutating (two-phase emission);
- redefine `artifacts.markdown_sha256` over the Phase 1 literal Markdown (boundary artifact, markers only, no method comments — op-spec §4.2) so the traceability hash is consistent with the artifact the report describes;
- migrate the report, gate, CLI, and validator consumers and their tests to the synchronized contract.

**Non-Goals:**

- inventing truncation detection (no heuristic detector; `truncated: true` only on explicit authoritative knowledge; memo §8.5 prohibits implicit heuristic thresholds as fatal rules);
- adding a gate markdown-hash comparison (not in the tech-spec §8.5 sequence);
- changing the direct-conversion Markdown artifact or any conversion/OCR/cleaning/routing/atomic-write behavior;
- editing any FROZEN baseline; writing to `repo_jur/bundle/`; adding or changing dependencies; modifying Stage 4 code; implementing Stage 6+ capabilities;
- renaming the method vocabulary (retained: op-spec §3.3/§6 schema-defined names).

## Decisions

### 1. Two-phase report emission; the gate stays pure and non-mutating

The report must record the gate result (§6.3 `result` block; op-spec §3 output 2 "resultado do gate"), but the Stage 5 spec requires the gate to never mutate the serialized report. These are reconciled by emitting in two phases: (a) the conversion pipeline builds the candidate report (all deterministic blocks except `result`); (b) the pipeline evaluates the gate over `Phase1Artifacts(markdown=literal, report_json=candidate)`; (c) the pipeline emits the final report whose `result.quality_gate` is the serialized gate state and whose `result.warnings`/`result.errors` are the gate's tuples. The gate never writes; the emitted report is contract-validated in full (`validate_report_contract`) only in its final form.

**Rationale:** preserves the archived Stage 5 non-mutation invariant (the gate never touches the report it received — byte-identity tests still hold) while satisfying the §6.3/op-spec §3 requirement that the JSON técnico carries the gate result.

**Alternative considered:** the gate mutates the report to record its result.
**Rejected because:** violates the Stage 5 non-mutation contract and would make the gate's behavior depend on serialization details.

**Alternative considered:** single-phase report whose top-level `status` is mapped to the gate state.
**Rejected because:** `StatusExecucao` (execution status) and `GateState` (physical quality state) are distinct FROZEN concepts; Stage 5 already rejected fusing them.

### 2. Per-page boolean `truncated` is the explicit frozen truncation signal

Each `pages[]` record gains a mandatory boolean `truncated`. `true` means the pipeline has explicit, authoritative knowledge that this page's output was truncated; `false` (the value recorded when the pipeline holds no such knowledge) means no known truncation. The field is mandatory and always present on every emitted page record — absence of the field is a report-contract violation (FAIL), never equivalent to `false`. The gate fails when any page has `truncated: true`; it never infers truncation from `char_count`, `method`, warnings, or any other observable; the empty-return rule (`char_count == 0` with `method != "vazia"`) remains its own independent fatal rule.

**Derivation chain (per-page boolean from FROZEN authorities — verbatim evidence):**

1. **The rule is normative and fatal.** "Truncamento conhecido" (known truncation) is a FAIL condition stated verbatim in the corpus: memo §3.4 lists "truncamento conhecido" among the objective conditions the gate detects ("O gate deve detectar condições objetivas como: ... truncamento conhecido ..."), §6 criterion 6 makes PASS require "não há truncamento conhecido", §8.2 lists "truncamento conhecido da saída" under "Falha de extração"; op-spec §7.1 makes PASS require "nenhum truncamento conhecido" and §7.3 includes "truncamento conhecido" in FAIL; tech-spec §17 ("known truncation causes FAIL"); ESIC §11 condition 4 (FAIL includes "truncamento conhecido").
2. **The check is a function of the report.** Tech-spec §8.5 defines the mandatory conceptual gate sequence `evaluate_phase1(markdown, report)` including `validate_no_known_truncation(report)` — the corpus itself wires the rule to the technical report. A check invoked on the report can be evaluated only if the report carries the truncation state; the corpus therefore requires the report to represent known truncation. This is the anchor that locates the signal in the report (not in the Markdown, not outside both).
3. **Truncation is a per-page extraction outcome.** Memo §8.2 lists "truncamento conhecido da saída" under "Falha de extração" alongside page-level bullets ("página com conteúdo que termina em estado error", "retorno vazio quando a página não foi determinada como realmente vazia"); memo §3.4 lists it among objective page-level textual conditions. Op-spec §6 requires exactly one page-inventory entry per physical page identifying the extraction outcome. The document-level conditions "não há truncamento conhecido" (memo §6 c.6; op-spec §7.1) aggregate the per-page outcomes — the same pattern as criterion 4 ("todas as páginas possuem resultado técnico concluído"), which aggregates per-page facts; a whole-document truncation that manifests as missing/incomplete pages is already caught by the page-inventory and marker rules.
4. **The page-inventory field list is a minimum, and serialized names are schema-delegated.** Op-spec §6: "Cada entrada deve permitir identificar ao menos: `page_number`; método/estado de extração normalizado; quantidade de caracteres ou métrica equivalente; warnings; errors" — "ao menos" (at least) leaves the schema free to add fields, and the corpus explicitly delegates naming: op-spec §6 "Os nomes serializados exatos podem ser definidos pelo schema operacional, mas devem permanecer engine-neutral" and memo §3.3 "Os nomes exatos podem ser normalizados pelo schema da Fase 1, desde que não dependam de um engine específico". The corpus-defined concept is binary — known truncation: yes/no — so a boolean is the minimal faithful encoding, placed at the corpus-assigned granularity (page, step 3) in the corpus-designated carrier (report page record, step 2).
5. **"Known" means explicit, authoritative knowledge — never inference.** The corpus separates fatal deterministic rules from heuristic diagnostics: memo §8.5 ("Sem threshold heurístico fatal implícito") states that only a proven deterministic detector can be a fatal rule, and heuristic signals remain warning/diagnostic until an objective rule is approved. "Conhecido" (known) therefore maps to explicit, authoritative knowledge: the signal is set only when the pipeline knows truncation occurred, and is never inferred from character counts, methods, warnings, or any other observable. This is exactly the semantic the design records as "explicit, authoritative".
6. **The §14.3 synchronization is mandatory and is this change.** Memo §14.3 requires synchronizing "regras do gate; page inventory; JSON técnico mínimo; partial diagnostic mode; retry bounded/configurável; separação entre campos determinísticos e telemetria". The archived Stage 5 design (human-approved, `openspec/changes/archive/2026-08-21-stage5-phase1-quality-gate/design.md`) records that "the §14.3 report-schema synchronization must add the executable check — an explicit frozen truncation flag — before the already-normative condition becomes evaluable on the report contract; the gate would then consume it as a fatal signal without changing its architecture"; the archived proposal Residual Risk 2 records the same determination, and the master backlog R1 purpose is "make truncation-signal rule evaluable" (`docs/planning/MASTER_IMPLEMENTATION_BACKLOG_stages_6_10.md` §J).

**Normative-gap check:** the concept ("truncamento conhecido"), its fatal consequence, its per-page granularity, its report carrier, and the mandate to define its serialized form are all corpus-defined (steps 1–3 and 6). What the corpus explicitly delegates to the operational schema (step 4) is only the exact serialized field name (`truncated`) and type (boolean) — an exercise of the delegated authority op-spec §6 / memo §3.3 confer by name, not an invention of semantics. No HUMAN DECISION is required: the corpus is silent only on the serialized spelling, which the corpus assigns to this schema; it is not silent on the concept, consequence, granularity, or carrier.

**Rationale:** steps 1–3 establish the concept, its fatal consequence, its per-page granularity, and its report carrier from the corpus itself; steps 4–5 establish that defining the exact serialized field (name `truncated`, type boolean) is the operational schema's delegated authority, exercised here as the mandated §14.3 sync. No new semantics are invented: the field carries only the corpus-defined concept, the fatal consequence is unchanged, and no heuristic, threshold, or inference rule is introduced (memo §8.5: only deterministic proven detectors can be fatal).

**Alternative considered:** a single report-level `truncated` flag (or a list of truncated page numbers).
**Rejected because:** coarser and less traceable; the per-page flag subsumes it and keeps the signal with the extraction outcome it describes (memo §8.2 places the concept at page granularity).

### 3. Method vocabulary retained (`texto_nativo`/`ocr_integral`/`hibrido`/`vazia`/`erro`)

The §6.3 example serializes `"method": "native_text"`, but op-spec §3.3 and §6 explicitly permit the Phase 1 schema to define the exact serialized names ("Os nomes exatos podem ser normalizados pelo schema da Fase 1, desde que não dependam de um engine específico"). The existing values are engine-neutral and map 1:1 to the conceptual states (native/OCR/hybrid/blank/error). The gate's allowed-method vocabulary is unchanged.

**Rationale:** renaming the vocabulary would churn the converter, validator, tests, and Stage 4 consumers for zero normative gain; §6.3's example is illustrative.

### 4. Page state derives from `method` + `errors`; per-page `status` is removed; `truncated` is an independent fatal signal, not a state carrier

The §6.3 page record has no `status` field; op-spec §6 requires only a normalized method/state. A page is not completed when `method == "erro"` (failed extraction, fatal independently of anything else — memo §3.3 `error` outcome) or `errors` is non-empty (unresolved page errors). The per-page `truncated` boolean is NOT part of the completed-state derivation: it is an additional independent fatal signal (known truncation ⇒ FAIL regardless of the completed state, per Decision 2). The top-level execution `status` (`sucesso`/`incompleto`/`falha`) is likewise removed from the report; the outcome is `result.quality_gate`, and partial artifacts yield `FAIL` through the page-level not-completed states (Stage 5 partial semantics unchanged).

**Rationale:** matches the §6.3 record shape exactly; the gate's fatal semantics (Stage 5 Decision 6 mapping) are preserved with the state carrier moved from `pages[].status` to `pages[].errors` + `method`.

**Alternative considered:** keep a per-page `status` field alongside `errors`.
**Rejected because:** the §6.3 record has no such field; keeping it would re-introduce the divergence the sync removes and duplicate state (two carriers for the same fact).

### 5. Dataclass fields are renamed to the wire names (no serializer mapping layer)

`Relatorio` and the per-page record are reshaped in `models.py` so `asdict()` yields the §6.3 JSON directly. Internal consumers (`validator.py:115` page-record mapping, converter report construction, CLI assertions) are migrated in the same change.

**Rationale:** the current pipeline already treats dataclass field names as wire names; a mapping layer would add indirection and a second source of truth for the contract.

**Alternative considered:** keep dataclass names and add a serializer mapping.
**Rejected because:** two sources of truth for the wire contract; higher drift risk for downstream Stages 7–9 that consume the JSON.

### 6. `artifacts.markdown_sha256` is the hash of the Phase 1 literal Markdown — and only of that artifact

The hash covers exactly the Phase 1 literal Markdown: the boundary artifact with canonical `[[Pág. N]]` markers and no technical method comments (op-spec §3 output 1, §4.2 literalidade). Three distinct Markdown texts exist and are NOT interchangeable:

1. **The Phase 1 literal Markdown** — the boundary artifact exposed by the Shared Conversion Core (`Phase1Artifacts.markdown`): canonical markers, no `<!-- método: ... -->` comments, per op-spec §3/§4.2 and shared-conversion-core "Literal Markdown and technical information remain separate". This is the artifact `artifacts.markdown_sha256` hashes, and the only artifact the report's hash claim describes.
2. **The raw converter output written by the CLI** (`cli.py` writes the `markdown` returned by `convert_document` to `<stem>.md`): the direct-conversion artifact that still carries the canonical marker-adjacent `<!-- método: ... -->` comments. This file is NOT the Phase 1 literal — the two differ exactly by the technical method-comment lines, which the boundary removes (shared-conversion-core: "the only permitted Markdown difference is the FROZEN-required removal of technical routing/method comments from the literal body exposed by the shared boundary"; direct conversion remains available "without a breaking behavioral change"). The report does NOT hash this file, and the report's hash is NOT verifiable against it. Any reader comparing `markdown_sha256` against the CLI-written `<stem>.md` would be comparing against the wrong artifact by contract.
3. **The old `output.sha256` semantics** — hashing the raw converter output (with method comments). This is exactly Stage 5 Residual Risk 3 and is what this change replaces: `markdown_sha256` is redefined over the literal so that a hash comparison against the boundary artifact would not false-FAIL conformant output.

Normative basis for the hash target: op-spec §3 (Phase 1 outputs = literal Markdown + JSON técnico, so the report describes the literal), op-spec §4.2 (no technical comments in the literal body), memo §11.3 ("hash do Markdown quando houver saída final" — the Phase 1 Markdown output, which is the literal), tech-spec §6.3/§11.2 (`artifacts.markdown_sha256`). The direct-conversion raw file is not the Phase 1 output artifact under any FROZEN authority — it is the pre-boundary converter result, preserved only by the shared-conversion-core non-breaking requirement.

**Implementation consequence:** the emission site computes the hash over the literal — in the Stage 3 boundary flow this is `Phase1Artifacts.markdown`, which is already the comment-stripped literal (`conversion_engine.py:48–51` `strip_technical_routing_metadata`); in the CLI flow the pipeline MUST strip the marker-adjacent `<!-- método: ... -->` comment lines (the same normalization the boundary applies) before hashing. The CLI-written `<stem>.md` (raw converter output with the comments present — `converter.py` inserts them at page-marker assembly and `cli.py` writes that exact text) is byte-different from the literal exactly by those comment lines, so `markdown_sha256` is NOT verifiable against the CLI file; the report does not claim to audit that file, and the contract states so explicitly (juridical-pdf-conversion spec, scenario "O hash cobre somente o Markdown literal"). The gate still performs no comparison (not in the §8.5 sequence); the field is validated for presence and type only. This resolves Stage 5 Residual Risk 3 with no gate behavior change and no direct-conversion artifact change.

**Rationale:** the report must describe the artifact it accompanies; the boundary literal is the Phase 1 output per op-spec §3/§4.

### 7. `phase1` identifiers and `relevant_config_fingerprint`

`phase1.implementation`, `phase1.implementation_version`, and `phase1.logical_processing_version` are non-empty opaque identifiers owned by the implementation (e.g. implementation id, package version, logical-processing version constant). `relevant_config_fingerprint` is a deterministic opaque fingerprint over the non-secret configuration relevant to the conversion output (e.g. routing limits, partial-mode flag, OCR-enabled flag); identical configuration yields an identical fingerprint, and any change to that configuration changes it. Exact values and composition are implementation-detail (the corpus defines field names, not values — §6.3/§11.3 "identidade/versão lógica da implementação" and "fingerprint da configuração relevante").

**Rationale:** §6.3/§11.3 require the fields; their content is versioned implementation metadata, not FROZEN values.

### 8. Former `runtime`/`ocr`/`timing`/paths/durations move under `telemetry`

`telemetry` is a mandatory object that MAY be empty, carrying non-normative per-run data: the former `runtime` (package versions), `ocr` (provider/model/prompt hash), `timing` (start/finish/duration), input/output paths, and per-page durations. Memo §11.4 explicitly permits engine-specific details as optional technical extensions, and §14.3 requires the separation of deterministic fields from telemetry. The gate never reads `telemetry` (engine-neutrality and determinism preserved).

**Rationale:** preserves observability while making the deterministic contract exact; the §6.3 `telemetry: {}` block is the designated home.

### 9. Gate input requirements exclude the `result` block; full contract validation applies to the emitted report

The gate's minimum-field rule covers the structural fields it derives state from (`input.sha256`, `input.page_count`, complete `pages[]` with `page_number`/`method`/`char_count`/`warnings`/`errors`/`truncated`). The `result` block is a gate *output* and is not required on the gate's input (the candidate report legitimately lacks it); `validate_report_contract` requires the full §6.3 layout including `result` and `telemetry` on the emitted final report.

**Rationale:** reconciles the two-phase emission (Decision 1) with the report contract; prevents the gate from circularly requiring its own output.

### 10. No new dependency; direct-conversion behavior preserved

No `uv add`, no FROZEN edit, no bundle write, no Stage 4/6+ change. The CLI's Markdown file keeps the raw converter output (shared-conversion-core "no breaking behavioral change"); only the report contract, its emission, and the gate's mapping change.

## Risks / Trade-offs

| Risk | Mitigation |
| --- | --- |
| Field renames ripple into converter-internal consumers (`validator.py`, converter, CLI, tests) | Explicit migration task group; full-suite regression gate; the report contract is the single source of truth (Decision 5) |
| Two-phase emission could be misread as gate mutation | Non-mutation tests keep asserting byte-identity of the report passed to the gate; emission helper is outside the gate module |
| `truncated` could become a dead field (no detector sets it) | Contract-mandatory + gate check tested; residual documented (proposal Residual Risk 1); no heuristic invented |
| Downstream Stages 7–9 depend on the new shape | R1 is first in the ordered roadmap; the synchronized shape IS the §6.3 shape those stages consume |
| Over-encoding (adding rules the corpus does not mandate) | Every contract field cites §6.3/§11.2; every gate rule cites the FROZEN condition; no heuristic threshold |
| CLI report hash vs CLI-written raw Markdown file mismatch | The contract declares the hash over the Phase 1 literal only (Decision 6); the CLI-written `<stem>.md` is the raw converter output with method comments and is NOT the hashed artifact — the report does not claim to audit it, and this is stated explicitly in the spec and the proposal Impact. Emission computes the hash over the comment-stripped literal in both flows |

## Migration / Test impact

- `tests/test_report.py`: contract fixtures and scenarios move to the §6.3 shape (blocks, types, `result.quality_gate` vocabulary, `truncated` mandatory, telemetry optional content, secrets prohibition).
- `tests/test_quality_gate.py`: report fixtures move to the new field paths; new truncation cases (any `truncated: true` ⇒ FAIL; `truncated: false` never fails; never inferred; empty-return rule unchanged); state-carrier cases move from `pages[].status` to `pages[].errors` + `method == "erro"`; new cases asserting the gate ignores `result` and `telemetry`; all Stage 5 invariants (determinism, non-mutation, independence, no routing/production) re-verified against the new contract.
- `tests/test_cli.py`: `report["status"]` assertions become `report["result"]["quality_gate"]` assertions (`FAIL` for strict failure; `FAIL` for `--allow-partial` diagnostic output — partial never PASS/PASS_WITH_WARNINGS).
- `tests/test_models.py`, `tests/test_validator.py`, `tests/test_acceptance.py`, `tests/test_converter_integration.py`: migrated where they touch renamed per-page fields or report status.
- OpenSpec: `openspec validate --all --strict` must stay green; this change adds `specs/juridical-pdf-conversion/spec.md` and `specs/phase1-quality-gate/spec.md` MODIFIED sections.

No architectural question remains open: the corpus is internally consistent, the per-page truncation boolean is derived from FROZEN authorities (Decision 2 derivation chain with verbatim evidence: normative fatal rule → report-carried check `validate_no_known_truncation(report)` → per-page extraction outcome → schema-delegated serialized names → mandated §14.3 sync; "known" = explicit authoritative knowledge per memo §8.5, never inference), the emission ordering and hash target are resolved here (Decisions 1–10; `markdown_sha256` covers the Phase 1 literal only, never the CLI-written raw file — Decision 6), the mandatory-field contract is internally consistent (absence of `pages[].truncated` is a missing-required-field FAIL, never equivalent to `false` — proposal, design, and both specs state this), and no HUMAN DECISION is required for this change. All three human-review points were resolved with corpus evidence: (1) truncation-signal derivation chain demonstrated verbatim (Decision 2), (2) absence-of-field semantics made unambiguous across all documents, (3) markdown-hash target clarified with byte-level precision (Decision 6 + juridical-pdf-conversion spec scenario).
