> Mudança exclusivamente diagnóstica (instrução explícita do usuário: "SEM implementar correções"). Conclusão: conversor adequado como base para processos judiciais de 1º grau em texto nativo, com 2 defeitos novos determinísticos delimitados (Categoria C, ambos em `100-106-DECISÃO.pdf`, páginas 1–5, mesma causa raiz upstream em MarkItDown) e 1 variação nova de uma limitação já conhecida e aceita (Categoria B). Nenhuma implementação foi feita. Ver `design.md` para a evidência completa e `proposal.md` para o resumo executivo.

## 0. Diagnóstico (concluído)

- [x] 0.1 Baseline: `git status --short`, HEAD, `uv run pytest tests/`, `openspec validate --all --strict`. Resultado: repo limpo, HEAD `1f24617`, 354/354 testes passando, 1/1 spec válida. `design.md`, ETAPA 1.
- [x] 0.2 Inspecionar os 4 PDFs de `input/processos_auditoria/` via PyMuPDF (páginas, caracteres nativos por página, imagens, blocos, sem OCR). `design.md`, ETAPA 2.
- [x] 0.3 Converter os 4 PDFs com `converter-juridico --no-ocr`, saída isolada em `audit_output/` (via `OUTPUT_DIR`/`LOGS_DIR`), sem sobrescrever `output/`. Resultado: 3/4 sucesso (`texto_nativo` em 100% das páginas); 1/4 (`Testamento Publico.pdf`) corretamente bloqueado por inteiro em modo estrito (nenhuma página contornada). `design.md`, ETAPA 3.
- [x] 0.4 Auditar página a página (PDF nativo vs. Markdown gerado), classificando cada achado em A–F. Resultado: `Petição Inicial` = A (paridade exata de tokens, 7/7 páginas); `Testamento Publico` = D (100% dependente de OCR, bloqueio correto); `CONTESTAÇÃO` = A (única diferença é remoção correta de timbre repetitivo, comportamento já validado); `DECISÃO` = 2 achados C + 1 achado B. `design.md`, ETAPA 4.
- [x] 0.5 Para cada achado novo, documentar arquivo/página, trecho antes/depois, etapa responsável, causa raiz isolada e reproduzida isoladamente, generalidade, gravidade, viabilidade de critério determinístico, risco de regressão e recomendação de mudança futura. `design.md`, ETAPA 5 (achados C.1, C.2, B.1).
- [x] 0.6 Confirmar não regressão do corpus canônico (4 documentos, hashes MD5 inalterados, nenhuma reconversão) e ausência total de chamadas de OCR/LLM. `design.md`, "Verificação de não regressão do corpus canônico".

## 1. Encerramento do ciclo

- [x] 1.1 Claude (orquestrador) executou todo o diagnóstico diretamente (sem Codex/OpenCode), por se tratar de tarefa de auditoria/análise, não de implementação de código em `src/`/`tests/` — consistente com `AGENTS.md` (Codex é exclusivamente o implementador; esta mudança não implementa nada).
- [x] 1.2 Nenhum código, teste, dependência ou corpus canônico foi alterado; commit local (sem push) desta mudança e de suas saídas de auditoria, sem arquivar (instrução explícita do usuário).
- [x] 1.3 Atualizar `LOOPS.md` com o resultado desta auditoria e os candidatos a futuras mudanças (C.1, C.2, B.1).
