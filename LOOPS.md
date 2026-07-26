# Loop de implementação

Mudança ativa:

`establish-juridical-pdf-conversion-pipeline`

Fluxo:

1. Claude identifica a primeira subtarefa não marcada.
2. OpenCode implementa e testa somente essa subtarefa.
3. Codex verifica sem editar arquivos.
4. Claude marca a subtarefa após aprovação explícita.
5. O ciclo recomeça na próxima subtarefa.

Após duas tentativas sem progresso, interromper o ciclo e informar o erro.

OCR real e arquivamento exigem aprovação humana.
