## 1. Testes (TDD, antes de qualquer implementação)

- [x] 1.1 Adicionar teste positivo (página 14 real): dois itens "Jurisprudência em Teses" originalmente independentes ficam em parágrafos/linhas separados, cada um preservado integralmente. Implementado em `test_convert_inf0024e_page_14_separates_saiba_mais_items` (commit `c7c75d0`).
- [x] 1.2 Adicionar teste positivo (página 18 real): um item "Jurisprudência em Teses" e o "Informativo de Jurisprudência" seguinte ficam separados. Implementado em `test_convert_inf0024e_page_18_separates_saiba_mais_items` (commit `c7c75d0`).
- [x] 1.3 Adicionar teste positivo (página 4 real): o precedente `CC 159976/SP, ... DJe 16/04/2019` e o "Informativo de Jurisprudência n. 474" seguinte ficam separados; a quebra de linha física interna do próprio precedente ("...julgado em" + "10/04/2019, DJe 16/04/2019") continua unida em uma só linha. Implementado em `test_convert_inf0024e_page_4_separates_precedent_from_next_informativo` (commit `c7c75d0`).
- [x] 1.4 Adicionar teste garantindo que os demais itens da mesma seção `SAIBA MAIS` (ex. "Informativo de Jurisprudência n. 135/474/346/174" na página 4) permanecem cada um em seu próprio parágrafo, sem regressão. Implementado em `test_convert_inf0024e_page_4_saiba_mais_items_remain_separated` (commit `c7c75d0`).
- [x] 1.5 Adicionar teste negativo: um bloco de 2 linhas físicas fora de qualquer seção `SAIBA MAIS` continua sendo unido ao bloco seguinte pela lógica geométrica normal (sem o novo guard interferir fora do intervalo). Implementado em `test_recompose_native_paragraphs_saiba_mais_guard_does_not_affect_blocks_outside_section` (commit `c7c75d0`).
- [x] 1.6 Adicionar teste negativo: uma frase jurídica comum contendo as palavras "Informativo", "Jurisprudência", "/", "DJe" ou números, fora de uma seção `SAIBA MAIS`, não é dividida. Implementado em `test_recompose_native_paragraphs_does_not_split_legal_sentence_with_saiba_mais_vocabulary` (commit `fcfb1d9`).
- [x] 1.7 Adicionar teste negativo: `PROCESSO`, `TEMA`, `DESTAQUE`, `RAMO DO DIREITO`, `INFORMAÇÕES DO INTEIRO TEOR` continuam corretamente separados do conteúdo seguinte (comportamento pré-existente, sem regressão). Coberto pela suíte existente (reexecutada sem regressão nas duas subtarefas de teste).
- [x] 1.8 Adicionar teste negativo: o cabeçalho `SAIBA MAIS` em si permanece em parágrafo próprio, sem ser unido ao primeiro item da lista (comportamento pré-existente via `native_label_pattern`, sem regressão). Implementado em `test_recompose_native_paragraphs_saiba_mais_label_stays_separate_from_first_item` (commit `c7c75d0`).
- [x] 1.9 Adicionar teste negativo: os 4 casos R01, os 8 SUBTÍTULO e o índice do Código Civil permanecem intactos (reexecução dos testes de regressão existentes). Confirmado: suíte completa reexecutada sem regressão (326 passed além das 6 falhas RED esperadas).
- [x] 1.10 Adicionar teste negativo: rodapés técnicos já removidos e a normalização de thin-space permanecem intactos (reexecução dos testes de regressão existentes). Confirmado junto com 1.9.
- [x] 1.11 Adicionar teste negativo: o defeito `Papel/Nome` permanece inalterado (fora de escopo, não corrigido incidentalmente). Sem teste próprio nesta mudança (comportamento inalterado por construção, já que o guard novo só atua dentro do literal `SAIBA MAIS`); confirmação final via reconversão do corpus na Seção 3.
- [x] 1.12 Rodar a suíte e confirmar que os novos testes falham (red) antes da implementação. Resultado: 6 falhas (as 3 integrações reais + 2 unitários positivos + 1 de regressão de item da página 4), 326 passed (verificado de forma independente pelo orquestrador, commits `c7c75d0` e `fcfb1d9`).

## 2. Implementação

- [x] 2.1 Em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), adicionar detecção do intervalo `SAIBA MAIS`: ativo a partir de um bloco cuja única linha física é exatamente `SAIBA MAIS` (já reconhecido por `native_label_pattern`), até o próximo bloco cuja primeira linha física também corresponda a `native_label_pattern`. Implementado via lista paralela `in_saiba_mais_span` (commit `cdc55e6`).
- [x] 2.2 Adicionar uma nova cláusula de exclusão a `should_join`: quando a linha atual está dentro do intervalo `SAIBA MAIS` E é a primeira linha física de um novo bloco (transição entre blocos, não continuação de linha física dentro do mesmo bloco), nunca unir. Implementado (commit `cdc55e6`).
- [x] 2.3 Rodar a suíte completa e confirmar que os testes novos e existentes passam (green). Resultado: 332/332 passed (verificado de forma independente pelo orquestrador).

## 3. Validação do corpus

- [x] 3.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado. Resultado: 332/332 passed.
- [x] 3.2 Rodar `openspec validate --all --strict` e registrar o resultado. Resultado: 2 passed, 0 failed (`change/fix-saiba-mais-item-boundaries`, `spec/juridical-pdf-conversion`).
- [x] 3.3 Reconverter os 4 PDFs do corpus com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR. Resultado: 241 páginas (12+29+186+14) roteadas como `texto_nativo`; `ocr.enabled: false` e `status: sucesso` nos 4 relatórios.
- [x] 3.4 Confirmar que os 3 casos reais de `SAIBA MAIS` identificados no diagnóstico ficam separados em `output/Inf0024E.md`, com antes/depois de cada um. Resultado: página 4 (precedente CC / Informativo n. 474), página 14 (2× Jurisprudência em Teses / Informativo n. 751), página 18 (Jurisprudência em Teses / Informativo n. 388) — os 3 casos agora em parágrafos separados por linha em branco.
- [x] 3.5 Confirmar que nenhuma palavra ou referência foi perdida (contagem de tokens antes/depois, restrita às linhas alteradas de `Inf0024E.md`). Resultado: 9084 → 9084 tokens (`\w+`), diferença zero — a correção apenas insere quebras de parágrafo, nenhum token perdido ou adicionado.
- [x] 3.6 Confirmar que `AINTARESP_1462304-PA.md`, `REsp_1704551-SP.md` e `L10.406_CC_2002.md` ficam byte-idênticos à reconversão anterior a esta mudança (nenhum contém `SAIBA MAIS`). Resultado: os 3 arquivos com MD5 idêntico ao baseline pré-mudança.
- [x] 3.7 Confirmar que a primeira página do Inf0024E permanece fora de escopo (sem alteração inesperada) e que `Papel/Nome` continua inalterado. Resultado: diff do corpus mostra só 3 blocos alterados (páginas 4, 14, 18), nada na primeira página; `Papel/Nome` só ocorre em AINTARESP/REsp, que ficaram byte-idênticos.
- [x] 3.8 Confirmar R01 (4/4), 8 SUBTÍTULO, índice do CC, rodapés técnicos e thin-space preservados em `Inf0024E.md`/`L10.406_CC_2002.md`. Resultado: `L10.406_CC_2002.md` byte-idêntico (R01/SUBTÍTULO/índice trivialmente preservados); rodapés técnicos (`GABGF09`, `Documento: 1807307`) continuam em 0 ocorrências; thin-space (`&#8201;`/variantes) continua em 0 ocorrências em `Inf0024E.md`.
- [x] 3.9 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais nos 4 arquivos. Resultado: AINT=12, REsp=14, Inf0024E=29, CC=186, todos únicos e sequenciais.
- [x] 3.10 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira) nos 4 arquivos. Resultado: os 4 arquivos byte-idênticos entre a 1ª e a 2ª reconversão.
- [x] 3.11 Produzir e explicar o diff completo do corpus (todos os arquivos alterados e por quê). Resultado: único arquivo alterado é `output/Inf0024E.md` (3 blocos, páginas 4/14/18, cada um separando itens de `SAIBA MAIS` antes fundidos); os outros 3 arquivos byte-idênticos ao baseline pré-mudança.

## 4. Encerramento do ciclo

- [x] 4.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar cada subtarefa. Feito em cada subtarefa.
- [x] 4.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex. Feito (commits `c7c75d0`, `fcfb1d9`, `cdc55e6`, `1a2ce2c`).
- [x] 4.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana).
