# IDENTIDADE CONCEITUAL E ESTRUTURA FÍSICA DO BUNDLE (`repo_jur`)

**Versão:** 1.3 (Baseline — atualização controlada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Referência:** Baseline v1.1 + `decision-memo-duplicate-act-handling-v1.0-FROZEN.md` (APPROVED — CLOSED — FROZEN), mantendo `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, Legal OKF Profile v1.1, ESIC e Retrieval Contract como referências de controle.

---

## 1. Estrutura do Bundle OKF

O diretório `/bundle/` do `repo_jur/` é o subdiretório exclusivo que reúne o corpus jurídico canônico do projeto. A organização física das pastas deve separar as classes de documentos e conceitos jurídicos de forma lógica, mantendo o bundle portátil, independente de runtimes, e em estrita conformidade com o padrão OKF v0.2 [35, 99].

### 1.1 Diretórios e Classes de Conceitos
*   **`/bundle/legislacao/`**: Diretório exclusivo para abrigar documentos do tipo `Legislacao` (leis, decretos, portarias, emendas constitucionais) [37, 148].
*   **`/bundle/jurisprudencia/`**: Diretório exclusivo para abrigar documentos do tipo `Jurisprudencia` (acórdãos de inteiro teor, votos de relatores, ementas de julgados e notas taquigráficas) [37, 149].
*   **`/bundle/temas/`**: Diretório exclusivo para abrigar documentos do tipo `TemaJuridico` (teses jurídicas vinculantes de repercussão geral, recursos repetitivos e conceitos doutrinários abstratos) [37, 150].
*   **`/bundle/precedentes/`**: Diretório exclusivo para abrigar documentos do tipo `PrecedenteVinculante` (enunciados de súmulas, súmulas vinculantes e outros precedentes classificados nesse tipo pelo Legal OKF Profile) [37, 151].
    *   *Justificativa de separação*: A existência de um diretório próprio decorre da distinção semântica já adotada no Legal OKF Profile entre `PrecedenteVinculante` e `Jurisprudencia`. A organização física não depende do tamanho do documento, de RAG, de filtros de busca ou de qualquer mecanismo de retrieval.
*   **`repo_jur Project Requirement — Mandatory`**: A separação das pastas nas quatro estruturas acima (`legislacao/`, `jurisprudencia/`, `temas/`, `precedentes/`) é obrigatória para a organização física da base do projeto, devendo ser estritamente respeitada pelo Produtor OKF no momento da publicação atômica do conceito.

### 1.2 Arquivos Reservados
*   **`/bundle/index.md`**: Arquivo de catálogo de navegação hierárquica localizado na raiz do bundle (e opcionalmente em qualquer subdiretório) [58, 74]. Não possui frontmatter (salvo a chave `okf_version: "0.2"` na raiz) e agrupa os conceitos do diretório em listas estruturadas de links com suas respectivas descrições de ementa, facilitando a navegação progressiva por agentes [52, 74].
*   **`/bundle/log.md`**: Arquivo de histórico cronológico descendente (YYYY-MM-DD) para auditar as ações de modificações, ingesta ou depreciação de conceitos na base [53, 58, 75].
*   **`OKF v0.2 Normative Requirement`**: Os arquivos `index.md` e `log.md` são os únicos nomes reservados dentro do bundle OKF [58]. Eles são fisicamente opcionais na estrutura de diretórios, mas, *caso estejam presentes*, devem seguir estritamente as regras de parsing e gramáticas da especificação OKF v0.2 [61, 83]. Qualquer outro arquivo `.md` não reservado dentro do subdiretório do bundle é automaticamente considerado um documento de conceito [101, 126].

---

## 2. Regras de Filename e Slug

A geração de nomes de arquivos e identificadores textuais pelo Produtor OKF deve ser estritamente determinística, padronizada e imune a incompatibilidades de codificação de sistemas operacionais distintos, garantindo a portabilidade do repositório Git [30, 35].

*   **`repo_jur Project Requirement — Mandatory`**: O Produtor OKF deve aplicar as seguintes regras lógicas de transformação e sanitização para gerar os slugs de arquivos a partir dos metadados das fontes originais:
    1.  **Conversão de Caixa (Lowercase)**: Todos os caracteres devem ser convertidos obrigatoriamente para caixa baixa (letras minúsculas).
    2.  **Transliteração de Acentos e Caracteres Especiais**: Sinais diacríticos e acentos devem ser removidos e substituídos por seus caracteres ASCII equivalentes básicos (ex: `á` -> `a`, `ã` -> `a`, `ç` -> `c`, `ê` -> `e`, `í` -> `i`).
    3.  **Remoção de Espaços e Pontuação**: Espaços em branco, pontos, vírgulas, barras, hifens e símbolos ordinais (ex: `º`, `ª`) devem ser totalmente removidos ou convertidos.
    4.  **Uso de Caracteres Permitidos**: Os únicos caracteres permitidos para a composição física do nome do arquivo são letras minúsculas de `a-z`, dígitos de `0-9` e o caractere de sublinhado `_` (underscore) como separador de termos lógicos.
    5.  **Tratamento de Siglas e Termos de Origem**: Siglas oficiais de tribunais ou tipos de atos devem ser mantidas em letras minúsculas (ex: `stf`, `stj`, `re`, `adi`, `lei`).
    6.  **Sufixo de Extensão**: O nome do arquivo deve ser obrigatoriamente encerrado pela extensão física minúscula `.md`.
*   **`Recommendation`**: Os slugs devem conter metadados cronológicos estruturados (como o ano de promulgação da lei ou julgamento do acórdão) para facilitar a ordenação alfabética natural do sistema de arquivos e evitar colisões lógicas de nomes.

---

## 3. Canonical OKF Concept ID

O `concept_id` é o identificador básico de junção de grafos no ecossistema do Open Knowledge Format [56].

*   **`OKF v0.2 Normative Requirement`**: O `concept_id` de um documento de conceito dentro do bundle é determinado obrigatoriamente pelo caminho relativo do arquivo Markdown a partir da raiz do bundle, removendo-se o sufixo de extensão `.md` [56].
    *   *Sintaxe canônica*: `pasta/subpasta/slug_do_arquivo` [56].
    *   *Exemplo*: `jurisprudencia/acordao_stf_re_635659` (correspondente ao arquivo físico `/bundle/jurisprudencia/acordao_stf_re_635659.md`).
*   **`OKF v0.2 Normative Requirement`**: O `concept_id` é estritamente **posicional** [56]. Ele reflete o estado e a localização física atual do arquivo de conceito na árvore de diretórios. Se um arquivo for movido de pasta ou tiver seu nome alterado, o seu `concept_id` muda de forma correspondente [56].
*   **`repo_jur Project Requirement — Mandatory`**: O `concept_id` derivado do caminho relativo **não** deve ser duplicado ou salvo como um campo literal estático no frontmatter YAML do conceito, evitando redundância e potenciais dessincronizações de dados em commits do Git [21, 35]. O identificador é computado de forma dinâmica em tempo de execução pelos leitores e indexadores a partir do sistema de arquivos.

---

## 4. Stable Concept Identity

*   **`Decision Status — CLOSED: Stable Concept Identity`**: encerrada por `decision-memo-stable-concept-identity-v1.0-FROZEN.md`.
*   **Modelo adotado:** Identidade Posicional Pura. O `concept_id` continua sendo a referência canônica do concept dentro do bundle e deriva exclusivamente do caminho relativo do Markdown sem `.md`.
*   **Sem Stable ID adicional:** o `repo_jur` não adota UUID, hash lógico ou outro identificador persistente adicional no frontmatter nesta baseline.
*   **Rename/Move:** mover ou renomear altera imediatamente o `concept_id`; links internos dependentes do path devem ser tratados antes da publicação e artefatos derivados devem ser sincronizados, reconstruídos ou invalidados conforme o Retrieval Contract.
*   **Git:** preserva histórico/versionamento, mas não constitui identidade persistente de domínio.
*   **Limite da decisão:** Stable IDs não são incompatíveis com OKF; apenas não há necessidade atual demonstrada no `repo_jur`. A decisão pode ser reaberta futuramente por novo Decision Memo se surgir requisito concreto de identidade imutável externa ao path.

---

## 5. Regras de Nomenclatura por Tipo de Conceito

O Produtor OKF deve aplicar convenções determinísticas de filename utilizando somente metadados realmente disponíveis e já definidos no Legal OKF Profile. As fórmulas abaixo são condicionais: quando os elementos necessários não existirem, deve ser utilizado um fallback determinístico baseado em título ou identificador oficial disponível, sem inventar tribunal, número, classe processual ou outro metadado ausente.

### 5.1 Tipo `Legislacao`
*   **`repo_jur Project Requirement — Mandatory`**: Para atos normativos numerados, usar preferencialmente `[tipo_norma]_[numero_norma]_[ano].md`.
    *   *Exemplo abstrato*: `bundle/legislacao/lei_12345_2026.md`
*   **`repo_jur Project Requirement — Fallback`**: Para atos sem número oficial ou quando algum elemento necessário não estiver disponível, gerar slug determinístico a partir do título oficial e dos identificadores efetivamente disponíveis, respeitando as regras da Seção 2.

### 5.2 Tipo `Jurisprudencia`
*   **`repo_jur Project Requirement — Mandatory`**: O filename deve identificar de forma determinística o ato judicial sem presumir que todo concept seja um acórdão ou possua classe processual específica.
*   **`Recommendation`**: Quando tribunal, classe processual e número oficial estiverem disponíveis, pode-se utilizar `[tipo_documento]_[tribunal]_[classe]_[numero].md`.
    *   *Exemplo abstrato*: `bundle/jurisprudencia/acordao_stf_re_987654.md`
*   **`repo_jur Project Requirement — Fallback`**: Se algum desses elementos não existir, usar os identificadores oficiais disponíveis e, em último caso, slug determinístico derivado do título do documento, sem inventar metadados.

### 5.3 Tipo `TemaJuridico`
*   **`repo_jur Project Requirement — Mandatory`**: Temas oficiais numerados de tribunal podem utilizar `tema_[tribunal]_[numero_tema].md`.
    *   *Exemplo abstrato*: `bundle/temas/tema_stf_4321.md`
*   **`repo_jur Project Requirement — Fallback`**: `TemaJuridico` abstrato ou doutrinário sem tribunal e/ou número oficial deve usar slug determinístico baseado no título do conceito, por exemplo `bundle/temas/<slug_do_titulo>.md`. Não devem ser criados tribunal ou número artificiais.

### 5.4 Tipo `PrecedenteVinculante`
*   **`repo_jur Project Requirement — Mandatory`**: O filename deve refletir a espécie efetiva do precedente e seus identificadores oficiais disponíveis.
*   **`Recommendation`**: Para súmulas numeradas, pode-se utilizar `sumula_[classe_precedente]_[tribunal]_[numero].md`.
    *   *Exemplo abstrato*: `bundle/precedentes/sumula_vinculante_stf_99.md`
*   **`repo_jur Project Requirement — Fallback`**: Para outros precedentes classificados como `PrecedenteVinculante`, usar slug determinístico baseado na espécie e nos identificadores oficiais disponíveis, sem forçar o prefixo `sumula_`.

---

## 6. Tratamento de Duplicatas e Colisões

O Produtor OKF deve diferenciar **identidade física da evidência** de **identidade jurídica/lógica do ato**.

*   **`repo_jur Project Requirement — Mandatory`**: O SHA-256 identifica os bytes exatos de uma evidência PDF, mas não identifica concept, ato jurídico nem autenticidade. O mesmo PDF pode legitimamente participar da proveniência de múltiplos concepts.
*   **`repo_jur Project Requirement — Mandatory`**: Um hash já conhecido é sinal de evidência física já ingerida; não autoriza rejeição automática, no-op automático nem fusão de concepts.
*   **`repo_jur Project Requirement — Mandatory`**: Metadados estruturados do Legal OKF Profile são **sinais de identidade**, não uma primary key universal do ato. Nenhum campo isolado — inclusive SHA-256, URL, filename, `concept_id` ou número de processo — decide equivalência jurídica.
*   **`repo_jur Project Requirement — Mandatory`**: Antes de consolidar evidências, devem ser avaliados conjuntamente: sinais jurídicos disponíveis, autoridade/origem aplicável, equivalência material do conteúdo e inexistência de autonomia jurídica entre os atos.
*   **`repo_jur Project Requirement — Same Bytes / Multiple Locators`**: Os mesmos bytes obtidos por URLs/locators diferentes continuam representando uma única evidência física. Não se cria automaticamente uma segunda fonte PDF apenas por existir outro locator de coleta.
*   **`repo_jur Project Requirement — Different PDFs / Same Act`**: PDFs fisicamente distintos podem sustentar um único concept somente quando a equivalência lógica e material do ato estiver estabelecida sem ambiguidade. Nesse caso, `sources` e a cardinalidade singular/plural são atualizados conforme o memo de PDF Source Cardinality.
*   **`repo_jur Project Requirement — Material Change`**: Mudança material ou dúvida entre duplicata, nova versão e ato autônomo bloqueia fusão automática e exige revisão humana. O Produtor não altera `status` autonomamente e não cria sufixos artificiais como `_v2` para resolver versionamento.
*   **`repo_jur Project Requirement — Distinct Acts`**: Documentos juridicamente distintos do mesmo processo, PDF ou Diário permanecem em concepts separados quando representarem atos autônomos.
*   **`repo_jur Project Requirement — Slug Collision`**: Colisões de slug devem ser resolvidas apenas com identificadores oficiais já disponíveis. É proibido sobrescrever silenciosamente ou inventar metadados; persistindo a colisão, a operação exige revisão humana.
*   **`Decision Status — CLOSED: Duplicate Act Handling`**: Encerrada por `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`.

---

## 7. Cardinalidade entre Concepts e Fontes

*   **`repo_jur Project Requirement`**: A arquitetura deve admitir, sem alterar a estrutura canônica do bundle, um PDF originando mais de um concept; um concept derivando de mais de uma fonte; múltiplos PDFs contribuindo para um concept; múltiplos PDFs sustentando múltiplos concepts; e fontes não-PDF participando da proveniência.
*   **`repo_jur Project Requirement`**: Relações 1:1, 1:N, N:1 e N:M entre PDFs e concepts não alteram a regra normativa do `concept_id`, que continua derivado exclusivamente do caminho relativo do arquivo Markdown.
*   **`repo_jur Project Requirement — Exactly 1 PDF`**: Quando um concept derivar de exatamente uma evidência PDF, deve utilizar `repo_jur_pdf_hash` com o SHA-256 dos bytes dessa evidência.
*   **`repo_jur Project Requirement — 2+ PDFs`**: Quando um concept derivar de duas ou mais evidências PDF, deve omitir `repo_jur_pdf_hash` e utilizar `repo_jur_pdf_hashes`, mapeando `sources[].id` → SHA-256 de cada evidência PDF.
*   **`repo_jur Project Requirement — Mutual Exclusivity`**: `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` são mutuamente exclusivos.
*   **`repo_jur Project Requirement — Source Mapping`**: Em cenário multi-PDF, toda fonte PDF listada em `sources` deve possuir `id`, e cada `id` deve possuir exatamente uma entrada correspondente em `repo_jur_pdf_hashes`. Fontes não-PDF podem permanecer em `sources`, mas não devem aparecer no mapping de hashes.
*   **`repo_jur Project Requirement — Shared Evidence`**: O mesmo PDF e o mesmo SHA-256 podem aparecer na proveniência de múltiplos concepts quando a mesma evidência física sustentar unidades lógicas distintas.
*   **`repo_jur Project Requirement — Hash Semantics`**: SHA-256 identifica os bytes da evidência física; não constitui identidade lógica do concept e não prova autenticidade jurídica.
*   **`repo_jur Project Requirement — Pages`**: Para concept literal derivado de uma única evidência PDF, os marcadores `[[Pág. N]]` referem-se às páginas físicas efetivamente representadas desse PDF. Concepts sintéticos multi-fonte não devem criar uma sequência global artificial de `[[Pág. N]]`.
*   **`repo_jur Project Requirement`**: Esta decisão não cria subcampos customizados de hash dentro de `sources` e não altera a semântica normativa de `sources[].resource`.
*   **`Decision Status — CLOSED`**: A **PDF Source Cardinality** foi encerrada por `decision-memo-pdf-source-cardinality-v1.0` (FROZEN) e incorporada ao *Legal OKF Profile* v1.1.

### 7.1 Matriz de Cardinalidade

| Relação | Representação canônica |
|---|---|
| 1 PDF → 1 Concept | `sources` + `repo_jur_pdf_hash` |
| 1 PDF → N Concepts | cada concept usa `sources` + o mesmo `repo_jur_pdf_hash` |
| N PDFs → 1 Concept | `sources[].id` + `repo_jur_pdf_hashes` |
| N PDFs → N Concepts | cada concept lista apenas suas fontes aplicáveis e usa `repo_jur_pdf_hashes` quando possuir 2+ PDFs |

### 7.2 Alteração controlada v1.3

*   **Decisões incorporadas:** `PDF Source Cardinality` e `Duplicate Act Handling` estão CLOSED.
*   **Impacto físico:** nenhum novo diretório é criado no bundle.
*   **Impacto de schema:** nenhum novo campo YAML é criado por Duplicate Act Handling; `repo_jur_pdf_hashes` permanece conforme Legal OKF Profile v1.1.
*   **Compatibilidade:** concepts derivados de exatamente um PDF permanecem usando `repo_jur_pdf_hash`.
*   **Escopo:** `Stable Concept Identity` está CLOSED; nenhuma nova identidade persistente foi criada.

---

## 8. Movimentação e Renomeação de Concepts

*   **`repo_jur Project Requirement — Mandatory`**: Se um concept for movido ou renomeado dentro de `/bundle/`, seu `concept_id` muda imediatamente porque o identificador é posicional.
*   **`repo_jur Project Requirement — Mandatory`**: Antes da publicação da alteração, todas as referências internas do bundle que dependam do caminho antigo devem ser revisadas e atualizadas para evitar links quebrados. O mecanismo concreto de atualização não é prescrito por este documento.
*   **`repo_jur Project Requirement — Mandatory`**: Artefatos derivados associados ao `concept_id` antigo, quando existirem, devem ser atualizados, reconstruídos ou invalidados conforme o Retrieval Contract.
*   **`repo_jur Project Requirement`**: O histórico de movimentações e renomeações é preservado pelo versionamento Git do projeto. Este contrato não exige um comando Git específico nem duplicação de histórico no frontmatter.
*   **`Decision Status — CLOSED: Stable Concept Identity`**: `decision-memo-stable-concept-identity-v1.0-FROZEN.md` confirma que movimentações e renomeações alteram o `concept_id` e não são estabilizadas por um ID adicional.

---

## 9. Relações e Links entre Concepts

O OKF v0.2 representa relações canônicas por links Markdown convencionais no corpo textual do concept.

*   **`OKF v0.2 Normative Requirement`**: Relações entre concepts devem utilizar links Markdown padrão; o OKF não define sintaxe estrutural própria para links tipados.
*   **`Recommendation`**: Utilizar links relativos ou bundle-relative de forma consistente. O destino do link deve apontar para o arquivo Markdown, por exemplo `[Texto de Exibição](/jurisprudencia/acordao_exemplo.md)` ou `[Texto de Exibição](../temas/tema_exemplo.md)`.
*   **`repo_jur Project Requirement`**: Não confundir `concept_id` com o caminho literal do link: o `concept_id` não possui `.md`, enquanto o link Markdown referencia o arquivo de destino.
*   **`repo_jur Project Requirement`**: A natureza da relação deve ser expressa pela prosa ao redor do link. O texto visível do link pode conter qualquer rótulo humano normal; o que não deve ser criado é um esquema proprietário que codifique um tipo de aresta como sintaxe estrutural obrigatória.
*   **`OKF v0.2 Normative Requirement`**: Links para concepts ainda inexistentes podem ser sintaticamente válidos no bundle. O `repo_jur`, entretanto, pode aplicar validações próprias para sinalizar links não resolvidos sem alterar a semântica do OKF.

---

## 10. Invariantes da Identidade e Estrutura Física

As regras abaixo constituem invariantes estruturais do `repo_jur`:

1.  **Corpus canônico**: `repo_jur/bundle/` é o corpus jurídico canônico. Runtimes, caches, índices e bancos derivados permanecem fora do bundle.
2.  **Zero-Write de retrieval**: mecanismos de busca e retrieval não podem modificar `/bundle/`.
3.  **Isolamento operacional**: `AGENTS.md`, Skills, scripts, configurações de runtime e demais arquivos operacionais não pertencem à árvore do bundle.
4.  **Concepts derivados de PDF**: quando o concept for produzido a partir de PDF, o corpo jurídico preserva o conteúdo literal definido pela pipeline e os marcadores físicos `[[Pág. N]]` quando aplicáveis. Concepts com exatamente 1 PDF usam `repo_jur_pdf_hash`; concepts com 2 ou mais PDFs usam `repo_jur_pdf_hashes`, conforme o Legal OKF Profile v1.1.
5.  **Concepts abstratos ou sintéticos**: podem conter conteúdo jurídico produzido ou curado segundo seu perfil, sem páginas artificiais e sem `repo_jur_pdf_hash`/`repo_jur_pdf_hashes` quando não houver PDF de origem.
6.  **Metadados técnicos da conversão**: método de OCR, confiança, warnings e demais métricas operacionais permanecem no JSON técnico da Fase 1 e não devem ser duplicados no frontmatter canônico.
7.  **Não-fragmentação para retrieval**: o bundle não deve ser fisicamente reestruturado ou dividido apenas para atender limitações de contexto, indexadores ou estratégias de RAG.
8.  **Chunking derivado**: chunks, quando existirem, são dados derivados e reconstruíveis fora de `/bundle/`. Este documento não determina em qual etapa operacional o chunking ocorre.
9.  **Neutralidade tecnológica**: a estrutura canônica não depende de RAG, embeddings, banco vetorial, grafos, MCP ou outro mecanismo específico de retrieval.

---

## Apêndice A: Exemplos Abstratos de Caminhos e Nomes de Arquivos

Os caminhos de diretório e nomes de arquivo estruturados a seguir representam aplicações práticas fictícias baseadas nos padrões determinísticos estabelecidos por esta especificação, não correspondendo a processos, leis ou decisões reais:

### A.1 Exemplo de Conceito de Legislação
*   **Tipo do conceito**: `Legislacao`
*   **Caminho físico no repositório**: `repo_jur/bundle/legislacao/lei_99999_2026.md`
*   **Canonical OKF Concept ID**: `legislacao/lei_99999_2026`
*   **Descrição**: Representa o texto literal e frontmatter de uma lei fictícia número 99.999 sancionada no ano de 2026.

### A.2 Exemplo de Conceito de Jurisprudência (Acórdão Derivado de PDF)
*   **Tipo do conceito**: `Jurisprudencia`
*   **Caminho físico no repositório**: `repo_jur/bundle/jurisprudencia/acordao_stf_re_888888.md`
*   **Canonical OKF Concept ID**: `jurisprudencia/acordao_stf_re_888888`
*   **Descrição**: Representa o inteiro teor e metadados de proveniência do acórdão do Recurso Extraordinário (RE) número 888.888 do STF, convertido a partir de arquivo PDF oficial de evidência com hash de bytes calculado.

### A.3 Exemplo de `TemaJuridico` abstrato
*   **Tipo do concept**: `TemaJuridico`
*   **Caminho físico no repositório**: `repo_jur/bundle/temas/<slug_do_titulo>.md`
*   **Canonical OKF Concept ID**: `temas/<slug_do_titulo>`
*   **Descrição**: Representa um conceito jurídico abstrato sem tribunal ou número oficial. Não recebe campos físicos de PDF nem marcadores de página quando não houver PDF de origem.

### A.4 Exemplo de Conceito de Precedente Vinculante
*   **Tipo do conceito**: `PrecedenteVinculante`
*   **Caminho físico no repositório**: `repo_jur/bundle/precedentes/sumula_vinculante_stf_55.md`
*   **Canonical OKF Concept ID**: `precedentes/sumula_vinculante_stf_55`
*   **Descrição**: Representa o verbete e ementa resumida da Súmula Vinculante número 55 do STF.

### A.5 Exemplo de Concept com Múltiplos PDFs
*   **Tipo do concept**: qualquer tipo jurídico aplicável.
*   **Caminho físico**: determinado normalmente pelas regras de nomenclatura do tipo.
*   **Canonical OKF Concept ID**: continua derivado apenas do caminho físico do Markdown.
*   **Proveniência**: cada PDF aparece em `sources` com `id`; `repo_jur_pdf_hashes` mapeia cada `sources[].id` de PDF ao SHA-256 correspondente.
*   **Regra estrutural**: a existência de múltiplos PDFs não cria subdiretório especial, concept auxiliar, novo `concept_id` ou fragmentação física obrigatória.

---

### Alterações controladas v1.3

*   **Decisões incorporadas:** `decision-memo-duplicate-act-handling-v1.0-FROZEN.md` e `decision-memo-stable-concept-identity-v1.0-FROZEN.md`.
*   **Estado:** Duplicate Act Handling = CLOSED.
*   **Princípio:** consolidação automática somente quando equivalência lógica/material for segura; ambiguidade exige revisão humana.
*   **Sem novo schema:** não cria stable ID, campo de versão ou sufixo `_v2` canônico.

**Status de Maturidade do Documento:** **FROZEN**
