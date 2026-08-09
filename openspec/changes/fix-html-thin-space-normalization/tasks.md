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

- [x] 2.1 Adicionar em `src/pipeline_juridico/cleaner.py` uma função determinística (ex. `normalize_thin_space_entities`) que substitui o padrão `[ \t]*&(?:#8201|#[xX]2009|thinsp);[ \t]*` (case-insensitive) por um único espaço ASCII, sem tocar nenhuma outra entidade HTML nem caracteres de quebra de linha. Implementado (commit `771078a`).
- [x] 2.2 Chamar a nova função em `src/pipeline_juridico/converter.py` sobre o `raw_markdown` já composto, antes de `remove_repetitive_margins` (ou em outro ponto do mesmo grupo de transformações textuais, desde que a ordem não afete o resultado — justificar a escolha no diff). Implementado: `raw_markdown = normalize_thin_space_entities(raw_markdown)` logo após `compose_document(blocks)`, primeiro passo do grupo de normalizações textuais.
- [x] 2.3 Rodar a suíte completa e confirmar que os testes novos e existentes passam (green). Resultado: 323/323 passed (verificado de forma independente pelo orquestrador).

## 3. Validação do corpus

- [x] 3.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado. Resultado: 323/323 passed.
- [x] 3.2 Rodar `openspec validate --all --strict` e registrar o resultado. Resultado: 2 passed, 0 failed (`change/fix-html-thin-space-normalization`, `spec/juridical-pdf-conversion`).
- [x] 3.3 Reconverter os 4 PDFs do corpus (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, `L10.406_CC_2002.pdf`) com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR. Resultado: as 241 páginas dos 4 arquivos (12+29+186+14) roteadas como `texto_nativo`; `ocr.enabled: false` nos 4 relatórios; `status: sucesso` nos 4.
- [x] 3.4 Confirmar zero ocorrências literais de `&#8201;` (e das variantes equivalentes) em `output/Inf0024E.md`, com antes/depois dos 3 casos reais citados no diagnóstico. Resultado: 0 ocorrências (antes: 21). Antes/depois: `apreensão de &#8201;37 gramas` → `apreensão de 37 gramas`; `Lei n.&#8201;11.343/2006` → `Lei n. 11.343/2006`; `na&#8201;realidade` → `na realidade`.
- [x] 3.5 Confirmar que nenhuma palavra foi perdida ou adicionada (contagem de tokens antes/depois, restrita às linhas alteradas de `Inf0024E.md`). Resultado: 9105 → 9084 tokens (`\w+`), diferença de exatamente 21, idêntica ao número de entidades removidas (cada entidade contribuía um token artificial `8201`); nenhum outro token perdido ou adicionado.
- [x] 3.6 Confirmar que `AINTARESP_1462304-PA.md`, `REsp_1704551-SP.md` e `L10.406_CC_2002.md` ficam byte-idênticos à reconversão anterior a esta mudança (nenhuma ocorrência do padrão nesses arquivos). Resultado: os 3 arquivos com MD5 idêntico ao baseline pré-mudança.
- [x] 3.7 Confirmar R01 (4/4), 8 SUBTÍTULO e índice do Código Civil intactos; rodapés técnicos continuam removidos. Resultado: trivialmente preservados (`L10.406_CC_2002.md` byte-idêntico); `GABGF09` e `Documento: 1807307` com 0 ocorrências em AINT/REsp.
- [x] 3.8 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais nos 4 arquivos. Resultado: AINT=12, REsp=14, Inf0024E=29, CC=186, todos únicos e sequenciais.
- [x] 3.9 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira) nos 4 arquivos. Resultado: os 4 arquivos byte-idênticos entre a 1ª e a 2ª reconversão (mesmo MD5).
- [x] 3.10 Produzir e explicar o diff completo do corpus (todos os arquivos alterados e por quê). Resultado: único arquivo alterado é `output/Inf0024E.md` (5 linhas, todas removendo o literal `&#8201;`/variantes por um espaço); os outros 3 arquivos byte-idênticos ao baseline pré-mudança.

## 4. Encerramento do ciclo

- [x] 4.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar cada subtarefa. Feito em cada subtarefa.
- [x] 4.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex. Feito (commits `82d9bdb`, `f1bfc0e`, `771078a`, `e86bbac`).
- [ ] 4.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana).
