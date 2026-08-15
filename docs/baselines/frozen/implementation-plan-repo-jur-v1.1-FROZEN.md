# PLANO DE EXECUÇÃO DE IMPLEMENTAÇÃO — `repo_jur`

**Versão:** 1.1 (Baseline corrigida e congelada)  
**Data:** 15 de agosto de 2026  
**Status:** FROZEN  
**Supersedes:** `implementation-plan-repo-jur-v1.0-FROZEN.md`  
**Rastreabilidade:** a v1.0 permanece preservada e não foi sobrescrita.

**Baselines obrigatórias:**

- `arquitetura-fase2-repo-jur-v15-FROZEN.md`
- `technical-implementation-spec-repo-jur-v1.2-FROZEN.md`
- `phase1-operational-spec-v1.1-FROZEN.md`
- `external-source-ingestion-contract-v1.6-FROZEN.md`
- `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`
- `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`
- `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md`
- `decision-memo-physical-layout-logical-capability-mapping-v1.0-FROZEN.md`
- `decision-memo-semantic-review-enrichment-layer-v1.1-FROZEN.md`
- `decision-memo-post-ocr-critical-data-validation-seam-v1.1-FROZEN.md`
- `decision-memo-retrieval-bounded-context-scope-v1.0-FROZEN.md`
- `retrieval-contract-v2.8-FROZEN.md`
- demais baselines FROZEN referenciadas pela Arquitetura v15.

---

## 0. Regra Obrigatória — Repository Implementation Map

Antes de qualquer alteração de código, o implementador deve inspecionar o repositório real.

Produzir:

| Capacidade lógica | Implementação física encontrada | Ação | Testes existentes | Justificativa |
|---|---|---|---|---|
| exemplo | caminho real | REUSE / ADAPT / CREATE | testes | motivo |

Ordem obrigatória:

```text
INSPECT
  ↓
REUSE
  ↓ se necessário
ADAPT IN PLACE
  ↓
TEST
```

Somente quando não existir implementação adequada:

```text
CREATE
```

Relocação física é mudança separada e exige justificativa explícita.

### Fato físico confirmado

O conversor estabilizado já existe em:

```text
src/pipeline_juridico/
```

Ele não deve ser movido ou duplicado apenas para coincidir com nomes de diagramas.

---

# 1. Regras Gerais

## 1.1 Logical targets, not physical mandates

Nomes como:

```text
shared_conversion
semantic_review
legal_producer
process_producer
retrieval
```

são capacidades lógicas.

Eles não obrigam:

```text
pipeline/
producer/
src/core/
```

ou qualquer árvore específica.

## 1.2 Legal bundle

`repo_jur/bundle/` continua exclusivo do bounded context **Legal Knowledge**.

Judicial Process nunca publica nessa árvore.

## 1.3 Phase 1 literal

O Markdown original da Phase 1:

- é literal;
- é preservado;
- nunca é sobrescrito por Semantic Review;
- não recebe routing/OCR/warnings/telemetria.

## 1.4 No silent technology replacement

A implementação atual de conversão é reutilizada.

MarkItDown / markitdown-ocr + Gemini via cliente OpenAI-compatible permanecem Implementation Choice atual quando esse for o estado real encontrado.

Não congelar provider/model/client.

---

# 2. Sequência Corrigida

```text
Stage 0  Repository Implementation Map
Stage 1  Contract Harness
Stage 2  ITP / Ingress / Preflight / Evidence Preservation
Stage 3  Shared Conversion Core
Stage 4  Post-OCR Critical-Data Validation Seam
Stage 5  Phase 1 Quality Gate
Stage 6  Domain Router
Stage 7  Legal Knowledge Pipeline
Stage 8  Judicial Process Pipeline
Stage 9  Legal Knowledge Retrieval
Stage 10 Conformance / Regression
```

---

# 3. Stage 1 — Contract Harness

## Objetivo

Reutilizar/estabelecer contratos realmente comuns.

## Capacidades

- Actor validation;
- evidence references;
- Phase 1 artifact types;
- Gate states;
- CriticalValidationResult;
- RouteTarget;
- Zero-Write guards aplicáveis ao runtime controlado.

## Ação

Primeiro localizar implementações existentes.

Criar apenas o mínimo ausente.

## Testes

- Actors válidos/inválidos;
- paths seguros;
- tentativa de write indevida no bundle;
- Process Producer não pode apontar para Legal bundle.

## Conclusão

Contracts comuns disponíveis sem importar schema Legal ou Process.

---

# 4. Stage 2 — ITP / Ingress / Preflight / Evidence Preservation

## Objetivo

Restaurar explicitamente a cadeia anterior à conversão.

Fluxo obrigatório:

```text
ITP / Ingress
      ↓
Preflight
      ↓
official receiver SHA-256
      ↓
Evidence Preservation
      ↓
Shared Conversion Core
```

## Reutilizar

Sem redesenhar:

- ITP/1.0;
- ESIC v1.6;
- ZIP safety rules;
- same-filesystem completion;
- streaming/bounded reads;
- official SHA-256;
- candidate SHA comparison;
- structural PDF validation;
- Object Storage preservation.

## Implementação

Repository Implementation Map deve localizar:

- ingress handler existente;
- preflight existente;
- hash calculation;
- storage adapter;
- tests.

## Regras

Evidence Preservation acontece antes da Phase 1.

O Shared Conversion Core recebe evidence reference/bytes preservados conforme o contrato, não um PDF assumidamente “aceito” sem cadeia de ingresso.

## Testes

- envelope válido;
- membros extras;
- traversal;
- encrypted/special members;
- malformed manifest;
- size/ratio policies;
- candidate SHA mismatch;
- official SHA exact bytes;
- preservation success/failure.

## Proibido

- redesenhar ITP;
- carregar whole evidence sem limites quando streaming é viável;
- gravar PDF no bundle;
- iniciar conversão antes de evidence preservation conformante.

---

# 5. Stage 3 — Shared Conversion Core

## Objetivo

Expor a implementação já existente através de `ConversionEngine`.

## Physical implementation

Confirmado:

```text
src/pipeline_juridico/
```

## Regra principal

Não criar:

```text
pipeline/shared_conversion/
```

em paralelo apenas para cumprir o desenho.

Mapear a capacidade lógica ao código existente.

## Interface lógica

```python
class ConversionEngine:
    def convert(self, evidence_ref, config) -> Phase1Artifacts:
        ...
```

O adapter pode ser uma interface/facade mínima em torno da implementação existente.

## Garantias

- literal Markdown;
- page markers;
- Technical JSON;
- OCR routing técnico fora do body;
- engine/provider neutrality arquitetural.

## Testes

Regressão sobre o conversor atual:

- textual PDF;
- scanned PDF;
- mixed PDF;
- blank page;
- OCR fallback;
- marker sequence;
- no technical metadata leakage.

## Proibido

- rewrite;
- duplicate converter;
- physical relocation por nomenclatura;
- silent engine swap.

---

# 6. Stage 4 — Post-OCR Critical-Data Validation Seam

## Objetivo

Detectar inconsistências críticas sem mutar o literal.

## Interface

```python
CriticalValidationResult(
    status="OK | WARNING | REVIEW_REQUIRED",
    findings=[...]
)
```

## Rule registry

Cada regra deve possuir:

```text
rule_id
rule_version
identifier_type
source/specification
validation_logic_version
```

## Regra de evidência normativa

Formato, comprimento, dígito verificador ou estrutura somente são implementados quando sustentados por fonte técnica/normativa confiável e versionada.

### Especial atenção

Para:

- selo digital;
- matrícula;
- identificadores de cartório/tribunal;

não generalizar uma regra a partir de um documento isolado.

## Allowed

- format validation respaldada;
- check digit respaldado;
- warning;
- REVIEW_REQUIRED.

## Forbidden

- autocorreção;
- preencher caracteres;
- escolher valor;
- converter “válido formalmente” em “verdade jurídica”.

## Teste invariável

```text
SHA256(markdown_before) == SHA256(markdown_after)
```

para a seam.

## Future boundary

Comparação determinística de valores redundantes dentro do documento continua fora do escopo.

---

# 7. Stage 5 — Phase 1 Quality Gate

## Objetivo

Preservar:

```text
PASS
PASS WITH WARNINGS
FAIL
```

## Independence

Critical-data status é distinto do Quality Gate físico.

Exemplo:

```text
physical = PASS
critical = REVIEW_REQUIRED
```

Resultado downstream:

```text
review_required
```

não:

```text
FAIL
```

## Regras

FAIL físico interrompe o fluxo.

`allow_partial` permanece diagnóstico.

## Testes

- missing marker;
- duplicated marker;
- inverted marker;
- extraction error;
- truncation;
- legitimate blank;
- successful OCR;
- PASS + REVIEW_REQUIRED.

---

# 8. Stage 6 — Domain Router

## Objetivo

Roteamento conservador pós-Quality-Gate.

Targets:

```text
legal_knowledge
judicial_process
review_required
```

## Precedence

```text
if gate == FAIL:
    stop

if critical == REVIEW_REQUIRED:
    route review_required
```

Depois, usar apenas routing signal explicitamente permitido.

## No hidden semantic classifier

O Router não executa análise semântica profunda.

Pode usar:

- workflow context;
- trusted routing hint;
- deterministic rule aprovada.

Ambiguidade:

```text
review_required
```

## Proibido

- LLM classification silenciosa;
- enrichment;
- YAML generation;
- publication.

---

# 9. Stage 7 — Legal Knowledge Pipeline

## Fluxo Legal atualizado

```text
ITP / Ingress
      ↓
Preflight
      ↓
official SHA-256
      ↓
Evidence Preservation
      ↓
Shared Conversion Core
      ↓
Critical-Data Validation
      ↓
Quality Gate
      ↓
Domain Router → legal_knowledge
      ↓
Legal Semantic Review / Enrichment
      ↓
Legal Producer
      ↓
repo_jur/bundle/
      ↓
Legal Knowledge Retrieval
```

## Semantic Review invariants

Phase 1 Markdown original é imutável.

A camada pode corrigir estrutura, classificação e enrichment.

Não pode:

- resumir;
- parafrasear;
- traduzir;
- inventar;
- preencher por inferência.

### Structural correction

Quando a mudança é estrutural:

- preservar todas as palavras originais;
- preferir structured patches;
- registrar:
  - before;
  - after;
  - reason;
  - confidence;
  - page refs;
  - evidence refs.

Problemas como fronteira:

```text
Papel / Nome
```

pertencem a esta camada.

### Ambiguidade

```text
REVIEW_REQUIRED
```

## Producer

Somente Legal Producer publica em `/bundle/`.

Preservar:

- Legal OKF Profile;
- Lifecycle;
- Field Ownership;
- Verification History;
- PDF cardinality;
- Duplicate Act Handling;
- concept identity;
- atomic validation/publication.

---

# 10. Stage 8 — Judicial Process Pipeline

## Fluxo Process atualizado

```text
ITP / Ingress
      ↓
Preflight
      ↓
official SHA-256
      ↓
Evidence Preservation
      ↓
Shared Conversion Core
      ↓
Critical-Data Validation
      ↓
Quality Gate
      ↓
Domain Router → judicial_process
      ↓
Process Semantic Review / Enrichment
      ↓
Process Producer
      ↓
Process-domain Storage
```

## Scope

Process documents:

- petições;
- contestações;
- decisões;
- procurações;
- testamentos;
- anexos;
- demais peças.

## Domain isolation

Process possui próprios:

- YAML schemas;
- enrichment schemas;
- Producer;
- storage.

Semantic Review processual obedece às mesmas garantias de preservação do literal Phase 1.

## Retrieval

**Judicial Process Retrieval não é implementado por este plano.**

Ele exige contrato/decisão própria futura.

## Proibido

- gravar process document no Legal bundle;
- usar Legal OKF schema como schema processual;
- criar índice compartilhado Legal + Process.

---

# 11. Stage 9 — Legal Knowledge Retrieval

## Escopo explícito

Retrieval Contract v2.8 atende somente:

```text
repo_jur/bundle/
```

e o bounded context Legal Knowledge.

## Covered

- legislação;
- jurisprudência;
- temas;
- precedentes.

## Out of scope

```text
Judicial Process Retrieval
```

## Isolation

Proibido indexar process-domain storage no índice Legal Knowledge.

## Preservar

- Lexical-First, Hybrid-Ready;
- concept-level lexical index;
- structured filters;
- filesystem fallback;
- canonical materialization;
- Structural Block-First chunking;
- Page-Aware;
- Size-Profiled;
- reranking optional/conditional/profile-governed/fail-open;
- relevance ≠ trust;
- Zero-Write.

SQLite FTS5 permanece reference Implementation Choice.

Reranker default:

```yaml
enabled: false
```

Nenhum vector DB ou embedding é introduzido.

---

# 12. Stage 10 — Conformance / Regression

## Legal end-to-end

```text
ITP
→ Preflight
→ SHA
→ Preservation
→ Conversion
→ Critical Validation
→ Quality Gate
→ Legal Router
→ Semantic Review
→ Legal Producer
→ bundle
→ Retrieval
→ Canonical Materialization
```

## Process end-to-end

```text
ITP
→ Preflight
→ SHA
→ Preservation
→ Conversion
→ Critical Validation
→ Quality Gate
→ Process Router
→ Semantic Review
→ Process Producer
→ Process Storage
```

## Required assertions

- ingress contracts unchanged;
- converter not duplicated;
- original Phase 1 Markdown preserved;
- structural patches traceable;
- critical rules versioned;
- no unsupported identifier rule;
- Legal bundle untouched by Process flow;
- Legal index excludes Process storage;
- Semantic Review cannot publish;
- retrieval remains Zero-Write;
- no Stable IDs;
- no vector/embedding infrastructure;
- no automatic push/merge/archive.

---

# 13. Capability → Physical Implementation Map

Esta tabela define o estado que o implementador deve confirmar no início.

| Logical capability | Physical implementation existing/proposed | Required action |
|---|---|---|
| Repository inventory | repositório real | INSPECT first |
| ITP / Ingress | localizar implementação existente | REUSE/ADAPT; create only if absent |
| Preflight | localizar implementação existente | REUSE existing FROZEN contract |
| official SHA-256 | localizar implementação existente | REUSE/ADAPT |
| Evidence Preservation | localizar storage adapter atual | REUSE/ADAPT |
| Shared Conversion Core | **`src/pipeline_juridico/` confirmed existing** | REUSE → ADAPT IN PLACE → TEST |
| ConversionEngine interface | mapear ao converter existente | thin adapter/facade only if needed |
| OCR adapter | localizar stack MarkItDown/markitdown-ocr/Gemini-compatible atual | preserve current implementation |
| Technical JSON | localizar implementação atual | REUSE/ADAPT |
| Critical-data validation | localizar; se ausente criar próximo ao core existente | CREATE only if absent |
| Phase 1 Quality Gate | localizar implementação atual | REUSE/ADAPT |
| Domain Router | localizar; se ausente criar em namespace coerente com repo real | CREATE minimal |
| Legal Semantic Review | localizar implementação existente/proposta | REUSE or create domain-isolated module |
| Legal Producer | localizar Producer atual | REUSE/ADAPT |
| Process Semantic Review | localizar; provável capacidade nova | create isolated only if absent |
| Process Producer | localizar; provável capacidade nova | create isolated only if absent |
| Process Storage | configuração/provider ainda domain-specific | adapter separado; no Legal bundle |
| Legal Retrieval | localizar retrieval atual | preserve/regression-first |
| Judicial Process Retrieval | **not in scope** | DO NOT IMPLEMENT |

---

# 14. Baselines não afetadas

Permanecem sem alteração semântica:

- PDF Source Cardinality;
- Duplicate Act Handling;
- Stable Concept Identity;
- Verification History;
- Lifecycle & Field Ownership;
- Search Execution Path;
- Chunking Strategy;
- Reranking Pipeline;
- Phase 1 Quality Gate;
- ITP/ESIC.

---

# 15. Diferenças precisas em relação à v1.0

1. adiciona Stage explícito de ITP/Ingress/Preflight/SHA/Evidence Preservation;
2. elimina pressuposto de começar com `accepted evidence`;
3. remove qualquer leitura de `pipeline/` e `producer/` como estrutura física obrigatória;
4. reconhece `src/pipeline_juridico/` como implementação real existente do conversor;
5. proíbe criação de árvore paralela apenas para seguir diagrama;
6. reforça Repository Implementation Map;
7. torna Semantic Review estruturalmente corretiva, mas não reescritora de conteúdo jurídico;
8. torna Phase 1 Markdown explicitamente imutável;
9. exige patches `before/after/reason/confidence`;
10. exige rastreabilidade por página/evidência;
11. posiciona `Papel/Nome` e problemas equivalentes em Semantic Review;
12. reforça YAML/enrichment separado por bounded context;
13. restringe Retrieval Contract ao Legal Knowledge bundle;
14. retira Judicial Process Retrieval do escopo atual;
15. proíbe índice compartilhado Legal + Process;
16. exige provenance/versioning para regras críticas de identificadores;
17. proíbe generalização de regra de selo/identificador a partir de documento único;
18. preserva todas as demais decisões FROZEN.

---

# 16. Acceptance Criteria

1. v1.0 FROZEN permanece disponível e inalterada.
2. Repository Implementation Map precede alterações.
3. Ingress → Preflight → SHA → Preservation precede conversion.
4. Existing `src/pipeline_juridico/` converter is reused.
5. No parallel converter tree is created without need.
6. Phase 1 Markdown is immutable downstream.
7. Semantic structural patch preserves original words.
8. Patch provenance includes before/after/reason/confidence.
9. Ambiguity routes to REVIEW_REQUIRED.
10. Critical validation never autocorrects.
11. Critical identifier rules have reliable/versioned specification provenance.
12. Legal and Process schemas remain isolated.
13. Only Legal Producer writes `/bundle/`.
14. Process pipeline writes only process-domain storage.
15. Retrieval v2.8 indexes only Legal Knowledge.
16. No Legal/Process shared index.
17. Judicial Process Retrieval remains unimplemented.
18. Existing Search/Chunking/Reranking semantics remain unchanged.
19. No vector DB, embeddings, new reranker or Stable IDs.
20. All affected regression/conformance tests pass before implementation stage closure.

---

**Plan Status: APPROVED — CLOSED — FROZEN**
