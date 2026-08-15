# MEMORANDO DE DECISÃO ARQUITETURAL: CARDINALIDADE DE FONTES PDF (`repo_jur`)

**Versão:** 1.0 (Proposta de Solução)  
**Data:** 10 de agosto de 2026  
**Status:** FROZEN  
**Referência:** Baseado estritamente no *External Source Ingestion Contract* (ESIC) v1.1, no *Retrieval Contract* v2.1, no *Legal OKF Profile* v1.0, no *Concept Identity & Physical Structure* v1.0 e nas regras normativas da especificação oficial do **Open Knowledge Format (OKF) v0.2**.

---

## 1. Finalidade e Escopo do Memorando

Este memorando de decisão arquitetural analisa a **Open Decision — PDF Source Cardinality** estabelecida nas baselines de conformidade técnica e de identidade do projeto `repo_jur` [141, 221] e propõe uma solução para revisão. A decisão somente será considerada encerrada após aprovação formal deste memo e atualização controlada das especificações afetadas. O objetivo principal é definir e padronizar o modelo de representação de proveniência física e de integridade de dados quando as relações entre os arquivos PDF originais obtidos dos tribunais (evidências físicas) e os concept documents Markdown armazenados no repositório canônico (`repo_jur/bundle/`) desviarem da correspondência simples de 1:1 [41, 185, 204].

Este documento estabelece as garantias necessárias para sustentar a auditabilidade das peças e respostas jurídicas produzidas pelo Hermes Agent, preservando de forma rigorosa a separação de responsabilidades entre pipeline físico de extração (Fase 1), Produtor OKF (Fase 2) e os runtimes de busca lidos fora de banda [156, 157, 159].

---

## 2. Classificação de Diretrizes e Regras Técnicas

Para assegurar o rigor técnico e o alinhamento de conformidade do projeto, as diretrizes de dados estabelecidas pelas baselines congeladas e pela norma internacional são classificadas e catalogadas sob quatro categorias de controle [v4]:

### 2.1 OKF v0.2 Normative Requirements (Fatos Normativos)
*   **Identificador de Conceito Canônico (`concept_id`)**: Determinado exclusivamente pelo caminho relativo do arquivo Markdown a partir da raiz do diretório do bundle, omitindo-se a extensão `.md` (§3) [56]. O identificador é estritamente posicional e muda caso o arquivo de conceito seja movido de diretório [56].
*   **Soberania do Frontmatter**: O bloco de metadados delimitado por `---` deve conter obrigatoriamente a chave `type` [37, 61]. `type` é o único campo sempre obrigatório do frontmatter; não é uma primary key. Chaves customizadas incluídas pelo produtor são plenamente suportadas como extensões e devem ser toleradas de forma permissiva pelos consumidores (§4.1) [39, 61].
*   **Conformidade de Proveniência**: Se a família de metadados `sources` estiver declarada no frontmatter, cada entrada deve conter obrigatoriamente `resource` [42, 142]. O OKF define subcampos padronizados para `sources`, mas este memo não trata como requisito normativo uma proibição geral de extensões adicionais dentro de `sources[]`. Como política do `repo_jur`, hashes de evidência permanecerão em chaves próprias de nível superior para manter a separação semântica entre proveniência OKF e integridade física.
*   **Relação de Notas de Rodapé**: A atribuição de claims a fontes pode utilizar Markdown footnotes associadas ao `sources[].id` como join key (§5.1) [45, 67]. Essa convenção atribui o claim à fonte; ela não define, por si só, um schema de mapeamento página→fonte.
*   **Convenção Actor**: Campos de identidade e assinatura de logs (`generated.by`, `verified[].by`) utilizam obrigatoriamente três padrões sintáticos paralelos, incluindo o prefixo `human:<id>` para revisores e o padrão `<producer>/<version>` para ferramentas de software (§7) [51, 146].

### 2.2 repo_jur Project Requirements (Regras Frozen)
*   **Soberania do `/bundle/`**: O subdiretório exclusivo `/bundle/` do repositório maior é o corpus canônico soberano de todo o conhecimento do projeto, de caráter passivo e estático [21, 30, 99].
*   **Segurança de Somente Leitura (*Zero-Write*)**: O mecanismo de recuperação e o runtime de execução dos agentes são estritamente impedidos de realizar gravações, edições ou criação de arquivos sob a árvore do `/bundle/` [159, 187].
*   **Hash de Integridade Física**: O hash SHA-256 é calculado deterministicamente no preflight de ingresso no `repo_jur` a partir dos bytes brutos do PDF original obtido [185, 204]. **Ele comprova a integridade e reprodutibilidade física dos bytes ingeridos, não correspondendo a uma identidade única ou lógica do conceito e não provando autenticidade jurídica da fonte** [185, 204].
*   **Obrigatoriedade de Proveniência e Geração**: `generated` é obrigatório para concepts produzidos pelo pipeline canônico do `repo_jur`; `sources` é obrigatório quando o concept deriva de fontes identificáveis. Para concepts derivados de PDF, ambos se aplicam [14, 186, 204].
*   **Isolamento de Runtime**: Todos os arquivos operacionais em Markdown do Hermes (como `AGENTS.md` e `SKILL.md`) devem obrigatoriamente permanecer fora da árvore física de `/bundle/` [36, 61, 68].

### 2.3 Inferências Lógicas (Deduzidas das Baselines)
*   **Rastreabilidade no Object Storage**: A preservação dos PDFs originais em Object Storage externo exige uma referência estável e rastreável em `sources[].resource` para a evidência efetivamente utilizada pelo pipeline. Este memo não restringe essa referência a um esquema URI específico, desde que o contrato de ingestão consiga resolvê-la de forma confiável.
*   **Idempotência e Proteção Humana**: Reprocessamentos devem ser idempotentes quando inputs canônicos, configuração relevante e versão lógica do processamento forem equivalentes, preservando os metadados humanos válidos conforme o Lifecycle & Field Ownership FROZEN. O mesmo hash SHA-256, isoladamente, não garante saída idêntica se algoritmo, configuração ou versão lógica tiverem mudado.
*   **Preflight Precedente**: O SHA-256 deve ser calculado antes do processamento pesado. Um hash já conhecido sinaliza evidência física já ingerida, mas não autoriza rejeição automática do concept candidato, pois o mesmo PDF pode legitimamente originar múltiplos concepts.

### 2.4 Novas Propostas (Introduzidas neste Memorando)
*   **Extensão Jurídica `repo_jur_pdf_hashes`**: Propõe-se uma nova propriedade customizada de nível superior para concepts derivados de múltiplos PDFs, mapeando `sources[].id` → SHA-256 da evidência correspondente. Sua adoção exige atualização controlada do Legal OKF Profile e dos documentos FROZEN afetados.
*   **Atribuição de claims por fonte**: Em concepts sintéticos com múltiplas fontes, `sources[].id` e footnotes podem atribuir claims à fonte correspondente. Este memo não cria um schema canônico de página→fonte nem reutiliza `[[Pág. N]]` como sequência global artificial para múltiplos PDFs.

---

## 3. Análise dos Quatro Cenários de Cardinalidade

A representação de metadados físicos, quebras de páginas ordinais e rastreabilidade deve acomodar de forma coerente os quatro cenários de relacionamento de cardinalidade entre evidências físicas (PDFs originais) e concept documents (.md):

```
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                    CENÁRIOS DE CARDINALIDADE                                |
+─────────────────────────────────────────────────────────────────────────────────────────────+
|                                                                                             |
| [ 1 PDF ──► 1 Concept ]            [ 1 PDF ──► Múltiplos Concepts ]                         |
|   (Mapeamento padrão 1:1)             (Desmembramento lógico de diários de justiça)          |
|                                                                                             |
| [ Múltiplos PDFs ──► 1 Concept ]   [ Múltiplos PDFs ──► Múltiplos Concepts ]                |
|   (Consolidação de Temas)             (Redes complexas de acórdãos e recursos)              |
|                                                                                             |
+─────────────────────────────────────────────────────────────────────────────────────────────+
```

### 3.1 Cenário A: 1 PDF ──► 1 Concept (Caso de Alinhamento Direto)
*   *Definição*: O cenário padrão de processamento. Um arquivo PDF oficial e unívoco contendo o texto completo de uma única lei, portaria ou acórdão é ingerido e convertido para um único concept document correspondente no bundle [148, 149].
*   *Mecanismo de Proveniência*:
    *   `sources`: Contém uma única entrada mapeando o arquivo PDF original, seu autor e sua data de modificação oficial de origem [41, 149].
    *   `repo_jur_pdf_hash`: Preenchido diretamente na propriedade top-level do frontmatter com o hash SHA-256 calculado a partir dos bytes originais do PDF [185, 204].
    *   *Rastreabilidade*: O corpo Markdown reproduz fielmente as quebras ordinais através de marcadores `[[Pág. N]]` de 1 até o total de páginas N do PDF de entrada [181]. A cadeia de rastreabilidade é: `Trecho` ──► `[[Pág. N]]` ──► `concept_id` ──► `sources[].resource` + `repo_jur_pdf_hash` ──► evidência PDF preservada.

### 3.2 Cenário B: 1 PDF ──► Múltiplos Concepts (Caso de Desmembramento Lógico)
*   *Definição*: Ocorre quando um único arquivo PDF volumoso de entrada (como um Diário de Justiça unificado ou um Diário Oficial da União) abriga logicamente múltiplos atos jurídicos independentes (ex: 50 acórdãos de julgamentos separados de relatores distintos) que necessitam ser catalogados como conceitos individuais [35, 37].
*   *Mecanismo de Proveniência*:
    *   *Extração*: O pipeline de conversão física (Fase 1) extrai o texto do PDF unificado em um único arquivo de Markdown intermediário e gera o relatório técnico JSON unificado de proveniência [184, 186].
    *   *Compilação OKF*: O Produtor OKF (Fase 2) analisa as saídas físicas e secciona o conteúdo em múltiplos arquivos Markdown de conceito independentes, salvando-os de forma isolada nos subdiretórios adequados do bundle (ex: `/bundle/jurisprudencia/acordao_a.md`, `/bundle/jurisprudencia/acordao_b.md`) [35, 37].
    *   `sources`: Cada concept document individual gerado preenche seu bloco `sources` mapeando o mesmo arquivo PDF unificado como sua fonte de origem física [41].
    *   `repo_jur_pdf_hash`: Todos os conceitos gerados a partir do mesmo diário preencherão em sua propriedade de nível superior `repo_jur_pdf_hash` o **mesmo hash SHA-256 do PDF unificado original**, assegurando o lastro físico fidedigno da evidência.
    *   *Páginas físicas*: Os marcadores `[[Pág. N]]` contidos no corpo Markdown de cada conceito refletirão de forma estrita a numeração física da página correspondente dentro do PDF unificado original (ex: se o acórdão A reside nas páginas 150 a 160 do Diário, seu Markdown conterá os marcadores `[[Pág. 150]]` a `[[Pág. 160]]`). Isso garante que a cadeia de proveniência remonte com precisão à página física exata do documento do tribunal, sem requerer a criação de PDFs artificiais desmembrados.

### 3.3 Cenário C: Múltiplos PDFs ──► 1 Concept (Caso de Consolidação/Conceito Abstrato)
*   *Definição*: Ocorre quando um único concept document (como um conceito abstrato doutrinário `TemaJuridico` de repercussão geral, ou uma súmula do tipo `PrecedenteVinculante`) consolida ou cita em seu ementário e fundamentação histórica múltiplos acórdãos e precedentes baseados em PDFs físicos de origens distintas [150, 151].
*   *Mecanismo de Proveniência*:
    *   `sources`: O concept document Markdown final (que reside em um único arquivo sob `/bundle/temas/` ou `/bundle/precedentes/`) lista cada arquivo PDF de entrada correspondente na família `sources` (ex: `sources: - id: preced_01`, `- id: preced_02`) [41, 151].
    *   `repo_jur_pdf_hash`: Quando houver múltiplos PDFs de origem, o campo singular deixa de ser suficiente. Nesta proposta, ele é omitido em favor de `repo_jur_pdf_hashes`; a omissão decorre da cardinalidade múltipla, não do fato de o concept ser abstrato.
    *   `repo_jur_pdf_hashes` (Proposta): Para preservar a integridade física de bytes de cada uma das fontes originais consolidadas, o Produtor OKF insere no frontmatter o dicionário de extensão customizada de nível superior de domínio juridico, vinculando cada hash ao ID correspondente listado em `sources`.
    *   *Rastreabilidade*: Em concept sintético multi-fonte, o corpo não deve criar uma numeração global artificial `[[Pág. N]]`. `sources[].id` e footnotes podem atribuir claims às fontes; uma representação estruturada de página específica por fonte fica fora do escopo desta decisão.

### 3.4 Cenário D: Múltiplos PDFs ──► Múltiplos Concepts (Caso de Redes de Processos Complexas)
*   *Definição*: Ocorre em processos judiciais interconectados por embargos de declaração paralelos, recursos cruzados de instâncias superiores e incidentes de inconstitucionalidade, em que múltiplos arquivos PDFs físicos originam e influenciam uma pluralidade de peças lógicas conceituais no bundle.
*   *Mecanismo de Proveniência*:
    *   *Comportamento*: É representado de forma descentralizada por meio da combinação robusta das regras lógicas descritas nos cenários B e C. Cada peça de conhecimento do processo habitará seu próprio arquivo Markdown conceitual (com seu slug de arquivo determinístico próprio e `concept_id` de diretório correspondente) [35, 37]. 
    *   Os documentos de conceito farão referências cruzadas entre si no corpo do texto utilizando markdown links normais do OKF [21, 48]. As origens físicas serão mapeadas individualmente pelas entradas em `sources` e os hashes de bytes garantidos em `repo_jur_pdf_hashes`, permitindo que o Hermes caminhe pelo grafo conceitual-físico de forma multidirecional e segura [41, 48].

---

## 4. Alternativas de Modelagem Arquitetural

Três alternativas técnicas de modelagem de proveniência física e lógica foram projetadas e avaliadas pelo comitê técnico do projeto:

### 4.1 Alternativa 1: Acoplamento Rígido e Mandatório 1:1 (Modelo Canônico Restrito)
*   **Estrutura Proposta**: Limita de forma estrita o sistema para que cada concept document Markdown OKF possua obrigatoriamente um correspondente de PDF físico original em Object Storage, travando a cardinalidade em 1:1 de forma mandatória.
*   **Comportamento nos Quatro Cenários**:
    *   *Cenário A*: Alinhamento direto perfeito.
    *   *Cenário B*: Bloqueado na sua forma nativa. Exige que a Fase 1 execute uma quebra física dos bytes do PDF de Diário da Justiça, fatiando-o em dezenas de arquivos PDF independentes antes do processamento [184], o que gera novos hashes e descaracteriza a evidência física oficial original do tribunal.
    *   *Cenário C*: Bloqueado na sua forma nativa. Exige a fragmentação forçada do conceito sintético único (TemaJuridico) em múltiplos Markdown lógicos vazios (um para cada PDF precedente), interligados de forma complexa por links no Git.
    *   *Cenário D*: Decomposto artificialmente em múltiplas relações separadas 1:1.
*   **Vantagens**: Simplicidade conceitual extrema para codificação do Produtor OKF na Fase 2; o hash de nível superior `repo_jur_pdf_hash` sempre possui correspondente idêntico de PDF em Object Storage.
*   **Riscos**: 
    *   Exige pré-processamentos e manipulações pesadas sobre binários na Fase 1, o que pode corromper a integridade estrutural e tipográfica de PDFs complexos, gerando erros e falhas de cota em OCRs de visão [181, 184].
    *   Incompatibilidade física com conceitos abstratos ou teses vinculantes, forçando a criação de referências vazias ou arquivos dummy.
*   **Complexidade**: Baixa na Fase 2, mas transfere alta complexidade de runtime e custos computacionais para a Fase 1 (pipeline físico).
*   **Impacto nos Documentos FROZEN**: Elevado. Viola a especificação de `legal-okf-profile-v1.0.md` que estabelece a omissão de dados de hashes físicos para o tipo de conceito abstrato `TemaJuridico` [150, 204], exigindo a reabertura de baselines consolidadas.

### 4.2 Alternativa 2: Desacoplamento Total via Repositório de Fontes Dedicado (Modelo Normalizado)
*   **Estrutura Proposta**: Cria uma pasta dedicada exclusivamente ao inventário de proveniência física dentro de `/bundle/` (ex: `/bundle/sources/`), onde cada arquivo representa unicamente um PDF original de evidência cadastrado com seu hash, link de storage, data de obtenção e metadados de preflight. Os concept documents de Legislação ou Jurisprudência não carregam propriedades físicas de PDF, apontando para estes arquivos lógicos de fontes na família `sources[].resource` (ex: `sources: - resource: /sources/acordao_original_stf_re635659.md`) [41, 42].
*   **Comportamento nos Quatro Cenários**:
    *   *Cenário A*: O conceito aponta para o arquivo de fonte lógica em `/sources/`.
    *   *Cenário B*: Vários arquivos de conceito (.md) compartilham a mesma referência apontando para o arquivo de fonte correspondente ao PDF unificado.
    *   *Cenário C*: O conceito lista múltiplos caminhos de `/sources/` em seu campo `sources`.
    *   *Cenário D*: Resolvido de forma flexível por meio de associações e arestas no grafo de referências do bundle.
*   **Vantagens**: Elevada elegância de engenharia de dados e normalização de tabelas de banco; evita a duplicação de hashes e URIs físicas no frontmatter do bundle canônico.
*   **Riscos**:
    *   Aumenta a indireção e a complexidade operacional para consumidores humanos e agentes, exigindo saltos adicionais para correlacionar concept, fonte, PDF e hash.
    *   Exige uma nova classe/estrutura de concepts de fonte e altera a arquitetura física FROZEN do `repo_jur`. Sua rejeição decorre da arquitetura e da simplicidade desejada pelo projeto, não de uma proibição normativa geral do OKF.
*   **Complexidade**: Altíssima. Requer do `repo_jur_producer` o gerenciamento sincronizado e atômico de duas árvores físicas de diretórios de forma paralela no Git.
*   **Impacto nos Documentos FROZEN**: Alto. Exige reescrever os perfis estruturais de `sources` e os metadados estabelecidos no `legal-okf-profile-v1.0.md` [204].

### 4.3 Alternativa 3: Cardinalidade Nativa com Hash Singular/Plural no Top-Level (RECOMENDADA)

*   **Estrutura Proposta**:
    *   **Exatamente 1 PDF de origem**: usar `repo_jur_pdf_hash: "<sha256-64-hex>"`.
    *   **2 ou mais PDFs de origem**: omitir `repo_jur_pdf_hash` e usar `repo_jur_pdf_hashes`, um mapping top-level `sources[].id` → SHA-256.
    *   `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` são mutuamente exclusivos.
    *   Em cenário multi-PDF, cada fonte PDF em `sources` deve possuir `id`, e cada `id` de PDF deve ter exatamente uma entrada correspondente em `repo_jur_pdf_hashes`.
    *   Fontes não-PDF podem permanecer em `sources`, mas não aparecem em `repo_jur_pdf_hashes`.
    *   O mesmo hash pode aparecer em múltiplos concepts quando a mesma evidência PDF sustentar mais de um concept.

*   **Comportamento nos Quatro Cenários**:
    *   **Cenário A — 1 PDF → 1 Concept**: `repo_jur_pdf_hash` singular + uma entrada PDF em `sources`.
    *   **Cenário B — 1 PDF → múltiplos Concepts**: cada concept usa o mesmo `repo_jur_pdf_hash` singular e referencia a mesma evidência em `sources`; seus `concept_id`s continuam distintos.
    *   **Cenário C — múltiplos PDFs → 1 Concept**: cada PDF entra em `sources` com `id`; `repo_jur_pdf_hashes` mapeia cada `id` ao hash correspondente.
    *   **Cenário D — múltiplos PDFs → múltiplos Concepts**: cada concept lista apenas as fontes que efetivamente o sustentam e mantém o mapping `repo_jur_pdf_hashes` correspondente às suas fontes PDF.

*   **Páginas e claims**:
    *   Para concept literal derivado de uma única evidência PDF, `[[Pág. N]]` continua referindo-se à página física dessa evidência.
    *   Para concept sintético multi-fonte, não se cria sequência global artificial de `[[Pág. N]]`.
    *   `sources[].id` + footnotes podem atribuir claims à fonte; eventual schema estruturado de página por fonte não é decidido neste memo.

*   **Vantagens**:
    *   Mantém o caso comum simples.
    *   Resolve 1:1, 1:N, N:1 e N:M sem transformar SHA-256 em identidade de concept.
    *   Preserva a separação entre `sources` (proveniência lógica) e hashes (integridade física).
    *   Permite reconstrução determinística da relação concept ↔ evidência PDF.

*   **Riscos**:
    *   Introduz um novo campo customizado (`repo_jur_pdf_hashes`) e exige validação de consistência entre suas chaves e `sources[].id`.
    *   Exige atualização controlada das baselines FROZEN afetadas.

*   **Complexidade**: Média e localizada no Produtor/validador.

*   **Impacto nos Documentos FROZEN**: **Não é zero.** A aprovação desta alternativa exige, no mínimo, atualização controlada do Legal OKF Profile e das especificações que hoje tratam `PDF Source Cardinality` como Open Decision. A mudança deve ser explícita, versionada e limitada ao fechamento dessa decisão.

---

## 5. Recommended Option (Opção Recomendada)

Propõe-se a adoção da **Alternativa 3 corrigida: Cardinalidade Nativa com Hash Singular/Plural no Top-Level**.

### Regra proposta

```yaml
# exatamente 1 PDF de origem
repo_jur_pdf_hash: "<sha256-64-hex>"
```

```yaml
# múltiplos PDFs de origem
sources:
  - id: "source_pdf_a"
    resource: "<source-a-resource>"
  - id: "source_pdf_b"
    resource: "<source-b-resource>"

repo_jur_pdf_hashes:
  source_pdf_a: "<sha256-64-hex>"
  source_pdf_b: "<sha256-64-hex>"
```

### Invariantes da proposta

1. `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` são mutuamente exclusivos.
2. `repo_jur_pdf_hash` aplica-se somente quando houver exatamente uma evidência PDF de origem.
3. `repo_jur_pdf_hashes` aplica-se quando houver duas ou mais evidências PDF.
4. Cada chave de `repo_jur_pdf_hashes` deve corresponder exatamente a um `sources[].id` de uma fonte PDF.
5. Toda fonte PDF em cenário multi-PDF deve possuir `sources[].id`.
6. Fontes não-PDF não entram no mapping de hashes.
7. O mesmo PDF/hash pode participar da proveniência de vários concepts.
8. SHA-256 identifica bytes da evidência, não o concept e não prova autenticidade jurídica.
9. Aprovar esta opção exige atualização controlada das baselines FROZEN afetadas.
10. Idempotência continua dependente de inputs canônicos, configuração relevante e versão lógica do processamento, não apenas do hash.

### Justificativa

A proposta mantém simples o cenário dominante de uma única evidência PDF e adiciona somente o mecanismo necessário para múltiplos PDFs. Não exige uma árvore paralela de fontes, não altera `concept_id`, não acopla o bundle a retrieval e preserva a proveniência física de cada evidência sem transformar `sources` em um repositório de metadados técnicos.

---

## 6. Diferenciação das Regras do Memorando

### **OKF v0.2 Normative Requirement** (Exigência do Padrão Internacional)
*   A determinação obrigatória do `concept_id` com base no caminho relativo do arquivo a partir da raiz do bundle sem a extensão `.md` (§3) [56].
*   Se `sources` estiver presente, cada entrada deve possuir `resource`; `sources[].id` pode ser utilizado como join key para atribuição de claims.
*   O uso de Markdown footnotes associado a `sources[].id` para atribuição de claims à fonte quando essa técnica for utilizada.

### **repo_jur Project Requirement** (Regras Obrigatórias Congeladas nas Baselines)
*   Para concept derivado de exatamente um PDF, `repo_jur_pdf_hash` registra o SHA-256 dos bytes originais da evidência. A cardinalidade múltipla é precisamente a decisão encerrada por este memo.
*   Concepts literais derivados de PDF preservam os marcadores físicos `[[Pág. N]]` correspondentes às páginas efetivamente representadas; um concept originado de trecho de PDF maior não precisa iniciar em `[[Pág. 1]]`.
*   O corpo literal producer-owned de qualquer concept derivado de PDF deve preservar o conteúdo canônico produzido pela pipeline; a regra depende da origem/modo de produção, não apenas do `type`.
*   `verified` é condicional e somente registra eventos reais de verificação; geração pelo Produtor não constitui autoverificação.

### **Recommendation** (Recomendação Arquitetural de Design)
*   Recomenda-se manter qualquer estratégia futura de retrieval fora desta decisão e preservar apenas os requisitos canônicos de proveniência definidos neste memo.

### **Open Decision** (Decisões Técnicas Mantidas em Aberto para Fase Posterior)
*   **Open Decision — Stable Concept Identity**: Deliberação sobre o método de identificação lógica global persistente (UUID) no YAML para rastrear conceitos após movimentos físicos de pastas.
*   **Open Decision — Duplicate Act Handling**: Regras de governança lógicas para tratamento de atos ementados idênticos originários de caminhos distintos no bundle.

---

**Status do Memorando:** **FROZEN**
