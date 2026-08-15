## Why

Instrução explícita do usuário (via `/goal`) para executar exclusivamente o **Stage 0 — Repository Implementation Map**: inspecionar o estado físico real de `repo_jur` e mapear cada uma de 23 capacidades arquiteturais lógicas (de baselines FROZEN presumidas como vigentes) para sua implementação física existente, antes de qualquer futura mudança de código.

Esta mudança é **exclusivamente diagnóstica**. Não implementa código, não cria/move módulos ou diretórios (além desta própria mudança OpenSpec), não cria adapters/facades, não refatora, não altera configuração ou testes, não executa OCR/LLM externo, não modifica `/bundle/` (que não existe neste repositório), não arquiva e não faz push.

## Achado central

Busca textual em todo o repositório não encontrou nenhuma ocorrência da terminologia da baseline FROZEN referenciada pela tarefa (`ITP`, `Preflight`, `Evidence Preservation`, `Domain Router`, `Legal/Process Producer`, `Process Storage`, `Legal Knowledge Retrieval`, `chunking/reranking`) em nenhum documento commitado. A única baseline arquitetural física é `docs/Pipeline_Conversao_Juridica_Corrigido.md`, cobrindo integralmente a Fase 1 (implementada) e, na §20, apenas a Fase 2 do lado Legal (revisão semântica + YAML Frontmatter, "planejado, não implementado"). Essa baseline FROZEN é, portanto, externa a este repositório.

## Resultado (resumo — tabela completa e evidência em `repository-implementation-map.md`)

Das 23 capacidades lógicas mapeadas:
- **8 REUSE** — já satisfazem integralmente a baseline: receiver SHA-256, Shared Conversion Core (o próprio `src/pipeline_juridico/`), MarkItDown/markitdown-ocr, cliente Gemini/OpenAI-compatible, OCR routing, page markers, Technical JSON/report, Phase 1 Quality Gate.
- **6 ADAPT** — funcionalidade real existe, mas não formalizada sob o nome/generalização da capacidade: ITP/Ingress, Preflight, Evidence Preservation, `ConversionEngine`/interface, observability/logging, schemas/contracts comuns.
- **9 CREATE** — nenhuma implementação equivalente encontrada: Post-OCR Critical-Data Validation, Domain Router, Legal Semantic Review, Legal Producer, Process Semantic Review, Process Producer, Process Storage, Legal Knowledge Retrieval, chunking/reranking.
- **1 OUT_OF_SCOPE** — Judicial Process Retrieval, por instrução explícita da tarefa.

**Primeiro Stage seguro recomendado após aprovação deste mapa:** Post-OCR Critical-Data Validation — único candidato sem dependência de capacidade ainda ausente, com achado real já confirmado pela auditoria arquivada `audit-ocr-critical-data-fidelity` (commit `4759696`) e extensão natural de `validator.py` já existente. Ordem completa recomendada das 9 mudanças `CREATE` em `repository-implementation-map.md`, seção 11.

## Validação (baseline, nada corrigido)

`uv run pytest tests/` → 391 passed, 0 failed. `openspec validate --all --strict` → 1 passed, 0 failed. Nenhuma falha encontrada para registrar.

## Reconciliação com baselines FROZEN (segunda sessão, mesmo dia)

`docs/baselines/frozen/` (24 arquivos) passou a existir fisicamente após o Stage 0 acima. Nova instrução explícita do usuário (via `/goal`): reconciliar o mapa já produzido contra essas baselines, sem repetir o inventário do zero. Resultado (evidência completa em `repository-implementation-map.md`, seção `R`):

- **Total corrigido: 24 capacidades**, não 23 — o relatório original já havia classificado `Judicial Process Retrieval` como `OUT_OF_SCOPE` em prosa, mas nunca a promoveu à tabela numerada nem ao total declarado (seção `R.0`).
- **2 classificações alteradas, ambas `REUSE → ADAPT`:** `#11 Technical JSON/report` e `#13 Phase 1 Quality Gate` — o código atual é funcionalmente equivalente em espírito, mas não replica o schema/vocabulário normativo exato exigido (`PASS`/`PASS_WITH_WARNINGS`/`FAIL`; `execution_id`/`logical_processing_version`/`relevant_config_fingerprint`) (seção `R.2`).
- **As demais 22 classificações foram confirmadas**, com lacunas agora descritas com citação precisa de baseline/interface (ex.: `CriticalDataValidator`, `ConversionEngine`, `LexicalIndexBackend`, fluxo de publicação de 9 passos do Legal Producer).
- **Ordem de Stages corrigida:** as baselines agora disponíveis definem, de forma idêntica em `technical-implementation-spec-repo-jur-v1.2` §18 e `implementation-plan-repo-jur-v1.1` §2, uma sequência oficial Stage 0→10 que diverge da recomendação inferida na primeira sessão — Critical-Data Validation é Stage 4 (depois de Ingress/Preflight/Evidence Preservation e do wrap do `ConversionEngine`), não o primeiro passo (seções `R.4`/`R.5`).
- **Primeiro Stage seguro recomendado (corrigido):** Stage 1 — Contract Harness (consolidação do que já é `REUSE`/`ADAPT`); primeiro Stage com volume real de código novo: Stage 2 — ITP/Ingress/Preflight/Evidence Preservation.

Validação pós-reconciliação (nada corrigido): `uv run pytest tests/` → 391 passed, 0 failed. `openspec validate --all --strict` → 1 passed, 1 failed (a mudança diagnóstica em si, por não ter delta spec — esperado e consistente com todas as auditorias diagnósticas anteriores deste repositório; nenhuma spec artificial foi criada para mascarar essa falha).

## Fora do escopo desta investigação

Implementação de qualquer capacidade `CREATE`; criação de módulos/diretórios/adapters; refatoração; alteração de configuração ou testes; chamada real de OCR/LLM; arquivamento; push. `src/pipeline_juridico/` foi apenas inspecionado, nunca movido. `var/ocr_final/` foi apenas listado no `git status`, nunca alterado.

## Capabilities

### New Capabilities
(nenhuma — mudança exclusivamente diagnóstica, não implementa)

### Modified Capabilities
(nenhuma)

## Impact

Nenhum código de produção, teste, configuração, dependência ou spec normativa foi alterado. Único artefato novo: esta pasta de mudança OpenSpec (`proposal.md`, `tasks.md`, `repository-implementation-map.md`).
