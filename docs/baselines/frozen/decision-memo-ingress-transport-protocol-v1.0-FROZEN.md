# MEMORANDO DE DECISÃO ARQUITETURAL: INGRESS TRANSPORT PROTOCOL (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v8-FROZEN.md`, `external-source-ingestion-contract-v1.4-FROZEN.md`, `legal-okf-profile-v1.3-FROZEN.md`, `concept-identity-physical-structure-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `retrieval-contract-v2.4-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md` e `decision-memo-verification-history-schema-v1.0-FROZEN.md`.

---

## 1. Problem Statement

A **Open Decision — Ingress Transport Protocol** deve definir a serialização e o canal técnico inicial pelo qual `juridico-cli` e outros coletores externos entregam candidatos ao `repo_jur`.

A decisão deve preservar a fronteira já congelada:

```text
fonte externa
    ↓
handoff
    ↓
preflight repo_jur
    ↓
preservação da evidência aceita
    ↓
Fase 1
    ↓
Produtor OKF
    ↓
validação
    ↓
publicação atômica em repo_jur/bundle/
```

O protocolo de ingresso não possui autoridade para criar conteúdo OKF canônico, `verified`, `status`, identidade jurídica ou decisão final de duplicidade.

A decisão precisa distinguir explicitamente:

1. **Envelope Format** — como bytes + manifesto são serializados;
2. **Delivery Channel** — como o envelope completo chega ao receptor;
3. **Ingress State** — estado operacional usado para retry/idempotência;
4. **Canonical Ingestion Lifecycle** — estados ESIC `Discovered → Candidate → Selected → Accepted → Incorporated`.

Essas quatro dimensões não são equivalentes.

---

## 2. Frozen Constraints

1. `juridico-cli` e coletores possuem **zero direct write** em `/bundle/`. **[Existing FROZEN Requirement]**
2. Handoff contém evidência física + proveniência candidata, não Markdown/frontmatter canônico. **[Existing FROZEN Requirement]**
3. O preflight ocorre antes da conversão pesada. **[Existing FROZEN Requirement]**
4. SHA-256 oficial é calculado pelo `repo_jur` sobre os bytes exatos recebidos. **[Existing FROZEN Requirement]**
5. SHA-256 identifica evidência física, não concept ou ato jurídico. **[Existing FROZEN Requirement]**
6. PDF original aceito é preservado em Object Storage externo, fora de Git e `/bundle/`. **[Existing FROZEN Requirement]**
7. `source_origin`, `retrieved_at`, `collector` e `last_modified` possuem semânticas distintas. **[Existing FROZEN Requirement]**
8. `source_origin` não é automaticamente `sources[].resource`. **[Existing FROZEN Requirement]**
9. `collector` não é `sources[].author`. **[Existing FROZEN Requirement]**
10. `retrieved_at` não é `sources[].last_modified`. **[Existing FROZEN Requirement]**
11. Duplicate Act Handling está CLOSED; hash conhecido não autoriza rejeição ou No-Op canônico automático. **[Existing FROZEN Requirement]**
12. Stable Concept Identity está CLOSED. **[Existing FROZEN Requirement]**
13. Verification History Schema está CLOSED. **[Existing FROZEN Requirement]**
14. Fase 1 é **engine-neutral**; nenhum motor de OCR/conversão é fixado por esta decisão. **[Existing FROZEN Requirement]**
15. PDF Source Cardinality descreve relação entre evidências e concepts, não obriga que várias evidências sejam transportadas no mesmo handoff. **[Existing FROZEN Requirement]**

---

## 3. Candidate Transport Models

### 3.1 Filesystem — arquivos soltos

PDF e manifesto são entregues separadamente em diretório compartilhado.

**Vantagens:** implementação simples.

**Limitações:** exige protocolo adicional para determinar quando o conjunto está completo; facilita leitura antecipada de arquivo parcial.

**[New Decision Proposal]**

### 3.2 CLI / STDIN

Bytes são entregues por stream e metadados por argumentos/STDIN estruturado.

**Vantagens:** bom para pipelines Unix e chamadas locais explícitas.

**Limitações:** mistura framing, metadados e transporte; retry exige reconstruir a mesma requisição; não produz artefato de handoff facilmente transferível.

**[New Decision Proposal]**

### 3.3 Package / Envelope versionado

Bytes e manifesto são encapsulados em um único envelope versionado.

**Vantagens:** unidade de entrega auditável, movível e validável; o mesmo envelope pode viajar por filesystem ou futuro HTTP sem mudar a semântica interna.

**Limitações:** requer validação segura do archive e proteção contra decompression bombs/path traversal.

**[New Decision Proposal]**

### 3.4 HTTP/API

Canal remoto de envio de um envelope ou multipart.

**Vantagens:** adequado a coletores remotos e autenticação de rede.

**Limitações:** adiciona servidor, autenticação, limites de upload, retry de rede e operação de infraestrutura não necessários à implantação local inicial.

**[New Decision Proposal]**

---

## 4. Comparative Analysis

| Critério | Arquivos soltos | CLI/STDIN | Envelope versionado | HTTP/API |
|---|---|---|---|---|
| Unidade auditável de handoff | Baixa | Baixa | Alta | Depende do payload |
| Framing completo | Exige convenção | Pelo processo | Intrínseco ao envelope | Pelo protocolo HTTP |
| Retry local | Médio | Médio | Alto | Alto |
| Reuso futuro remoto | Baixo | Médio | Alto | Nativo |
| Complexidade inicial | Baixa | Média | Média | Alta |
| Segurança de archive | N/A | N/A | Exige regras próprias | Depende do payload |
| Independência do canal | Baixa | Baixa | Alta | Baixa |
| Adequação ao ambiente local inicial | Alta | Alta | Alta | Desnecessariamente alta |

---

## 5. Recommended Decision

Adotar **Ingress Transport Protocol v1 (ITP/1.0)** com duas decisões separadas:

### 5.1 Envelope oficial

**ZIP versionado**, contendo exatamente:

```text
<handoff>.zip
├── manifest.json
└── evidence.pdf
```

O envelope v1 contém **uma única evidência PDF física**.

Isso não limita a cardinalidade canônica. Um concept multi-PDF pode ser formado posteriormente a partir de duas ou mais evidências aceitas por handoffs independentes, conforme PDF Source Cardinality e Duplicate Act Handling.

### 5.2 Canal oficial inicial

**Filesystem ingress inbox local, configurável e fora de `/bundle/`.**

O produtor do handoff:

1. grava o envelope com extensão/estado temporário não consumível;
2. fecha completamente o arquivo;
3. publica o envelope no inbox por rename atômico **dentro do mesmo filesystem**;
4. o receptor observa apenas nomes finais elegíveis.

A decisão não congela um path absoluto.

### 5.3 Canal remoto futuro

Um futuro endpoint HTTP pode transportar **o mesmo envelope ITP/1.0** sem alterar `manifest.json` ou as regras de preflight.

HTTP não é parte obrigatória desta baseline.

**[New Decision Proposal]**

---

## 6. Handoff Package

### 6.1 Conteúdo

O ZIP deve possuir exatamente dois membros regulares, não criptografados e localizados na raiz:

- `manifest.json`
- `evidence.pdf`

São proibidos:

- diretórios internos;
- membros adicionais;
- membros duplicados com o mesmo nome;
- symlinks/hardlinks;
- caminhos absolutos;
- `..`;
- nomes equivalentes após normalização que produzam colisão.

### 6.2 Evidência

`evidence.pdf` contém exatamente os bytes obtidos pelo coletor.

O nome anônimo no envelope:

- não é identidade jurídica;
- não é filename canônico;
- não determina slug;
- não é usado como `concept_id`.

O protocolo não exige preservação do filename original como metadado canônico.

### 6.3 Multi-PDF

ITP/1.0 é deliberadamente **single-evidence-per-envelope**.

Razões:

- preserva a unidade física do handoff;
- simplifica hash, tamanho, retry e idempotência;
- evita confundir cardinalidade de transporte com cardinalidade do concept;
- permite que o mesmo PDF seja usado por múltiplos concepts;
- permite que múltiplos PDFs independentes sejam consolidados posteriormente quando a equivalência lógica/material for segura.

Um envelope com múltiplas evidências exigiria nova versão do protocolo.

**[New Decision Proposal]**

---

## 7. Manifest Schema

Os nomes abaixo deixam de ser apenas rótulos conceituais do ESIC e tornam-se a serialização oficial do **ITP/1.0**.

### 7.1 Campos

| Campo | Regra |
|---|---|
| `protocol_version` | obrigatório; `"1.0"` |
| `handoff_id` | obrigatório; identificador opaco único do handoff; preservado em retries |
| `evidence_reference` | obrigatório; exatamente `"evidence.pdf"` |
| `source_origin` | obrigatório; string não vazia representando locator/origem de coleta; não precisa ser URI Web |
| `retrieved_at` | obrigatório; timestamp ISO 8601 com timezone |
| `collector` | obrigatório; Actor que realizou a coleta |
| `last_modified` | opcional; instante/data da última modificação conhecida da própria fonte |
| `media_type` | obrigatório; `"application/pdf"` |
| `byte_size` | obrigatório; inteiro positivo dos bytes de `evidence.pdf` |
| `candidate_sha256` | opcional; SHA-256 lowercase dos bytes antes do empacotamento |
| `legal_hints` | opcional; mapping de candidatos jurídicos sem autoridade canônica |

### 7.2 `handoff_id`

`handoff_id` existe **somente para identidade da requisição de transporte/retry**.

Ele:

- não é Stable Concept ID;
- não identifica ato jurídico;
- não identifica PDF por conteúdo;
- não entra automaticamente no frontmatter;
- não substitui SHA-256;
- deve permanecer igual quando o mesmo handoff for retransmitido após falha.

Formato recomendado para ITP/1.0: UUID v4 textual em lowercase.

### 7.3 `collector`

O campo deve aceitar a Actor Convention aplicável ao projeto, incluindo:

- `human:<id>`;
- `process:<id>`;
- `<producer>/<version>`.

A serialização não deve restringir collectors apenas a software versionado ou a humanos.

### 7.4 `source_origin`

`source_origin` representa um locator/origem operacional.

Quando a coleta for Web, deve ser a URL oficial disponível.

O schema não exige `format: uri` universalmente, porque uma origem válida pode não ser uma URL Web.

### 7.5 `last_modified`

É opcional.

Nunca receber valor de `retrieved_at` por fallback.

### 7.6 `candidate_sha256`

É opcional e calculado pelo coletor.

O valor oficial continua sendo o SHA-256 recalculado pelo `repo_jur`.

Divergência entre os dois indica inconsistência física do handoff e causa rejeição do pacote.

### 7.7 `legal_hints`

Hints:

- são candidatos;
- não criam identity;
- não decidem Duplicate Act Handling;
- não definem filename/slug;
- não têm autoridade de frontmatter.

### 7.8 Exemplo

```json
{
  "protocol_version": "1.0",
  "handoff_id": "4bbedf1e-5625-4e0b-a81f-8ca3a55d0bbc",
  "evidence_reference": "evidence.pdf",
  "source_origin": "https://example.invalid/original.pdf",
  "retrieved_at": "2026-08-12T17:00:00-03:00",
  "collector": "juridico-cli/1.0.0",
  "last_modified": "2026-08-11",
  "media_type": "application/pdf",
  "byte_size": 1234567,
  "candidate_sha256": "<64-lowercase-hex>",
  "legal_hints": {
    "process_number": "<candidate-value>"
  }
}
```

---

## 8. Preflight Validation

O preflight valida transporte e evidência física antes da Fase 1.

### 8.1 Envelope

Antes de extrair conteúdo:

1. validar que o arquivo recebido é ZIP suportado;
2. inspecionar central directory;
3. rejeitar archive encrypted;
4. exigir exatamente dois membros válidos;
5. rejeitar duplicatas de nomes;
6. rejeitar paths absolutos, `..`, diretórios e links;
7. aplicar limites configuráveis ao tamanho do ZIP;
8. aplicar limites configuráveis ao tamanho total descompactado;
9. aplicar limite configurável de compression ratio;
10. rejeitar métodos de compressão não suportados.

### 8.2 Manifest

1. limitar tamanho máximo configurável de `manifest.json`;
2. decodificar estritamente como UTF-8;
3. parsear JSON;
4. validar schema ITP/1.0;
5. rejeitar versão não suportada;
6. validar `handoff_id`.

### 8.3 Evidência

O receptor deve processar `evidence.pdf` de forma bounded/streaming quando aplicável:

1. conferir `byte_size`;
2. recalcular SHA-256 oficial;
3. comparar `candidate_sha256`, quando fornecido;
4. verificar assinatura/estrutura mínima compatível com PDF;
5. confirmar que o arquivo pode ser aberto pela rota PDF sem executar conteúdo incorporado.

A qualidade textual/visual do PDF e critérios de OCR pertencem à **Phase 1 Quality Gate**, ainda aberta.

### 8.4 Hash conhecido

Hash conhecido é apenas sinal de evidência física já conhecida.

No preflight:

- não rejeitar automaticamente;
- não declarar No-Op canônico;
- não fundir concepts;
- não decidir que dois atos são iguais.

A resolução jurídica/lógica permanece governada por Duplicate Act Handling no estágio que possua informação suficiente para comparar o candidato com concepts existentes.

---

## 9. Atomicity / Retry / Idempotency

### 9.1 Atomicidade local

ZIP **não garante atomicidade sozinho**.

A regra oficial do canal filesystem é:

```text
<inbox>/<handoff_id>.partial
        ↓ gravação completa + close
rename no mesmo filesystem
        ↓
<inbox>/<handoff_id>.zip
        ↓
preflight
```

O receptor ignora `.partial`.

Rename só é tratado como atômico quando origem e destino pertencem ao mesmo filesystem e a implementação oferece essa garantia.

### 9.2 Idempotência de transporte

O receptor mantém estado operacional de ingresso **fora de `/bundle/`**, indexado por `handoff_id`.

Retry com:

- mesmo `handoff_id`;
- mesmo manifesto sem alteração semântica;
- mesmo SHA-256 oficial da evidência

deve retornar/reutilizar o resultado já conhecido, sem duplicar execução.

Se o mesmo `handoff_id` reaparecer com evidência ou manifesto semanticamente diferente, ocorre **handoff conflict** e o pacote é rejeitado.

### 9.3 Hash do ZIP

Hash do ZIP **não é chave de idempotência normativa**.

Recompressão, timestamps internos ou diferenças de container podem produzir bytes ZIP distintos para o mesmo handoff lógico.

### 9.4 Evidência igual, handoff diferente

Mesmo SHA-256 com outro `handoff_id` pode representar:

- nova proveniência de coleta;
- outro locator;
- outra tentativa de incorporação;
- outro ato presente na mesma evidência.

Portanto não é descartado automaticamente.

### 9.5 Falhas

Falha antes de conclusão do handoff permite retry com o mesmo `handoff_id`.

Estados/result codes operacionais de transporte não alteram `status` OKF nem criam novos lifecycle states normativos além dos já definidos no ESIC.

---

## 10. Security Rules

1. **Nenhum path recebido é confiável.**
2. **Archive members são validados antes de extração.**
3. **Não extrair membros desconhecidos.**
4. **Proibir path traversal e paths absolutos.**
5. **Proibir links e membros especiais.**
6. **Proibir archives criptografados no ITP/1.0.**
7. **Impor limites configuráveis de tamanho comprimido/descomprimido.**
8. **Impor limite configurável de compression ratio.**
9. **Não congelar limite numérico global como 100 MB nesta decisão.**
10. **Não carregar PDF inteiro em memória quando processamento streaming/bounded for possível.**
11. **Validar PDF por conteúdo/estrutura, não somente extensão ou MIME declarado.**
12. **Não executar scripts, macros, anexos ou conteúdo incorporado ao PDF.**
13. **Processar em quarentena operacional fora de `/bundle/`.**
14. **Filename não participa de identidade jurídica.**
15. **Nenhum passo de transporte possui autoridade de publicação no bundle.**

---

## 11. Object Storage Interaction

### 11.1 Preservação

Depois de o envelope passar pelas validações físicas necessárias, a evidência aceita deve ser preservada em Object Storage externo **antes da Fase 1**.

A Fase 1 não depende do arquivo ZIP como evidência durável.

### 11.2 Referência estável

O storage layer deve produzir/resolver uma referência estável e resolvível para os bytes efetivamente preservados.

Esta decisão **não congela**:

- provider;
- bucket;
- esquema URI;
- hostname;
- object key;
- filename baseado em SHA;
- política de deduplicação física do storage.

### 11.3 `sources[].resource`

Quando o concept for posteriormente produzido, `sources[].resource` referencia a evidência preservada efetivamente utilizada conforme Legal OKF Profile/ESIC.

Não se copia automaticamente `source_origin`.

### 11.4 `source_origin`

Permanece proveniência operacional de coleta.

O protocolo não determina que ela seja persistida no frontmatter canônico.

A forma de retenção operacional do manifesto/handoff fora do bundle pode ser definida pela implementação, desde que a proveniência necessária não seja perdida antes da incorporação.

---

## 12. Invariants

1. O envelope v1 contém uma evidência PDF.
2. Multi-PDF de concept não significa multi-PDF de envelope.
3. O formato do envelope é ZIP; o canal local inicial é filesystem inbox.
4. ZIP não é considerado atomicidade suficiente sem completion protocol.
5. `handoff_id` identifica retry/transporte, não concept/ato/evidência.
6. SHA-256 oficial é calculado pelo receptor sobre os bytes exatos.
7. Hash conhecido não gera rejeição ou No-Op canônico automático.
8. `source_origin` não é automaticamente `sources[].resource`.
9. `collector` não é `sources[].author`.
10. `retrieved_at` não é `sources[].last_modified`.
11. Preflight não resolve sozinho identidade jurídica quando não possui evidência suficiente.
12. PDF aceito é preservado em Object Storage antes da Fase 1.
13. Object Storage naming/URI scheme não é congelado por esta decisão.
14. Fase 1 permanece engine-neutral.
15. Collectors e `juridico-cli` não escrevem no bundle.
16. Retrieval continua podendo **ler** o bundle sob Zero-Write; Zero-Write não significa Zero-Read.
17. Nenhuma regra deste protocolo altera `verified`, `repo_jur_verification_history` ou `status`.
18. `handoff_id`, transport result codes e quarantine paths nunca são convertidos automaticamente em metadados OKF canônicos.

---

## 13. Required Baseline Updates

Após aprovação e congelamento:

### 13.1 External Source Ingestion Contract

Criar versão controlada que:

- marque Ingress Transport Protocol como CLOSED;
- substitua rótulos conceituais do handoff pela serialização oficial ITP/1.0;
- registre `handoff_id`;
- registre ZIP single-evidence;
- registre canal inicial filesystem inbox + atomic rename;
- incorpore regras de retry/idempotência;
- mantenha `source_origin` como locator, não URI obrigatória;
- mantenha Duplicate Act Handling fora de rejeição automática por hash;
- preserve Fase 1 engine-neutral.

### 13.2 Architecture Phase 2

Criar versão controlada que:

- marque Ingress Transport Protocol como CLOSED;
- registre envelope ITP/1.0;
- registre canal local inicial;
- registre Object Storage antes da Fase 1;
- remova a decisão da lista de próximas decisões.

### 13.3 Baselines sem mudança normativa necessária

Esta decisão não requer nova versão normativa de:

- Legal OKF Profile;
- Lifecycle & Field Ownership;
- Concept Identity & Physical Structure;
- Retrieval Contract.

Esses documentos não mantêm Ingress Transport Protocol como Open Decision e o protocolo não altera seus schemas ou ownership.

---

## 14. Remaining Open Questions

Permanecem abertas:

- **Phase 1 Quality Gate**

No Retrieval Contract permanecem independentes:

- **Search Execution Path**
- **Chunking Strategy**
- **Reranking Pipeline**

### Fora de escopo desta baseline

- perfil de transporte HTTP remoto e autenticação;
- retenção operacional detalhada de envelopes já processados;
- provider/object-key strategy do Object Storage;
- schema estruturado de página específica por fonte em concepts multi-PDF.

Esses itens não são reclassificados automaticamente como Open Decisions arquiteturais por este memo.

---

## 15. Technical Review Corrections

A revisão técnica corrigiu os seguintes pontos da proposta inicial:

1. separou **Envelope Format** de **Delivery Channel**;
2. manteve ZIP como envelope, mas definiu filesystem inbox como canal local oficial inicial;
3. removeu a alegação de que ZIP sozinho garante atomicidade; atomicidade depende do completion protocol e rename no mesmo filesystem;
4. definiu ITP/1.0 como **single-evidence-per-envelope**, evitando confundir envelope multi-PDF com cardinalidade multi-PDF de concept;
5. adicionou `handoff_id` para idempotência de transporte, sem confundi-lo com Stable Concept Identity;
6. removeu hash do ZIP como chave normativa de idempotência;
7. corrigiu `source_origin`: locator/origem não precisa ser URI Web;
8. ampliou `collector` para Actor Convention compatível com humanos, processos e software versionado;
9. removeu UTC obrigatório de `retrieved_at`; exige timestamp com timezone;
10. renomeou `candidate_hash` para `candidate_sha256`, explicitando algoritmo e semântica;
11. retirou No-Op canônico e consolidação lógica da responsabilidade automática do preflight;
12. removeu `markitdown-ocr` da baseline de transporte; Fase 1 permanece engine-neutral;
13. removeu o limite arbitrário de 100 MB e manteve limites configuráveis;
14. acrescentou proteção explícita contra ZIP bombs, membros duplicados, encryption, links e decompression ratio;
15. removeu filename `<sha256>.pdf` e URI de Object Storage prescritos; storage scheme continua implementação externa;
16. corrigiu Zero-Write: retrieval pode ler `/bundle/`; não pode escrevê-lo;
17. removeu Required Baseline Updates desnecessárias de Legal OKF Profile, Lifecycle e Retrieval;
18. manteve como Open Decision principal somente Phase 1 Quality Gate, sem reabrir page→source mapping nem inventar autenticação HTTP como decisão atual.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
