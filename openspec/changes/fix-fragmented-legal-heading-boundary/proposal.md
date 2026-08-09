## Why

`output/REsp_1704551-SP.md` tem, em duas páginas (1 e 6), a mesma ementa fragmentada logo no início:

```
RECURSO

ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE COMPROMISSO ARBITRAL E DE SENTENÇA ARBITRAL. OMISSÃO, CONTRADIÇÃO OU ERRO MATERIAL. AUSÊNCIA. VALOR DA CAUSA. IMPUGNAÇÃO. MENSURAÇÃO DO CONTEÚDO ECONÔMICO. CONDENAÇÃO EM SENTENÇA ARBITRAL. POSSIBILIDADE.
```

**Esta mudança é SOMENTE DIAGNÓSTICO** — nenhuma correção, teste de produção, arquivamento ou push foi realizado. `git status` permanece limpo além dos artefatos desta mudança.

## Conclusão do diagnóstico

**A) CRITÉRIO SEGURO ENCONTRADO.** Causa raiz comprovada, critério exato definido e validado empiricamente com **blast radius de exatamente 2 em ~241 páginas do corpus — as duas únicas ocorrências reais do defeito, sem nenhum falso positivo e sem nenhum falso negativo** (ver `design.md` para a evidência completa, rastreada estágio a estágio e validada com simulação da função real de produção nos 4 PDFs).

## Causa raiz (resumo — detalhes completos em `design.md`)

O próprio PyMuPDF — em `page.get_text("dict")` **e** em `page.get_text("blocks")`, igualmente — fragmenta uma linha de texto totalmente justificada com espaçamento entre palavras muito largo (aqui, "RECURSO ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE") em vários registros de "linha" separados, um por palavra, apesar de todos compartilharem exatamente a mesma coordenada vertical (`y0=339.75, y1=351.75`, sem nenhuma diferença, nem de arredondamento). Isso não é um defeito introduzido por este pipeline — é uma característica da própria extração do PyMuPDF diante desse padrão tipográfico específico.

O pipeline já recompõe corretamente a maior parte dessas pseudo-linhas (`ESPECIAL.` → `PROCESSUAL` → `CIVIL.` → ... fluem normalmente), exceto a primeira ("RECURSO"), porque ela coincide, por acaso, com o padrão já usado para proteger rótulos de campo genuínos (`PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `AGRAVANTE` etc.) de serem fundidos ao valor que os segue (`native_label_pattern.match(previous_text) and previous_is_first` em `recompose_native_paragraphs`). "RECURSO" é uma palavra isolada, inteiramente maiúscula, sem dígito ou pontuação, e é a primeira linha física do seu bloco de origem — satisfazendo o mesmo critério usado para rótulos reais, mas sem ser um rótulo.

A varredura dos 4 PDFs mostrou que esse mesmo mecanismo de base (PyMuPDF fragmentando uma linha em pseudo-linhas de mesma coordenada Y, cuja primeira bate no padrão de rótulo) ocorre **76 vezes** no corpus — e em **74 delas é o comportamento correto e já validado** (rótulo:valor genuíno, ex. `PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `AGRAVANTE`, `AGRAVADO`, `ASSUNTO`, `RECORRENTE`, `VÍDEO DO JULGAMENTO`). Somente as 2 ocorrências de `RECURSO`/`ESPECIAL.` são falsos positivos desse guard.

## Critério exato

O que distingue estruturalmente um rótulo genuíno de um falso positivo como `RECURSO`: nos rótulos genuínos, as demais linhas físicas do MESMO bloco (o "valor" do campo) começam em uma coordenada horizontal (x0) consistentemente DIFERENTE (recuada) da coordenada do próprio rótulo — um recuo estrutural de "rótulo: valor". No caso `RECURSO`, as demais linhas do bloco (a continuação natural do parágrafo/ementa) retornam à MESMA coordenada x0 do próprio bloco — um parágrafo justificado comum, sem coluna de valor recuada.

Medido nos 46 blocos do corpus que têm essa estrutura completa (rótulo + linhas adicionais no mesmo bloco): 44 têm recuo consistentemente diferente (rótulo genuíno, 0% das linhas seguintes compartilham a margem do rótulo); exatamente 2 têm a margem idêntica (81% das linhas seguintes compartilham a margem do "rótulo") — e são precisamente as 2 ocorrências reais do defeito.

## Fora do escopo (confirmado, não tocado nesta investigação)

`Papel/Nome`, thin-space, rodapés técnicos, `SUBTÍTULO`, índice, R01, `SAIBA MAIS`, capa editorial de `Inf0024E.pdf` — nenhum código foi alterado; nenhum teste de produção foi criado. A simulação completa nos 4 PDFs confirma 0 diferenças em `Inf0024E.pdf`, `AINTARESP_1462304-PA.pdf` e `L10.406_CC_2002.pdf` inteiros, e 0 diferenças em qualquer outro trecho de `REsp_1704551-SP.pdf` além das 2 ocorrências-alvo — confirmando que nenhuma das 74 proteções de rótulo genuíno já existentes é afetada. Extrator, roteamento, OCR e dependências não foram tocados nem avaliados para alteração.

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
(nenhuma — diagnóstico apenas, nenhuma implementação)

## Impact

- Nenhum código de `src/` ou `tests/` foi alterado. Todos os scripts de investigação foram executados fora do repositório versionado (`/tmp/.../scratchpad/`).
- Achado registrado em `LOOPS.md` (após aprovação deste relatório) para que uma futura mudança de implementação não precise refazer esta investigação.
