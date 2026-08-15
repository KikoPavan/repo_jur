# CICLO DE VIDA DO DOCUMENTO E PROPRIEDADE DE CAMPOS: `repo_jur`
**Versão:** 1.4 (Baseline — atualização controlada)  
**Data:** 12 de agosto de 2026  
**Status:** **FROZEN**  
**Referência:** Legal OKF Profile v1.3, `decision-memo-verification-history-schema-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md`, ESIC v1.4 e decisões FROZEN de cardinalidade.

---

## 1. Finalidade e Escopo

Este documento define formalmente as regras de governança, o ciclo de vida (*lifecycle*) dos concept documents no `/bundle/` do `repo_jur` e a propriedade intelectual e técnica de cada campo (*field ownership*) [137, 201]. 

Esta especificação assegura que o **Produtor OKF** e outros agentes possam atualizar e regenerar de forma segura o corpus canônico, sem apagar de forma silenciosa ou corromper contribuições manuais de revisores jurídicos humanos, notas de rodapé de claims, classificações refinadas ou assinaturas históricas de confiança [46, 115, 204].

---

## 2. Estados do Concept Document

O lifecycle de incorporação definido pelo ESIC (`Discovered → Candidate → Selected → Accepted → Incorporated`) e o campo OKF `status` representam dimensões distintas. Os estados do ESIC descrevem o fluxo externo de ingresso; `status` descreve a maturidade/condição do concept já representado no bundle.

### 2.1 Criação (*Creation*)
*   **repo_jur Project Requirement**: Ocorre quando um novo concept é publicado pela primeira vez no bundle após cumprir o fluxo de ingestão aplicável.
*   **Regra de `status`**: `status` não é derivado automaticamente de `verified`. Um concept pode ser `stable` e permanecer `unverified`.
*   **OKF v0.2 Normative Requirement**: `status` pode assumir `draft`, `stable` ou `deprecated`; quando ausente, sua semântica é `stable`.
*   **repo_jur Project Requirement**: Como `status` é Human-Owned neste perfil, o Produtor não deve alterar ou declarar `draft`, `stable` ou `deprecated` por decisão autônoma. Quando `status` estiver ausente, aplica-se a semântica padrão do OKF (`stable`); qualquer valor explícito deve decorrer da governança humana aplicável. A existência ou ausência de `verified` não determina, por si só, esse estado.

### 2.2 Atualização (*Update*)
*   **repo_jur Project Requirement**: Ocorre quando campos producer-owned, campos human-owned ou o corpo sofrem alteração válida sem criação de um novo concept lógico.
*   **Comportamento**: Cada alteração deve respeitar field ownership, proveniência, semântica de `generated.at` e política de verificação da Seção 6.

### 2.3 Reprocessamento (*Reprocessing*)
*   **repo_jur Project Requirement**: Ocorre quando a pipeline é executada novamente sobre a mesma origem física ou lógica.
*   **Idempotência**: O reprocessamento deve produzir o mesmo resultado canônico quando **inputs canônicos, configuração relevante e versão lógica do processamento forem equivalentes**. O mesmo PDF, isoladamente, não garante saída idêntica se algoritmo, configuração ou versão de conversão tiverem mudado.
*   **Comportamento**: Campos human-owned válidos devem ser preservados; campos producer-owned podem ser recomputados; o corpo deve seguir as regras de ownership da Seção 8.

### 2.4 Substituição (*Replacement*)
*   **repo_jur Project Requirement**: Ocorre quando surge nova evidência, republicação, retificação ou versão oficial que exige avaliar se o concept existente continua representando a mesma unidade lógica.
*   **Decision Status — CLOSED: Duplicate Act Handling**: Governado por `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`. Evidências fisicamente diferentes podem ser consolidadas no mesmo concept somente quando identidade lógica e equivalência material estiverem seguras; ambiguidade ou mudança material exige revisão humana.
*   **Regra de `status`**: Replacement/version candidate não autoriza o Produtor a definir `status: deprecated`; `status` permanece Human-Owned.
*   **Regra de versionamento**: O Produtor não cria automaticamente `_v2`, UUID ou identidade persistente para encadear versões.
*   **Decision Status — CLOSED: Stable Concept Identity**: encerrada por `decision-memo-stable-concept-identity-v1.0-FROZEN.md`. O projeto mantém identidade posicional pura e não cria Stable ID adicional.

### 2.5 Depreciação (*Deprecation*)
*   **OKF v0.2 Normative Requirement**: `status: deprecated` indica que o concept não deve ser considerado atual, mas permanece disponível para links, histórico e navegação.
*   **repo_jur Project Requirement**: Concepts deprecated permanecem no bundle salvo remoção excepcional. Este documento **não** define demotes, boosts, exclusões automáticas ou política de ranking; qualquer comportamento de retrieval pertence à implementação compatível com o Retrieval Contract.

### 2.6 Remoção Física Excepcional (*Physical Deletion*)
*   **repo_jur Project Requirement**: A remoção física de um concept do bundle é excepcional e deve ocorrer somente por decisão explícita de governança, como erro de incorporação, artefato indevido ou duplicação lógica cuja remoção tenha sido deliberada.
*   **repo_jur Project Requirement**: Antes da remoção, referências internas e artefatos derivados devem ser tratados conforme os contratos congelados. O mecanismo concreto de execução não é prescrito por este documento.
---

## 3. Matriz de Propriedade dos Campos (Field Ownership)

As propriedades persistidas no concept e as propriedades derivadas são classificadas em quatro categorias:

1. **Producer-Owned**: valor canônico controlado pelo Produtor OKF e recomputável deterministicamente a partir das entradas autorizadas.
2. **Human-Owned**: valor controlado por revisão/curadoria humana e que não pode ser apagado ou sobrescrito silenciosamente pelo Produtor.
3. **Shared Ownership**: rótulo operacional usado neste documento para campos que o Legal OKF Profile já classifica conjuntamente como **producer-owned / human-owned**. Não constitui uma nova classe canônica; indica apenas que o Produtor pode preencher o valor inicial e que curadoria humana posterior deve ser preservada segundo as regras de merge.
4. **Derived**: propriedade calculada por consumidores e não persistida como metadado canônico no bundle.

### Matriz de Propriedade

| Chave YAML / Seção | Ownership | Regra principal | Retrieval-Relevant |
| :--- | :--- | :--- | :--- |
| `type` | **Producer-Owned** | Classificação jurídica canônica definida pelo perfil. | Sim |
| `title` | **Shared Ownership** | Pode ser produzido deterministicamente e posteriormente customizado por humano. | Sim |
| `description` | **Shared Ownership** | Pode ser produzido pelo sistema e refinado por humano; não pode ser sobrescrito silenciosamente após curadoria. | Sim |
| `resource` | **Producer-Owned** | Identificador do ativo subjacente quando aplicável. | Não |
| `tags` | **Shared Ownership** | Pode ser sugerido/produzido e depois curado; merge deve preservar curadoria válida. | Sim |
| `sources` | **Producer-Owned** | Proveniência identificável do concept. | Não como filtro obrigatório |
| `generated` | **Producer-Owned** | Proveniência de geração da versão atual. | Não |
| `verified` | **Human-Owned / independent-process-owned** | Somente eventos reais de verificação. | Não como filtro canônico |
| `repo_jur_verification_history` | **Producer-Owned archival structure** | Preserva eventos reais anteriormente ativos e sua invalidação; `by`/`at` originais são imutáveis. | Auditoria apenas; nunca trust tier |
| `status` | **Human-Owned** | Estado de maturidade/lifecycle OKF. | Sim |
| `stale_after` | **Shared Ownership** | Pode decorrer de regra de vigência ou decisão humana. | Não por padrão |
| `repo_jur_pdf_hash` | **Producer-Owned** | SHA-256 quando o concept deriva de exatamente 1 PDF. | Não como filtro |
| `repo_jur_pdf_hashes` | **Producer-Owned** | Mapping `sources[].id` → SHA-256 quando o concept deriva de 2+ PDFs. | Não como filtro |
| `repo_jur_lei_numero` | **Producer-Owned** | Número oficial da norma. | Sim |
| `repo_jur_lei_ano` | **Producer-Owned** | Ano oficial da norma. | Sim |
| `repo_jur_lei_esfera` | **Producer-Owned** | `federal`, `estadual`, `distrital` ou `municipal`. | Sim |
| `repo_jur_lei_tipo` | **Shared Ownership** | Espécie normativa identificada/curada. | Sim |
| `repo_jur_processo_numero` | **Producer-Owned** | Número processual quando aplicável. | Sim |
| `repo_jur_tribunal` | **Producer-Owned** | Tribunal emissor/responsável quando aplicável. | Sim |
| `repo_jur_relator` | **Producer-Owned** | Relator quando aplicável. | Sim |
| `repo_jur_data_julgamento` | **Producer-Owned** | Data oficial do julgamento. | Sim |
| `repo_jur_ramo_direito` | **Shared Ownership** | Classificação jurídica passível de curadoria. | Sim |
| `repo_jur_precedente_numero` | **Producer-Owned** | Número oficial do precedente numerado. | Sim |
| `repo_jur_precedente_status` | **Shared Ownership** | Situação jurídica do precedente, sustentada por fonte oficial/curadoria. | Sim |
| `repo_jur_tema_numero` | **Producer-Owned** | Número oficial do tema, quando houver. | Sim |
| corpo — concept derivado de PDF | **Producer-Owned** | Conteúdo canônico vindo da pipeline física. | Sim |
| corpo — concept abstrato/sintético | **Human-Owned ou Shared Ownership** | Conteúdo produzido/curado conforme o perfil. | Sim |
| `trust_tier` | **Derived** | Calculado a partir de `verified`; não persistido no bundle. | Sim |

*   **repo_jur Project Requirement**: Campos Human-Owned não podem ser alterados, apagados ou substituídos silenciosamente.
*   **repo_jur Project Requirement**: Em campos Shared Ownership, o Produtor pode preencher ausência inicial, mas uma curadoria humana existente deve ser preservada salvo regra explícita de invalidação ou nova curadoria.
*   **repo_jur Project Requirement**: Derived não deve ser persistido como campo canônico apenas para atender retrieval.
*   **repo_jur Project Requirement — PDF Hash Ownership**: `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` são Producer-Owned e mutuamente exclusivos. O Produtor deve escolher o campo exclusivamente pela cardinalidade de evidências PDF: 1 PDF → singular; 2+ PDFs → plural.
---

## 4. Fluxo de Regeneração Determinística

Para regenerar um concept preservando integridade e ownership, o Produtor OKF deve seguir a sequência:

```text
1. Carregar concept existente, se houver
2. Ler frontmatter e corpo
3. Resolver identidade/proveniência da entrada
4. Detectar mudanças materiais e técnicas
5. Recomputar campos Producer-Owned
6. Fazer merge de campos Shared/Human-Owned
7. Aplicar política de verified
8. Substituir ou preservar o corpo conforme ownership
9. Validar OKF + regras repo_jur
10. Escrever atomicamente
11. Expor diff para revisão Git
```

1. **Carregar concept existente**: localizar o concept candidato segundo as regras congeladas de identidade/caminho.
2. **Ler frontmatter e corpo**: carregar o estado canônico anterior antes de qualquer sobrescrita.
3. **Resolver identidade/proveniência**: verificar as fontes disponíveis, contar as evidências PDF aplicáveis e selecionar deterministicamente `repo_jur_pdf_hash` para exatamente 1 PDF ou `repo_jur_pdf_hashes` para 2+ PDFs, sem tratar hash como identidade lógica do concept.
   * Se nova evidência física sustentar com segurança o mesmo ato e for materialmente equivalente, atualizar `sources` e cardinalidade conforme aplicável.
   * Se houver mudança material ou ambiguidade entre duplicata, versão e ato autônomo, interromper a fusão automática antes da escrita e exigir revisão humana.
4. **Detectar mudanças**: distinguir mudança apenas técnica, mudança material de conteúdo/significado e mudança estrutural de caminho.
5. **Recomputar Producer-Owned**: recalcular apenas os campos sob domínio do Produtor.
6. **Merge de ownership**: preservar campos Human-Owned e valores humanos já consolidados em campos Shared Ownership.
7. **Política de `verified` + histórico**: preservar, invalidar e arquivar somente de acordo com a Seção 6.
8. **Body ownership**: substituir o corpo apenas quando ele for producer-owned e houver nova saída canônica válida; concepts curados não podem perder conteúdo humano silenciosamente.
9. **Validação**: validar YAML, OKF, Legal OKF Profile v1.1, estrutura física, exclusividade singular/plural e correspondência `repo_jur_pdf_hashes` ↔ `sources[].id` quando aplicável.
10. **Escrita atômica**: publicar o arquivo completo de forma atômica, evitando estados parciais.
11. **Revisão Git**: expor o diff para revisão; o documento não prescreve CLI ou comando Git específico.

### Idempotência
*   **repo_jur Project Requirement**: Para inputs canônicos equivalentes, configuração relevante equivalente e mesma versão lógica de processamento, a regeneração deve produzir conteúdo canônico equivalente e não gerar alterações espúrias.
*   **repo_jur Project Requirement**: Timestamps técnicos de execução não devem, por si só, criar diffs sem mudança significativa do conteúdo.
---

## 5. Governança da Família `generated`

*   **OKF v0.2 Normative Requirement**: `generated` registra a proveniência de geração do **conteúdo atual** do concept. Se a família for declarada, `generated.by` é obrigatório.
*   **repo_jur Project Requirement**: `generated.by` deve utilizar a assinatura `repo_jur_producer/<version>` para concepts produzidos pelo pipeline canônico.
*   **OKF v0.2 Normative Requirement**: `generated.at`, quando presente, representa a data/hora da **última mudança significativa do conteúdo atual**. Não é timestamp de simples execução, gravação física, touch do arquivo ou rebuild sem mudança significativa.
*   **repo_jur Project Requirement**: Reprocessamento que não altere significativamente o conteúdo atual não deve atualizar `generated.at` apenas porque o Produtor foi executado novamente.
*   **repo_jur Project Requirement**: `generated` não equivale a `verified`; geração pelo Produtor não constitui revisão jurídica nem verificação independente.
---

## 6. Governança da Família `verified`

*   **OKF v0.2 Normative Requirement**: `verified`, quando presente, registra eventos reais de verificação por Actor e instante correspondente. A ausência do campo significa que o concept permanece sem verificação registrada.
*   **repo_jur Project Requirement**: O Produtor não pode inserir `verified` automaticamente nem assinar como verificador sem um processo independente e real de verificação.

### 6.1 Preservação
*   **repo_jur Project Requirement**: Uma alteração estritamente técnica que não modifique o conteúdo jurídico, o significado, a proveniência material relevante ou o escopo do que foi verificado pode preservar os eventos ativos de `verified`.
*   **repo_jur Project Requirement**: Mudança de caminho/slug, normalização puramente estrutural ou correção operacional que não altere o objeto verificado não invalida automaticamente `verified`.

### 6.2 Mudança de hash e cardinalidade
*   **repo_jur Project Requirement**: Alteração de `repo_jur_pdf_hash` ou de qualquer valor em `repo_jur_pdf_hashes` **não implica automaticamente** alteração material do concept; exige análise da razão da mudança.
*   **repo_jur Project Requirement**: Mudança entre campo singular e plural indica mudança na cardinalidade de evidências PDF e deve ser tratada como alteração de proveniência relevante, com validação explícita de `sources`.
*   **repo_jur Project Requirement**: Se os bytes mudaram, mas foi confirmado que o conteúdo jurídico relevante e o objeto efetivamente verificado permanecem equivalentes, a verificação pode continuar válida.
*   **repo_jur Project Requirement**: Se a mudança de bytes, de conjunto de fontes ou de cardinalidade alterar o conteúdo jurídico, as páginas relevantes, a proveniência material do objeto verificado ou seu significado, a verificação anterior não pode permanecer ativa sem nova revisão.

### 6.3 Mudança material
*   **repo_jur Project Requirement**: Mudança significativa do conteúdo jurídico, significado, tese, corpo literal verificado, proveniência material relevante ou escopo coberto pela revisão torna a verificação anterior **não reutilizável**.
*   **repo_jur Project Requirement**: Nessa situação, o evento anterior não permanece no campo ativo `verified` sem nova verificação real.
*   **Decision Status — CLOSED: Verification History Schema**: governada por `decision-memo-verification-history-schema-v1.0-FROZEN.md`. Eventos realmente existentes que deixam de ser aplicáveis são arquivados em `repo_jur_verification_history`.

### 6.4 Arquivamento em `repo_jur_verification_history`
*   **Condição:** arquivar somente quando o evento existia em `verified` e foi determinado que deixou de ser aplicável ao conteúdo atual.
*   **Estrutura:** copiar `by` e `at` sem alteração e registrar `invalidated_at`, `invalidated_by` e `reason`.
*   **Actor:** `invalidated_by` identifica quem decidiu ou autorizou a invalidação; não é automaticamente o software que apenas escreveu o arquivo.
*   **Idempotência:** o par `(by, at)` pode ser arquivado no máximo uma vez no mesmo concept.
*   **Ausência de ativo:** se nenhum evento permanecer ativo, a chave `verified` deve ser omitida.
*   **Trust:** histórico nunca conta como verificação ativa e nunca eleva `trust_tier`.
*   **Hash:** não existe `evidence_pdf_hash` histórico obrigatório nesta baseline.
*   **Ambiguidade:** se não for possível determinar com segurança se a mudança atingiu o objeto verificado, não invalidar silenciosamente; exigir revisão humana.

### 6.5 Re-verificação
*   **Nova verificação real:** cria novo evento em `verified`.
*   **Histórico anterior:** permanece imutável e não é reativado automaticamente.
---

## 7. Políticas Frente a Alterações na Fonte Física (PDF)

Os campos `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` registram integridade física das evidências PDF conforme a cardinalidade aprovada. Nenhum deles constitui identidade lógica do concept nem prova autenticidade jurídica.

### 7.1 Exatamente 1 PDF
*   **repo_jur Project Requirement**: O concept deve usar `repo_jur_pdf_hash`.
*   **Comportamento**: O valor é o SHA-256 dos bytes exatos da única evidência PDF de origem.
*   **Compartilhamento**: O mesmo hash pode aparecer em vários concepts quando o mesmo PDF originar ou sustentar múltiplas unidades lógicas.

### 7.2 Dois ou mais PDFs
*   **repo_jur Project Requirement**: O concept deve omitir `repo_jur_pdf_hash` e usar `repo_jur_pdf_hashes`.
*   **Source Mapping**: Cada evidência PDF deve possuir `sources[].id`, e cada `id` de PDF deve corresponder exatamente a uma entrada em `repo_jur_pdf_hashes`.
*   **Fontes não-PDF**: Podem permanecer em `sources`, mas não aparecem no mapping de hashes.
*   **Exclusividade**: `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` nunca coexistem no mesmo concept.

### 7.3 Mudança de cardinalidade
*   **1 PDF → 2+ PDFs**: remover o campo singular somente após construir e validar `sources[].id` + `repo_jur_pdf_hashes`.
*   **2+ PDFs → 1 PDF**: remover o mapping plural somente após confirmar qual evidência única permanece canônica e gravar seu `repo_jur_pdf_hash`.
*   **2+ PDFs → conjunto multi-PDF diferente**: recomputar o mapping plural e avaliar materialidade da alteração de proveniência.
*   **Regra de `verified`**: mudança de cardinalidade ou hash não invalida automaticamente `verified`; aplica-se a análise material da Seção 6.

### 7.4 Mesmos bytes e reprocessamento
*   **repo_jur Project Requirement**: Hash idêntico indica a mesma evidência física em bytes.
*   **Idempotência**: O mesmo hash, isoladamente, não garante saída idêntica. Inputs canônicos, configuração relevante e versão lógica do processamento também devem ser equivalentes.
*   **Preflight**: Evidência já conhecida não autoriza rejeição automática do concept, pois um mesmo PDF pode participar legitimamente de múltiplos concepts.

### 7.5 Decisões em aberto relacionadas
*   **Decision Status — CLOSED: PDF Source Cardinality**: encerrada por `decision-memo-pdf-source-cardinality-v1.0` (FROZEN) e incorporada ao Legal OKF Profile v1.1 e Concept Identity & Physical Structure v1.1.
*   **Decision Status — CLOSED: Duplicate Act Handling**: encerrada por `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`; consolidação automática é conservadora e ambiguidade exige revisão humana.
*   **Decision Status — CLOSED: Stable Concept Identity**: encerrada por `decision-memo-stable-concept-identity-v1.0-FROZEN.md`; rename/move altera `concept_id` e não existe identidade persistente adicional.
*   **Decision Status — CLOSED: Verification History Schema**: encerrada por `decision-memo-verification-history-schema-v1.0-FROZEN.md`; histórico persistente usa `repo_jur_verification_history`.

---

## 8. Governança e Propriedade do Corpo (Body Ownership)

A propriedade do corpo é determinada pela **origem e pelo modo de produção do concept**, não apenas por seu `type`.

### 8.1 Concept derivado de PDF
*   **repo_jur Project Requirement**: Qualquer `Legislacao`, `Jurisprudencia`, `TemaJuridico` ou `PrecedenteVinculante` pode ser derivado de PDF.
*   **Body Ownership**: Quando o concept representa conteúdo literal extraído do PDF, o corpo é **Producer-Owned** e deve ser regenerado a partir da saída canônica da Fase 1.
*   **Preservação física**: Marcadores `[[Pág. N]]` devem permanecer quando aplicáveis.
*   **Restrição**: Edições humanas silenciosas dentro de um corpo producer-owned não devem ser usadas como mecanismo de curadoria, pois seriam substituíveis numa regeneração. Curadoria deve ocorrer nos espaços previstos pelo perfil ou em concepts apropriados.

### 8.2 Concept abstrato ou sintético
*   **repo_jur Project Requirement**: Quando o concept não é uma transcrição literal de uma fonte física, seu corpo pode ser Human-Owned ou Shared Ownership conforme seu processo de criação.
*   **Comportamento**: O Produtor não pode apagar, substituir ou regenerar silenciosamente conteúdo humano já curado.
*   **Regra física**: Não criar marcadores de página, `repo_jur_pdf_hash`, `repo_jur_pdf_hashes` ou outros atributos físicos de PDF quando não houver PDF de origem.

### 8.3 Mudança de modo de ownership
*   **Open Decision**: Se um concept inicialmente sintético passar a incorporar corpo literal producer-owned, ou o inverso, a migração deve ser deliberada e revisada; este documento não define transformação automática.
---

## 9. Invariantes do Ciclo de Vida e Propriedade

1. **Proteção humana**: nenhuma rotina automática pode alterar ou apagar silenciosamente campos/trechos Human-Owned.
2. **Shared Ownership**: curadoria humana existente prevalece sobre recomputação automática, salvo regra explícita de invalidação.
3. **Verificação**: `verified` não pode ser preservado automaticamente após mudança material do objeto efetivamente verificado.
4. **Hash/cardinalidade ≠ materialidade automática**: mudança de SHA-256, conjunto de hashes ou cardinalidade exige análise; não invalida `verified` por si só.
5. **Histórico ≠ confiança ativa**: `repo_jur_verification_history` nunca participa de `trust_tier`.
6. **Histórico real e idempotente**: nenhum evento é inventado; `(by, at)` é arquivado no máximo uma vez por concept.
5. **Zero-Write de retrieval**: mecanismos de retrieval não modificam `/bundle/`.
6. **Git**: o histórico de alterações canônicas é preservado pelo versionamento do projeto.
7. **Atomicidade**: writes do Produtor devem ocorrer de forma atômica.
8. **Idempotência controlada**: mesmas entradas canônicas, mesma configuração relevante e mesma versão lógica de processamento não devem gerar diffs espúrios.
9. **Neutralidade de retrieval**: este contrato não define ranking, demote, boost, RAG, embeddings, MCP ou banco.
10. **Cardinalidade fechada**: nenhuma implementação pode divergir silenciosamente da regra 1 PDF → `repo_jur_pdf_hash` e 2+ PDFs → `repo_jur_pdf_hashes`.
11. **Open Decisions preservadas**: nenhuma implementação pode resolver silenciosamente `Verification History Schema`.
12. **Stable Concept Identity fechado**: identidade posicional pura; rename/move altera `concept_id`; nenhum Stable ID adicional é persistido.
12. **Duplicate Act Handling fechado**: equivalência física não substitui equivalência jurídica; fusão automática só ocorre quando lógica/materialmente segura, e `status` não é alterado automaticamente.
---

## 10. Classificação das Diretrizes do Documento

### OKF v0.2 Normative Requirement
*   Semântica de `status` (`draft`, `stable`, `deprecated`), incluindo ausência equivalente a `stable`.
*   Semântica e requisitos internos de `generated` e `verified`.
*   `generated.at` representa a última mudança significativa do conteúdo atual.
*   `generated` e `verified` são dimensões distintas.

### repo_jur Project Requirement
*   Field ownership e merge seguro durante regeneração.
*   Proteção de campos Human-Owned e valores humanos em campos Shared Ownership.
*   Regeneração determinística e escrita atômica.
*   Zero-Write de retrieval sobre `/bundle/`.
*   Hash SHA-256 como proveniência física quando aplicável, sem tratá-lo como identidade lógica ou prova de autenticidade.
*   Exatamente 1 PDF → `repo_jur_pdf_hash`; 2+ PDFs → `repo_jur_pdf_hashes`; os campos são mutuamente exclusivos e o mapping plural deve corresponder a `sources[].id`.
*   Runtimes, scripts operacionais, caches e índices derivados permanecem fora do corpus canônico conforme a arquitetura do `repo_jur`. Esta é uma regra do projeto, não uma exigência normativa geral do OKF.
*   Invalidação de `verified` somente quando a mudança material atingir o objeto efetivamente verificado.

### Recommendation
*   Manter regras de ownership pequenas e explícitas para reduzir merges ambíguos.
*   Expor toda regeneração como diff revisável antes da incorporação definitiva.
*   Derivar sinais de confiança/retrieval fora do frontmatter canônico quando não forem parte do perfil.

### Alteração controlada v1.4
*   **Decisões já incorporadas:** PDF Source Cardinality, Duplicate Act Handling e Stable Concept Identity permanecem CLOSED.
*   **Decisão incorporada nesta versão:** Verification History Schema = CLOSED por `decision-memo-verification-history-schema-v1.0-FROZEN.md`.
*   **Novo campo:** `repo_jur_verification_history` como estrutura arquivística Producer-Owned.
*   **Lifecycle:** somente eventos reais anteriormente ativos podem ser arquivados; `verified` é omitido quando não restar evento ativo.
*   **Materialidade:** hash/cardinalidade/path isolados continuam insuficientes para invalidação.

---

## 11. Exemplos YAML Abstratos e Não Normativos de Regeneração

Os exemplos são apenas ilustrativos. Usam placeholders explícitos e não representam auditorias, fontes ou verificações reais.

### Exemplo 1: Concept derivado de PDF, sem verificação registrada

```yaml
type: Jurisprudencia
title: "<decision-title>"
description: "<one-sentence-description>"
sources:
  - id: "source_pdf"
    resource: "<archived-source-resource>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
repo_jur_pdf_hash: "<sha256-64-hex>"
repo_jur_tribunal: "<tribunal>"
```

> `verified` é omitido porque nenhum evento real de verificação foi representado.

### Exemplo 2: Após evento real de verificação humana

```yaml
type: Jurisprudencia
title: "<decision-title>"
description: "<one-sentence-description>"
sources:
  - id: "source_pdf"
    resource: "<archived-source-resource>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
verified:
  - by: "human:<reviewer-id>"
    at: "<iso-8601-real-verification-time>"
repo_jur_pdf_hash: "<sha256-64-hex>"
repo_jur_tribunal: "<tribunal>"
```

### Exemplo 3: Concept derivado de múltiplos PDFs

```yaml
type: TemaJuridico
title: "<concept-title>"
description: "<one-sentence-description>"
sources:
  - id: "source_pdf_a"
    resource: "<source-a-resource>"
  - id: "source_pdf_b"
    resource: "<source-b-resource>"
  - id: "source_non_pdf"
    resource: "<non-pdf-resource>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
repo_jur_pdf_hashes:
  source_pdf_a: "<sha256-64-hex>"
  source_pdf_b: "<sha256-64-hex>"
```

> O campo singular `repo_jur_pdf_hash` é omitido. A fonte não-PDF permanece em `sources`, mas não aparece em `repo_jur_pdf_hashes`.

### Exemplo 4: Reprocessamento técnico sem mudança significativa

Se a execução do Produtor não modificar significativamente o conteúdo atual, `generated.at` **não deve ser atualizado apenas para refletir a nova execução**. Os campos human-owned e um `verified` ainda válido permanecem preservados.

### Exemplo 5: Mudança material

Quando a alteração modifica o objeto efetivamente verificado, o evento anterior deixa o campo ativo `verified` e, se realmente existiu, é arquivado em `repo_jur_verification_history` conforme `decision-memo-verification-history-schema-v1.0-FROZEN.md`. Uma nova revisão real será necessária para criar novo evento ativo.
---

**Status de Maturidade do Contrato:** **FROZEN**

