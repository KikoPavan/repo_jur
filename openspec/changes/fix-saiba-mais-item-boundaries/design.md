## Context

`output/Inf0024E.md` contém 3 ocorrências reais de fusão indevida dentro de seções `SAIBA MAIS`:

1. Página 14: três itens fundidos em uma linha — `Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 117: INTERCEPTAÇÃO TELEFÔNICA - I Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 69: NULIDADES NO PROCESSO PENAL Informativo de Jurisprudência n. 751`.
2. Página 18: dois itens fundidos — `Jurisprudência em Teses / DIREITO PENAL - EDIÇÃO N. 57: CRIMES CONTRA A ADMINISTRAÇÃO PÚBLICA Informativo de Jurisprudência n. 388`.
3. Página 4: um precedente fundido ao informativo seguinte — `CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA SEÇÃO, julgado em 10/04/2019, DJe 16/04/2019 Informativo de Jurisprudência n. 474`.

## Rastreamento da causa raiz (evidência empírica)

### 1. Localização dos blocos PyMuPDF

Extração via `page.get_text("blocks")` sobre `input/Inf0024E.pdf`, páginas 4, 14 e 18, confirma que cada item de `SAIBA MAIS` é sempre um bloco PyMuPDF **isolado e distinto** — nunca dois itens compartilham um bloco, e nenhum item legítimo é dividido em dois blocos (verificado nas 16 páginas do corpus com 2+ itens em `SAIBA MAIS`: todas as 43 entradas reconstroem referências completas e bem formadas, sem fragmento de sentença cortado). Exemplo (página 4, `page.get_text("blocks")`):

```
y0=85.0  y1=95.0  x0=60.0  "Informativo de Jurisprudência n. 135"
y0=110.0 y1=135.0 x0=60.0  "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA SEÇÃO, julgado em\n10/04/2019, DJe 16/04/2019"
y0=150.0 y1=160.0 x0=60.0  "Informativo de Jurisprudência n. 474"
y0=175.0 y1=185.0 x0=60.0  "Informativo de Jurisprudência n. 346"
y0=200.0 y1=210.0 x0=60.0  "Informativo de Jurisprudência n. 174"
```

### 2. Como os blocos passam por `compose_document`/`recompose_native_paragraphs`

`_sorted_native_text_blocks` (`converter.py`) devolve, por página, uma tripla `(y0, y1, texto_do_bloco)` por bloco PyMuPDF — a mesma geometria acima. `recompose_native_paragraphs` (`cleaner.py`) recebe essa lista e, para cada bloco, faz `block_text.split("\n")` para obter as linhas físicas e estima a geometria de CADA linha dividindo a altura total do bloco igualmente:

```python
line_height = (y1 - y0) / len(physical_lines)
```

Para o bloco do precedente CC (2 linhas físicas, `y0=110.0, y1=135.0`), isso produz `line_height = 12.5` e as linhas interpoladas `(110.0, 122.5)` e `(122.5, 135.0)`. A decisão de unir a linha seguinte usa:

```python
gap = current_y0 - previous_y1
should_join = ... and gap <= previous_height * 1.2
```

Entre o fim interpolado do bloco CC (`122.5`–`135.0`, `previous_height=12.5`) e o início do bloco "Informativo de Jurisprudência n. 474" (`y0=150.0`): `gap = 150.0 - 135.0 = 15.0`; `threshold = 12.5 * 1.2 = 15.0`. Como a comparação é `<=`, `15.0 <= 15.0` é **verdadeiro** — os dois blocos são unidos.

### 3. Confirmação com geometria real de linha

Extração via `page.get_text("dict")` (que expõe a bounding box real de cada linha, não apenas do bloco) mostra que as 2 linhas físicas do bloco CC têm, na verdade, a MESMA altura que os itens de uma só linha (`10.0`pt cada), com um espaçamento interno de apenas `5.0`pt entre elas — não `12.5`pt cada como a interpolação assume:

```
LINE bbox=[60.0, 110.0, 488.1, 120.0] "CC 159976/SP, ... julgado em"       (altura real = 10.0)
LINE bbox=[60.0, 125.0, 194.5, 135.0] "10/04/2019, DJe 16/04/2019"          (altura real = 10.0)
```

Com a altura REAL da última linha (`10.0`), o limiar correto seria `10.0 * 1.2 = 12.0`; como o gap real entre blocos (`150.0 - 135.0 = 15.0`) excede esse limiar, a decisão correta é **não unir** — exatamente o comportamento que os itens de uma só linha já exibem hoje (ex. "Informativo de Jurisprudência n. 135" → "CC 159976/SP...": `gap=15.0`, `height=10.0`, `threshold=12.0`, `15.0 > 12.0`, corretamente não unidos). A mesma verificação, repetida para as páginas 14 e 18, confirma que a geometria real de linha (não a interpolada) separaria corretamente os 3 casos reais.

### 4. Comparação com itens que já permanecem corretamente separados

Nas mesmas páginas 4, 14 e 18, todos os itens de uma única linha física (ex. "Informativo de Jurisprudência n. 135/474/346/174" na página 4) já permanecem corretamente separados, porque sua altura de bloco (sem interpolação necessária, já que há uma só linha) é `10.0`pt exata — o mesmo valor real medido para as linhas dos blocos de 2 linhas. **A causa raiz não é a lista em si, é especificamente a interpolação aplicada a blocos com 2+ linhas físicas**, que só existe quando o item de `SAIBA MAIS` precisa quebrar linha (título de "Jurisprudência em Teses" longo, ou precedente com Relator + data em 2 linhas).

## Candidatos descartados (evidência de blast radius)

O requisito do `/goal` exige um critério seguro e geral, e explicitamente instrui a parar caso nenhum seja encontrado sem alargar para limpeza editorial genérica. Dois candidatos mais amplos foram avaliados e descartados:

### Candidato A — substituir a interpolação por geometria real de linha em todo `recompose_native_paragraphs`

Tecnicamente a correção "correta" na origem (elimina a imprecisão da interpolação para qualquer bloco multi-linha, não só `SAIBA MAIS`). Testado por simulação: recomputando a decisão de junção com `page.get_text("dict")` para TODAS as páginas dos 4 PDFs do corpus, comparando contra a decisão atual (interpolada):

| PDF | Decisões de junção que mudam |
| --- | --- |
| `Inf0024E.pdf` | 8 (inclui as 3 páginas do defeito real, mas também páginas 1, 2, 9, 22) |
| `AINTARESP_1462304-PA.pdf` | 19 (páginas 3, 4, 6, 7, 8, 9, 10, 11) |
| `REsp_1704551-SP.pdf` | 7 (páginas 1, 2, 3, 4, 9, 14) |
| `L10.406_CC_2002.pdf` | 10 (página 141, e páginas 178–186 — exatamente o intervalo do índice final, já protegido por `fix-legislative-index-heading-hierarchy`) |

Duas amostras confirmam que esse candidato quebraria junções legítimas já em produção, nunca cobertas por teste explícito mas presentes na saída atual:
- `AINTARESP_1462304-PA.pdf`, página 3: "Requer, ao final, o provimento do especial com a atribuição do valor de R$ 10.000,00 (dez mil reais) à causa." seguido de "Decorrido o prazo legal, a agravada não apresentou impugnação." — hoje unidos no mesmo parágrafo (confirmado em `output/AINTARESP_1462304-PA.md`); com geometria real, o gap (`15.8`) excede o limiar real (`12.0 * 1.2 = 14.4`) e a junção se perderia.
- `Inf0024E.pdf`, página 2: "...para manifestação." seguido de "O Superior Tribunal de Justiça decidiu reiteradas vezes..." — mesmo padrão.
- `L10.406_CC_2002.pdf`, páginas 178–186: mudança de decisão de junção dentro do índice final já endurecido por mudança arquivada anterior — risco direto de regressão em área já validada.

Descartado: blast radius de 44 decisões de junção alteradas em todo o corpus, sem cobertura de teste que garanta que cada uma é segura; contraria a exigência de "uma mudança = um defeito" e "não ampliar para limpeza editorial genérica".

### Candidato B — apertar o limiar de empate (`gap <= h*1.2` para `gap < h*1.2`)

Os 3 casos reais de `SAIBA MAIS` são empates matemáticos exatos sob a interpolação atual (`gap == threshold == 15.0`), então trocar `<=` por `<` os resolveria sem tocar a interpolação. Descartado pela mesma verificação: o mesmo AINTARESP página 3 (`gap=15.8, threshold=15.75`, quase-empate) e outros dois pontos (`Inf0024E.pdf` página 2, `AINTARESP_1462304-PA.pdf` páginas 8 e 10) também são empates/quase-empates sob a interpolação atual — a mesma junção legítima do Candidato A se perderia.

## Critério adotado — âncora estrutural em `SAIBA MAIS`

`SAIBA MAIS` é um cabeçalho editorial fixo, genérico de qualquer informativo de jurisprudência do STJ — não é específico do nome do arquivo, do número da edição ou do conteúdo de um item. Confirmado por varredura de texto bruto (`page.get_text()`) nos 4 PDFs do corpus: a substring `SAIBA MAIS` ocorre exclusivamente em `Inf0024E.pdf` (18 páginas), zero ocorrências nos outros 3. O texto "SAIBA MAIS" já corresponde a `native_label_pattern` (linha inteiramente maiúscula, sem pontuação) — a mesma classe estrutural genérica já usada para proteger rótulos de campo como `PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `DESTAQUE`, `INFORMAÇÕES DO INTEIRO TEOR`.

Critério: dentro do intervalo delimitado por um bloco cuja única linha física é exatamente `SAIBA MAIS` (início) e o próximo bloco cuja primeira linha física também corresponda a `native_label_pattern` (fim — na prática sempre `VÍDEO DO JULGAMENTO`, `ÁUDIO DO TEXTO` ou `PROCESSO`, mas o critério não enumera esses rótulos, apenas reusa o padrão já genérico), **nunca unir dois blocos DIFERENTES entre si**. A quebra de linha física DENTRO do mesmo bloco (ex. as 2 linhas de um único item "Jurisprudência em Teses / ... - I") continua sendo unida normalmente pela lógica geométrica já existente — o novo guard só se aplica quando a linha atual é a PRIMEIRA linha física de um NOVO bloco (`current_is_first`), nunca a uma continuação intra-bloco.

Por que é seguro e geral:
- **Não usa vocabulário de item**: não verifica `Informativo`, `Jurisprudência em Teses`, `/`, `DJe` ou números de edição — apenas a origem do bloco PyMuPDF (um item = um bloco) e o cabeçalho fixo `SAIBA MAIS`.
- **Zero blast radius fora de `Inf0024E.pdf`**: `SAIBA MAIS` não ocorre nos outros 3 PDFs; a condição nunca é satisfeita neles.
- **Zero blast radius dentro de `Inf0024E.pdf` fora das 18 seções `SAIBA MAIS`**: o guard só é avaliado dentro do intervalo delimitado; nas 15 seções já corretamente separadas hoje, o guard é uma operação nula (a decisão já era "não unir").
- **Não altera a interpolação geométrica compartilhada** nem nenhum outro guard existente — é apenas uma nova cláusula de exclusão em `should_join`, o que significa que só pode transformar decisões de junção JÁ VERDADEIRAS em falsas dentro do intervalo protegido, nunca o contrário; não pode introduzir uma nova junção indevida em lugar nenhum.
- **Determinístico e idempotente**: baseado inteiramente em texto fixo e estrutura de blocos, estável entre execuções.

## Fora de escopo (confirmado, não corrigido nesta mudança)

- Primeira página colapsada do Inf0024E, `Papel/Nome`, `RECURSO / ESPECIAL`, outras estruturas editoriais fora de `SAIBA MAIS` (ex. `LEGISLAÇÃO`, `SÚMULAS`, que usam o mesmo padrão de rótulo genérico mas não apresentam o defeito no corpus atual e não são tocadas por este guard, que é ancorado especificamente ao literal `SAIBA MAIS`).
- Qualquer correção geral da interpolação de altura de linha em `recompose_native_paragraphs` (Candidato A) — permanece um defeito de precisão geométrica compartilhado, não corrigido nesta mudança; uma futura mudança própria precisaria validar, caso a caso, as 44 decisões de junção identificadas acima antes de generalizar a correção.
