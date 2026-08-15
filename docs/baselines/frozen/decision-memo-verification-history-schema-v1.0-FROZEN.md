# MEMORANDO DE DECISÃO ARQUITETURAL: SCHEMA DE HISTÓRICO DE VERIFICAÇÃO (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v7-FROZEN.md`, `external-source-ingestion-contract-v1.3-FROZEN.md`, `legal-okf-profile-v1.2-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.3-FROZEN.md`, `retrieval-contract-v2.3-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md` e OKF v0.2.

---

## 1. Problem Statement

O campo nativo `verified` do OKF registra **eventos de verificação aplicáveis ao conteúdo atual do concept**. Quando uma alteração material atinge o objeto efetivamente verificado, os eventos anteriores deixam de ser reutilizáveis no `verified` ativo.

A **Open Decision — Verification History Schema** deve decidir como preservar, de forma estruturada, o fato histórico de que uma verificação real ocorreu e posteriormente deixou de valer para o estado atual, sem permitir que esse histórico seja interpretado como confiança ativa.

A decisão deve responder:

1. se histórico estruturado persistente é necessário;
2. onde armazená-lo;
3. qual é o schema mínimo;
4. quem registra a invalidação;
5. como garantir idempotência;
6. como separar `verified` ativo de histórico;
7. como preservar auditabilidade sem duplicar indevidamente a proveniência física.

---

## 2. Frozen Constraints

1. **`verified` contém apenas eventos reais de verificação.** **[Existing FROZEN Requirement]**
2. **Ausência de `verified` significa ausência de verificação ativa registrada.** **[Existing FROZEN Requirement]**
3. **O Produtor não cria verificação ativa automaticamente.** **[Existing FROZEN Requirement]**
4. **Mudança técnica não invalida `verified` automaticamente.** **[Existing FROZEN Requirement]**
5. **Mudança de hash, cardinalidade, source set ou path não invalida `verified` por si só.** É necessária análise da razão da mudança e de seu impacto sobre o objeto efetivamente verificado. **[Existing FROZEN Requirement]**
6. **Quando uma mudança material atinge o conteúdo, significado, páginas relevantes, proveniência material ou outro elemento coberto pela revisão, o evento anterior não pode permanecer/copiar-se para o `verified` ativo sem nova verificação real.** **[Existing FROZEN Requirement]**
7. **`status` é Human-Owned e independente de `verified`.** **[Existing FROZEN Requirement]**
8. **`concept_id` é posicional; Stable Concept Identity está CLOSED.** **[Existing FROZEN Requirement]**
9. **Duplicate Act Handling está CLOSED e ambiguidade material exige revisão humana.** **[Existing FROZEN Requirement]**
10. **Retrieval é Zero-Write sobre `/bundle/`.** **[Existing FROZEN Requirement]**
11. **SHA-256 identifica bytes da evidência PDF; não identifica concept, ato jurídico ou autenticidade.** **[Existing FROZEN Requirement]**

---

## 3. Required Properties

A solução deve:

1. preservar integralmente a semântica nativa de `verified`;
2. manter histórico e confiança ativa semanticamente separados;
3. registrar somente eventos de verificação que realmente existiram;
4. não inferir retroativamente escopo de revisão que nunca foi registrado;
5. ser idempotente;
6. sobreviver a rename/move junto com o concept quando o histórico for canônico;
7. não depender de Stable Concept Identity;
8. permitir distinguir quem verificou de quem declarou/registrou a invalidação;
9. não tratar mudança de hash como materialidade automática;
10. evitar duplicar todo o estado de proveniência apenas para formar um log histórico;
11. manter compatibilidade com consumidores OKF que desconheçam a extensão.

---

## 4. Candidate Models

### 4.1 Modelo A — Git History Only

Ao deixar um evento de ser aplicável ao conteúdo atual, ele é retirado do `verified` ativo. O estado anterior permanece recuperável no histórico Git do projeto.

**Vantagens:**

- nenhum novo campo;
- baixa complexidade;
- histórico completo de diffs no repositório.

**Limitações:**

- um bundle distribuído sem `.git` não leva consigo esse histórico;
- responder diretamente “quem verificou uma versão anterior e por que essa verificação foi retirada?” exige reconstrução histórica externa ao concept atual;
- o Git registra mudanças de arquivo, mas não oferece uma semântica estruturada própria para “verification invalidation”.

**[New Decision Proposal]**

### 4.2 Modelo B — Campo Histórico no Frontmatter

Criar a extensão top-level:

`repo_jur_verification_history`

O campo contém registros históricos de eventos que **existiram em `verified`** e posteriormente deixaram de ser aplicáveis ao conteúdo atual.

**Vantagens:**

- histórico portátil junto ao concept;
- separação explícita entre confiança ativa e auditoria histórica;
- consulta direta sem reconstrução do Git;
- compatível com extensibilidade do OKF.

**Riscos:**

- novo schema de projeto a validar;
- risco de duplicação se o append não for idempotente;
- risco semântico se consumidores tratarem a extensão como trust signal, o que deve ser proibido pelo perfil.

**[New Decision Proposal]**

### 4.3 Modelo C — Registro Estruturado Externo

Manter histórico em armazenamento externo ao bundle.

**Vantagens:**

- não aumenta o frontmatter;
- pode atender auditoria operacional ampla.

**Limitações:**

- exige mecanismo próprio de associação ao concept posicional;
- rename/move exige sincronização do registro externo;
- uma cópia isolada do bundle não contém a trilha histórica.

Esse modelo não é impossível, mas introduz acoplamento adicional sem necessidade demonstrada para a finalidade atual.

**[New Decision Proposal]**

---

## 5. Comparative Analysis

| Critério | Git Only | Histórico no YAML | Registro Externo |
|---|---|---|---|
| Compatibilidade OKF | Total | Total como extensão | Total |
| Novo schema canônico | Não | Sim | Não no bundle |
| Histórico acompanha exportação do bundle | Não necessariamente | Sim | Não necessariamente |
| Separação explícita ativo/histórico | Indireta | Direta | Direta |
| Rename/move | Dependente do histórico Git | Acompanha o arquivo | Exige sincronização |
| Consulta sem Git | Baixa | Alta | Depende do sistema externo |
| Complexidade | Baixa | Média | Média/Alta |
| Idempotência | Nativa no arquivo atual | Deve ser especificada | Deve ser especificada |

---

## 6. Recommended Decision

Adotar o **Modelo B — Campo Histórico no Frontmatter**.

Criar a extensão canônica de projeto:

`repo_jur_verification_history`

### Justificativa

O histórico de verificação é parte relevante da governança do próprio concept e deve permanecer disponível quando o bundle for distribuído sem seu repositório Git completo.

O OKF v0.2 permite chaves adicionais de frontmatter e exige que consumidores tolerem campos desconhecidos. A extensão, portanto, é compatível com o formato, desde que não altere a semântica nativa de `verified`.

### Limite da decisão

`repo_jur_verification_history` registra **histórico de eventos de verificação e de sua invalidação**. Ele **não substitui Git**, não constitui trust signal ativo e não pretende reconstruir sozinho todo o estado histórico de `sources`, hashes ou corpo do concept.

**[New Decision Proposal]**

---

## 7. Schema / Representation

### 7.1 Campo top-level

**Chave:** `repo_jur_verification_history`  
**Tipo:** lista de mappings  
**Obrigatoriedade:** condicional; omitido quando não houver evento histórico  
**Aplicabilidade:** qualquer concept  
**Retrieval-Relevant:** não para confiança/ranking canônico  
**Ownership:** **Producer-Owned archival structure**, com conteúdo derivado de eventos reais de verificação/invalidação.

A estrutura é mantida pelo Produtor segundo regras determinísticas, mas ele não se torna autor da verificação original.

### 7.2 Entrada mínima

Cada item possui:

- **`by` — obrigatório:** Actor copiado exatamente do evento original `verified[].by`.
- **`at` — obrigatório:** timestamp original `verified[].at`.
- **`invalidated_at` — obrigatório:** instante em que o evento deixou de ser considerado aplicável ao conteúdo atual.
- **`invalidated_by` — obrigatório:** Actor que realizou ou autorizou a decisão de invalidação.
- **`reason` — obrigatório:** motivo estruturado da invalidação.

Valores permitidos de `reason` nesta baseline:

- `material_content_change`
- `material_provenance_change`
- `material_scope_change`
- `manual_invalidation`

### 7.3 Sem snapshot obrigatório de hash

Esta baseline **não adiciona `evidence_pdf_hash` obrigatório ao registro histórico**.

Motivos:

1. concepts podem ser não-PDF;
2. concepts podem possuir múltiplos PDFs;
3. mudança de hash não implica materialidade automaticamente;
4. o `verified` nativo não possui um campo de escopo que permita afirmar retroativamente quais PDFs específicos foram efetivamente cobertos por cada verificação;
5. obrigar um hash histórico criaria uma falsa precisão semântica.

A proveniência física atual continua governada por `sources`, `repo_jur_pdf_hash` e `repo_jur_pdf_hashes`. O estado histórico completo do arquivo continua disponível pelo Git quando o repositório estiver presente.

Se no futuro for necessário registrar explicitamente o **escopo/basis de cada nova verificação**, isso exigirá uma decisão própria e não deve ser inferido retroativamente por este schema.

### 7.4 Exemplo

```yaml
---
type: Jurisprudencia
title: "Decisão Fictícia"
generated:
  by: repo_jur_producer/1.0.0
  at: 2026-08-12T10:00:00Z
sources:
  - resource: "<stable-evidence-resource>"
repo_jur_pdf_hash: "<sha256-atual>"
repo_jur_verification_history:
  - by: "human:revisor_a"
    at: 2026-08-01T14:30:00Z
    invalidated_at: 2026-08-12T10:00:00Z
    invalidated_by: "process:materiality-review"
    reason: material_content_change
---
```

A ausência de `verified` significa que não existe verificação ativa registrada para o conteúdo atual.

---

## 8. Lifecycle Rules

### 8.1 Arquivamento de evento ativo

Um evento de `verified` somente é movido para o histórico quando:

1. ele existia realmente no concept anterior;
2. foi determinado que não se aplica mais ao conteúdo atual;
3. existe um Actor responsável pela invalidação;
4. a decisão não decorre apenas de hash/path/cardinalidade diferentes.

O Produtor então:

1. copia `by` e `at` sem modificá-los;
2. registra `invalidated_at`, `invalidated_by` e `reason`;
3. adiciona o registro uma única vez ao histórico;
4. retira o evento correspondente do `verified` ativo;
5. se não restar nenhum evento ativo, **omite a chave `verified`**.

### 8.2 Quem pode invalidar

`invalidated_by` identifica quem tomou ou autorizou a decisão semântica de invalidação:

- `human:<id>` para decisão humana;
- `process:<id>` para processo determinístico autorizado;
- `<producer>/<version>` somente se o próprio produtor for formalmente o Actor responsável pela regra determinística de invalidação, e não apenas o escritor mecânico do arquivo.

O fato de o Produtor escrever o frontmatter não significa, por si só, que ele seja o `invalidated_by`.

### 8.3 Re-verificação

Uma nova verificação real cria novo evento em `verified`.

O histórico anterior permanece inalterado.

Não existe “reativação” automática de registro histórico.

### 8.4 Rename / Move

Rename/move altera `concept_id`, mas não invalida verificação automaticamente.

O histórico, por estar no mesmo arquivo, acompanha o concept.

### 8.5 Idempotência

Cada evento original `(by, at)` pode ser arquivado no máximo uma vez no histórico do mesmo concept.

Reprocessamento que encontre:

- o `verified` já ausente; e
- o par `(by, at)` já presente no histórico

não cria novo registro nem atualiza `invalidated_at`.

---

## 9. Material Change Behavior

### 9.1 Regra central

A invalidação depende do **objeto efetivamente verificado**, não de um sinal técnico isolado.

### 9.2 Não são gatilhos automáticos

Isoladamente, não invalidam `verified`:

- mudança de SHA-256;
- transição singular ↔ plural;
- adição de fonte equivalente;
- rename/move;
- alteração de path;
- normalização estrutural;
- mudança de marcadores de página que não altere o conteúdo/páginas cobertos pela revisão.

### 9.3 Mudança material

Pode exigir invalidação quando alterar efetivamente:

- conteúdo jurídico relevante;
- significado/tese/dispositivo;
- corpo literal coberto pela revisão;
- páginas relevantes cobertas pela revisão;
- proveniência material relevante ao objeto revisado;
- escopo do concept verificado.

### 9.4 Ambiguidade

Se não for possível determinar de modo seguro se a mudança atinge o objeto verificado, não executar invalidação automática silenciosa; encaminhar para revisão humana conforme a governança vigente.

---

## 10. Active vs Historical Verification

### 10.1 Estado ativo

Somente `verified` participa da derivação de trust tier.

- sem `verified` → `unverified`;
- apenas verificadores não-humanos → `machine-confirmed`;
- pelo menos um `human:<id>` → `human-reviewed`.

### 10.2 Estado histórico

`repo_jur_verification_history`:

- nunca eleva trust tier;
- nunca conta como confirmação atual;
- nunca deve ser transformado automaticamente em `verified`;
- serve apenas para auditoria histórica.

### 10.3 Retrieval

Consumidores podem expor o histórico em consultas de auditoria, mas **devem ignorá-lo ao derivar confiança ativa**.

Esta decisão não cria boost, demote ou política de ranking.

---

## 11. Migration

### 11.1 Concepts existentes

Nenhum backfill artificial é obrigatório.

Concepts sem histórico simplesmente omitem `repo_jur_verification_history`.

### 11.2 Eventos históricos já existentes apenas no Git

Esta baseline **não exige reconstrução retroativa** de eventos antigos a partir de commits passados.

Motivo: reconstrução heurística poderia inventar `reason`, `invalidated_by` ou escopo não registrados no momento do evento.

Backfill só é permitido quando todos os dados necessários forem comprováveis e a migração for deliberadamente aprovada.

### 11.3 Round-trip

Consumidores OKF devem tolerar a chave adicional; ferramentas do `repo_jur` devem preservá-la em round-trip.

---

## 12. Invariants

1. `verified` representa somente confiança ativa do conteúdo atual.
2. Histórico nunca conta como `verified`.
3. Nenhum evento histórico pode ser inventado.
4. `by` e `at` históricos são cópias imutáveis do evento real original.
5. `invalidated_by` identifica o Actor da invalidação, não necessariamente o software que escreveu o arquivo.
6. Mudança de hash/cardinalidade/path não invalida automaticamente.
7. Materialidade é avaliada em relação ao objeto efetivamente verificado.
8. Se não houver verificação ativa, a chave `verified` é omitida.
9. `(by, at)` é a chave de idempotência do evento histórico dentro do concept.
10. `repo_jur_verification_history` não registra trust tier persistido.
11. O schema não introduz Stable Concept ID.
12. O schema não altera `status`.
13. O schema não duplica obrigatoriamente hashes PDF históricos.
14. Git continua sendo a trilha completa de diffs quando disponível; o novo campo oferece uma trilha semântica portátil de verificação/invalidação.
15. Retrieval permanece Zero-Write.

---

## 13. Required Baseline Updates

Após aprovação e congelamento:

### 13.1 Legal OKF Profile

Atualizar para nova versão controlada e incorporar formalmente:

- `repo_jur_verification_history`;
- tipo e obrigatoriedade condicional;
- schema mínimo;
- ownership arquivístico;
- proibição de uso como trust signal ativo.

### 13.2 Lifecycle & Field Ownership

Fechar `Verification History Schema` e incorporar:

- fluxo `verified` → histórico;
- regra de materialidade;
- `invalidated_by` como Actor da decisão;
- idempotência por `(by, at)`;
- ausência de invalidação automática por hash/cardinalidade/path.

### 13.3 ESIC

Remover `Verification History Schema` das Open Decisions.

Não transferir essa lógica para o **preflight de ingresso**: a manutenção do histórico pertence ao lifecycle canônico/Produtor OKF, não à aceitação física da evidência na Fase 1.

### 13.4 Retrieval Contract

Adicionar regra explícita de consumo:

- `repo_jur_verification_history` pode ser exposto para auditoria;
- deve ser ignorado na derivação de trust tier ativo;
- nenhuma política de ranking é criada por esta decisão.

### 13.5 Arquitetura Fase 2

Marcar `Verification History Schema` como CLOSED e removê-la das próximas decisões.

### 13.6 Baselines sem alteração necessária

`Concept Identity & Physical Structure` não requer mudança normativa por esta decisão, pois não mantém esta Open Decision e o novo campo não altera identidade física/lógica.

---

## 14. Remaining Open Questions

Permanecem abertas:

- **Ingress Transport Protocol**
- **Phase 1 Quality Gate**

No Retrieval Contract permanecem independentes:

- **Search Execution Path**
- **Chunking Strategy**
- **Reranking Pipeline**

### Questão futura separada, se necessária

- **Verification Scope/Basis Schema**: somente se o projeto futuramente precisar registrar, em cada novo evento de verificação, exatamente quais claims, fontes, páginas ou evidências foram cobertos pela revisão. Esta decisão não infere esse escopo retroativamente.

---

## 15. Technical Review Corrections

A revisão técnica corrigiu os seguintes pontos da proposta inicial:

1. removeu a regra de que qualquer mudança de hash invalida `verified`; hash/cardinalidade não implicam materialidade automaticamente;
2. removeu `evidence_pdf_hash` obrigatório do histórico, pois é inadequado para multi-PDF, non-PDF e pode atribuir um escopo de verificação que nunca foi registrado;
3. separou o Actor que **decide/autoriza a invalidação** do software que apenas escreve o arquivo;
4. classificou o novo campo como estrutura arquivística mantida pelo Produtor, preservando imutavelmente `by`/`at` dos eventos humanos ou de processos independentes;
5. substituiu `material_change_evidence` por `material_provenance_change`, que só se aplica quando a proveniência alterada é material ao objeto revisado;
6. acrescentou `material_scope_change` para mudanças no escopo efetivamente verificado;
7. determinou omissão de `verified` quando não houver eventos ativos, em vez de depender de lista vazia não definida pelo OKF;
8. definiu idempotência pelo par original `(by, at)`;
9. proibiu backfill heurístico de histórico a partir do Git;
10. removeu a prescrição de integrar invalidação ao preflight da Fase 1; essa lógica pertence ao lifecycle canônico;
11. corrigiu a afirmação de que logs externos necessariamente quebram em rename/move: eles são possíveis, mas exigem sincronização adicional;
12. manteve o Modelo B porque fornece uma trilha semântica portátil sem alterar a semântica nativa de `verified`.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
