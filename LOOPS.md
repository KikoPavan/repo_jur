# Loop de implementação

Mudança ativa:

`fix-jurisprudence-precedent-fusion` — corrige a fusão indevida entre dois precedentes jurisprudenciais consecutivos em `recompose_native_paragraphs`, detectada em `AINTARESP_1462304-PA.pdf` após o R01. Aberta em 2026-07-30, não arquivar sem aprovação humana explícita.

Histórico:

- `establish-juridical-pdf-conversion-pipeline` foi concluída e arquivada em 2026-07-27.
- `improve-markdown-cleanup-structuring` foi concluída (grupos 0–9, incluindo o defeito R01 de recomposição determinística de parágrafos) e arquivada em 2026-07-30 (`openspec/changes/archive/2026-07-30-improve-markdown-cleanup-structuring/`). Detalhes e métricas de cada rodada de validação em `RELATORIO_FINAL.md` dentro dessa pasta.

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
