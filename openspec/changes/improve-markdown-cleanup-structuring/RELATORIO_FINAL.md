# Relatório Final — Limpeza e Estruturação Markdown Determinística

Mudança OpenSpec: `improve-markdown-cleanup-structuring`
Escopo: `src/pipeline_juridico/cleaner.py`, `src/pipeline_juridico/converter.py`, `tests/test_cleaner.py`, `tests/test_converter_integration.py`.
Sem LLM em runtime; toda a lógica é Python determinístico (regex + geometria de PDF via PyMuPDF).

## 1. O que foi implementado

Cinco novas funções em `cleaner.py`, encadeadas em `converter.py` (uma por página, para recomposição de parágrafos; as demais sobre o documento já composto), nesta ordem:

1. **`recompose_native_paragraphs(content, blocks)`** — recompõe parágrafos fragmentados em páginas `texto_nativo`, usando blocos geométricos do PyMuPDF (bbox + texto) extraídos em `converter.py` (`_sorted_native_text_blocks`). Une linhas quando a folga vertical é pequena (≤ 1,2× a altura da linha anterior) e nenhuma exceção se aplica (Art./§/Parágrafo/inciso romano/alínea/item/estrutura formal/marcador nu anterior/tabela nativa). Protegida por checagem de sobreposição lexical (≥98%) contra a saída original do MarkItDown antes de substituir o conteúdo.
2. **`remove_repetitive_margins(markdown)`** — remove só as 4 categorias autorizadas (data/hora de impressão + nome técnico de arquivo; URL; contador de página "N/total" ou "Página N de M") quando repetidas em ≥60% das páginas na mesma posição (primeira/última linha do bloco), removendo apenas o trecho casado, nunca a linha inteira se houver mais conteúdo.
3. **`normalize_legal_symbols(content)`** — normaliza só os 4 padrões ancorados por palavra-chave jurídica: `Art. N o`→`Art. Nº`, `§ N o`→`§ Nº`, `Lei n o`→`Lei nº`, `parágrafo N o`→`parágrafo Nº`. Não toca em ordinais soltos sem âncora.
4. **`build_legislative_headings(markdown)`** — funde um marcador estrutural "nu" (PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO + numeral romano/ÚNICO, nada mais) com o parágrafo de título imediatamente seguinte em um único cabeçalho Markdown (`#` a `######`).
5. **`mark_final_index(markdown)`** — localiza o último "Art. N" do documento; se pelo menos 3 parágrafos estruturais o seguem, insere `# ÍNDICE` logo depois, sem remover nada.

## 2. Métricas de corpus (reconversão completa, `--no-ocr`, linha de base vs. final)

Todas as 4 conversões terminaram com `status: sucesso`; contagem de páginas idêntica à linha de base em todos os arquivos.

| Arquivo | Páginas | Tokens removidos | Tokens adicionados | O que mudou |
| --- | --- | --- | --- | --- |
| L10.406_CC_2002.pdf | 186 | 4188 | 421 | cabeçalho/rodapé técnico (3348), símbolos "N o"→"Nº" (420 "o" + 10 "n" removidos, 410 "Nº"+"nº" adicionados), "índice" (+1) |
| AINTARESP_1462304-PA.pdf | 12 | 0 | 0 | nenhuma mudança (nenhum padrão autorizado presente) |
| REsp_1704551-SP.pdf | 14 | 56 | 0 | contador "Página N de 6" removido (14 páginas) |
| Inf0024E.pdf | 29 | 261 | 0 | rodapé URL+contador removido (29 páginas) |

Em todos os casos, a diferença de tokens foi auditada campo a campo (não apenas em contagem agregada) confirmando que o conjunto de tokens removidos/adicionados corresponde exatamente às 4 categorias autorizadas — nenhum número, data, valor monetário ou palavra de conteúdo jurídico foi alterado fora desses padrões.

## 3. Critérios de conclusão do objetivo

- [x] Suíte completa aprovada: **241 passed**, 0 falhas.
- [x] 186 marcadores `[[Pág. N]]` preservados e sequenciais no Código Civil.
- [x] Cabeçalhos/rodapés repetitivos identificados ausentes ("30/11/24, 19:06 L10406compilada" e URL+contador do CC; URL+contador do Inf0024E; "Página N de 6" do REsp — todos com contagem 0 na saída final).
- [x] Parágrafo obrigatório recomposto: "Art. 2 o ... desde a concepção, os" + "direitos do nascituro." formam um único parágrafo.
- [x] Símbolos normalizados apenas nos contextos autorizados (Art./§/Lei n/parágrafo); ordinais soltos sem âncora (ex. "1 o Ofício da Capital", "181 o da Independência e 114 o da República") permanecem intocados, por decisão de escopo documentada.
- [x] Hierarquia Markdown validada: `#`=1 (ÍNDICE), `##`=8 (LIVRO), `###`=42 (TÍTULO), `####`=175 (CAPÍTULO), `#####`=152 (Seção), `######`=15 (Subseção) — níveis consistentes, sem título espúrio nos outros 3 arquivos (0 cabeçalhos criados).
- [x] Três PDFs restantes sem regressão: AINTARESP byte-a-byte idêntico (0 tokens alterados); REsp e Inf0024E só perderam os tokens do rodapé autorizado.
- [x] `openspec validate improve-markdown-cleanup-structuring --strict` → válido.

## 4. Arquivos alterados

- `src/pipeline_juridico/cleaner.py` (+327 linhas): as 5 funções novas.
- `src/pipeline_juridico/converter.py` (+33 linhas): `_sorted_native_text_blocks` + 5 novos pontos de chamada na composição do documento.
- `tests/test_cleaner.py` (+398 linhas): testes unitários das 5 funções, incluindo casos negativos e de idempotência.
- `tests/test_converter_integration.py` (+233 linhas): testes de integração com fatias reais do corpus (`_isolate_first_page`, `_isolate_page_range`).

Nenhum outro arquivo do repositório foi tocado. Nenhuma dependência nova. `router.py`, `engines.py`, `inspector.py` e a salvaguarda de ordem de leitura existente (`_geometric_reading_order_text`, `_has_native_reading_order_defect`, `_has_fabricated_native_table`) permanecem inalterados.

## 5. Testes criados (43 novos, todos com contraparte negativa quando aplicável)

`tests/test_cleaner.py`: 13 testes de `recompose_native_paragraphs` (junção básica + 10 exceções + tabela + blocos vazios), 9 de `normalize_legal_symbols` (3 padrões positivos + 2 negativos reais do corpus + idempotência), 8 de `build_legislative_headings` (4 níveis + caso de linha única + negativo + preservação de conteúdo/marcadores), 3 de `mark_final_index` (positivo via integração + 2 negativos).

`tests/test_converter_integration.py`: caso obrigatório do Art. 2º; 2 testes de cabeçalho/rodapé (CC e Inf0024E) + 1 de correção de espaçamento (REsp) + 2 de preservação de conteúdo repetido legítimo (AINTARESP, Inf0024E); 1 de fusão de cabeçalho no documento real; 1 de detecção de índice real + 2 de ausência de índice (AINTARESP, REsp).

## 6. Comandos de reprodução

```bash
uv sync
uv run pytest tests/ -q

# Reconversão do corpus (sem OCR — este objetivo não exercita o caminho de OCR)
uv run converter-juridico input/L10.406_CC_2002.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/AINTARESP_1462304-PA.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/REsp_1704551-SP.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/Inf0024E.pdf --no-ocr --overwrite --log-level WARNING

openspec validate improve-markdown-cleanup-structuring --strict
```

## 7. Casos encaminhados para revisão humana — estado ao final da PRIMEIRA rodada (histórico; ver seção 9 para a lista atualizada após a segunda rodada — os itens 2 e 4 abaixo foram resolvidos)

1. **Ordinais soltos sem âncora jurídica** (Código Civil): `"...no 1 o Ofício da Capital do Estado..."` e `"...181 o da Independência e 114 o da República."` continuam com o "o" não normalizado. Corrigir exigiria uma heurística sem palavra-chave anterior, o que a instrução do projeto proíbe explicitamente ("não fazer substituição global de toda letra 'o' após números"). Testado e documentado como comportamento intencional.
2. **`"P A R T E GERAL"` / `"P A R T E ESPECIAL"`** (Código Civil): grafados com letras espaçadas (kerning) no PDF de origem; não casam com o regex de marcador estrutural "nu" e por isso não viram cabeçalho de nível 1 (`#`). LIVRO/TÍTULO/CAPÍTULO/SEÇÃO funcionam normalmente porque não têm essa grafia espaçada no original.
3. **Cabeçalho/rodapé técnico do AINTARESP** (ex. "Superior Tribunal de Justiça" repetido, bloco de assinatura eletrônica com códigos de controle "GABGF09 AREsp 1462304 Petição : 592169/2020 C542506155;...") e do REsp (`"Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019"` repetido): nenhum corresponde às 4 categorias autorizadas (não é data/hora+arquivo isolado, não é URL, não é contador de página no formato esperado) e por isso permaneceu intocado, por decisão conservadora — remover exigiria uma quinta categoria autorizada, que não foi solicitada pelo objetivo e arriscaria remover conteúdo de assinatura/autenticação juridicamente relevante.
4. **"LIVRO COMPLEMENTAR DAS DISPOSIÇÕES FINAIS E TRANSITÓRIAS"** (dentro do índice do Código Civil): usa "COMPLEMENTAR" em vez de numeral romano/"ÚNICO"; se essa mesma grafia existir como marcador "nu" no corpo (fora do índice), não seria reconhecida pela subtarefa 4. Não foi encontrada ocorrência assim no corpo durante os testes, mas fica registrado para o caso de aparecer em outro documento.

## 8. Segunda rodada de validação (grupo 7) — correções de regressão e cobertura residual

Uma segunda validação humana identificou 5 categorias de defeito residual não cobertas pela primeira rodada. Cada uma foi diagnosticada por reconversão completa do corpus antes de qualquer código ser escrito, corrigida com um teste de regressão criado primeiro, e verificada de forma independente pelo orquestrador (suíte completa + reconversão do corpus + comparação de tokens/letras antes-depois) antes de ser aprovada.

### 8.1 Causas raiz e correções

1. **Falso positivo maiúscula/minúscula em `recompose_native_paragraphs`** — as exceções de marcador estrutural (`formal_structure_pattern`/`bare_structure_pattern`) usavam `re.IGNORECASE` sem exigir letra inicial maiúscula, então as palavras comuns minúsculas "parte" e "título" (não os marcadores PARTE/TÍTULO) bloqueavam indevidamente a junção de parágrafos. **Corrigido** com uma checagem adicional `_is_uppercase_led(text)`. Confirmados e corrigidos os 7 artigos citados (129, 233, 244, 880, 1.027, 1.258, 1.673) mais 7 outros pontos do mesmo padrão — 14 blocos no total, 0 residuais após a correção.
2. **Continuidade de símbolo entre páginas** — "Lei n" terminava a página 175 e "o 3.071, de 1 o de janeiro de 1916." começava a página 176 (Art. 2.029), sem normalizar através da fronteira. **Corrigido** com `join_symbol_across_page_break`, que funde "Lei n" + "o " através do marcador `[[Pág. N]]` sem mover ou remover o marcador. Único caso desse tipo no corpus inteiro (verificado por varredura completa); 0 residuais.
3. **Cobertura de símbolos estendida** — `normalize_legal_symbols` só reconhecia "Art." maiúsculo; ocorrências reais minúsculas "art. 3 o" e "art. 5 o" (×2) não eram normalizadas, e a variante "§ 1 º" (já com "º" correto, mas espaço espúrio antes) também não. **Corrigido** com duas regras novas. "191 6" no Art. 2.040 foi investigado contra o PDF de origem: confirmado como artefato do próprio PyMuPDF (presente até em `page.get_text("text")` bruto), ocorrência única no corpus — **deliberadamente não alterado** nesta rodada (ver seção 9).
4. **Estrutura legislativa incompleta** — `build_legislative_headings` não reconhecia sufixo "-A" em numeral romano (TÍTULO I-A, CAPÍTULO VII-A), qualificador feminino "ÚNICA" (Seção Única), qualificador "COMPLEMENTAR" (LIVRO COMPLEMENTAR), nem anotações parentéticas "(Incluído/Redação dada pela Lei ...) (Vigência)" separadas do marcador em parágrafo próprio (causava fusão ERRADA: "Seção I" fundia com a anotação órfã em vez do título real "Disposições Gerais"); e "P A R T E GERAL"/"P A R T E ESPECIAL" (letras espaçadas no PDF de origem) não eram reconhecidas. **Corrigidos os cinco casos.**
5. **Posicionamento do índice** — `mark_final_index` inseria `# ÍNDICE` logo após o último artigo, deixando o segundo signatário (Aloysio Nunes Ferreira Filho) e a nota de publicação DENTRO do índice. **Corrigido** ancorando no parágrafo que contém a palavra literal "ÍNDICE" (título terminal real, presente no próprio texto de origem como link de navegação) e inserindo o cabeçalho imediatamente depois dele.

### 8.2 Verificação final da segunda rodada

- Suíte completa: **251 passed**, 0 falhas (era 241 ao final da primeira rodada; +10 testes novos).
- 186 marcadores `[[Pág. N]]` sequenciais preservados.
- Comparação letra-a-letra (todo caractere que não é letra ou "º" removido, incluindo espaços/dígitos/pontuação) entre o estado pré-rodada-2 e pós-rodada-2 do Código Civil: soma de letras+ordinais idêntica (503.729 = 503.729); a única diferença posicional encontrada corresponde exatamente às trocas "o"→"º" já auditadas nas correções 2 e 3 — nenhuma perda, duplicação ou alteração de conteúdo jurídico.
- AINTARESP, REsp e Inf0024E: **0 tokens alterados** nas correções 1, 2, 3 e 5 (nenhum desses padrões existe nesses arquivos); **0 cabeçalhos novos** criados pela correção 4 (bloqueio explícito do objetivo, confirmado).
- Contagem de cabeçalhos por nível no Código Civil (antes → depois da correção 4): H1 1→4, H2 8→9, H3 42→43, H4 175→176, H5 152→153, H6 15→15 (só adições correspondentes aos marcadores recém-reconhecidos, sem duplicatas).
- `openspec validate improve-markdown-cleanup-structuring --strict` → válido (reexecutado ao final).

### 8.3 Arquivos alterados nesta rodada

- `src/pipeline_juridico/cleaner.py`: correção pontual em `recompose_native_paragraphs`; nova função `join_symbol_across_page_break`; duas regras novas em `normalize_legal_symbols`; extensão de `_LEGISLATIVE_MARKER_PATTERN` e `build_legislative_headings`; correção de ancoragem em `mark_final_index`.
- `src/pipeline_juridico/converter.py`: uma chamada nova (`join_symbol_across_page_break`).
- `tests/test_cleaner.py`: +10 testes novos.

### 8.4 Comandos de reprodução (iguais aos da seção 6, repetidos para conveniência)

```bash
uv sync
uv run pytest tests/ -q
uv run converter-juridico input/L10.406_CC_2002.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/AINTARESP_1462304-PA.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/REsp_1704551-SP.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/Inf0024E.pdf --no-ocr --overwrite --log-level WARNING
openspec validate improve-markdown-cleanup-structuring --strict
```

## 9. Terceira rodada de validação (defeitos de estrutura final e símbolos)

Uma terceira validação humana, a partir de geometria real do PDF (página física 177), identificou 4 defeitos adicionais. Diagnosticados e corrigidos com o mesmo processo (teste primeiro, menor alteração, verificação independente).

### 9.1 Causas raiz e correções

1. **"P A R T E ESPECIAL" colado ao final do Art. 232** — o marcador letra-espaçado ficava unido ao parágrafo do artigo (mesma folga vertical abaixo do limiar de junção), então nunca chegava à pré-passada letra-espaçada de `build_legislative_headings` (que exige o parágrafo inteiro ser só o marcador). **Corrigido** com uma nova pré-passada que detecta e separa um marcador letra-espaçado colado ao FINAL de um parágrafo maior, antes da construção de cabeçalhos, sem dividir texto maiúsculo comum.
2. **Blocos finais da lei fundidos** — Art. 2.046, linha de promulgação, os dois signatários, nota de publicação e "ÍNDICE" terminal formavam uma cadeia de parágrafos unidos (gaps geométricos de 9,8–10,9pt, todos abaixo do limiar de 1,2×). **Corrigido** com três novas exceções em `recompose_native_paragraphs`, ancoradas em padrões de CONTEÚDO genéricos (fórmula de promulgação "Cidade, DD de mês de AAAA"; frase padrão "não substitui o publicado"; palavra isolada "ÍNDICE") — não em nomes próprios. A separação entre os dois signatários já ocorria por acaso graças à salvaguarda `native_label_pattern` existente.
3. **Índice terminal duplicado** — com o "ÍNDICE" agora isolado (correção 2), `mark_final_index` inseria um `# ÍNDICE` novo AO LADO do "ÍNDICE" solto, em vez de substituí-lo. **Corrigido**: agora substitui o parágrafo "ÍNDICE" isolado (quando existe) pelo cabeçalho, em vez de inserir ao lado. O "ÍNDICE" válido da página 1 permanece como texto comum (fora da região de busca, que só olha depois do último artigo).
4. **Símbolos residuais** — "Lei n º" (variante de espaço não coberta antes), ordinais de data ancorados por nome de mês ("N o de janeiro"→"Nº de janeiro", cobrindo os 12 meses) e ancorados pela fórmula constitucional ("N o da Independência"/"N o da República"), e "191 6" no Art. 2.040 (já confirmado na rodada 2 como artefato de extração do PyMuPDF; agora autorizado e corrigido, com regra estritamente ancorada ao contexto de data "de \<mês\> de NNN N"). **Corrigidos os quatro casos.** O ordinal "1 o Ofício da Capital" (sem âncora de mês/Independência/República) permanece intencionalmente intocado — teste da rodada 1 ainda passa.

### 9.2 Verificação final da terceira rodada

- Suíte completa: **260 passed**, 0 falhas (era 251 ao final da segunda rodada; +9 testes novos, 1 teste da rodada 1 atualizado para refletir a expansão de escopo autorizada dos ordinais de promulgação — o exemplo do "Ofício" permanece intocado e ainda passa).
- 186 marcadores `[[Pág. N]]` sequenciais preservados.
- Reconciliação exata de tokens no Código Civil entre o estado pré-rodada-3 e pós-rodada-3: removidos `1`×7, `o`×9, `6`×1, `114`×1, `181`×1, `191`×1, `n`×12, `º`×12; adicionados `nº`×12, `1º`×7, `1916`×1, `181º`×1, `114º`×1 — cada mudança corresponde exatamente a uma das quatro correções, nenhuma sobra inexplicada.
- Comparação letra-a-letra confirma: nenhuma perda de conteúdo jurídico; a única redução de conteúdo (-6 letras) corresponde exatamente à remoção do "ÍNDICE" duplicado (correção 3), não a texto legal.
- AINTARESP, REsp e Inf0024E: **0 mudanças** em todas as quatro correções (nenhum desses padrões existe nesses arquivos); **0 cabeçalhos novos**.
- Idempotência verificada em cada subtarefa (reaplicar a limpeza duas vezes produz o mesmo resultado).

### 9.3 Arquivos alterados nesta rodada

- `src/pipeline_juridico/cleaner.py`: nova pré-passada em `build_legislative_headings` (marcador letra-espaçado colado); três novas exceções em `recompose_native_paragraphs` (promulgação, nota de publicação, ÍNDICE isolado); correção de substituição em `mark_final_index`; quatro regras novas em `normalize_legal_symbols`.
- `tests/test_cleaner.py`: +9 testes novos, 1 teste atualizado (escopo de ordinais de promulgação).

### 9.4 Comandos de reprodução (iguais aos da seção 6)

```bash
uv sync
uv run pytest tests/ -q
uv run converter-juridico input/L10.406_CC_2002.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/AINTARESP_1462304-PA.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/REsp_1704551-SP.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/Inf0024E.pdf --no-ocr --overwrite --log-level WARNING
openspec validate improve-markdown-cleanup-structuring --strict
```

## 10. Casos encaminhados para revisão humana (atualizado após a terceira rodada)

Os casos "191 6" e os ordinais de promulgação ("181 o da Independência"/"114 o da República"), pendentes desde a segunda rodada, foram **resolvidos** nesta terceira rodada (ver seção 9 acima). Casos que permanecem:

1. **Ordinal solto sem âncora de mês/Independência/República** (Código Civil): `"...no 1 o Ofício da Capital do Estado..."` continua com o "o" não normalizado — não há palavra-chave ou contexto de data inequívoco por perto (não é "de \<mês\>" nem "da Independência/República"), e generalizar mais arrisca a "substituição global de toda letra 'o' após números" explicitamente proibida. Testado e documentado como comportamento intencional.
2. **Cabeçalho/rodapé técnico do AINTARESP e do REsp** (ex. "Superior Tribunal de Justiça" repetido, bloco de assinatura eletrônica com códigos de controle, `"Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019"` repetido): nenhum corresponde às 4 categorias autorizadas de remoção de margem e por isso permanece intocado, por decisão conservadora.
3. **Segunda ocorrência de "Seção Única" dentro do índice do Código Civil**: aparece como `"Seção Única Da Caracterização"`, já fundida em um único parágrafo pela recomposição geométrica de parágrafos — não é um par marcador+título separado, então a correção da subtarefa 7.4 (escopada a pares marcador+título) não se aplica a essa ocorrência específica. Nenhuma perda de conteúdo; permanece como texto comum dentro do índice.

## 11. Quarta rodada de validação (grupo 9 — defeito R01: referência estrutural em prosa bloqueando junção)

Um novo objetivo (rotulado "R01") pediu recomposição determinística de linhas fragmentadas, citando 3 casos reais do Código Civil (Art. 44 §2º, Art. 593, Art. 1.458). Diagnosticados e corrigidos com o mesmo processo (mapeamento → teste primeiro → menor correção → verificação independente), em duas iterações porque a primeira correção introduziu uma regressão detectada pela varredura de resíduos do próprio orquestrador.

### 11.1 Causas raiz e correções

1. **Referência em prosa tratada como cabeçalho** — em `recompose_native_paragraphs`, `formal_structure_pattern` bloqueava a junção sempre que a linha seguinte COMEÇASSE com PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO (maiúscula inicial), mesmo quando a linha era só o final de uma frase citando o termo em prosa: "...são objeto do Livro II da" + "Parte Especial deste Código. (Incluído pela Lei nº 10.825, de 22.12.2003)" (Art. 44 §2º); "...disposições deste" + "Capítulo." (Art. 593); "...pela presente" + "Seção." (Art. 1.458). Confirmadas exatamente 3 ocorrências reais no corpo do texto (as ~380 demais correspondências do padrão no documento são entradas legítimas do ÍNDICE final). **Corrigido** restringindo o bloqueio a quando a linha seguinte for, ela própria, um marcador nu (`bare_structure_pattern`) ou inteiramente maiúscula.
2. **Regressão intermediária: entradas do índice mescladas** — a correção acima não reconhecia entradas do ÍNDICE no formato "Marcador + numeral romano/qualificador + Título em Title Case" (ex. "Seção I Da Curadoria dos Bens do Ausente"), que não são nuas nem totalmente maiúsculas — 158 entradas foram engolidas em 37 parágrafos indevidamente mesclados. Detectado pela varredura de resíduos do orquestrador antes do fechamento do grupo. **Corrigido** com `qualified_structure_pattern` (marcador imediatamente seguido de numeral romano — com sufixo opcional "-A" — ou qualificador ÚNICO/ÚNICA/COMPLEMENTAR), adicionada como mais uma condição de bloqueio, independente do que vier depois na linha.

### 11.2 Verificação final da quarta rodada

- Suíte completa: **271 passed**, 0 falhas (era 260 ao final da terceira rodada; +11 testes novos: 3 positivos + 4 negativos na primeira iteração, 4 parametrizados na segunda).
- 186 marcadores `[[Pág. N]]` sequenciais preservados no Código Civil; idempotência confirmada (duas reconversões independentes produzem `output/L10.406_CC_2002.md` byte-idêntico).
- Os 3 casos do objetivo corrigidos, mais um caso adicional generalizado corretamente (Art. 1.368-F, mesmo padrão "disposições deste Capítulo.").
- Entradas de índice indevidamente mescladas: 37 parágrafos (158 entradas) → 1 parágulo (2 entradas) remanescente, que é um artefato de extração do PyMuPDF pré-existente (caractere "&gt;" literal entre "Seção II Da Ocupação" e "Seção III Do Achado do Tesouro"), já presente na reconversão de linha de base antes de qualquer alteração desta rodada — não causado pela lógica de junção, fora de escopo (análogo ao "191 6" da segunda rodada).
- Casos negativos revalidados sem regressão: 202 transições artigo→cabeçalho real; 1.092→1.094 pares de artigos consecutivos (aumento esperado — os 2 casos corrigidos passam a ficar adjacentes ao artigo seguinte); fechamento da lei (Art. 2.046 → promulgação → assinaturas → nota de publicação → `# ÍNDICE`) intacto.
- AINTARESP, REsp e Inf0024E: reconvertidos sem erro, 0 `[[TEXTO ILEGÍVEL]]`, contagem de páginas inalterada.
- `openspec validate improve-markdown-cleanup-structuring --strict` → válido (reexecutado ao final).

### 11.3 Arquivos alterados nesta rodada

- `src/pipeline_juridico/cleaner.py`: duas condições novas em `recompose_native_paragraphs` (checagem de marcador nu/maiúsculo; `qualified_structure_pattern` para marcador+numeral/qualificador).
- `tests/test_cleaner.py`: +11 testes novos (3 positivos, 4 negativos de cobertura, 4 parametrizados para o caso de índice).

### 11.4 Comandos de reprodução (iguais aos da seção 6)

```bash
uv sync
uv run pytest tests/ -q
uv run converter-juridico input/L10.406_CC_2002.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/AINTARESP_1462304-PA.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/REsp_1704551-SP.pdf --no-ocr --overwrite --log-level WARNING
uv run converter-juridico input/Inf0024E.pdf --no-ocr --overwrite --log-level WARNING
openspec validate improve-markdown-cleanup-structuring --strict
```

## 12. Casos encaminhados para revisão humana (atualizado após a quarta rodada)

Além dos itens já listados na seção 10 (ainda pendentes: ordinal solto sem âncora, cabeçalho/rodapé técnico do AINTARESP/REsp, "Seção Única" já fundida no índice), adiciona-se:

4. **"Seção II Da Ocupação >Seção III Do Achado do Tesouro"** (índice do Código Civil): caractere "&gt;" literal entre duas entradas de índice, presente desde a linha de base original (antes de qualquer alteração desta ou de rodadas anteriores) — artefato de extração do PyMuPDF (possível link/anotação malformado), não causado pela lógica de recomposição de parágrafos. Fora de escopo do defeito R01; registrado para eventual investigação futura da camada de extração.

## 13. Estado da mudança

Todas as subtarefas 0–9.5 de `tasks.md` estão marcadas `[x]`. Falta apenas o arquivamento (`openspec archive`), que este orquestrador não deve executar sem aprovação humana explícita, conforme `AGENTS.md`.
