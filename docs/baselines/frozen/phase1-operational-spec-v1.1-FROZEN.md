# PHASE 1 OPERATIONAL SPECIFICATION (`repo_jur`)

**Versão:** 1.1 (Controlled Reconciliation) (Baseline operacional sincronizada)  
**Data:** 15 de agosto de 2026  
**Status:** FROZEN  
**Autoridade arquitetural:** `decision-memo-phase1-quality-gate-v1.0-FROZEN.md`, `external-source-ingestion-contract-v1.6-FROZEN.md`, `decision-memo-shared-conversion-core-bounded-contexts-v1.0-FROZEN.md`, `decision-memo-post-ocr-critical-data-validation-seam-v1.0-FROZEN.md` e `arquitetura-fase2-repo-jur-v14-FROZEN.md`.

---


## 0A. Controlled Reconciliation v1.1

Esta versão incorpora, sem reabrir o Phase 1 Quality Gate:

- Shared Conversion Core;
- reutilização do conversor existente atrás de `ConversionEngine`;
- post-OCR critical-data validation seam;
- domain split somente após Quality Gate.

### Shared Conversion Core

Phase 1 é compartilhada por:

- Legal Knowledge Pipeline;
- Judicial Process Pipeline.

Ela permanece domain-neutral.

### ConversionEngine

A implementação concreta atual é reutilizada atrás de um contrato `ConversionEngine`.

A arquitetura continua engine-neutral.

A implementação pode ser documentada operacionalmente como MarkItDown/markitdown-ocr + Gemini por cliente compatível com OpenAI, sem transformar Gemini ou essa stack em dependência arquitetural.

### Literal Body

O body da Phase 1 continua literal.

Não inserir no Markdown:

- routing;
- `native`;
- `hybrid`;
- `OCR`;
- model/provider;
- warnings;
- telemetria;
- critical-data validation findings.

Esses dados pertencem ao Technical JSON.

### Post-OCR Critical-Data Validation Seam

Após conversão/OCR pode haver uma seam técnica para detectar inconsistências em dados críticos.

Ela:

- não autocorrige;
- não reescreve body;
- pode emitir `WARNING` ou `REVIEW_REQUIRED`;
- registra findings técnicos fora do Markdown.

Comparação determinística de valores redundantes no mesmo documento permanece futura capacidade separada.

### Downstream Domain Boundary

Somente outputs `PASS` / `PASS WITH WARNINGS` podem seguir ao roteamento de bounded context.

O Quality Gate não seleciona schema jurídico/processual e não realiza enrichment semântico.

---

## 1. Purpose

Esta baseline operacional define o contrato mínimo da Fase 1 após o fechamento do **Phase 1 Quality Gate**.

Ela não seleciona engine, parser, OCR provider ou modelo.

Fluxo:

```text
evidência PDF preservada
        ↓
Fase 1 — conversão física conservadora
        ↓
Markdown literal + JSON técnico
        ↓
Quality Gate
   ├─ PASS ───────────────► Produtor OKF
   ├─ PASS WITH WARNINGS ─► Produtor OKF
   └─ FAIL ───────────────► diagnóstico/reprocessamento
```

---

## 2. Inputs

A Fase 1 recebe uma evidência PDF que:

1. passou pelo ITP/1.0/preflight;
2. possui SHA-256 oficial calculado pelo receptor;
3. foi preservada em Object Storage externo;
4. possui total de páginas físicas determinável.

A Fase 1 não depende do ZIP de handoff como evidência durável.

---

## 3. Outputs

Para cada execução, a Fase 1 produz:

1. **Markdown literal** — representação textual conservadora do PDF integral;
2. **JSON técnico** — relatório de conversão, page inventory, warnings/errors, configuração relevante e resultado do gate.

Nenhum desses artefatos pertence diretamente a `/bundle/`.

---

## 4. Markdown Literal Contract

### 4.1 Page markers

Para um PDF de `N` páginas:

```text
[[Pág. 1]]
...
[[Pág. 2]]
...
...
[[Pág. N]]
...
```

Regras:

- exatamente um marker por página física;
- sequência 1..N;
- nenhuma omissão;
- nenhuma duplicidade;
- nenhuma inversão;
- página vazia legítima mantém o marker.

### 4.2 Literalidade

É proibido:

- resumir;
- traduzir;
- reescrever;
- corrigir semanticamente;
- completar texto por inferência.

Método de extração, engine, warnings e observabilidade **não são inseridos no body literal**.

---

## 5. Engine-Neutral Extraction

A implementação pode usar:

- extração nativa de texto;
- OCR fallback;
- estratégia híbrida;
- outras rotas compatíveis.

Nenhuma tecnologia específica é requisito desta baseline.

OCR:

- é fallback quando necessário;
- não é falha por definição;
- não é warning por definição;
- pode resultar em PASS quando a saída for completa e conformante.

---

## 6. Page Inventory

O JSON técnico deve possuir exatamente uma entrada por página física.

Cada entrada deve permitir identificar ao menos:

- `page_number`;
- método/estado de extração normalizado;
- quantidade de caracteres ou métrica equivalente;
- warnings;
- errors.

Estados conceituais mínimos:

- native text;
- OCR;
- hybrid;
- blank;
- error.

Os nomes serializados exatos podem ser definidos pelo schema operacional, mas devem permanecer engine-neutral.

---

## 7. Quality Gate

O gate possui exatamente três resultados normativos.

### 7.1 PASS

PASS exige cumulativamente:

- page inventory completo;
- markers 1..N corretos;
- nenhuma página em erro;
- nenhuma omissão silenciosa;
- nenhuma duplicação/inversão;
- nenhum truncamento conhecido;
- Markdown UTF-8 válido;
- JSON técnico válido;
- nenhuma condição fatal;
- nenhum warning técnico ativo.

OCR bem-sucedido é compatível com PASS.

### 7.2 PASS WITH WARNINGS

PASS WITH WARNINGS exige:

- todos os requisitos estruturais de completude;
- nenhuma página em erro;
- zero perda conhecida de conteúdo;
- um ou mais warnings técnicos não fatais registrados.

### 7.3 FAIL

FAIL ocorre quando qualquer condição não resolvida impede saída física suficientemente conformante, incluindo:

- marker ausente/duplicado/fora de ordem;
- página silenciosamente omitida;
- erro de extração persistente;
- página não vazia sem representação válida;
- truncamento conhecido;
- Markdown inválido;
- JSON técnico inválido/incompleto;
- corrupção textual estrutural determinística.

**FAIL nunca entra no Produtor OKF.**

---

## 8. Partial Diagnostic Mode

Uma implementação pode oferecer `allow_partial` ou função equivalente.

Esse modo:

- não cria quarto estado do gate;
- não converte FAIL em PASS WITH WARNINGS;
- pode persistir Markdown/JSON diagnósticos fora do bundle;
- deve registrar todas as páginas afetadas;
- não autoriza handoff ao Produtor;
- exige correção/reprocessamento até uma nova execução obter PASS ou PASS WITH WARNINGS.

Revisão humana pode diagnosticar/corrigir o problema, mas não emitir waiver para ignorar perda física conhecida.

---

## 9. Technical JSON Minimum Contract

Estrutura conceitual mínima:

```json
{
  "schema_version": "1.0",
  "execution_id": "<opaque-run-id>",
  "input": {
    "sha256": "<64-lowercase-hex>",
    "byte_size": 0,
    "page_count": 0
  },
  "phase1": {
    "implementation": "<implementation-id>",
    "implementation_version": "<version>",
    "logical_processing_version": "<version>",
    "relevant_config_fingerprint": "<opaque-fingerprint>"
  },
  "result": {
    "quality_gate": "PASS",
    "warnings": [],
    "errors": []
  },
  "artifacts": {
    "markdown_sha256": "<64-lowercase-hex>"
  },
  "pages": [],
  "telemetry": {}
}
```

Obrigatórios:

- schema version;
- execution ID;
- input SHA-256;
- input byte size;
- page count;
- implementation/version;
- logical processing version;
- relevant config fingerprint;
- quality gate result;
- warnings/errors;
- page inventory;
- Markdown hash quando houver saída final.

---

## 10. Deterministic vs. Telemetry Data

### Deterministic/reproducible

- input hash;
- page count;
- logical processing version;
- config fingerprint;
- page outcomes;
- warnings/errors derivados da entrada/configuração;
- gate result;
- Markdown output.

### Per-run telemetry

Pode variar:

- execution ID;
- start/end timestamps;
- duration;
- retry timing;
- host/runtime observations.

O JSON completo não precisa ser byte-a-byte idêntico entre execuções.

---

## 11. Secrets and Host Paths

Nunca persistir no JSON técnico:

- API keys;
- tokens;
- passwords;
- cookies;
- authorization headers;
- credentials equivalentes.

Paths absolutos temporários do host:

- não são identidade;
- não são proveniência canônica;
- não são obrigatórios no relatório persistente.

---

## 12. Retry

Retry deve ser:

- bounded;
- configurável;
- registrado no JSON quando relevante.

Esta baseline não fixa:

- número de tentativas;
- algoritmo específico de backoff;
- códigos HTTP;
- provider/model.

Após esgotamento de retry, a regra considera apenas o resultado final da página/execução.

---

## 13. Idempotency

Para os mesmos:

- bytes de entrada;
- logical processing version;
- relevant configuration;

o Markdown deve ser deterministicamente equivalente e o gate deve produzir o mesmo resultado normativo.

Telemetria por execução pode variar.

Uma execução FAIL não sobrescreve silenciosamente uma saída válida anterior.

---

## 14. Producer Boundary

O Produtor OKF recebe somente saídas com:

```text
quality_gate ∈ { PASS, PASS_WITH_WARNINGS }
```

O Produtor:

- não recebe partial FAIL como entrada válida;
- não utiliza score diagnóstico para decidir publicação;
- mantém suas próprias validações OKF/governança;
- continua sendo o único publicador canônico no bundle.

PASS não significa Incorporated.

---

## 15. Non-Goals

Esta especificação não define:

- engine de conversão;
- OCR provider/model;
- thresholds de confidence;
- threshold de mojibake heurístico;
- detecção de watermark;
- tuning de concorrência;
- segmentação jurídica em concepts;
- frontmatter OKF;
- `verified`;
- `status`;
- retrieval.

---

## 16. Invariants

1. Toda página física é representada exatamente uma vez na saída integral.
2. Markers são `[[Pág. N]]`.
3. OCR não é falha/warning por definição.
4. Página vazia legítima não é warning obrigatório.
5. Método de extração pertence ao JSON técnico.
6. Gate é determinístico.
7. Score é diagnóstico apenas.
8. FAIL nunca segue ao Produtor.
9. Partial continua FAIL.
10. JSON técnico é engine-neutral.
11. Secrets são proibidos.
12. Telemetria pode variar entre execuções.
13. Fase 1 não decide identidade jurídica.
14. Fase 1 não publica no bundle.

---

**Baseline Status: FROZEN**
