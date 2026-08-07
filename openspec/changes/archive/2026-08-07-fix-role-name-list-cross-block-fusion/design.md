## Context

`recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) recebe `blocks: list[tuple[float, float, str]]` — blocos geométricos do PyMuPDF (`page.get_text("blocks")`, apenas y0/y1/texto; x0 é descartado por `_sorted_native_text_blocks` em `converter.py`). A decisão de unir duas linhas físicas consecutivas usa, entre outras condições, `gap <= previous_height * 1.2`, onde `previous_height` é inferido dividindo a altura do bloco pelo número de linhas físicas. Essa condição não sabe se as duas linhas pertencem ao mesmo bloco ou a blocos diferentes — ela junta indiscriminadamente sempre que a distância vertical é pequena o bastante, o que é necessário para recompor frases que o extrator dividiu mecanicamente entre dois blocos, mas também funde, por coincidência geométrica, entradas de uma lista estruturada "Papel/Nome" que nunca deveriam se unir.

## Evidência geométrica coletada

### Casos `Papel/Nome` (fusão indevida, real)

`AINTARESP_1462304-PA.pdf` p.11 (`page.get_text("dict")`, x0/x1/y0/y1 por linha):
```
x0=36.0  'Relator do AgInt '                         (bloco A, linha 1)
x0=36.0  'Exmo. Sr. Ministro GURGEL DE FARIA'         (bloco A, linha 2)
x0=36.0  'Presidente da Sessão'                       (bloco B, linha 1)
x0=36.0  'Exmo. Sr. Ministro GURGEL DE FARIA'         (bloco B, linha 2)
```
`REsp_1704551-SP.pdf` p.3:
```
x0=104.2 'Relatora'                                   (bloco A)
x0=104.2 'Exma. Sra. Ministra  NANCY ANDRIGHI'         (bloco A)
x0=104.2 'Presidente da Sessão'                       (bloco B)
x0=104.2 'Exmo. Sr. Ministro MOURA RIBEIRO'           (bloco B)
x0=104.2 'Subprocurador-Geral da República'           (bloco C)
x0=104.2 'Exmo. Sr. Dr. .'                            (bloco C)
```
x0 idêntico em toda a sequência, dentro e entre blocos — nenhum recuo, nenhuma mudança de coluna, apenas proximidade vertical.

`AINTARESP_1462304-PA.pdf` p.11 (lista de advogados, blocos de 1 linha cada):
```
x0=38.2  'ADVOGADOS : PRISCILA SANTOS ARTIGAS - PR022529'
x0=123.0 'EDIS MILARE - SP129895'
x0=123.0 'MARIA CLARA RODRIGUES ALVES GOMES E OUTRO(S) - SP260338'
x0=123.0 'THIAGO SALES PEREIRA E OUTRO(S) - SP282430'
```
Aqui x0 *aumenta* (38.2→123.0), padrão de lista com recuo pendurado — direção oposta à convenção de continuação de parágrafo do corpo do Código Civil.

### Casos R01 reais (recomposição legítima, deve permanecer unida)

Os 4 casos citados na tarefa, inspecionados via `page.get_text("blocks")`:
```
Art. 44 §2º  (p.5,  bloco único, 2 linhas físicas no MESMO bloco)
Art. 593     (p.44, bloco único, 2 linhas físicas no MESMO bloco)
Art. 1.458   (p.126, bloco único, 3 linhas físicas no MESMO bloco)
Art. 1.368-F (p.118, bloco único, 2 linhas físicas no MESMO bloco)
```
Nenhum dos 4 depende de junção *entre* blocos — todos já estão dentro de um único bloco PyMuPDF na geometria real (diferente do que os testes unitários sintéticos do arquivo sugerem, que os modelam com 2 blocos separados).

Outras continuações reais do Código Civil que **dependem** de junção entre blocos (`page.get_text("dict")`, por linha):
```
Art. 288   (p.25):  x0=54.5 'Art. 288. ...ou'          (bloco A)
                     x0=36.5 'instrumento particular...' (bloco B)
Art. 1.079 (p.82):  x0=54.5 'Art. 1.079. ...assembléia,' (bloco A)
                     x0=36.5 'obedecido o disposto...'    (bloco B)
Art. 1.271 (p.100): x0=54.5 'Art. 1.271. ...especificador' (bloco A)
                     x0=36.5 'de má-fé, no caso...'         (bloco B)
Parágrafo único (p.88): x0=54.5 'Parágrafo único. ...montante de' (bloco A)
                         x0=36.5 'capital destinado...'            (bloco B, 2 linhas, ambas x0=36.5)
Art. 1.544 (p.136): x0=54.5 'Art. 1.544. ...respectivas autoridades ou os cônsules brasileiros,'
                     x0=36.5 'deverá ser registrado...respectivo'   (MESMO bloco que a linha anterior)
                     x0=36.5 'domicílio, ou...residir.'             (bloco SEGUINTE — aqui sim, entre blocos)
```
Padrão consistente: a primeira linha do parágrafo tem x0=54.5 (recuada); toda linha de continuação — seja no mesmo bloco, seja em um bloco seguinte — tem x0=36.5 (recuo suprimido, ~18pt à esquerda). Esse é o sinal geométrico que de fato distingue continuação de parágrafo (corpo de artigo) de lista Papel/Nome.

### Por que esse sinal (x0) não generaliza com segurança

Título legislativo centralizado que quebra em 2 blocos, `TÍTULO IV` (`L10.406_CC_2002.pdf` p.152):
```
x0=282.6 'TÍTULO IV'                                          (marcador bare, já protegido por outra regra)
x0=187.1 'Da Tutela, da Curatela e da Tomada de Decisão Apoiada' (bloco A, abertura do "parágrafo" de título)
x0=210.7 '(Redação dada pela Lei nº 13.146, de 2015)'          (bloco B)
```
x0 *aumenta* de 187.1 para 210.7 (texto centralizado: a segunda linha, mais curta, começa mais à direita quando centralizada) — o oposto do padrão de recuo do corpo de artigos. Um critério "x0 deve decrescer" bloqueia essa junção legítima, quebrando o título formatado pela função `build_legislative_headings` (que espera o título completo em um único parágrafo antes de combiná-lo com o marcador `TÍTULO IV`).

Página de rosto em colunas (`L10.406_CC_2002.pdf` p.1): "Presidência da República" e "Casa Civil Subchefia para Assuntos Jurídicos" ocupam a mesma leitura vertical mas são, na prática, duas colunas/linhas de citação distintas — o `gap` calculado entre elas fica negativo/artificial (não é uma continuação vertical real), e o comportamento do critério x0 nesse caso é inconsistente com o resultado desejado (ora corrige uma fusão espúria pré-existente, ora não, um efeito colateral fora do escopo desta mudança).

Fronteira de página `Art. 2.029` → `Art. 2.030` (p.175/176): bloquear uma junção específica alterou a estrutura de parágrafos resultante o suficiente para que `join_symbol_across_page_break` — uma função *separada*, que normaliza `"Lei n" + quebra de página + "o "` para `"Lei nº"` via regex de correspondência exata — deixasse de reconhecer o padrão esperado, resultando em `"Lei n"` (sem `º`) na página 175 e um `"o"` solto no início da página 176.

## Rodada 2 — refinar o critério x0 com exceções específicas (também descartada)

Após reportar a Rodada 1 (acima), o critério x0 foi retomado e refinado com três ajustes adicionais, todos ainda geométricos/estruturais, testados contra o corpus real:

1. **Bloqueio incondicional de "mesma linha visual"**: quando duas linhas físicas têm sobreposição vertical substancial (`previous_y1 - current_y0 > previous_height * 0.5`), nunca unir — independente de qualquer outra condição. Corrige o caso de colunas da página de rosto do CC.
2. **Isenção para títulos que seguem marcador estrutural bare**: quando o parágrafo imediatamente anterior ao que está em acumulação é um marcador bare já reconhecido (`bare_structure_pattern`, ex. `TÍTULO IV`), a exigência de recuo x0 é dispensada para esse parágrafo (ele é, por definição, o título que `build_legislative_headings` vai combinar com o marcador). Corrigiu `TÍTULO IV — Da Tutela... (Redação dada pela Lei nº 13.146, de 2015)`.
3. **Colapso de linhas em branco consecutivas em `remove_repetitive_margins`**: quando uma linha de margem é removida por corresponder inteiramente ao padrão (não apenas um prefixo/sufixo), a linha em branco resultante ao lado de outra linha em branco pré-existente passou a ser colapsada em uma só. Isso corrigiu, como efeito colateral necessário, a quebra de `join_symbol_across_page_break` na fronteira `Art. 2.029`/`Art. 2.030` (uma cabeçalho de margem — timestamp + nome de arquivo — que antes ficava fundido ao parágrafo seguinte passou a ficar isolado e integralmente removido, deixando duas linhas em branco adjacentes sem o colapso).

**Resultado nos casos citados na tarefa**: com os três ajustes, o diff do Código Civil caiu de 28 → 20 → 16 → 12 linhas alteradas, eliminando as regressões de `Art. 1.544`, `Art. 1.619`, `Art. 1.734`, `Parágrafo único`, `TÍTULO IV` e a normalização de símbolo `Art. 2.029`/`2.030`. Restaram apenas 3 blocos de diferença, todos confinados à capa/índice do CC (nenhuma perda de token): "Presidência da República"/"Casa Civil..." e "Lei de Introdução..."/"Institui o Código Civil." (masthead centralizado sem marcador bare precedente, não coberto pela isenção 2) e "Seção II Da Ocupação"/"Seção III..." (aparentemente uma correção, não uma regressão — separa dois itens de índice antes indevidamente fundidos com um `>` solto).

**Por que foi descartado mesmo assim — achado decisivo**: a validação completa do corpus (não só o Código Civil) revelou que o mesmo critério **fragmenta gravemente o texto substantivo de `Inf0024E.pdf` e `AINTARESP_1462304-PA.pdf`** — parágrafos inteiros e coerentes de fundamentação jurídica (ex. "A controvérsia em discussão gira em torno da possibilidade de ajuizar ação penal privada subsidiária da pública... proteção deficiente." seguido de outra frase da MESMA análise) passaram a ser cortados em um parágrafo por frase. Isso ocorre porque esses dois documentos (gerados por uma ferramenta de PDF diferente da do Código Civil) não usam a convenção de recuo-na-primeira-linha: cada frase/linha de texto corrido está em um bloco PyMuPDF próprio, todos compartilhando o mesmo x0 (sem recuo), então a exigência de "x0 deve decrescer para permitir a junção entre blocos" bloqueia a recomposição de praticamente toda frase seguinte em praticamente todo parágrafo desses dois arquivos — um dano muito mais grave e generalizado do que os casos de borda do Código Civil que motivaram o ajuste. Isso prova que o padrão geométrico x0 observado no Código Civil é uma convenção de formatação de UM gerador de PDF específico, não uma propriedade universal do "início de parágrafo" — logo, não é uma base seura para um critério aplicado a todo o pipeline.

Todo o código experimental (`converter.py`, `cleaner.py`) foi revertido; corpus e suíte confirmados byte-idênticos/294-294 ao estado committado antes desta rodada também.

## Conclusão

Nenhum dos critérios geométricos testados — mesmo-bloco-apenas; recuo x0 obrigatório entre blocos; e a versão refinada com bloqueio de mesma-linha-visual + isenção de título bare + colapso de margem — separa com segurança as listas `Papel/Nome` das demais recomposições legítimas do corpus inteiro. A versão refinada chegou a resolver todos os casos do Código Civil, mas causou uma regressão ainda mais severa (fragmentação frase a frase) em `Inf0024E.pdf` e `AINTARESP_1462304-PA.pdf`, cujo layout de PDF não segue a mesma convenção de recuo. Por instrução explícita da tarefa, a implementação foi interrompida aqui, sem exceção.

## Próximos passos possíveis (não avaliados)

- Investigar um sinal que não dependa da convenção de recuo-na-primeira-linha (que se mostrou específica de UM gerador de PDF, não universal) — ex. repetição estatística do padrão "bloco curto, N linhas, mesmo x0 do bloco vizinho" ao longo da página inteira (uma lista Papel/Nome tende a se repetir várias vezes na mesma página; uma continuação de frase normal, não).
- Investigar detectar se o bloco seguinte, sozinho, já teria caído em algum guard existente (`native_label_pattern` + `is_first`) se avaliado como bloco isolado — i.e., usar a MESMA lógica já validada de "primeira linha do bloco" para blocos inteiros de 1-2 linhas, em vez de uma nova heurística de x0.
- Investigar detectar a MESMA proporção de linhas curtas (poucas palavras) por bloco como já usado — mas evitando a regra 2 da tarefa ("não decidir apenas por caixa alta ou comprimento curto") a menos que combinado com evidência estrutural adicional (ex. altura de bloco muito menor que a média da página, sugerindo um "campo" e não um parágrafo).
- Considerar que talvez não exista um critério puramente geométrico seguro, e que a solução correta exija tratar `Papel/Nome` como um formato estrutural reconhecível por OUTRO meio (ex. um segundo `bare_structure`-like vocabulário de rótulos comuns de capa processual — mas isso conflitaria com a regra 1 da tarefa, "não criar lista fixa de nomes, partes, tribunais ou processos", a menos que restrito a palavras-função genéricas como "Relator(a)", "Presidente da Sessão", "Secretário", que não são nomes próprios nem específicos de tribunal/processo).
