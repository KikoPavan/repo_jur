# RETRIEVAL CONTRACT: CONEXÃO ENTRE O CORPUS CANÔNICO E MECANISMOS DE BUSCA (`repo_jur`)

Este documento estabelece o **Retrieval Contract (Contrato de Recuperação de Informação) v2.8** para a Fase 2 do projeto `repo_jur`, como atualização controlada das baselines anteriores.

**Status: FROZEN**

**Atualização v2.8:** incorpora `Reranking Pipeline` como CLOSED por `decision-memo-reranking-pipeline-v1.0-FROZEN.md`. O modelo oficial é Optional, Conditional, Profile-Governed e Fail-Open. Search Execution Path, Chunking Strategy e Reranking Pipeline estão CLOSED; não permanece Open Decision arquitetural de retrieval entre as atualmente registradas.

---

## 1. Finalidade e Escopo do Contrato

A finalidade deste contrato é assegurar que o corpus jurídico estruturado em `/bundle/` permaneça como a verdade única, soberana e portátil de dados, completamente independente de qualquer software ou banco de dados de runtime [21, 30, 98].

* **repo_jur Project Requirement**: O corpus de conhecimento contido no subdiretório `/bundle/` é um ativo canônico e não pode sofrer mutações, alterações estruturais ou divisões físicas **motivadas por necessidades do mecanismo de retrieval**, como janela de contexto, chunking ou schemas de bancos derivados. O OKF v0.2 define o formato como Markdown com YAML frontmatter e não prescreve infraestrutura de serving, storage ou query.
* **repo_jur Project Requirement**: Todas as estruturas de dados derivadas, como chunks temporários, índices lexicais, embeddings vetoriais, representações relacionais ou de grafos de adjacência, além de caches de sessão e estados de busca, são classificadas como **dados derivados e reconstruíveis** [135]. Elas devem residir obrigatoriamente fora da árvore física do `/bundle/` e sua reconstruibilidade completa é mandatória [135, 187].
* **Recommendation**: O contrato deve ser totalmente agnóstico em relação à tecnologia de armazenamento (SQL, NoSQL, vetorial ou grafos) e ao protocolo de transporte (stdio, HTTP ou RPC), assegurando que novos motores de busca possam ser acoplados ou substituídos sem alteração no corpus canônico [28, 182].

---


## 1A. Bounded-Context Scope — CLOSED

Este contrato é normativo somente para **Legal Knowledge**.

Canonical source:

```text
repo_jur/bundle/
├── legislacao/
├── jurisprudencia/
├── temas/
└── precedentes/
```

`Judicial Process Retrieval` não é coberto por esta baseline.

É proibido construir, sob este contrato, índice compartilhado que misture Legal Knowledge e documentos processuais.

Qualquer retrieval para o bounded context Judicial Process exige contrato/decisão própria.

---

## 2. Responsabilidades das Camadas

Para manter a separação estrita de responsabilidades, as obrigações da base de dados (passiva) e do mecanismo de recuperação (ativo) são definidas da seguinte forma [184]:

### 2.1 Corpus Canônico (`repo_jur/bundle/`)
* **repo_jur Project Requirement**: Fornecer concept documents Markdown íntegros, contendo YAML frontmatter válido e corpo governado pelo *Lifecycle & Field Ownership v1.4*. Concepts literais derivados de PDF preservam o conteúdo canônico produzido pela Fase 1 e os marcadores físicos `[[Pág. N]]` quando aplicáveis; concepts abstratos ou sintéticos seguem seu próprio body ownership.
* **repo_jur Project Requirement**: Servir como o corpus jurídico canônico, mantendo o histórico de auditorias e versionamento de forma exclusiva no Git (por exemplo, por meio de commits, sendo o uso de pull requests um fluxo de trabalho opcional) [35, 195].

### 2.2 Consumidor de Retrieval (Mecanismo de Busca / Indexador / MCP Server)
* **repo_jur Project Requirement**: Realizar a leitura fria e não destrutiva do subdiretório `/bundle/`, interpretando gramaticalmente o YAML frontmatter e o corpo de cada concept document [103, 159].
* **repo_jur Project Requirement**: O mecanismo de recuperação pode criar de forma opcional e sob demanda quaisquer estruturas derivadas e índices necessários para sua própria performance de busca e recuperação — tais como fatias textuais temporárias (*chunks*), índices lexicais, representações de vetores de características (*embeddings*) ou grafos de relacionamentos —, sem persistir nenhuma alteração em disco dentro do diretório `/bundle/` [126, 135].
* **repo_jur Project Requirement**: Expor ao agente consumidor (como o Hermes) as ferramentas de busca e recursos de forma estruturada, assegurando que cada fragmento recuperado contenha a respectiva marcação de proveniência lógica de rede e integridade física [79, 132].

---

## 3. Identificador de Conceito Canônico (Canonical OKF Concept ID)

* **OKF v0.2 Normative Requirement**: O identificador de conceito (`concept_id`) é determinado obrigatoriamente pelo caminho relativo do arquivo Markdown a partir da raiz do bundle, removendo-se o sufixo `.md` [56]. Este identificador é posicional à árvore de diretórios do bundle e, portanto, se alterará caso o arquivo de conceito seja movido ou renomeado dentro da estrutura do bundle [56].
    * *Sintaxe*: `classe_juridica/conceito_slug` (ou `/classe_juridica/conceito_slug`) [56].
    * *Exemplos fictícios*: `pasta_leis/norma_slug_exemplo` ou `pasta_documentos/documento_slug_ficticio`.
* **repo_jur Project Requirement**: O mecanismo de recuperação e quaisquer estruturas derivadas devem utilizar o `concept_id` baseado no caminho relativo como chave canônica de referência e associação (`canonical reference/join key`) para relacionar os dados derivados ao concept de origem.
---

## 4. Requisitos Mínimos do Resultado Recuperado

Independentemente do algoritmo de pesquisa executado (busca lexical, busca vetorial por proximidade ou caminhada em grafos), qualquer fragmento de texto retornado pelo mecanismo de busca para o agente consumidor deve estruturar as informações de proveniência lógica. Os campos variam de acordo com a classe do conceito recuperado [46, 112]:

### 4.1 Campos Universais (Obrigatórios para todos os conceitos)
1. **`concept_id`**: O identificador canônico OKF do documento de conceito de onde o trecho foi extraído [56].
2. **`text_content`**: O fragmento de texto literal recuperado da seção do corpo Markdown [39].
3. **`source_refs`** (Condicional): Referências de proveniência às fontes originais do documento (obtidas da família `sources` do frontmatter YAML) preservadas quando existirem no conceito original [42, 186].
    * *Regra de Atribuição*: Se o documento contiver múltiplas fontes e houver uma associação específica (como notas de rodapé atribuindo claims a IDs de sources no corpo do Markdown) [45, 67], o mecanismo deve preservar e reportar essa atribuição específica. Se não houver associação explícita por trecho, o mecanismo **não** deve inventar qual source originou o trecho, reportando as fontes em nível de documento geral.

### 4.2 Campos Condicionais para Concepts com Evidência PDF

1. **`page_refs`**: Lista das páginas físicas associadas ao trecho **quando essa associação estiver explicitamente representada e for inequívoca**. Se um chunk cruzar fronteiras de página, deve incluir todas as páginas relacionadas; é proibido escolher uma página por maioria de caracteres.
2. **Proveniência de exatamente 1 PDF**:
   * **`source_pdf`**: referência estável à única evidência PDF, derivada de `sources[].resource`.
   * **`repo_jur_pdf_hash`**: SHA-256 copiado do campo singular do concept.
3. **Proveniência de 2 ou mais PDFs**:
   * **`source_refs`** deve preservar os `sources[].id` e recursos relevantes já presentes no concept.
   * **`repo_jur_pdf_hashes`**: mapping `sources[].id` → SHA-256 copiado do frontmatter canônico.
   * O mecanismo **não deve inventar** associação página→fonte quando o concept não a declarar explicitamente.
   * Concepts sintéticos multi-fonte não devem receber uma sequência global artificial de `page_refs`.
4. **Exclusividade**: o envelope de um concept não deve apresentar simultaneamente `repo_jur_pdf_hash` e `repo_jur_pdf_hashes`, refletindo a regra canônica do Legal OKF Profile v1.3.

### 4.3 Campos Opcionais / Derivados
* **`trust_tier`**: O nível de confiança derivado de forma dinâmica com base no preenchimento e tipo de assinaturas presentes no campo `verified` (*unverified*, *machine-confirmed* ou *human-reviewed*) [47, 51, 146]. Trata-se de um metadado opcional derivado, não sendo um campo canônico obrigatório.
* **`repo_jur_verification_history`**: Campo canônico de auditoria histórica definido por `decision-memo-verification-history-schema-v1.0-FROZEN.md`. Pode ser exposto em consultas de auditoria, mas deve ser ignorado ao derivar `trust_tier`, filtros de confiança e políticas normativas de ranking.

---

## 5. Cadeia Obrigatória de Proveniência

Cada resultado recuperado deve permanecer rastreável ao concept canônico e às fontes que efetivamente constam no bundle.

```text
Trecho Recuperado
      │
      ▼
concept_id
      │
      ▼
source_refs (quando existirem)
      │
      ├── exatamente 1 PDF ──► source_pdf + repo_jur_pdf_hash
      │
      └── 2+ PDFs ───────────► sources[].id + repo_jur_pdf_hashes
```

* **repo_jur Project Requirement**: `page_refs` participa da cadeia apenas quando o trecho possuir associação física de página explícita e inequívoca.
* **repo_jur Project Requirement**: Em chunks que cruzem páginas de uma única evidência PDF, todas as páginas relacionadas devem ser preservadas.
* **repo_jur Project Requirement**: Em provenance multi-fonte, o mecanismo deve preservar atribuições explícitas a `sources[].id`, mas não deve inferir qual fonte ou página originou um trecho quando o concept não fornecer essa associação.
* **repo_jur Project Requirement**: SHA-256 identifica os bytes da evidência física; não identifica logicamente o concept e não prova autenticidade jurídica.

---

## 6. Regras para Chunking Derivado

* **repo_jur Project Requirement**: Se houver fatiamento de texto (`chunking`), os chunks serão artefatos derivados, permanecerão fora de `/bundle/` e preservarão a rastreabilidade e a proveniência do concept de origem. O contrato não determina em qual etapa operacional o chunking será executado. Chunks podem cruzar páginas; quando isso ocorrer, devem carregar todas as `page_refs` correspondentes.
* **Recommendation**: Cada chunk gerado pode herdar as propriedades semânticas do frontmatter YAML do conceito pai (como `type` e `tags` se declarados retrieval-relevant), permitindo o acoplamento de filtros lógicos rápidos em segundo plano antes da correspondência de vetores ou strings [46, 60].

---

## 7. Uso de Metadados Estruturados para Filtros Jurídicos

* **repo_jur Project Requirement**: O indexador derivado deve realizar o parsing sistemático do frontmatter YAML de cada conceito OKF e traduzi-lo para uma representação estruturada adequada ao mecanismo de retrieval [59, 135].
* **repo_jur Project Requirement**: Somente metadados declarados explicitamente como **retrieval-relevant** (em configurações do sistema ou definições de pacotes de schemas) poderão ser utilizados como filtros estruturados na requisição de busca. O sistema de recuperação não deve exigir que todo campo `repo_jur_*` seja automaticamente filtrável.
* **repo_jur Project Requirement**: Os filtros mínimos de busca do contrato de recuperação devem suportar as chaves universais do OKF [60, 69]:
    * `type`: Filtragem exata por classe jurídica (`type: Legislacao`, `type: Jurisprudencia`) [37].
    * `status`: Exclusão ou inclusão condicional de rascunhos ou conceitos obsoletos (`status: stable`, `status: deprecated`) [69].
    * `tags`: Filtros transversais por temas jurídicos ou ramos de direito mapeados na base (quando declaradas retrieval-relevant) [60].

---

## 8. Tratamento de Links e Relações entre Concepts

* **OKF v0.2 Normative Requirement**: O grafo de relações no OKF é modelado no corpo do Markdown por markdown links direcionados convencionais [21, 48]. O OKF não possui links tipados na sintaxe de escrita; a semântica da relação é descrita em prosa livre ao redor do link [21, 71].
* **Recommendation**: Se um grafo de relações derivado for criado, o mecanismo de recuperação pode possuir uma rotina estritamente determinística de extração de arestas de links Markdown (sem custos de API de LLMs cognitivos) executada durante a varredura do bundle, registrando as conexões em uma tabela de junção em memória ou banco relacional derivado [42].
* **Recommendation**: O mecanismo de busca pode expor ferramentas de travessia de grafo baseadas em saltos de relacionamento (multi-hop traversal), permitindo recuperar caminhos de julgados e precedentes correlacionados [39, 41].

---

## 9. Requisitos de Read-Only e Zero-Write no Bundle

* **repo_jur Project Requirement**: Toda a infraestrutura do mecanismo de recuperação opera sob a regra de **segurança de somente leitura (Zero-Write)** em relação ao diretório de dados canônico `/bundle/` [159, 187].
* **repo_jur Project Requirement**: Zero-Write significa a impossibilidade absoluta de alterar os arquivos sob `/bundle/`. É estritamente proibido que as rotinas de recuperação, geração de embeddings, compilação de índices ou caches de sessões gravem, modifiquem ou excluam qualquer arquivo sob esta árvore [135, 159].
* **repo_jur Project Requirement**: A restrição de Zero-Write **não impede** o mecanismo de escrever em seus próprios índices derivados, bancos de dados privados ou caches em disco, contanto que residam inteiramente fora do subdiretório `/bundle/` e, caso residam dentro do worktree Git, sejam declarados no arquivo `.gitignore` [113, 135].

---

## 10. Reconstrução Completa de Índices Derivados

* **repo_jur Project Requirement**: O subdiretório `repo_jur/bundle/` é declarado como a **fonte canônica de todo o conhecimento jurídico** do projeto (§3) [103]. Toda a infraestrutura de indexação (tais como índices lexicais, bancos SQLite, caches de busca e bancos vetoriais derivados) é classificada de forma estrita como dados derivados e voláteis, não fazendo parte do corpus canônico ou do versionamento de dados [135]. Se esses artefatos derivados forem temporariamente criados ou residirem dentro do worktree do Git do repositório maior, eles deverão ser obrigatoriamente incluídos no arquivo `.gitignore` para evitar a poluição do controle de versão do Git [113, 135].
* **repo_jur Project Requirement**: Quando o mecanismo de retrieval utilizar índices derivados persistentes, deverá existir um processo automatizado e reproduzível de reconstrução ou sincronização desses índices a partir do corpus canônico e da configuração/versionamento do mecanismo. Essa obrigação não se aplica a mecanismos que realizem busca diretamente no filesystem sem índices persistentes.
* **repo_jur Project Requirement**: O contrato **não exige um resultado byte-a-byte idêntico ou determinístico** dos índices compilados ou das pontuações (*scores*) de relevância. Reconhece-se que variações nas representações binárias de floats em embeddings, atualizações de modelos locais, ou diferenças lógicas em algoritmos de tokenização podem gerar pequenas divergências substantivas sem comprometer a integridade do conhecimento jurídico indexado.

---

## 11. Comportamento Diante de Concept Atualizado, Removido ou Depreciado

O lifecycle canônico é governado pelo **Lifecycle & Field Ownership v1.4 FROZEN**. O mecanismo de retrieval apenas sincroniza seus artefatos derivados com o estado do bundle.

* **repo_jur Project Requirement (Atualização)**: Se um concept for modificado, índices persistentes derivados devem atualizar ou reconstruir os registros associados ao `concept_id` conforme sua estratégia de sincronização.
* **repo_jur Project Requirement (Exclusão)**: Se um concept for removido fisicamente, artefatos derivados persistentes associados devem ser purgados ou invalidados para evitar resultados órfãos.
* **OKF v0.2 Normative Requirement**: `status` admite `draft`, `stable` e `deprecated`; ausência de `status` equivale semanticamente a `stable`.
* **repo_jur Project Requirement**: O mecanismo deve ler e expor `status` quando relevante. Este contrato **não prescreve** demote, boost, exclusão automática ou ranking específico para `deprecated` ou `draft`.
* **Decision Status — CLOSED: Document Lifecycle**: As regras de criação, atualização, reprocessamento, depreciação e remoção excepcional estão definidas no *Lifecycle & Field Ownership v1.4 FROZEN*.

---

## 12. Requisitos Mínimos para Integração com Agentes

* **repo_jur Project Requirement**: O mecanismo de recuperação deve expor suas capacidades através de uma interface estruturada e read-only de retrieval, a qual pode ser consumida por agentes cognitivos (por exemplo, por meio do protocolo Model Context Protocol (MCP) como exemplo futuro de integração) [79, 110, 320].
* **repo_jur Project Requirement**: A interface de busca deve fornecer ferramentas com suporte a controle de limites de tamanho (*limits*) e paginação, impedindo o retorno excessivo de texto bruto de modo a resguardar a estabilidade da janela de contexto [101, 133].
* **repo_jur Project Requirement**: O contrato de recuperação foca-se estritamente na interface de dados entre o bundle de conhecimento e o motor de indexação. As diretrizes gerais e as regras cognitivas de raciocínio interno do modelo de IA (como a proibição de alucinação ou regras de formatação de prosa do chat) permanecem isoladas nos arquivos de controle operacional (`AGENTS.md`) e de comportamento (`Skills`), não pertencendo a este contrato de dados.

---

## Diferenciação de Diretrizes do Contrato

### **Requirement** (Obrigatório por Segurança, Conformidade e Integridade Física)
* Toda a estrutura de dados de recuperação derivada (chunks, vetores, índices, caches) deve residir fora da pasta `/bundle/` do OKF e ser tratada como dados derivados e reconstruíveis [126, 135].
* O `concept_id` é a referência canônica posicional do concept e é determinado pelo caminho relativo sem a extensão `.md`; não é uma identidade persistente imutável.
* Qualquer trecho retornado deve carregar `concept_id` e `text_content`; deve preservar `source_refs` quando existirem; `page_refs` somente quando aplicável e explicitamente sustentado; para exatamente 1 PDF, `source_pdf` + `repo_jur_pdf_hash`; para 2+ PDFs, `repo_jur_pdf_hashes` e as referências de fonte correspondentes.
* O mecanismo de recuperação deve expor uma interface estruturada e estritamente read-only de retrieval para os agentes consumidores, operando sob a regra estrita de Zero-Write em relação à pasta do bundle [159, 187].
* **Search Execution Path — CLOSED:** o caminho inicial oficial é Lexical-First, Hybrid-Ready. O discovery usa índice lexical derivado em nível de concept; o resultado final deve ser materializado/validado contra o concept atual no bundle; filesystem read-only search é o fallback normativo.
* O `concept_id` posicional é a canonical join key do índice derivado. IDs internos de implementação podem existir, mas não constituem identidade do concept.
* Índices persistentes devem ser sincronizáveis/reconstruíveis e não podem depender exclusivamente de `mtime`, Git hooks ou `juridico-cli` para correção.

### **Recommendation** (Recomendação de Design Técnico e Otimização)
* A Chunking Strategy CLOSED preserva limites estruturais e referências de página de forma auditável. Chunks podem cruzar páginas, desde que todas as páginas inequivocamente relacionadas sejam mantidas em `page_refs`.
* Recomenda-se a extração determinística de links Markdown direcionados do OKF para a montagem de um grafo relacional derivado, caso seja projetado [36, 42].
* Recomenda-se expor filtros estruturados baseados nas chaves de extensão que forem explicitamente declaradas como retrieval-relevant, otimizando as consultas [105, 149].
* SQLite FTS5 pode ser usado como implementação de referência para o índice lexical, mas não é requisito arquitetural.
* `ripgrep` pode ser usado como implementação de referência do filesystem fallback, mas não é requisito arquitetural.
* A interface pode expor um semantic candidate seam futuro, sem selecionar embedding model, vector DB, ANN/HNSW ou estratégia de chunks nesta baseline.

### **Decisões incorporadas até a atualização v2.7**
* **Document Lifecycle — CLOSED**: governado pelo `lifecycle-field-ownership-v1.4-FROZEN.md`.
* **PDF Source Cardinality — CLOSED**: exatamente 1 PDF usa `repo_jur_pdf_hash`; 2+ PDFs usam `repo_jur_pdf_hashes`.
* **Stable Concept Identity — CLOSED**: `concept_id` continua posicional e rename/move altera a join key.
* **Verification History Schema — CLOSED**: somente `verified` participa da confiança ativa; histórico permanece auditoria.
* **Search Execution Path — CLOSED**: Lexical-First, Hybrid-Ready, com concept-level lexical index, canonical materialization e direct read-only filesystem fallback.
* **Chunking Strategy — CLOSED**: Structural Block-First, Page-Aware, Size-Profiled, com Chunking Profile versionado.
* **Reranking Pipeline — CLOSED**: governado por `decision-memo-reranking-pipeline-v1.0-FROZEN.md`; Optional, Conditional, Profile-Governed e Fail-Open, com relevance separada de trust.

### **Open Decisions**
Não permanece Open Decision arquitetural de retrieval entre as atualmente registradas.

---

## 13. Search Execution Path — CLOSED

Governado por `decision-memo-search-execution-path-v1.0-FROZEN.md`.

### 13.1 Caminho inicial

```text
query
  ↓
retrieval orchestrator
  ↓
concept-level lexical candidate index
  ↓
structured filters
  ↓
candidate concept_id
  ↓
canonical materialization from bundle
  ↓
Retrieval Contract validation
  ↓
consumer
```

### 13.2 Índice derivado

* Unidade inicial: **concept document**.
* Join key: `concept_id`.
* Localização: sempre fora de `/bundle/`.
* Persistência: permitida, desde que derivada e reconstruível.
* SQLite FTS5 é implementação possível, não requisito.

### 13.3 Sincronização

O índice deve suportar create, content update, rename/move e delete.

Rename/move remove/invalida o `concept_id` antigo e cria associação sob o novo caminho.

Persistência deve registrar fingerprint/versionamento suficiente para detectar staleness. `mtime` e Git hooks podem otimizar, mas não são a única garantia de correção.

### 13.4 Fallback

Na ausência, corrupção, incompatibilidade ou rebuild do índice, o runtime degrada para **Direct Read-Only Filesystem Search**.

`ripgrep` é implementação possível, não requisito.

### 13.5 Canonical materialization

O índice é apenas mecanismo de localização.

Antes de retornar `text_content` e proveniência ao consumidor, o runtime deve confirmar/materializar o concept atual no bundle, impedindo que conteúdo stale do índice substitua a fonte canônica.

### 13.6 Semantic-ready boundary

A arquitetura mantém seam futuro para semantic candidates. A Chunking Strategy já está CLOSED, porém esta baseline não ativa automaticamente semantic search e não seleciona:

* embedding model;
* vector DB;
* ANN/HNSW;
* fusion algorithm;
* RRF ou `k=60`.

### 13.7 Ranking boundary

Scores do mecanismo lexical são derivados e não canônicos.

`repo_jur_verification_history` nunca participa de trust/ranking ativo.

Nenhuma política automática de boost/demote/exclusão por `status` é criada por esta decisão.

---

## 14. Chunking Strategy — CLOSED

Governado por `decision-memo-chunking-strategy-v1.0-FROZEN.md`.

### 14.1 Fonte canônica

O chunker opera sobre o **concept canônico atual materializado do `bundle/`**.

A saída intermediária da Fase 1 não é source of truth para chunking de retrieval.

Frontmatter é parseado separadamente; `text_content` deriva exclusivamente do body Markdown canônico.

### 14.2 Modelo oficial

O modelo é **Structural Block-First, Page-Aware, Size-Profiled**.

Regras normativas:

- blocos estruturais Markdown são fronteiras preferenciais;
- chunks preservam spans literais contíguos;
- quebras físicas de página não forçam quebra de chunk;
- forced split ocorre apenas quando necessário;
- nenhuma reescrita, síntese ou rearranjo textual é permitido.

### 14.3 Chunking Profile

Soft limit, hard limit, unidade de medição e overlap pertencem a um **Chunking Profile versionado**.

Nenhum valor numérico específico é requisito arquitetural desta baseline.

Mudança de profile invalida/reconstrói os chunk sets afetados.

### 14.4 Page mapping

`page_refs` são calculados pela interseção entre o span textual do chunk e os intervalos físicos de página representados no concept.

Quando um span cruza páginas, todas as páginas inequivocamente relacionadas são preservadas.

Sem associação física inequívoca, `page_refs` é omitido.

Em multi-source/multi-PDF, nenhuma associação page→source é inventada.

### 14.5 Chunk identity

Não existe Stable Chunk ID canônico.

Cada chunk set pode possuir:

- `chunk_set_fingerprint` derivado;
- `chunk_ordinal` determinístico;
- body range/span derivado.

`concept_id` continua sendo a canonical join key.

Referências operacionais de chunk são derivadas e reconstruíveis.

### 14.6 Contexto estrutural derivado

Headings, table headers ou contexto equivalente não devem ser artificialmente duplicados dentro de `text_content`.

Quando útil, contexto estrutural pode ser exposto separadamente em metadados derivados como `section_path` ou `table_header_context`.

### 14.7 Rebuild

Chunk sets devem ser invalidados/reconstruídos quando houver mudança de:

- conteúdo canônico relevante;
- `concept_id`;
- Chunking Profile;
- chunker logical version.

Rename/move invalida a associação antiga e reconstrói sob o novo `concept_id`.

### 14.8 Relação com Search Execution Path

O índice lexical inicial permanece **concept-level**.

Fechar Chunking Strategy não obriga chunk-level lexical indexing e não ativa automaticamente semantic search.

Os chunks definidos aqui formam uma representação derivada disponível para futuras capacidades semânticas compatíveis.

### 14.9 Reranking boundary

Chunking Strategy não define:

- embedding model;
- vector DB;
- ANN/HNSW;
- fusion algorithm;
- RRF;
- score normalization;
- reranker.

**Reranking Pipeline permanece OPEN.**

---

## 15. Reranking Pipeline — CLOSED

Governado por `decision-memo-reranking-pipeline-v1.0-FROZEN.md`.

### 15.1 Modelo oficial

**Optional, Conditional, Profile-Governed, Fail-Open Reranking**.

Reranking é uma melhoria opcional de relevance em runtime e nunca uma dependência de disponibilidade do corpus.

### 15.2 Posição

```text
query
  ↓
candidate discovery
  ↓
structured filtering
  ↓
reranking decision seam
  ├─ bypass
  └─ optional reranker
          ↓
canonical materialization
          ↓
result assembly
```

### 15.3 Reranking Profile

O profile versionado governa habilitação, trigger policy, candidate limits, timeout, implementation e observability.

Nenhum model, provider, API, GPU, candidate limit, timeout, threshold ou peso específico é requisito FROZEN.

### 15.4 Fail-open

Falha, timeout ou indisponibilidade do reranker:

1. descarta ordenação parcial/inválida;
2. preserva a ordem anterior válida;
3. continua para canonical materialization;
4. registra telemetria operacional.

Não existe reranker heurístico de fallback obrigatório.

### 15.5 Relevance vs Trust

Reranking altera somente **relevance query↔candidate**.

Não são multiplicadores automáticos de relevance:

- `trust_tier`;
- `verified`;
- `status`;
- `repo_jur_verification_history`;
- temporal decay jurídico.

Trust e relevance permanecem dimensões distintas.

### 15.6 Scores e corpus

Scores são derivados, efêmeros e não canônicos.

Reranking não altera:

- `/bundle/`;
- frontmatter;
- `verified`;
- `status`;
- trust;
- lifecycle;
- identidade canônica.

### 15.7 Canonical materialization

Canonical materialization permanece obrigatória após bypass, sucesso ou fallback.

### 15.8 Observability

A execução deve distinguir pelo menos:

- `disabled`;
- `bypassed`;
- `applied`;
- `failed_fallback`.

Esses estados são operacionais, não canônicos.

### 15.9 Closure

Search Execution Path, Chunking Strategy e Reranking Pipeline estão CLOSED.

**Não permanece Open Decision arquitetural de retrieval entre as atualmente registradas.**

---

## Apêndice A: Exemplo Abstrato e Não Normativo de Payload de Comunicação

O exemplo a seguir ilustra de forma puramente conceitual e em formato JSON como o **Retrieval Contract** representa requisições, filtros de metadados declarados como *retrieval-relevant* e a entrega lógica do envelope de proveniência com suporte a múltiplas referências de página. Este exemplo não vincula o projeto a nenhuma tecnologia física, banco ou servidor específico.

### A.1 Exemplo de Requisição de Recuperação (Request)
```json
{
  "search_query": "excesso de poder por autoridade publica",
  "retrieval_filters": {
    "type": "Jurisprudencia",
    "status": "stable",
    "repo_jur_tribunal": "STF"
  },
  "limit": 1
}
```

### A.2 Exemplo de Resposta — Concept com Exatamente 1 PDF

```json
{
  "recovered_elements": [
    {
      "concept_id": "pasta_documentos/documento_slug_ficticio",
      "text_content": "Trecho recuperado. [[Pág. 12]] Continuação do trecho. [[Pág. 13]]",
      "source_refs": [
        {
          "id": "source_pdf",
          "resource": "<archived-source-resource>"
        }
      ],
      "page_refs": [12, 13],
      "source_pdf": "<archived-source-resource>",
      "repo_jur_pdf_hash": "<sha256-64-hex>"
    }
  ]
}
```

### A.3 Exemplo de Resposta — Concept com Múltiplos PDFs

```json
{
  "recovered_elements": [
    {
      "concept_id": "temas/conceito_multi_fonte",
      "text_content": "Trecho sintético atribuído às fontes explicitamente registradas no concept.",
      "source_refs": [
        {
          "id": "source_pdf_a",
          "resource": "<source-a-resource>"
        },
        {
          "id": "source_pdf_b",
          "resource": "<source-b-resource>"
        }
      ],
      "repo_jur_pdf_hashes": {
        "source_pdf_a": "<sha256-64-hex>",
        "source_pdf_b": "<sha256-64-hex>"
      }
    }
  ]
}
```

> O exemplo multi-PDF não inventa `page_refs`. Elas somente devem ser retornadas quando houver associação física de página explicitamente sustentada pelo concept.
