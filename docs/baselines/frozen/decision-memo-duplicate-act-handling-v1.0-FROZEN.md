# MEMORANDO DE DECISÃO ARQUITETURAL: TRATAMENTO DE ATOS DUPLICADOS (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v5-FROZEN.md`, `external-source-ingestion-contract-v1.1-FROZEN.md`, `legal-okf-profile-v1.1-FROZEN.md`, `concept-identity-physical-structure-v1.1-FROZEN.md`, `lifecycle-field-ownership-v1.1-FROZEN.md`, `retrieval-contract-v2.2-FROZEN.md` e `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`.

---

## 1. Problem Statement

A **Open Decision — Duplicate Act Handling** deve distinguir com segurança:

1. mesma evidência física;
2. PDFs fisicamente diferentes que representam o mesmo ato jurídico;
3. republicação/retificação;
4. atos autônomos que apenas compartilham processo, número, título, data, PDF ou outros sinais parciais.

O objetivo é evitar tanto concepts duplicados quanto fusões destrutivas.

---

## 2. Frozen Constraints

- `concept_id` deriva do caminho e é posicional. **[Existing FROZEN Requirement]**
- SHA-256 identifica bytes; não identifica concept, ato jurídico ou autenticidade. **[Existing FROZEN Requirement]**
- O mesmo PDF/hash pode sustentar múltiplos concepts. **[Existing FROZEN Requirement]**
- 1 PDF → `repo_jur_pdf_hash`; 2+ PDFs → `repo_jur_pdf_hashes`; nunca ambos. **[Existing FROZEN Requirement]**
- `sources` registra proveniência e, em multi-PDF, cada PDF possui `sources[].id`. **[Existing FROZEN Requirement]**
- `status` é Human-Owned e não pode ser alterado autonomamente pelo Produtor. **[Existing FROZEN Requirement]**
- `generated.at` representa a última mudança significativa do conteúdo atual, não uma execução. **[Existing FROZEN Requirement]**
- `verified` exige evento real e só deixa de ser reutilizável quando a mudança material atinge o objeto verificado. **[Existing FROZEN Requirement]**
- `Stable Concept Identity` continua aberta; esta decisão não cria UUID nem identidade persistente. **[Existing FROZEN Requirement]**

---

## 3. Definitions

### 3.1 Mesma Evidência Física

Bytes idênticos, demonstrados pelo mesmo SHA-256. Isso não implica identidade jurídica. **[New Decision Proposal]**

### 3.2 Sinais de Identidade Jurídica

Campos do Legal OKF Profile funcionam como **sinais estruturados**, não como primary key universal.

Exemplos: metadados de lei; processo, tribunal, data e relator; número de tema; número de precedente. Nenhuma combinação fixa deve ser tratada como suficiente em todos os casos.

Motivos: um processo pode possuir vários atos; o mesmo tribunal/processo/data pode conter decisões distintas; jurisdição/autoridade pode não estar totalmente discriminada; campos podem estar ausentes.

**[New Decision Proposal]**

### 3.3 Mesmo Ato Jurídico Lógico

Duas evidências somente podem ser consolidadas automaticamente quando:

1. os sinais estruturados disponíveis são compatíveis;
2. não há conflito de autoridade/origem oficial;
3. o conteúdo jurídico relevante é equivalente;
4. não há indício de atos autônomos;
5. a equivalência pode ser estabelecida deterministicamente ou foi confirmada por revisão humana.

**[New Decision Proposal]**

### 3.4 Variante Física Não Material

PDFs diferentes em bytes podem representar o mesmo ato por diferenças de assinatura, compressão, marca d’água ou republicação sem mudança jurídica. PDF diferente, isoladamente, não significa nova versão. **[New Decision Proposal]**

### 3.5 Mudança Material

Mudança relevante de teor, significado, dispositivo, tese, ementa, páginas verificadas ou proveniência material coberta pela revisão transforma o candidato em `version/replacement candidate` e bloqueia fusão automática. **[New Decision Proposal]**

### 3.6 Ato Juridicamente Distinto

Atos autônomos permanecem separados, mesmo que compartilhem processo, PDF, tribunal, data ou título. Uma lei ou decisão nova que altera outra é um novo ato, não mera duplicata. **[Existing FROZEN Requirement + New Decision Proposal]**

---

## 4. Duplicate Scenarios

### 4.1 Mesmo SHA-256

Hash conhecido significa mesma evidência física.  
- mesmo PDF + novo ato autônomo → **NEW CONCEPT**;
- mesmo ato já representado → seguir idempotência;
- nunca rejeitar apenas pelo hash.  
**[Existing FROZEN Requirement]**

### 4.2 Mesmo PDF obtido por URLs diferentes

Se os bytes são idênticos, continua existindo uma única evidência PDF. Outro locator de coleta não cria automaticamente outra fonte PDF em `sources`. `sources[].resource` deve referenciar a evidência preservada utilizada pelo pipeline. **[New Decision Proposal]**

### 4.3 PDFs diferentes, mesmo ato e conteúdo equivalente

Se a equivalência lógica/material estiver confirmada:
- manter um único concept;
- adicionar as evidências PDF distintas em `sources`;
- migrar singular→plural quando passar de 1 para 2+ PDFs;
- preservar ownership e avaliar `verified`;
- atualizar `generated.at` se a ampliação de proveniência for mudança significativa.

Sem equivalência segura → **HUMAN REVIEW**.  
**[New Decision Proposal]**

### 4.4 Republicação sem mudança material

Pode permanecer no mesmo concept. O Produtor não altera `status` automaticamente. Se houver nova evidência PDF distinta e equivalente, ela pode ser adicionada à proveniência; se forem os mesmos bytes, a cardinalidade física não muda. **[New Decision Proposal]**

### 4.5 Retificação ou nova publicação com mudança material

Proibido automaticamente:
- fundir;
- sobrescrever;
- declarar `status: deprecated`;
- criar slug `_v2`;
- presumir equivalência.

Resultado: **HUMAN REVIEW REQUIRED**. A governança humana decidirá atualização do mesmo concept, criação de concept distinto, depreciação explícita e links entre versões/atos. **[New Decision Proposal]**

### 4.6 Mesmo processo com atos distintos

Número de processo não é identidade do concept. Cada ato autônomo permanece separado. **[Existing FROZEN Requirement]**

### 4.7 Um PDF contendo vários atos

Cada ato autônomo pode gerar seu próprio concept e todos podem compartilhar o mesmo `repo_jur_pdf_hash`. **[Existing FROZEN Requirement]**

### 4.8 Vários PDFs sustentando um concept

2+ PDFs aplicáveis → `sources[].id` + `repo_jur_pdf_hashes`; singular omitido. **[Existing FROZEN Requirement]**

---

## 5. Decision Models

### Modelo A — Physical Identity Only
Rejeitado: SHA-256/URL não representam identidade jurídica.

### Modelo B — Metadata Identity Only
Rejeitado: o perfil atual não possui uma chave universal suficiente e metadados podem colidir.

### Modelo C — Multi-layered Conservative Resolution
Combina:
1. identidade física;
2. sinais jurídicos;
3. equivalência material;
4. autonomia jurídica;
5. revisão humana na ambiguidade.

**Recomendado. [New Decision Proposal]**

---

## 6. Recommended Decision

Adotar o **Modelo C — Multi-layered Conservative Resolution**.

> O sistema só consolida automaticamente evidências fisicamente diferentes no mesmo concept quando identidade lógica e equivalência material puderem ser estabelecidas sem ambiguidade. Na dúvida, preserva o bundle e exige revisão humana.

---

## 7. Deterministic Decision Flow

```text
CANDIDATO ACEITO
      ↓
SHA-256
      ↓
resolver unidade jurídica candidata
      ├─ mesmo PDF + outro ato autônomo → NEW CONCEPT
      ↓
existe concept candidato?
      ├─ não → NEW CONCEPT
      ↓
mesma evidência física?
      ├─ sim → inputs/config/versão equivalentes e sem mudança canônica?
      │          ├─ sim → NO-OP
      │          └─ não → REGENERATE / UPDATE
      ↓
PDF fisicamente diferente
      ↓
equivalência lógica + material segura?
      ├─ sim → ADD SOURCE / UPDATE CARDINALITY
      └─ não → ato claramente distinto?
                 ├─ sim → NEW CONCEPT
                 └─ não → HUMAN REVIEW
```

### NO-OP
Exige mesmo ato, mesma evidência relevante, inputs/configuração/versão lógica equivalentes, nenhuma nova proveniência canônica e nenhuma mudança significativa. Hash + `concept_id` isoladamente não bastam.

### REGENERATE / UPDATE
Segue o Lifecycle & Field Ownership. `generated.at` só muda se houver alteração significativa.

### ADD SOURCE / UPDATE CARDINALITY
Nova evidência PDF distinta e equivalente é adicionada em `sources`; singular→plural é aplicado somente após mapping completo e validado.

### NEW CONCEPT
Usado para ato juridicamente distinto ou nova unidade autônoma contida em evidência já conhecida.

### HUMAN REVIEW
Usado para mudança material, colisão não resolvida ou equivalência não segura. A escrita automática conflitante é bloqueada. Este memo não prescreve painel, fila ou staging específico.

---

## 8. Effects on `sources` and Hashes

### 8.1 Outro locator, mesmos bytes
Não criar uma segunda evidência PDF somente porque o download veio de outro URL.

### 8.2 Segunda evidência PDF realmente distinta

```yaml
sources:
  - id: "source_pdf_a"
    resource: "<source-a-resource>"
  - id: "source_pdf_b"
    resource: "<source-b-resource>"

repo_jur_pdf_hashes:
  source_pdf_a: "<sha256-64-hex>"
  source_pdf_b: "<sha256-64-hex>"
```

`repo_jur_pdf_hash` deve ser removido apenas após o mapping plural estar válido.

### 8.3 Fontes não-PDF
Podem constar em `sources`, mas não em `repo_jur_pdf_hashes`.

---

## 9. Lifecycle and `verified`

### `status`
É Human-Owned. Detecção de duplicata, republicação ou retificação nunca depreca automaticamente um concept.

### `generated.at`
- rebuild puramente técnico sem mudança significativa → preservar;
- mudança significativa de conteúdo/proveniência canônica → atualizar.

### `verified`
Pode permanecer quando o objeto verificado continua equivalente. Se mudança material atingir o objeto verificado, os eventos anteriores não podem ser copiados para o `verified` ativo sem nova verificação real.

---

## 10. Ambiguity Handling

### Colisão de slug
Resolver apenas com identificadores oficiais já disponíveis. Não inventar metadados e não criar `_v2` arbitrariamente. Persistindo conflito → HUMAN REVIEW.

### Metadados compatíveis, conteúdo divergente
Não fundir automaticamente. Classificar como `version/replacement candidate` ou ato potencialmente distinto.

### Metadados incompletos
Não preencher por inferência apenas para deduplicação. Sem identidade demonstrável, não consolidar automaticamente.

---

## 11. Invariants

1. SHA-256 nunca é identidade jurídica.
2. URL nunca é identidade jurídica.
3. Filename/slug nunca é identidade jurídica.
4. `concept_id` é posicional, não stable identity.
5. Número de processo isolado nunca identifica um ato.
6. Metadados estruturados são sinais, não primary key universal.
7. Um PDF pode sustentar múltiplos concepts.
8. Dois PDFs diferentes só são consolidados após equivalência segura.
9. Mesmos bytes encontrados por URLs diferentes continuam sendo uma evidência física.
10. Mudança material não é fundida automaticamente.
11. `status` não é alterado automaticamente.
12. `_v2`, UUID ou outro mecanismo de versionamento não é criado por esta decisão.
13. `verified` segue materialidade.
14. Cardinalidade singular/plural permanece intacta.
15. Ambiguidade exige revisão humana.
16. Retrieval e sistemas externos permanecem Zero-Write.

---

## 12. Required Baseline Updates After Approval

Após aprovação/FROZEN:

- **Concept Identity & Physical Structure:** fechar `Duplicate Act Handling` e incorporar regras de equivalência, colisão e consolidação conservadora.
- **Lifecycle & Field Ownership:** fechar a decisão e registrar que `status` não muda automaticamente; incorporar `ADD SOURCE` e `HUMAN REVIEW`.
- **External Source Ingestion Contract:** fechar `Duplicate Act Handling`, distinguir múltiplos locators dos mesmos bytes de múltiplas evidências e integrar o resultado de deduplicação ao preflight.
- **Arquitetura Fase 2:** marcar `Duplicate Act Handling` como CLOSED e removê-la da lista de próximas decisões.
- **Legal OKF Profile / PDF Source Cardinality / Retrieval Contract:** nenhuma alteração de schema ou regra é necessária por esta decisão.

---

## 13. Remaining Open Questions

Permanecem abertas:
- Stable Concept Identity
- Verification History Schema
- Ingress Transport Protocol
- Phase 1 Quality Gate

As Open Decisions de retrieval (`Search Execution Path`, `Chunking Strategy`, `Reranking Pipeline`) não são alteradas.

Nenhum novo campo YAML é criado.

---

## 14. Technical Review Corrections

A revisão técnica corrigiu a proposta inicial nos seguintes pontos:

1. metadados deixaram de ser tratados como identidade jurídica absoluta;
2. `tipo de decisão processual` foi removido como pseudo-campo inexistente no perfil;
3. PDF diferente deixou de significar nova versão;
4. depreciação automática foi removida porque `status` é Human-Owned;
5. slug `_v2` automático foi removido para não resolver silenciosamente Stable Concept Identity;
6. No-Op passou a respeitar inputs/configuração/versão lógica;
7. locator alternativo foi separado de segunda evidência PDF;
8. `sources[].resource` passou a apontar à evidência preservada, não automaticamente à URL de coleta;
9. painel/staging específico do `juridico-cli` deixou de ser prescrito;
10. `generated.at` foi alinhado à última mudança significativa;
11. `verified` permanece dependente da materialidade do objeto efetivamente verificado;
12. o ESIC foi incluído entre as baselines que precisarão de sincronização após aprovação.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
