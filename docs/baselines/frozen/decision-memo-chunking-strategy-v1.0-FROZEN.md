# MEMORANDO DE DECISÃO ARQUITETURAL: CHUNKING STRATEGY (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 13 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v11-FROZEN.md`, `retrieval-contract-v2.5-FROZEN.md`, `legal-okf-profile-v1.3-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `external-source-ingestion-contract-v1.6-FROZEN.md`, `phase1-operational-spec-v1.0-FROZEN.md`, `decision-memo-search-execution-path-v1.0-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md`, `decision-memo-verification-history-schema-v1.0-FROZEN.md`, `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md` e `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`.

---

## 1. Problem Statement

A **Open Decision — Chunking Strategy** deve definir como produzir unidades textuais derivadas para retrieval preservando:

- literalidade;
- vínculo com o `concept_id`;
- proveniência;
- rastreabilidade física por página quando explicitamente sustentada;
- reconstruibilidade;
- Zero-Write no bundle.

O chunker opera **sobre o concept canônico atual materializado de `repo_jur/bundle/`**, não sobre a saída intermediária da Fase 1.

A Fase 1 produz a conversão física integral; o Produtor OKF pode posteriormente criar concepts diferentes, subconjuntos ou conceitos sintéticos. Por isso, somente o concept publicado no bundle é a fonte correta para chunking de retrieval.

---

## 2. Frozen Constraints

1. Chunks são derivados e não canônicos. **[Existing FROZEN Requirement]**
2. Chunks ficam fora de `/bundle/`. **[Existing FROZEN Requirement]**
3. Chunks devem ser descartáveis e reconstruíveis. **[Existing FROZEN Requirement]**
4. `concept_id` posicional é a canonical reference/join key. **[Existing FROZEN Requirement]**
5. Rename/move altera `concept_id`. **[Existing FROZEN Requirement]**
6. Não existe Stable Chunk ID canônico. **[Existing FROZEN Requirement]**
7. Search Execution Path está CLOSED como **Lexical-First, Hybrid-Ready**. **[Existing FROZEN Requirement]**
8. O índice lexical inicial é concept-level. O fechamento de Chunking Strategy não obriga sua substituição por um índice chunk-level. **[Existing FROZEN Requirement]**
9. Nenhum embedding model, vector DB, ANN/HNSW ou algoritmo de fusão é selecionado. **[Existing FROZEN Requirement]**
10. Reranking Pipeline permanece OPEN. **[Existing FROZEN Requirement]**
11. `page_refs` somente existem quando a associação física de página é explícita e inequívoca. **[Existing FROZEN Requirement]**
12. Em chunks que cruzam páginas de uma única evidência mapeável, todas as páginas relacionadas devem ser preservadas. **[Existing FROZEN Requirement]**
13. Em provenance multi-fonte, não se inventa associação página→fonte. **[Existing FROZEN Requirement]**
14. Concepts sintéticos/multi-fonte sem associação física explícita não recebem paginação artificial. **[Existing FROZEN Requirement]**
15. `text_content` retornado pelo retrieval é um fragmento literal do corpo Markdown canônico. **[Existing FROZEN Requirement]**
16. Canonical materialization impede que índice/chunk stale substitua o bundle como fonte de verdade. **[Existing FROZEN Requirement]**

---

## 3. Required Properties

### 3.1 Canonical Source

O chunker deve receber o **corpo Markdown canônico do concept atual** depois do parsing do frontmatter YAML.

Frontmatter pode fornecer metadados retrieval-relevant, mas não faz parte de `text_content`.

### 3.2 Literal Contiguity

Cada `text_content` de chunk deve corresponder a um **intervalo contíguo** do corpo canônico.

É proibido:

- sintetizar frases;
- reordenar texto;
- corrigir ortografia;
- concatenar trechos não contíguos como se fossem um único trecho original;
- repetir artificialmente cabeçalhos/títulos dentro de `text_content`.

Contexto derivado adicional deve ser armazenado separadamente.

### 3.3 Structural Preference

As fronteiras preferenciais devem respeitar blocos Markdown e unidades naturais, como:

- headings;
- parágrafos;
- itens/listas;
- blockquotes;
- tabelas;
- fenced code blocks;
- outros blocos reconhecidos pelo parser.

### 3.4 Page-Aware Mapping

O chunker deve mapear os spans textuais do corpo para o contexto de página física **antes ou durante** a geração dos chunks.

A presença literal do marker dentro do chunk não é requisito para produzir `page_refs`; o que importa é a interseção inequívoca do span do chunk com intervalos de página explicitamente representados no concept.

### 3.5 Size Control Without Arbitrary Architecture Thresholds

A arquitetura deve possuir:

- `soft_limit`;
- `hard_limit`;
- unidade de medição definida;
- política de forced split;
- política de overlap.

Os valores numéricos pertencem a um **Chunking Profile versionado**, não ao contrato arquitetural FROZEN, salvo futura calibração empírica suficiente para promover valores específicos.

### 3.6 Determinism

Para o mesmo:

- concept canônico;
- Chunking Profile;
- versão lógica do chunker;

a geração deve produzir chunks deterministicamente equivalentes.

---

## 4. Candidate Models

### 4.1 Fixed-Size Blind Chunking

Divide mecanicamente por tamanho.

**Rejeitado como estratégia principal**, pois pode cortar estruturas jurídicas e tokens importantes sem necessidade.

### 4.2 Page-Grain Chunking

Cada página vira um chunk.

Excelente para proveniência, porém a página física não é fronteira semântica confiável.

**Rejeitado como estratégia principal.**

### 4.3 Structural Block Chunking

Usa blocos Markdown como unidades.

Preserva bem estrutura, mas blocos podem variar drasticamente de tamanho.

### 4.4 Semantic/Model-Driven Chunking

Usa embeddings/modelos para decidir fronteiras.

Não é necessário para obter uma estratégia determinística e local-first; também adiciona acoplamento operacional desnecessário ao rebuild.

### 4.5 Structural Block-First, Page-Aware, Size-Profiled

Usa blocos estruturais como unidades preferenciais, agrupa spans contíguos segundo um perfil de tamanho, permite cruzar páginas e executa forced split determinístico apenas quando necessário.

**Modelo recomendado.**

---

## 5. Comparative Analysis

| Critério | Fixed | Page | Structural | Semantic | Structural + Page-Aware + Profiled |
|---|---:|---:|---:|---:|---:|
| Literalidade | Alta | Alta | Alta | Variável | Alta |
| Contexto jurídico | Baixo | Médio | Alto | Alto | Alto |
| Page traceability | Frágil | Alta | Alta com mapping | Variável | Alta |
| Tamanho controlável | Alto | Baixo | Médio | Médio | Alto |
| Local-first | Alto | Alto | Alto | Baixo/Variável | Alto |
| Rebuild determinístico | Alto | Alto | Alto | Variável | Alto |
| Technology neutrality | Alto | Alto | Alto | Baixo | Alto |
| Preserva contiguous `text_content` | Sim | Sim | Sim | Depende | **Sim** |

---

## 6. Recommended Decision

Adotar **Structural Block-First, Page-Aware, Size-Profiled Chunking**.

A decisão congela:

- a natureza estrutural das fronteiras;
- a preservação de spans contíguos;
- o mapeamento físico de páginas;
- a necessidade de limites soft/hard;
- forced split determinístico;
- isolamento dos chunks;
- identidade apenas derivada;
- sincronização/rebuild.

A decisão **não congela valores arbitrários como 1.200/2.000 caracteres ou overlap 100–200** sem calibração sobre o corpus real.

---

## 7. Canonical Input and Parsing

### 7.1 Source

```text
repo_jur/bundle/<concept>.md
        ↓
parse YAML frontmatter
        ↓
canonical Markdown body
        ↓
page/source interval mapping
        ↓
structural parser
        ↓
chunks derivados
```

### 7.2 Frontmatter

Frontmatter:

- não entra em `text_content`;
- pode alimentar filtros/metadados derivados;
- continua regido pelo Legal OKF Profile.

### 7.3 Parser

A arquitetura não seleciona uma biblioteca Markdown específica.

A implementação deve possuir uma versão lógica do parser/chunker para que mudanças de interpretação estrutural provoquem invalidação/rebuild controlado.

---

## 8. Chunk Boundaries

### 8.1 Primary Units

Blocos estruturais contíguos são as unidades preferenciais.

### 8.2 Grouping

Blocos adjacentes podem ser agrupados enquanto:

- permanecerem contíguos no corpo canônico;
- a inclusão não violar `hard_limit`;
- o agrupamento for compatível com a política do Chunking Profile.

### 8.3 Soft Limit

`soft_limit` é um alvo de tamanho.

Ao atingir/ultrapassar esse alvo, o chunker prefere fechar o chunk na próxima fronteira estrutural apropriada sem ultrapassar o `hard_limit`.

### 8.4 Hard Limit

`hard_limit` é um limite operacional máximo para chunks normais.

Um bloco individual maior que esse limite ativa forced split.

### 8.5 Versioned Chunking Profile

Os parâmetros operacionais residem em perfil versionado, conceitualmente:

```yaml
profile_version: "..."
measurement_unit: "..."
soft_limit: ...
hard_limit: ...
forced_split_overlap: ...
```

Regras:

- `soft_limit > 0`;
- `hard_limit > soft_limit`;
- unidade deve ser determinística e documentada;
- perfil não depende obrigatoriamente de tokenizer/modelo de embedding;
- qualquer alteração do perfil invalida/reconstrói os chunk sets afetados.

Nenhum valor numérico inicial é FROZEN por este memo.

---

## 9. Forced Split

Quando uma unidade estrutural isolada exceder `hard_limit`, o chunker procura pontos de corte dentro do bloco na seguinte ordem conceitual:

1. fronteira estrutural interna segura;
2. quebra de linha;
3. limite de sentença/pontuação reconhecido deterministicamente;
4. whitespace;
5. último recurso: corte estrito conforme a unidade de medição do perfil.

Em todos os casos:

- nenhum caractere é perdido;
- ordem é preservada;
- cada chunk continua sendo span contíguo;
- offsets/ranges derivados permitem reconstruir a origem.

O chunker não “corrige” o texto para produzir fronteiras melhores.

---

## 10. Page References

### 10.1 Marker Mapping

Markers `[[Pág. N]]` do corpo canônico definem mudanças de contexto físico.

O chunker deve construir uma representação de intervalos, por exemplo:

```text
body range A → page 12
body range B → page 13
body range C → page 14
```

### 10.2 `page_refs`

Para um chunk, `page_refs` corresponde à união ordenada das páginas cujos intervalos físicos intersectam o span do `text_content`.

Exemplo:

```text
chunk span intersects page 12 + page 13
→ page_refs: [12, 13]
```

Essa regra funciona mesmo quando o marker `[[Pág. 13]]` não for textualmente incluído no recorte entregue ao consumidor.

### 10.3 No Initial Active Page

Se texto aparecer antes de qualquer marker físico e não houver outra associação inequívoca, o chunker **não inventa** `page_refs`.

### 10.4 Multi-PDF / Multi-Source

Em concepts com múltiplos PDFs:

- `page_refs` só pode ser emitido se o trecho tiver mapeamento físico inequívoco;
- `source_refs` específicos só são emitidos quando a atribuição estiver explicitamente sustentada pelo concept;
- não se usa “última fonte presumida”;
- não se inventa page→source mapping.

### 10.5 Synthetic / Abstract Concepts

A ausência de `page_refs` depende da ausência de associação física explícita, **não do `type` nominal do concept**.

Um `TemaJuridico`, `PrecedenteVinculante` ou qualquer outro type pode ter ou não evidência física; a regra segue os dados efetivamente presentes.

---

## 11. Chunk Identity

### 11.1 Canonical Identity

Não existe Stable Chunk ID canônico.

`concept_id` continua sendo a única canonical join key.

### 11.2 Derived Chunk Set

Cada geração deve ser identificável por um `chunk_set_fingerprint` derivado de, no mínimo:

- identidade/conteúdo canônico relevante do concept;
- Chunking Profile version;
- chunker logical version.

O algoritmo físico de fingerprint é detalhe de implementação, desde que determinístico e adequadamente versionado.

### 11.3 Ordinal

Cada chunk possui `chunk_ordinal` determinístico dentro de seu chunk set.

### 11.4 Optional Runtime Reference

Uma implementação pode sintetizar uma referência operacional a partir de:

```text
concept_id
chunk_set_fingerprint
chunk_ordinal
```

Essa referência:

- é derivada;
- não é gravada no frontmatter;
- não é identidade canônica;
- pode mudar após conteúdo/profile/parser/version change.

### 11.5 Why `concept_id#chunk_N` Alone Is Insufficient

`concept_id#chunk_003` isoladamente pode apontar para texto diferente depois de uma alteração de conteúdo ou configuração.

Portanto, um ordinal pode ser usado operacionalmente apenas dentro de um chunk set identificado/versionado.

---

## 12. Overlap

### 12.1 Global Overlap

Não existe overlap global obrigatório entre chunks estruturais independentes.

### 12.2 Forced-Split Overlap

Overlap pode ser usado somente como política derivada do Chunking Profile para forced splits.

Ele deve:

- permanecer bounded;
- preservar spans contíguos;
- não alterar caracteres;
- ser computado deterministicamente;
- possuir page refs calculadas sobre o span efetivamente duplicado.

### 12.3 Numerical Value

Nenhuma faixa como `100–200 caracteres` é FROZEN nesta baseline.

O valor pode ser zero.

Calibração posterior pode alterar o perfil sem alterar o modelo arquitetural.

---

## 13. Special Structures

### 13.1 Headings

Headings são texto canônico.

Podem ser agrupados com conteúdo subsequente quando isso formar um span contíguo.

É proibido copiar o mesmo heading artificialmente para múltiplos `text_content`.

Para preservar contexto hierárquico sem duplicar texto, o chunk record pode manter metadado derivado como:

```text
section_path
```

### 13.2 Tables

Uma tabela deve permanecer inteira quando couber no perfil.

Se exceder `hard_limit`:

- dividir em ranges contíguos de linhas;
- preservar literalmente as linhas pertencentes a cada range;
- não repetir o cabeçalho dentro de `text_content` de fragmentos posteriores.

O cabeçalho pode ser exposto separadamente como contexto derivado, por exemplo:

```text
table_header_context
```

Esse contexto não pode ser apresentado como se fosse parte contígua do trecho recuperado.

### 13.3 Lists

Listas devem preferir fronteiras entre itens.

Sublistas e itens dependentes são preservados juntos quando possível.

Forced split continua obedecendo literal contiguity.

### 13.4 Blockquotes / Code Blocks

Devem ser tratados como blocos estruturais.

Se excederem `hard_limit`, forced split deve preservar ordem e caracteres sem sintetizar cercas, headings ou linhas que não façam parte do span.

---

## 14. Derived Chunk Record

Um chunk derivado pode possuir estrutura conceitual como:

```json
{
  "concept_id": "jurisprudencia/exemplo",
  "chunk_set_fingerprint": "<derived>",
  "chunk_ordinal": 3,
  "text_content": "<literal contiguous body span>",
  "body_range": {
    "start": 1200,
    "end": 1980
  },
  "page_refs": [12, 13],
  "source_refs": [],
  "section_path": [],
  "warnings": []
}
```

### Required

- `concept_id`;
- chunk set identity/fingerprint;
- ordinal;
- literal `text_content`;
- deterministic body range/span representation.

### Conditional

- `page_refs`;
- `source_refs`.

### Optional derived context

- `section_path`;
- `table_header_context`;
- warnings/diagnostics.

Nenhum desses campos é promovido automaticamente ao frontmatter canônico.

---

## 15. Synchronization / Rebuild

### 15.1 Rebuild Key

Um chunk set é válido somente enquanto permanecerem equivalentes:

- canonical concept content;
- `concept_id`;
- Chunking Profile;
- chunker logical version.

### 15.2 Create

Novo concept → gerar novo chunk set.

### 15.3 Content Update

Mudança de corpo/conteúdo relevante → invalidar o chunk set anterior e gerar novo.

### 15.4 Rename / Move

Novo path → novo `concept_id` → chunk set anterior invalidado e reconstruído sob a nova join key.

Não há tentativa de preservar uma identidade antiga de chunk.

### 15.5 Delete

Concept ausente → derived chunk set correspondente deve ser removido/inativado.

### 15.6 Profile / Parser Change

Mudança de Chunking Profile ou chunker logical version → rebuild dos chunk sets afetados, mesmo se o Markdown canônico não mudou.

### 15.7 Fingerprint Algorithm

Este memo não congela MD5 ou SHA-256 para fingerprint de chunk set.

O fingerprint:

- é derivado;
- não prova autenticidade;
- não é identidade jurídica;
- serve a sincronização/invalidação.

### 15.8 Full Rebuild

Deve existir full rebuild que:

1. descarta chunks/índices derivados;
2. percorre o bundle atual;
3. materializa cada concept;
4. reconstrói chunks;
5. não escreve em `/bundle/`.

---

## 16. Relationship to Search Execution Path

O Search Execution Path continua **Lexical-First, Hybrid-Ready**.

O fechamento desta decisão:

- disponibiliza uma estratégia oficial de chunks derivados;
- **não obriga** substituir o concept-level lexical index por chunk-level lexical index;
- não ativa automaticamente embeddings;
- não seleciona vector DB;
- não seleciona fusion algorithm;
- não seleciona reranker.

Uma futura implementação semântica pode consumir os chunks definidos aqui sem alterar o bundle.

---

## 17. Reranking Boundary

Reranking Pipeline permanece **OPEN**.

Esta decisão não seleciona:

- cross-encoder;
- LLM reranker;
- local vs API;
- top-k;
- latency budget;
- ranking fusion;
- score normalization.

Chunking produz unidades derivadas; reranking decide, se adotado, como reordenar candidates posteriormente.

---

## 18. Invariants

1. Chunking lê concepts canônicos do bundle; não lê a saída intermediária da Fase 1 como source of truth de retrieval.
2. Zero-Write no bundle.
3. Chunks são derivados, descartáveis e reconstruíveis.
4. `concept_id` é canonical join key.
5. Não existe Stable Chunk ID canônico.
6. `text_content` é sempre um span literal contíguo do body canônico.
7. Contexto repetido/sintético nunca é injetado em `text_content`.
8. Page markers podem ser cruzados; quebra física de página não força quebra de chunk.
9. `page_refs` preserva todas as páginas inequivocamente relacionadas ao span.
10. Sem associação física inequívoca, `page_refs` é omitido.
11. Multi-source nunca recebe page→source mapping inventado.
12. A ausência/presença de page refs depende dos dados, não do `type`.
13. Blocos estruturais são fronteiras preferenciais.
14. Soft/hard limits existem, mas seus valores ficam em Chunking Profile versionado.
15. Nenhum valor 1.200/2.000 caracteres é requisito FROZEN.
16. Overlap global não é obrigatório.
17. Nenhuma faixa 100–200 caracteres é requisito FROZEN.
18. Forced split nunca perde/reordena caracteres.
19. Headings/table headers não são artificialmente copiados para `text_content`.
20. Chunk set é invalidado por content/profile/chunker-version change.
21. Rename/move invalida derived chunk identity antiga.
22. Chunking não altera o concept-level lexical path já FROZEN.
23. Chunking não seleciona embeddings, vector DB, ANN, fusion ou reranking.
24. Reranking Pipeline permanece OPEN.

---

## 19. Required Baseline Updates

Após aprovação e congelamento:

### 19.1 Retrieval Contract

Criar `retrieval-contract-v2.6-FROZEN.md` que:

- marque Chunking Strategy CLOSED;
- incorpore Structural Block-First, Page-Aware, Size-Profiled;
- preserve literal contiguous `text_content`;
- formalize `page_refs` por span/interval mapping;
- registre Chunking Profile versionado;
- registre derived chunk-set identity;
- mantenha concept-level lexical index como caminho inicial;
- mantenha Reranking Pipeline OPEN.

### 19.2 Architecture Phase 2

Criar `arquitetura-fase2-repo-jur-v12-FROZEN.md` que:

- marque Chunking Strategy CLOSED;
- registre chunks como derivados do concept canônico;
- registre size-profiled structural chunking;
- preserve Search Execution Path CLOSED;
- deixe Reranking Pipeline como única Open Decision de retrieval.

### 19.3 Baselines sem mudança normativa necessária

Não precisam de nova versão:

- Legal OKF Profile;
- Lifecycle & Field Ownership;
- Concept Identity & Physical Structure;
- ESIC;
- Phase 1 Operational Specification;
- Ingress Transport Protocol;
- Phase 1 Quality Gate.

---

## 20. Remaining Open Questions

Após o fechamento desta decisão, permanece:

1. **Reranking Pipeline**

Não são promovidos a novas Open Decisions arquiteturais:

- valores numéricos de `soft_limit`;
- valores numéricos de `hard_limit`;
- overlap;
- biblioteca Markdown;
- algoritmo de fingerprint derivado;
- política de ativação de embeddings;
- engine de vector storage.

Esses itens são parâmetros/implementações versionados, desde que preservem os invariantes desta decisão.

---

## 21. Technical Review Corrections

A revisão técnica corrigiu os seguintes pontos da proposta inicial:

1. mudou a fonte do chunker da saída da Fase 1 para o **concept canônico materializado do bundle**;
2. separou parsing de frontmatter e chunking do body;
3. preservou o Modelo 5, refinado para **Structural Block-First, Page-Aware, Size-Profiled**;
4. removeu `1.200` e `2.000` caracteres como thresholds arquiteturais sem calibração empírica;
5. removeu aproximações normativas em tokens, evitando dependência implícita de tokenizer;
6. introduziu Chunking Profile versionado para soft/hard/overlap;
7. removeu overlap `100–200` como faixa FROZEN;
8. formalizou `text_content` como span literal contíguo;
9. removeu repetição artificial de cabeçalho de tabela dentro de `text_content`;
10. moveu table/header context para metadado derivado separado;
11. proibiu duplicação artificial de headings em múltiplos `text_content`;
12. substituiu regex-local simples por **page interval mapping**, permitindo page refs corretas mesmo quando o marker não aparece dentro do recorte;
13. condicionou page refs à associação física explícita e inequívoca;
14. corrigiu multi-PDF/multi-source para nunca inventar page→source mapping;
15. removeu regras de página baseadas nominalmente em `TemaJuridico`/`PrecedenteVinculante`; a regra passa a depender dos dados efetivos;
16. substituiu `concept_id#chunk_N` como referência suficiente por chunk set versionado + ordinal;
17. removeu a promessa incorreta de que o mesmo ordinal sempre representaria o mesmo texto após mudanças;
18. tornou mudança de Chunking Profile/chunker version causa explícita de rebuild;
19. removeu MD5/SHA-256 como escolha arquitetural do fingerprint derivado;
20. deixou explícito que fechar Chunking Strategy não substitui automaticamente o concept-level lexical index nem ativa semantic search;
21. preservou Reranking Pipeline como única Open Decision de retrieval.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
