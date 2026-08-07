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

## Conclusão

Nenhum dos dois critérios geométricos testados (mesmo-bloco-apenas; recuo x0 obrigatório entre blocos) separa com segurança as listas `Papel/Nome` das demais recomposições legítimas do corpus — cada um resolve o problema declarado mas introduz regressões novas em categorias de conteúdo não cobertas pelos exemplos/testes citados na tarefa (títulos centralizados, layout de rosto em colunas, interação com normalização de símbolo entre páginas). Por instrução explícita da tarefa, a implementação foi interrompida aqui.

## Próximos passos possíveis (não avaliados)

- Investigar um sinal que combine x0 com informação de que a linha de abertura do bloco seguinte é ou não um cabeçalho/título já tratado por `build_legislative_headings` (evitar aplicar o critério a parágrafos que alimentam essa função).
- Investigar detectar "mesma linha visual" (sobreposição de y0/y1 entre duas linhas de blocos diferentes) como sinal para NUNCA unir (resolveria o caso de colunas da página de rosto) antes de aplicar qualquer critério de x0.
- Investigar isolar a correção de símbolo entre páginas (`join_symbol_across_page_break`) de mudanças em `recompose_native_paragraphs`, tornando-a independente da estrutura exata de parágrafos.
- Considerar largura relativa do bloco (x1−x0) em vez de x0 absoluto, para lidar com texto centralizado.
