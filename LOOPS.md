# Loop de implementação

Mudança ativa:

`establish-juridical-pdf-conversion-pipeline`

Fluxo:

1. Claude identifica a primeira subtarefa não marcada.
2. Codex implementa e testa somente essa subtarefa.
3. Claude verifica (diff, testes, `openspec validate --strict`) sem que o Codex se autoaprove.
4. Claude marca a subtarefa e commita localmente (sem push) após aprovação explícita própria.
5. O ciclo recomeça na próxima subtarefa.

Nota: o OpenCode foi removido do fluxo em 2026-07-26 por instabilidade (travamentos recorrentes em execuções headless). Codex assumiu o papel de implementador; Claude assumiu a verificação final, já que o mesmo agente não deve implementar e aprovar sozinho.

Após duas tentativas sem progresso, interromper o ciclo e informar o erro.

OCR real e arquivamento exigem aprovação humana.
