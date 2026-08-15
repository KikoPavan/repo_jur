# MEMORANDO DE DECISÃO ARQUITETURAL: PHASE 1 QUALITY GATE (`repo_jur`)

**Versão:** 1.0 (Baseline aprovada e congelada)  
**Data:** 12 de agosto de 2026  
**Status:** FROZEN  
**Referências de controle:** `arquitetura-fase2-repo-jur-v9-FROZEN.md`, `external-source-ingestion-contract-v1.5-FROZEN.md`, `legal-okf-profile-v1.3-FROZEN.md`, `lifecycle-field-ownership-v1.4-FROZEN.md`, `retrieval-contract-v2.4-FROZEN.md`, `decision-memo-ingress-transport-protocol-v1.0-FROZEN.md`, `decision-memo-pdf-source-cardinality-v1.0-FROZEN.md`, `decision-memo-duplicate-act-handling-v1.0-FROZEN.md`, `decision-memo-stable-concept-identity-v1.0-FROZEN.md` e `decision-memo-verification-history-schema-v1.0-FROZEN.md`.

---

## 1. Problem Statement

A **Open Decision — Phase 1 Quality Gate** deve definir quando a saída da Fase 1:

1. pode seguir para o Produtor OKF;
2. pode seguir com warnings técnicos registrados;
3. deve ser bloqueada por não existir saída física suficientemente conformante.

A Fase 1 converte a evidência PDF preservada em:

- Markdown literal com rastreabilidade física de páginas;
- JSON técnico de execução.

O Quality Gate avalia **qualidade e conformidade da conversão física**. Ele não avalia mérito jurídico, identidade lógica do ato, lifecycle OKF, confiança jurídica ou publicação canônica.

---

## 2. Frozen Constraints

1. **Fase 1 produz Markdown literal + JSON técnico.** **[Existing FROZEN Requirement]**
2. **Marcadores `[[Pág. N]]` preservam a numeração física do PDF.** **[Existing FROZEN Requirement]**
3. **Fase 1 é engine-neutral.** Nenhum parser, OCR engine, provedor ou modelo é normativo nesta decisão. **[Existing FROZEN Requirement]**
4. **OCR é fallback operacional quando necessário.** **[Existing FROZEN Requirement]**
5. **Uso de OCR ou warning de OCR não implica rejeição automática.** **[Existing FROZEN Requirement]**
6. **Falha fatal ocorre quando não é possível produzir saída física conformante.** **[Existing FROZEN Requirement]**
7. **Metadados técnicos de conversão permanecem no JSON técnico, não no frontmatter/body canônico.** **[Existing FROZEN Requirement]**
8. **Quality Gate não cria `verified`, não altera `status` e não decide identidade jurídica.** **[Existing FROZEN Requirement]**
9. **PDF original já está preservado em Object Storage antes da Fase 1.** **[Existing FROZEN Requirement]**
10. **ITP/1.0 e preflight estão CLOSED.** O Quality Gate não reabre validação de transporte. **[Existing FROZEN Requirement]**
11. **A Fase 1 trabalha sobre a evidência física completa.** A posterior divisão em concepts pertence ao Produtor OKF; o Quality Gate não define ranges de concepts. **[Existing FROZEN Requirement]**

---

## 3. Quality Dimensions

O gate avalia cinco dimensões:

### 3.1 Page Coverage

- total de páginas conhecido;
- exatamente um marcador `[[Pág. N]]` por página física;
- sequência 1..N na saída integral da Fase 1;
- nenhuma página silenciosamente omitida ou duplicada.

### 3.2 Structural Conformance

- Markdown decodificável em UTF-8;
- marcador de página parseável;
- JSON técnico parseável e conforme ao schema vigente;
- ausência de corrupção estrutural da saída.

### 3.3 Extraction Outcome

Cada página deve possuir resultado técnico explícito no JSON, por exemplo:

- `native_text`
- `ocr`
- `hybrid`
- `blank`
- `error`

Os nomes exatos podem ser normalizados pelo schema da Fase 1, desde que não dependam de um engine específico.

### 3.4 Textual Integrity

O gate deve detectar condições objetivas como:

- saída vazia incompatível com a página de origem;
- bytes/controle incompatíveis com texto UTF-8 válido;
- truncamento conhecido;
- erro explícito do extrator;
- conteúdo manifestamente corrompido por regras determinísticas.

Métricas heurísticas podem complementar observabilidade, mas não substituem regras fatais.

### 3.5 Technical Traceability

O relatório deve permitir relacionar:

- evidência de entrada;
- versão lógica da Fase 1;
- configuração relevante;
- página;
- método de extração;
- warnings/errors;
- resultado do Quality Gate.

---

## 4. Candidate Gate Models

### 4.1 Score-Only

Um score agregado decide aprovação.

**Rejeitado.**

Uma média pode esconder uma página crítica completamente perdida e introduz threshold arbitrário como autoridade de aceitação.

### 4.2 Strict Deterministic Gate

Somente regras booleanas determinam aprovação/rejeição.

É seguro e auditável, mas pode perder informação útil de observabilidade.

### 4.3 Deterministic Gate + Non-Authoritative Diagnostics

Regras determinísticas decidem `PASS`, `PASS WITH WARNINGS` ou `FAIL`.

Métricas e scores, se produzidos, são **diagnósticos opcionais**. Nunca:

- convertem FAIL em PASS;
- convertem warning em PASS;
- autorizam publicação;
- substituem uma regra de integridade.

**[New Decision Proposal]**

---

## 5. Recommended Decision

Adotar o **Modelo 4.3 — Deterministic Gate + Non-Authoritative Diagnostics**.

### 5.1 Estados normativos

O Quality Gate possui exatamente três resultados:

- **PASS**
- **PASS WITH WARNINGS**
- **FAIL**

### 5.2 Sem score normativo

Não existe threshold agregado obrigatório de 0–100 nesta baseline.

Uma implementação pode calcular score diagnóstico, confidence ou métricas similares, mas:

- são opcionais;
- sua fórmula não é parte do contrato;
- não participam da decisão normativa;
- devem ser identificados como telemetria/diagnóstico.

### 5.3 Significado dos resultados

**PASS:** saída física conformante e sem warnings técnicos ativos.

**PASS WITH WARNINGS:** saída física conformante, completa e apta a seguir ao Produtor OKF, mas com warnings não fatais registrados.

**FAIL:** a Fase 1 não produziu saída física suficientemente conformante para seguir ao Produtor OKF.

PASS/PASS WITH WARNINGS significam apenas **eligible to proceed to the Producer**. Não significam incorporação/publicação automática no bundle.

---

## 6. PASS Criteria

O resultado é **PASS** quando cumulativamente:

1. o PDF de entrada possui `N >= 1` páginas físicas;
2. o Markdown integral contém exatamente `N` marcadores `[[Pág. 1]]` ... `[[Pág. N]]`;
3. não há marker ausente, duplicado ou fora de ordem;
4. todas as páginas possuem resultado técnico concluído, não `error`;
5. páginas legitimamente vazias continuam representadas por seu marcador;
6. não há truncamento conhecido;
7. não há erro de parsing/extraction não resolvido;
8. o Markdown é UTF-8 válido e atende ao contrato físico da Fase 1;
9. o JSON técnico é válido e contém os campos mínimos obrigatórios;
10. não há warning técnico ativo;
11. não há alteração/invenção semântica conhecida introduzida pelo pipeline.

### OCR e PASS

**OCR utilizado com sucesso pode resultar em PASS.**

O simples fato de uma página ter usado OCR:

- não é falha;
- não é warning obrigatório;
- é uma informação técnica/observabilidade.

Se OCR produzir saída conformante sem warning ativo, o documento pode receber PASS.

**[New Decision Proposal]**

---

## 7. PASS WITH WARNINGS Criteria

O resultado é **PASS WITH WARNINGS** somente quando:

1. todos os critérios estruturais/completude necessários para prosseguir são satisfeitos;
2. nenhuma página está em `error`;
3. nenhuma página foi silenciosamente omitida;
4. existe pelo menos um warning técnico não fatal.

Exemplos admissíveis:

- retry de OCR/extraction ocorreu e posteriormente concluiu com saída íntegra;
- engine emitiu warning não fatal preservado no relatório;
- fonte apresenta baixa legibilidade, mas foi possível produzir representação fiel/conformante;
- página contém característica visual/estrutural incomum que merece auditoria, sem perda conhecida de conteúdo;
- métrica de sanidade disparou alerta, mas nenhuma regra fatal foi violada.

### Não são warnings por si só

Não devem gerar `PASS WITH WARNINGS` automaticamente:

- uso de OCR;
- página genuinamente vazia;
- normalização de line ending exigida pelo contrato;
- execução lenta;
- arquivo grande;
- engine específico utilizado.

Esses itens são observabilidade, salvo se acompanhados por uma condição técnica relevante.

---

## 8. FAIL Criteria

O resultado é **FAIL** se ocorrer qualquer uma das condições abaixo e ela não for resolvida na própria execução:

### 8.1 Integridade de páginas

- número de markers diferente do total de páginas;
- marker ausente;
- marker duplicado;
- sequência fora de ordem;
- página física silenciosamente ignorada.

### 8.2 Falha de extração

- página com conteúdo que termina em estado `error`;
- caminho de fallback necessário indisponível ou falho;
- timeout/erro externo persistente após política bounded de retry;
- retorno vazio quando a página não foi determinada como realmente vazia;
- truncamento conhecido da saída.

### 8.3 Corrupção estrutural/textual objetiva

- Markdown não é UTF-8 válido;
- JSON técnico inválido;
- presença de bytes NUL/controle proibidos pelo contrato textual;
- corrupção determinística conhecida do decoder/parser;
- conteúdo binário introduzido indevidamente na saída textual.

### 8.4 Falha do relatório

- JSON técnico não gerado;
- page inventory incompleto;
- input SHA-256 ausente;
- total de páginas ausente;
- resultado do Quality Gate ausente;
- errors/warnings necessários não registrados.

### 8.5 Sem threshold heurístico fatal implícito

“Quantidade alta de caracteres estranhos” não se torna FAIL apenas por um percentual não congelado.

Se a implementação possuir detector determinístico comprovado de corrupção, a regra específica pode ser fatal. Caso contrário, sinais heurísticos ficam como warning/diagnóstico até que uma regra objetiva seja aprovada.

---

## 9. Page Integrity Rules

### 9.1 Saída integral da Fase 1

A saída física da Fase 1 corresponde ao **PDF integral aceito**.

Para PDF de N páginas:

```text
[[Pág. 1]]
...
[[Pág. 2]]
...
...
[[Pág. N]]
...
```

Cada página aparece exatamente uma vez.

### 9.2 Página genuinamente vazia

Uma página realmente vazia:

- mantém `[[Pág. N]]`;
- possui `state: blank` (ou equivalente no JSON);
- não exige inserir comentário técnico no Markdown;
- não é warning obrigatório.

Método de conversão e classificação de página pertencem ao JSON técnico.

### 9.3 Página aparentemente vazia

Se a extração retornar vazio, mas não houver confirmação suficiente de que a página é realmente vazia:

1. tentar o caminho de fallback autorizado;
2. se ainda não for possível produzir representação conformante, resultado FAIL.

### 9.4 Concepts posteriores

O Quality Gate **não divide o PDF em concepts**.

Quando o Produtor OKF posteriormente criar concepts a partir de subconjuntos de páginas, a numeração física original deve ser preservada conforme as baselines existentes.

Concepts sintéticos/multi-source não são objeto deste gate.

---

## 10. OCR / Partial Processing

### 10.1 OCR

OCR permanece fallback engine-neutral.

O Quality Gate não define:

- provedor;
- modelo;
- API;
- credenciais;
- endpoint;
- número de parâmetros específicos do engine.

### 10.2 Retry

Falhas transitórias podem receber política bounded de retry configurável.

Esta baseline **não congela “3 tentativas”**, backoff específico ou códigos HTTP particulares.

O relatório técnico deve registrar:

- número de tentativas;
- resultado final;
- erro sanitizado quando houver.

### 10.3 `allow_partial`

`allow_partial` pode existir como **modo operacional de diagnóstico/recuperação**, mas não modifica a decisão normativa.

Se uma ou mais páginas permanecerem sem representação física conformante:

- Quality Gate = **FAIL**;
- o Markdown parcial, se produzido, é **noncanonical diagnostic artifact**;
- o artefato fica fora do caminho de entrada do Produtor OKF;
- erros/páginas afetadas são registrados no JSON;
- uma revisão humana pode orientar correção, nova aquisição da fonte ou novo processamento;
- para prosseguir ao Produtor OKF, uma nova execução deve obter PASS ou PASS WITH WARNINGS.

### 10.4 Sem waiver humano do gate físico

Revisão humana não transforma diretamente um artefato parcial FAIL em saída canônica da Fase 1.

A correção precisa resultar em nova saída que satisfaça o gate.

Isso evita que `allow_partial` se torne atalho para perda conhecida de páginas.

### 10.5 Texto ilegível na própria fonte

Se o **documento fonte** for realmente ilegível em determinado trecho, isso é diferente de uma falha de processamento.

A representação literal dessa ilegibilidade segue a especificação textual da Fase 1. O Quality Gate apenas exige que:

- a condição seja explicitamente registrada;
- não seja inventado texto;
- não seja confundida com erro silencioso do pipeline.

Este memo não cria novo sentinel Markdown obrigatório.

---

## 11. Technical Report

### 11.1 Finalidade

O JSON técnico deve ser engine-neutral e suficiente para auditoria/reexecução.

### 11.2 Núcleo mínimo recomendado

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
  "pages": [
    {
      "page_number": 1,
      "method": "native_text",
      "char_count": 0,
      "warnings": [],
      "errors": []
    }
  ],
  "telemetry": {}
}
```

### 11.3 Regras

Obrigatórios:

- versão do schema;
- execution ID;
- SHA-256 e tamanho da evidência;
- page count;
- identidade/versão lógica da implementação;
- fingerprint da configuração relevante;
- resultado do gate;
- inventário completo de páginas;
- warnings/errors;
- hash do Markdown quando houver saída final.

### 11.4 Engine-specific details

Informações como:

- library/package;
- OCR provider;
- model;
- confidence;
- retry telemetry;

podem existir como campos opcionais/extensões técnicas.

Nenhum package, modelo ou provider específico é obrigatório pelo contrato.

### 11.5 Segredos

É proibido registrar no JSON técnico:

- API keys;
- tokens;
- passwords;
- cookies;
- headers de autenticação;
- credentials;
- secrets equivalentes.

Somente identificadores/configuração **não secretos** ou fingerprints sanitizados podem ser persistidos.

### 11.6 Paths

Paths absolutos temporários do host não são identidade nem proveniência canônica.

Podem existir como debugging efêmero, mas não são campos obrigatórios do contrato persistente.

---

## 12. Retry / Idempotency

### 12.1 Idempotência lógica

Para:

- mesmos bytes de entrada;
- mesma versão lógica de processamento;
- mesma configuração relevante;

a Fase 1 deve produzir **Markdown literal deterministicamente equivalente** e o mesmo resultado determinístico do Quality Gate.

### 12.2 JSON técnico

O JSON técnico contém duas classes de informação:

**Determinística/reprodutível:**

- input hash;
- page count;
- versão lógica;
- config fingerprint;
- page outcomes;
- gate result;
- warnings/errors decorrentes do conteúdo/configuração.

**Telemetria por execução:**

- `execution_id`;
- started/completed timestamps;
- duration;
- retry timing;
- host/runtime observations.

Telemetria pode variar entre execuções e, portanto, o JSON completo **não precisa ser byte-a-byte idêntico**.

### 12.3 Falha posterior

Uma execução FAIL:

- não sobrescreve silenciosamente uma saída válida anterior;
- produz seu próprio relatório de falha fora do bundle;
- não invalida automaticamente artefato anterior;
- não chega ao Produtor como substituição válida.

A seleção de qual execução será utilizada deve ser explícita no pipeline.

---

## 13. Invariants

1. Nenhuma página física desaparece silenciosamente.
2. Saída integral da Fase 1 preserva markers 1..N.
3. Página vazia legítima preserva o marker.
4. Método de extração pertence ao JSON técnico, não ao corpo literal.
5. OCR não é falha nem warning por definição.
6. Um documento pode obter PASS mesmo usando OCR.
7. PASS WITH WARNINGS exige saída completa/conformante.
8. FAIL nunca segue ao Produtor OKF.
9. `allow_partial` não converte FAIL em sucesso.
10. Artefato parcial é diagnóstico e não canônico.
11. Nenhum score diagnóstico decide aceitação.
12. Quality Gate permanece engine-neutral.
13. JSON técnico não contém secrets.
14. Retry policy é bounded/configurável, não fixada em número arbitrário nesta baseline.
15. JSON de telemetria pode variar; conteúdo determinístico deve permanecer equivalente.
16. Quality Gate não cria `verified`, não altera `status` e não decide identidade jurídica.
17. Quality Gate não define segmentação em concepts.
18. Quality Gate não reabre ITP/preflight.
19. Metadados técnicos não são promovidos automaticamente ao frontmatter.
20. PASS/PASS WITH WARNINGS tornam a saída elegível ao Produtor, não garantem publicação no bundle.

---

## 14. Required Baseline Updates

Após aprovação e congelamento:

### 14.1 ESIC

Criar versão controlada que:

- marque `Phase 1 Quality Gate` como CLOSED;
- registre os estados `PASS`, `PASS WITH WARNINGS`, `FAIL`;
- mantenha warnings/OCR sem rejeição automática;
- deixe explícito que o gate ocorre **depois do preflight**;
- mantenha `allow_partial` apenas como artefato FAIL de diagnóstico, fora do caminho do Produtor;
- remova a Open Decision da lista.

### 14.2 Architecture Phase 2

Criar versão controlada que:

- marque `Phase 1 Quality Gate` como CLOSED;
- remova a decisão das próximas decisões;
- registre que somente PASS/PASS WITH WARNINGS podem seguir da Fase 1 ao Produtor;
- preserve Fase 1 engine-neutral.

### 14.3 Phase 1 implementation/specification

A especificação operacional da Fase 1 deve ser sincronizada para:

- regras do gate;
- page inventory;
- JSON técnico mínimo;
- partial diagnostic mode;
- retry bounded/configurável;
- separação entre campos determinísticos e telemetria.

Essa sincronização não transforma packages/engines específicos em requisitos arquiteturais.

### 14.4 Baselines sem mudança normativa necessária

Não é necessária nova versão normativa de:

- Legal OKF Profile;
- Lifecycle & Field Ownership;
- Concept Identity & Physical Structure;
- Retrieval Contract.

O Quality Gate não altera seus schemas ou ownership.

---

## 15. Remaining Open Questions

Após o fechamento desta decisão, **não permanece Open Decision de ingestão/produção canônica identificada por esta baseline**.

Permanecem, no Retrieval Contract:

- **Search Execution Path**
- **Chunking Strategy**
- **Reranking Pipeline**

### Itens de implementação/calibração não bloqueantes

Não são promovidos a Open Decisions arquiteturais nesta baseline:

- heurísticas de detecção de mojibake/garbage;
- detecção de watermark/carimbos;
- tuning de concorrência;
- número de retries;
- fórmulas de score diagnóstico;
- thresholds de observabilidade específicos de engine.

Esses itens podem evoluir por configuração e testes enquanto preservarem os invariantes acima.

---

## 16. Technical Review Corrections

A revisão técnica corrigiu os seguintes pontos da proposta inicial:

1. removeu **zero OCR** dos critérios de PASS; OCR bem-sucedido pode resultar em PASS;
2. deixou de classificar uso de OCR como warning obrigatório;
3. deixou de classificar página genuinamente vazia como warning obrigatório;
4. removeu comentários técnicos de método do corpo Markdown; método pertence ao JSON técnico;
5. retirou segmentação de concepts/synthetic concepts do escopo do Quality Gate da Fase 1;
6. transformou score 0–100 em diagnóstico opcional, sem threshold normativo;
7. manteve exatamente três estados normativos: PASS, PASS WITH WARNINGS e FAIL;
8. tornou `allow_partial` um modo diagnóstico cujo resultado continua FAIL;
9. proibiu incorporação direta de artefato parcial mesmo após simples waiver humano;
10. removeu `[[TEXTO ILEGÍVEL]]` como novo sentinel obrigatório criado por este memo;
11. substituiu erros específicos de provider/API/model por falhas engine-neutral;
12. removeu número fixo de 3 retries; retry é bounded e configurável;
13. corrigiu idempotência: Markdown e campos determinísticos devem ser equivalentes, mas telemetria do JSON pode variar;
14. removeu packages, versões e modelos específicos como requisitos do JSON técnico;
15. proibiu persistência de credentials/secrets no relatório técnico;
16. removeu paths absolutos temporários como campos obrigatórios;
17. corrigiu PASS/PASS WITH WARNINGS para “eligible to proceed to Producer”, não publicação automática;
18. separou Quality Gate de preflight/ITP;
19. removeu atualização normativa desnecessária de Legal OKF Profile, Lifecycle e Retrieval;
20. classificou thresholds de mojibake, watermark e tuning de performance como implementação/calibração, não novas Open Decisions arquiteturais.

---

**Decision Status: APPROVED — CLOSED — FROZEN**
