> Nota de status: esta mudança está BLOQUEADA no diagnóstico (ETAPA 1). Nenhum código foi alterado. Ver `proposal.md` e `design.md` para os dois critérios geométricos investigados e descartados, e por quê. Não prosseguir para TDD/implementação sem antes encontrar (e validar contra o corpus real dos 4 PDFs, não apenas testes sintéticos) um critério geométrico que preserve simultaneamente: os 4 casos R01, as demais continuações reais entre blocos do Código Civil (ex. Art. 1.544, Art. 1.619, Art. 1.734), os títulos legislativos centralizados combinados por `build_legislative_headings`, e a normalização de símbolo entre páginas (`join_symbol_across_page_break`).

## 1. Diagnóstico

- [x] 1.1 Localizar os casos reais de fusão `Papel/Nome` em `AINTARESP_1462304-PA.pdf` (p.11) e `REsp_1704551-SP.pdf` (p.3, p.14); inspecionar `page.get_text("blocks")` e `page.get_text("dict")` (x0/x1/y0/y1 por linha) desses casos, dos 4 casos R01 reais no Código Civil, de outras continuações reais entre blocos do Código Civil, e de listas `Papel/Nome` corretamente preservadas. Resultado: documentado em `design.md`.
- [x] 1.2 Testar o critério "restringir junção ao mesmo bloco de origem" contra o corpus real (reconversão `--no-ocr` dos 4 PDFs, não apenas testes sintéticos). Resultado: os 4 casos R01 nomeados sobrevivem (estão dentro de um único bloco na geometria real), mas o critério quebra outras continuações reais do Código Civil (Art. 1.544, Art. 1.619, Art. 1.734, Parágrafo único antes do Art. 1.758) — descartado.
- [x] 1.3 Testar o critério "recuo x0 obrigatório em relação à abertura do parágrafo, apenas em junções entre blocos diferentes" (x0 por linha extraído via `page.get_text("dict")`) contra o corpus real. Resultado: corrige os casos `Papel/Nome` e preserva os 4 R01 e as demais continuações reais do corpo de artigos, mas introduz regressões em títulos legislativos centralizados (`TÍTULO IV — Da Tutela...`), no layout de página de rosto em colunas, e na normalização de símbolo `join_symbol_across_page_break` na fronteira Art. 2.029/2.030 — descartado.
- [x] 1.4 Reverter todo código experimental (`converter.py`, `cleaner.py`) ao estado committado; confirmar suíte `294/294` e corpus restaurado ao baseline antes de reportar.
- [x] 1.5 (Rodada 2) Refinar o critério x0 com três ajustes: bloqueio incondicional de junção entre linhas na mesma linha visual (sobreposição de y0/y1 substancial); isenção da exigência de recuo para parágrafos que seguem um marcador estrutural bare (`TÍTULO IV` etc.); colapso de linhas em branco consecutivas em `remove_repetitive_margins` após remoção integral de uma linha de margem. Resultado no Código Civil: todas as regressões da rodada 1 corrigidas (Art. 1.544, 1.619, 1.734, Parágrafo único, TÍTULO IV, símbolo Art. 2.029/2.030); restam só 3 diferenças confinadas à capa/índice, sem perda de token.
- [x] 1.6 (Rodada 2) Validar o critério refinado contra o corpus INTEIRO (não só o Código Civil). Resultado: fragmentação severa e generalizada do texto substantivo (fundamentação jurídica) em `Inf0024E.pdf` e `AINTARESP_1462304-PA.pdf` — um parágrafo por frase — porque esses arquivos não seguem a convenção de recuo-na-primeira-linha do Código Civil. Regressão mais grave que o problema original — critério definitivamente descartado.
- [x] 1.7 Reverter todo código experimental da Rodada 2; confirmar suíte `294/294` e corpus 4/4 byte-idêntico ao baseline committado antes de reportar.

## 2. TDD (bloqueado)

- [ ] 2.1 BLOQUEADO — aguardando critério geométrico seguro que não dependa de uma convenção de formatação específica de um gerador de PDF (ver nota de status acima e `design.md`, seção "Próximos passos possíveis").

## 3. Implementação (bloqueado)

- [ ] 3.1 BLOQUEADO — aguardando critério geométrico seguro.
