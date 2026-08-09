## Contexto

`output/Inf0024E.md`, primeira linha de conteúdo da página 1:

```
Informativo de Jurisprudência Informativo de Jurisprudência n. 24 - Edição Extraordinária 28 de janeiro de 2025 Direito Penal Este periódico destaca teses jurisprudenciais e não consiste em repositório oficial de jurisprudência. CORTE ESPECIAL
```

Seis elementos estruturalmente distintos da capa editorial — título estilizado, linha de edição/data (que também é o cabeçalho repetitivo removido corretamente em todas as outras páginas), ramo do direito, aviso editorial, e o cabeçalho de câmara julgadora — aparecem fundidos em uma única linha. Nas páginas 2+ do mesmo documento, o padrão equivalente (`PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `DESTAQUE` como rótulos separados do conteúdo) já funciona corretamente.

## ETAPA 1 — Estrutura nativa da página 1 (`page.get_text("dict")`)

Página 1 de `input/Inf0024E.pdf`, 595×842pt, 21 blocos (`page.get_text("dict")`). Blocos de texto relevantes, na ordem de índice bruto do PDF (não a ordem de leitura — ver observação abaixo):

| Bloco (índice bruto) | bbox (x0,y0,x1,y1) | linhas | conteúdo (spans) |
| --- | --- | --- | --- |
| 2 | (50.0, 53.1, 516.8, 197.0) | 9 | 7 linhas em branco (`' '`, Helvetica 12.0) + `"Informativo de Jurisprudência n. 24 - Edição Extraordinária     28 de janeiro de 2025 "` (MuseoSans-500, 12.0, cor 6250078) + `"Direito Penal"` (mesma fonte/tamanho/cor) |
| 4 | (50.0, 217.2, 465.0, 245.6) | 2 | `"Este periódico destaca teses jurisprudenciais..."` (MuseoSans-500, 9.0, cor 6250078) + 1 linha em branco (Helvetica 12.0) |
| 8 | (52.0, 252.0, 173.9, 267.0) | 1 | `"CORTE ESPECIAL"` (MuseoSans-700, **15.0**, cor 11853) |
| 9 | (145.6, 297.0, 536.0, 337.0) | 4 | `"PROCESSO"` (MuseoSans-500, 10.0, cor 11853) + 3 linhas de valor (MuseoSans-300, 10.0, cor 0) |
| 10 | (108.6, 357.0, 433.5, 367.0) | 2 | `"RAMO DO DIREITO"` + valor |
| 13 | (70.0, 490.0, 121.8, 500.0) | 1 | `"DESTAQUE"` (cor **16777215** = branco, sobre caixa colorida) |
| 19 | (52.0, 50.0, 270.7, 102.0) | 2 | `"Informativo"` (MuseoSans-300, **26.0**, cor 15446333) + `"de Jurisprudência"` (MuseoSans-700, 26.0, mesma cor) |
| 20 | (36.0, 814.5, 559.0, 824.5) | 2 | rodapé de URL + contador de página `"1/29"` |

**Observação crítica**: o bloco 19 (o título estilizado, y0=50.0) tem índice bruto MAIOR que os blocos 0–18, embora seja visualmente o elemento mais ao topo da página. A ordem de leitura usada pelo pipeline (`_sorted_native_text_blocks`/`_geometric_reading_order_text`, `converter.py`) já reordena os blocos por `(round(y0,1), x0)` antes de processá-los — então essa inversão bruta de índice não é, por si só, a causa do defeito; após o reordenamento, a sequência de leitura fica: título (y0=50.0) → bloco 2 (y0=53.1, edição/data + Direito Penal) → bloco 4 (y0=217.2, aviso) → bloco 8 (y0=252.0, CORTE ESPECIAL) → bloco 9 (PROCESSO) → ... — visualmente correta.

## ETAPA 2 — Rastreamento pelo pipeline

### 2.1 Extração nativa (MarkItDown/pdfminer)

Chamando `native_engine.convert(page_path)` isoladamente (página 1 isolada em PDF de página única, como o pipeline faz), o `text_content` retornado **já separa corretamente** os elementos:

```
Informativo\nde Jurisprudência\n\nInformativo de Jurisprudência n. 24 - Edição Extraordinária     28 de janeiro de 2025\nDireito Penal\n\nEste periódico destaca teses jurisprudenciais e não consiste em repositório oficial de jurisprudência.\n\nCORTE ESPECIAL\n\nPROCESSO\n\n...
```

`_has_native_reading_order_defect(content, reference_content)` → `False`. `_has_fabricated_native_table(content, reference_content)` → `False`. Logo, em produção, `content` permanece o texto do MarkItDown (correto), **não** cai no fallback para `reference_content`.

### 2.2 `recompose_native_paragraphs` — PRIMEIRO estágio da fusão

Apesar de `content` já estar corretamente segmentado, `converter.py` chama incondicionalmente:

```python
content = recompose_native_paragraphs(content, native_blocks)
```

Dentro da função, o texto de entrada (`content`) é usado apenas como referência de contagem de tokens (`overlap >= 0.98`) — o texto efetivamente retornado é `geometric_text`, reconstruído inteiramente a partir de `blocks` (geometria bruta), ignorando a segmentação em parágrafos que o MarkItDown já havia acertado. Chamando a função de produção, sem nenhuma modificação, diretamente sobre os blocos reais da página 1 (`page.get_text("blocks")`, ordenados como o pipeline ordena), o resultado já reproduz integralmente o defeito de produção — confirmando que a fusão não depende de nenhuma peculiaridade do MarkItDown, apenas da reconstrução geométrica.

**Mecanismo exato**: para cada bloco, a função filtra linhas em branco (`if line.strip()`) antes de dividir a altura do bloco pelo número de linhas restantes:

```python
physical_lines = [re.sub(r"\s+", " ", line).strip() for line in block_text.split("\n") if line.strip()]
line_height = (y1 - y0) / len(physical_lines)
```

Para o bloco 2 (9 linhas físicas brutas: 7 em branco + 2 reais), isso produz `line_height = (197.0 - 53.1) / 2 = 71.95` — quando a altura real de cada linha (medida via `page.get_text("dict")`) é de apenas 10-12pt. A primeira linha real ("Informativo de Jurisprudência n. 24...") recebe a posição interpolada `y0=53.1`, que **precede** o fim real do bloco do título (`y1=102.0`) — produzindo um `gap` de junção **negativo** (`53.1 - 102.0 = -48.9`), que satisfaz trivialmente qualquer limiar `gap <= previous_height * 1.2`, tornando a fusão praticamente inevitável, não apenas provável.

O mesmo mecanismo se repete no bloco 4 (1 linha em branco à direita/abaixo do texto real, interpolação infla a altura de 9pt real para 28.4pt), inflando o limiar da junção seguinte (para "CORTE ESPECIAL") de ~11pt (correto) para ~34pt.

Tabela completa da simulação (função real, blocos reais, primeiras 12 linhas físicas resultantes):

| y0 (interpolado) | y1 (interpolado) | gap | altura anterior | limiar (h×1.2) | é 1ª linha do bloco | texto |
| --- | --- | --- | --- | --- | --- | --- |
| 50.0 | 76.0 | — | — | — | sim | "Informativo" |
| 76.0 | 102.0 | 0.0 | 26.0 | 31.2 | não | "de Jurisprudência" |
| **53.1** | 125.0 | **-48.9** | 26.0 | 31.2 | sim | "Informativo de Jurisprudência n. 24..." |
| 125.0 | 197.0 | 0.0 | 72.0 | 86.3 | não | "Direito Penal" |
| 217.2 | 245.6 | 20.2 | 72.0 | **86.3** | sim | "Este periódico destaca..." |
| 252.0 | 267.0 | 6.4 | 28.3 | **34.0** | sim | "CORTE ESPECIAL" |
| 297.0 | 307.0 | 30.0 | 15.0 | 18.0 | sim | "PROCESSO" *(gap > limiar → corretamente NÃO unido; a cadeia de fusão para aqui)* |

### 2.3 `compose_document` e cleaners posteriores

`compose_document` apenas concatena o conteúdo já fundido de cada página. Nenhum cleaner posterior (`remove_repetitive_margins`, `join_symbol_across_page_break`, `normalize_legal_symbols`, `build_legislative_headings`, `mark_final_index`, `clean_markdown`) tenta re-separar um parágrafo já unido — todos operam por correspondência de linha inteira ou padrão textual, e uma vez fundidos em uma única linha física, os 6 elementos originais não são mais recuperáveis por essas etapas. Isso também explica por que a linha de edição/data recorrente ("Informativo de Jurisprudência n. 24 - Edição Extraordinária ... 28 de janeiro de 2025"), corretamente removida como margem repetitiva em todas as outras 28 páginas, permanece visível apenas na página 1: `remove_repetitive_margins` só reconhece a linha quando ela é a primeira/última linha de conteúdo isolada da página; aqui ela está soterrada no meio de um parágrafo maior.

**Conclusão da Etapa 2**: o primeiro (e único) estágio de fusão é `recompose_native_paragraphs`, especificamente a interpolação de `line_height` sobre blocos que contêm linhas físicas em branco intercaladas com conteúdo real.

## ETAPA 3 — Comparação e avaliação de sinais discriminantes

### Casos corretos usados como controle

- Página 1, transição `"PROCESSO"` → conteúdo do processo: gap=30.0 > limiar=18.0 → corretamente separado (a cadeia de fusão desta página termina exatamente aqui).
- Páginas 2+ do mesmo documento: `PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `DESTAQUE` corretamente separados do conteúdo seguinte (nenhum desses blocos contém linhas em branco intercaladas).
- Índice do Código Civil (páginas 178–186): estrutura de blocos limpa, sem linhas em branco intercaladas — nenhuma interferência do mecanismo aqui.

### Sinais avaliados

| Sinal | Blast radius medido (4 PDFs) | Veredito |
| --- | --- | --- |
| Geometria real de linha em todo o pipeline (`page.get_text("dict")` substituindo a interpolação, já avaliado na investigação de `SAIBA MAIS`) | 44 decisões de junção alteradas, incluindo o índice do CC já endurecido | Descartado (evidência anterior, reconfirmada) |
| Mudança de fonte OU tamanho OU cor entre blocos consecutivos, como veto universal à junção | **91 de 329** junções atualmente corretas seriam quebradas (medido rodando `recompose_native_paragraphs` real sobre os 4 PDFs e comparando o estilo dominante de cada bloco de origem via `page.get_text("dict")`) — inclui continuações legítimas de frase com trecho em negrito (`CalibriLight,Bold` → `CalibriLight`, ementas do REsp) e citações em corpo menor dentro do mesmo parágrafo (`TimesNewRoman 12.0` → `TimesNewRoman 9.8`, AINTARESP) | Descartado — sinal isolado é bom demais no caso desta página, mas grosseiro demais em geral |
| **Interpolar `line_height` sobre o número TOTAL de linhas físicas do bloco (incluindo as em branco), preservando o índice original de cada linha real ao posicioná-la** | **3 de ~241 páginas do corpus** alteradas (medido rodando a função real com essa única alteração, página a página, nos 4 PDFs) | Candidato viável — ver abaixo |
| Sequência de blocos curtos / caixa alta / centralização / largura isolados | Não avaliados isoladamente com simulação completa — já subsumidos: rótulos em caixa alta curtos (`PROCESSO`, `CORTE ESPECIAL`) já são protegidos por `native_label_pattern` quando são a **primeira** linha de um bloco seguinte; o defeito desta página ocorre porque esses rótulos são fundidos como **continuação** do bloco **anterior** (proteção assimétrica pré-existente, não teria efeito aqui sem o sinal de interpolação acima) | Não discriminam sozinhos; não avaliados como candidato independente |

### Candidato aceito: interpolação sensível a linhas em branco

Alteração pontual, dentro de `recompose_native_paragraphs`: ao dividir a altura do bloco para estimar a posição de cada linha física, usar o número TOTAL de linhas do split original (`block_text.split("\n")`, incluindo as em branco), não apenas as sobreviventes após o filtro — preservando o índice de cada linha real dentro dessa contagem total ao calcular sua posição interpolada. As linhas em branco continuam sendo descartadas do resultado final (não aparecem no Markdown); apenas a ARITMÉTICA da interpolação passa a contabilizá-las.

Simulação completa (função real, com essa única mudança, rodada nas 4 PDFs, 241 páginas):

- **`Inf0024E.pdf` página 1** (defeito-alvo): título, edição/data, "Direito Penal", aviso editorial e "CORTE ESPECIAL" ficam cada um em parágrafo próprio — igual à estrutura já correta das páginas 2+. Nenhum outro elemento da página muda.
- **`AINTARESP_1462304-PA.pdf` página 11**: separa `"...GURGEL DE FARIA"` de `"Presidente da Sessão Exmo. Sr. Ministro GURGEL DE FARIA"` — inspeção confirma que o bloco `"Presidente da Sessão"` também tem uma linha em branco à esquerda (`' \nPresidente da Sessão\nExmo. Sr. Ministro GURGEL DE FARIA\n'`), o mesmo mecanismo de causa raiz. **Este é território do achado pendente `Papel/Nome`** (já documentado, duas rodadas de investigação sem critério seguro geral encontrado).
- **`REsp_1704551-SP.pdf` página 2**: separa `"MINISTRA NANCY ANDRIGHI"` do parágrafo de assinatura anterior — mesmo mecanismo (bloco `' \nBrasília (DF), 02 de abril de 2019(Data do Julgamento)\n'` com linha em branco líder). **Também território de `Papel/Nome`.**
- `L10.406_CC_2002.pdf`: nenhuma página afetada.

Em nenhum dos 3 casos o candidato produz uma junção NOVA incorreta ou perda de token — todas as 3 diferenças são no sentido de SEPARAR conteúdo hoje indevidamente unido, e as duas fora do alvo desta mudança coincidem exatamente com o padrão já descrito no achado `Papel/Nome` ("fusão geométrica de listas Papel/Nome sem `:`, blocos com o mesmo x0, sem recuo").

### Por que a conclusão é "A condicional", não "A" pura

O candidato é determinístico, geral (não depende de nome de arquivo, número de página, ou texto como "CORTE ESPECIAL") e tem blast radius extremamente baixo e totalmente mapeado. Mas ele **não pode ser implementado como "uma mudança = um defeito"** sem decisão humana, porque:

1. As duas páginas fora do alvo pertencem a um achado JÁ documentado e FORMALMENTE fechado sem correção (`fix-role-name-list-cross-block-fusion`, arquivado em 2026-08-07 como fechamento administrativo, não uma correção).
2. Implementar este candidato produziria uma alteração de corpus em `AINTARESP_1462304-PA.md` e `REsp_1704551-SP.md` que um validador ingênuo classificaria como "alteração inesperada fora do escopo" — desqualificando a mudança pelos critérios de validação já estabelecidos neste projeto (`AINT, REsp e CC sem alterações inesperadas`), mesmo que a alteração seja, pelo próprio mérito, uma correção (não uma regressão).
3. Não foi encontrado, dentro do tempo desta investigação, um refinamento adicional que preserve o candidato para a página-alvo mas exclua especificamente essas 2 páginas sem introduzir uma condição ad-hoc (ex. "só na página 1 do documento" seria uma regra específica de página, proibida pela tarefa).

## Próximos passos possíveis (não iniciados)

1. Levar esta sobreposição para decisão humana explícita: aceitar o efeito colateral em `Papel/Nome` como uma correção parcial documentada (não uma regressão) e prosseguir com TDD/implementação sob uma mudança que declare abertamente tocar as duas áreas; OU
2. Investigar um sinal adicional que distinga estruturalmente a capa editorial (bloco de título com fonte >20pt, cor de marca, presença de imagem de fundo no mesmo intervalo y — blocos 0/1 tipo=1 não avaliados nesta rodada) do padrão `Papel/Nome` (blocos de texto puro, sem elementos gráficos de fundo), o que permitiria escopar o candidato apenas à capa; OU
3. Tratar esta sobreposição como evidência adicional a favor de uma futura mudança dedicada a `Papel/Nome` que use precisamente este mecanismo (interpolação sensível a linhas em branco) como parte de um critério mais amplo — mas isso reabriria uma investigação já fechada duas vezes e exigiria sua própria validação completa contra os R01 e demais casos já documentados como frágeis.

Nenhuma dessas opções foi executada nesta investigação.
