## Why

Em páginas de capa/sessão de `AINTARESP_1462304-PA.pdf` (p.11) e `REsp_1704551-SP.pdf` (p.3, p.14), listas estruturadas do tipo "Papel\nNome" (ex. `RELATOR`/`MINISTRO...`, `AGRAVANTE`/`NORTE ENERGIA S.A.`, `ADVOGADOS`/`PRISCILA...`) são fundidas indevidamente em um único parágrafo corrido pelo mecanismo geométrico de junção **entre blocos** de `recompose_native_paragraphs` (`gap <= previous_height * 1.2`), mesmo sem nenhuma linha iniciada por `:`. Esse defeito ficou visível após `fix-colon-label-pagewide-recomposition-bypass`, quando essas páginas deixaram de ser inteiramente bypassadas.

**Diagnóstico concluído, implementação BLOQUEADA**: dois critérios geométricos candidatos foram desenhados e validados empiricamente contra o corpus real (não apenas testes sintéticos), e **ambos foram descartados** por causarem regressões reais em recomposições legítimas já validadas. Nenhum critério seguro foi encontrado até o momento — conforme a diretriz explícita da tarefa ("Se não encontrar um critério que separe com segurança Papel/Nome dos casos R01, PARE e informe. Não implemente heurística ampla."), esta mudança permanece em diagnóstico, sem implementação, aguardando decisão humana sobre como prosseguir.

## Causa raiz

`recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) monta uma lista única e achatada de linhas físicas a partir de TODOS os blocos geométricos da página (`page.get_text("blocks")`), e decide unir cada par consecutivo de linhas com base, entre outras condições, em `gap <= previous_height * 1.2` — um limiar de distância vertical calibrado para reconhecer quando duas linhas físicas em blocos PyMuPDF **diferentes** são, na verdade, a mesma frase mecanicamente dividida pelo extrator (um comportamento real e necessário: ver `Art. 288`, `Art. 1.079`, `Art. 1.271`, `Parágrafo único` do Código Civil, todos frases genuinamente partidas entre dois blocos). Esse mesmo limiar, porém, não distingue essa situação de duas entradas **semanticamente distintas** (um rótulo de papel e o nome seguinte, ou dois papéis/nomes consecutivos) que apenas *também* satisfazem o limiar de proximidade vertical — daí a fusão indevida.

## Critérios investigados e descartados

### Candidato 1 — restringir junção ao mesmo bloco de origem

Impedir qualquer junção entre linhas de blocos PyMuPDF diferentes (permitir apenas junção dentro do mesmo bloco).

- **Resultado nos 4 casos R01 nomeados na tarefa** (Art. 44 §2º, Art. 593, Art. 1.458, Art. 1.368-F): sobrevivem intactos — inspeção geométrica real (`page.get_text("blocks")`) mostrou que, ao contrário do que os testes unitários sintéticos sugerem (que os modelam como 2 blocos separados), esses 4 casos reais estão de fato **dentro de um único bloco PyMuPDF** (múltiplas linhas físicas no mesmo bloco), então não dependem de junção entre blocos.
- **Por que foi descartado**: reconversão do corpus real revelou que esse critério quebra **outras** recomposições legítimas do Código Civil que genuinamente precisam de junção entre blocos diferentes — `Art. 1.544`, `Art. 1.619`, `Art. 1.734`, `Parágrafo único` (antes do `Art. 1.758`), entre outras — não cobertas pelos 4 casos nomeados, mas igualmente reais e previamente corretas. Ou seja: os 4 R01 "sobrevivem" por acidente de geometria, mas o critério continua inseguro para o restante do corpus.

### Candidato 2 — exigir recuo negativo (dedent) do x0 em relação à abertura do parágrafo

Coordenada x0 (esquerda) por linha física, hoje descartada pelo pipeline (`_sorted_native_text_blocks` só propaga y0/y1/texto), extraída via `page.get_text("dict")`. Critério: uma junção **entre blocos diferentes** só é permitida quando a linha atual tiver x0 estritamente menor que o x0 da primeira linha do parágrafo em acumulação (o padrão clássico "recuo na primeira linha, recuo suprimido na continuação", confirmado no corpus real: `Art. 288`, `Art. 1.079`, `Art. 1.271`, `Parágrafo único` sempre 54.5→36.5).

- **Resultado nos casos `Papel/Nome`**: corrige corretamente — nesses blocos o x0 é idêntico em todas as linhas (36.0→36.0 no AINTARESP; 104.2→104.2→104.2→104.2 no REsp), sem nenhum recuo, então a condição bloqueia a fusão como esperado.
- **Resultado nos 4 R01 e nas demais continuações reais do Código Civil** (`Art. 1.544`, `Art. 1.734`, `Parágrafo único`): todas corretamente preservadas com esse critério mais refinado (ao contrário do Candidato 1).
- **Por que foi descartado mesmo assim**: reconversão completa do corpus revelou 3 categorias de regressão nova, fora do escopo dos R01 nomeados:
  1. **Títulos legislativos centralizados que quebram em 2 blocos**: `TÍTULO IV — Da Tutela, da Curatela e da Tomada de Decisão Apoiada` + `(Redação dada pela Lei nº 13.146, de 2015)` (p.152) — texto centralizado, onde x0 varia com a largura de cada linha (187.1→210.7, x0 *aumenta*, não decresce), não segue a convenção de recuo-na-primeira-linha usada pelo corpo de artigos.
  2. **Layout de página de rosto em colunas**: "Presidência da República" / "Casa Civil Subchefia..." e "Lei de Introdução às normas do Direito Brasileiro" / "Institui o Código Civil." (p.1) — pares de texto na MESMA linha vertical (y sobreposto), não uma continuação vertical real; o critério às vezes "corrige" essas fusões espúrias (efeito colateral, não o objetivo desta mudança) e às vezes as preserva, de forma inconsistente com o resultado esperado.
  3. **Interação com a normalização de símbolo entre páginas**: `Art. 2.029` → `Art. 2.030` (fronteira das páginas 175/176) — o bloqueio de uma junção específica alterou a estrutura de parágrafos o suficiente para que `join_symbol_across_page_break` deixasse de reconhecer o padrão `"Lei n" + quebra de página + "o "` que normalmente normaliza para `"Lei nº"`, resultando em `"Lei n"` (sem `º`) e um `"o"` solto no início da página seguinte.

## Estado desta mudança

Diagnóstico (ETAPA 1) concluído e documentado em `design.md`. TDD (ETAPA 2) e implementação (ETAPA 3) **não iniciados**, conforme a regra explícita da tarefa de não implementar heurística ampla sem um critério seguro demonstrado. Nenhum código foi alterado — todos os experimentos foram feitos em arquivos temporários e revertidos; `git status` permanece limpo (além do MP3 pré-existente fora de escopo).

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
(nenhuma — nenhuma implementação foi feita nesta mudança)

## Impact

- Nenhum código de `src/` foi alterado.
- Achado permanece registrado em `LOOPS.md`, agora com os dois critérios investigados e descartados documentados, para que uma tentativa futura não repita a mesma investigação.
