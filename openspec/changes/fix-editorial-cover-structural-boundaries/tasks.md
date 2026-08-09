> Histórico: esta mudança começou como diagnóstico puro (Seção 0). Após comparação empírica de 3 alternativas e decisão humana explícita, foi aprovada para TDD/implementação restrita ao Candidato 2b (interpolação sensível a linhas em branco, com gate por página ≥20pt). `Papel/Nome` permanece fora de escopo.

## 0. Diagnóstico e comparação de alternativas (concluído)

- [x] 0.1 Inspecionar a página 1 de `input/Inf0024E.pdf` com `page.get_text("dict")`, rastrear pelo pipeline e determinar causa raiz e primeiro estágio da fusão. Resultado: documentado em `design.md`, ETAPAS 1–3.
- [x] 0.2 Avaliar candidatos (geometria real em todo o pipeline; mudança de fonte/tamanho/cor; interpolação sensível a linhas em branco sem gate) com blast radius medido nos 4 PDFs. Resultado: candidato sem gate tem blast radius de 3/241 páginas, mas toca `Papel/Nome` em 2 delas.
- [x] 0.3 Comparar 3 alternativas (aceitar efeito colateral; sinal estrutural adicional; deferir para futura mudança de `Papel/Nome`) segundo 10 critérios, com simulação completa da função real nos 4 PDFs. Resultado: Candidato 2b (gate por página ≥20pt) tem blast radius de 1/241 páginas, 0 falsos positivos, 0 falsos negativos, 0 impacto em `Papel/Nome`.
- [x] 0.4 Obter decisão humana explícita aprovando o Candidato 2b. Resultado: aprovado.
- [x] 0.5 Documentar em `design.md` a evidência tipográfica que justifica o limiar de 20pt (não um número mágico). Resultado: lacuna real de 10.5pt (15.0pt maior rótulo estrutural do corpus inteiro, 25.5pt menor elemento de masthead) medida em ~13.500 spans dos 4 PDFs.

## 1. Testes (TDD, antes de qualquer implementação)

- [x] 1.1 Adicionar teste positivo (página 1 real do Inf0024E, via `_isolate_first_page`): título, linha de edição/data + "Direito Penal", aviso editorial e "CORTE ESPECIAL" ficam cada um em parágrafo próprio no Markdown final. Implementado em `test_convert_inf0024e_page_1_separates_editorial_cover_elements` (commit `41e206d`).
- [x] 1.2 Adicionar teste positivo unitário de `recompose_native_paragraphs`, replicando a geometria real medida (blocos com linhas em branco intercaladas, bloco de título ≥20pt): confirma a separação dos elementos e ausência de perda de token. Implementado em `test_recompose_native_paragraphs_separates_cover_elements_with_leading_blank_lines` (commit `41e206d`).
- [x] 1.3 Adicionar teste unitário cobrindo especificamente linhas em branco no início e no meio de um bloco geométrico (não apenas no fim), replicando os dois padrões reais encontrados (7 linhas em branco antes do conteúdo; 1 linha em branco depois do conteúdo). Coberto pelo mesmo cenário sintético `_editorial_cover_scenario` (blocos com 7 linhas em branco líderes e 1 linha em branco final), commit `41e206d`.
- [x] 1.4 Adicionar teste negativo: página 11 de `AINTARESP_1462304-PA.pdf` (via `_isolate_first_page`) mantém o comportamento atual — a fusão de `Papel/Nome` já existente permanece inalterada (mesmo texto produzido antes desta mudança). Implementado em `test_convert_aintaresp_page_11_papel_nome_unaffected` (commit `41e206d`) — já passa (verde) antes da implementação, confirmando baseline.
- [x] 1.5 Adicionar teste negativo: página 2 de `REsp_1704551-SP.pdf` mantém o comportamento atual pelo mesmo motivo. Implementado em `test_convert_resp_page_2_signature_block_unaffected` (commit `41e206d`) — já passa (verde).
- [x] 1.6 Adicionar teste negativo unitário: uma página sem nenhum bloco ≥20pt, mas com um bloco contendo linhas em branco intercaladas, não aciona a correção (resultado idêntico ao comportamento pré-existente, calculado sem a correção). Implementado em `test_recompose_native_paragraphs_blank_lines_gate_requires_large_text` (commit `41e206d`) — compara explicitamente `page_has_large_text=False` contra o resultado legado sem o parâmetro.
- [x] 1.7 Adicionar teste de controle próximo ao limiar tipográfico: um bloco com tamanho 19.9pt não aciona o gate; um bloco com tamanho exatamente 20.0pt aciona. Implementado em `test_page_has_large_text_threshold_boundary` (`tests/test_converter.py`, commit `b1809ab`) — página real do PyMuPDF com `insert_text(fontsize=19.9)` retorna `False`, `fontsize=20.0` retorna `True`.
- [x] 1.8 Adicionar teste negativo: um bloco geométrico legítimo, sem linhas em branco intercaladas, em uma página com bloco ≥20pt, continua sendo recomposto normalmente (a correção não introduz nem impede junções fora do padrão de linha em branco). Coberto por `test_recompose_native_paragraphs_separates_cover_elements_with_leading_blank_lines` (o bloco PROCESSO, sem linhas em branco, continua unindo suas próprias linhas físicas normalmente mesmo com o gate ligado).
- [x] 1.9 Adicionar teste negativo: marcadores `[[Pág. N]]` preservados, únicos e sequenciais no resultado dos testes de integração acima. Coberto implicitamente pelos testes de integração existentes (página isolada única); confirmação explícita nos 4 PDFs completos na Seção 3.
- [x] 1.10 Adicionar teste negativo: os 4 casos R01, os 8 SUBTÍTULO, o índice do Código Civil, o guard de `SAIBA MAIS`, os rodapés técnicos já removidos e a normalização de thin-space permanecem intactos (reexecução da suíte existente, sem novos casos específicos). Confirmado: suíte completa reexecutada sem regressão (334 passed além das 4 falhas RED esperadas).
- [x] 1.11 Rodar a suíte e confirmar que os novos testes falham (red) antes da implementação. Resultado: 4 failed (3 `TypeError` por parâmetro inexistente + 1 `StopIteration` na integração, já que os elementos ainda estão fundidos), 334 passed (verificado de forma independente pelo orquestrador, commit `41e206d`).

## 2. Implementação

- [x] 2.1 Em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), alterar a interpolação de `line_height` para dividir pelo número TOTAL de linhas físicas do bloco (incluindo as em branco), preservando o índice original de cada linha não-vazia ao posicioná-la. Implementado via novo parâmetro `page_has_large_text: bool = False` (commit `b1809ab`).
- [x] 2.2 Restringir essa correção a páginas com pelo menos um bloco de texto com tamanho tipográfico ≥20pt; disponibilizar esse sinal ao pipeline (via `converter.py`/`_sorted_native_text_blocks` ou equivalente) sem alterar o extrator, o roteamento ou o OCR. Implementado: `_page_has_large_text(page, threshold=20.0)` em `converter.py`, via `page.get_text("dict")`, calculado ao lado de `native_blocks` e passado a `recompose_native_paragraphs`.
- [x] 2.3 Fora dessas páginas, preservar exatamente o cálculo já existente (divisão apenas pelas linhas não-vazias), byte a byte. Implementado: ramo `else` da função preserva o código original sem alteração.
- [x] 2.4 Rodar a suíte completa e confirmar que os testes novos e existentes passam (green). Resultado: 339/339 passed (verificado de forma independente pelo orquestrador).

## 3. Validação do corpus

- [ ] 3.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado.
- [ ] 3.2 Rodar `openspec validate --all --strict` e registrar o resultado.
- [ ] 3.3 Reconverter os 4 PDFs do corpus com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR.
- [ ] 3.4 Confirmar que `output/Inf0024E.md` p.1 tem os elementos editoriais separados, com antes/depois.
- [ ] 3.5 Confirmar que `AINTARESP_1462304-PA.md`, `REsp_1704551-SP.md` e `L10.406_CC_2002.md` ficam byte-idênticos à reconversão anterior a esta mudança.
- [ ] 3.6 Confirmar que nenhuma palavra foi perdida ou adicionada em `Inf0024E.md` (contagem de tokens antes/depois).
- [ ] 3.7 Confirmar `Papel/Nome` inalterado (decorrência direta de 3.5), R01 (4/4), 8 SUBTÍTULO, índice do CC, rodapés técnicos, `SAIBA MAIS` e thin-space preservados.
- [ ] 3.8 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais nos 4 arquivos.
- [ ] 3.9 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira) nos 4 arquivos.
- [ ] 3.10 Produzir e explicar o diff completo do corpus.

## 4. Encerramento do ciclo

- [ ] 4.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar cada subtarefa.
- [ ] 4.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex.
- [ ] 4.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana).
