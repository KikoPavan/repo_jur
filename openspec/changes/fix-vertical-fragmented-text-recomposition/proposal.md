## Why

Em `AINTARESP_1462304-PA.md` (ementa da p.7: "PROVEITO / ECONÔMICO / DA / DEMANDA. ORIENTAÇÃO / PACIFICADA / NO / STJ. DIVERGÊNCIA / JURISPRUDENCIAL / NÃO / CARACTERIZADA...") e em `Inf0024E.md` (campo temático da p.4: "DIREITO / PROCESSUAL / PENAL, DIREITO / DA / PESSOA / COM / DEFICIÊNCIA") sequências de linhas que pertencem à mesma expressão/bloco textual são publicadas fragmentadas verticalmente, uma palavra ou fragmento por linha, em vez de recompostas em texto corrido.

Causa raiz: em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), a condição de junção usa `not native_label_pattern.match(previous_text)` para proteger rótulos de campo reais (`PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `DESTAQUE`, `ACÓRDÃO`, `RELATÓRIO`, `VOTO`, etc.) de serem fundidos ao valor que os segue. O regex `native_label_pattern` casa qualquer linha só de maiúsculas/espaços, sem verificar a posição dessa linha dentro do bloco geométrico de origem (`page.get_text("blocks")` do PyMuPDF). Inspeção da geometria real do corpus mostra que em toda ocorrência legítima de rótulo a linha-rótulo é a primeira linha física do seu bloco (`idx==0`); em toda ocorrência do defeito, a palavra que bloqueia a junção está no meio de um bloco já em fluxo (`idx>0`) — é continuação de um valor já iniciado, não um novo rótulo. A regra atual não distingue os dois casos porque avalia apenas a forma textual da linha (maiúsculas, sem pontuação), não sua posição estrutural no bloco.

Um segundo mecanismo (early-return de página inteira quando qualquer linha do bloco começa com `:`) também produz fragmentação vertical indevida em outras páginas do corpus (`AINTARESP_1462304-PA.pdf` p.1, 4, 11; `REsp_1704551-SP.pdf` p.1, 3, 4, 6, 7, 14), mas tem causa técnica distinta (desativação total da recomposição da página vs. decisão de junção incorreta) e está fora do escopo desta mudança — ver nota em `LOOPS.md`.

## What Changes

- Em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), propagar, junto com cada linha física reconstruída a partir dos blocos geométricos, um marcador estrutural indicando se ela é a primeira linha física do seu bloco de origem.
- Restringir a proteção de `native_label_pattern` para bloquear a junção apenas quando `previous_text` for a primeira linha física do seu bloco de origem. Linhas em maiúsculas que ocorrem no meio de um bloco já em fluxo deixam de ser tratadas como rótulo e passam a poder se juntar à linha seguinte, sujeitas às demais condições geométricas e estruturais já existentes (gap vertical, marcadores de dispositivo/estrutura formal, fechamento jurisprudencial etc.).
- Não alterar nenhuma outra condição de `recompose_native_paragraphs` (early-return de tabelas `|`, early-return de linhas iniciadas por `:`, `current_line_pattern`, `formal_structure_pattern`, `bare_structure_pattern`, `qualified_structure_pattern`, proteção de fechamento jurisprudencial, cálculo de `gap`/`line_height`, verificação de overlap de tokens).
- Não alterar extrator, OCR, roteamento, dependências, remoção de margens ou arquitetura geral do pipeline.

## Capabilities

### New Capabilities
(nenhuma — correção pontual da capacidade existente)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Recomposição geométrica de parágrafos" passa a exigir que a proteção contra fusão de rótulos de campo (linhas inteiramente em maiúsculas sem pontuação) considere a posição estrutural da linha dentro do bloco geométrico de origem — só bloqueia a junção quando a linha for a primeira do bloco — em vez de bloquear qualquer linha que apenas pareça um rótulo pela forma textual.

## Impact

- Código: `src/pipeline_juridico/cleaner.py`, exclusivamente dentro de `recompose_native_paragraphs`. Nenhum outro módulo (`inspector.py`, `router.py`, `engines.py`, `converter.py`) é tocado.
- Testes: novos testes de regressão em `tests/test_cleaner.py` cobrindo os dois formatos reais citados (AINTARESP p.7, Inf0024E p.4), as ocorrências equivalentes encontradas no corpus (AINTARESP p.9, REsp p.12) e os casos negativos: rótulos de campo reais (`PROCESSO`, `RAMO DO DIREITO`, `TEMA`, `DESTAQUE`) permanecendo separados do valor; títulos/cabeçalhos estruturais legítimos; listas/incisos/enumerações; precedentes distintos; parágrafos realmente separados; cabeçalhos/rodapés repetitivos já corrigidos; os 8 casos de `SUBTÍTULO` do Código Civil; os casos R01 e as separações jurisprudenciais já protegidas.
- Corpus: reconversão dos 4 PDFs fixos com `converter-juridico --no-ocr` para confirmar a correção dos casos reais, ausência de fusão indevida e ausência de regressão nos demais arquivos.
- Fora de escopo: o guard de linhas iniciadas por `:` (registrado como achado pendente em `LOOPS.md` para mudança futura); qualquer regra específica a palavra, tribunal, processo, página ou arquivo; reabertura de mudanças arquivadas; OCR real; arquivamento sem aprovação humana explícita.
