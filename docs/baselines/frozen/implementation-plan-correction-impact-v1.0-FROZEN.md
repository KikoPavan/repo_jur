# CORREÇÃO CONTROLADA DO IMPLEMENTATION PLAN — IMPACTO E AMENDMENTS

**Versão:** 1.0  
**Data:** 15 de agosto de 2026  
**Status:** APPROVED — CLOSED — FROZEN  
**Origem:** `Correção controlada do plano de implementação repo_jur.md`

## 1. Baseline preservada

`implementation-plan-repo-jur-v1.0-FROZEN.md` permanece intacto para rastreabilidade.

Esta correção não o sobrescreve.

## 2. Impacto

### 2.1 Ingress / Preflight / Evidence Preservation
O plano v1.0 pulou a implementação explícita de:
`ITP/Ingress → Preflight → official SHA-256 → Evidence Preservation`.

Impacto: **Implementation Plan**.  
As decisões ITP/ESIC existentes continuam válidas e não são redesenhadas.

### 2.2 Caminhos físicos
A Arquitetura v14 e a Technical Spec v1.1 ainda poderiam ser lidas como imposição física de `pipeline/` e `producer/`.

O estado real informado do repositório possui o conversor estabilizado em:

`src/pipeline_juridico/`

Impacto: **Architecture + Technical Spec + Implementation Plan**.

Nova regra: nomes de capacidades/pacotes na documentação são **logical targets**, não obrigação de relocação física.

### 2.3 Semantic Review / Enrichment
A decisão v1.0 precisa de invariantes adicionais para impedir reescrita jurídica disfarçada de enriquecimento.

Impacto: **Decision Memo + Architecture + Technical Spec + Plan**.

### 2.4 Retrieval bounded-context scope
O Retrieval Contract atual lê o Legal Knowledge `/bundle/`, mas a reconciliação exige declarar formalmente que Judicial Process Retrieval não está coberto.

Impacto: **Retrieval Contract + Architecture + Technical Spec + Plan**.

### 2.5 Critical-data validation
A seam permanece não mutante. É acrescentada governança das regras determinísticas: regras de formato/comprimento/check digit devem ter fonte técnica/normativa confiável e versionada.

Impacto: **Decision Memo + Technical Spec + Plan**.

## 3. Baselines / memos afetados

Novas versões controladas:

- `decision-memo-physical-layout-logical-capability-mapping-v1.0-FROZEN.md`
- `decision-memo-semantic-review-enrichment-layer-v1.1-FROZEN.md`
- `decision-memo-post-ocr-critical-data-validation-seam-v1.1-FROZEN.md`
- `decision-memo-retrieval-bounded-context-scope-v1.0-FROZEN.md`
- `retrieval-contract-v2.8-FROZEN.md`
- `arquitetura-fase2-repo-jur-v15-FROZEN.md`
- `technical-implementation-spec-repo-jur-v1.2-FROZEN.md`
- `implementation-plan-repo-jur-v1.1-FROZEN.md`

Permanecem inalterados:

- ITP/1.0;
- ESIC v1.6;
- Phase 1 Quality Gate;
- Phase 1 Operational Spec v1.1;
- PDF Source Cardinality;
- Duplicate Act Handling;
- Stable Concept Identity;
- Verification History;
- Lifecycle & Field Ownership;
- Search Execution Path;
- Chunking Strategy;
- Reranking Pipeline.

## 4. Decisões que permanecem intactas

- Shared Conversion Core;
- Legal Knowledge × Judicial Process;
- reuse do conversor;
- literal Phase 1 Markdown;
- Producer-only publication;
- Legal `/bundle/` exclusivo;
- critical validation não mutante;
- Quality Gate independente;
- Domain Router conservador;
- Retrieval Zero-Write;
- no vector DB / embeddings / new reranker / Stable IDs.

## 5. Traceability

```text
Implementation Plan v1.0 FROZEN
        ↓ controlled correction
Decision/amendment set (15 Aug 2026)
        ↓
Retrieval Contract v2.8
        ↓
Architecture v15
        ↓
Technical Implementation Spec v1.2
        ↓
Implementation Plan v1.1
```

**Correction Status: APPROVED — CLOSED — FROZEN**
