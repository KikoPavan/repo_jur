```yaml
iteration: 3
status: ACCEPTED
defect_id: ocr-acionado-por-icones-decorativos-inserido-em-frase-nativa
pdf: Inf0024E.pdf
pages: [1]
baseline_result: >
  Página 1 roteada como `hibrido` (texto nativo abundante + soma de 3
  imagens pequenas/decorativas ultrapassando 15% de área); o motor de OCR
  interrompia a frase nativa "Ausência de inércia do [OCR] Ministério
  Público" com a transcrição de um ícone decorativo (selo ODS 16 da ONU) e
  colava rótulos ao valor seguinte sem quebra de linha.
expected_result: >
  Página 1 classificada como `texto_nativo`; nenhuma frase interrompida por
  OCR; rótulos e valores em linhas separadas; nenhum bloco `[Image OCR]`.
root_cause: >
  `route_page` promovia a `hibrido` qualquer página com texto nativo
  suficiente e QUALQUER sinal de imagem significativa, sem distinguir uma
  imagem de página inteira (forte indício de digitalização real) da soma de
  várias imagens pequenas/decorativas quando o texto nativo já é claramente
  suficiente.
changed_files:
  - src/pipeline_juridico/router.py
new_tests:
  - tests/test_router.py::test_route_page_abundant_multiblock_text_with_small_images_stays_native
  - tests/test_converter_integration.py::test_convert_inf0024e_first_page_uses_clean_native_output
commands_executed:
  - "uv run pytest tests/test_router.py::test_route_page_abundant_multiblock_text_with_small_images_stays_native tests/test_converter_integration.py::test_convert_inf0024e_first_page_uses_clean_native_output -q  (falharam antes da correção, confirmado por mim via git stash: sem a guarda, a página vai para 'erro' com --no-ocr por ser roteada hibrido)"
  - "uv run pytest tests/ -q  -> 189 passed (verificado de forma independente)"
  - "uv run pytest tests/test_router.py::test_route_page_hybrid tests/test_acceptance.py::test_9_3_mixed_pdf_records_each_page_method_correctly -q  -> 2 passed (fixtures genuínas de híbrido preservadas, verificado por mim)"
  - "UV_CACHE_DIR=/tmp/uv-cache-verify uv run --no-sync converter-juridico input/Inf0024E.pdf --overwrite --no-ocr --allow-partial"
  - "grep método página 1 -> texto_nativo (era hibrido)"
  - "grep '[Image OCR]' na página 1 -> 0 ocorrências"
  - "grep -c \"^\\[\\[Pág\\.\" output/Inf0024E.md -> 29, sequencial"
  - "grep processo/datas/símbolos jurídicos preservados"
before_metrics:
  Inf0024E:
    pagina_1_metodo: hibrido
    image_ocr_blocks_pagina_1: 3
    paginas: 29
after_metrics:
  Inf0024E:
    pagina_1_metodo: texto_nativo
    image_ocr_blocks_pagina_1: 0
    paginas: 29
mandatory_blocks_triggered: []
regressions: []
decision_reason: >
  Defeito corrigido: a página 1 de Inf0024E.pdf deixou de acionar OCR real
  para imagens puramente decorativas (logo, ícone ODS, capa sem texto
  legível) e a frase nativa não é mais interrompida por conteúdo de OCR.
  Regra implementada em router.py: quando char_count >= 10x o mínimo
  configurado (500 caracteres com os padrões atuais) E block_count >= 3
  (texto claramente substancial, não uma legenda isolada), a soma de
  imagens pequenas (sem nenhuma de página inteira) não promove a página a
  `hibrido`. Escopo respeitado à risca: config.py e converter.py
  permaneceram intocados, nenhuma dependência nova, nenhuma fixture
  genuína de híbrido (imagem de página inteira) foi alterada — verificado
  independentemente por mim, não apenas relatado pelo Codex. Páginas 2-29
  de Inf0024E.pdf permaneceram texto_nativo, sem alteração. Suíte completa
  (189 testes) passa.
```

## Correção aplicada (Codex)

Em `src/pipeline_juridico/router.py::route_page`: nova variável
`has_clearly_sufficient_native` (`char_count >= native_min_text_chars * 10`
e `block_count >= 3`, usando sinais já existentes de `NativeTextSignal`).
Quando essa condição é verdadeira E não há imagem de página inteira
(`not has_full_page_image`), a página permanece `texto_nativo` mesmo com
sinal de imagem significativa. O caminho de imagem de página inteira
(`hibrido` ou `ocr_integral`) não foi alterado.

## Próximo candidato (iteração 4)

Nenhum novo defeito de prioridade 1-5 identificado nas 3 amostras do
corpus. Restam para investigação futura: prioridade 7 (fragmentação de
palavras/parágrafos — ex.: espaçamento duplo entre palavras justificadas,
como "Ausência  de  inércia" com espaço duplo, presente em várias páginas
nativas; não é perda de conteúdo, mas pode afetar legibilidade/comparação)
e prioridade 9 (cabeçalhos/rodapés repetitivos, ex.: "Informativo de
Jurisprudência n. 24..." repetido em quase todas as páginas de
Inf0024E.pdf). Nenhum dos dois é um bloqueio obrigatório nem perda de
conteúdo — avaliar se vale a pena tratar nas próximas iterações ou encerrar
o loop aqui, já que os defeitos de maior prioridade (1-6) conhecidos no
corpus atual foram corrigidos.
