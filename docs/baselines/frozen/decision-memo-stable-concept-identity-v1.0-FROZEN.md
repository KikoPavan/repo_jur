# DECISION MEMO: STABLE CONCEPT IDENTITY (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v6-FROZEN.md`, `external-source-ingestion-contract-v1.2-FROZEN.md`, `legal-okf-profile-v1.1-FROZEN.md`, `concept-identity-physical-structure-v1.2-FROZEN.md`, `lifecycle-field-ownership-v1.2-FROZEN.md`, `retrieval-contract-v2.2-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md` e OKF v0.2.

---

## 1. Problem Statement

A **Open Decision — Stable Concept Identity** deve decidir se o `repo_jur` necessita de uma identidade persistente adicional ao `concept_id` posicional do OKF.

O problema existe porque:

- `concept_id` deriva do caminho relativo do arquivo;
- rename/move altera o `concept_id`;
- links Markdown que apontam para o caminho antigo precisam ser tratados;
- índices e estruturas derivadas associados ao caminho antigo precisam ser sincronizados;
- Git preserva histórico do repositório, mas não transforma o caminho em uma identidade persistente de domínio.

A decisão deve distinguir claramente:

1. **referência canônica do concept no bundle**;
2. **identidade jurídica do ato representado**;
3. **histórico de mudanças no Git**.

Essas três dimensões não são equivalentes.

---

## 2. Frozen Constraints

1. **`concept_id` é posicional.** É o caminho relativo do Markdown sem `.md`; rename/move altera o valor. **[Existing FROZEN Requirement]**
2. **`concept_id` não é duplicado no YAML.** **[Existing FROZEN Requirement]**
3. **SHA-256 identifica bytes, não concept ou ato jurídico.** **[Existing FROZEN Requirement]**
4. **Duplicate Act Handling está CLOSED.** Metadados são sinais de identidade, não primary key universal; equivalência jurídica/material deve ser segura antes de consolidação. **[Existing FROZEN Requirement]**
5. **`status` é Human-Owned.** O Produtor não depreca concepts autonomamente. **[Existing FROZEN Requirement]**
6. **Não existe versionamento automático por `_v2`.** Mudança material/ambígua exige revisão humana. **[Existing FROZEN Requirement]**
7. **Retrieval é Zero-Write.** Estruturas derivadas ficam fora do bundle e devem ser reconstruíveis/sincronizáveis. **[Existing FROZEN Requirement]**
8. **Links internos são Markdown links normais.** **[Existing FROZEN Requirement]**
9. **Nenhum campo YAML de Stable Concept Identity existe atualmente.** **[Existing FROZEN Requirement]**

---

## 3. Required Properties

Qualquer solução deve:

1. manter conformidade com OKF v0.2;
2. não alterar a semântica normativa do `concept_id`;
3. preservar legibilidade e portabilidade do bundle;
4. não depender de Stable ID para que o bundle seja legível;
5. permitir rename/move controlado;
6. manter índices derivados sincronizáveis/reconstruíveis;
7. não confundir identidade do concept com identidade do ato jurídico;
8. não resolver Duplicate Act Handling novamente;
9. evitar criação acidental de IDs duplicados;
10. justificar qualquer novo campo por necessidade real de interoperabilidade ou persistência externa.

---

## 4. Candidate Models

### 4.1 Modelo A — Identidade Posicional Pura

O `concept_id` continua sendo a única **referência canônica de identidade do concept dentro do bundle**.

Não é criado Stable ID adicional no frontmatter.

Rename/move:

- altera o `concept_id`;
- exige revisão/atualização dos links internos dependentes do caminho;
- exige sincronização dos artefatos derivados;
- mantém o histórico de alteração no Git.

**[New Decision Proposal]**

### 4.2 Modelo B — Stable ID Persistente

Adicionar um campo de projeto, por exemplo `repo_jur_stable_id`, com identificador persistente gerado uma vez e preservado em rename/move.

O OKF permite chaves adicionais de frontmatter; portanto, esse modelo **não seria incompatível com OKF por si só**.

Entretanto, sua adoção criaria obrigações adicionais:

- definir semântica exata do ID;
- definir ownership;
- geração e validação de unicidade;
- impedir cópia acidental do mesmo ID;
- migração dos concepts existentes;
- decidir se links/retrieval realmente utilizariam esse ID;
- manter mapping entre Stable ID e `concept_id`.

**[New Decision Proposal]**

### 4.3 Modelo C — Identidade Derivada de Metadados Jurídicos

Gerar um ID determinístico a partir de campos jurídicos.

**Rejeitado como Stable Concept Identity.**

Duplicate Act Handling já estabeleceu que os metadados disponíveis são sinais de identidade, não uma primary key universal. Atos diferentes podem compartilhar sinais e alguns concepts podem não possuir todos os campos necessários.

Hash de atributos também não resolve essa insuficiência semântica.

**[Existing FROZEN Requirement + New Decision Proposal]**

---

## 5. Comparative Analysis

| Critério | Modelo A — Posicional | Modelo B — Stable ID | Modelo C — Derivado |
|---|---|---|---|
| Compatibilidade OKF | Total | Total como extensão de projeto | Total como extensão, mas semanticamente frágil |
| Novo campo YAML | Não | Sim | Sim |
| Rename/move mantém ID adicional | Não | Sim | Em tese |
| Links Markdown deixam de depender de path | Não | Não automaticamente | Não automaticamente |
| Necessita mapping adicional | Não | Sim, se usado por consumidores | Sim |
| Risco de colisão semântica | Gerido pelo path + Duplicate Act Handling | Baixo se UUID bem gerido, mas cópias devem ser validadas | Alto/indeterminado |
| Migração necessária | Não | Sim | Sim |
| Complexidade operacional | Baixa, mas rename/move exige coordenação | Maior | Maior |
| Identifica o ato jurídico | Não | Não necessariamente | Não de forma universal |
| Necessidade atual demonstrada | Sim, já atende o modelo vigente | Não demonstrada | Não demonstrada |

### Observação

O Modelo A **não elimina duplicatas jurídicas por si só**. Essa responsabilidade pertence ao `Duplicate Act Handling`.

Da mesma forma, o Modelo B não elimina links quebrados automaticamente: links Markdown continuam apontando para paths, a menos que seja introduzido outro mecanismo de resolução — que não existe hoje.

---

## 6. Recommended Decision

Adotar o **Modelo A — Identidade Posicional Pura**, mantendo o `concept_id` como única referência canônica do concept no bundle e **não introduzir Stable ID adicional no frontmatter nesta baseline**.

### Fundamentação

A necessidade atual de um Stable ID adicional não foi demonstrada.

Os requisitos existentes são atendidos por:

- `concept_id` posicional para referência canônica;
- Duplicate Act Handling para equivalência jurídica;
- atualização controlada de links em rename/move;
- sincronização/reconstrução de dados derivados;
- Git para histórico de alterações do repositório.

### Limite da decisão

Esta decisão **não afirma** que Stable IDs são incompatíveis com OKF ou tecnicamente inválidos.

Ela afirma apenas que, **para os requisitos atuais do `repo_jur`, o custo e a complexidade de introduzir uma segunda identidade não são justificados**.

Se surgir no futuro uma necessidade concreta de:

- referências externas permanentes independentes de path;
- interoperabilidade entre bundles;
- integração com sistemas que dependam de identidade imutável;
- preservação de identidade de nó através de reorganizações físicas sem atualização de referências externas;

a decisão poderá ser reaberta por novo Decision Memo.

**[New Decision Proposal]**

---

## 7. Lifecycle Rules

### 7.1 Creation

Novo concept recebe:

- filename/slug conforme regras determinísticas;
- `concept_id` derivado automaticamente do path;
- nenhum Stable ID adicional.

**[New Decision Proposal]**

### 7.2 Regeneration

Reprocessamento do mesmo concept no mesmo path mantém o mesmo `concept_id`.

Idempotência continua dependendo de inputs canônicos, configuração relevante e versão lógica, conforme Lifecycle.

**[Existing FROZEN Requirement]**

### 7.3 Rename / Move

Rename/move:

- altera o `concept_id`;
- não representa automaticamente criação de novo ato jurídico;
- não altera `status` automaticamente;
- não invalida `verified` automaticamente;
- exige tratamento das referências e artefatos derivados dependentes do path.

**[Existing FROZEN Requirement + New Decision Proposal]**

### 7.4 Material Change / Replacement Candidate

Mudança material não gera automaticamente:

- `_v2`;
- novo Stable ID;
- `status: deprecated`;
- novo concept.

A operação continua sujeita ao Duplicate Act Handling e à revisão humana quando aplicável.

**[Existing FROZEN Requirement]**

---

## 8. Rename / Move Behavior

Antes da publicação de rename/move:

1. determinar o novo path;
2. reconhecer que o novo path produzirá novo `concept_id`;
3. localizar referências internas ao arquivo antigo;
4. atualizar/revisar essas referências conforme a política autorizada do `repo_jur`;
5. publicar a alteração de forma controlada;
6. atualizar, reconstruir ou invalidar artefatos derivados associados ao `concept_id` anterior.

### Autoridade de escrita

O `juridico-cli`, agentes externos e retrieval permanecem Zero-Write sobre `/bundle/`.

Este memo **não prescreve** qual CLI, script ou comando executará a refatoração de links. A escrita deve ocorrer apenas através de tooling autorizado do `repo_jur` conforme a arquitetura vigente.

### Git

Git preserva o histórico de commits do projeto e pode auxiliar no acompanhamento de renames/moves. Isso é mecanismo de auditoria/versionamento, **não Stable Concept Identity**.

**[New Decision Proposal]**

---

## 9. Duplicate Act Interaction

A decisão de identidade posicional não substitui Duplicate Act Handling.

### Mesma evidência / atos distintos

Um PDF pode sustentar vários concepts e vários `concept_id`.

### PDFs diferentes / mesmo ato

Quando equivalência lógica/material estiver estabelecida, múltiplas evidências podem ser consolidadas no mesmo concept e sua proveniência/cardinalidade atualizada.

### Mudança material / ambiguidade

Não fundir automaticamente e não criar automaticamente novo path/version suffix.

Aplicar HUMAN REVIEW conforme Duplicate Act Handling.

**[Existing FROZEN Requirement]**

---

## 10. Retrieval / Links Impact

### 10.1 Retrieval

`concept_id` continua sendo a canonical reference/join key para estruturas derivadas.

Em rename/move:

- registros derivados associados ao path antigo devem ser sincronizados, atualizados, reconstruídos ou invalidados conforme a implementação;
- esta decisão não exige índice persistente;
- esta decisão não escolhe mecanismo lexical, vetorial, híbrido, MCP ou outro.

### 10.2 Links

Links entre concepts continuam sendo Markdown links convencionais para arquivos.

Um Stable ID adicional, mesmo se existisse, não corrigiria automaticamente links de path sem a introdução de um resolver adicional.

### 10.3 Broken links

OKF tolera links cujo destino não exista, mas o `repo_jur` mantém como requisito de qualidade que renames/moves deliberados tratem as referências internas conhecidas antes da publicação.

**[Existing FROZEN Requirement + New Decision Proposal]**

---

## 11. Migration

A adoção do Modelo A não exige migração de schema.

Não há:

- campo para adicionar;
- UUID para gerar;
- hash lógico para calcular;
- mapping Stable ID ↔ path para construir.

Após aprovação:

- apenas as baselines que ainda registram Stable Concept Identity como Open Decision devem ser sincronizadas;
- índices derivados continuam seguindo seus processos normais de sincronização/reconstrução.

**[New Decision Proposal]**

---

## 12. Invariants

1. `concept_id` é posicional.
2. `concept_id` não é duplicado no YAML.
3. O `repo_jur` não adiciona Stable Concept ID nesta baseline.
4. SHA-256 não é Stable Concept ID.
5. Metadados jurídicos não formam Stable Concept ID universal.
6. Duplicate Act Handling continua sendo a autoridade para equivalência jurídica.
7. Rename/move altera o `concept_id`.
8. Rename/move não implica novo ato jurídico.
9. Rename/move não altera `status` automaticamente.
10. Mudança material não produz `_v2` automaticamente.
11. Links internos continuam baseados em paths Markdown.
12. Retrieval continua usando `concept_id` como canonical reference/join key.
13. Artefatos derivados permanecem sincronizáveis/reconstruíveis.
14. Git registra histórico do repositório, mas não constitui identidade persistente de domínio.
15. O projeto pode reabrir Stable Concept Identity futuramente se surgir requisito concreto não atendido pelo modelo posicional.

---

## 13. Required Baseline Updates

Após aprovação e congelamento deste memo:

### 13.1 Concept Identity & Physical Structure

Atualizar para nova versão controlada:

- Stable Concept Identity → CLOSED;
- adotar Identidade Posicional Pura;
- remover alternativas abertas de UUID;
- registrar possibilidade de futura reabertura somente por nova decisão controlada.

### 13.2 Lifecycle & Field Ownership

Atualizar referências que ainda classificam Stable Concept Identity como aberta.

Não criar novo campo ou ownership.

### 13.3 ESIC

Remover Stable Concept Identity das Open Questions.

Nenhuma mudança de ingestão ou schema adicional é necessária.

### 13.4 Retrieval Contract

Remover Stable Concept Identity das Open Decisions.

Manter:

- `concept_id` como canonical reference/join key;
- sincronização/reconstrução de dados derivados após rename/move;
- neutralidade tecnológica.

### 13.5 Legal OKF Profile

Atualizar o registro de Open Decisions para indicar:

- Stable Concept Identity = CLOSED;
- nenhum campo adicional de Stable ID adotado.

Nenhuma mudança de schema é necessária.

### 13.6 Arquitetura Fase 2

Remover Stable Concept Identity de:

- Outras Open Decisions;
- Próximas Decisões Requeridas.

Registrar a decisão CLOSED.

---

## 14. Remaining Open Questions

Permanecem abertas:

- **Verification History Schema**
- **Ingress Transport Protocol**
- **Phase 1 Quality Gate**

No Retrieval Contract permanecem independentes:

- **Search Execution Path**
- **Chunking Strategy**
- **Reranking Pipeline**

---

## 15. Technical Review Corrections

A revisão técnica corrigiu os seguintes pontos da proposta inicial:

1. removeu a afirmação de que UUID/custom ID viola OKF — campos adicionais são permitidos pelo formato;
2. substituiu “única identidade lógica” por **referência canônica do concept no bundle**, evitando confusão com identidade do ato jurídico;
3. removeu a afirmação de que os metadados do Legal OKF Profile identificam “perfeitamente” o ato jurídico;
4. corrigiu “risco de duplicação inexistente” do modelo posicional — Duplicate Act Handling continua necessário;
5. corrigiu “risco de colisão inexistente” de UUID — colisão matemática pode ser desprezível, mas duplicação por cópia/configuração exige validação;
6. removeu o argumento de que Stable ID necessariamente exige runtime/resolver; isso só seria necessário caso consumers passassem a resolver referências por esse ID;
7. corrigiu a caracterização de dados derivados: podem ser persistentes, desde que fora do bundle e reconstruíveis/sincronizáveis;
8. removeu `_v2` e `status: deprecated` automáticos, incompatíveis com Duplicate Act Handling e Human-Owned `status`;
9. removeu autorização de escrita no bundle pelo `juridico-cli`;
10. removeu prescrição de purga/reindexação atômica específica, mantendo o comportamento dependente da estratégia de sincronização do Retrieval Contract;
11. tratou Git como histórico/versionamento, não como substituto semântico de Stable Concept Identity;
12. ampliou Required Baseline Updates para todas as baselines que ainda registram a decisão como aberta.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
