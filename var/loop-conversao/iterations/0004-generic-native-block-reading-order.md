```yaml
iteration: 4
status: ACCEPTED
defect_id: ordem-leitura-blocos-nativos-generico
pdf: AINTARESP_1462304-PA.pdf (principal, páginas 3, 7, 10 apontadas na validação anterior);
     REsp_1704551-SP.pdf e Inf0024E.pdf (regressão de corpus completo)
pages: [2, 3, 5, 6, 7, 8, 9, 10] (AINTARESP; ver seção de análise); Inf0024E [8, 25] (benignas)
baseline_result: >
  A correção da iteração 1 só substituía a ordem nativa (MarkItDown ->
  pdfplumber/pdfminer) pela referência quando a página continha um bloco de
  rótulo/valor em maiúsculas (heurística `_has_label_value_block`). Páginas
  de parágrafo corrido comum (3, 7, 10) não disparavam essa heurística e
  permaneciam com blocos/frases fora da ordem visual de leitura. A
  referência usada (`page.get_text("text")`) também seguia a ordem do
  content stream do PDF, não a ordem geométrica — o que já havia causado um
  cabeçalho deslocado para o rodapé em `Inf0024E.pdf` (não perseguido antes
  por não ser o defeito-alvo daquela iteração).
expected_result: >
  Página 3: "Requer, ao final, o provimento do especial com a atribuição do
  valor de" antes de "R$ 10.000,00 (dez mil reais) à causa.". Página 7: a
  sequência "ORIENTAÇÃO PACIFICADA NO STJ. DIVERGÊNCIA JURISPRUDENCIAL NÃO
  CARACTERIZADA" contígua, e "interpretação jurídica" não pode ser
  quebrada. Página 10: "Diante do exposto, DOU PARCIAL PROVIMENTO ao
  agravo" antes de "interno, apenas para afastar a Súmula 283 do STF.". O
  mesmo padrão de defeito não pode restar em nenhuma outra página do
  corpus fixo (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`,
  `Inf0024E.pdf`).
root_cause: >
  MarkItDown's PdfConverter (pdfplumber/pdfminer, terceiros) às vezes
  emite blocos de texto fora da ordem geométrica top-to-bottom/left-to-
  right, independentemente do conteúdo — não é um problema específico de
  formulários rótulo/valor. A salvaguarda anterior tratava apenas um
  subconjunto do sintoma (via um gate de conteúdo específico), não a causa.
fix: >
  Trocado o gate de conteúdo (`_has_label_value_block`, removido) por uma
  detecção puramente estrutural: sempre que uma página `texto_nativo` tiver
  a mesma composição lexical do PyMuPDF (>=98% de sobreposição, threshold
  já existente da iteração 1) mas ordem de tokens diferente, o conteúdo
  nativo é substituído. A referência usada deixou de ser
  `page.get_text("text")` (ordem do content stream, não confiável para
  ordem visual — provado com `Inf0024E.pdf`) e passou a ser uma extração
  geométrica própria: blocos de texto do PyMuPDF (`page.get_text("blocks")`)
  ordenados por `(y0 arredondado a 1 casa, x0)`. Nenhuma condição por nome
  de arquivo, número de página ou conteúdo jurídico foi introduzida — o
  gate vale para qualquer página `texto_nativo`.
changed_files:
  - src/pipeline_juridico/converter.py
new_tests:
  - tests/test_converter_integration.py::test_convert_aintaresp_page_3_preserves_paragraph_reading_order
  - tests/test_converter_integration.py::test_convert_aintaresp_page_7_preserves_contiguous_text
  - tests/test_converter_integration.py::test_convert_aintaresp_page_10_preserves_paragraph_reading_order
  - tests/test_converter_integration.py::test_convert_complete_aintaresp_preserves_native_reading_order
commands_executed:
  - "uv run pytest tests/test_converter_integration.py tests/test_converter.py tests/test_router.py -q  -> 38 passed (reportado pelo Codex)"
  - "uv run pytest tests/ -q  -> 193 passed (verificado de forma independente pelo orquestrador, não apenas relatado pelo Codex)"
  - "uv run converter-juridico input/AINTARESP_1462304-PA.pdf --overwrite --no-ocr"
  - "uv run converter-juridico input/REsp_1704551-SP.pdf --overwrite --no-ocr"
  - "uv run converter-juridico input/Inf0024E.pdf --overwrite --no-ocr --allow-partial"
  - "grep -c \"^\\[\\[Pág\\.\" output/*.md  -> 12, 14, 29 (sequenciais, inalterado)"
  - "grep -c \"�\" output/*.md  -> 0 nos três arquivos"
  - "Varredura própria (script ad-hoc) das 55 páginas texto_nativo do corpus, comparando tokens
    nativos pós-correção contra a ordem geométrica de referência (mesmo critério de
    _has_native_reading_order_defect): 0 páginas com defeito remanescente (overlap>=0.90 e ordem
    divergente)."
  - "Comparação token-a-token (via git stash do converter.py) entre saída ANTES e DEPOIS da
    correção para os 3 PDFs do corpus: REsp_1704551-SP.pdf e Inf0024E.pdf com multiset de tokens
    idêntico (nenhuma palavra alterada, apenas reordenação); AINTARESP_1462304-PA.pdf com uma
    única divergência de conteúdo, analisada abaixo."
mandatory_blocks_triggered: []
regressions: []
achado_numero_investigado: >
  A comparação antes/depois de AINTARESP_1462304-PA.pdf mostrou que o
  código de controle de rodapé "C542506155;NNNNNNNNNN@" mudou de
  "00029089584" (7 de 8 ocorrências, antes da correção) para "0029089584"
  (8 de 8 ocorrências, depois). Investigado com `page.get_text("dict")` no
  nível de span de caractere do PDF original: o span real embutido no PDF
  é "C542506155;0029089584@" (um único zero) em todas as 8 páginas onde o
  código aparece — confirmado diretamente, sem depender de nenhum dos dois
  motores de extração. Ou seja, o valor "00029089584" já era um artefato
  de duplicação de caractere do motor nativo (pdfplumber/pdfminer) em 7 das
  8 páginas antes desta correção; a correção da ordem de leitura, ao trocar
  o conteúdo nativo pela referência geométrica nessas páginas, removeu esse
  artefato como efeito colateral. Não é perda nem alteração de um número
  real do processo — é a eliminação de um dígito espúrio que nunca existiu
  no PDF original. Nenhuma outra divergência numérica, de data, valor
  monetário ou símbolo jurídico foi encontrada nos três arquivos do corpus.
decision_reason: >
  Os três casos obrigatórios (páginas 3, 7 e 10) foram verificados
  diretamente no markdown reconvertido, não apenas nos testes: as
  sequências exigidas aparecem na ordem correta e "interpretação jurídica"
  permanece contígua. Uma varredura de todas as 55 páginas texto_nativo do
  corpus fixo (12 + 14 + 29 páginas) confirmou zero páginas com o mesmo
  padrão de defeito remanescente — incluindo páginas adicionais de
  AINTARESP (2, 5, 6, 8, 9) que tinham o mesmo defeito de cabeçalho
  deslocado e não estavam na lista original, mas foram corrigidas pela
  generalização, conforme exigido pelo objetivo 2 do `/goal`. A suíte
  completa (193 testes, 189 anteriores + 4 novos) passa. A única alteração
  de conteúdo fora da reordenação pura foi a correção de um dígito
  duplicado espúrio, verificada contra o span de caractere real do PDF
  original (evidência de nível mais baixo possível, não apenas comparação
  entre saídas do pipeline). Nenhuma alteração em `router.py`, `engines.py`,
  `config.py`, OCR, detecção de tabelas ou dependências.
