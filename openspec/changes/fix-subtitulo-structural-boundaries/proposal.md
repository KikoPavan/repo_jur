## Why

Em `output/L10.406_CC_2002.md` existem 8 ocorrências no corpo da lei em que o marcador estrutural `SUBTÍTULO` foi indevidamente anexado ao final do conteúdo anterior (artigo, parágrafo, inciso ou cabeçalho `TÍTULO`), em vez de formar seu próprio cabeçalho Markdown com a denominação que o segue. Causa raiz: `SUBTÍTULO`/`SUBTITULO` nunca foi incluído no vocabulário de marcadores estruturais usado por `recompose_native_paragraphs` (`formal_structure_pattern`, `bare_structure_pattern`, `qualified_structure_pattern`) nem por `build_legislative_headings` (`_LEGISLATIVE_MARKER_PATTERN`, `heading_levels`), ambos em `src/pipeline_juridico/cleaner.py`. A hierarquia formal do Código Civil é PARTE > LIVRO > TÍTULO > SUBTÍTULO > CAPÍTULO > SEÇÃO > SUBSEÇÃO, mas o requisito "Reconhecimento de estrutura legislativa" e o código só reconhecem PARTE, LIVRO, TÍTULO, CAPÍTULO, SEÇÃO e SUBSEÇÃO. Como resultado, `SUBTÍTULO I`/`II`/`III`/`IV` é tratado como texto comum e unido geometricamente ao bloco anterior, e nunca chega a `build_legislative_headings` como parágrafo próprio.

## What Changes

- Adicionar `SUBTÍTULO`/`SUBTITULO` ao vocabulário de marcadores estruturais reconhecidos em `src/pipeline_juridico/cleaner.py`: `_LEGISLATIVE_MARKER_PATTERN`, `formal_structure_pattern`, `bare_structure_pattern`, `qualified_structure_pattern` (usados por `recompose_native_paragraphs` e `build_legislative_headings`).
- Adicionar `"subtítulo"`/`"subtitulo"` a `heading_levels` no nível Markdown `4` (`####`), o mesmo nível hoje usado por `CAPÍTULO` — no corpus real, `CAPÍTULO` permanece em `####` independentemente de estar diretamente sob `TÍTULO` ou sob `SUBTÍTULO`, então essa é a única atribuição consistente com o esquema plano (nível fixo por palavra-chave, sem profundidade recursiva) já usado pelo projeto.
- Não alterar `current_line_pattern`, a lógica de junção geométrica de dispositivos (Art./§/inciso/alínea/item), a proteção de fechamento jurisprudencial, `mark_final_index`, o extrator, o roteamento, o OCR ou a arquitetura geral.

## Capabilities

### New Capabilities
(nenhuma — correção pontual da capacidade existente)

### Modified Capabilities
- `juridical-pdf-conversion`: os requisitos "Recomposição geométrica de parágrafos" e "Reconhecimento de estrutura legislativa" passam a incluir `SUBTÍTULO` na lista de marcadores estruturais formais reconhecidos, com nível Markdown `####` (mesmo nível de `CAPÍTULO`).

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (apenas os pontos listados acima), sem tocar em `inspector.py`, `router.py`, `engines.py`, `converter.py` ou dependências.
- Testes: novos testes de regressão em `tests/test_cleaner.py` cobrindo os 4 formatos positivos (artigo, parágrafo, inciso, cabeçalho `TÍTULO`) e os casos negativos (palavra comum, índice final, hierarquias já corretas, artigos consecutivos, os 4 casos do R01, precedentes jurisprudenciais).
- Corpus: reconversão dos 4 PDFs fixos com `converter-juridico --no-ocr` para confirmar as 8 correções e ausência de regressão nos demais 3 arquivos.
- Fora de escopo: qualquer regra específica a números de artigo ou ao Código Civil; reabertura de mudanças arquivadas; OCR real; arquivamento sem aprovação humana explícita.
