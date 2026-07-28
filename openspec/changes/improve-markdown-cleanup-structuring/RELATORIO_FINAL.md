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

## 9. Casos encaminhados para revisão humana (atualizado após a segunda rodada)

Os casos 2 ("P A R T E" com letras espaçadas) e 4 ("LIVRO COMPLEMENTAR") listados na seção 7 da primeira rodada foram **resolvidos** nesta segunda rodada e removidos desta lista. Casos que permanecem, mais um novo caso investigado:

1. **Ordinais soltos sem âncora jurídica** (Código Civil): `"...no 1 o Ofício da Capital do Estado..."` e `"...181 o da Independência e 114 o da República."` continuam com o "o" não normalizado. Corrigir exigiria uma heurística sem palavra-chave anterior, o que a instrução do projeto proíbe explicitamente ("não fazer substituição global de toda letra 'o' após números"). Testado e documentado como comportamento intencional.
2. **"191 6" no Art. 2.040** (Código Civil): investigado diretamente contra o PDF de origem — confirmado como artefato de extração do próprio PyMuPDF (presente até em `page.get_text("text")` bruto, sem qualquer processamento do pipeline), ocorrência única em todo o corpus. Não corrigido nesta rodada: uma regra genérica para "juntar números partidos por um espaço" seria frágil e arriscada para um único caso conhecido: poderia colidir com incisos, valores ou outras numerações legítimas em pontos não testados do corpus. Recomenda-se decisão humana explícita antes de qualquer normalização aqui.
3. **Cabeçalho/rodapé técnico do AINTARESP e do REsp** (ex. "Superior Tribunal de Justiça" repetido, bloco de assinatura eletrônica com códigos de controle, `"Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019"` repetido): nenhum corresponde às 4 categorias autorizadas de remoção de margem e por isso permanece intocado, por decisão conservadora.
4. **Segunda ocorrência de "Seção Única" dentro do índice do Código Civil**: aparece como `"Seção Única Da Caracterização"`, já fundida em um único parágrafo pela recomposição geométrica de parágrafos (porque no índice o espaçamento vertical entre marcador e título é menor que no corpo) — não é um par marcador+título separado, então a correção da subtarefa 7.4 (por design, escopada a pares marcador+título) não se aplica a essa ocorrência específica. Nenhuma perda de conteúdo; permanece como texto comum dentro do índice.

## 10. Estado da mudança

Todas as subtarefas 0–7.7 de `tasks.md` estão marcadas `[x]`. Falta apenas o arquivamento (`openspec archive`), que este orquestrador não deve executar sem aprovação humana explícita, conforme `AGENTS.md`.
