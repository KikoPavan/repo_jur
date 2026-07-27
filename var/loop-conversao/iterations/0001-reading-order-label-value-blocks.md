```yaml
iteration: 1
status: ACCEPTED
defect_id: ordem-leitura-blocos-rotulo-valor
pdf: AINTARESP_1462304-PA.pdf (principal); REsp_1704551-SP.pdf (regressão)
pages: [1, 4]
baseline_result: >
  Blocos de rótulo/valor ("RELATOR" / ": MINISTRO ...") e ementa
  centralizados eram reordenados pelo motor nativo (MarkItDown ->
  pdfplumber/pdfminer); na página 4 o mesmo conteúdo virava tabela Markdown
  falsa com "|" e "---".
expected_result: >
  Rótulo imediatamente seguido do seu valor, na mesma ordem da extração de
  referência via PyMuPDF (page.get_text("text")); nenhuma sintaxe de tabela
  fabricada para esse conteúdo.
root_cause: >
  Heurística de "formulário" do PdfConverter empacotado da biblioteca
  markitdown (pdfplumber/pdfminer, código de terceiros em site-packages),
  agravada pela arquitetura de isolar cada página em um PDF de página única
  antes da conversão nativa.
changed_files:
  - src/pipeline_juridico/converter.py
new_tests:
  - tests/test_converter_integration.py::test_convert_document_preserves_native_label_value_reading_order
commands_executed:
  - "uv run pytest tests/test_converter_integration.py::test_convert_document_preserves_native_label_value_reading_order -q  (falhou antes da correção, confirmado por mim via git stash da correção)"
  - "uv run pytest tests/test_converter.py tests/test_converter_integration.py tests/test_engines.py -q  -> 37 passed"
  - "uv run pytest tests/ -q  -> 186 passed (verificado de forma independente por mim, não apenas relatado pelo Codex)"
  - "UV_CACHE_DIR=/tmp/uv-cache-verify uv run --no-sync converter-juridico input/AINTARESP_1462304-PA.pdf --overwrite --no-ocr"
  - "UV_CACHE_DIR=/tmp/uv-cache-verify uv run --no-sync converter-juridico input/REsp_1704551-SP.pdf --overwrite --no-ocr"
  - "grep -n \"^|\" output/AINTARESP_1462304-PA.md  -> 0 linhas (era 19 na linha de base)"
  - "grep -c \"^\\[\\[Pág\\.\" output/*.md  -> 12 e 14, sequenciais e completos"
  - "grep processo/data/símbolos jurídicos preservados em ambos os arquivos"
before_metrics:
  AINTARESP_1462304-PA:
    tabelas_falsas_linhas_pipe: 19
    paginas: 12
  REsp_1704551-SP:
    tabelas_falsas_linhas_pipe: 32
    paginas: 14
after_metrics:
  AINTARESP_1462304-PA:
    tabelas_falsas_linhas_pipe: 0
    paginas: 12
  REsp_1704551-SP:
    tabelas_falsas_linhas_pipe: 32
    paginas: 14
mandatory_blocks_triggered: []
regressions: []
decision_reason: >
  Defeito corrigido (0 tabelas falsas remanescentes em AINTARESP; ordem de
  leitura do bloco rótulo/valor restaurada). Nenhum token do PDF original foi
  perdido (verificado por comparação lexical). Nenhum bloqueio obrigatório
  disparado: números de processo, datas e símbolos jurídicos preservados,
  marcadores de página sequenciais, sem caractere de substituição, sem
  duplicação. Suíte completa (186 testes) passa, incluindo o novo teste de
  regressão, que falha comprovadamente sem a correção. As 32 linhas de tabela
  falsa remanescentes em REsp_1704551-SP.pdf não são o mesmo defeito: nelas o
  rótulo e o valor já aparecem na ordem correta (mesma linha), apenas
  envoltos em sintaxe de tabela — não houve reordenação de tokens, então a
  salvaguarda (que exige `native_tokens != reference_tokens`) corretamente
  não interveio. Fica registrado como candidato à próxima iteração (defeito
  de prioridade 6, tabelas falsas, categoria distinta da corrigida aqui).
```

## Diagnóstico original

(ver histórico da sessão / diff acima do YAML)

## Correção aplicada (Codex)

Em `src/pipeline_juridico/converter.py`:
- `_reading_order_tokens`: tokeniza texto em palavras (`\w+`, casefold).
- `_has_label_value_block`: detecta, no texto de referência (PyMuPDF), pelo
  menos 2 pares consecutivos de linha "RÓTULO" (maiúsculas, ≤4 palavras)
  seguida de linha iniciando com `:`.
- `_has_native_reading_order_defect`: retorna verdadeiro quando o texto do
  motor nativo tem tokens não vazios, o texto de referência tem padrão de
  rótulo/valor, a ordem dos tokens diverge da referência, e ao menos 98% dos
  tokens coincidem lexicalmente (garante que é reordenação, não perda real
  de conteúdo).
- Em `convert_document`, para páginas `texto_nativo`, calcula
  `reference_content = page.get_text("text")` (mesmo objeto `fitz.Page` já
  aberto para roteamento) e substitui `content` pelo texto de referência
  quando o defeito é detectado. Método permanece `texto_nativo`. Nenhuma
  outra página é afetada.

## Próximo candidato (iteração 2)

Tabelas falsas em `REsp_1704551-SP.pdf` (linhas 6-29 e 215-234 de
`output/REsp_1704551-SP.md`) onde rótulo e valor já estão na ordem correta na
mesma linha, mas são envoltos em sintaxe de tabela Markdown (`|`, `---`) sem
necessidade — nenhuma inversão de tokens ocorre, portanto a salvaguarda desta
iteração não se aplica. Requer uma nova detecção específica para "tabela
Markdown fabricada sem conteúdo tabular real" (prioridade 6 do `/goal`).
