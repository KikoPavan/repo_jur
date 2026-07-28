> Nota geral: toda reconversão do corpus mencionada neste arquivo (linha de base e comparações "antes/depois") DEVE usar `converter-juridico --no-ocr`. Este objetivo não altera nem exercita o caminho de OCR; qualquer página que exija OCR real sob `--no-ocr` é regressão de roteamento ou caso BLOQUEADO — nunca chamar a API Gemini para contornar.

## 0. Linha de base do corpus

- [x] 0.1 Reconverter o corpus completo (`input/L10.406_CC_2002.pdf`, `input/AINTARESP_1462304-PA.pdf`, `input/REsp_1704551-SP.pdf`, `input/Inf0024E.pdf`) com `converter-juridico --no-ocr` (sem chamadas reais de OCR — este objetivo não altera nem exercita o caminho de OCR) e salvar as saídas como linha de base para comparação antes/depois em cada subtarefa seguinte. Toda página que sair como `erro`/vazia por exigir OCR deve ser registrada como regressão de roteamento ou caso BLOQUEADO, sem chamar a API Gemini para resolver.

## 1. Recomposição geométrica de parágrafos

- [x] 1.1 Criar teste de regressão que reproduza o caso obrigatório do Código Civil: "Art. 2º ... desde a concepção, os" + "direitos do nascituro." devem virar um único parágrafo no Markdown final, e que hoje falha (fragmentado).
- [x] 1.2 Implementar extração de blocos geométricos por página nativa (bbox, texto) reutilizando o padrão já usado em `_geometric_reading_order_text`, sem alterar a salvaguarda de ordem de leitura existente.
- [x] 1.3 Implementar a regra de junção de blocos (distância vertical relativa + continuidade textual) com a lista de exceção (Art./§/inciso/alínea/item; PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO; marcador `[[Pág. N]]`; novo bloco estrutural) e conectá-la ao ponto de geração do conteúdo nativo em `converter.py`.
- [x] 1.4 Adicionar testes cobrindo cada exceção de não-junção (um teste por tipo de marcador que bloqueia a junção).
- [x] 1.5 Executar a suíte completa e reconverter o corpus; comparar com a linha de base e confirmar ausência de regressão (nenhuma perda/alteração/duplicação de texto, 186 marcadores sequenciais no Código Civil).

## 2. Remoção de cabeçalhos e rodapés repetitivos

- [x] 2.1 A partir do corpus reconvertido, identificar concretamente quais linhas marginais repetitivas existem (data/hora, nome de arquivo, URL, contador "N/186") e escrever teste de regressão com exemplos reais extraídos do corpus.
- [x] 2.2 Implementar detecção por repetição entre blocos de página (topo/rodapé) restrita aos 4 padrões autorizados, sem tocar nos demais.
- [x] 2.3 Implementar a remoção preservando `[[Pág. N]]` e todo conteúdo jurídico repetido que não corresponda aos padrões autorizados.
- [x] 2.4 Adicionar teste garantindo que conteúdo jurídico repetido (ex. cabeçalho de seção genuíno) NÃO é removido.
- [x] 2.5 Executar a suíte completa e reconverter o corpus; comparar com a linha de base e confirmar ausência de regressão.

## 3. Normalização contextual de símbolos

- [x] 3.1 Criar testes de regressão para os três padrões obrigatórios ("Art. 1 o" → "Art. 1º", "§ 1 o" → "§ 1º", "Lei n o" → "Lei nº") e para um caso negativo explícito (uma letra "o" após número que NÃO deve ser alterada, ex. numeração de item ou data).
- [x] 3.2 Implementar a normalização com regex restritas aos padrões autorizados.
- [x] 3.3 Executar a suíte completa e reconverter o corpus; comparar com a linha de base e confirmar que nenhum número, data, valor ou referência legal fora do padrão foi alterado.

## 4. Estrutura Markdown legislativa

- [x] 4.1 Criar teste de regressão para o caso obrigatório "LIVRO I" + "DAS PESSOAS" (Código Civil) tornando-se um único cabeçalho Markdown, e um teste negativo de texto maiúsculo comum que não deve virar título.
- [x] 4.2 Implementar reconhecimento de PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO e fusão com o título imediatamente seguinte no nível de cabeçalho correspondente (`#` a `######`). Caso para revisão humana: "P A R T E GERAL"/"P A R T E ESPECIAL" no Código Civil são grafados com letras espaçadas no PDF de origem e não casam com o regex de marcador nu, então não viram cabeçalho nível 1 (`#`) — LIVRO/TÍTULO/CAPÍTULO/SEÇÃO funcionam normalmente.
- [x] 4.3 Executar a suíte completa e reconverter o corpus; comparar com a linha de base e validar a hierarquia Markdown resultante (níveis consistentes, sem título espúrio).

## 5. Índice final

- [x] 5.1 Localizar no corpus (provavelmente Código Civil) o ponto real de transição corpo normativo → índice e escrever teste de regressão com esse caso.
- [x] 5.2 Implementar a heurística de detecção do início do índice e inserção do cabeçalho `# ÍNDICE`, sem remover ou reordenar conteúdo.
- [x] 5.3 Adicionar teste garantindo que documentos sem índice detectável permanecem inalterados (nenhum cabeçalho `# ÍNDICE` inserido).
- [x] 5.4 Executar a suíte completa e reconverter o corpus; comparar com a linha de base e confirmar ausência de regressão.

## 6. Fechamento

- [ ] 6.1 Executar a suíte completa de testes uma última vez e registrar o resultado.
- [ ] 6.2 Reconverter o corpus completo uma última vez e confirmar: 186 marcadores `[[Pág. N]]` sequenciais no Código Civil; ausência dos cabeçalhos/rodapés identificados; parágrafos obrigatórios recompostos; símbolos normalizados apenas nos contextos autorizados; hierarquia Markdown validada; os outros 3 PDFs sem regressão frente à linha de base.
- [ ] 6.3 Executar `openspec validate improve-markdown-cleanup-structuring --strict` e resolver todos os apontamentos.
- [ ] 6.4 Escrever o relatório final (métricas, arquivos alterados, testes criados, comandos de reprodução, casos encaminhados para revisão humana) e arquivar a mudança somente após aprovação humana dos critérios de aceite.
