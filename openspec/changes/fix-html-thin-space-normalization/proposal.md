## Why

A auditoria do corpus encontrou 21 ocorrências do literal `&#8201;` (entidade HTML decimal do THIN SPACE, U+2009) em `output/Inf0024E.md`, coladas diretamente entre palavras e tokens sem nenhum espaço de separação real (ex. `apreensão de &#8201;37 gramas`, `Lei n.&#8201;11.343/2006`, `na&#8201;realidade`). Diagnóstico via extração bruta do PyMuPDF (`page.get_text()`) sobre `input/Inf0024E.pdf`, página 9, confirmou que o literal `&#8201;` já está embutido no texto do PDF de origem — não é produzido por nenhum código deste pipeline (MarkItDown/pdfminer apenas repassam os caracteres exatamente como estão no PDF; nenhuma função em `src/pipeline_juridico/` decodifica ou toca entidades HTML hoje). A causa mais provável é que o PDF foi gerado a partir de um documento HTML/rich-text em que a entidade `&#8201;` (originalmente destinada a virar um espaço fino de separação) nunca foi decodificada antes da renderização, ficando embutida como texto literal.

Uma varredura dos 4 PDFs do corpus de regressão por variantes equivalentes (`&#8201;`, `&#x2009;`/`&#X2009;`, `&thinsp;`, e o caractere Unicode real U+2009) confirmou que **somente** `&#8201;` ocorre, e **somente** em `Inf0024E.pdf` (21 ocorrências, página 9). Os outros 3 PDFs (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `L10.406_CC_2002.pdf`) têm zero ocorrências de qualquer variante. `L10.406_CC_2002.pdf` contém 501 ocorrências do caractere Unicode real non-breaking space (U+00A0) — um caractere diferente, semanticamente legítimo, já corretamente preservado como espaço de fato pela extração; está fora do escopo desta mudança.

## What Changes

- Adicionar uma normalização determinística e local em `src/pipeline_juridico/cleaner.py` que substitui o literal `&#8201;` (e as variantes equivalentes de THIN SPACE documentadas no diagnóstico: `&#x2009;`/`&#X2009;`, `&thinsp;`, sem diferenciação de maiúsculas/minúsculas) por um único espaço ASCII regular (U+0020), absorvendo espaços adjacentes já existentes para não duplicá-los.
- A correção é puramente textual/determinística (busca e substituição por regex do padrão exato da entidade, sem decodificação HTML genérica), aplicada de forma geral a qualquer página/documento do pipeline — nenhuma regra depende do nome do arquivo, número do informativo ou texto específico do Inf0024E.
- Nenhuma outra entidade HTML (`&amp;`, `&lt;`, `&nbsp;`, etc.) é tocada; a correção é restrita à classe de entidades equivalentes a espaço fino, evidenciada no diagnóstico.

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
- `juridical-pdf-conversion`: novo requisito "Normalização de entidades HTML de espaçamento fino" — o sistema SHALL substituir entidades HTML equivalentes a THIN SPACE (`&#8201;`, `&#x2009;`, `&thinsp;`, case-insensitive) por um espaço ASCII regular, sem duplicar espaços adjacentes e sem alterar qualquer outra entidade HTML ou conteúdo textual.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (nova função de normalização) e `src/pipeline_juridico/converter.py` (uma linha adicionando a chamada à função no pipeline de composição do documento). Nenhuma outra área (extrator, roteador, OCR, `recompose_native_paragraphs`, `remove_repetitive_margins`) é alterada.
- Testes: novos casos em `tests/` cobrindo os 3 exemplos reais do corpus (`&#8201;37`, `n.&#8201;11.343`, `na&#8201;realidade`), as variantes equivalentes (`&#x2009;`, `&#X2009;`, `&thinsp;`), e os casos negativos (não duplicar espaço quando já há espaço adjacente, não alterar outras entidades HTML, não introduzir espaço dentro de palavra além do exigido pela própria correção, preservar `[[Pág. N]]`, R01, SUBTÍTULO, índice do CC, rodapés técnicos já removidos, Papel/Nome).
- Corpus de regressão: reconversão `--no-ocr` dos 4 PDFs, com diff completo explicado e idempotência confirmada.
