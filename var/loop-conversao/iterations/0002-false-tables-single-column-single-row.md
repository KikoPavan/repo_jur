```yaml
iteration: 2
status: ACCEPTED
defect_id: tabelas-falsas-coluna-unica-ou-linha-unica
pdf: REsp_1704551-SP.pdf (principal); AINTARESP_1462304-PA.pdf (regressão)
pages: [1, 6]
baseline_result: >
  32 linhas de tabela Markdown fabricadas (`|`, `---`) para blocos
  rótulo/valor (já na ordem correta) e um fragmento de ementa, sem
  correspondência real de estrutura tabular no PDF original.
expected_result: >
  Conteúdo em texto corrido, na mesma ordem da referência PyMuPDF, sem
  sintaxe de tabela fabricada.
root_cause: >
  Mesma heurística de "formulário" do PdfConverter empacotado da biblioteca
  markitdown (iteração 1), aqui classificando como "tabela" um bloco de
  coluna única (demais colunas vazias em todas as linhas) ou uma única linha
  de cabeçalho sem nenhuma linha de dado.
changed_files:
  - src/pipeline_juridico/converter.py
new_tests:
  - tests/test_converter_integration.py::test_convert_document_replaces_fabricated_native_tables
commands_executed:
  - "uv run pytest tests/test_converter_integration.py::test_convert_document_replaces_fabricated_native_tables -q  (falhou antes da correção, confirmado por mim via git stash)"
  - "uv run pytest tests/ -q  -> 187 passed (verificado de forma independente)"
  - "UV_CACHE_DIR=/tmp/uv-cache-verify uv run --no-sync converter-juridico input/REsp_1704551-SP.pdf --overwrite --no-ocr"
  - "UV_CACHE_DIR=/tmp/uv-cache-verify uv run --no-sync converter-juridico input/AINTARESP_1462304-PA.pdf --overwrite --no-ocr"
  - "grep -c \"^|\" output/REsp_1704551-SP.md  -> 0 (era 32)"
  - "grep -c \"^|\" output/AINTARESP_1462304-PA.md  -> 0 (sem regressão da iteração 1)"
  - "grep -c \"^\\[\\[Pág\\.\" output/REsp_1704551-SP.md  -> 14, sequencial"
  - "md5sum output/Inf0024E.md  -> inalterado (OCR real não foi acionado)"
before_metrics:
  REsp_1704551-SP:
    tabelas_falsas_linhas_pipe: 32
    paginas: 14
  AINTARESP_1462304-PA:
    tabelas_falsas_linhas_pipe: 0
    paginas: 12
after_metrics:
  REsp_1704551-SP:
    tabelas_falsas_linhas_pipe: 0
    paginas: 14
  AINTARESP_1462304-PA:
    tabelas_falsas_linhas_pipe: 0
    paginas: 12
mandatory_blocks_triggered: []
regressions: []
decision_reason: >
  Defeito corrigido (0 tabelas falsas remanescentes no corpus conhecido).
  Nenhuma palavra perdida (multiconjuntos de tokens idênticos antes/depois,
  verificado pelo Codex e por checagem independente de números de processo,
  data e símbolos jurídicos). Nenhum bloqueio obrigatório disparado:
  marcadores sequenciais, sem caractere de substituição, sem regressão na
  correção da iteração 1. A detecção é estrutural e conservadora (exige
  tabela de coluna única disfarçada OU tabela sem nenhuma linha de dado, mais
  98% de sobreposição lexical com a referência), preservando qualquer tabela
  real com 2+ linhas de dado e 2+ colunas populadas — nenhuma tabela genuína
  é conhecida neste corpus, então este ponto fica como atenção para corpora
  futuros com tabelas reais. Suíte completa (187 testes) passa.
```

## Correção aplicada (Codex)

Em `src/pipeline_juridico/converter.py`:
- `_lexical_overlap`: extraída da lógica de sobreposição já usada na
  iteração 1, reutilizável.
- `_has_fabricated_table_structure`: percorre o conteúdo do motor nativo,
  agrupa linhas consecutivas iniciadas por `|` em regiões de tabela, valida
  que a segunda linha é um separador Markdown válido, e marca como
  fabricada quando (a) não há nenhuma linha de dado após cabeçalho+separador,
  ou (b) todas as linhas de dado têm somente a primeira coluna preenchida.
- `_has_fabricated_native_table`: combina o padrão estrutural acima com
  sobreposição lexical ≥98% em relação à referência PyMuPDF.
- `convert_document` agora substitui `content` pela referência quando
  QUALQUER UMA das duas condições (reordenação da iteração 1 OU tabela
  fabricada desta iteração) é detectada.

## Próximo candidato (iteração 3)

Nenhum novo defeito de prioridade 1-6 foi encontrado nas 3 amostras do
corpus após esta correção (perda de conteúdo, páginas vazias, números/datas/
símbolos, inversão de colunas, uso incorreto de OCR e tabelas falsas foram
verificados sem achados adicionais). Próxima verificação a fazer: prioridade
7 (fragmentação de palavras/linhas/parágrafos) e 9 (cabeçalhos/rodapés
repetitivos) em `Inf0024E.pdf` (29 páginas, maior amostra, ainda não
inspecionada em detalhe nesta rodada) — sem reconvertê-lo com OCR real.
