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

- [x] 6.1 Executar a suíte completa de testes uma última vez e registrar o resultado. (241 passed)
- [x] 6.2 Reconverter o corpus completo uma última vez e confirmar: 186 marcadores `[[Pág. N]]` sequenciais no Código Civil; ausência dos cabeçalhos/rodapés identificados; parágrafos obrigatórios recompostos; símbolos normalizados apenas nos contextos autorizados; hierarquia Markdown validada; os outros 3 PDFs sem regressão frente à linha de base.
- [x] 6.3 Executar `openspec validate improve-markdown-cleanup-structuring --strict` e resolver todos os apontamentos. (Change is valid)
- [x] 6.4 Escrever o relatório final (métricas, arquivos alterados, testes criados, comandos de reprodução, casos encaminhados para revisão humana) — ver `RELATORIO_FINAL.md`. Arquivamento da mudança pendente de aprovação humana explícita.

## 7. Correções de regressão e cobertura residual (segunda rodada de validação)

Diagnóstico prévio (reconversão completa do corpus, `--no-ocr`, estado pós-grupo 5):

- **7.1 causa raiz**: `formal_structure_pattern`/`bare_structure_pattern` em `recompose_native_paragraphs` usam `re.IGNORECASE` sem exigir primeira letra maiúscula, então palavras comuns minúsculas "parte" e "título" (não os marcadores estruturais) são tratadas como exceção e bloqueiam a junção. Confirmados 14 blocos afetados no Código Civil (6 "parte", 8 "título"), incluindo os 7 artigos citados no objetivo (129, 233, 244, 880, 1.027, 1.258, 1.673) mais outros correlatos.
- **7.3 causa raiz**: `normalize_legal_symbols` só reconhece "Art." maiúsculo; ocorrências reais de "art. 3 o" e "art. 5 o" (minúsculo, referência em prosa) não são normalizadas. Também existe "§ 1 º" (já com "º" correto mas com espaço espúrio antes) que não casa com o padrão atual (que espera a letra "o", não "º"). Investigado "191 6" no Art. 2.040 (página física 176): confirmado como artefato de extração do próprio PyMuPDF (`page.get_text("text")` já retorna "191 6" com espaço, não é introduzido pelo pipeline); ocorrência única no corpus inteiro — decisão: NÃO normalizar nesta rodada (risco de regra frágil para 1 ocorrência), registrar como caso de revisão humana.
- **7.2**: "Lei n" termina a página física 175 e "o 3.071, de 1 o de janeiro de 1916." começa a página 176 (Art. 2.029) — o marcador `[[Pág. 176]]` deve permanecer exatamente onde está; a normalização do símbolo precisa reconhecer a continuidade textual através do marcador de página sem movê-lo ou removê-lo.
- **7.4 causa raiz**: `build_legislative_headings` não reconhece: (a) "TÍTULO I-A"/"CAPÍTULO VII-A" (sufixo "-A" após numeral romano); (b) qualificador "ÚNICA" (feminino, usado com Seção/Subseção) — só "ÚNICO"/"UNICO" está previsto; (c) qualificador "COMPLEMENTAR" (LIVRO COMPLEMENTAR); (d) quando o parágrafo imediatamente após o marcador é só uma anotação parentética "(Incluído/Redação dada/Revogado pela Lei nº ...) (Vigência)" (sem o título real), a implementação atual funde erroneamente o marcador com a ANOTAÇÃO em vez de pular para o título real (caso real confirmado: "Seção I" + "(Incluído pela Lei nº 13.777, de 2018) (Vigência)" virou cabeçalho errado, deixando "Disposições Gerais" — o título de verdade — órfão duas linhas depois); (e) "P A R T E G E R A L"/"P A R T E ESPECIAL" (letras espaçadas no PDF de origem) não são reconhecidas, e mesmo quando despaçadas, são um caso "marcador+qualificador completo em um único parágrafo" (sem próximo parágrafo de título para fundir) que a lógica atual não cobre.
- **7.5 causa raiz**: `mark_final_index` insere `# ÍNDICE` logo após o último artigo (Art. 2.046), mas o parágrafo seguinte ("Aloysio Nunes Ferreira Filho ... Este texto não substitui o publicado no DOU de 11.1.2002 ÍNDICE" — segundo signatário + nota de publicação + a própria palavra de navegação "ÍNDICE" do documento de origem) fica DEPOIS do cabeçalho, ou seja, dentro do índice — violando a exigência de manter signatários e nota de publicação fora do índice. A palavra literal "ÍNDICE" presente nesse parágrafo é o título terminal real do índice e deve ser usada como âncora: o cabeçalho `# ÍNDICE` deve ser inserido IMEDIATAMENTE APÓS esse parágrafo (não antes dele).

### Subtarefas

- [x] 7.1 Corrigir falso positivo de maiúscula/minúscula em `recompose_native_paragraphs`: exigir que a primeira letra do texto candidato seja maiúscula para valer como exceção estrutural (formal e "nua"). Teste de regressão primeiro, cobrindo os 7 artigos citados + reconversão completa para confirmar que os 14 blocos identificados (e só eles) passam a ser unidos corretamente, sem nenhuma união indevida nova.
- [x] 7.2 Implementar continuidade de símbolo entre páginas: quando um parágrafo termina em `Lei n` (ou variantes ancoradas equivalentes) imediatamente antes de um marcador de página, e o parágrafo seguinte (após marcador + comentário de método) começa com `o <número>`, normalizar para `Lei nº <número>` sem mover ou remover `[[Pág. N]]`. Teste de regressão com o caso real do Art. 2.029 (fronteira da página 175/176) primeiro.
- [x] 7.3 Estender `normalize_legal_symbols` para âncoras minúsculas ("art. N o" → "art. Nº") e para a variante "§ N º" (espaço antes de um "º" já correto) → "§ Nº". Não alterar "191 6" (caso investigado e documentado como fora de escopo nesta rodada). Teste de regressão primeiro com os casos reais.
- [x] 7.4 Estender `build_legislative_headings`: sufixo "-A" em numeral romano; qualificador "ÚNICA" além de "ÚNICO"; qualificador "COMPLEMENTAR"; absorver anotação parentética "(Incluído/Redação dada/Revogado pela Lei ...)" (inline ou em parágrafo separado) antes de localizar o título real; reconhecer "P A R T E ..." com letras espaçadas e tratar marcador+qualificador completo (sem título separado) como cabeçalho autônomo. Teste de regressão primeiro com os 6 casos reais (TÍTULO I-A, CAPÍTULO VII-A, Seção Única ×2, LIVRO COMPLEMENTAR, P A R T E GERAL/ESPECIAL, Seção I com anotação órfã).
- [x] 7.5 Corrigir `mark_final_index` para ancorar no parágrafo que contém a palavra literal "ÍNDICE" (título terminal real) dentro da região após o último artigo, inserindo o cabeçalho imediatamente DEPOIS desse parágrafo (mantendo Art. 2.046, data de promulgação, assinaturas e nota de publicação fora do índice); manter o heurístico de densidade estrutural como fallback caso a palavra não seja encontrada. Teste de regressão primeiro com o caso real do Código Civil.
- [ ] 7.6 Escanear o documento inteiro (todas as 186 páginas) após cada correção acima em busca de instâncias residuais do mesmo defeito (não só os exemplos citados), documentando a contagem antes/depois.
- [ ] 7.7 Executar a suíte completa; reconverter o corpus completo (`--no-ocr`); comparar token a token com o estado anterior (pós-grupo 5) e confirmar: nenhuma perda/alteração/duplicação de texto fora do autorizado; 186 marcadores sequenciais; nenhum cabeçalho novo nos 3 PDFs não legislativos; nenhum teste anteriormente aprovado quebrado.
- [ ] 7.8 Atualizar `RELATORIO_FINAL.md` com as métricas, diffs exatos e casos desta segunda rodada (incluindo "191 6" como caso deliberadamente adiado).
