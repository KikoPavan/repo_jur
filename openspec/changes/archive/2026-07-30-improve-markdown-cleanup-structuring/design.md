## Context

Hoje `clean_markdown` (`src/pipeline_juridico/cleaner.py`) opera apenas sobre a string Markdown já composta (`compose_document` em `converter.py`), sem acesso a geometria de página. A única geometria hoje extraída é `_geometric_reading_order_text` em `converter.py`, usada exclusivamente como salvaguarda de ordem de leitura para páginas `texto_nativo` (substitui o conteúdo nativo quando ele diverge da ordem geométrica com alta sobreposição lexical). Essa mesma extração (`page.get_text("blocks")`, filtrando `block[6] == 0`) já fornece bounding boxes (`x0, y0, x1, y1`) por bloco de texto nativo, o que é a matéria-prima necessária para a recomposição de parágrafos.

O marcador de página `[[Pág. N]]` e o comentário de método já segmentam o documento composto em blocos por página de forma inequívoca, o que permite implementar detecção de cabeçalho/rodapé repetitivo e separação de índice como um passo pós-composição, sem precisar re-abrir o PDF.

## Goals / Non-Goals

**Goals:**
- Recompor parágrafos fragmentados em páginas `texto_nativo` usando geometria de bloco já disponível no PyMuPDF, com lista de exceção que impede junção indevida.
- Remover cabeçalhos/rodapés técnicos repetitivos (data/hora, nome de arquivo, URL, contador de página) detectados por repetição entre páginas + posição (primeira/última linha do bloco de página).
- Normalizar contextualmente símbolos jurídicos corrompidos pela extração, com regex restritas a padrões seguros.
- Reconhecer hierarquia legislativa (PARTE→SUBSEÇÃO) e fundir o marcador com o título imediatamente seguinte em um único cabeçalho Markdown.
- Separar o índice final sob `# ÍNDICE`, preservando conteúdo integralmente.
- Zero LLM em runtime; tudo determinístico e testável unitariamente.

**Non-Goals:**
- Não alterar roteamento de página, engines de OCR/nativo, ou a salvaguarda de ordem de leitura existente (`_has_native_reading_order_defect`).
- Não aplicar recomposição geométrica de parágrafos a páginas `ocr_integral`/`hibrido` nesta mudança (o texto de OCR não carrega geometria de bloco do PDF original de forma equivalente); ficam apenas sujeitas às etapas 2–5 (cabeçalho/rodapé, símbolos, estrutura, índice), que operam sobre o Markdown composto.
- Não introduzir novas dependências.
- Não resolver casos em que um título estrutural (ex. "LIVRO I") termina uma página e seu título (ex. "DAS PESSOAS") começa a próxima — junção só ocorre dentro do mesmo bloco de página, por respeito ao bloqueio "não unir quando a próxima linha iniciar marcador de página". Caso real detectado no corpus deve ser documentado como caso para revisão humana, não contornado com regra específica de arquivo/página.

## Decisions

1. **Onde a recomposição geométrica de parágrafos acontece**: em `converter.py`, imediatamente após `content = result.text_content or ""` para páginas `texto_nativo`, chamando uma nova função (ex. `cleaner.recompose_native_paragraphs(content, page)` ou módulo novo `structure.py`) que recebe o `fitz.Page` já aberto (mesmo objeto usado por `_geometric_reading_order_text`) e o texto nativo do MarkItDown, e devolve o texto com parágrafos unidos. Isso mantém a geometria disponível exatamente onde já é usada hoje, sem reabrir páginas nem mudar a arquitetura de isolamento por página.
   - Alternativa descartada: fazer a junção só por heurística textual (sem geometria) no `cleaner.py` pós-composição — mais simples, mas não atende ao requisito explícito de usar "dados geométricos do PDF, distância vertical, alinhamento" e teria mais falsos positivos/negativos em colunas ou blocos tabulares.
2. **Regra de junção de blocos geométricos**: unir bloco atual ao próximo quando (a) o espaçamento vertical entre o fim de um bloco e o início do próximo for menor ou igual a um limiar relativo à altura de linha típica da página (evita magic number fixo entre documentos com fontes diferentes), (b) o próximo bloco não casar com nenhuma regex de exceção (Art./§/inciso/alínea/item, PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO, marcador de página, ou início de novo bloco estrutural), e (c) a linha atual não terminar em pontuação de fechamento de frase seguida de heurística de nova sentença isolada (para não grudar frases que coincidentemente estão próximas mas são unidades distintas — critério conservador: só une quando o bloco atual não termina em `.`/`:`/`;` seguido de bloco que começa com maiúscula E marcador de lista, ou quando a continuidade lexical indicar claramente a mesma frase, ex. bloco atual termina sem pontuação terminal).
   - Alternativa descartada: usar apenas distância vertical sem checar pontuação — geraria junções indevidas entre itens de lista com espaçamento uniforme.
3. **Cabeçalho/rodapé repetitivo — proxy de posição sem re-abrir o PDF**: em vez de re-extrair bbox após a composição, usar a primeira e a última linha não vazia de cada bloco de página (delimitado por `[[Pág. N]]`) como proxy de "posição geométrica semelhante" (topo/rodapé da página). Uma linha candidata só é removida se (a) aparecer, em forma idêntica ou com apenas o número de página variando, em uma fração alta das páginas (limiar configurável, ex. ≥ 60% das páginas com conteúdo) E (b) casar com um padrão explícito da lista permitida (data/hora, nome de arquivo técnico, URL, contador `N/186`). Nunca remove por repetição isolada.
   - Alternativa descartada: reabrir o PDF por página para comparar bbox exato do rodapé — mais fiel geometricamente, mas exige threading de estado extra por todo o pipeline e maior custo de manutenção; o proxy textual+posicional é suficiente para os padrões-alvo (todos são strings altamente regulares).
4. **Normalização de símbolos**: função dedicada com lista fechada de regex (`Art\.\s*(\d+)\s*o\b` → `Art. \1º`, equivalentes para `§` e `Lei n`), aplicada sobre o Markdown composto, após a recomposição de parágrafos e antes da limpeza final de espaços/linhas. Nenhuma substituição de `o` isolado fora desses contextos.
5. **Estrutura legislativa**: regex de âncora (`^(PARTE|LIVRO|TÍTULO|CAPÍTULO|SEÇÃO|SUBSEÇÃO)\b.*$`) seguida de checagem da próxima linha não vazia dentro do mesmo bloco de página: se for uma linha curta, majoritariamente maiúscula, e não for ela mesma uma âncora estrutural/Art./marcador de página, funde as duas em um único cabeçalho Markdown no nível correspondente (`#` PARTE … `######` SUBSEÇÃO). Título comum em maiúsculas sem âncora antecedente não vira cabeçalho.
6. **Índice final**: varrer o documento composto de trás para frente por blocos de página; identificar o início do índice pela primeira página (a partir do fim) cujo conteúdo deixa de conter marcadores de artigo/estrutura normativa e passa a ser dominado por padrões de índice (linhas curtas terminando em número, "..........", ou títulos repetidos sem corpo de artigo). Inserir `# ÍNDICE` imediatamente antes do primeiro bloco de página classificado como índice; não remove nem reordena conteúdo.
7. **Ordem de execução em `clean_markdown`/pipeline**: (1) recomposição geométrica por página [em `converter.py`, antes da composição] → (2) composição (inalterada) → (3) remoção de cabeçalho/rodapé repetitivo → (4) normalização de símbolos → (5) estrutura legislativa → (6) separação de índice → (7) limpeza final existente (CRLF→LF, trailing spaces, linhas vazias). Cada etapa é uma função pura testável isoladamente.

## Risks / Trade-offs

- [Falsos positivos na junção de parágrafos podem grudar frases distintas] → limiar conservador + lista de exceção ampla + suíte de regressão com reconversão do corpus completo a cada iteração; qualquer regressão bloqueia a iteração.
- [Proxy textual de cabeçalho/rodapé pode não generalizar a formatos de rodapé fora do corpus] → escopo explicitamente limitado aos 4 padrões citados no objetivo; qualquer outro candidato vai para "casos para revisão humana" no relatório final, não para regra ad-hoc.
- [Detecção de índice por heurística pode ter falso negativo em documentos sem índice ou com formato atípico] → etapa é aditiva (insere cabeçalho, nunca remove texto); ausência de índice detectado não quebra nada, só não insere `# ÍNDICE`.
- [Threading de `fitz.Page` para dentro da recomposição de parágrafos aumenta acoplamento entre `converter.py` e a nova lógica de limpeza] → mitigado mantendo a função de recomposição pura (recebe blocos/geometria já extraídos, não o objeto `Page` inteiro) sempre que possível, e testável sem abrir PDFs reais (usando tuplas de bbox sintéticas nos testes unitários).

## Migration Plan

Sem migração de dados — mudança é puramente de código determinístico. Ativação imediata após merge; reconversão do corpus de regressão (`input/*.pdf`) a cada subtarefa concluída, comparando saída anterior/posterior antes de aceitar. Rollback trivial via reversão do commit local (sem publicação/push envolvida).

## Open Questions

- Título estrutural dividido entre o fim de uma página e o início da próxima (ex. "LIVRO I" / "DAS PESSOAS" em páginas adjacentes): registrar como caso conhecido para revisão humana no relatório final, sem regra por página/arquivo.
- Se o corpus de regressão revelar um quinto padrão de cabeçalho/rodapé não previsto no objetivo, decidir caso a caso durante a iteração 2 se ele é seguro o bastante para entrar na lista fechada ou deve ir para revisão humana.
