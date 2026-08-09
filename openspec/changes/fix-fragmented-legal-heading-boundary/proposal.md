## Why

`output/REsp_1704551-SP.md` tem, em duas páginas (1 e 6), a mesma ementa fragmentada logo no início:

```
RECURSO

ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE COMPROMISSO ARBITRAL E DE SENTENÇA ARBITRAL. OMISSÃO, CONTRADIÇÃO OU ERRO MATERIAL. AUSÊNCIA. VALOR DA CAUSA. IMPUGNAÇÃO. MENSURAÇÃO DO CONTEÚDO ECONÔMICO. CONDENAÇÃO EM SENTENÇA ARBITRAL. POSSIBILIDADE.
```

## Diagnóstico e decisão (histórico desta mudança)

Esta mudança começou como diagnóstico puro. Conclusão: **A) CRITÉRIO SEGURO ENCONTRADO** — causa raiz comprovada, critério exato definido e validado empiricamente com **blast radius de exatamente 2 em ~241 páginas do corpus — as duas únicas ocorrências reais do defeito, sem nenhum falso positivo e sem nenhum falso negativo** (ver `design.md` para a evidência completa). Aprovado por decisão humana para TDD/implementação, restrita ao critério diagnosticado.

## Causa raiz (resumo — detalhes completos em `design.md`)

O próprio PyMuPDF — em `page.get_text("dict")` **e** em `page.get_text("blocks")`, igualmente — fragmenta uma linha de texto totalmente justificada com espaçamento entre palavras muito largo (aqui, "RECURSO ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE") em vários registros de "linha" separados, um por palavra, apesar de todos compartilharem exatamente a mesma coordenada vertical (`y0=339.75, y1=351.75`, sem nenhuma diferença, nem de arredondamento). Isso não é um defeito introduzido por este pipeline — é uma característica da própria extração do PyMuPDF diante desse padrão tipográfico específico.

O pipeline já recompõe corretamente a maior parte dessas pseudo-linhas (`ESPECIAL.` → `PROCESSUAL` → `CIVIL.` → ... fluem normalmente), exceto a primeira ("RECURSO"), porque ela coincide, por acaso, com o padrão já usado para proteger rótulos de campo genuínos (`PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `AGRAVANTE` etc.) de serem fundidos ao valor que os segue (`native_label_pattern.match(previous_text) and previous_is_first` em `recompose_native_paragraphs`). "RECURSO" é uma palavra isolada, inteiramente maiúscula, sem dígito ou pontuação, e é a primeira linha física do seu bloco de origem — satisfazendo o mesmo critério usado para rótulos reais, mas sem ser um rótulo.

A varredura dos 4 PDFs mostrou que esse mesmo mecanismo de base (PyMuPDF fragmentando uma linha em pseudo-linhas de mesma coordenada Y, cuja primeira bate no padrão de rótulo) ocorre **76 vezes** no corpus — e em **74 delas é o comportamento correto e já validado** (rótulo:valor genuíno, ex. `PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `AGRAVANTE`, `AGRAVADO`, `ASSUNTO`, `RECORRENTE`, `VÍDEO DO JULGAMENTO`). Somente as 2 ocorrências de `RECURSO`/`ESPECIAL.` são falsos positivos desse guard.

## Critério exato

O que distingue estruturalmente um rótulo genuíno de um falso positivo como `RECURSO`: nos rótulos genuínos, as demais linhas físicas do MESMO bloco (o "valor" do campo) começam em uma coordenada horizontal (x0) consistentemente DIFERENTE (recuada) da coordenada do próprio rótulo — um recuo estrutural de "rótulo: valor". No caso `RECURSO`, as demais linhas do bloco (a continuação natural do parágrafo/ementa) retornam à MESMA coordenada x0 do próprio bloco — um parágrafo justificado comum, sem coluna de valor recuada.

Medido nos 46 blocos do corpus que têm essa estrutura completa (rótulo + linhas adicionais no mesmo bloco): 44 têm recuo consistentemente diferente (rótulo genuíno, 0–23% das linhas seguintes compartilham a margem do rótulo); exatamente 2 têm a margem idêntica (81% das linhas seguintes compartilham a margem do "rótulo") — e são precisamente as 2 ocorrências reais do defeito. Não há nenhum caso do corpus entre 23% e 81% (lacuna de 58 pontos percentuais). O limiar de decisão é fixado em **50%** (maioria simples), o ponto médio dessa lacuna — não um número ajustado a um único caso (justificativa completa em `design.md`, seção "Decisão aprovada e limiar geométrico formalizado").

## What Changes

- `src/pipeline_juridico/converter.py`: `_sorted_native_text_blocks` passa a carregar, além de `(y0, y1, texto)` por bloco, o x0 de cada linha física bruta do bloco (dado geométrico já disponível via `page.get_text("dict")`, hoje descartado).
- `src/pipeline_juridico/cleaner.py`: `recompose_native_paragraphs` usa esse dado exclusivamente para refinar a condição `native_label_pattern.match(previous_text) and previous_is_first` — a proteção de rótulo só permanece ativa quando o bloco de origem não tem outras linhas físicas (comportamento atual preservado) OU quando mais de 50% dessas outras linhas têm x0 a menos de 2pt do x0 da própria linha-rótulo. Nenhuma outra condição de `should_join` é alterada.
- Nenhum vocabulário jurídico, nome de arquivo, número de página ou processo é usado como critério — apenas geometria (x0) e a estrutura já existente (contagem/posição de linhas físicas).

## Fora do escopo (confirmado)

`Papel/Nome`, thin-space, rodapés técnicos, `SUBTÍTULO`, índice, R01, `SAIBA MAIS`, capa editorial de `Inf0024E.pdf` — nenhum deve ser alterado por esta mudança. Extrator, roteamento, OCR e dependências não são tocados. Nenhuma alteração fora das 2 páginas-alvo de `REsp_1704551-SP.md` é esperada ou aceitável.

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Recomposição geométrica de parágrafos" passa a cobrir também a distinção entre um rótulo de campo genuíno e uma pseudo-linha criada pela fragmentação do PyMuPDF dentro de uma única linha visual justificada, usando o padrão de recuo (x0) das demais linhas físicas do mesmo bloco.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (`recompose_native_paragraphs`), `src/pipeline_juridico/converter.py` (`_sorted_native_text_blocks`). Nenhuma outra função, o extrator, o roteamento, o OCR ou as dependências são tocados.
- Testes: cobertura das 2 ocorrências reais, dos 8 rótulos genuínos citados na tarefa, de `Papel/Nome` inalterado, de controles próximos ao limiar de 50%, e de blocos sem dado de x0 (comportamento preservado).
- Corpus de regressão: reconversão `--no-ocr` dos 4 PDFs, diff completo explicado, idempotência confirmada.
