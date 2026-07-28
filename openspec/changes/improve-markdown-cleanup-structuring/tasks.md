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
- [x] 7.6 Escanear o documento inteiro (todas as 186 páginas) após cada correção acima em busca de instâncias residuais do mesmo defeito (não só os exemplos citados), documentando a contagem antes/depois. Resultado: 0 residuais em todos os 5 defeitos.
- [x] 7.7 Executar a suíte completa; reconverter o corpus completo (`--no-ocr`); comparar token a token com o estado anterior (pós-grupo 5) e confirmar: nenhuma perda/alteração/duplicação de texto fora do autorizado; 186 marcadores sequenciais; nenhum cabeçalho novo nos 3 PDFs não legislativos; nenhum teste anteriormente aprovado quebrado. Suíte: 251/251. Comparação letra-a-letra (letras+"º") confirma soma exata de caracteres igual (503.729=503.729), diferença localizada exatamente nas trocas "o"→"º" já validadas nas subtarefas 7.2/7.3.
- [x] 7.8 Atualizar `RELATORIO_FINAL.md`

## 8. Terceira rodada de validação (defeitos de estrutura final e símbolos)

Diagnóstico prévio (via geometria real do PDF, página física 177, e reconversão do corpus):

- **8.1 causa raiz**: "P A R T E E S P E C I A L" (letras espaçadas) fica no MESMO bloco geométrico do fim do Art. 232 com uma folga vertical (gap) menor que o limiar de 1,2× já usado por `recompose_native_paragraphs` — nenhuma exceção existente reconhece um marcador letra-espaçado como "próxima linha", então ele é indevidamente unido ao parágrafo do artigo, chegando em `build_legislative_headings` já "contaminado" (não bate mais com o regex de correspondência total exigido pela pré-passada letra-espaçada da subtarefa 7.4).
- **8.2 causa raiz**: na página 177, os blocos geométricos reais são: Art. 2.046 (y0=28.6-51.7) → linha de promulgação "Brasília, 10 de janeiro de 2002; 181 o da Independência e 114 o da República." (y0=62.3-77.5, gap=10.6) → bloco com as DUAS assinaturas "FERNANDO HENRIQUE CARDOSO\nAloysio Nunes Ferreira Filho" (y0=88.4-110.9, gap=10.9 do anterior, MESMO bloco entre si) → nota de publicação "Este texto não substitui o publicado no DOU de 11.1.2002" (y0=120.7-131.9, gap=9.8) → "ÍNDICE" isolado (y0=142.6-153.7, gap=10.7). Todos esses gaps (9.8–10.9) ficam abaixo do limiar de 1,2×altura-de-linha, então tudo é unido numa cadeia. A separação entre FERNANDO/Aloysio já ocorre hoje por acaso (salvaguarda existente `native_label_pattern`, que exclui quando a linha anterior é totalmente maiúscula); as demais fronteiras (Art.→promulgação, promulgação→assinatura, assinatura→nota, nota→ÍNDICE) não têm nenhuma exceção.
- **8.3 causa raiz**: depende de 8.2 — só depois que "ÍNDICE" virar seu próprio parágrafo isolado é que faz sentido `mark_final_index` SUBSTITUIR esse parágrafo por `# ÍNDICE` (em vez de inserir um parágrafo novo do lado, o que hoje produz `...ÍNDICE` (palavra solta, dentro do parágrafo da nota de publicação) seguido de um `# ÍNDICE` novo seguido — redundante, embora não literalmente "duplicado" porque nunca ficou como parágrafo próprio).
- **8.4 causa raiz**: "Lei n º" (espaço antes de um "º" já correto) não é coberto por nenhuma regra existente (a subtarefa 7.3 só cobriu "§ N º", não "Lei n º"); "1 o de janeiro" / "181 o da Independência" / "114 o da República" continuam sem normalizar (decisão de escopo da rodada 1 foi não cobrir ordinais soltos sem âncora — o objetivo agora pede explicitamente para cobrir esses contextos de data/promulgação, que são inequívocos). "191 6" no Art. 2.040 já foi investigado na rodada 2 (confirmado artefato do PyMuPDF, único no corpus) — o objetivo agora autoriza corrigir SE confirmado, então será corrigido nesta rodada com uma regra estritamente ancorada ao contexto de data.

### Subtarefas

- [ ] 8.1 Detectar e separar, ANTES da construção de cabeçalhos, um marcador estrutural letra-espaçado colado ao final de um parágrafo (ex. "... com o exame. P A R T E E S P E C I A L"), suportando pelo menos "P A R T E G E R A L" e "P A R T E E S P E C I A L", sem dividir texto maiúsculo comum. Teste de regressão com o caso real do Art. 232 primeiro.
- [ ] 8.2 Separar os blocos finais da lei (fim do artigo; linha de promulgação; blocos de assinatura curtos e isolados; nota de publicação; marcador de índice terminal) usando geometria de bloco do PDF e fronteiras estruturais conservadoras (não usar nomes próprios como regra principal). Teste de regressão com o caso real do Art. 2.046 primeiro.
- [ ] 8.3 Corrigir a marcação do índice terminal para localizar o "ÍNDICE" isolado real (após a nota de publicação, uma vez separado pela subtarefa 8.2) e SUBSTITUÍ-LO por `# ÍNDICE` (em vez de inserir um parágrafo adicional), garantindo exatamente uma ocorrência e preservando o "ÍNDICE" válido da página 1 inalterado. Teste de regressão primeiro.
- [ ] 8.4 Completar a normalização segura de símbolos: "Lei n º" → "Lei nº"; ordinais de data/promulgação inequívocos ("N o de janeiro"→"Nº de janeiro" e equivalentes para os 12 meses; "N o da Independência"→"Nº da Independência"; "N o da República"→"Nº da República"); corrigir "191 6"→"1916" no Art. 2.040 (já investigado e confirmado como artefato de extração, autorizado a corrigir nesta rodada) com regra estritamente ancorada ao contexto de data. Teste de regressão primeiro para cada caso.
- [ ] 8.5 Escanear o documento inteiro (186 páginas) em busca de instâncias residuais de cada defeito acima, documentando contagem antes/depois; verificar idempotência (rodar a limpeza duas vezes produz o mesmo resultado).
- [ ] 8.6 Executar a suíte completa; reconverter o corpus completo (`--no-ocr`); comparar token a token / letra a letra com o estado anterior (fim da rodada 2) e confirmar ausência de regressão em todos os 4 arquivos; 186 marcadores sequenciais; nenhum cabeçalho novo nos 3 PDFs não legislativos; nenhum teste anteriormente aprovado quebrado.
- [ ] 8.7 Atualizar `RELATORIO_FINAL.md` com as métricas, diffs exatos e casos desta terceira rodada. com as métricas, diffs exatos e casos desta segunda rodada (incluindo "191 6" como caso deliberadamente adiado).
