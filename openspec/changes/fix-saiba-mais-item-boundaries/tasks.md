## 1. Testes (TDD, antes de qualquer implementação)

- [ ] 1.1 Adicionar teste positivo (página 14 real): dois itens "Jurisprudência em Teses" originalmente independentes ficam em parágrafos/linhas separados, cada um preservado integralmente.
- [ ] 1.2 Adicionar teste positivo (página 18 real): um item "Jurisprudência em Teses" e o "Informativo de Jurisprudência" seguinte ficam separados.
- [ ] 1.3 Adicionar teste positivo (página 4 real): o precedente `CC 159976/SP, ... DJe 16/04/2019` e o "Informativo de Jurisprudência n. 474" seguinte ficam separados; a quebra de linha física interna do próprio precedente ("...julgado em" + "10/04/2019, DJe 16/04/2019") continua unida em uma só linha.
- [ ] 1.4 Adicionar teste garantindo que os demais itens da mesma seção `SAIBA MAIS` (ex. "Informativo de Jurisprudência n. 135/474/346/174" na página 4) permanecem cada um em seu próprio parágrafo, sem regressão.
- [ ] 1.5 Adicionar teste negativo: um bloco de 2 linhas físicas fora de qualquer seção `SAIBA MAIS` continua sendo unido ao bloco seguinte pela lógica geométrica normal (sem o novo guard interferir fora do intervalo).
- [ ] 1.6 Adicionar teste negativo: uma frase jurídica comum contendo as palavras "Informativo", "Jurisprudência", "/", "DJe" ou números, fora de uma seção `SAIBA MAIS`, não é dividida.
- [ ] 1.7 Adicionar teste negativo: `PROCESSO`, `TEMA`, `DESTAQUE`, `RAMO DO DIREITO`, `INFORMAÇÕES DO INTEIRO TEOR` continuam corretamente separados do conteúdo seguinte (comportamento pré-existente, sem regressão).
- [ ] 1.8 Adicionar teste negativo: o cabeçalho `SAIBA MAIS` em si permanece em parágrafo próprio, sem ser unido ao primeiro item da lista (comportamento pré-existente via `native_label_pattern`, sem regressão).
- [ ] 1.9 Adicionar teste negativo: os 4 casos R01, os 8 SUBTÍTULO e o índice do Código Civil permanecem intactos (reexecução dos testes de regressão existentes).
- [ ] 1.10 Adicionar teste negativo: rodapés técnicos já removidos e a normalização de thin-space permanecem intactos (reexecução dos testes de regressão existentes).
- [ ] 1.11 Adicionar teste negativo: o defeito `Papel/Nome` permanece inalterado (fora de escopo, não corrigido incidentalmente).
- [ ] 1.12 Rodar a suíte e confirmar que os novos testes falham (red) antes da implementação.

## 2. Implementação

- [ ] 2.1 Em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), adicionar detecção do intervalo `SAIBA MAIS`: ativo a partir de um bloco cuja única linha física é exatamente `SAIBA MAIS` (já reconhecido por `native_label_pattern`), até o próximo bloco cuja primeira linha física também corresponda a `native_label_pattern`.
- [ ] 2.2 Adicionar uma nova cláusula de exclusão a `should_join`: quando a linha atual está dentro do intervalo `SAIBA MAIS` E é a primeira linha física de um novo bloco (transição entre blocos, não continuação de linha física dentro do mesmo bloco), nunca unir.
- [ ] 2.3 Rodar a suíte completa e confirmar que os testes novos e existentes passam (green).

## 3. Validação do corpus

- [ ] 3.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado.
- [ ] 3.2 Rodar `openspec validate --all --strict` e registrar o resultado.
- [ ] 3.3 Reconverter os 4 PDFs do corpus com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR.
- [ ] 3.4 Confirmar que os 3 casos reais de `SAIBA MAIS` identificados no diagnóstico ficam separados em `output/Inf0024E.md`, com antes/depois de cada um.
- [ ] 3.5 Confirmar que nenhuma palavra ou referência foi perdida (contagem de tokens antes/depois, restrita às linhas alteradas de `Inf0024E.md`).
- [ ] 3.6 Confirmar que `AINTARESP_1462304-PA.md`, `REsp_1704551-SP.md` e `L10.406_CC_2002.md` ficam byte-idênticos à reconversão anterior a esta mudança (nenhum contém `SAIBA MAIS`).
- [ ] 3.7 Confirmar que a primeira página do Inf0024E permanece fora de escopo (sem alteração inesperada) e que `Papel/Nome` continua inalterado.
- [ ] 3.8 Confirmar R01 (4/4), 8 SUBTÍTULO, índice do CC, rodapés técnicos e thin-space preservados em `Inf0024E.md`/`L10.406_CC_2002.md`.
- [ ] 3.9 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais nos 4 arquivos.
- [ ] 3.10 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira) nos 4 arquivos.
- [ ] 3.11 Produzir e explicar o diff completo do corpus (todos os arquivos alterados e por quê).

## 4. Encerramento do ciclo

- [ ] 4.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar cada subtarefa.
- [ ] 4.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex.
- [ ] 4.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana).
