# MEMORANDO DE DECISÃO ARQUITETURAL: RERANKING PIPELINE (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 14 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v12-FROZEN.md`, `retrieval-contract-v2.6-FROZEN.md`, `legal-okf-profile-v1.3-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `decision-memo-search-execution-path-v1.0-FROZEN.md`, `decision-memo-chunking-strategy-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md` e `decision-memo-verification-history-schema-v1.0-FROZEN.md`.

---

## 1. Problem Statement

A **Open Decision — Reranking Pipeline** deve definir se o retrieval do `repo_jur` possui uma etapa adicional de reordenação de candidates e, caso exista, quais são seus limites.

A decisão deve preservar a separação entre:

1. **candidate discovery**;
2. **structured filtering**;
3. **optional reranking**;
4. **canonical materialization**;
5. **result assembly**.

Reranking atua somente sobre **relevance em runtime**.

Ele não determina:

- confiança jurídica;
- validade jurídica;
- autoridade da fonte;
- lifecycle;
- identidade do concept;
- publicação no bundle.

---

## 2. Frozen Constraints

1. `/bundle/` é a única fonte canônica. **[Existing FROZEN Requirement]**
2. Retrieval é Zero-Write sobre `/bundle/`. **[Existing FROZEN Requirement]**
3. Search Execution Path está CLOSED como **Lexical-First, Hybrid-Ready**. **[Existing FROZEN Requirement]**
4. O índice lexical inicial permanece concept-level. **[Existing FROZEN Requirement]**
5. Chunking Strategy está CLOSED como **Structural Block-First, Page-Aware, Size-Profiled**. **[Existing FROZEN Requirement]**
6. Chunks são derivados, descartáveis e reconstruíveis. **[Existing FROZEN Requirement]**
7. `concept_id` permanece a canonical reference/join key. **[Existing FROZEN Requirement]**
8. Canonical materialization é obrigatória antes da entrega final do resultado. **[Existing FROZEN Requirement]**
9. `repo_jur_verification_history` nunca participa de trust ou ranking ativo. **[Existing FROZEN Requirement]**
10. `status` pode ser lido/filtrado, mas não existe política FROZEN de boost, demote ou exclusão automática baseada em `status`. **[Existing FROZEN Requirement]**
11. `verified` pode participar da derivação de `trust_tier`, mas relevance e trust são dimensões distintas. **[Existing FROZEN Requirement]**
12. Nenhum embedding model, vector DB, ANN/HNSW, RRF, cross-encoder ou LLM reranker foi previamente selecionado. **[Existing FROZEN Requirement]**
13. Scores derivados não são dados canônicos e não precisam ser comparáveis entre engines. **[Existing FROZEN Requirement]**
14. Nenhum componente de retrieval pode alterar `verified`, `status`, frontmatter ou conteúdo canônico. **[Existing FROZEN Requirement]**

---

## 3. Required Properties

### 3.1 Optionality

O corpus e o retrieval básico devem funcionar corretamente sem reranker.

Reranking é uma melhoria opcional de relevance, nunca uma dependência de disponibilidade do corpus.

### 3.2 Conditional Execution

Quando habilitado, reranking pode ser aplicado somente quando uma política de runtime determinar que seu custo adicional é justificável.

A arquitetura não exige um classificador binário específico de `Exact vs Conceptual`.

### 3.3 Fail-Open

Falha, timeout ou indisponibilidade do reranker não pode derrubar a busca básica.

O fallback preserva a ordem produzida pelo estágio anterior de candidate discovery/filtering.

### 3.4 Relevance-Only Boundary

O reranker deve ordenar por **relevance query↔candidate**.

Ele não pode converter:

- `trust_tier`;
- `verified`;
- `status`;
- histórico de verificação;
- antiguidade;
- autoridade presumida;

em multiplicadores implícitos de relevance.

### 3.5 Technology Neutrality

A arquitetura define uma interface de reranking, não um modelo, fornecedor ou engine.

### 3.6 Profiled Runtime Parameters

Parâmetros de custo/latência/limites pertencem a um **Reranking Profile versionado**, não a constantes arquiteturais arbitrárias.

### 3.7 Observability

A execução deve permitir distinguir:

- reranking não configurado;
- bypass por política;
- reranking aplicado;
- reranking falhou e houve fallback.

---

## 4. Candidate Models

### 4.1 No Reranking

Usa a ordem produzida pelo candidate discovery.

**Vantagens**
- menor complexidade;
- menor latência;
- operação offline natural;
- melhor fallback possível.

**Limitações**
- pode não melhorar casos em que o score primário não representa bem relevance contextual.

### 4.2 Deterministic Relevance Reranking

Reordena por sinais estritamente ligados à correspondência query↔candidate, como:

- exact phrase match;
- title/query term coverage;
- field-specific lexical match;
- outros sinais determinísticos explicitamente retrieval-relevant.

Não pode usar trust/lifecycle como relevance implícita.

### 4.3 Learned / Semantic Reranking

Uma implementação especializada pode avaliar query e candidate conjuntamente.

Pode ser local ou remota.

Esta decisão não fixa:

- cross-encoder;
- modelo;
- provider;
- inference engine;
- hardware.

### 4.4 Generative / LLM Reranking

É uma implementação possível da interface, mas não é requisito nem default arquitetural.

### 4.5 Conditional Profile-Governed Reranking

O pipeline básico funciona sempre; um Reranking Profile determina se uma implementação de reranking é chamada para determinada requisição.

**Modelo recomendado.**

---

## 5. Comparative Analysis

| Critério | No Rerank | Deterministic Relevance | Learned/Semantic | Generative | Conditional/Profile-Governed |
|---|---:|---:|---:|---:|---:|
| Disponibilidade básica | Alta | Alta | Depende | Depende | **Alta** |
| Latência adicional | Nenhuma | Baixa | Variável | Variável | **Controlável** |
| Custo | Nenhum | Baixo | Variável | Variável | **Controlável** |
| Offline | Sim | Sim | Depende | Depende | **Sim, com bypass/fallback** |
| Auditabilidade | Alta | Alta | Variável | Variável | **Alta no controle de pipeline** |
| Technology-neutral | Sim | Sim | Sim se abstraído | Sim se abstraído | **Sim** |
| Fail-open natural | Sim | Sim | Requer política | Requer política | **Sim** |
| Adequado como arquitetura oficial | Fallback | Implementação possível | Implementação possível | Implementação possível | **Sim** |

---

## 6. Recommended Decision

Adotar **Optional, Conditional, Profile-Governed, Fail-Open Reranking**.

### 6.1 Optional

O Reranking Pipeline pode estar desabilitado.

Quando desabilitado:

```text
candidate discovery
        ↓
structured filtering
        ↓
canonical materialization
        ↓
result assembly
```

### 6.2 Conditional

Quando habilitado, uma política configurada no Reranking Profile decide se a requisição passa pelo reranker.

A arquitetura não fixa:

- regex de CNJ;
- regex de leis;
- classificação `Exact/Conceptual`;
- classifier ML/LLM;
- threshold de confiança.

Essas são políticas de implementação/calibração.

### 6.3 Profile-Governed

Candidate limits, timeouts e demais parâmetros operacionais são versionados no profile.

### 6.4 Fail-Open

Qualquer falha no reranker retorna à ordenação anterior válida.

Não existe dependência obrigatória de um “heuristic fallback reranker”.

### 6.5 Relevance-Only

O reranker altera somente a ordem de relevance da requisição atual.

**[New Decision Proposal]**

---

## 7. Pipeline Position

Fluxo oficial:

```text
query
  ↓
candidate discovery
  ↓
structured filtering
  ↓
reranking decision seam
  ├─ bypass ──────────────────────┐
  │                               │
  └─ enabled → optional reranker ─┤
                                  ↓
                       canonical materialization
                                  ↓
                         result assembly
```

### 7.1 Why Before Final Materialization

Reranking pode operar sobre representações derivadas já atribuídas a `concept_id` para evitar materialização completa desnecessária de todos os candidates.

### 7.2 Mandatory Final Guard

Antes de entregar qualquer resultado ao consumidor:

- confirmar que o `concept_id` ainda existe;
- materializar/validar o conteúdo canônico atual;
- reconstruir proveniência aplicável.

Se um candidate não puder ser materializado, ele não é entregue como resultado grounded.

---

## 8. Inputs and Outputs

### 8.1 Input

O contrato lógico mínimo do reranker inclui:

```text
query
candidate list
Reranking Profile
```

Cada candidate deve possuir, conforme a granularidade ativa:

- `concept_id`;
- derived candidate reference;
- literal candidate text ou representation necessária ao engine;
- primary rank;
- primary score quando disponível;
- retrieval-relevant fields explicitamente permitidos.

### 8.2 Chunk Candidates

Quando o candidate for chunk:

- `concept_id` continua a canonical join key;
- chunk reference é derivada;
- `text_content` continua literal/contíguo conforme Chunking Strategy;
- `page_refs`/proveniência continuam sujeitos às regras do Retrieval Contract.

### 8.3 Concept Candidates

Quando o candidate for concept-level, o reranker pode usar representação derivada do concept compatível com seu engine.

Isto não transforma a representação derivada em fonte canônica.

### 8.4 Output

O reranker retorna:

- candidate references;
- nova ordem;
- score de relevance quando o engine produzir um;
- identificador/método de reranking derivado.

O output não altera o candidate original no bundle.

---

## 9. Reranking Profile

O Reranking Profile é configuração operacional versionada fora do bundle.

Estrutura conceitual:

```yaml
profile_version: "..."
enabled: true

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

### 9.1 Parameters

O profile pode definir:

- habilitação;
- trigger policy;
- candidate pool limit;
- timeout;
- implementation;
- configuration fingerprint;
- observability level.

### 9.2 Not Frozen

Esta decisão não congela:

- `candidate_pool_limit: 50`;
- `timeout_ms: 250`;
- qualquer threshold;
- top-k específico;
- pesos;
- multiplicadores;
- modelo;
- provider;
- endpoint;
- GPU;
- inference engine.

### 9.3 Secrets

Secrets não devem ser persistidos em profiles compartilháveis.

Profiles podem referenciar nomes/handles de credenciais gerenciadas externamente.

---

## 10. Trigger Policy

### 10.1 Architecture Requirement

Deve existir um seam que permita:

```text
should_rerank(query, candidates, profile) -> boolean/decision
```

### 10.2 Implementation Freedom

Uma política pode considerar sinais como:

- confiança do candidate discovery;
- tipo de query;
- quantidade/ambiguidade de candidates;
- budget da requisição;
- disponibilidade do reranker.

### 10.3 Exact Identifiers

Implementações podem bypassar reranking quando houver correspondência exata inequívoca.

Isto é uma otimização permitida, não uma regra arquitetural universal.

Uma query que contém um número CNJ ou número de lei não é automaticamente “somente exata”; ela pode conter também uma pergunta conceitual.

---

## 11. Failure / Timeout / Fallback

### 11.1 Failure Conditions

Incluem genericamente:

- timeout;
- engine indisponível;
- erro de execução;
- recurso insuficiente;
- resposta inválida;
- configuração incompatível.

A arquitetura não fixa códigos HTTP, vendors ou processos específicos.

### 11.2 Fail-Open Rule

Em falha:

1. descartar a ordem parcial/incompleta produzida pelo reranker;
2. restaurar/preservar a ordem válida anterior ao reranking;
3. continuar para canonical materialization;
4. registrar telemetria operacional.

### 11.3 Not Silent

Fallback não deve ser “silencioso” do ponto de vista operacional.

Ele pode ser transparente para o usuário final quando a busca continua válida, mas deve deixar estado observável no relatório/log de retrieval.

### 11.4 No Mandatory Heuristic Fallback

A baseline não exige executar outro reranker heurístico após uma falha neural/remota.

O fallback normativo é a ordem anterior válida.

---

## 12. Relevance vs Trust Boundary

### 12.1 Relevance

Reranking responde:

> “Quão relevante é este candidate para esta query?”

### 12.2 Trust

`trust_tier` responde a uma dimensão diferente derivada de `verified`.

Reranking não responde:

> “Quão juridicamente confiável é este documento?”

### 12.3 Prohibited Automatic Blending

É proibido nesta baseline aplicar automaticamente ao relevance score:

- `human_reviewed_multiplier`;
- `stable_status_multiplier`;
- `deprecated_multiplier`;
- temporal decay baseado em idade jurídica;
- multiplicadores derivados de `trust_tier`;
- `repo_jur_verification_history`.

### 12.4 Explicit Filters/Policies

`status` e outros campos podem ser usados como **filtros explicitamente solicitados** ou em política separada já compatível com o Retrieval Contract.

Eles não são transformados silenciosamente em relevance.

### 12.5 Trust Presentation

Uma resposta pode apresentar relevance e trust como sinais separados.

Não deve fundi-los em um score único que faça parecer que relevance prova confiabilidade jurídica.

---

## 13. Can Reranking Exclude Evidence?

O reranker não remove nem deprecia concepts e não altera o corpus.

Ele pode:

- reordenar candidates;
- fornecer score efêmero;
- limitar a lista encaminhada ao próximo estágio conforme o result/candidate limit da requisição/profile.

Essa limitação é seleção operacional de retrieval, não decisão sobre validade ou existência da evidência.

Nenhum candidate é apagado do índice/bundle por ter score baixo.

Não se cria threshold canônico de “evidência inválida”.

---

## 14. Canonical Materialization

Canonical materialization permanece obrigatória após bypass, sucesso ou fallback.

Reranking score nunca substitui:

- `concept_id`;
- `text_content` canônico;
- `source_refs`;
- `page_refs`;
- hashes aplicáveis;
- `verified`;
- `status`.

Se a representação derivada usada para reranking estiver stale, o conteúdo final ainda deve ser obtido/validado contra o bundle antes da entrega.

---

## 15. Scores and Persistence

### 15.1 Runtime Score

Scores de reranking são efêmeros para a requisição.

Podem ser retornados como diagnóstico/relevance metadata no envelope de execução quando a interface permitir.

### 15.2 No Canonical Persistence

É proibido persistir score de reranking como:

- frontmatter;
- campo canônico do concept;
- propriedade de lifecycle;
- `verified`;
- trust.

### 15.3 Operational Telemetry

Logs/telemetria fora do bundle podem registrar:

- reranking applied/bypassed/failed;
- implementation/profile version;
- duração;
- candidate counts;
- fallback reason;
- métricas agregadas.

Telemetria não se torna propriedade permanente do concept.

---

## 16. Observability

Estado mínimo conceitual da execução:

```text
reranking_status:
  disabled
  bypassed
  applied
  failed_fallback
```

Quando aplicável, também pode registrar:

- profile version;
- implementation id;
- candidate count before/after;
- elapsed time;
- failure category.

Nenhum desses campos é promovido automaticamente ao bundle.

---

## 17. Evaluation and Calibration

Esta decisão não congela alegações como:

- “Cross-Encoder é sempre superior”;
- “reranking melhora X%”;
- `Precision@5` ou `Recall@5` como único objetivo;
- latência típica universal;
- custo universal por token.

Implementações devem avaliar o benefício sobre um conjunto jurídico representativo antes de ativar profiles mais caros por default.

Métricas de avaliação podem incluir:

- precision;
- recall;
- MRR;
- nDCG;
- latency;
- failure rate;
- cost.

A escolha das métricas e thresholds de aceitação é calibração operacional, não metadado canônico.

---

## 18. Invariants

1. Reranking é opcional.
2. Reranking é profile-governed.
3. Reranking pode ser condicionado por política de runtime.
4. Não existe classificador `Exact vs Conceptual` obrigatório.
5. Não existe Cross-Encoder obrigatório.
6. Não existe LLM reranker obrigatório.
7. Nenhum model/provider/API/GPU é FROZEN.
8. Candidate pool/timeout/thresholds não possuem números FROZEN.
9. Falha é fail-open.
10. Fallback normativo preserva a ordem anterior válida.
11. Fallback é observável operacionalmente.
12. Reranking score é relevance, não trust.
13. `trust_tier` não é multiplicador automático de relevance.
14. `verified` não é multiplicador automático de relevance.
15. `status` não é boost/demote automático.
16. `repo_jur_verification_history` nunca participa do ranking ativo.
17. Reranker não altera `/bundle/`.
18. Reranker não altera frontmatter.
19. Reranker não cria identidade canônica.
20. Reranker não remove evidence do corpus.
21. Scores são efêmeros.
22. Canonical materialization permanece obrigatória.
23. `concept_id` continua canonical join key.
24. Chunk references continuam derivadas.
25. Search Execution Path e Chunking Strategy permanecem intactos.

---

## 19. Required Baseline Updates

Após aprovação e congelamento:

### 19.1 Retrieval Contract

Criar `retrieval-contract-v2.7-FROZEN.md` que:

- marque Reranking Pipeline CLOSED;
- registre Optional, Conditional, Profile-Governed, Fail-Open Reranking;
- preserve relevance/trust separation;
- formalize fallback para primary order;
- formalize Reranking Profile;
- preserve canonical materialization;
- remova Reranking Pipeline da lista de Open Decisions.

### 19.2 Architecture Phase 2

Criar `arquitetura-fase2-repo-jur-v13-FROZEN.md` que:

- marque Reranking Pipeline CLOSED;
- registre o reranking seam opcional;
- registre fail-open e profile governance;
- registre relevance/trust boundary;
- declare encerradas as Open Decisions atuais de retrieval.

### 19.3 Baselines sem mudança normativa necessária

Não precisam de nova versão:

- Legal OKF Profile;
- Lifecycle & Field Ownership;
- Concept Identity & Physical Structure;
- ESIC;
- Phase 1 Operational Specification;
- Search Execution Path memo;
- Chunking Strategy memo.

---

## 20. Remaining Open Questions

Após o fechamento deste memo, **não permanece Open Decision arquitetural de retrieval dentre as atualmente registradas**.

Os itens abaixo são implementação/calibração e não novas decisões arquiteturais:

- engine/modelo de reranker;
- trigger policy concreta;
- candidate limit;
- timeout;
- thresholds;
- evaluation dataset;
- deployment local/remoto;
- tuning de latência;
- métricas e critérios de ativação.

Novas Open Decisions só devem ser criadas se surgir um requisito arquitetural concreto que não possa ser resolvido dentro dos invariantes FROZEN existentes.

---

## 21. Technical Review Corrections

A revisão técnica corrigiu os seguintes pontos da proposta inicial:

1. preservou a decisão central de reranking opcional/condicional/profile-based;
2. removeu Cross-Encoder como mecanismo semanticamente obrigatório;
3. removeu a exigência de classifier binário `Exact vs Conceptual`;
4. tornou bypass de exact match uma otimização de profile, não uma regra universal;
5. removeu a afirmação de que consultas contendo CNJ/lei sempre dispensam reranking;
6. removeu números arquiteturais de latência (`250 ms`) e candidate pool (`50`);
7. removeu modelo/provider/API/path específicos do profile;
8. removeu regex específicas de CNJ/Lei/Artigo do contrato arquitetural;
9. removeu `human_reviewed_multiplier`;
10. removeu `stable_status_multiplier`;
11. removeu `deprecated_multiplier`;
12. removeu temporal decay automático;
13. proibiu blending automático entre relevance e trust;
14. reconciliou `status` com a baseline FROZEN que não define boost/demote automático;
15. reconciliou `trust_tier` como sinal separado, não multiplicador de relevance;
16. substituiu fallback heurístico obrigatório por preservação da primary order;
17. substituiu “degradação silenciosa” por **fail-open observável**;
18. tornou failure modes genéricos em vez de vendor/HTTP específicos;
19. manteve canonical materialization após bypass, reranking ou fallback;
20. distinguiu score efêmero de telemetria operacional;
21. removeu claims quantitativos não demonstrados sobre precisão, latência e custo;
22. deixou explícito que o reranker não exclui evidence do corpus;
23. definiu que o fechamento deste memo encerra as Open Decisions de retrieval atualmente registradas.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
