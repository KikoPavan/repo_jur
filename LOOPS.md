# Loop de implementação

Mudança ativa:

`fix-repeated-header-cross-page-fusion` (`openspec/changes/fix-repeated-header-cross-page-fusion/`) — todas as 4 subtarefas concluídas e verificadas (1.1 testes de regressão, 1.2 implementação, 1.3 suíte completa, 1.4 reconversão do corpus). Aguardando aprovação humana para arquivamento (não arquivar nem fazer push sem aprovação explícita).

Histórico:

- `establish-juridical-pdf-conversion-pipeline` foi concluída e arquivada em 2026-07-27.
- `improve-markdown-cleanup-structuring` foi concluída (grupos 0–9, incluindo o defeito R01 de recomposição determinística de parágrafos) e arquivada em 2026-07-30 (`openspec/changes/archive/2026-07-30-improve-markdown-cleanup-structuring/`). Detalhes e métricas de cada rodada de validação em `RELATORIO_FINAL.md` dentro dessa pasta.
- `fix-jurisprudence-precedent-fusion` foi concluída e arquivada em 2026-07-31 (commit de arquivamento `ff850e4`, `openspec/changes/archive/2026-07-31-fix-jurisprudence-precedent-fusion/`). Causa raiz: ausência de proteção contra fusão entre o fechamento de uma citação jurisprudencial e o início em caixa alta do precedente seguinte. Correção: verificação do parágrafo acumulado por regex antes da decisão de junção. Ocorrências corrigidas: `AINTARESP_1462304-PA.pdf` e `REsp_1704551-SP.pdf`. Validação: suíte `272/272`, quatro PDFs reconvertidos com `--no-ocr`, marcadores `[[Pág. N]]` preservados, `openspec validate --all --strict`: 1 passed, 0 failed.
- `fix-subtitulo-structural-boundaries` foi concluída e arquivada em 2026-08-06 (commit de arquivamento `26449ca`, `openspec/changes/archive/2026-08-06-fix-subtitulo-structural-boundaries/`). Causa raiz: `SUBTÍTULO`/`SUBTITULO` nunca fora incluído no vocabulário de marcadores estruturais de `cleaner.py` (`_LEGISLATIVE_MARKER_PATTERN`, `formal_structure_pattern`, `bare_structure_pattern`, `qualified_structure_pattern`, `heading_levels`), fazendo com que fosse tratado como texto comum e fundido ao artigo/parágrafo/inciso/TÍTULO anterior. Correção: SUBTÍTULO adicionado a esse vocabulário no nível Markdown `####` (mesmo de CAPÍTULO, confirmado no corpus real). Ocorrências corrigidas: as 8 do corpo de `L10.406_CC_2002.pdf`. Validação: suíte `278/278`, quatro PDFs reconvertidos com `--no-ocr` (nenhuma página exigiu OCR), índice final e os 3 demais arquivos do corpus byte-idênticos, `openspec validate --all --strict`: 2 passed, 0 failed durante a mudança / 1 passed após o arquivamento.

Regra geral do corpus de regressão (válida para qualquer mudança futura sobre esses 4 PDFs, não só a arquivada acima): todas as reconversões usam `converter-juridico --no-ocr`. Nenhuma mudança sobre este corpus deve alterar ou exercitar o caminho de OCR; página que exigir OCR sob `--no-ocr` é regressão de roteamento ou caso BLOQUEADO, nunca resolvido chamando a API Gemini.

Fluxo:

1. Claude identifica a primeira subtarefa não marcada.
2. Codex implementa e testa somente essa subtarefa.
3. Claude verifica (diff, testes, `openspec validate --strict`) sem que o Codex se autoaprove.
4. Claude marca a subtarefa e commita localmente (sem push) após aprovação explícita própria.
5. O ciclo recomeça na próxima subtarefa.

Nota: o OpenCode foi removido do fluxo em 2026-07-26 por instabilidade (travamentos recorrentes em execuções headless). Codex assumiu o papel de implementador; Claude assumiu a verificação final, já que o mesmo agente não deve implementar e aprovar sozinho.

Após duas tentativas sem progresso, interromper o ciclo e informar o erro.

OCR real e arquivamento exigem aprovação humana.
