# PERFIL DE METADADOS OKF JURÍDICO (legal-okf-profile-v1.3)
**Versão:** 1.3 (Especificação de Schema — atualização controlada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Foco:** Definição dos campos YAML de metadados aplicados aos concept documents do repositório canônico `repo_jur/bundle/`.

---

## 1. OKF v0.2 Base Fields (Campos Base do Padrão)

Esta seção define as chaves de metadados padronizadas pela especificação oficial do **Open Knowledge Format (OKF) v0.2**. Toda a semântica nativa do formato é rigorosamente preservada.

### 1.1 type
*   **Chave YAML:** `type`
*   **Finalidade:** Identificar a classe lógica ou tipo do documento de conceito para fins de visualização, roteamento, filtragem e renderização por sistemas consumidores [56, 59].
*   **Tipo de Dado:** String (curta, case-sensitive).
*   **Obrigatoriedade:** `OKF v0.2 Normative Requirement — Mandatory` [59, 83].
*   **Concepts Aplicáveis:** Todos os conceitos do bundle [59, 83].
*   **Responsabilidade:** **producer-owned** (Injetado automaticamente pelo compilador).
*   **Retrieval-Relevant:** Sim (Permite filtragem e roteamento de especialistas na busca) [59].
*   **Regra de Validação OKF:** Não pode ser nulo ou vazio [83]. O OKF não define taxonomia central de tipos e consumidores devem tolerar tipos desconhecidos.
*   **Regra `repo_jur`:** Neste perfil, os tipos jurídicos atualmente definidos pelo projeto são `Legislacao`, `Jurisprudencia`, `TemaJuridico` e `PrecedenteVinculante`. Esta enumeração é uma política do `repo_jur`, não uma restrição normativa do OKF.
*   **Fonte:** `SPEC.md` §4.1 [59], `especificacao-tecnica-fase2-v4.md` §1.1 [197].

### 1.2 title
*   **Chave YAML:** `title`
*   **Finalidade:** Nome legível por humanos para exibição do conceito em painéis de interface, listas e grafos [36, 60].
*   **Tipo de Dado:** String.
*   **Obrigatoriedade:** `OKF v0.2 Normative Requirement — Recommended` (Na sua ausência, o consumidor deriva o título do filename do conceito) [60].
*   **Concepts Aplicáveis:** Todos os conceitos [60].
*   **Responsabilidade:** **producer-owned** / **human-owned** (O Produtor OKF pode sugerir deterministicamente; revisores humanos podem customizar).
*   **Retrieval-Relevant:** Sim. O contrato apenas declara o campo como relevante para retrieval; qualquer estratégia de boost, ponderação ou ranking pertence à implementação do mecanismo de busca.
*   **Fonte:** `SPEC.md` §4.1 [60], `especificacao-tecnica-fase2-v4.md` §1.2 [198].

### 1.3 description
*   **Chave YAML:** `description`
*   **Finalidade:** Fornecer uma ementa descritiva ou resumo de uma única frase sobre o conceito, ideal para snippets de busca e navegação hierárquica [60].
*   **Tipo de Dado:** String.
*   **Obrigatoriedade:** `OKF v0.2 Normative Requirement — Recommended` [60].
*   **Concepts Aplicáveis:** Todos os conceitos [60].
*   **Responsabilidade:** **producer-owned** / **human-owned**. O método de produção do resumo não é prescrito por este perfil.
*   **Retrieval-Relevant:** Sim. O perfil não prescreve busca lexical, vetorial ou qualquer algoritmo de similaridade.
*   **Fonte:** `SPEC.md` §4.1 [60], `especificacao-tecnica-fase2-v4.md` §1.2 [198].

### 1.4 resource
*   **Chave YAML:** `resource`
*   **Finalidade:** URI estável que identifica unicamente o ativo físico ou página de consulta oficial subjacente [60].
*   **Tipo de Dado:** String (URI/URL).
*   **Obrigatoriedade:** `OKF v0.2 Normative Requirement — Recommended` (Omitido para conceitos abstratos que não possuem um correspondente no mundo real) [60, 204].
*   **Concepts Aplicáveis:** Qualquer concept que descreva um ativo subjacente identificável. Deve ser omitido quando o concept representar uma ideia abstrata sem ativo correspondente.
*   **Responsabilidade:** **producer-owned** (URI permanente do Diário Oficial, LexML ou portais de tribunais).
*   **Retrieval-Relevant:** Não.
*   **Fonte:** `SPEC.md` §4.1 [60], `especificacao-tecnica-fase2-v4.md` §2.1 [204].

### 1.5 tags
*   **Chave YAML:** `tags`
*   **Finalidade:** Vetor de termos curtos para categorização transversal de conceitos em múltiplas dimensões [60].
*   **Tipo de Dado:** Lista de Strings.
*   **Obrigatoriedade:** `OKF v0.2 Normative Requirement — Recommended` [60].
*   **Concepts Aplicáveis:** Todos os conceitos [60].
*   **Responsabilidade:** **producer-owned** / **human-owned**.
*   **Retrieval-Relevant:** Sim (Habilita filtros transversais por assuntos no motor de busca).
*   **Fonte:** `SPEC.md` §4.1 [60], `especificacao-tecnica-fase2-v4.md` §1.2 [198].

### 1.6 sources
*   **Chave YAML:** `sources`
*   **Finalidade:** Mapear os materiais externos ou internos dos quais o concept document foi extraído ou derivado, estabelecendo sua proveniência [63]. As fontes podem ser documentos físicos, páginas oficiais, outros concepts ou outros recursos identificáveis.
*   **Tipo de Dado:** Lista de Mappings (Objetos).
*   **Obrigatoriedade:** `repo_jur Project Requirement — Conditional` (Opcional pela norma do OKF; no `repo_jur`, deve estar presente quando o concept for derivado de fontes identificáveis) [63, 204].
*   **Concepts Aplicáveis:** Qualquer tipo de concept quando houver fontes de derivação identificáveis, inclusive `TemaJuridico`. A presença de `sources` não implica, por si só, origem em PDF.
*   **Responsabilidade:** **producer-owned** (preenchido a partir da proveniência disponível no pipeline ou na curadoria).
*   **Retrieval-Relevant:** Não como filtro obrigatório. Quando existir, deve ser preservado para proveniência e atribuição conforme o Retrieval Contract.
*   **Fonte:** `SPEC.md` §5.1 [63], `especificacao-tecnica-fase2-v4.md` §2.1 [204].

#### Subcampos de `sources`:
*   **`resource`**: `OKF v0.2 Normative Requirement — Mandatory` dentro de cada entrada de `sources` [42, 142]. Identifica a fonte por URL absoluta, caminho relativo ao bundle, caminho relativo ao concept ou outro descritor de escopo admitido pelo OKF. Para concepts derivados de PDF, deve identificar a evidência de origem utilizada pelo pipeline segundo o contrato de ingestão do `repo_jur`.
*   **`id`**: `OKF v0.2 Normative Requirement — Optional`; deve ser usado quando o corpo atribuir claims específicos à fonte. Funciona como chave estável de associação (*join key*) para atribuição por notas de rodapé Markdown [64, 67]. **Regra `repo_jur` adicional:** torna-se `Conditional Mandatory` para cada fonte PDF quando o concept derivar de **2 ou mais PDFs**, porque o `id` é a chave usada por `repo_jur_pdf_hashes`.
*   **`title`**: `OKF v0.2 Normative Requirement — Optional` [64]. String com o nome descritivo amigável da fonte.
*   **`author`**: `OKF v0.2 Normative Requirement — Optional` [65]. String (Actor) que identifica quem ou qual entidade produziu a fonte original (ex: `process:stf` ou `human:relator`). **Regra estrita:** Representa o autor da fonte original; nunca deve registrar o agente ou humano que realizou o download.
*   **`last_modified`**: `OKF v0.2 Normative Requirement — Optional` [65]. Date String (YYYY-MM-DD). Registra a data de última modificação da própria fonte quando esse dado for conhecido. **Regra estrita:** Não representa data de coleta, download ou ingestão; se a data de modificação da fonte não for conhecida, o campo deve ser omitido.

### 1.7 generated
*   **Chave YAML:** `generated`
*   **Finalidade:** Registrar a proveniência lógica da criação do concept document, identificando quem escreveu o arquivo e em qual momento [68].
*   **Tipo de Dado:** Mapping.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` (Opcional no OKF, mas exigido em repo_jur para rastrear a atividade dos geradores) [68, 204].
*   **Concepts Aplicáveis:** Todos os conceitos do bundle [204].
*   **Responsabilidade:** **producer-owned** [204].
*   **Retrieval-Relevant:** Não.
*   **Fonte:** `SPEC.md` §5.2 [68], `especificacao-tecnica-fase2-v4.md` §2.1 [204].

#### Subcampos de `generated`:
*   **`by`**: `OKF v0.2 Normative Requirement — Mandatory` dentro de `generated` [46, 142]. String (Actor). **Regra estrita:** Deve ser obrigatoriamente preenchido com a assinatura identificadora do Produtor no padrão `repo_jur_producer/<version>` (ex: `repo_jur_producer/1.0.0`) [51, 146].
*   **`at`**: `OKF v0.2 Normative Requirement — Recommended` [68]. Datetime String (ISO 8601) que registra a última alteração significativa do conteúdo atual do concept. Não representa simplesmente a criação física ou a gravação do arquivo Markdown.

### 1.8 verified
*   **Chave YAML:** `verified`
*   **Finalidade:** Registrar os eventos de auditoria e validação factual e conceitual do concept document, atestando sua integridade [68].
*   **Tipo de Dado:** Lista de Mappings (ou mapping simplificado se houver apenas um validador, convertido internamente pelo leitor) [68, 144].
*   **Obrigatoriedade:** `repo_jur Project Requirement — Conditional` (Registrado apenas se ocorrer um evento real e documentado de revisão jurídica. A ausência do campo indica que o documento permanece semanticamente como `unverified` no OKF) [204]. **Regra estrita:** Jamais simular ou inventar registros verified fictícios apenas para preencher schemas ou satisfazer validadores. O Produtor OKF `repo_jur_producer` **não** pode assinar como verified a menos que execute um teste real independente de conformidade ou integridade factual sobre o corpo.
*   **Concepts Aplicáveis:** Todos os conceitos [204].
*   **Responsabilidade:** **human-owned** (Preferencialmente assinado por advogados/revisores reais no padrão `human:<id>`) / **derived** (ou por processos reais em `process:<id>`).
*   **Retrieval-Relevant:** Não como filtro canônico. Consumidores podem derivar `trust_tier` a partir de `verified`, conforme o OKF e o Retrieval Contract.
*   **Fonte:** `SPEC.md` §5.2 [68], `especificacao-tecnica-fase2-v4.md` §2.1 [204].

#### Subcampos de `verified`:
*   **`by`**: String (Actor). Identificação de quem verificou (ex: `human:advogado_revisor` ou `process:integrity_check`) [51, 146].
*   **`at`**: Datetime String (ISO 8601). Momento em que a verificação ocorreu [68].

### 1.9 status
*   **Chave YAML:** `status`
*   **Finalidade:** Expressar a fase atual do ciclo de vida e estabilidade do concept document [47].
*   **Tipo de Dado:** String. Valores permitidos: `draft`, `stable`, `deprecated` [47].
*   **Obrigatoriedade:** `OKF v0.2 Normative Requirement — Optional` (Sua ausência é interpretada semanticamente como `status: stable` pelas regras do OKF) [47, 70].
*   **Concepts Aplicáveis:** Todos os conceitos.
*   **Responsabilidade:** **human-owned** (Alterado sob a discrição e revisão do advogado).
*   **Retrieval-Relevant:** Sim. O campo pode ser utilizado por filtros ou políticas de ordenação, mas este perfil não determina demotes, boosts ou regras específicas de ranking.
*   **Fonte:** `SPEC.md` §5.4 [47, 70], `especificacao-tecnica-fase2-v4.md` §1.5 [146].

### 1.10 stale_after
*   **Chave YAML:** `stale_after`
*   **Finalidade:** Determinar uma data limite absoluta após a qual as informações do conceito são consideradas potencialmente desatualizadas ou sujeitas a reavaliação [48].
*   **Tipo de Dado:** Date String (YYYY-MM-DD).
*   **Obrigatoriedade:** `OKF v0.2 Normative Requirement — Optional` (Se a data atual >= `stale_after`, o conceito é considerado `stale`, isto é, potencialmente desatualizado) [48].
*   **Concepts Aplicáveis:** Todos os conceitos [48].
*   **Responsabilidade:** **human-owned** / **producer-owned** (Definido em comitê jurídico ou regras de vigência).
*   **Retrieval-Relevant:** Não por padrão. Consumidores podem derivar sinalização de desatualização a partir desse campo sem alterar o valor canônico.
*   **Fonte:** `SPEC.md` §5.5 [48, 70], `especificacao-tecnica-fase2-v4.md` §1.5 [146].

---

## 2. Universal `repo_jur` Fields (Campos Universais do Projeto)

Campos customizados de nível superior adicionados sob as regras de extensibilidade do OKF v0.2. Sua aplicabilidade pode ser universal ou condicional conforme a origem e a natureza do concept.

### 2.1 repo_jur_pdf_hash
*   **Chave YAML:** `repo_jur_pdf_hash`
*   **Finalidade:** Registrar o hash SHA-256 calculado diretamente sobre os bytes do PDF bruto efetivamente utilizado pelo pipeline quando houver **exatamente uma evidência PDF de origem**.
*   **Tipo de Dado:** String hexadecimal em caixa baixa, 64 caracteres.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Conditional Mandatory`: obrigatório quando o concept for derivado de exatamente **1 PDF**; deve ser omitido quando não houver PDF de origem ou quando houver **2 ou mais PDFs**.
*   **Concepts Aplicáveis:** Qualquer tipo de concept quando derivado de exatamente um PDF. A aplicabilidade é determinada pela origem física, não pela classe jurídica.
*   **Responsabilidade:** **producer-owned**.
*   **Retrieval-Relevant:** Não como filtro. Deve ser preservado na cadeia de proveniência física.
*   **Regra de Validação:** SHA-256 hexadecimal válido de 64 caracteres em caixa baixa. Identifica os bytes da evidência, não constitui identidade lógica do concept e não prova autenticidade jurídica.
*   **Exclusividade:** `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` são mutuamente exclusivos.
*   **Fonte:** `decision-memo-pdf-source-cardinality-v1.0` (FROZEN), `especificacao-tecnica-fase2-v4.md` §2.1 [204], `repo_jur.md` §9 [185].

### 2.2 repo_jur_pdf_hashes
*   **Chave YAML:** `repo_jur_pdf_hashes`
*   **Finalidade:** Preservar a integridade física individual de múltiplas evidências PDF associadas ao mesmo concept, mapeando `sources[].id` → SHA-256.
*   **Tipo de Dado:** Mapping `String -> String`, onde cada chave é um `sources[].id` de uma fonte PDF e cada valor é um SHA-256 hexadecimal em caixa baixa de 64 caracteres.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Conditional Mandatory`: obrigatório quando o concept for derivado de **2 ou mais PDFs**; deve ser omitido quando houver zero ou exatamente um PDF de origem.
*   **Concepts Aplicáveis:** Qualquer tipo de concept quando derivado de múltiplas evidências PDF.
*   **Responsabilidade:** **producer-owned**.
*   **Retrieval-Relevant:** Não como filtro. Deve ser preservado na cadeia de proveniência física.
*   **Regras de Validação:**
    1. `repo_jur_pdf_hashes` e `repo_jur_pdf_hash` são mutuamente exclusivos.
    2. Toda fonte PDF de um concept multi-PDF deve possuir `sources[].id`.
    3. Cada chave de `repo_jur_pdf_hashes` deve corresponder exatamente ao `id` de uma fonte PDF presente em `sources`.
    4. Cada fonte PDF presente em `sources` deve possuir exatamente uma entrada correspondente em `repo_jur_pdf_hashes`.
    5. Fontes não-PDF podem permanecer em `sources`, mas não devem aparecer em `repo_jur_pdf_hashes`.
    6. O mesmo SHA-256 pode aparecer em múltiplos concepts quando a mesma evidência PDF sustentar mais de um concept.
    7. Nenhum hash identifica, por si só, o concept nem prova autenticidade jurídica.
*   **Fonte:** `decision-memo-pdf-source-cardinality-v1.0` (FROZEN).

### 2.3 repo_jur_verification_history
*   **Chave YAML:** `repo_jur_verification_history`
*   **Finalidade:** Preservar eventos reais que existiram em `verified` e posteriormente deixaram de ser aplicáveis ao conteúdo atual do concept.
*   **Tipo de Dado:** Lista de Mappings.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Conditional`: omitido quando não houver eventos históricos de invalidação.
*   **Concepts Aplicáveis:** Todos os concepts.
*   **Responsabilidade:** **Producer-Owned archival structure**. O Produtor mantém a estrutura e o merge deterministicamente; `by` e `at` preservam o Actor e o instante do evento original; `invalidated_by` identifica o Actor que decidiu ou autorizou a invalidação.
*   **Retrieval-Relevant:** Apenas auditoria; nunca para derivação de confiança, filtro ou ranking canônico.
*   **Regra de Confiança:** `repo_jur_verification_history` nunca conta como `verified` e nunca eleva `trust_tier`.
*   **Idempotência:** o par original `(by, at)` pode aparecer no histórico do mesmo concept no máximo uma vez.
*   **Fonte:** `decision-memo-verification-history-schema-v1.0-FROZEN.md`.

#### Subcampos de `repo_jur_verification_history`
*   **`by`**: obrigatório. String (Actor), copiada exatamente de `verified[].by`.
*   **`at`**: obrigatório. Datetime String (ISO 8601), copiada exatamente de `verified[].at`.
*   **`invalidated_at`**: obrigatório. Datetime String (ISO 8601) do momento em que o evento deixou de ser aplicável ao conteúdo atual.
*   **`invalidated_by`**: obrigatório. String (Actor) que tomou ou autorizou a decisão de invalidação. O software que apenas escreve o arquivo não se torna automaticamente esse Actor.
*   **`reason`**: obrigatório. Valores permitidos:
    * `material_content_change`
    * `material_provenance_change`
    * `material_scope_change`
    * `manual_invalidation`
*   **Hash histórico:** nenhum `evidence_pdf_hash` é obrigatório nesta baseline. Hash/cardinalidade/path não constituem isoladamente prova de materialidade nem escopo de verificação.

### 2.4 Metadados técnicos de conversão
*   **repo_jur Project Requirement:** Método de conversão, uso de OCR, confiança, warnings e demais métricas operacionais da Fase 1 **não pertencem ao frontmatter canônico do concept**. Esses dados permanecem no JSON técnico da Fase 1 e não devem ser duplicados em chaves `repo_jur_*` do bundle.

---

## 3. Legislation Profile (Perfil de Legislação)

Campos específicos aplicáveis a leis, decretos, portarias, medidas provisórias e demais atos normativos do poder público.

### 3.1 repo_jur_lei_numero
*   **Chave YAML:** `repo_jur_lei_numero`
*   **Finalidade:** Registrar o número oficial de identificação da norma legal (ex: `13869`) [205].
*   **Tipo de Dado:** String.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` para atos legislativos numerados.
*   **Concepts Aplicáveis:** `Legislacao` [205].
*   **Responsabilidade:** **producer-owned**. O método de extração ou validação não é prescrito por este perfil.
*   **Retrieval-Relevant:** Sim (Configurado como retrieval-relevant, permitindo que consultas por número localizem a lei correspondente).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-A [205].

### 3.2 repo_jur_lei_ano
*   **Chave YAML:** `repo_jur_lei_ano`
*   **Finalidade:** Registrar o ano oficial de promulgação ou assinatura do ato normativo [205].
*   **Tipo de Dado:** Integer.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` para atos legislativos numerados.
*   **Concepts Aplicáveis:** `Legislacao` [205].
*   **Responsabilidade:** **producer-owned**.
*   **Retrieval-Relevant:** Sim (retrieval-relevant para indexação e ordenação de buscas por período temporal).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-A [205].

### 3.3 repo_jur_lei_esfera
*   **Chave YAML:** `repo_jur_lei_esfera`
*   **Finalidade:** Identificar a esfera governamental de vigência e aplicação da lei [205].
*   **Tipo de Dado:** String. Valores permitidos: `federal`, `estadual`, `distrital`, `municipal`.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` [205].
*   **Concepts Aplicáveis:** `Legislacao` [205].
*   **Responsabilidade:** **producer-owned**.
*   **Retrieval-Relevant:** Sim (retrieval-relevant, ideal para filtros lógicos de competência territorial).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-A [205].

### 3.4 repo_jur_lei_tipo
*   **Chave YAML:** `repo_jur_lei_tipo`
*   **Finalidade:** Registrar a espécie normativa da lei [205].
*   **Tipo de Dado:** String. Valores sugeridos: `constituicao`, `complementar`, `ordinaria`, `decreto`, `portaria`, `medida_provisoria`.
*   **Obrigatoriedade:** `Recommendation` (Recomendado).
*   **Concepts Aplicáveis:** `Legislacao` [205].
*   **Responsabilidade:** **producer-owned** / **human-owned**.
*   **Retrieval-Relevant:** Sim (permite filtragem pela espécie normativa).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-A [205].

---

## 4. Jurisprudence Profile (Perfil de Jurisprudência e Precedentes)

Campos específicos para decisões judiciais, acórdãos, súmulas, enunciados e precedentes vinculantes de tribunais do Poder Judiciário.

### 4.1 repo_jur_processo_numero
*   **Chave YAML:** `repo_jur_processo_numero`
*   **Finalidade:** Registrar o número único de identificação do processo judicial no padrão nacional estabelecido pelo CNJ [206].
*   **Tipo de Dado:** String.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` para acórdãos e decisões processuais [206].
*   **Concepts Aplicáveis:** `Jurisprudencia` [206].
*   **Responsabilidade:** **producer-owned** (Extraído e padronizado deterministicamente).
*   **Retrieval-Relevant:** Sim (retrieval-relevant para busca direta por número de processo).
*   **Regra de Validação:** Deve seguir preferencialmente a máscara CNJ: `NNNNNNN-DD.AAAA.J.TR.OOOO`.
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-B [206].

### 4.2 repo_jur_tribunal
*   **Chave YAML:** `repo_jur_tribunal`
*   **Finalidade:** Identificar a sigla do tribunal emissor ou responsável pelo julgado, precedente ou tema oficial [206, 207, 208].
*   **Tipo de Dado:** String (Maiúsculas, ex: `STF`, `STJ`, `TJSP`, `TRF1`).
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` para `Jurisprudencia` e `PrecedenteVinculante`; `Conditional Mandatory` para `TemaJuridico` quando representar tema oficial de tribunal. Deve ser omitido em conceitos abstratos sem tribunal emissor.
*   **Concepts Aplicáveis:** `Jurisprudencia`, `PrecedenteVinculante` e `TemaJuridico` quando houver tribunal emissor ou responsável [206, 207, 208].
*   **Responsabilidade:** **producer-owned**. O método de identificação não é prescrito por este perfil.
*   **Retrieval-Relevant:** Sim (permite filtragem por tribunal sem criar chaves diferentes para a mesma semântica).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §§2.1-B, 2.1-C e 2.1-D [206, 207, 208].

### 4.3 repo_jur_relator
*   **Chave YAML:** `repo_jur_relator`
*   **Finalidade:** Registrar o nome do magistrado relator responsável pela redação do acórdão [206].
*   **Tipo de Dado:** String.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` para decisões colegiadas [206].
*   **Concepts Aplicáveis:** `Jurisprudencia` [206].
*   **Responsabilidade:** **producer-owned**. Deve refletir o dado identificável na fonte; o método de extração não é prescrito por este perfil.
*   **Retrieval-Relevant:** Sim (retrieval-relevant, permitindo isolar a linha decisória de determinados relatores).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-B [206].

### 4.4 repo_jur_data_julgamento
*   **Chave YAML:** `repo_jur_data_julgamento`
*   **Finalidade:** Registrar a data oficial do julgamento da decisão, conforme informada pela fonte [206]. Não deve ser usada para representar data de assinatura, publicação ou outro evento processual distinto.
*   **Tipo de Dado:** Date String (YYYY-MM-DD).
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` [206].
*   **Concepts Aplicáveis:** `Jurisprudencia` [206].
*   **Responsabilidade:** **producer-owned**.
*   **Retrieval-Relevant:** Sim (retrieval-relevant para filtros temporais de evolução da jurisprudência).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-B [206].

### 4.5 repo_jur_ramo_direito
*   **Chave YAML:** `repo_jur_ramo_direito`
*   **Finalidade:** Categorizar a matéria ou ramo do direito correspondente ao julgado [206].
*   **Tipo de Dado:** String. Valores sugeridos: `civil`, `penal`, `tributario`, `trabalhista`, `administrativo`, `constitucional`.
*   **Obrigatoriedade:** `Recommendation` (Recomendado) [206].
*   **Concepts Aplicáveis:** `Jurisprudencia`, `PrecedenteVinculante` [206, 208].
*   **Responsabilidade:** **producer-owned** / **human-owned**. A classificação deve ser sustentada pelo conteúdo ou pela curadoria; o método não é prescrito por este perfil.
*   **Retrieval-Relevant:** Sim (retrieval-relevant para segmentação temática da base jurídica).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-B [206].

### 4.6 repo_jur_precedente_numero
*   **Chave YAML:** `repo_jur_precedente_numero`
*   **Finalidade:** Registrar o número oficial do enunciado da súmula ou tese repetitiva vinculante [208].
*   **Tipo de Dado:** String.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` para enunciados de súmulas ou teses vinculantes numeradas.
*   **Concepts Aplicáveis:** `PrecedenteVinculante` [208].
*   **Responsabilidade:** **producer-owned**.
*   **Retrieval-Relevant:** Sim (retrieval-relevant para busca direta por número de verbete).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-D [208].

### 4.7 repo_jur_precedente_status
*   **Chave YAML:** `repo_jur_precedente_status`
*   **Finalidade:** Registrar o estado de vigência do enunciado e da súmula [208].
*   **Tipo de Dado:** String. Valores permitidos: `ativo`, `cancelado`, `revisado`.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Mandatory` para precedentes vinculantes [208].
*   **Concepts Aplicáveis:** `PrecedenteVinculante` [208].
*   **Responsabilidade:** **human-owned** / **producer-owned** (Alterado deterministicamente na ocorrência de ato de cancelamento ou revisão oficial).
*   **Retrieval-Relevant:** Sim. Permite filtrar ou sinalizar a situação jurídica do precedente; este perfil não define política automática de exclusão, ranking ou citação.
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-D [208].

---

## 5. Legal Theme / Doctrinal Concept Profile (Perfil de Temas e Conceitos Abstratos)

Destinado a concepts jurídicos conceituais, sintéticos ou abstratos, incluindo estudos doutrinários e, quando aplicável, temas oficiais numerados de tribunais. Um `TemaJuridico` pode possuir `sources` quando for derivado de materiais identificáveis, sem que isso implique origem em PDF.

*   **repo_jur Project Requirement**: Campos de proveniência física de PDF, como `repo_jur_pdf_hash`, `repo_jur_pdf_hashes` e marcadores `[[Pág. N]]`, somente podem existir quando o concept tiver sido efetivamente derivado de PDF. Não devem ser criados artificialmente para concepts abstratos. A escolha entre hash singular e plural depende da quantidade de evidências PDF de origem.

### 5.1 repo_jur_tema_numero
*   **Chave YAML:** `repo_jur_tema_numero`
*   **Finalidade:** Identificar o número oficial atribuído a um tema de repercussão geral, recurso repetitivo ou outra série oficial numerada [207].
*   **Tipo de Dado:** String.
*   **Obrigatoriedade:** `repo_jur Project Requirement — Conditional Mandatory`: obrigatório somente quando o `TemaJuridico` representar um tema oficial numerado; omitido em conceitos doutrinários ou abstratos sem numeração oficial.
*   **Concepts Aplicáveis:** `TemaJuridico` quando representar tema oficial numerado [207].
*   **Responsabilidade:** **producer-owned**.
*   **Retrieval-Relevant:** Sim (retrieval-relevant para conexões de busca de teses).
*   **Fonte:** `especificacao-tecnica-fase2-v4.md` §2.1-C [207].

### 5.2 Texto da tese ou conteúdo jurídico
*   **repo_jur Project Requirement:** O texto literal de tese fixada, enunciado, explicação doutrinária ou outro conteúdo jurídico substantivo deve permanecer no **corpo Markdown** do concept, e não ser duplicado em uma chave YAML como `repo_jur_tese_fixada`.
*   **Retrieval-Relevant:** O corpo textual é recuperável conforme o Retrieval Contract. O frontmatter deve identificar e classificar o concept, não duplicar seu conteúdo jurídico principal.

---

## 6. Exemplos YAML Abstratos e Não Normativos

Os exemplos a seguir ilustram a aplicação dos perfis usando **placeholders explícitos**. Eles não representam documentos, processos, revisões ou eventos de verificação reais.

### 6.1 Exemplo 1: Legislação (norma numerada derivada de PDF)
```yaml
---
type: Legislacao
title: "<official-title>"
description: "<one-sentence-description>"
resource: "<official-resource-uri>"
tags:
  - "<tag-1>"
  - "<tag-2>"
sources:
  - id: "source_pdf"
    resource: "<archived-source-resource>"
    title: "<source-title>"
    last_modified: "<source-last-modified-date>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
repo_jur_pdf_hash: "<sha256-64-hex>"
repo_jur_lei_numero: "<norm-number>"
repo_jur_lei_ano: <year>
repo_jur_lei_esfera: "<federal|estadual|distrital|municipal>"
repo_jur_lei_tipo: "<normative-act-type>"
---
```

### 6.2 Exemplo 2: Jurisprudência (acórdão derivado de PDF)
```yaml
---
type: Jurisprudencia
title: "<decision-title>"
description: "<one-sentence-description>"
resource: "<official-decision-uri>"
sources:
  - id: "source_pdf"
    resource: "<archived-source-resource>"
    title: "<source-title>"
    author: "process:<source-producer-id>"
    last_modified: "<source-last-modified-date>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
status: stable
repo_jur_pdf_hash: "<sha256-64-hex>"
repo_jur_processo_numero: "<process-number>"
repo_jur_tribunal: "<tribunal>"
repo_jur_relator: "<relator>"
repo_jur_data_julgamento: "<yyyy-mm-dd>"
repo_jur_ramo_direito: "<legal-branch>"
---
```

> `verified` foi deliberadamente omitido: ele só deve existir após um evento real e documentado de verificação.

### 6.3 Exemplo 3: Tema jurídico abstrato sem PDF
```yaml
---
type: TemaJuridico
title: "<concept-title>"
description: "<one-sentence-description>"
tags:
  - "<tag-1>"
  - "<tag-2>"
sources:
  - id: "source_a"
    resource: "<source-resource-uri>"
    title: "<source-title>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
status: stable
---
```

> Este exemplo não contém `repo_jur_pdf_hash`, `repo_jur_pdf_hashes`, `page_refs` ou marcadores `[[Pág. N]]`, porque não representa um concept derivado de PDF. Se um `TemaJuridico` representar um tema oficial numerado de tribunal, `repo_jur_tema_numero` e `repo_jur_tribunal` tornam-se obrigatórios conforme as regras condicionais das Seções 4 e 5.


### 6.4 Exemplo 4: Concept derivado de múltiplos PDFs
```yaml
---
type: TemaJuridico
title: "<concept-title>"
description: "<one-sentence-description>"
sources:
  - id: "source_pdf_a"
    resource: "<source-a-resource>"
    title: "<source-a-title>"
  - id: "source_pdf_b"
    resource: "<source-b-resource>"
    title: "<source-b-title>"
  - id: "source_non_pdf"
    resource: "<non-pdf-source-resource>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
repo_jur_pdf_hashes:
  source_pdf_a: "<sha256-64-hex>"
  source_pdf_b: "<sha256-64-hex>"
---
```

> `repo_jur_pdf_hash` foi omitido porque o concept possui múltiplas evidências PDF. A fonte não-PDF permanece em `sources`, mas não aparece em `repo_jur_pdf_hashes`.

### 6.5 Exemplo 5: Histórico de verificação invalidada
```yaml
---
type: Jurisprudencia
title: "<decision-title>"
generated:
  by: "repo_jur_producer/<version>"
  at: "<iso-8601-last-meaningful-change>"
repo_jur_verification_history:
  - by: "human:<reviewer-id>"
    at: "<iso-8601-original-verification-time>"
    invalidated_at: "<iso-8601-invalidation-time>"
    invalidated_by: "process:<materiality-review-process>"
    reason: material_content_change
---
```

> `verified` está omitido porque não existe evento ativo registrado para o conteúdo atual. O histórico não altera o trust tier.

---

## 7. Classificação e Governança das Regras

As decisões e definições descritas neste perfil são de conformidade técnica estrita e governadas sob as seguintes classificações:

*   **OKF v0.2 Normative Requirement (Requisito da Norma):**
    *   Uso obrigatório de bloco frontmatter YAML delimitado por `---` e presença de `type` como o único campo sempre obrigatório do frontmatter [59, 83].
    *   Obrigatoriedade do campo `generated.by` quando a família `generated` for declarada [46, 142].
    *   Uso de strings sintáticas normativas para Actor Convention (`human:`, `process:`, `<producer>/<version>`) [73, 146].
    *   Separação semântica de `generated.by` e `verified[].by` [68].
    *   Preservação semântica e suporte permissivo de unknown keys (como o prefixo `repo_jur_*`) sem causar a rejeição do bundle [61, 84].
*   **repo_jur Project Requirement (Requisito de Negócio do Projeto):**
    *   `generated` é obrigatório para os concepts produzidos pelo pipeline do `repo_jur`; `sources` é obrigatório quando o concept derivar de fontes identificáveis.
    *   Concepts derivados de exatamente 1 PDF usam obrigatoriamente `repo_jur_pdf_hash`.
    *   Concepts derivados de 2 ou mais PDFs usam obrigatoriamente `repo_jur_pdf_hashes`; nesses casos, cada fonte PDF em `sources` deve possuir `id` correspondente ao mapping de hashes.
    *   `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` são mutuamente exclusivos.
    *   SHA-256 identifica os bytes da evidência física; não constitui identidade lógica do concept nem prova autenticidade jurídica.
    *   Obrigação de registrar o Produtor OKF na assinatura `generated.by` utilizando estritamente a string `repo_jur_producer/<version>` [51, 146].
    *   Proibição absoluta de simular verification events fictícios em `verified`, sendo este campo tratado como condicional exclusivo de eventos reais [204].
*   `repo_jur_verification_history` é governado por `decision-memo-verification-history-schema-v1.0-FROZEN.md` e contém apenas eventos reais anteriormente presentes em `verified` que deixaram de ser aplicáveis ao conteúdo atual.
*   A chave histórica nunca participa da derivação de `trust_tier` e não pode ser reativada automaticamente como `verified`.
*   Mudança de SHA-256, cardinalidade ou path não invalida `verified` automaticamente; materialidade deve ser avaliada em relação ao objeto efetivamente verificado.
*   **Recommendation (Recomendação Arquitetural de Design):**
    *   Recomenda-se o preenchimento condicional de `verified` com assinaturas humanas para elevar o conceito ao Trust Tier de *human-reviewed* [47, 51, 146].
    *   Recomenda-se limitar os campos retrieval-relevant estritamente às chaves especificadas neste perfil, impedindo o inchaço e a poluição de índices de busca derivados.
### 7.1 Alteração controlada v1.3
*   **Decisões já incorporadas:** `PDF Source Cardinality`, `Duplicate Act Handling` e `Stable Concept Identity` permanecem CLOSED.
*   **Decisão incorporada nesta versão:** `Verification History Schema` foi encerrada por `decision-memo-verification-history-schema-v1.0-FROZEN.md`.
*   **Mudança de schema:** inclusão formal de `repo_jur_verification_history` como extensão canônica condicional, separada de `verified`.
*   **Ownership:** estrutura arquivística Producer-Owned; `by`/`at` preservam o evento original e `invalidated_by` representa o Actor da invalidação.
*   **Trust:** somente `verified` participa da confiança ativa; histórico nunca eleva `trust_tier`.
*   **Materialidade:** SHA-256, cardinalidade e path isolados não causam invalidação automática.
*   **Stable Concept Identity:** permanece CLOSED; nenhuma identidade persistente adicional é criada.
