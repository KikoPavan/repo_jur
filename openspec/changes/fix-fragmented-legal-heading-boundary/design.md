## Contexto

`output/REsp_1704551-SP.md` contém, nas páginas 1 e 6 (o mesmo conteúdo de ementa aparece duas vezes no documento — uma no resumo inicial, outra dentro do acórdão), a seguinte fragmentação:

```
RECURSO

ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE COMPROMISSO ARBITRAL E DE SENTENÇA ARBITRAL. OMISSÃO, CONTRADIÇÃO OU ERRO MATERIAL. AUSÊNCIA. VALOR DA CAUSA. IMPUGNAÇÃO. MENSURAÇÃO DO CONTEÚDO ECONÔMICO. CONDENAÇÃO EM SENTENÇA ARBITRAL. POSSIBILIDADE.
```

Não há outras ocorrências desse defeito específico no corpus (confirmado por varredura completa nos 4 PDFs — ver ETAPA 4).

## ETAPA 1 — Inspeção nativa

`input/REsp_1704551-SP.pdf`, página 1, bloco geométrico com `bbox=(160.1, 339.75, 558.09, 650.0)` (o mesmo bloco na página 6, com `bbox=(160.1, 326.8, 558.1, 637.0)`, apenas deslocado verticalmente). Extração via `page.get_text("dict")`, sem arredondamento:

| # | texto | bbox (x0, y0, x1, y1) | fonte | tamanho | flags |
| --- | --- | --- | --- | --- | --- |
| linha 0 | `"RECURSO "` | (160.10, **339.75**, 208.63, **351.75**) | CalibriLight | 12.0 | 0 |
| linha 1 | `"ESPECIAL. "` | (220.10, **339.75**, 269.40, **351.75**) | CalibriLight | 12.0 | 0 |
| linha 2 | `"PROCESSUAL "` | (280.90, **339.75**, 346.02, **351.75**) | CalibriLight | 12.0 | 0 |
| linha 3 | `"CIVIL. "` | (357.45, **339.75**, 386.95, **351.75**) | CalibriLight | 12.0 | 0 |
| linha 4 | `"ARBITRAGEM. "` | (398.40, **339.75**, 467.36, **351.75**) | CalibriLight | 12.0 | 0 |
| linha 5 | `"NULIDADE "` | (478.80, **339.75**, 531.25, **351.75**) | CalibriLight | 12.0 | 0 |
| linha 6 | `"DE "` | (542.70, **339.75**, 558.06, **351.75**) | CalibriLight | 12.0 | 0 |
| linha 7 | `"COMPROMISSO ARBITRAL E DE SENTENÇA ARBITRAL. OMISSÃO, CONTRADIÇÃO OU "` | (160.10, 353.95, 558.04, 365.95) | CalibriLight | 12.0 | 0 |

As linhas 0–6 têm **exatamente** o mesmo `y0`/`y1` (339.75/351.75, sem diferença de nenhuma casa decimal, incluindo `origin` idêntico em y=348.75) — ou seja, é **uma única linha visual**, mas o PyMuPDF a devolve como 7 registros de "linha" separados (cada um com 1 span), um por palavra. A linha 7 ("COMPROMISSO ARBITRAL...") já é uma linha real seguinte (y0=353.95), devolvida corretamente como uma única linha/span, cobrindo toda a largura da coluna.

Gap horizontal entre as pseudo-linhas 0→1: `220.10 - 208.63 = 11.47pt`; 1→2: `11.50pt`; 4→5: `11.42pt` — consistentemente ~11.5pt, um espaçamento bem maior que o espaço normal entre palavras (que nesta mesma fonte/tamanho fica em torno de 2–3pt, visível dentro dos spans de texto corrido como a linha 7). Esse é o padrão típico de texto **totalmente justificado**, em que o mecanismo de justificação distribui espaço extra entre as palavras para preencher a largura da coluna — aqui, largo o bastante para o agrupador de linhas do PyMuPDF tratar cada palavra como uma "linha" própria, apesar da coordenada Y idêntica.

`rawdict` não foi necessário — `dict` já expõe a coordenada exata (`float64`) sem perda de precisão, suficiente para confirmar a igualdade exata de Y.

## ETAPA 2 — Rastreamento pelo pipeline

### 2.1 O PDF já entrega a estrutura fragmentada (resposta: **A**, não B)

Confirmado nas duas APIs do PyMuPDF usadas pelo pipeline:

- `page.get_text("blocks")` (usado por `_sorted_native_text_blocks`, que alimenta `recompose_native_paragraphs`): o texto bruto do bloco já vem como `'RECURSO \nESPECIAL. \nPROCESSUAL \nCIVIL. \nARBITRAGEM. \nNULIDADE \nDE \nCOMPROMISSO ARBITRAL...'` — cada palavra já separada por `\n`.
- `page.get_text("dict")`: confirma que a causa é a mesma no nível mais baixo da extração — 7 registros de linha com y idêntico, não uma peculiaridade de reconstrução de texto do modo "blocks".

Ou seja: **o PDF, através do próprio extrator PyMuPDF, já entrega a estrutura fragmentada** — nenhuma etapa deste pipeline (nem MarkItDown/pdfminer, nem `_sorted_native_text_blocks`, nem `recompose_native_paragraphs`) introduz a fragmentação inicial. O que o pipeline faz é **deixar de recompor** apenas a primeira dessas pseudo-linhas.

### 2.2 `recompose_native_paragraphs` — onde a recomposição falha

Dentro da função, os blocos são achatados em uma lista de linhas físicas com posição interpolada. Como as 7 pseudo-linhas (0–6) já vêm de um único bloco PyMuPDF com posições Y reais e idênticas (não há problema de interpolação aqui — o bug de linhas em branco já identificado em investigações anteriores não se aplica, porque não há linhas em branco neste bloco), a lógica geométrica (`gap <= previous_height * 1.2`) funciona corretamente para todas as transições **exceto** a primeira:

- `"RECURSO"` → `"ESPECIAL."`: gap real = 0 (mesma linha Y). A condição geométrica permitiria a união — mas a condição:
  ```python
  not (native_label_pattern.match(previous_text) and previous_is_first)
  ```
  bloqueia, porque `"RECURSO"` (sem pontuação, todo maiúsculo) bate em `native_label_pattern`, e é a primeira linha física (`is_first=True`) do seu bloco de origem — exatamente o mesmo critério usado para proteger rótulos de campo genuínos como `PROCESSO`, `TEMA`, `RAMO DO DIREITO` (ver `fix-vertical-fragmented-text-recomposition`, arquivada em 2026-08-07, que introduziu essa proteção).
- `"ESPECIAL."` → `"PROCESSUAL"`: `"ESPECIAL."` tem pontuação, não bate em `native_label_pattern` — a união prossegue normalmente.
- Da mesma forma, todas as transições seguintes (`PROCESSUAL`→`CIVIL.`, ..., `DE`→`COMPROMISSO ARBITRAL...`) fluem normalmente, porque nenhuma delas volta a satisfazer simultaneamente `native_label_pattern` + `is_first` (só a primeira pseudo-linha de um bloco pode ser `is_first`).

**Conclusão da Etapa 2**: o primeiro (e único) estágio que impede a recomposição correta é a condição de proteção de rótulo dentro de `recompose_native_paragraphs`, aplicada sobre uma pseudo-linha fragmentada pelo próprio PyMuPDF que coincide, por acaso, com o padrão de um rótulo de campo genuíno.

### 2.3 `compose_document` e cleaners posteriores

Nenhuma etapa posterior tenta reunir parágrafos já separados — o mesmo padrão já observado nas duas investigações anteriores (capa editorial, `SAIBA MAIS`).

## ETAPA 3 — Controles

### Controle positivo direto: mesma expressão, união correta

`REsp_1704551-SP.pdf`, página 12, mesmo tipo de ementa, começando também com `"RECURSO ESPECIAL."`:

```
L0S0 bbox=(160.0, 287.5, 558.1, 299.5) texto="RECURSO ESPECIAL. AÇÃO CIVIL PÚBLICA. COMERCIALIZAÇÃO DE UNIDADES "
```

Aqui a linha inteira é devolvida pelo PyMuPDF como **uma única linha, um único span**, cobrindo toda a largura da coluna (160.0–558.1) — sem fragmentação alguma. `"RECURSO ESPECIAL. AÇÃO CIVIL PÚBLICA..."` contém pontuação (o ponto após "ESPECIAL"), então nem chegaria a bater em `native_label_pattern` de qualquer forma. O resultado final em `output/REsp_1704551-SP.md` já mostra essa ementa corretamente unida em uma única linha (linha 385 do arquivo). Esse controle confirma que a mesma expressão jurídica, quando o PyMuPDF não fragmenta a linha, é recomposta (ou melhor, nunca precisa ser recomposta) corretamente — reforçando que o defeito é puramente geométrico/estrutural, não relacionado ao conteúdo textual "RECURSO ESPECIAL" em si.

### Controle do mecanismo de base: 74 casos onde o MESMO guard funciona corretamente

Varredura completa dos 4 PDFs (script de diagnóstico, ver ETAPA 4) encontrou 76 blocos onde a mesma combinação de sinais ocorre (PyMuPDF fragmenta uma linha em pseudo-linhas de Y idêntico; a primeira pseudo-linha bate em `native_label_pattern`; é a primeira linha física do bloco). Em **74 delas**, esse é exatamente o comportamento **desejado e já validado**: rótulos de campo genuínos como `PROCESSO`, `TEMA`, `RAMO DO DIREITO` (`Inf0024E.pdf`, 67 ocorrências), `AGRAVANTE`/`AGRAVADO`/`ASSUNTO`/`RECORRENTE` (`AINTARESP_1462304-PA.pdf`/`REsp_1704551-SP.pdf`, 7 ocorrências) e `VÍDEO DO JULGAMENTO` (4 ocorrências) — todos corretamente protegidos de serem fundidos ao valor que os segue, mesmo quando o próprio PyMuPDF fragmenta a linha "rótulo: valor" em pseudo-linhas de Y idêntico (o mesmo tipo de artefato do defeito, aplicado a um contexto onde a proteção é correta).

Isso significa: **o mecanismo geométrico de base (fragmentação por Y idêntico) é extremamente comum e o guard que o utiliza está correto na esmagadora maioria dos casos** — qualquer candidato de correção que enfraqueça esse guard de forma ampla arrisca quebrar 74 proteções já validadas.

### Sinal discriminante encontrado

Comparando a geometria completa dos 46 blocos do corpus que têm essa estrutura (rótulo fragmentado + linhas físicas adicionais no mesmo bloco, permitindo comparação):

| Caso | x0 do "rótulo" | x0 das linhas seguintes do mesmo bloco | fração das linhas seguintes com a MESMA margem do rótulo |
| --- | --- | --- | --- |
| `Inf0024E.pdf` p.1, `PROCESSO` | 145.6 | 218.4 (todas) | 0% |
| `Inf0024E.pdf` p.1, `TEMA` | 171.8 | 218.4 (todas) | 0% |
| `Inf0024E.pdf` p.4, `RAMO DO DIREITO` | 108.6 | 218.4 (todas) | 0% |
| `REsp_1704551-SP.pdf` p.3, `RECORRENTE` | 104.2 | 104.2, 203.4 (mista) | 23% |
| `REsp_1704551-SP.pdf` p.1/p.6, `RECURSO` | 160.1 | 160.1, 234.0, 318.1, 405.4, 438.9 | **81%** |

Nos rótulos genuínos, as linhas seguintes do MESMO bloco (o "valor" do campo) começam consistentemente em uma coordenada x0 diferente e maior que a do rótulo — um recuo estrutural de coluna "rótulo: valor" (a mesma convenção visual, por exemplo, de `PROCESSO` na coluna esquerda com o texto do processo recuado à direita). Em `RECURSO`, as linhas seguintes do bloco (a continuação natural do parágrafo justificado) retornam predominantemente (81%) à MESMA margem esquerda do próprio bloco — não há coluna de valor recuada, é um parágrafo comum.

Todos os demais sinais pedidos na tarefa (fonte, tamanho, flags, caixa alta, pontuação) são **idênticos** entre `RECURSO` (defeito) e `PROCESSO`/`TEMA` (controle correto) — mesma fonte, mesmo tamanho (exceto os rótulos maiúsculos e negritados de "RELATORA"/cabeçalhos, que usam fonte diferente mas não fazem parte deste padrão), mesmos flags, mesma pontuação (nenhuma), mesma caixa alta. **Apenas o padrão de recuo das linhas seguintes do bloco discrimina corretamente os dois grupos**, com uma margem enorme (0%–23% vs. 81%, sem nenhum caso intermediário ambíguo no corpus).

## ETAPA 4 — Blast radius

### Candidato avaliado: refinar o guard de rótulo para exigir recuo consistente das linhas seguintes

Critério exato: a condição `native_label_pattern.match(previous_text) and previous_is_first` só bloqueia a junção quando, ADICIONALMENTE, as demais linhas físicas do MESMO bloco de origem têm x0 predominantemente (mais de 50%) DIFERENTE (por pelo menos 2pt) do x0 da própria linha-rótulo. Quando o bloco não tem mais nenhuma linha física além do rótulo, o comportamento atual (protegido) é mantido — sem mudança para blocos "rótulo: valor" que estão inteiramente contidos na mesma linha Y sem continuação.

**Importante**: isso exige que o pipeline passe a rastrear a coordenada x0 por linha física — hoje `_sorted_native_text_blocks` descarta essa informação (só retorna `y0, y1, texto`). Qualquer implementação futura precisaria estender essa função (ou introduzir uma nova), sem alterar o extrator, o roteamento ou o OCR.

**Simulação**: a função real `recompose_native_paragraphs` (importada sem modificação) foi comparada com uma reimplementação idêntica em tudo, exceto esse refinamento pontual do guard de rótulo — rodada página a página nos 4 PDFs (241 páginas), usando os mesmos blocos reais (`page.get_text("blocks")`) e x0 obtido via `page.get_text("dict")`.

**Resultado**:

| PDF | Páginas com diferença |
| --- | --- |
| `Inf0024E.pdf` (29 páginas, inclui as 67 proteções `PROCESSO`/`TEMA`/`RAMO DO DIREITO`/`VÍDEO DO JULGAMENTO`) | **0** |
| `AINTARESP_1462304-PA.pdf` (12 páginas, inclui as proteções `AGRAVANTE`/`AGRAVADO`/`ASSUNTO`) | **0** |
| `REsp_1704551-SP.pdf` (14 páginas, inclui as proteções `RECORRENTE` nas páginas 3 e 14) | **2** (páginas 1 e 6 — exatamente as 2 ocorrências reais do defeito) |
| `L10.406_CC_2002.pdf` (186 páginas) | **0** |

**Total: 2 de 241 páginas alteradas — nenhum falso positivo, nenhum falso negativo.** Nas duas páginas alteradas, a única mudança é a união de "RECURSO" com "ESPECIAL. PROCESSUAL CIVIL. ... POSSIBILIDADE." em um único parágrafo (com todo o restante da página deslocado em um parágrafo, sem qualquer alteração de conteúdo); contagem de tokens confirmada idêntica antes/depois (358→358 na página 1, 307→307 na página 6).

Classificação de cada alteração: **correta** (as 2 únicas mudanças corrigem exatamente o defeito relatado, sem efeito colateral detectável).

### Verificação de impacto nas áreas protegidas

Como a simulação cobre as 241 páginas do corpus inteiro comparando diretamente com a saída da função de produção real, os seguintes itens ficam confirmados por decorrência direta do resultado "0 diferenças" em cada arquivo:

- **R01, 8 SUBTÍTULO, índice do CC**: `L10.406_CC_2002.pdf`, 0 páginas alteradas.
- **Rodapés técnicos**: nenhuma página de `AINTARESP_1462304-PA.pdf`/`REsp_1704551-SP.pdf` fora das 2 páginas-alvo foi alterada; nas 2 páginas-alvo, o rodapé técnico (quando presente) permanece na mesma posição relativa, isolado como último parágrafo, inalterado.
- **Thin-space, `SAIBA MAIS`, capa editorial**: `Inf0024E.pdf`, 0 páginas alteradas.
- **`Papel/Nome`**: `AINTARESP_1462304-PA.pdf`, 0 páginas alteradas (inclui a página 11, já documentada como achado pendente); `REsp_1704551-SP.pdf` páginas 3 e 14 (`RECORRENTE`), 0 alteração.

### Candidato descartado sem necessidade de simulação completa

Um candidato mais amplo — remover ou enfraquecer de forma geral a condição `previous_is_first` do guard de rótulo (por exemplo, exigindo apenas que a linha bata em `native_label_pattern`, independentemente de ser a primeira linha do bloco) — foi descartado sem chegar a ser simulado por análise direta da varredura da Etapa 3: esse guard já é usado deliberadamente para permitir que palavras maiúsculas isoladas NO MEIO de um bloco (ementas fragmentadas palavra a palavra, ver `fix-vertical-fragmented-text-recomposition`) sejam unidas normalmente; enfraquecê-lo romperia esse comportamento já validado, sem nenhuma relação com a causa raiz específica deste defeito (que está exclusivamente na PRIMEIRA linha física do bloco).

## Conclusão

**A) CRITÉRIO SEGURO ENCONTRADO.**

- Causa raiz: fragmentação de uma linha totalmente justificada em pseudo-linhas de coordenada Y idêntica pelo próprio PyMuPDF, combinada com o guard existente de proteção de rótulo de campo (`native_label_pattern` + `previous_is_first`), que confunde a primeira pseudo-linha ("RECURSO") com um rótulo genuíno.
- Critério exato: exigir que as demais linhas físicas do mesmo bloco de origem tenham x0 predominantemente diferente do x0 da linha-rótulo para que a proteção continue ativa.
- Blast radius: 2 de 241 páginas do corpus, exatamente as 2 ocorrências reais do defeito, 0 falsos positivos, 0 falsos negativos, 0 perda/adição de token.
- Proposta mínima futura (não implementada nesta mudança): estender `_sorted_native_text_blocks` para carregar x0 por linha física, e usar esse dado em `recompose_native_paragraphs` para refinar exclusivamente essa condição do guard de rótulo, sem alterar mais nada da função.
