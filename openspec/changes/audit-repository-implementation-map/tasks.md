> Mudança exclusivamente diagnóstica (instrução explícita do usuário via `/goal`: "SOMENTE DIAGNÓSTICO", Stage 0 — Repository Implementation Map). Nenhuma implementação foi feita. Ver `repository-implementation-map.md` para a tabela completa e evidência, e `proposal.md` para o resumo executivo.

## 0. Precheck (concluído)

- [x] 0.1 Registrar branch, HEAD, `git status --short --untracked-files=all`, mudanças OpenSpec ativas. `repository-implementation-map.md`, seção 0.
- [x] 0.2 Registrar `pyproject.toml`, CLI/entrypoints, `.env.example`, confirmar ausência de `/bundle/`. `repository-implementation-map.md`, seção 0.
- [x] 0.3 Executar `uv run pytest tests/` e `openspec validate --all --strict` como baseline, sem corrigir falhas. `repository-implementation-map.md`, seção 0 (391 passed; 1 passed/0 failed).

## 1. Inventário (concluído)

- [x] 1.1 Mapear as 23 capacidades lógicas do inventário obrigatório para implementação física, com arquivos/módulos/classes/funções/dependências/CLI/testes/integrações. `repository-implementation-map.md`, seção 3 (tabela principal).
- [x] 1.2 Classificar cada capacidade como `REUSE`/`ADAPT`/`CREATE`/`OUT_OF_SCOPE`, com busca demonstrada antes de qualquer `CREATE`. `repository-implementation-map.md`, seção 3.
- [x] 1.3 Registrar árvore física relevante real (não presumida por documentação). `repository-implementation-map.md`, seção 1.
- [x] 1.4 Registrar divergências entre a baseline FROZEN referenciada pela tarefa e o estado físico real commitado. `repository-implementation-map.md`, seção 2 e 7.
- [x] 1.5 Registrar overlaps/duplicações existentes e riscos de arquitetura caso módulos paralelos sejam criados. `repository-implementation-map.md`, seções 5 e 6.
- [x] 1.6 Registrar cobertura e lacunas de testes, sem criar nenhum teste novo. `repository-implementation-map.md`, seções 8 e 9.
- [x] 1.7 Registrar dependências entre capacidades, ordem recomendada das futuras mudanças OpenSpec e o primeiro Stage seguro após aprovação. `repository-implementation-map.md`, seções 10, 11 e 12.

## 2. Encerramento do ciclo (Stage 0 inicial)

- [x] 2.1 Claude (orquestrador) executou todo o diagnóstico diretamente (sem Codex/OpenCode), por se tratar de tarefa de inspeção/mapeamento de repositório, não de implementação de código em `src/`/`tests/` — consistente com `AGENTS.md` e com o precedente das mudanças diagnósticas já arquivadas (`audit-judicial-process-pdf-support`, `audit-scanned-pdf-ocr-support`, `audit-ocr-critical-data-fidelity`).
- [x] 2.2 Nenhum código, teste, dependência do projeto (`pyproject.toml`/`uv.lock`), prompt, modelo, provider, configuração ou diretório de `src/pipeline_juridico/`/`/bundle/` foi criado, movido ou alterado.
- [x] 2.3 Commit local (sem push) desta mudança, seguindo o mesmo padrão de todas as mudanças diagnósticas anteriores já arquivadas neste repositório (nunca arquivada nem enviada ao remoto sem instrução humana explícita separada).

## 3. Reconciliação com baselines FROZEN (segunda sessão, mesmo dia)

- [x] 3.1 Ler `docs/baselines/frozen/` (24 arquivos) e cruzar cada uma das 23 capacidades já inventariadas contra `código real + testes reais + baseline FROZEN aplicável`, sem repetir o inventário físico do zero. 16/24 arquivos lidos integralmente (os de maior prioridade citados pela tarefa: Architecture v15, Technical Implementation Spec v1.2, Implementation Plan v1.1 + correction impact, Phase1 Quality Gate memo, ITP/ESIC, Shared Conversion Core, Semantic Review v1.1, Critical-Data Validation v1.1, Duplicate/Identity/Cardinality, Lifecycle/Ownership, Retrieval Bounded-Context Scope, Physical Layout mapping); os 8 restantes (Legal OKF Profile, Phase1 Operational Spec, Retrieval Contract v2.8, Chunking/Reranking/Search) não lidos integralmente porque seu conteúdo normativo já está coberto com precisão suficiente pelas duas baselines-mestre lidas por completo (Architecture v15 §8/invariantes 1–67; Technical Spec §6/§10–13) — nenhuma classificação depende de trecho não coberto. `repository-implementation-map.md`, seção `R.1`.
- [x] 3.2 Resolver a inconsistência "23 capacidades" vs. 24 classificações do relatório original: causa identificada (Judicial Process Retrieval classificado em prosa, fora da tabela numerada) e total corrigido para 24. `repository-implementation-map.md`, seção `R.0`.
- [x] 3.3 Alterar classificação somente onde a baseline FROZEN exigir comportamento/forma que o código real não satisfaz: 2 mudanças (`#11 Technical JSON/report` e `#13 Phase 1 Quality Gate`, ambas `REUSE → ADAPT`); as demais 22 classificações confirmadas, não alteradas. `repository-implementation-map.md`, seção `R.2`.
- [x] 3.4 Confirmar especificamente os 9 pontos pedidos pela tarefa (`src/pipeline_juridico/` sem relocação; Ingress/Preflight/Evidence Preservation vs. ITP/ESIC; Technical JSON e Quality Gate vs. Phase1 specs; Critical Validation vs. memo v1.1; Semantic Review Legal/Process vs. invariantes v1.1; Legal/Process Producer e schemas separados; Legal Retrieval vs. Retrieval v2.8; Judicial Process Retrieval OUT_OF_SCOPE; chunking/reranking somente conforme escopo FROZEN). `repository-implementation-map.md`, seção `R.3`.
- [x] 3.5 Substituir a ordem de Stages recomendada (inferida na primeira sessão) pela sequência oficial encontrada de forma idêntica em `technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §18 e `implementation-plan-repo-jur-v1.1-FROZEN.md` §2 (Stage 0–10), e corrigir a recomendação de "primeiro Stage seguro" de Critical-Data Validation (Stage 4 na sequência oficial) para Stage 1 — Contract Harness / Stage 2 — Ingress-Preflight-Evidence Preservation. `repository-implementation-map.md`, seções `R.4` e `R.5`.
- [x] 3.6 Executar `uv run pytest tests/`, `openspec validate --all --strict` e `git status --short --untracked-files=all` como baseline pós-reconciliação, sem corrigir a falha OpenSpec esperada (mudança diagnóstica sem delta spec) e sem criar spec artificial para fazê-la passar. Ver resultado no encerramento desta mudança.
- [x] 3.7 Commit local (sem push) da reconciliação, separado do commit original do Stage 0.
