## 1. Testes (TDD, antes de qualquer implementação)

- [x] 1.1 Adicionar teste positivo: `apreensão de &#8201;37 gramas` → `apreensão de 37 gramas` (sem espaço duplicado).
- [x] 1.2 Adicionar teste positivo: `Lei n.&#8201;11.343/2006` → `Lei n. 11.343/2006`.
- [x] 1.3 Adicionar teste positivo: `na&#8201;realidade` → `na realidade`.
- [x] 1.4 Adicionar teste positivo: entidade imediatamente antes de um espaço já existente (ex. `regulamentar.&#8201; A diferença`) → um único espaço, não dois (`regulamentar. A diferença`).
- [x] 1.5 Adicionar teste positivo para cada variante equivalente documentada no diagnóstico: `&#x2009;`, `&#X2009;`, `&thinsp;`, `&THINSP;` → mesmo comportamento de substituição por espaço único.
- [x] 1.6 Adicionar teste negativo: outras entidades HTML (`&amp;`, `&lt;`, `&gt;`, `&nbsp;`) permanecem inalteradas.
- [x] 1.7 Adicionar teste negativo: a substituição não introduz espaço dentro de uma palavra além do exigido pela própria correção (verificar que nenhum caractere alfanumérico adjacente à entidade é removido ou alterado).
- [x] 1.8 Adicionar teste negativo: nenhuma pontuação adjacente à entidade é alterada (ex. o `.` em `n.&#8201;11.343` permanece).
- [x] 1.9 Adicionar teste negativo: `[[Pág. N]]` e o comentário `<!-- método: ... -->` permanecem intactos quando presentes no mesmo documento.
- [x] 1.10 Adicionar teste negativo: os 4 casos R01, os 8 SUBTÍTULO, o índice do Código Civil, os rodapés técnicos já removidos por mudanças anteriores e o defeito `Papel/Nome` (inalterado, fora de escopo) permanecem intactos — cobertura via reexecução dos testes de regressão já existentes, sem necessidade de novos casos específicos. Confirmação plena adiada para a Seção 3 (só é possível reexecutar a suíte completa após a implementação, já que `tests/test_cleaner.py` inteiro falha ao coletar em ImportError na fase RED).
- [x] 1.11 Adicionar teste de idempotência: aplicar a função de normalização duas vezes seguidas no mesmo texto produz o mesmo resultado da primeira aplicação.
- [x] 1.12 Rodar a suíte e confirmar que os novos testes falham (red) antes da implementação. Resultado: `ImportError: cannot import name 'normalize_thin_space_entities'` (verificado de forma independente pelo orquestrador, commit `82d9bdb`).

## 2. Implementação

- [ ] 2.1 Adicionar em `src/pipeline_juridico/cleaner.py` uma função determinística (ex. `normalize_thin_space_entities`) que substitui o padrão `[ \t]*&(?:#8201|#[xX]2009|thinsp);[ \t]*` (case-insensitive) por um único espaço ASCII, sem tocar nenhuma outra entidade HTML nem caracteres de quebra de linha.
- [ ] 2.2 Chamar a nova função em `src/pipeline_juridico/converter.py` sobre o `raw_markdown` já composto, antes de `remove_repetitive_margins` (ou em outro ponto do mesmo grupo de transformações textuais, desde que a ordem não afete o resultado — justificar a escolha no diff).
- [ ] 2.3 Rodar a suíte completa e confirmar que os testes novos e existentes passam (green).

## 3. Validação do corpus

- [ ] 3.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado.
- [ ] 3.2 Rodar `openspec validate --all --strict` e registrar o resultado.
- [ ] 3.3 Reconverter os 4 PDFs do corpus (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, `L10.406_CC_2002.pdf`) com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR.
- [ ] 3.4 Confirmar zero ocorrências literais de `&#8201;` (e das variantes equivalentes) em `output/Inf0024E.md`, com antes/depois dos 3 casos reais citados no diagnóstico.
- [ ] 3.5 Confirmar que nenhuma palavra foi perdida ou adicionada (contagem de tokens antes/depois, restrita às linhas alteradas de `Inf0024E.md`).
- [ ] 3.6 Confirmar que `AINTARESP_1462304-PA.md`, `REsp_1704551-SP.md` e `L10.406_CC_2002.md` ficam byte-idênticos à reconversão anterior a esta mudança (nenhuma ocorrência do padrão nesses arquivos).
- [ ] 3.7 Confirmar R01 (4/4), 8 SUBTÍTULO e índice do Código Civil intactos; rodapés técnicos continuam removidos.
- [ ] 3.8 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais nos 4 arquivos.
- [ ] 3.9 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira) nos 4 arquivos.
- [ ] 3.10 Produzir e explicar o diff completo do corpus (todos os arquivos alterados e por quê).

## 4. Encerramento do ciclo

- [ ] 4.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar cada subtarefa.
- [ ] 4.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex.
- [ ] 4.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana).
