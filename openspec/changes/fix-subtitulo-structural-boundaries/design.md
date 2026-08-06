## Contexto

`src/pipeline_juridico/cleaner.py` reconhece a hierarquia legislativa formal PARTE, LIVRO, TÍTULO, CAPÍTULO, SEÇÃO e SUBSEÇÃO em cinco pontos:

1. `_LEGISLATIVE_MARKER_PATTERN` (módulo) — usado por `build_legislative_headings` para identificar um parágrafo que é *apenas* um marcador bare (ex. "TÍTULO I").
2. `formal_structure_pattern`, `bare_structure_pattern`, `qualified_structure_pattern` (dentro de `recompose_native_paragraphs`) — usados em `should_join` para impedir que um marcador estrutural seja geometricamente unido ao bloco anterior ou seguinte.
3. `heading_levels` (dentro de `build_legislative_headings`) — mapeia cada palavra-chave a um nível de cabeçalho Markdown fixo (`parte`→1 ... `subseção`→6).
4. `structural_pattern` (dentro de `mark_final_index`) — conta densidade de marcadores estruturais após o último artigo para detectar o índice final.

`SUBTÍTULO`/`SUBTITULO` nunca foi incluído em nenhum desses cinco pontos, apesar de fazer parte da hierarquia real do Código Civil (Livro IV — Do Direito de Família, e Livro II — Do Direito de Empresa, Título II — Da Sociedade). Verificado em `output/L10.406_CC_2002.md`: as 8 ocorrências relatadas seguem o mesmo padrão — a linha física `SUBTÍTULO N` aparece logo após o fim de um artigo, parágrafo, inciso ou cabeçalho `TÍTULO` já formado, e como nenhuma exceção de não-junção em `should_join` reconhece `SUBTÍTULO`, ela é tratada como continuação de prosa comum e fundida ao parágrafo anterior antes mesmo de `build_legislative_headings` rodar.

O nível Markdown correto foi determinado inspecionando o corpus real: em todas as 8 ocorrências, o `CAPÍTULO` que segue imediatamente o `SUBTÍTULO` permanece em `####` (nível 4) tanto quando é filho direto de `TÍTULO` quanto quando é filho de `SUBTÍTULO` (ex. linha 3801 `#### CAPÍTULO I — Da Sociedade em Comum`, logo após `SUBTÍTULO I` na linha 3797). Como o esquema de `heading_levels` é plano (um nível fixo por palavra-chave, não recursivo pela árvore real do documento) e não deve ser alterado para os demais marcadores, a única atribuição consistente é `subtítulo`/`subtitulo` → nível 4, o mesmo de `capítulo`.

## Decisão

Adicionar `SUBTÍTULO`/`SUBTITULO` aos quatro primeiros pontos (`_LEGISLATIVE_MARKER_PATTERN`, `formal_structure_pattern`, `bare_structure_pattern`, `qualified_structure_pattern`, `heading_levels`), replicando exatamente o padrão já usado para os seis marcadores existentes (mesma alternativa regex, mesmo tratamento de acento/sem-acento). Isso:

- impede a junção geométrica indevida de `SUBTÍTULO N` ao bloco anterior em `recompose_native_paragraphs`;
- permite que `build_legislative_headings` combine `SUBTÍTULO N` com a denominação seguinte em um único cabeçalho `#### SUBTÍTULO N — Denominação`;
- não requer nenhuma regra específica a artigo, parágrafo, inciso ou ao Código Civil — a correção opera inteiramente no nível do marcador estrutural, igual às demais palavras-chave.

`mark_final_index`/`structural_pattern` (ponto 5) **não** será alterado: a detecção do índice final já funciona corretamente sem reconhecer `SUBTÍTULO` (há sempre `TÍTULO`/`CAPÍTULO`/`SEÇÃO` suficientes ao redor para ultrapassar o limiar de densidade de 3), e as entradas do índice final para `SUBTÍTULO` (ex. "SUBTÍTULO I DA SOCIEDADE NÃO PERSONIFICADA") já estão em uma única linha (marcador + denominação já combinados pelo extrator), formato que não é afetado pelas mudanças em `recompose_native_paragraphs`/`build_legislative_headings` (essas funções só combinam marcador+título quando eles aparecem como *parágrafos separados*). Tocar em `structural_pattern` sem necessidade ampliaria o escopo além do mínimo generalizável.

## Alternativas consideradas

- **Nível Markdown 4 exclusivo para SUBTÍTULO e renumerar CAPÍTULO→5, SEÇÃO→6, SUBSEÇÃO→7**: rejeitada — nível 7 não existe em Markdown (máximo `######`), e renumerar CAPÍTULO/SEÇÃO/SUBSEÇÃO globalmente contradiria a regra de não alterar hierarquias já corretas nos demais arquivos do corpus, além de não corresponder ao comportamento observado (CAPÍTULO já permanece em `####` mesmo sob SUBTÍTULO).
- **Criar uma exceção específica para os 8 casos relatados (ex. buscar literalmente "SUBTÍTULO I", "SUBTÍTULO II" etc.)**: rejeitada — viola explicitamente a regra de não criar regras específicas a números de artigo ou ao Código Civil, e não generaliza para outros documentos com `SUBTÍTULO`.
- **Reconhecer SUBTÍTULO apenas em `build_legislative_headings` sem tocar em `recompose_native_paragraphs`**: rejeitada — nos 8 casos reais, o defeito ocorre na etapa de recomposição geométrica (o marcador já está fundido ao parágrafo anterior antes de `build_legislative_headings` rodar); sem a correção em `should_join`, `SUBTÍTULO` nunca chegaria como parágrafo próprio para ser combinado.

## Riscos

- Falso positivo: um documento que use "subtítulo" como palavra comum em prosa (ex. "o subtítulo do capítulo trata de...") poderia ser afetado. Mitigado pelo mesmo mecanismo já usado para as outras 6 palavras-chave: a exceção só age quando a linha é integralmente maiúscula E corresponde ao padrão de marcador bare/qualificado — texto comum minúsculo ou misto nunca aciona `formal_structure_pattern` combinado com `_is_uppercase_led`.
- Colisão com o índice final: mitigada — entradas do índice já vêm em uma única linha "SUBTÍTULO N DENOMINAÇÃO" (sem separador), que não corresponde ao padrão bare (`_LEGISLATIVE_MARKER_PATTERN` exige que a linha seja *apenas* o marcador) e portanto nunca é reescrita como cabeçalho.
