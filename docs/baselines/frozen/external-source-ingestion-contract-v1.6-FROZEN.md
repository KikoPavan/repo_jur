# EXTERNAL SOURCE INGESTION CONTRACT (ESIC) v1.6

**Versão:** 1.6 (Baseline — atualização controlada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `legal-okf-profile-v1.3-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `retrieval-contract-v2.4-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md`, `decision-memo-verification-history-schema-v1.0-FROZEN.md`, `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`, `decision-memo-phase1-quality-gate-v1.0-FROZEN.md` e arquitetura consolidada da Fase 2.
**Fonte histórica recuperada:** `Protocolo de Ingestão e Governança de Dados do repo_jur.md`, que contém o **External Source Ingestion Contract (ESIC) v1.1 — Consolidada e Corrigida — READY TO FREEZE**.

---

## 1. Purpose and Scope

Este contrato governa a entrada de fontes externas no `repo_jur`, desde a descoberta e coleta até a incorporação de conhecimento em `repo_jur/bundle/`.

Ele estabelece a fronteira entre coletores externos e o pipeline canônico, a preservação da evidência física, o handoff de proveniência, o preflight, a conversão física da Fase 1, o handoff ao Produtor OKF e as condições para incorporação.

**[Existing FROZEN Requirement]** `repo_jur/bundle/` é o corpus jurídico canônico. Sistemas externos não podem alterar diretamente seu conteúdo.

**[Recovered Historical Requirement]** A descoberta ou o download de uma fonte não equivale à incorporação dessa fonte no corpus.

**Fora de escopo:** escolha de RAG, embeddings, banco vetorial, MCP, mecanismo de busca, reranker ou tecnologia de retrieval.

---

## 2. Trust Boundary

### 2.1 Sistemas externos

O `juridico-cli` e agentes/coletores de fontes operam fora da fronteira de escrita do `repo_jur`. Eles podem localizar fontes, baixar evidências e preparar um handoff, mas não possuem autoridade para publicar concepts canônicos.

### 2.2 Zero direct write

**[Existing FROZEN Requirement]** Nenhum coletor, agente externo, mecanismo de retrieval ou runtime cognitivo pode criar, editar ou excluir diretamente arquivos em `repo_jur/bundle/`.

A única rota de incorporação é:

```text
fonte externa
    ↓
handoff
    ↓
preflight repo_jur
    ↓
Fase 1
    ↓
Produtor OKF
    ↓
validação
    ↓
publicação atômica em repo_jur/bundle/
```

### 2.3 Autoridade do handoff

O handoff externo fornece **evidência e proveniência candidata**. Ele não fornece Markdown canônico, frontmatter OKF autoritativo, `verified` ou decisões finais de classificação.

---

## 3. Ingestion States

Os estados de ingestão são independentes do campo OKF `status`.

```text
Discovered → Candidate → Selected → Accepted → Incorporated
```

### 3.1 Discovered

**[Recovered Historical Requirement]** A fonte foi localizada, mas ainda pode existir apenas como referência externa, URL, identificador oficial ou outro locator.

### 3.2 Candidate

**[Recovered Historical Requirement]** A evidência foi obtida pelo coletor e permanece em staging/sandbox externo, fora do corpus canônico.

### 3.3 Selected

**[Recovered Historical Requirement]** O candidato foi explicitamente selecionado para tentativa de incorporação e o handoff é preparado.

A seleção deve ser um evento de governança identificável. Este contrato não transforma descoberta automática em autorização automática para escrever no bundle.

### 3.4 Accepted

**[Recovered Historical Requirement atualizado]** O handoff passou pelo preflight e a evidência original foi aceita para preservação/processamento.

Para PDFs, os bytes originais aceitos devem ser preservados em **Object Storage externo**, com referência estável e resolvível para a evidência efetivamente utilizada pelo pipeline.

### 3.5 Incorporated

O estado `Incorporated` somente é alcançado quando a Fase 1 e o Produtor OKF terminam com sucesso, as validações aplicáveis são satisfeitas e o concept é publicado atomicamente em `repo_jur/bundle/`.

`Incorporated` não implica `verified` e não determina automaticamente o campo OKF `status`.

---

## 4. Source Handoff Contract

Para a rota física de ingestão de PDF, o handoff deve conter as propriedades lógicas abaixo. **Os nomes apresentados são rótulos conceituais do contrato e não congelam a serialização, formato de payload, protocolo ou nomes finais de campos de uma API/CLI; isso permanece em `Ingress Transport Protocol`.**

1. **`source_bytes`** — bytes brutos e intactos do PDF obtido.
2. **`source_origin`** — locator/origem externa de onde a evidência foi obtida; quando a fonte for Web, registrar a URL oficial disponível.
3. **`retrieved_at`** — instante de obtenção/download, para auditoria operacional.
4. **`collector`** — identificação do agente, processo ou pessoa que realizou a coleta.
5. **`last_modified`**, quando conhecido — data de última modificação **da própria fonte**, não a data de download.
6. **hints opcionais de domínio** — por exemplo, número de processo ou identificador jurídico descoberto pelo coletor; são candidatos e não valores canônicos por autoridade do coletor.

### 4.1 Regras de mapeamento

**`collector` ≠ `sources[].author`.** O collector identifica quem coletou. `sources[].author`, quando usado, identifica quem ou qual entidade produziu a fonte original.

**`retrieved_at` ≠ `sources[].last_modified`.** A data de obtenção nunca deve ser reutilizada como data de modificação da fonte.

**`source_origin` não é automaticamente `sources[].resource`.** Após preservação, `sources[].resource` deve identificar de forma estável e resolvível a evidência efetivamente utilizada pelo pipeline, conforme o Legal OKF Profile e a decisão de cardinalidade. O locator original continua sendo proveniência de coleta; os dois valores somente coincidem quando realmente identificarem a mesma evidência preservada de forma confiável.

---

## 4. Ingress Transport Protocol — CLOSED

**Decision Status — CLOSED:** governado por `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`.

### 4.1 Protocolo oficial

O transporte oficial inicial é o **Ingress Transport Protocol v1 (ITP/1.0)**.

O protocolo separa:

1. **Envelope Format** — ZIP versionado;
2. **Delivery Channel** — filesystem ingress inbox local e configurável;
3. **Ingress State** — estado operacional de transporte/retry;
4. **Canonical Ingestion Lifecycle** — estados ESIC `Discovered → Candidate → Selected → Accepted → Incorporated`.

Essas dimensões não são equivalentes.

### 4.2 Envelope ITP/1.0

Cada envelope contém exatamente:

```text
<handoff>.zip
├── manifest.json
└── evidence.pdf
```

O envelope v1 contém **uma única evidência PDF física**.

A cardinalidade canônica multi-PDF de um concept é resolvida posteriormente pelo Produtor OKF/DAH e não implica múltiplos PDFs no mesmo envelope.

### 4.3 Manifest serializado

O `manifest.json` formaliza os seguintes campos do ITP/1.0:

* `protocol_version` — obrigatório; `"1.0"`;
* `handoff_id` — obrigatório; identidade opaca do transporte/retry;
* `evidence_reference` — obrigatório; `"evidence.pdf"`;
* `source_origin` — obrigatório; locator/origem operacional;
* `retrieved_at` — obrigatório; timestamp ISO 8601 com timezone;
* `collector` — obrigatório; Actor da coleta;
* `last_modified` — opcional;
* `media_type` — obrigatório; `"application/pdf"`;
* `byte_size` — obrigatório;
* `candidate_sha256` — opcional;
* `legal_hints` — opcional e sem autoridade canônica.

`handoff_id` não é concept ID, Stable Concept ID, identidade jurídica ou hash de conteúdo.

### 4.4 Canal inicial

O canal oficial inicial é um **filesystem ingress inbox local**, fora de `/bundle/`.

O produtor do handoff:

1. grava um arquivo temporário não consumível;
2. fecha completamente o ZIP;
3. publica o arquivo por rename atômico no mesmo filesystem;
4. somente nomes finais elegíveis entram no preflight.

O path absoluto do inbox não é congelado por esta baseline.

### 4.5 Preflight do ITP/1.0

O preflight deve:

* validar ZIP e estrutura esperada;
* rejeitar archive criptografado, links, paths absolutos, `..`, membros extras ou duplicados;
* aplicar limites configuráveis de tamanho comprimido/descomprimido e compression ratio;
* validar `manifest.json` em UTF-8 e schema ITP/1.0;
* validar `byte_size`;
* recalcular o SHA-256 oficial dos bytes de `evidence.pdf`;
* comparar `candidate_sha256` quando presente;
* validar que a evidência é compatível com PDF por conteúdo/estrutura;
* nunca executar conteúdo recebido.

Hash conhecido não autoriza rejeição, No-Op canônico, fusão de concepts ou decisão de identidade jurídica no preflight.

### 4.6 Retry e idempotência de transporte

O estado operacional de ingresso permanece fora de `/bundle/`.

Retries do mesmo handoff reutilizam o mesmo `handoff_id`.

O mesmo `handoff_id` com manifesto ou evidência semanticamente diferente é conflito de transporte e deve ser rejeitado.

Hash do ZIP não é chave normativa de idempotência.

### 4.7 Object Storage

Após validação física do envelope e antes da Fase 1, a evidência aceita é preservada em Object Storage externo.

Esta baseline não congela provider, bucket, URI scheme, hostname, object key ou filename físico.

`source_origin` não é automaticamente `sources[].resource`.

## 5. Preflight

O preflight ocorre antes da conversão pesada.

### 5.1 Validações mínimas

- validar presença dos dados obrigatórios do handoff;
- validar que os bytes recebidos correspondem a um PDF processável pela rota PDF;
- calcular SHA-256 sobre os **bytes exatos recebidos**;
- verificar se a evidência já é conhecida;
- resolver a referência de preservação da evidência;
- impedir qualquer publicação direta no bundle.

### 5.2 Semântica do SHA-256

**[Existing FROZEN Requirement]** SHA-256 identifica os bytes exatos de uma evidência e permite verificar igualdade/integridade desses bytes.

Ele:

- não é identidade lógica do concept;
- não é identidade jurídica do ato;
- não prova autenticidade jurídica;
- pode aparecer em múltiplos concepts legítimos.

### 5.3 Evidência já conhecida e Duplicate Act Handling

**[Existing FROZEN Requirement]** Um hash conhecido **não autoriza rejeição automática**.

**[Decision Status — CLOSED: Duplicate Act Handling]** O tratamento é governado por `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`:

- **mesmo SHA-256**: mesma evidência física em bytes; ainda é necessário resolver a unidade jurídica candidata;
- **mesmos bytes, outro ato autônomo no mesmo PDF**: o candidato pode produzir novo concept;
- **mesmos bytes por locators/URLs diferentes**: continua sendo uma única evidência PDF; o locator adicional não cria automaticamente segunda fonte PDF em `sources`;
- **PDF fisicamente diferente, mesmo ato e equivalência material segura**: pode atualizar `sources` e a cardinalidade singular/plural do concept existente;
- **mudança material ou ambiguidade**: bloquear fusão automática e exigir revisão humana;
- **No-Op**: somente quando a evidência relevante já está representada e inputs canônicos, configuração relevante, versão lógica e conteúdo canônico não exigem alteração;
- **proibições**: não usar hash, URL, filename, `concept_id` ou número de processo isoladamente como identidade jurídica; não alterar `status` nem criar sufixos de versão automaticamente.

O mesmo PDF pode originar vários concepts.

---

## 6. Phase 1 Conversion

Após `Accepted`, a Fase 1 produz os artefatos físicos preservados.

### 6.1 Evidência original

O PDF original permanece fora do Git/bundle, preservado no Object Storage externo. A referência utilizada em `sources[].resource` deve ser estável e resolvível pelo contrato de ingestão; este contrato não fixa esquema URI específico.

### 6.2 Conversão

A Fase 1 executa conversão conservadora página a página, com extração textual e **OCR fallback quando necessário**.

O ESIC não fixa um motor específico de OCR. Implementação, versão, modelo, método de conversão e páginas submetidas a OCR pertencem à configuração/execução da Fase 1 e ao JSON técnico.

### 6.3 Marcadores físicos

A saída integral da Fase 1 para um PDF preserva a numeração física mediante:

```text
[[Pág. N]]
```

Quando um único PDF gerar vários concepts, cada concept literal deve preservar somente as páginas efetivamente representadas, mantendo a numeração física original. Um concept que corresponda às páginas 150–160 não precisa iniciar em `[[Pág. 1]]`.

Concepts sintéticos multi-fonte não devem receber uma sequência global artificial de páginas.

### 6.4 JSON técnico

Método de conversão, OCR, confiança, warnings, versões, timestamps técnicos e demais informações operacionais permanecem no JSON técnico da Fase 1 e não são duplicados no frontmatter canônico.

### 6.5 Literalidade

A rota literal de PDF não corrige silenciosamente ortografia, não resume, não traduz e não reescreve o conteúdo jurídico.

### 6.6 Phase 1 Quality Gate — CLOSED

Governado por `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`.

Após produzir Markdown literal + JSON técnico, a Fase 1 executa um gate determinístico com exatamente três resultados normativos:

- **PASS** — saída física completa/conformante e sem warnings técnicos ativos;
- **PASS WITH WARNINGS** — saída física completa/conformante com warnings não fatais registrados;
- **FAIL** — saída insuficientemente conformante e bloqueada para o Produtor OKF.

Somente **PASS** e **PASS WITH WARNINGS** são elegíveis para o handoff ao Produtor OKF.

Regras consolidadas:

1. a saída integral da Fase 1 deve preservar exatamente os marcadores `[[Pág. 1]]` ... `[[Pág. N]]`, sem omissões, duplicidades ou inversão;
2. OCR utilizado com sucesso não é falha nem warning por definição;
3. página genuinamente vazia preserva `[[Pág. N]]` e não é warning obrigatório;
4. método de extração, warnings, erros e telemetria pertencem ao JSON técnico, não ao corpo Markdown literal;
5. score/confidence, se calculados, são apenas diagnósticos e nunca alteram o resultado normativo;
6. `allow_partial`, se implementado, produz somente artefato diagnóstico **FAIL**, fora do caminho do Produtor;
7. revisão humana não converte diretamente um artefato parcial FAIL em saída válida; é necessária nova execução com PASS ou PASS WITH WARNINGS;
8. retry é bounded/configurável e não possui número normativo fixado neste contrato;
9. o JSON técnico não pode persistir secrets/credentials;
10. a Fase 1 permanece engine-neutral.

O Quality Gate ocorre **depois** do preflight/ITP e não reabre validações de transporte.

---

## 7. OKF Producer Handoff

O Produtor OKF é o único componente autorizado a transformar as saídas aceitas da Fase 1 em concept documents canônicos.

**Gate obrigatório:** somente resultados `PASS` ou `PASS WITH WARNINGS` do Phase 1 Quality Gate podem entrar nesta etapa. Resultado `FAIL`, inclusive sob modo parcial/diagnóstico, permanece fora do caminho do Produtor.

Ele deve:

1. carregar saída física e proveniência;
2. resolver concept(s) e caminhos determinísticos;
3. preservar body ownership;
4. montar frontmatter conforme o Legal OKF Profile v1.3;
5. aplicar cardinalidade de PDF;
6. preservar campos Human-Owned e Shared Ownership existentes conforme Lifecycle v1.4;
7. aplicar a política de `verified`;
8. validar OKF + regras `repo_jur`;
9. publicar atomicamente;
10. expor mudança como diff revisável na governança do Git.

### 7.1 `generated`

Para concepts produzidos pelo pipeline:

```yaml
generated:
  by: "repo_jur_producer/<version>"
  at: "<last-meaningful-content-change>"
```

`generated.at` representa a última mudança significativa do conteúdo atual, não o horário de cada execução.

### 7.2 `generated` ≠ `verified`

Execução bem-sucedida do Produtor não constitui verificação jurídica ou factual independente.

---

## 8. Provenance and Hash Rules

`sources` registra os materiais dos quais o concept deriva. Os hashes `repo_jur_*` registram integridade física dos bytes PDF.

**[Existing FROZEN Requirement]** No `repo_jur`, `sources` é obrigatório quando o concept deriva de fontes identificáveis. Para concepts derivados de PDF, a(s) evidência(s) PDF efetivamente utilizada(s) pelo pipeline deve(m) aparecer em `sources`.

### 8.1 Exatamente 1 PDF

```yaml
sources:
  - resource: "<source-pdf-resource>"

repo_jur_pdf_hash: "<sha256-64-hex>"
```

Deve existir exatamente uma evidência PDF de origem aplicável ao concept. O campo plural deve ser omitido. `sources[].id` continua opcional neste caso, salvo quando necessário para atribuição de claims.

### 8.2 Dois ou mais PDFs

```yaml
sources:
  - id: "source_pdf_a"
    resource: "<source-a-resource>"
  - id: "source_pdf_b"
    resource: "<source-b-resource>"

repo_jur_pdf_hashes:
  source_pdf_a: "<sha256-64-hex>"
  source_pdf_b: "<sha256-64-hex>"
```

Regras:

- cada fonte PDF deve possuir `sources[].id`;
- cada PDF deve possuir exatamente uma entrada correspondente em `repo_jur_pdf_hashes`;
- cada chave do mapping deve corresponder a uma fonte PDF existente;
- fontes não-PDF podem existir em `sources`, mas não entram no mapping;
- `repo_jur_pdf_hash` e `repo_jur_pdf_hashes` são mutuamente exclusivos.

### 8.3 Fontes não-PDF

Fontes não-PDF podem participar da proveniência de qualquer concept quando aplicáveis. Elas não recebem automaticamente `repo_jur_pdf_hash`, `repo_jur_pdf_hashes` ou `[[Pág. N]]`.

Este ESIC v1.1 não define um conversor físico universal para binários não-PDF; define apenas sua participação na proveniência quando identificáveis.

---

## 9. Source Cardinality — CLOSED

A decisão `PDF Source Cardinality` está encerrada.

| Cenário | Regra |
|---|---|
| 1 PDF → 1 concept | `sources` + `repo_jur_pdf_hash` |
| 1 PDF → N concepts | cada concept referencia a mesma evidência e usa o mesmo hash singular |
| N PDFs → 1 concept | `sources[].id` + `repo_jur_pdf_hashes` |
| N PDFs → N concepts | cada concept lista somente as fontes que efetivamente o sustentam |

Para 1 PDF → N concepts, a mesma evidência física e o mesmo SHA-256 podem sustentar vários `concept_id` distintos.

Para concepts sintéticos multi-fonte, `sources[].id` e footnotes podem atribuir claims a fontes específicas. Este contrato não inventa um schema de página→fonte quando tal associação não estiver explicitamente representada.

---

## 10. Reprocessing and Idempotency

### 10.1 Idempotência

Para inputs canônicos equivalentes, configuração relevante equivalente e mesma versão lógica de processamento, a regeneração deve produzir **conteúdo canônico equivalente** e não gerar diffs espúrios.

O mesmo SHA-256, isoladamente, não garante saída idêntica se configuração ou versão lógica tiverem mudado.

### 10.2 Field ownership

O Produtor deve obedecer à matriz do Lifecycle & Field Ownership v1.1:

- **Producer-Owned:** campos canônicos sob domínio do Produtor, incluindo `type`, `sources`, `generated`, hashes PDF e metadados jurídicos classificados dessa forma no perfil;
- **Shared Ownership:** por exemplo `title`, `description`, `tags` e demais campos explicitamente classificados como compartilhados;
- **Human-Owned:** campos como `status` e curadoria exclusivamente humana aplicável;
- **`verified`:** somente eventos reais de verificação humana ou processo independente.

O Produtor não pode apagar silenciosamente valores humanos válidos.

### 10.3 `verified` e histórico

Mudança de hash, cardinalidade ou caminho não invalida `verified` automaticamente.

Se a alteração atingir materialmente o objeto efetivamente verificado — conteúdo jurídico, significado, páginas relevantes, proveniência material relevante ou escopo coberto pela revisão — o evento anterior não permanece ativo sem nova verificação real.

**Verification History Schema — CLOSED:** eventos reais anteriormente ativos que deixem de ser aplicáveis são arquivados em `repo_jur_verification_history` conforme `decision-memo-verification-history-schema-v1.0-FROZEN.md`.

Esta lógica pertence ao **lifecycle canônico/Produtor OKF**, não ao preflight físico da Fase 1. O preflight não inventa, invalida nem migra eventos de verificação.

---

## 11. Error / Rejection Conditions

A incorporação deve ser interrompida quando ocorrer uma condição que impeça conformidade ou rastreabilidade, incluindo:

1. **PDF inválido/inutilizável:** bytes corrompidos ou evidência que não possa ser processada pela rota PDF autorizada.
2. **Handoff incompleto:** ausência de proveniência obrigatória, como locator de origem quando aplicável, `retrieved_at` ou `collector`.
3. **Falha de preservação:** impossibilidade de preservar a evidência aceita ou de estabelecer referência estável/resolvível para ela.
4. **Phase 1 Quality Gate = FAIL:** qualquer condição determinística que impeça saída física completa/conformante, incluindo perda/duplicação/inversão de página, erro de extração não resolvido, truncamento conhecido ou relatório técnico inválido. **OCR utilizado com sucesso e warnings isolados não são motivo automático de FAIL.**
5. **Colisão/identidade não resolvida:** a operação exigiria sobrescrever silenciosamente um concept existente ou não é possível resolver deterministicamente a unidade lógica/caminho. Hash repetido, isoladamente, não é motivo de rejeição.
6. **Desalinhamento singular/plural:** violação das regras de `repo_jur_pdf_hash` / `repo_jur_pdf_hashes` ou do mapping para `sources[].id`.
7. **Falha de conformidade OKF/repo_jur:** YAML não parseável, `type` vazio/ausente ou violação de requisito obrigatório do perfil do projeto.

---

## 12. Invariants

1. **Corpus canônico:** somente `repo_jur/bundle/` é o corpus jurídico canônico.
2. **Zero-Write:** coletores e mecanismos de retrieval não gravam no bundle.
3. **Evidência preservada:** bytes PDF aceitos são preservados fora do bundle e permanecem rastreáveis por referência estável + SHA-256.
4. **Hash ≠ identidade:** SHA-256 identifica bytes, não concept nem autenticidade jurídica.
5. **Literalidade:** body literal derivado de PDF segue a saída canônica da Fase 1.
6. **Páginas reais:** `[[Pág. N]]` representa página física real da evidência correspondente; não se fabricam páginas para concepts abstratos/sintéticos.
7. **Cardinalidade:** 1 PDF → hash singular; 2+ PDFs → mapping plural; nunca ambos.
8. **Metadados técnicos isolados:** detalhes de OCR/conversão permanecem no JSON técnico.
9. **Field ownership:** regeneração preserva Human-Owned e curadoria humana em Shared Ownership.
10. **`generated` ≠ `verified`:** produção não é verificação.
11. **Derived retrieval data:** chunks, índices, embeddings, caches ou outras estruturas de retrieval, se existirem, permanecem fora do bundle e são derivados/reconstruíveis; podem ser temporários ou persistentes conforme o Retrieval Contract.
12. **Nenhuma tecnologia de retrieval é escolhida por este contrato.**
13. **Quality Gate:** somente PASS/PASS WITH WARNINGS seguem ao Produtor; FAIL nunca segue.
14. **OCR:** uso de OCR bem-sucedido não é falha nem warning por definição.
15. **Partial:** artefatos parciais permanecem diagnósticos e não canônicos.
16. **Gate determinístico:** score/confidence nunca decide aceitação normativa.

---

## 13. Open Questions

No escopo de **ingestão e produção canônica** deste ESIC, não permanece Open Decision arquitetural após o fechamento de `Phase 1 Quality Gate`.

As Open Decisions próprias do Retrieval Contract — `Search Execution Path`, `Chunking Strategy` e `Reranking Pipeline` — permanecem regidas por esse contrato e não são encerradas nem reabertas pelo ESIC.

**CLOSED:** PDF Source Cardinality.  
**CLOSED:** Document Lifecycle.  
**CLOSED:** Duplicate Act Handling — `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`.  
**CLOSED:** Stable Concept Identity — `decision-memo-stable-concept-identity-v1.0-FROZEN.md`.  
**CLOSED:** Verification History Schema — `decision-memo-verification-history-schema-v1.0-FROZEN.md`.  
**CLOSED:** Ingress Transport Protocol — `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`.  
**CLOSED:** Phase 1 Quality Gate — `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`.  
**RESOLVED/SUPERSEDED:** PDF Storage Location — PDFs originais preservados em Object Storage externo conforme baselines FROZEN posteriores.

---

## 14. Reconstructed-vs-Frozen Traceability Summary

### 14.1 Fonte histórica recuperada

A sequência `Discovered → Candidate → Selected → Accepted → Incorporated`, o handoff de bytes + proveniência, a fronteira de escrita e o preflight não são meras inferências: foram recuperados do documento histórico `Protocolo de Ingestão e Governança de Dados do repo_jur.md`, que contém o ESIC v1.1 consolidado em estado `READY TO FREEZE`.

### 14.2 Regras atualizadas pelas baselines FROZEN

- **Duplicate Act Handling:** incorporado como CLOSED por `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`. O ESIC passa a distinguir mesmos bytes por múltiplos locators, nova evidência física equivalente, ato autônomo e mudança material/ambígua sem fusão automática.
- **Verification History Schema:** incorporado como CLOSED por `decision-memo-verification-history-schema-v1.0-FROZEN.md`. A invalidação histórica é responsabilidade do lifecycle canônico e não do preflight; somente `verified` participa da confiança ativa.
- **Ingress Transport Protocol:** incorporado como CLOSED por `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`. O handoff passa a usar ITP/1.0, envelope ZIP single-evidence, `manifest.json`, `handoff_id`, inbox local e preflight de transporte seguro.
- **Phase 1 Quality Gate:** incorporado como CLOSED por `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`. O gate é determinístico, possui PASS/PASS WITH WARNINGS/FAIL, preserva engine-neutrality e bloqueia qualquer FAIL do handoff ao Produtor.

A revisão técnica substitui regras históricas superadas nos seguintes pontos:

- **PDF Storage Location:** a arquitetura v4 ainda a registra como aberta, mas essa marcação foi supersedida, para fins deste ESIC, pela baseline FROZEN posterior de cardinalidade, que assume preservação em Object Storage externo. A arquitetura deverá ser sincronizada em atualização controlada futura.
- **Document Lifecycle:** deixou de permanecer aberta; é governada por `lifecycle-field-ownership-v1.1-FROZEN.md`.
- **PDF Source Cardinality:** deixou de permanecer aberta; usa singular/plural conforme o memo FROZEN.
- **Known hash:** não é motivo automático de rejeição.
- **`generated.at`:** última mudança significativa, não timestamp de execução.
- **Field ownership:** `title`, `description` e `tags` são Shared Ownership, não simplesmente Human-Owned.
- **OCR warnings:** não constituem rejeição automática enquanto o Phase 1 Quality Gate estiver aberto.
- **`sources[].resource`:** deve rastrear a evidência efetivamente utilizada; não é automaticamente igual à URL original de download.
- **Page markers:** concepts derivados de trechos preservam a numeração física efetivamente representada, sem obrigação de começar em página 1.
- **Retrieval:** dados derivados podem existir fora do bundle; este ESIC não escolhe RAG ou mecanismo de busca.

### 14.3 Conformidade OKF v0.2

Este contrato preserva as semânticas OKF relevantes:

- `type` é o único campo sempre obrigatório em concept frontmatter;
- `sources[].resource` é obrigatório quando uma entrada de `sources` existe;
- `sources[].id` é opcional no OKF, mas torna-se obrigatório por política `repo_jur` para fontes PDF em cenário multi-PDF;
- `sources[].author` identifica o produtor da fonte, não o downloader;
- `sources[].last_modified` representa a última modificação da fonte, não a coleta;
- `generated` e `verified` são dimensões distintas;
- ausência de `verified` significa unverified;
- `concept_id` continua sendo derivado do caminho relativo e é posicional.

---

**Status: FROZEN**
