## Why

Em `AINTARESP_1462304-PA.md` (p.1, p.4) e `REsp_1704551-SP.md` (p.1, p.3, p.4, p.6, p.7, p.14) a ementa e outros parágrafos de mérito continuam fragmentados linha a linha, mesmo após a correção de `fix-vertical-fragmented-text-recomposition`, porque `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) tem um early-return no topo:

```python
if any(
    line.strip().startswith(":")
    for _, _, block_text in blocks
    for line in block_text.split("\n")
):
    return content
```

Essa condição varre TODOS os blocos da PÁGINA e, se QUALQUER linha física de QUALQUER bloco começar com `:` (formato usado nos campos "RÓTULO\n: VALOR" como RELATOR/AGRAVANTE/AGRAVADO/ADVOGADOS/RECORRENTE/RECORRIDO/RELATORA), a função inteira retorna `content` sem nenhuma recomposição — para a página inteira, não apenas para o bloco que contém o `:`. Inspeção geométrica confirma que, nas páginas afetadas, o bloco/ementa de mérito (ex. `AINTARESP_1462304-PA.pdf` p.1 bloco 7, 34 linhas físicas; `REsp_1704551-SP.pdf` p.1 bloco 4, 33 linhas físicas) é um bloco PyMuPDF totalmente distinto e sem nenhuma relação com o bloco que contém as linhas `:` — mas nunca chega a ser recomposto porque a verificação do guard não distingue blocos.

Essa causa é tecnicamente independente da corrigida em `fix-vertical-fragmented-text-recomposition`: lá, a função executava normalmente mas uma condição de junção linha-a-linha (`native_label_pattern`) decidia errado; aqui, a função inteira nunca chega a processar a página, por um bypass incondicional no topo, antes mesmo de montar a lista de linhas geométricas.

## What Changes

- Remover o early-return de página inteira baseado em `startswith(":")`.
- Substituir por uma condição escopada por bloco: para cada linha física, registrar se o bloco PyMuPDF de origem contém alguma linha física que comece com `:` (o mesmo teste textual já usado hoje, apenas reescopado). A condição de junção (`should_join`) passa a impedir a fusão sempre que a linha anterior OU a linha atual pertencer a um desses blocos — preservando a separação entre rótulo e valor e entre campos consecutivos — sem impedir a recomposição de blocos não relacionados na mesma página.
- Nenhuma outra condição de `recompose_native_paragraphs` é alterada (gap geométrico, `current_line_pattern`, `formal_structure_pattern`/`bare_structure_pattern`/`qualified_structure_pattern`, fechamento jurisprudencial, a correção de `native_label_pattern` por posição no bloco already implementada, early-return de tabelas `|`).
- Um teste pré-existente (`test_recompose_native_paragraphs_preserves_uppercase_label_and_value`) precisa ser atualizado: seu fixture (dois blocos de uma linha cada, "RELATOR" e ": MINISTRO FULANO") foi escrito para validar o antigo contrato de no-op total da função; com o escopo reduzido a nível de bloco, o par rótulo/valor continua sem se fundir (nenhum token é unido em uma única linha), mas passa a ser representado como dois parágrafos distintos (separados por linha em branco), a mesma convenção já usada em toda a função para blocos que não se unem. Justificativa detalhada em `design.md`.

## Capabilities

### New Capabilities
(nenhuma — correção pontual da capacidade existente)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Recomposição geométrica de parágrafos" passa a exigir que a proteção de campos `RÓTULO / : VALOR` seja aplicada por bloco geométrico de origem, não à página inteira — blocos sem nenhuma linha `:` continuam sendo recompostos normalmente mesmo quando outro bloco da mesma página contém esse padrão.

## Impact

- Código: `src/pipeline_juridico/cleaner.py`, exclusivamente dentro de `recompose_native_paragraphs`. Nenhum outro módulo é tocado.
- Testes: `tests/test_cleaner.py` — novos testes cobrindo os casos reais (página com campo `:` legítimo E parágrafo fragmentado não relacionado) e os negativos exigidos (rótulo/valor, múltiplos campos consecutivos, `:` no mesmo bloco do rótulo, listas/precedentes/títulos/campos estruturais, a correção de `native_label_pattern` já implementada, cabeçalhos repetitivos, SUBTÍTULO, R01, separações jurisprudenciais); atualização justificada de `test_recompose_native_paragraphs_preserves_uppercase_label_and_value`.
- Corpus: reconversão dos 4 PDFs fixos com `converter-juridico --no-ocr` confirmando a correção nas páginas listadas e ausência de regressão nos demais arquivos/páginas.
- Fora de escopo: qualquer alteração em `native_label_pattern`, no extrator, OCR, roteamento, dependências ou arquitetura; reabertura de mudanças arquivadas; exceções por arquivo/página/tribunal/texto.
