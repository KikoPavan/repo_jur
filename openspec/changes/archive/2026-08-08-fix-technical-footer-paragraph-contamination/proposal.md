## Why

A auditoria do corpus de regressão encontrou rodapés técnicos do STJ (ex. `GABGF09 AREsp 1462304 Petição : ... Documento Página N de 8` em `AINTARESP_1462304-PA.pdf`; `Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019` em `REsp_1704551-SP.pdf`) que permanecem no Markdown final ou, pior, ficam fundidos ao final de frases jurídicas legítimas — em um caso, interrompendo um nome próprio entre `Paulo de` e `Tarso Sanseverino` através de uma quebra de página. A causa raiz é que `remove_repetitive_margins` só reconhece um cabeçalho/rodapé repetido verbatim quando ele aparece como linha inteira ou como **prefixo** da linha seguinte (caso já corrigido em `fix-repeated-header-cross-page-fusion`, aplicável a cabeçalhos colados ao início do conteúdo da página seguinte); não existe hoje nenhum reconhecimento simétrico para quando o mesmo tipo de texto marginal aparece como **sufixo** colado ao final do conteúdo real da página anterior — exatamente a geometria de um rodapé.

## What Changes

- Estender o mecanismo de remoção de margens verbatim (`remove_repetitive_margins`/`remove_verbatim_margins` em `src/pipeline_juridico/cleaner.py`) para também reconhecer um rodapé técnico recorrente quando ele aparece como sufixo colado ao final da última linha de conteúdo de uma página, removendo apenas o trecho correspondente ao rodapé e preservando integralmente o texto substantivo anterior.
- Nenhuma lista fixa de números de processo/documento/código; o critério permanece baseado em recorrência verbatim entre páginas (já existente) e posição estrutural (início/fim de linha), sem depender de palavras-chave como `Documento`, `Página`, `DJe` ou `GABGF09`.
- Não afeta OCR, extrator, roteamento, dependências ou o defeito `Papel/Nome` (que permanece registrado como achado pendente e fora de escopo).

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Remoção de cabeçalhos e rodapés repetitivos" passa a cobrir também o caso em que o texto marginal repetido está fundido como **sufixo** ao final do conteúdo textual real da página anterior (simétrico ao caso de prefixo já coberto), removendo apenas o trecho marginal e preservando o conteúdo jurídico anterior.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (`remove_repetitive_margins`, função interna `remove_verbatim_margins`). Nenhuma outra área do pipeline (extrator, roteador, OCR, `recompose_native_paragraphs`) é alterada.
- Testes: novos casos em `tests/` cobrindo rodapé isolado, rodapé fundido ao final de parágrafo, rodapé fundido entre páginas interrompendo um nome, e os casos negativos (assinaturas eletrônicas legítimas, citações contendo palavras semelhantes, `Papel/Nome` inalterado).
- Corpus de regressão: reconversão `--no-ocr` dos 4 PDFs (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, `L10.406_CC_2002.pdf`), com diff explicado e idempotência confirmada.
