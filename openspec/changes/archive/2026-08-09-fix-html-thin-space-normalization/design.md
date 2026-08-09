## Context

`output/Inf0024E.md` contém 21 ocorrências do literal `&#8201;` (entidade HTML decimal do caractere THIN SPACE, U+2009), sempre colado diretamente entre um caractere e o próximo, sem espaço de separação real ao redor em pelo menos um dos lados — ex.: `apreensão de &#8201;37 gramas` (espaço antes, colado depois), `Lei n.&#8201;11.343/2006` (colado dos dois lados), `na&#8201;realidade` (colado dos dois lados), `regulamentar.&#8201;` seguido de um espaço já existente antes da próxima frase.

## Rastreamento da causa raiz (evidência empírica)

1. **Onde o literal aparece pela primeira vez no pipeline.** Extração bruta via PyMuPDF (`fitz.open("input/Inf0024E.pdf")`, `page.get_text()`) sobre a página 9 (0-based: página 8) mostra o literal `&#8201;` já presente no texto retornado pela biblioteca de extração — ANTES de qualquer código deste repositório processar a página. Isso isola a origem: não é MarkItDown, não é `recompose_native_paragraphs`, não é `remove_repetitive_margins` nem nenhuma outra função de `cleaner.py`/`converter.py` (nenhuma delas contém a substring `8201`, `thinsp`, `html.unescape` ou qualquer lógica de decodificação de entidades — confirmado por busca em todo `src/pipeline_juridico/`).

2. **Por que o literal está no PDF.** O caminho nativo do pipeline (`engines.py:create_native_engine` → `MarkItDown(enable_plugins=False)` → `PdfConverter.convert`, em `markitdown/converters/_pdf_converter.py`) usa `pdfplumber`/`pdfminer.six` para extrair o texto exatamente como ele está codificado nos content streams do PDF (via o CMap/ToUnicode de cada fonte incorporada). Nenhuma dessas bibliotecas decodifica entidades HTML — elas apenas convertem glifo → caractere Unicode conforme o mapeamento do PDF. O fato de a sequência de caracteres `&`, `#`, `8`, `2`, `0`, `1`, `;` aparecer como texto extraído significa que o próprio PDF foi gerado com esses sete caracteres como glifos individuais na página — não com o caractere único U+2009. A hipótese mais provável (não verificável sem a ferramenta de geração original) é que o documento de origem passou por uma etapa HTML → PDF em que a entidade `&#8201;` (destinada a virar um espaço fino tipográfico) não foi decodificada antes da renderização.

3. **Confirmação de que é um defeito de fonte, não do pipeline.** Rodando a mesma extração bruta (`page.get_text()`) sobre os outros 3 PDFs do corpus, nenhuma ocorrência de `&#8201;` aparece — o defeito está isolado ao arquivo-fonte `Inf0024E.pdf`, mas a função de correção não pode (e não deve) depender desse fato: a normalização deve operar sobre qualquer texto que contenha esse padrão, de qualquer PDF, futuro ou presente.

## Varredura de representações equivalentes

Verificação direta (`fitz`, extração bruta, os 4 PDFs do corpus) por:

| Representação | Ocorrências |
| --- | --- |
| `&#8201;` (decimal) | 21, somente em `Inf0024E.pdf` |
| `&#x2009;` / `&#X2009;` (hexadecimal) | 0 |
| `&thinsp;` (nomeada) | 0 |
| Caractere Unicode real U+2009 (THIN SPACE) | 0 |
| Caractere Unicode real U+00A0 (NBSP, para contraste) | 501, somente em `L10.406_CC_2002.pdf` — **fora de escopo**: é um caractere real (não um literal de entidade), semanticamente um espaço legítimo, já corretamente preservado como espaço pela extração |

Conclusão: no corpus atual, apenas a forma decimal `&#8201;` ocorre. A correção, no entanto, é definida para a classe de entidades equivalentes a THIN SPACE (decimal, hexadecimal, nomeada), já que essa é a evidência de diagnóstico disponível e generalizável sem introduzir uma regra específica de arquivo — não uma decodificação HTML genérica (que tocaria `&amp;`, `&lt;`, `&nbsp;` etc., fora do escopo autorizado por este defeito).

## Representação final escolhida

Um espaço ASCII regular (U+0020), e não o caractere Unicode real de espaço fino (U+2009).

Justificativa:
- Em todos os 21 casos reais, a função da entidade é exclusivamente separar palavras/tokens que, sem ela, ficam grudados (`na&#8201;realidade` → sem separação nenhuma seria ilegível como uma palavra só). Não há nenhuma evidência no corpus de que o espaçamento fino tenha significado tipográfico distinto que precise ser preservado — a função é puramente de separação lexical.
- O restante do pipeline já usa espaço ASCII regular como separador universal (inclusive nos pontos onde `recompose_native_paragraphs` normaliza espaços internos com `re.sub(r"\s+", " ", line)`); introduzir U+2009 criaria uma inconsistência de codificação sem benefício, e poderia ser normalizado de volta para espaço regular por qualquer ferramenta downstream que trate espaços Unicode de forma não uniforme.
- Preserva fidelidade textual (separação de palavras) sem introduzir um caractere nuançado que este pipeline não usa em nenhum outro lugar.

## Ponto de correção no pipeline

A substituição é aplicada como uma nova função em `src/pipeline_juridico/cleaner.py` (`normalize_thin_space_entities` ou nome equivalente), chamada em `converter.py` sobre o `raw_markdown` já composto (`compose_document`), no mesmo grupo de transformações textuais determinísticas já existentes (`remove_repetitive_margins`, `join_symbol_across_page_break`, `normalize_legal_symbols`). A ordem relativa a essas funções não é significativa — o padrão da entidade não interfere com paginação, símbolos jurídicos ou títulos legislativos — mas por clareza de leitura do pipeline ela é inserida como primeiro passo de normalização textual, antes de `remove_repetitive_margins`, já que é a forma mais "crua" de ruído de extração a ser removida.

Não é necessário tocar `recompose_native_paragraphs` (opera por página, antes da composição, e o padrão da entidade não é espaço em branco, então não afeta a lógica de junção geométrica de linhas) nem `clean_markdown` (que trata apenas CRLF, espaços à direita de linha e linhas em branco excessivas).

## Regra de substituição

Padrão: `[ \t]*&(?:#8201|#[xX]2009|thinsp);[ \t]*` → um único espaço `" "`.

- O `[ \t]*` em ambos os lados absorve qualquer espaço/tab horizontal já adjacente à entidade, evitando espaço duplicado quando ela já está parcialmente separada (ex. `de &#8201;37` → `de 37`, não `de  37`).
- Não inclui `\n` no conjunto de espaços absorvidos, preservando quebras de linha/parágrafo caso a entidade apareça perto de uma (não ocorre no corpus atual, mas evita interferir com a estrutura de parágrafos/páginas se ocorrer no futuro).
- `case_insensitive` apenas para a variante nomeada `thinsp`/`THINSP`/etc. e para o `x`/`X` do hexadecimal — não afeta `#8201` (só dígitos).
- Idempotente por construção: depois da primeira substituição, nenhuma entidade permanece no texto, então uma segunda execução não encontra mais nada para substituir.

## Fora de escopo (confirmado, não corrigido nesta mudança)

- Fusões em "SAIBA MAIS", primeira página colapsada do Inf0024E, "RECURSO / ESPECIAL", Papel/Nome — nenhum deles compartilha mecanismo com este defeito (nenhum é uma entidade HTML).
- Normalização HTML genérica (`&amp;`, `&lt;`, `&gt;`, `&nbsp;`) — sem evidência de defeito no corpus atual; tocar essas entidades exigiria decisão semântica própria por entidade, fora do escopo de "um defeito = uma mudança".
- O caractere Unicode real NBSP (U+00A0) em `L10.406_CC_2002.pdf` — não é uma entidade HTML literal, é um caractere de espaço real já funcionando corretamente.
