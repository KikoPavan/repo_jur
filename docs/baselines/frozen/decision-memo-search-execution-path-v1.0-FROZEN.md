# MEMORANDO DE DECISÃO ARQUITETURAL: SEARCH EXECUTION PATH (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 13 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v10-FROZEN.md`, `retrieval-contract-v2.4-FROZEN.md`, `legal-okf-profile-v1.3-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `external-source-ingestion-contract-v1.6-FROZEN.md`, `phase1-operational-spec-v1.0-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md`, `decision-memo-verification-history-schema-v1.0-FROZEN.md`, `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md` e `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`.

---

## 1. Problem Statement

A **Open Decision — Search Execution Path** deve definir como o retrieval localiza concepts relevantes no corpus canônico `repo_jur/bundle/` sem escrever no bundle e sem antecipar decisões ainda abertas de **Chunking Strategy** e **Reranking Pipeline**.

A decisão precisa separar quatro responsabilidades:

1. **Candidate Discovery** — como localizar concepts potencialmente relevantes;
2. **Structured Filtering** — como aplicar filtros explicitamente solicitados;
3. **Canonical Materialization** — como obter do bundle o conteúdo atual do concept selecionado;
4. **Result Assembly** — como produzir o envelope definido pelo Retrieval Contract.

A infraestrutura de busca é derivada. O bundle permanece a única fonte canônica do conteúdo jurídico.

---

## 2. Frozen Constraints

1. `repo_jur/bundle/` é a única fonte canônica do conhecimento. **[Existing FROZEN Requirement]**
2. Retrieval opera sob **Zero-Write** no bundle. **[Existing FROZEN Requirement]**
3. Chunks, índices, embeddings, caches, grafos e bancos derivados ficam fora do bundle. **[Existing FROZEN Requirement]**
4. Artefatos derivados devem ser reconstruíveis/sincronizáveis a partir do corpus canônico e da configuração/versionamento aplicável. **[Existing FROZEN Requirement]**
5. `concept_id` posicional é a canonical reference/join key. **[Existing FROZEN Requirement]**
6. Rename/move altera `concept_id`. **[Existing FROZEN Requirement]**
7. Nenhum Stable ID adicional é adotado no frontmatter. **[Existing FROZEN Requirement]**
8. O Retrieval Contract permanece agnóstico quanto a SQL, NoSQL, banco vetorial, grafo e protocolo de transporte. **[Existing FROZEN Requirement]**
9. **Chunking Strategy permanece OPEN.** Este memo não escolhe tamanho, overlap, fronteiras semânticas, página como chunk ou outra unidade de fatiamento. **[Existing FROZEN Requirement]**
10. **Reranking Pipeline permanece OPEN.** Este memo não seleciona cross-encoder, LLM reranker, RRF como reranker ou política equivalente de pós-ordenação. **[Existing FROZEN Requirement]**
11. `repo_jur_verification_history` nunca participa de trust/ranking ativo. **[Existing FROZEN Requirement]**
12. `status` pode ser lido/filtrado, mas não existe nesta baseline política universal de boost, demote ou exclusão automática por status. **[Existing FROZEN Requirement]**
13. Resultados continuam sujeitos aos requisitos de `concept_id`, `text_content`, proveniência, `page_refs` e hashes estabelecidos no Retrieval Contract. **[Existing FROZEN Requirement]**

---

## 3. Required Properties

O Search Execution Path deve possuir:

### 3.1 Exact Retrieval Capability

Deve localizar de forma eficiente:

- termos jurídicos literais;
- números de lei;
- números CNJ;
- identificadores;
- nomes;
- expressões entre aspas;
- outros tokens exatos presentes no corpus.

### 3.2 Structured Metadata Filtering

Deve suportar filtros sobre campos declarados **retrieval-relevant**, incluindo no mínimo os universais já definidos pelo Retrieval Contract quando solicitados:

- `type`;
- `status`;
- `tags`.

Filtros adicionais dependem de configuração/schema de retrieval e não tornam automaticamente todos os campos `repo_jur_*` filtráveis.

### 3.3 Canonical Fidelity

Um índice derivado é um mecanismo de localização, não uma nova fonte de verdade.

Antes da entrega de um resultado ao agente, o sistema deve ser capaz de confirmar que o `concept_id` ainda existe no bundle e materializar o conteúdo/proveniência canônicos atuais.

### 3.4 Local-First Operation

O caminho inicial deve funcionar localmente em WSL/Linux sem exigir:

- servidor remoto;
- banco vetorial;
- API de embeddings;
- GPU;
- daemon de rede.

### 3.5 Rebuildability

Corrupção ou ausência do índice não pode comprometer o corpus. O índice pode ser descartado e reconstruído.

### 3.6 Future Semantic Extension

A arquitetura deve possuir um seam para uma futura fonte de candidatos semânticos, mas não deve tornar embeddings requisito antes do fechamento das decisões que determinam sua unidade textual e governança operacional.

---

## 4. Candidate Models

### 4.1 Direct Filesystem Search

Busca diretamente os arquivos Markdown do bundle em cada consulta.

**Vantagens**

- nenhuma sincronização de índice;
- leitura direta da fonte canônica;
- excelente mecanismo de recuperação/fallback;
- baixa complexidade.

**Limitações**

- pior escalabilidade;
- filtros estruturados exigem parsing adicional;
- sem busca semântica.

### 4.2 Derived Concept-Level Lexical Index

Indexa o texto e metadados retrieval-relevant de cada **concept inteiro** em uma estrutura lexical derivada.

**Vantagens**

- busca rápida por termos exatos;
- números e identificadores;
- filtros estruturados;
- não depende de Chunking Strategy;
- totalmente local;
- reconstruível;
- auditável.

**Limitações**

- não recupera bem paráfrases/sinônimos sem expansão adicional;
- exige sincronização do índice.

### 4.3 Semantic/Vector Search

Produz representações vetoriais e busca por similaridade.

**Não pode ser normativamente ativado nesta decisão** porque sua unidade textual operacional depende de uma escolha que pertence à **Chunking Strategy**.

Este memo não decide:

- embeddings por página;
- embeddings por paragraph/chunk;
- embeddings do concept inteiro;
- modelo;
- dimensão;
- vector DB;
- ANN algorithm.

### 4.4 Hybrid Lexical + Semantic

É um desenho futuro compatível, mas sua execução completa depende da futura definição da fonte semântica de candidatos.

A Search Execution Path pode ser **hybrid-ready**, mas não deve fingir que o ramo semântico está especificado antes de Chunking Strategy.

---

## 5. Comparative Analysis

| Critério | Direct Filesystem | Lexical Index | Semantic | Hybrid |
|---|---:|---:|---:|---:|
| Exact terms | Alto | Alto | Não garantido | Alto |
| Law/process identifiers | Alto | Alto | Não garantido | Alto |
| Structured filters | Médio | Alto | Depende | Alto |
| Semantic recall | Baixo | Baixo/Médio | Alto | Alto |
| Requires Chunking Decision | Não | Não | Sim para desenho derivado segmentado | Sim para ramo semântico |
| Requires embedding infrastructure | Não | Não | Sim | Sim |
| Local-first simplicity | Alta | Alta | Variável | Variável |
| Rebuild cost | N/A | Baixo | Potencialmente alto | Potencialmente alto |
| Auditability | Alta | Alta | Menor | Mista |
| Suitable as initial official path | Sim como fallback | **Sim** | Não ainda | Como target/seam, não como requisito inicial |

---

## 6. Recommended Decision

Adotar o modelo **Lexical-First, Hybrid-Ready**.

### 6.1 Official Initial Search Path

O caminho oficial inicial é:

**Derived Concept-Level Lexical Index + Structured Metadata Filters + Canonical Materialization.**

Isto fecha Search Execution Path sem depender de uma decisão ainda não tomada sobre chunks ou embeddings.

### 6.2 Technology Boundary

A decisão normativa exige uma **capacidade de índice lexical derivado**, não um produto específico.

SQLite FTS5 é uma implementação de referência adequada ao ambiente local, mas **não é requisito arquitetural FROZEN**.

Outras implementações compatíveis podem ser substituídas sem alterar:

- bundle;
- schemas canônicos;
- Retrieval Contract;
- `concept_id`;
- interface de resultados.

### 6.3 Semantic Seam

A interface do orquestrador deve permitir adicionar futuramente uma segunda fonte de candidatos:

```text
lexical_candidates(query, filters)
semantic_candidates(query, filters)   # futuro
```

A segunda fonte permanece desativada/não normativa até que a Chunking Strategy defina a representação textual necessária e a implementação semântica seja configurada.

### 6.4 Fusion

Este memo não congela:

- RRF;
- `k=60`;
- weighted sum;
- score normalization;
- outro algoritmo de fusão.

Quando mais de uma candidate source existir, o mecanismo deve fornecer um **fusion seam** configurável.

A escolha de uma política de fusão operacional não é confundida com o Reranking Pipeline, mas também não precisa ser congelada antes da existência de duas fontes de candidatos.

### 6.5 Reranking

Permanece um seam posterior e **OPEN**.

Nenhum reranker é necessário para a execução lexical inicial.

**[New Decision Proposal]**

---

## 7. Execution Flow

### 7.1 Initial Path

```text
[ Query ]
    │
    ▼
[ Retrieval Orchestrator ]
    │
    ├──► parse explicit retrieval filters
    │
    ▼
[ Concept-Level Lexical Candidate Index ]
    │
    ▼
[ Candidate concept_id set ]
    │
    ▼
[ Canonical Materializer — read-only bundle ]
    │
    ▼
[ Retrieval Contract Validator ]
    │
    ▼
[ concept_id + text_content + provenance applicable ]
    │
    ▼
[ Consumer / Hermes ]
```

### 7.2 Future-Compatible Path

```text
                         ┌─ lexical candidates ───┐
[ Query + filters ] ────►│                       ├─► fusion seam ─► reranking seam ─► materializer
                         └─ semantic candidates ──┘      future        OPEN
                              future
```

A existência do seam não torna semantic search obrigatória.

### 7.3 Structured Filters

Filtros explicitamente solicitados devem ser aplicados de forma semanticamente consistente.

O mecanismo pode tecnicamente:

- pré-filtrar;
- pós-filtrar;
- combinar ambas as etapas;

desde que o resultado respeite o filtro solicitado.

Não existe exclusão automática universal de `draft` ou `deprecated` criada por este memo.

---

## 8. Derived Indexes

### 8.1 Index Unit

Antes do fechamento de Chunking Strategy, a unidade normativa do índice lexical é o **concept document**.

Cada registro derivado deve estar associado ao `concept_id`.

O índice pode armazenar:

- texto indexável do concept;
- campos retrieval-relevant;
- fingerprint de sincronização;
- informações técnicas necessárias ao índice.

### 8.2 Canonical Join Key

`concept_id` é a chave canônica de associação com o bundle.

A implementação **pode** usar IDs internos/surrogate row IDs para eficiência física, desde que:

- sejam estritamente derivados;
- não sejam expostos como identidade do concept;
- não substituam `concept_id`;
- possam ser descartados/reconstruídos.

### 8.3 Location

Índices devem residir fora de `/bundle/`.

A localização física é configurável, por exemplo:

- runtime/data directory do mecanismo de retrieval;
- cache/data directory do projeto fora do bundle;
- worktree externo ao bundle, se explicitamente ignorado pelo Git.

Este memo não exige `HERMES_HOME` como storage do índice.

### 8.4 Persistence

O índice lexical pode ser persistente para desempenho, mas é sempre:

- derivado;
- descartável;
- reconstruível;
- não canônico.

---

## 9. Synchronization / Rebuild

### 9.1 Source of Synchronization

A sincronização deve ser derivada do estado real do bundle, não depender exclusivamente de:

- `mtime`;
- Git hook;
- ação do `juridico-cli`.

### 9.2 Concept Fingerprint

Para um índice persistente, a implementação deve manter por concept um fingerprint derivado suficiente para detectar desatualização, baseado no conteúdo canônico relevante e na versão/configuração do indexador.

Um modelo aceitável inclui:

```text
concept_id
content_fingerprint
index_schema_version
indexer_logical_version
```

O algoritmo físico do fingerprint pode ser definido pela implementação.

### 9.3 Incremental Sync

O indexador deve ser capaz de detectar:

- **create** → inserir novo `concept_id`;
- **content update** → reindexar;
- **rename/move** → remover associação antiga + inserir novo `concept_id`;
- **delete** → purgar/inativar registro órfão.

Rename/move não preserva identidade antiga por heurística.

### 9.4 Invocation

A sincronização pode ocorrer:

- explicitamente por comando;
- na inicialização;
- antes de consulta quando o runtime detectar índice stale;
- por mecanismo operacional equivalente.

Git hooks podem ser usados como otimização, mas não são requisito de correção.

### 9.5 Full Rebuild

Deve existir operação de rebuild completo que:

1. descarta o índice derivado;
2. percorre o bundle atual;
3. recalcula registros a partir dos concepts;
4. não escreve no bundle.

---

## 10. Failure / Fallback

### 10.1 Trigger

Fallback ocorre quando o índice requerido estiver:

- ausente;
- incompatível;
- stale sem possibilidade de sync imediato;
- corrompido;
- indisponível durante rebuild;
- falhando na inicialização.

### 10.2 Official Fallback

O fallback normativo é **Direct Read-Only Filesystem Search**.

`ripgrep` pode ser usado como implementação otimizada de referência, mas não é requisito arquitetural.

Uma implementação equivalente pode utilizar:

- leitura/parsing local;
- biblioteca lexical;
- outra ferramenta determinística local.

### 10.3 Degraded Capability

Fallback não promete equivalência de ranking/performance ao índice.

O runtime deve sinalizar modo degradado quando isso for operacionalmente relevante.

Se uma capacidade não puder ser mantida no fallback — por exemplo, semântica futura — ela deve ser explicitamente declarada indisponível, e não simulada.

### 10.4 Canonical Correctness

Mesmo em fallback:

- o bundle continua read-only;
- `concept_id` é derivado do path atual;
- frontmatter é lido do concept;
- proveniência segue Retrieval Contract.

---

## 11. Canonical Materialization

### 11.1 Index Is Not Authority

O índice localiza candidates, mas não substitui o concept.

Antes de retornar evidência ao agente, o materializer deve garantir que o candidate ainda corresponde a um `concept_id` existente no bundle.

### 11.2 Returned Content

O `text_content` entregue pelo retrieval deve ser materializado a partir do conteúdo canônico atual ou validado contra ele.

Isso impede que um índice stale transforme texto derivado antigo em falsa fonte canônica.

### 11.3 Granularity Before Chunking Decision

Esta decisão não fixa unidade de fragmentação.

Até Chunking Strategy ser fechada, a implementação pode:

- localizar o concept;
- materializar o concept ou um excerpt determinístico para apresentação;

desde que não persista uma estratégia de chunks como requisito arquitetural e continue cumprindo os limites/interface do Retrieval Contract.

---

## 12. Ranking and Trust Boundaries

### 12.1 Relevance

A busca lexical inicial pode usar o score nativo/derivado de seu mecanismo para ordenar candidatos.

O contrato não exige que scores sejam:

- comparáveis entre engines;
- persistidos no bundle;
- deterministicamente idênticos entre implementações.

### 12.2 Trust

`verified` pode participar de `trust_tier` conforme Retrieval Contract.

`repo_jur_verification_history`:

- pode ser exposto para auditoria;
- nunca participa de trust ativo;
- nunca gera boost/demote de ranking.

### 12.3 Status

`status` é dado canônico consultável.

Este memo não cria regra automática de:

- esconder `deprecated`;
- demover `draft`;
- boost de `stable`.

Tais comportamentos só ocorrem quando definidos por filtro/política separada compatível com o Retrieval Contract.

---

## 13. Invariants

1. Bundle é fonte canônica; índice é derivado.
2. Retrieval é Zero-Write no bundle.
3. Search Execution Path inicial não depende de embeddings.
4. Search Execution Path inicial não depende de Chunking Strategy.
5. Índice lexical inicial é concept-level.
6. `concept_id` é canonical join key.
7. IDs internos derivados não constituem identidade do concept.
8. SQLite FTS5 não é requisito arquitetural; é possível implementação de referência.
9. Vector DB, HNSW e embedding model não são selecionados.
10. RRF e `k=60` não são congelados.
11. Reranking Pipeline permanece OPEN.
12. Semantic retrieval permanece seam futuro.
13. Índices ficam fora do bundle.
14. Índices persistentes devem ser reconstruíveis.
15. Sincronização não depende exclusivamente de `mtime` ou Git hooks.
16. Rename/move invalida o `concept_id` antigo no índice.
17. Delete remove/invalida derived entries órfãs.
18. Filesystem read-only search é fallback normativo.
19. `ripgrep` é opcional, não requisito.
20. Fallback pode ter capacidade/performance degradada e deve sinalizá-la quando relevante.
21. Resultado final deve ser materializado/validado contra o concept canônico atual.
22. Histórico de verificação não participa do ranking/trust ativo.
23. Nenhuma política automática de status é criada.
24. Este memo não define chunks.
25. Este memo não define reranker.

---

## 14. Required Baseline Updates

Após aprovação e congelamento:

### 14.1 Retrieval Contract

Criar versão controlada que:

- marque **Search Execution Path** como CLOSED;
- registre **Lexical-First, Hybrid-Ready**;
- defina concept-level lexical index como caminho inicial;
- registre direct filesystem search como fallback;
- registre canonical materialization;
- mantenha Chunking Strategy OPEN;
- mantenha Reranking Pipeline OPEN;
- corrija referências internas antigas de Legal OKF Profile/Lifecycle para as baselines atuais;
- preserve technology-neutrality do contrato.

### 14.2 Architecture Phase 2

Criar versão controlada que:

- marque Search Execution Path como CLOSED;
- substitua “retrieval technology-neutral / path open” pelo caminho inicial lexical derivado + fallback;
- registre semantic candidate seam futuro;
- mantenha Chunking Strategy e Reranking Pipeline como próximas decisões.

### 14.3 Baselines sem alteração normativa necessária

Não é necessária nova versão de:

- Legal OKF Profile;
- Lifecycle & Field Ownership;
- Concept Identity & Physical Structure;
- ESIC;
- Phase 1 Operational Specification.

Search Execution Path não altera seus schemas ou ownership.

---

## 15. Remaining Open Questions

Permanecem exatamente:

1. **Chunking Strategy**
2. **Reranking Pipeline**

A ativação normativa de uma camada semântica baseada em representações segmentadas deve respeitar a futura Chunking Strategy.

Detalhes de engine do índice lexical, storage driver e ferramenta de filesystem scan são escolhas de implementação, não novas Open Decisions arquiteturais.

---

## 16. Technical Review Corrections

A revisão técnica corrigiu os seguintes pontos da proposta inicial:

1. atualizou as referências de `Arquitetura v9` → `v10` e `ESIC v1.5` → `v1.6`, incluindo a Phase 1 Operational Specification atual;
2. removeu a contradição entre “neutralidade tecnológica” e a imposição de SQLite FTS5 + banco vetorial + HNSW;
3. preservou SQLite FTS5 apenas como implementação de referência possível, não requisito FROZEN;
4. removeu embeddings por página, pois isso antecipava Chunking Strategy;
5. removeu HNSW e qualquer vector DB específico;
6. substituiu “hybrid obrigatório agora” por **Lexical-First, Hybrid-Ready**;
7. removeu RRF obrigatório e a constante `k=60`;
8. preservou um fusion seam futuro sem confundi-lo com Reranking Pipeline;
9. manteve Reranking Pipeline explicitamente OPEN;
10. tornou o índice lexical concept-level até a decisão de chunking;
11. permitiu IDs internos derivados para implementação, sem substituir `concept_id`;
12. removeu `mtime` como critério exclusivo de sincronização;
13. removeu Git hooks e `juridico-cli` como mecanismos obrigatórios de correção do índice;
14. introduziu fingerprint/versionamento do índice para detectar staleness;
15. tornou filesystem search o fallback normativo, sem exigir `ripgrep`;
16. explicitou que fallback é degradado e não promete equivalência semântica/ranking;
17. adicionou **Canonical Materialization**, impedindo que texto stale do índice seja tratado como fonte canônica;
18. removeu dependência obrigatória de `HERMES_HOME` para storage de índices;
19. removeu qualquer política automática de exclusão/demotion por `status`;
20. manteve `repo_jur_verification_history` estritamente fora de trust/ranking ativo.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
