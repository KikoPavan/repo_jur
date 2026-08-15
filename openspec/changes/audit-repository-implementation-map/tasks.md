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

## 2. Encerramento do ciclo

- [x] 2.1 Claude (orquestrador) executou todo o diagnóstico diretamente (sem Codex/OpenCode), por se tratar de tarefa de inspeção/mapeamento de repositório, não de implementação de código em `src/`/`tests/` — consistente com `AGENTS.md` e com o precedente das mudanças diagnósticas já arquivadas (`audit-judicial-process-pdf-support`, `audit-scanned-pdf-ocr-support`, `audit-ocr-critical-data-fidelity`).
- [x] 2.2 Nenhum código, teste, dependência do projeto (`pyproject.toml`/`uv.lock`), prompt, modelo, provider, configuração ou diretório de `src/pipeline_juridico/`/`/bundle/` foi criado, movido ou alterado.
- [x] 2.3 Commit local (sem push) desta mudança, seguindo o mesmo padrão de todas as mudanças diagnósticas anteriores já arquivadas neste repositório (nunca arquivada nem enviada ao remoto sem instrução humana explícita separada).
