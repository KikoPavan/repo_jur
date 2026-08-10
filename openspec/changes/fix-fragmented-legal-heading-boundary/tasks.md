> Histórico: esta mudança começou como diagnóstico puro (Seção 0). Conclusão: A) CRITÉRIO SEGURO ENCONTRADO — blast radius previsto de 2/241 páginas, 0 falsos positivos, 0 falsos negativos. Aprovada por decisão humana para TDD/implementação restrita ao critério diagnosticado (recuo x0 das demais linhas do bloco, limiar de 50%, ver `design.md`).

## 0. Diagnóstico (concluído)

- [x] 0.1 Localizar as ocorrências reais e inspecionar a estrutura nativa via `page.get_text("dict")`. Resultado: 2 ocorrências reais, `REsp_1704551-SP.pdf` páginas 1 e 6; documentado em `design.md`, ETAPA 1.
- [x] 0.2 Rastrear pelo pipeline e determinar o primeiro estágio responsável. Resultado: **A** — o PDF (via PyMuPDF) já entrega a fragmentação; o guard de rótulo em `recompose_native_paragraphs` é quem falha ao recompor. `design.md`, ETAPA 2.
- [x] 0.3 Comparar com casos corretos e avaliar sinais candidatos, com blast radius medido nos 4 PDFs via simulação da função real. Resultado: recuo x0 das demais linhas do bloco discrimina perfeitamente 44 rótulos genuínos vs. 2 falsos positivos; blast radius de 2/241 páginas. `design.md`, ETAPA 3–4.
- [x] 0.4 Obter decisão humana explícita aprovando o critério. Resultado: aprovado.
- [x] 0.5 Formalizar o limiar geométrico (50%) com base na separação observada no corpus (0–23% vs. 81%, lacuna de 58 pontos percentuais), documentado em `design.md`, "Decisão aprovada e limiar geométrico formalizado".

## 1. Testes (TDD, antes de qualquer implementação)

- [x] 1.1 Adicionar teste positivo (página 1 real de `REsp_1704551-SP.pdf`, via `_isolate_first_page`): "RECURSO" e "ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE COMPROMISSO ARBITRAL..." ficam unidos em um único parágrafo. Implementado em `test_convert_resp_page_1_unifies_recurso_especial_heading` (commit `bdccba7`).
- [x] 1.2 Adicionar teste positivo equivalente para a página 6. Implementado em `test_convert_resp_page_6_unifies_recurso_especial_heading` (commit `bdccba7`).
- [x] 1.3 Adicionar teste positivo unitário de `recompose_native_paragraphs`, replicando a geometria real medida (bloco com pseudo-linhas de y0/y1 idênticos, x0 majoritariamente igual ao da linha-rótulo): confirma a união e ausência de perda de token/pontuação. Implementado em `test_recompose_native_paragraphs_unifies_recurso_especial_with_x0_signal` (commit `bdccba7`).
- [x] 1.4 Adicionar teste negativo: `PROCESSO` (label x0=145.6, linhas seguintes x0=218.4, 0% de coincidência) permanece separado do valor. Implementado em `test_recompose_native_paragraphs_keeps_processo_label_separated` (commit `bdccba7`).
- [x] 1.5 Adicionar teste negativo: `TEMA` (mesmo padrão de `PROCESSO`) permanece separado. Implementado em `test_recompose_native_paragraphs_keeps_tema_label_separated` (commit `bdccba7`).
- [x] 1.6 Adicionar teste negativo: `RAMO DO DIREITO` permanece separado. Implementado em `test_recompose_native_paragraphs_keeps_ramo_do_direito_label_separated` (commit `bdccba7`).
- [x] 1.7 Adicionar teste negativo: `AGRAVANTE` (bloco `:`-marcado) permanece separado. Implementado em `test_convert_aintaresp_page_11_agravante_agravado_assunto_unaffected` (commit `bdccba7`).
- [x] 1.8 Adicionar teste negativo: `AGRAVADO` permanece separado. Coberto pelo mesmo teste do item 1.7.
- [x] 1.9 Adicionar teste negativo: `ASSUNTO` permanece separado. Coberto pelo mesmo teste do item 1.7.
- [x] 1.10 Adicionar teste negativo: `RECORRENTE` (23% de coincidência, abaixo do limiar de 50%) permanece separado — caso mais próximo da fronteira entre os rótulos genuínos do corpus real. Implementado em `test_recompose_native_paragraphs_keeps_recorrente_label_separated` (geometria real) e `test_convert_resp_page_3_recorrente_unaffected`/`test_convert_resp_page_14_recorrente_unaffected` (integração, commit `bdccba7`).
- [x] 1.11 Adicionar teste negativo: `VÍDEO DO JULGAMENTO` permanece separado. Implementado em `test_convert_inf0024e_video_do_julgamento_unaffected` — teste escrito mas com `page_index` incorreto (0 em vez de 3); correção incluída como parte da Subtarefa 2 (o próprio Codex diagnosticou o índice correto ao rodar o teste, mas duas tentativas de aplicar a correção isoladamente travaram na execução; a correção de 2 strings foi agrupada à subtarefa de implementação para evitar uma terceira tentativa isolada).
- [x] 1.12 Adicionar teste negativo: os casos `Papel/Nome` (`AINTARESP_1462304-PA.pdf` p.11, `REsp_1704551-SP.pdf` p.3/p.14 `RECORRENTE`) permanecem exatamente como hoje. Coberto pelos testes dos itens 1.7 e 1.10.
- [x] 1.13 Adicionar teste de controle de fronteira: bloco sintético com exatamente 50% das linhas seguintes na mesma margem (não deve desativar a proteção — a regra exige MAIS de 50%, `> 0.5`, não `>=`) e outro com 51%/66% (deve desativar). Implementado em `test_recompose_native_paragraphs_boundary_exactly_fifty_percent_keeps_protection` e `test_recompose_native_paragraphs_boundary_above_fifty_percent_disables_protection` (commit `bdccba7`).
- [x] 1.14 Adicionar teste negativo: bloco cuja linha-rótulo não tem nenhuma outra linha física (sem dado de x0 para comparar) mantém a proteção ativa, idêntico ao comportamento anterior. Implementado em `test_recompose_native_paragraphs_block_without_extra_lines_keeps_protection` (commit `bdccba7`). Compatibilidade sem o parâmetro `line_x0s` coberta também por `test_recompose_native_paragraphs_without_x0_parameter_preserves_legacy_behavior`.
- [x] 1.15 Rodar a suíte e confirmar que os novos testes falham (red) antes da implementação. Resultado: 8 failed (os que dependem do parâmetro `line_x0s`, ainda inexistente), 345 passed (verificado de forma independente pelo orquestrador, commit `bdccba7`).

## 2. Implementação

- [x] 2.1 Em `_sorted_native_text_blocks` (`src/pipeline_juridico/converter.py`), adicionar apenas o dado geométrico necessário: x0 por linha física bruta de cada bloco (via `page.get_text("dict")`), sem alterar o extrator, o roteamento ou o OCR. Implementado (commit `e38b715`).
- [x] 2.2 Em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), usar esse dado exclusivamente para refinar a condição `native_label_pattern.match(previous_text) and previous_is_first`: desativar a proteção quando o bloco tiver outras linhas físicas E mais da metade delas tiverem x0 a menos de 2pt do x0 da linha-rótulo. Nenhuma outra condição de `should_join` é alterada. Implementado via novo parâmetro `line_x0s` (commit `e38b715`). Nota de revisão: a primeira versão da implementação incluía uma heurística extra não especificada (`horizontally_fragmented`), introduzida para compensar um fixture de teste truncado (16 de 33 linhas reais) que eu mesmo havia fornecido incorretamente. Corrigido: fixture substituído pelo bloco real completo (33 linhas), heurística extra removida — a regra final usa exclusivamente `same_margin_fraction <= 0.5`, exatamente como diagnosticado e aprovado.
- [x] 2.3 Preservar o comportamento atual quando o bloco não tiver outras linhas físicas (sem dado de comparação). Implementado: `if first_x0 is None or not other_x0s: genuine_label_blocks[block_index] = True`.
- [x] 2.4 Rodar a suíte completa e confirmar que os testes novos e existentes passam (green). Resultado: 354/354 passed (verificado de forma independente pelo orquestrador, commit `e38b715`).

## 3. Validação do corpus

- [x] 3.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado. Resultado: 354/354 passed.
- [x] 3.2 Rodar `openspec validate --all --strict` e registrar o resultado. Resultado: 2 passed, 0 failed (`change/fix-fragmented-legal-heading-boundary`, `spec/juridical-pdf-conversion`).
- [x] 3.3 Reconverter os 4 PDFs do corpus com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR. Resultado: 241 páginas roteadas como `texto_nativo`; `ocr.enabled: false` e `status: sucesso` nos 4 relatórios.
- [x] 3.4 Confirmar que somente as 2 ocorrências reais (`REsp_1704551-SP.pdf` p.1 e p.6) mudam, com antes/depois. Resultado: "RECURSO" + "ESPECIAL. PROCESSUAL CIVIL. ... POSSIBILIDADE." (antes em 2 parágrafos) → 1 parágrafo único, nas duas ocorrências.
- [x] 3.5 Confirmar que `Inf0024E.md`, `AINTARESP_1462304-PA.md` e `L10.406_CC_2002.md` ficam byte-idênticos à reconversão anterior a esta mudança. Resultado: os 3 arquivos com MD5 idêntico ao baseline pré-mudança.
- [x] 3.6 Confirmar que nenhuma palavra foi perdida ou adicionada em `REsp_1704551-SP.md` (contagem de tokens antes/depois). Resultado: 3497 → 3497 tokens (`\w+`), diferença zero.
- [x] 3.7 Confirmar `Papel/Nome` inalterado, R01 (4/4), 8 SUBTÍTULO, índice do CC, rodapés técnicos, thin-space, `SAIBA MAIS` e capa editorial preservados. Resultado: `AINTARESP_1462304-PA.md` p.11 continua com "Presidente da Sessão"/"GURGEL DE FARIA" fundido exatamente como antes; `RECORRENTE` continua em linha própria nas 6 ocorrências de `REsp_1704551-SP.md`; `L10.406_CC_2002.md` byte-idêntico (R01/SUBTÍTULO/índice triviais); `GABGF09`/`Documento: 1807307` continuam em 0; thin-space continua em 0; `CORTE ESPECIAL` continua separado (capa editorial preservada).
- [x] 3.8 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais nos 4 arquivos. Resultado: AINT=12, REsp=14, Inf0024E=29, CC=186, todos únicos e sequenciais.
- [x] 3.9 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira, byte a byte) nos 4 arquivos. Resultado: os 4 arquivos byte-idênticos entre a 1ª e a 2ª reconversão.
- [x] 3.10 Produzir e explicar o diff completo do corpus. Resultado: único arquivo alterado é `output/REsp_1704551-SP.md` (2 blocos, páginas 1 e 6, unindo "RECURSO" ao restante da ementa); os outros 3 arquivos byte-idênticos ao baseline pré-mudança.

## 4. Encerramento do ciclo

- [x] 4.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar cada subtarefa. Feito em cada subtarefa — inclusive identificando e corrigindo, na revisão da Subtarefa 2, uma heurística extra não aprovada que havia sido introduzida para compensar um fixture de teste truncado.
- [x] 4.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex. Feito (commits `bdccba7`, `91a5ee9`, `e38b715`, `facf023`, `e813d62`).
- [x] 4.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana).
