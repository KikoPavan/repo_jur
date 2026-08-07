## Why

Em `output/L10.406_CC_2002.md`, o índice final contém três cabeçalhos Markdown de nível 1 irmãos entre si: `# ÍNDICE`, `# PARTE GERAL` e `# PARTE ESPECIAL` (linhas 9172, 9174 e 9271). Causa raiz confirmada por extração bruta (`page.get_text()` da página 177 do PDF de origem): os rótulos "PARTE GERAL"/"PARTE ESPECIAL" chegam ao pipeline com espaçamento entre letras (`P A R T E   G E R A L`) tanto no corpo — onde legitimamente formam os dois cabeçalhos `#` que dividem o Código Civil — quanto, de forma idêntica, nas duas entradas de mesmo nome dentro do índice. `build_legislative_headings` (`src/pipeline_juridico/cleaner.py`) reconhece esse texto espaçado e o converte em cabeçalho usando a mesma tabela de níveis fixa (`heading_levels`) em todo o documento, sem qualquer noção de "dentro do índice" vs. "corpo". As demais entradas do índice (LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, Seção) não chegam letter-spaced no PDF de origem e por isso não acionam nenhuma das heurísticas de `build_legislative_headings`, permanecendo texto comum — só PARTE GERAL/PARTE ESPECIAL são afetadas. `mark_final_index`, que roda depois e é o único ponto do pipeline que sabe onde o índice começa, apenas insere/promove `# ÍNDICE` e nunca reexamina os cabeçalhos já gerados dentro da região do índice. Resultado: o índice compete estruturalmente com sua própria raiz.

O problema é somente de nível Markdown (nenhum outro mecanismo — extrator, roteamento, OCR, recomposição geométrica — está envolvido); os marcadores estruturais em si já são identificados corretamente, apenas o nível atribuído dentro do índice está errado.

## What Changes

- `mark_final_index` (`src/pipeline_juridico/cleaner.py`) passa, após localizar/inserir `# ÍNDICE`, a demover em exatamente um nível (adicionar um `#`, respeitando o teto de `######`) qualquer cabeçalho Markdown que `build_legislative_headings` já tenha produzido dentro da região do índice (hoje, na prática, `# PARTE GERAL` → `## PARTE GERAL` e `# PARTE ESPECIAL` → `## PARTE ESPECIAL`).
- A decisão é baseada exclusivamente na posição estrutural ("este cabeçalho está depois de `# ÍNDICE`"), não no texto "PARTE GERAL" — generaliza para qualquer marcador que eventualmente vire cabeçalho dentro de um índice em outro documento, preservando a ordem relativa PARTE < LIVRO < TÍTULO < SUBTÍTULO/CAPÍTULO < SEÇÃO já usada no corpo.
- Não altera `build_legislative_headings`, `recompose_native_paragraphs`, o extrator, o roteamento, o OCR ou a arquitetura geral.
- Não cria cabeçalhos novos para entradas do índice que hoje permanecem texto comum (LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, Seção) — apenas ajusta o nível dos cabeçalhos que já existem dentro do índice.

## Capabilities

### New Capabilities
(nenhuma — correção pontual da capacidade existente)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Separação do índice final" passa a exigir que qualquer cabeçalho Markdown já presente dentro do índice fique subordinado (nível estritamente maior) a `# ÍNDICE`, sem alterar cabeçalhos do corpo antes do índice.

## Impact

- Código: `src/pipeline_juridico/cleaner.py`, apenas dentro de `mark_final_index`, sem tocar em `inspector.py`, `router.py`, `engines.py`, `converter.py` ou dependências.
- Testes: novos testes de regressão em `tests/test_cleaner.py` cobrindo o caso positivo (PARTE GERAL/PARTE ESPECIAL demovidos para `##` dentro do índice) e os negativos obrigatórios (cabeçalhos do corpo antes do índice inalterados, os 8 `#### SUBTÍTULO` do corpo intactos, marcadores `[[Pág. N]]` inalterados, texto/tokens do índice inalterados, documentos sem índice detectável inalterados, jurisprudência não afetada).
- Corpus: reconversão dos 4 PDFs fixos com `converter-juridico --no-ocr` para confirmar a correção em `L10.406_CC_2002.md` e ausência de qualquer alteração indevida nos demais 3 arquivos.
- Fora de escopo: regra específica ao texto "PARTE GERAL"/"PARTE ESPECIAL"; qualquer alteração à hierarquia do corpo; reabertura de mudanças arquivadas; OCR real; arquivamento sem aprovação humana explícita.
