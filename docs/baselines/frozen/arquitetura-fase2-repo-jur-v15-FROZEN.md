# DESENHO ARQUITETURAL DA FASE 2: ESTRUTURAÇÃO OKF v0.2 + CONSUMO HERMES
**Versão:** 15.0 (Baseline consolidada — correção controlada)
**Data:** 15 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `external-source-ingestion-contract-v1.6-FROZEN.md`, `legal-okf-profile-v1.3-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `retrieval-contract-v2.8-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md`, `decision-memo-verification-history-schema-v1.0-FROZEN.md`, `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md` e `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`, `decision-memo-search-execution-path-v1.0-FROZEN.md`, `decision-memo-chunking-strategy-v1.0-FROZEN.md`, `decision-memo-reranking-pipeline-v1.0-FROZEN.md`, `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md`, `decision-memo-semantic-review-enrichment-layer-v1.1-FROZEN.md`, `decision-memo-post-ocr-critical-data-validation-seam-v1.1-FROZEN.md`, `phase1-operational-spec-v1.1-FROZEN.md`, `decision-memo-physical-layout-logical-capability-mapping-v1.0-FROZEN.md`, `decision-memo-retrieval-bounded-context-scope-v1.0-FROZEN.md`.


---

## 0. Atualização Controlada v15

Esta versão sincroniza o mapa arquitetural com as decisões FROZEN posteriores à v4, sem reabrir escolhas já encerradas.

**Decisões incorporadas:**
- **PDF Storage Location:** evidências PDF originais são preservadas em Object Storage externo.
- **PDF Source Cardinality:** 1 PDF usa `repo_jur_pdf_hash`; 2+ PDFs usam `repo_jur_pdf_hashes`.
- **Document Lifecycle / Field Ownership:** regeneração usa merge controlado e preserva propriedade humana/compartilhada.
- **Bundle structure:** inclusão formal de `precedentes/` permanece vigente.
- **Duplicate Act Handling:** CLOSED; consolidação automática só ocorre quando identidade lógica e equivalência material forem seguras; ambiguidade exige revisão humana.
- **Stable Concept Identity:** CLOSED; identidade posicional pura, sem Stable ID adicional.
- **Verification History Schema:** CLOSED; histórico canônico em `repo_jur_verification_history`, separado de `verified` ativo.
- **Ingress Transport Protocol:** CLOSED; ITP/1.0 usa envelope ZIP single-evidence, `manifest.json`, `handoff_id` e filesystem ingress inbox local.
- **Phase 1 Quality Gate:** CLOSED; gate determinístico PASS/PASS WITH WARNINGS/FAIL; somente resultados conformantes seguem ao Produtor.
- **Search Execution Path:** CLOSED; Lexical-First, Hybrid-Ready com índice lexical concept-level, canonical materialization e direct read-only filesystem fallback.
- **Chunking Strategy:** CLOSED; Structural Block-First, Page-Aware, Size-Profiled, com Chunking Profile versionado.
- **Reranking Pipeline:** CLOSED; Optional, Conditional, Profile-Governed e Fail-Open, com relevance separada de trust.
- **Shared Conversion Core & Bounded Contexts:** CLOSED; Phase 1 compartilhada, split após Quality Gate.
- **Semantic Review / Enrichment:** CLOSED; camada pré-Producer sem autoridade de publicação.
- **Post-OCR Critical-Data Validation Seam:** CLOSED; detecção/sinalização sem autocorreção.
- **Physical Layout & Logical Capability Mapping:** CLOSED; paths de documentação são alvos lógicos, não migração física obrigatória; `src/pipeline_juridico/` deve ser reutilizado quando já satisfaz a capacidade.
- **Semantic Review / Enrichment v1.1:** CLOSED; Phase 1 é imutável, patches estruturados e rastreabilidade before/after/reason/confidence.
- **Critical-Data Validation v1.1:** CLOSED; regras de identificadores exigem fonte técnica/normativa confiável e versionada.
- **Retrieval Bounded-Context Scope:** CLOSED; Retrieval Contract atual atende somente Legal Knowledge; Judicial Process Retrieval está fora de escopo.


As Open Decisions arquiteturais atualmente registradas estão encerradas; a Seção 10 passa a registrar a transição para planejamento de implementação.

---

## 1. Arquitetura de Alto Nível

A arquitetura passa a distinguir explicitamente o **Shared Conversion Core** dos dois bounded contexts downstream.

```text
[ juridico-cli / coletores externos ]
                │
                ▼
        [ Handoff + Preflight ]
                │
                ├────────► [ Object Storage externo ]
                │
                ▼
       [ SHARED CONVERSION CORE ]
                │
                ▼
[ Markdown literal + JSON técnico ]
                │
                ▼
[ Post-OCR Critical-Data Validation Seam ]
                │
                ▼
      [ Phase 1 Quality Gate ]
      PASS / PASS WITH WARNINGS
                │
                ▼
       [ Domain Boundary / Router ]
          ┌─────┴───────────┐
          ▼                 ▼
[ Legal Knowledge ]   [ Judicial Process ]
      Pipeline              Pipeline
          │                 │
          ▼                 ▼
[ Semantic Review ]   [ Semantic Review ]
[ / Enrichment ]      [ / Enrichment ]
          │                 │
          ▼                 ▼
 [ Legal Producer ]    [ Process Producer ]
          │                 │
          ▼                 ▼
 repo_jur/bundle/      Process-domain storage
          │
          ▼
 [ Retrieval Zero-Write ]
          │
          ▼
      [ Hermes ]
```

### 1.1 Shared Conversion Core

O Shared Conversion Core executa:

- recepção do evidence reference;
- conversão PDF → Markdown literal;
- OCR fallback quando necessário;
- page marker preservation;
- Technical JSON;
- post-OCR critical-data validation seam;
- Quality Gate.

Ele não conhece schemas de legislação, jurisprudência ou peças processuais.

### 1.2 Legal Knowledge Pipeline

Responsável por:

- legislação;
- jurisprudência;
- temas;
- precedentes.

É o único bounded context autorizado a usar o `repo_jur/bundle/` atual como canonical storage.

Fluxo:

```text
Phase 1 conformante
  ↓
Legal Semantic Review / Enrichment
  ↓
Legal Producer
  ↓
repo_jur/bundle/
```

### 1.3 Judicial Process Pipeline

Responsável por documentos processuais.

Fluxo:

```text
Phase 1 conformante
  ↓
Process Semantic Review / Enrichment
  ↓
Process Producer
  ↓
process-domain storage
```

Esse domínio não publica no Legal Knowledge bundle.

### 1.4 Semantic Review / Enrichment

É obrigatoriamente pós-Quality-Gate, bounded-context-specific e pré-Producer.

Pode corrigir:

- estrutura;
- classificação;
- enriquecimento;
- associação de campos.

Não possui liberdade para reescrever conteúdo jurídico.

Regras obrigatórias:

- o Markdown original da Phase 1 nunca é sobrescrito;
- sem resumo, paráfrase, tradução, invenção ou preenchimento inferido;
- em correção meramente estrutural, preservar todas as palavras do original;
- preferir patches estruturados;
- registrar `before`, `after`, `reason`, `confidence`;
- manter page/evidence traceability quando sustentada;
- ambiguidade → `REVIEW_REQUIRED`;
- Semantic Review nunca publica.

Problemas como fronteira `Papel/Nome` pertencem a esta camada, não ao conversor determinístico.

YAML e enrichment permanecem separados por bounded context.

### 1.5 Converter Implementation Boundary

A arquitetura permanece engine-neutral.

O conversor concreto já implementado deve ser reutilizado atrás de `ConversionEngine`.

A implementação atual pode usar MarkItDown/markitdown-ocr + Gemini por cliente compatível com OpenAI, sem congelar o provider.

### 1.6 Critical-Data Validation

A seam pós-OCR detecta/sinaliza inconsistências em dados críticos e nunca autocorrige conteúdo OCR.

Regras de formato, comprimento, check digit ou estrutura de identificadores somente podem ser implementadas quando sustentadas por especificação técnica/normativa confiável e versionada.

É proibido generalizar regra universal a partir de um único documento observado, especialmente para selos digitais e identificadores registrais.

Comparação determinística de valores redundantes permanece futura capacidade separada.


---

## 2. Fronteiras Físicas e Estrutura de Diretórios

Para preservar a pureza de dados do bundle OKF e garantir o correto funcionamento do ecossistema cognitivo do Hermes, estabelecemos uma divisão rígida entre os arquivos pertencentes ao repositório Git do projeto (`repo_jur/`) e os arquivos pertencentes ao diretório inicial global de runtime do Hermes (`HERMES_HOME/`).

### 2.1 Repositório Git do Projeto (`repo_jur/`)

A arquitetura congela **fronteiras de responsabilidade e autoridade**, não nomes obrigatórios de pacotes Python.

Os nomes `pipeline/`, `producer/`, `semantic_review/`, `shared_conversion/` e equivalentes usados em diagramas são **logical capability targets**.

Antes de qualquer alteração física deve existir um Repository Implementation Map.

Fato físico atualmente confirmado:

```text
src/pipeline_juridico/
```

contém o conversor estabilizado e deve ser preferido para `REUSE → ADAPT IN PLACE → TEST` quando satisfizer a capacidade lógica.

É proibido:

- criar uma árvore paralela apenas para coincidir com o desenho arquitetural;
- mover `src/pipeline_juridico/` somente por nomenclatura;
- duplicar módulos;
- tratar diagramas de pacotes como plano automático de migração.

Relocação física exige justificativa explícita e mudança revisada.

O requisito físico rígido permanece:

```text
repo_jur/bundle/
```

como canonical storage exclusivo de Legal Knowledge, livre de código, caches, estado operacional e documentos processuais.

### 2.1A Bounded Context Storage Boundary

`repo_jur/bundle/` permanece exclusivamente **Legal Knowledge**.

Artefatos do **Judicial Process Pipeline** não podem ser colocados em:

- `bundle/legislacao/`;
- `bundle/jurisprudencia/`;
- `bundle/temas/`;
- `bundle/precedentes/`;
- qualquer novo subdiretório processual dentro do bundle atual.

O armazenamento processual será domain-specific e governado separadamente.

### 2.2 Diretório de Runtime do Hermes (`HERMES_HOME/`)
Arquivos de configuração de software, bancos de dados de sessão, memórias persistentes e caches dinâmicos pertencem estritamente ao diretório global do Hermes (`HERMES_HOME/`, que por padrão mapeia para `~/.hermes/` no Linux/macOS/WSL2 ou `%LOCALAPPDATA%\hermes` no Windows nativo) [2, 3]. Eles não devem constar na árvore normal do repositório do projeto, resguardando a portabilidade e independência da base canônica, salvo se configurado explicitamente por meio de um perfil Hermes dedicado (`hermes profile create`) [114, 134].

```
HERMES_HOME/ (Geralmente ~/.hermes/ ou %LOCALAPPDATA%/hermes) [2, 3]
├── config.yaml                        # Arquivo de configurações globais, modelos e external_dirs [91]
├── MEMORY.md                          # Memória pessoal do agente (limite físico de 2.200 caracteres) [113]
├── USER.md                            # Perfil persistente do usuário (limite físico de 1.375 caracteres) [113]
├── state.db                           # Histórico de sessões, estado de execução e banco relacional do agente [111]
└── skills/                            # Diretório nativo de Skills (bundled e hub-installed) [133]
```

---

## 3. O Bundle OKF v0.2

O diretório `/bundle/` do `repo_jur/` reúne o **corpus jurídico canônico consumível** [30]. Ele funciona de maneira estática e autônoma, sendo projetado para ser empacotado, transportado ou clonado sem depender de nenhum runtime ativo [21, 30].

### Conteúdo Permitido e Regras Estruturais:
1.  **Concept Documents**: Arquivos Markdown (`.md`) individuais que contêm um bloco de frontmatter YAML válido delimitado por `---` e iniciado com a chave `type` preenchida [37, 61]. No corpo, usam-se títulos convencionais (como `# Schema` ou `# Examples`) e estrutura baseada em tabelas, títulos e listas [39, 40].
2.  **Arquivos Reservados (`index.md` e `log.md`)**:
    *   `index.md`: Arquivos opcionais sem frontmatter (exceto `okf_version: "0.2"` na raiz) estruturados em listas Markdown simples para descrever e catalogar o conteúdo de seu diretório, promovendo a navegação progressiva (*progressive disclosure*) de tokens [52, 63].
    *   `log.md`: Histórico opcional de modificações no formato de lista cronológica descendente (YYYY-MM-DD) [53].
3.  **Links entre Conceitos**: O grafo de relações cruzadas é modelado por meio de markdown links normais absolutos (relativos ao bundle, iniciando por `/`) ou relativos, sem tipagem explícita [21, 48]. Os links podem apontar para conceitos inexistentes ou não escritos sem invalidar a conformidade [49, 62].

### Regras de Conteúdo e Exclusão do Bundle:
*   **Arquivos Markdown (`.md`) Não Reservados (Sujeitos à Norma OKF)**: Qualquer arquivo `.md` incluído sob a árvore de diretórios do bundle que fuja dos nomes reservados (`index.md` e `log.md`) é interpretado semanticamente como um *concept document* segundo as regras normativas do OKF v0.2 [35, 36, 61]. Consequentemente, arquivos Markdown operacionais ou de controle (como `AGENTS.md` e `SKILL.md`) estão sujeitos a esta regra normativa e **devem** ser mantidos fora da árvore do bundle para evitar a criação de conceitos espúrios [36, 61].
*   **Arquivos Não-Markdown (Exclusão por Política do Projeto `repo_jur`)**: O isolamento e a proibição de colocar arquivos como scripts de pipelines, códigos-fonte, bancos de dados ativos, índices SQLite/FTS5, bancos de dados de embeddings vetoriais (como ChromaDB), arquivos `.json`/`.yaml` de configuração, caches ou credenciais dentro de `/bundle/` **não decorre de uma proibição ou restrição normativa do OKF v0.2** (que é neutro e agnóstico em relação a arquivos não-Markdown [30]), mas sim de uma **política arquitetural estrita do projeto `repo_jur`**. Esta política é estabelecida para manter uma barreira física e funcional perfeitamente limpa entre o corpus de conhecimento estático canônico e os mecanismos e runtimes de execução [21, 31].

---

## 4. O Legal Producer OKF

O **Legal Producer OKF** é a única camada autorizada a transformar artefatos do bounded context Legal Knowledge, já submetidos a Semantic Review / Enrichment, em concept documents canônicos sob `repo_jur/bundle/`. O Judicial Process Pipeline utiliza Producer e armazenamento próprios.

### Fluxo de Processamento do Produtor

```text
Markdown + JSON técnico + proveniência aceita
                    │
                    ▼
[ 1. Carregar concept existente, se houver ]
                    │
                    ▼
[ 2. Resolver identidade posicional e proveniência ]
                    │
                    ▼
[ 3. Detectar mudanças técnicas e materiais ]
                    │
                    ▼
[ 4. Recalcular Producer-Owned ]
                    │
                    ▼
[ 5. Mesclar Shared / preservar Human-Owned ]
                    │
                    ▼
[ 6. Aplicar cardinalidade PDF ]
                    │
                    ▼
[ 7. Aplicar verified + verification history + body ownership ]
                    │
                    ▼
[ 8. Validar OKF + repo_jur ]
                    │
                    ▼
[ 9. Publicação atômica + diff Git revisável ]
```

### Regras determinísticas obrigatórias

* **`type`:** obrigatório e preenchido conforme o perfil jurídico aplicável.
* **`sources`:** obrigatório quando o concept deriva de fontes identificáveis.
* **Exatamente 1 PDF:** usar `repo_jur_pdf_hash`.
* **2 ou mais PDFs:** usar `repo_jur_pdf_hashes`, mapeando `sources[].id` → SHA-256.
* **Exclusividade:** `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` nunca coexistem.
* **Hash:** SHA-256 identifica os bytes da evidência PDF; não é identidade do concept nem prova autenticidade jurídica.
* **`generated.by`:** usar `repo_jur_producer/<version>`.
* **`generated.at`:** registrar a última mudança significativa do conteúdo atual; não atualizar apenas porque o pipeline foi executado.
* **Body ownership:** concepts literais derivados de PDF preservam o corpo canônico da Fase 1; concepts abstratos/sintéticos seguem ownership humano/compartilhado conforme a baseline de lifecycle.
* **Metadados técnicos:** método de conversão, OCR, warnings, confiança e informações de execução permanecem no JSON técnico, não no frontmatter ou corpo canônico.
* **Regeneração:** o Produtor não sobrescreve silenciosamente valores Human-Owned nem curadoria humana válida em campos Shared Ownership.
* **`verified`:** somente eventos reais de verificação; geração pelo Produtor não constitui auto-verificação.

### Uso auxiliar de IA

IA pode auxiliar na sugestão de metadados classificados como Producer-Owned ou Shared Ownership quando permitido pelo perfil, mas não possui autoridade para reescrever silenciosamente corpo literal derivado de PDF, inventar proveniência, criar `verified` ou resolver Open Decisions.

---

## 5. Consumo pelo Hermes Agent

O Hermes Agent atua como o motor lógico principal que consome e raciocina com base no conhecimento estruturado [14]. Para garantir o isolamento físico de dados, mapeamos a sua integração física com o projeto `repo_jur`:

### 1. Instruções Permanentes (`AGENTS.md`)
*   **Interface**: Context Files de Projeto [68].
*   **Integração Física**: O arquivo `AGENTS.md` do projeto deve ser colocado **na raiz de `repo_jur`**, completamente fora do subdiretório `bundle/` [68, 69]. O Hermes descobre e carrega este arquivo de forma automática ao inicializar sessões no repositório, pois ele varre a cadeia de diretórios do git-root até o diretório ativo atual (git-root directory chain lookup) [69, 70]. Arquivos Markdown operacionais colocados em diretórios de execução locais fora da cadeia de caminhos do Git **não** são descobertos automaticamente por este mecanismo no git-root e, por estarem no formato `.md`, seriam tratados incorretamente como documentos de conceito caso fossem colocados sob a árvore do bundle [36, 61, 68].

### 2. Procedimentos de Consulta (Skills)
*   **Interface**: Skills baseadas no padrão `agentskills.io` [133].
*   **Integração Física**: As Skills nativas do Hermes residem exclusivamente em `HERMES_HOME/skills/` [133]. Caso o comitê decida manter Skills personalizadas e versionadas diretamente no repositório do projeto (como na pasta `repo_jur/skills/` na raiz do projeto, fora do subdiretório `bundle/`), elas **somente serão carregadas e utilizadas se forem explicitamente configuradas no campo `skills.external_dirs`** no arquivo `config.yaml` de `HERMES_HOME` [134, 145].

### 3. Acesso à Base Jurídica (Retrieval Read-Only)
*   **Interface:** mecanismo de retrieval read-only compatível com o Retrieval Contract v2.7.
*   **Integração Física:** o caminho inicial é Lexical-First, Hybrid-Ready: índice lexical derivado em nível de concept, canonical materialization e filesystem read-only fallback. A implementação concreta do índice continua substituível.

### 4. Recuperação Seletiva de Conhecimento (Implementação Aberta)
*   **Interface:** definida pela implementação de retrieval.
*   **Integração Física:** qualquer índice, chunk, embedding, cache ou banco derivado deve permanecer fora de `repo_jur/bundle/` e ser reconstruível/sincronizável conforme o Retrieval Contract v2.7. Semantic candidates permanecem seam futuro; MCP é uma possibilidade, não um requisito.

### 5. Memória Persistente (Persistent Memory)
*   **Interface**: `MEMORY.md` e `USER.md` [113].
*   **Integração Física**: Os arquivos de memória do Hermes (`MEMORY.md` e `USER.md`), seu arquivo de configurações gerais (`config.yaml`), as sessões de conversas e os bancos de dados de estado (como `state.db`) **pertencem estritamente a `HERMES_HOME`**, permanecendo fora da árvore normal do repositório Git do projeto `repo_jur` [3, 91, 111, 113]. Essa divisão garante a independência total da base canônica, exceto se configurado explicitamente um perfil do Hermes dedicado para o projeto [114, 134].
*   **Restrições de Escopo**: `USER.md` (limite de 1.375 caracteres) guarda apenas o perfil e preferências estáveis do advogado [113, 119]. `MEMORY.md` (limite de 2.200 caracteres) registra apenas convenções e quirks de ferramentas duráveis de ambiente [113, 118]. É proibido registrar nestas memórias prazos processuais, andamentos, diários de análises de peças, conteúdos de leis ou dados dinâmicos de processos ativos, impedindo o estouro de buffers e mantendo o prompt do sistema previsível [115, 120, 121].

---

## 6. Fluxo de Consulta de Exemplo

O fluxo de consulta não depende de uma tecnologia de retrieval específica:

```text
[ Advogado ]
     │
     ▼
[ juridico-cli ]
     │
     ▼
[ Hermes Agent ]
     │
     ▼
[ Retrieval read-only ]
     │
     ▼
[ repo_jur/bundle/ ]
     │
     ▼
[ concept_id + texto + proveniência aplicável ]
```

1. O advogado formula a consulta.
2. O Hermes solicita evidências por uma interface compatível com o Retrieval Contract v2.8.
3. O mecanismo recupera `concept_id` + `text_content` e preserva `source_refs` quando existentes.
4. Para concepts com evidência PDF, preserva `page_refs` quando houver associação física explícita; usa `repo_jur_pdf_hash` para exatamente 1 PDF ou `repo_jur_pdf_hashes` para 2+ PDFs.
5. O mecanismo não inventa associação trecho→fonte ou página→fonte que não esteja sustentada pelo concept.
6. Hermes realiza o raciocínio grounded sobre as evidências recuperadas.

---

## 7. Classificação de Dados

| Categoria | Descrição | Git (`repo_jur/`) | Localização |
| :--- | :--- | :--- | :--- |
| **1. Evidência / Fonte Original** | PDFs originais aceitos na ingestão; somente leitura lógico. | Não | Object Storage externo, com referência estável/resolvível e SHA-256 |
| **2. Artefatos da Fase 1** | Markdown literal e JSON técnico de conversão. Não são corpus canônico. | Conforme política operacional; nunca dentro do bundle | Área de pipeline/staging/output fora de `bundle/` |
| **3. Corpus Jurídico Canônico** | Concept documents OKF e reserved files permitidos. | Sim | `repo_jur/bundle/` |
| **4. Configuração Versionada do Projeto** | Código, `AGENTS.md`, configurações e Skills opcionais do projeto. | Sim | Fora de `bundle/` |
| **5. Runtime Privado do Hermes** | Configurações, memórias, sessões e estado de runtime. | Não | `HERMES_HOME/` |
| **6. Dados Derivados / Reconstruíveis de Retrieval** | Chunks, índices, embeddings, caches, grafos ou estruturas equivalentes, se existirem. | Não; se estiverem no worktree, devem ser ignorados pelo Git | Sempre fora de `bundle/`; localização definida pela implementação |

---

## 8. Decisões Arquiteturais: Estado Atual

### 8.1 PDF Storage Location — RESOLVED

A evidência PDF original aceita deve ser preservada em **Object Storage externo**, não no Git e não em `repo_jur/bundle/`.

* `sources[].resource` deve identificar a evidência efetivamente utilizada por referência estável e resolvível.
* O SHA-256 é calculado sobre os bytes exatos do PDF aceito.
* Controles de versionamento, retenção e acesso pertencem à infraestrutura de preservação.
* A URL/locator de coleta não é automaticamente igual a `sources[].resource`.

### 8.2 Document Lifecycle / Field Ownership — CLOSED

O Produtor segue `lifecycle-field-ownership-v1.4-FROZEN.md`.

* `status` é Human-Owned no perfil atual.
* Regeneração carrega o concept existente antes do merge.
* Producer-Owned é recalculado; Human-Owned é preservado; Shared Ownership não é sobrescrito silenciosamente.
* `generated.at` só muda quando há alteração significativa do conteúdo atual.
* Mudança de hash/cardinalidade não invalida `verified` automaticamente; aplica-se análise de materialidade.

### 8.3 PDF Source Cardinality — CLOSED

* 1 PDF → `repo_jur_pdf_hash`.
* 2+ PDFs → `repo_jur_pdf_hashes`.
* Em multi-PDF, cada fonte PDF possui `sources[].id` correspondente no mapping.
* A mesma evidência/hash pode sustentar vários concepts.

### 8.4 Duplicate Act Handling — CLOSED

Governado por `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`.

* SHA-256, URL, filename, `concept_id` e número de processo isolados não identificam o ato jurídico.
* Metadados estruturados são sinais de identidade, não primary key universal.
* PDFs fisicamente distintos só são consolidados automaticamente no mesmo concept quando equivalência lógica/material for segura.
* Mudança material ou ambígua exige revisão humana.
* `status` não é alterado automaticamente e nenhum sufixo `_v2` é criado para resolver versionamento.

### 8.5 Retrieval — CLOSED BASELINE SET — LEGAL KNOWLEDGE ONLY


**Escopo de bounded context:** esta baseline de Retrieval atende exclusivamente **Legal Knowledge** e `repo_jur/bundle/`.

`Judicial Process Retrieval` está fora do escopo e exige contrato/decisão própria futura.

É proibido criar índice compartilhado que misture base jurídica e peças processuais.

Governado por `decision-memo-search-execution-path-v1.0-FROZEN.md`, `decision-memo-chunking-strategy-v1.0-FROZEN.md`, `decision-memo-reranking-pipeline-v1.0-FROZEN.md` e `retrieval-contract-v2.8-FROZEN.md`.

#### Search Execution Path — CLOSED

* Lexical-First, Hybrid-Ready.
* Índice lexical inicial em nível de concept.
* `concept_id` como canonical join key.
* Canonical materialization obrigatória.
* Direct Read-Only Filesystem Search como fallback.

#### Chunking Strategy — CLOSED

* Structural Block-First, Page-Aware, Size-Profiled.
* Chunks derivados do concept canônico atual.
* `text_content` literal e contíguo.
* `page_refs` por interval mapping.
* Chunking Profile versionado.
* Nenhuma Stable Chunk ID canônica.

#### Reranking Pipeline — CLOSED

* Optional, Conditional, Profile-Governed, Fail-Open.
* Nenhum model/provider/API/GPU obrigatório.
* Candidate limits, timeout e trigger policy são parâmetros versionados.
* Falha preserva a ordem anterior válida.
* Relevance permanece separada de trust.
* Canonical materialization permanece obrigatória.

#### Retrieval Open Decisions

Não permanece Open Decision arquitetural de retrieval entre as atualmente registradas.

Nenhuma decisão de retrieval autoriza escrita em `bundle/`.

### 8.6 Stable Concept Identity — CLOSED

Governada por `decision-memo-stable-concept-identity-v1.0-FROZEN.md`.

* O `concept_id` posicional permanece a referência canônica do concept no bundle.
* Rename/move altera o `concept_id`.
* Nenhum Stable ID adicional é persistido no frontmatter.
* Git preserva histórico/versionamento, mas não constitui identidade persistente de domínio.
* Stable IDs não são proibidos pelo OKF; simplesmente não são necessários para os requisitos atuais do `repo_jur`.

### 8.7 Verification History Schema — CLOSED

Governada por `decision-memo-verification-history-schema-v1.0-FROZEN.md`.

* `verified` contém somente eventos ativos de verificação aplicáveis ao conteúdo atual.
* Eventos reais que deixem de ser aplicáveis podem ser arquivados em `repo_jur_verification_history`.
* Histórico nunca participa do trust tier.
* Hash, cardinalidade e path não invalidam `verified` automaticamente.
* `invalidated_by` identifica o Actor da decisão de invalidação, não necessariamente o software escritor.
* Não existe `evidence_pdf_hash` histórico obrigatório nesta baseline.

### 8.8 Ingress Transport Protocol — CLOSED

Governado por `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`.

* **Envelope:** ITP/1.0 ZIP versionado.
* **Conteúdo:** exatamente `manifest.json` + `evidence.pdf`.
* **Unidade:** uma evidência PDF por envelope.
* **Canal inicial:** filesystem ingress inbox local, configurável e fora de `/bundle/`.
* **Completion protocol:** arquivo temporário + close + rename atômico no mesmo filesystem.
* **Idempotência de transporte:** `handoff_id`; nunca Stable Concept ID.
* **Hash:** SHA-256 oficial recalculado pelo receptor.
* **Preflight:** valida transporte/evidência física, mas não decide identidade jurídica por hash.
* **Storage:** evidência aceita é preservada em Object Storage antes da Fase 1.
* **Neutralidade:** Fase 1 permanece engine-neutral.
* **HTTP remoto:** possível evolução futura, fora desta baseline.

### 8.9 Phase 1 Quality Gate — CLOSED

Governado por `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`.

* **Resultados normativos:** PASS, PASS WITH WARNINGS e FAIL.
* **Autoridade:** somente regras determinísticas decidem o resultado.
* **OCR:** uso bem-sucedido pode resultar em PASS; OCR não é warning por definição.
* **Página vazia:** preserva seu marcador e não é warning obrigatório.
* **Partial:** `allow_partial`, se existir, continua FAIL e produz somente artefato diagnóstico fora do caminho do Produtor.
* **Score:** qualquer score/confidence é diagnóstico e não possui autoridade de aceitação.
* **JSON técnico:** engine-neutral, sem secrets; telemetria pode variar entre execuções.
* **Downstream:** somente PASS/PASS WITH WARNINGS podem seguir da Fase 1 para o Domain Router; depois disso cada bounded context aplica Semantic Review / Enrichment antes de seu Producer.

### 8.10 Outras Open Decisions

Não permanece Open Decision de ingestão/produção canônica nesta arquitetura.

Não permanece Open Decision arquitetural de retrieval entre as atualmente registradas.

Novas Open Decisions somente devem ser abertas diante de requisito arquitetural concreto ainda não coberto pelas baselines FROZEN.

### 8.11 Governança de Escrita

* Sistemas externos e mecanismos de retrieval operam em Zero-Write sobre `repo_jur/bundle/`.
* Somente o Legal Knowledge Pipeline + Legal Producer podem publicar concepts em `repo_jur/bundle/`; o Judicial Process Pipeline publica somente em seu armazenamento próprio.
* A governança de commits, branches, revisão humana ou proteções de repositório pode reforçar o controle, mas não altera a fronteira lógica acima.

---

## 9. Diagrama Arquitetural de Componentes e Fronteiras

```text
================================================================================
                     REPOSITÓRIO / DOMÍNIOS CONTROLADOS
================================================================================

External Collectors / juridico-cli
              |
              v
          ITP / Ingress
              |
              v
           Preflight
              |
              v
       Official SHA-256
              |
              v
  Evidence Preservation / Object Storage
              |
              v
     SHARED CONVERSION CORE
              |
              v
  Markdown literal + Technical JSON
              |
              v
Critical-Data Validation Seam
              |
              v
       Quality Gate
              |
      PASS / PASS WITH WARNINGS
              |
              v
        Domain Router
        /          \
       v            v
LEGAL KNOWLEDGE   JUDICIAL PROCESS
     |                 |
     v                 v
Semantic Review    Semantic Review
     |                 |
     v                 v
Legal Producer     Process Producer
     |                 |
     v                 v
repo_jur/bundle/   process-domain storage
     |
     v
Retrieval Zero-Write
     |
     v
Hermes
```

Dados derivados, runtime, caches, índices, logs técnicos e artefatos processuais:
**NUNCA** são gravados em `repo_jur/bundle/`, salvo os concept documents do bounded context Legal Knowledge publicados pelo Legal Producer.

---

## 10. Próxima Etapa

As Open Decisions arquiteturais atualmente registradas para ingestão, produção canônica e retrieval estão encerradas.

O próximo trabalho passa para **implementation planning / technical specification**, sem reabrir decisões FROZEN silenciosamente.

A próxima baseline operacional deve transformar as decisões arquiteturais em:

- componentes implementáveis;
- interfaces;
- schemas técnicos derivados;
- comandos;
- testes de conformidade;
- critérios de aceite;
- ordem de implementação.

---

## 11. Invariantes Consolidados da Arquitetura v13

1. O corpus jurídico canônico é exclusivamente `repo_jur/bundle/`.
2. PDFs originais ficam em Object Storage externo.
3. Fase 1 produz Markdown literal + JSON técnico fora do bundle.
4. O Produtor OKF é o único publicador canônico.
5. 1 PDF usa hash singular; 2+ PDFs usam mapping plural.
6. SHA-256 identifica bytes, não concept nem autenticidade jurídica.
7. `generated` não equivale a `verified`.
8. Ownership e lifecycle seguem a baseline v1.4.
9. Retrieval é Zero-Write e technology-neutral.
10. Dados derivados/reconstruíveis permanecem fora do bundle.
11. `concept_id` é derivado do caminho relativo e é posicional.
12. A árvore canônica contém `legislacao/`, `jurisprudencia/`, `temas/` e `precedentes/`.
13. Duplicate Act Handling é conservador: fusão automática só ocorre com equivalência lógica/material segura; ambiguidade exige revisão humana.
14. `status` permanece Human-Owned e não há versionamento automático por `_v2`.
15. `repo_jur_verification_history` registra somente histórico de verificação/invalidação e nunca confiança ativa.
16. Hash/cardinalidade/path não invalidam `verified` automaticamente; materialidade é avaliada contra o objeto efetivamente verificado.
17. ITP/1.0 transporta uma evidência PDF por envelope ZIP; cardinalidade multi-PDF do concept é resolvida posteriormente.
18. `handoff_id` identifica transporte/retry e nunca concept, ato jurídico ou evidência por conteúdo.
19. ZIP não substitui completion protocol; inbox local usa arquivo temporário + rename no mesmo filesystem.
20. O SHA-256 oficial é recalculado pelo receptor e hash conhecido não resolve identidade jurídica.
21. Evidência aceita é preservada em Object Storage antes da Fase 1.
22. Phase 1 Quality Gate possui exatamente PASS, PASS WITH WARNINGS e FAIL.
23. Somente PASS/PASS WITH WARNINGS podem seguir ao Produtor OKF.
24. OCR bem-sucedido não é falha nem warning por definição.
25. `allow_partial` nunca converte FAIL em saída elegível ao Produtor.
26. Score/confidence de qualidade é apenas diagnóstico; não decide aceitação.
27. Search Execution Path inicial é Lexical-First, Hybrid-Ready.
28. O índice lexical inicial permanece em nível de concept; o fechamento de Chunking Strategy não obriga sua substituição por chunk-level lexical indexing.
29. `concept_id` permanece a canonical join key dos artefatos de retrieval.
30. O resultado final é materializado/validado contra o bundle atual; índice stale não substitui a fonte canônica.
31. Direct Read-Only Filesystem Search é o fallback normativo; `ripgrep` não é requisito.
32. Embedding model, vector DB, HNSW, RRF e `k=60` não são selecionados pelo Search Execution Path.
33. Chunking Strategy está CLOSED.
34. Chunking deriva exclusivamente do concept canônico atual materializado do bundle.
35. `text_content` de chunk permanece literal e contíguo.
36. Soft/hard limits e overlap pertencem a Chunking Profile versionado; nenhum threshold numérico é FROZEN aqui.
37. `page_refs` são derivados por interval mapping e nunca inventados.
38. Nenhum Stable Chunk ID canônico é criado.
39. Chunking Strategy não ativa automaticamente semantic search nem substitui o concept-level lexical index.
40. Reranking Pipeline está CLOSED como Optional, Conditional, Profile-Governed e Fail-Open.
41. Nenhum Cross-Encoder, LLM, provider, API, GPU, candidate limit ou timeout específico é requisito arquitetural FROZEN.
42. Relevance e trust permanecem dimensões separadas.
43. `trust_tier`, `verified`, `status` e `repo_jur_verification_history` não são multiplicadores automáticos de relevance.
44. Falha de reranking preserva a ordem anterior válida e deve ser observável operacionalmente.
45. Canonical materialization permanece obrigatória após bypass, reranking ou fallback.
46. Não permanece Open Decision arquitetural de retrieval entre as atualmente registradas.

47. Existe um único Shared Conversion Core reutilizado pelos dois bounded contexts.
48. O split Legal Knowledge / Judicial Process ocorre somente após Phase 1 / Quality Gate.
49. `repo_jur/bundle/` permanece exclusivo da base jurídica canônica.
50. Judicial Process possui canonical/domain storage separado.
51. Schemas YAML e enrichment são separados por domínio.
52. Semantic Review / Enrichment é pré-Producer e não possui autoridade de publicação.
53. O conversor concreto atual é reutilizado atrás de `ConversionEngine`; não é reescrito por esta reconciliação.
54. O body da Phase 1 permanece literal; método OCR/routing/warnings/telemetria ficam no Technical JSON.
55. OCR permanece provider-neutral em arquitetura.
56. Post-OCR critical-data validation detecta/sinaliza; nunca autocorrige o conteúdo.
57. Comparação determinística de valores redundantes permanece futura capacidade separada.


58. Ingress/Preflight/official SHA/Evidence Preservation precedem Shared Conversion Core.
59. Paths documentais de componentes são logical targets, não obrigação de relocação física.
60. `src/pipeline_juridico/` é implementação física existente confirmada e deve ser reutilizada quando satisfizer a capacidade.
61. Phase 1 Markdown é imutável para Semantic Review.
62. Semantic Review estrutural preserva palavras originais e registra before/after/reason/confidence.
63. Ambiguidade semântica/estrutural resulta em `REVIEW_REQUIRED`.
64. Regras determinísticas de identificadores exigem especificação confiável e versionada; observação isolada não cria regra universal.
65. Retrieval Contract vigente atende somente Legal Knowledge e seu bundle.
66. Judicial Process Retrieval exige contrato próprio futuro.
67. Índices Legal Knowledge e Judicial Process não podem ser misturados sob a baseline atual.

---

**Status: FROZEN**
