## Why

A validação supervisionada arquivada (`validate-supervised-ocr-testamento-publico`, 2026-08-12) identificou, mas não isolou com evidência independente nem avaliou blast radius formal, um defeito sistemático na rota `hibrido`/OCR: cada uma das 4/4 páginas de `012-015-Testamento Publico.pdf` traz, após `[End OCR]*`, ~209 linhas de ruído de caracteres isolados — o mesmo carimbo de autenticação e-SAJ vertical já lido corretamente pelo PyMuPDF, mas fragmentado pelo pacote de terceiros `markitdown-ocr`. Esta mudança é **exclusivamente diagnóstica**: reproduz a causa raiz de forma independente (sem confiar apenas no relatório anterior), rastreia PyMuPDF → pdfplumber → `markitdown-ocr` → composição final, e avalia formalmente critérios de correção candidatos contra o corpus de controle completo (8 PDFs, 270 páginas). Não implementa código, não cria testes de produção, não executa OCR/LLM novo, não altera prompt/modelo/provider, não arquiva e não faz push.

## Pré-voo (evidência completa em `design.md`)

- `git status --short`: limpo. HEAD `b30771d`. `uv run pytest tests/`: 364/364 passando. `openspec validate --all --strict`: 1 passed (spec), 1 failed (esta própria mudança, esperado — diagnóstica, sem deltas, mesmo padrão dos precedentes arquivados).
- Nenhuma chamada de OCR/LLM feita nesta investigação. Toda evidência via PyMuPDF (`page.get_text("dict")`), pdfplumber (`page.chars`, `page.images`) e leitura direta do código-fonte instalado de `markitdown_ocr`, reproduzindo localmente o algoritmo de agrupamento de linhas.

## Conclusão (resumo — evidência completa em `design.md`)

**A) CRITÉRIO SEGURO ENCONTRADO.**

- **Estrutura do texto vertical:** 2 linhas verticais (`dir=(0,-1)`, Helvetica) por página, ~174 e ~202 caracteres, **cada uma ocorrendo uma única vez** (sem duplicação geométrica) — diferente do achado já corrigido `fix-rotated-digital-signature-noise` (que exigia 2 cópias sobrepostas na rota `texto_nativo`).
- **Primeiro estágio responsável:** o agrupamento de caracteres em "linhas" por proximidade de coordenada Y (limiar fixo de 2pt), interno a `markitdown_ocr/_pdf_converter_with_ocr.py::PdfConverterWithOCR.convert()` (linhas 199–227). `page.chars` (pdfplumber) já está correto; o defeito é exclusivamente deste agrupamento heurístico, que assume texto horizontal e nunca verifica direção de escrita.
- **Causa raiz confirmada por reprodução local** (sem OCR real): aplicando o algoritmo exato do plugin aos 383 caracteres nativos da página 1, obtêm-se 228 fragmentos (115 de 1 caractere, 105 de 2–9 caracteres) — concatenados e invertidos, reconstroem o mesmo texto das 2 linhas verticais já lidas corretamente pelo PyMuPDF.
- **Origem do ruído:** B) texto nativo residual — confirmado por leitura de código, o texto OCR (resposta LLM) e os fragmentos nativos são calculados por mecanismos totalmente independentes, apenas intercalados por posição Y na composição final.
- **Combinação OCR+nativo:** reproduzida e confirmada byte a byte — 1 imagem por página (`y_pos≈0`), 100% dos fragmentos de texto nativo ordenam-se depois dela, explicando o padrão observado (OCR legível, depois `[End OCR]*`, depois todo o ruído).
- **Critério recomendado (Candidato E, combinação de sinais):** fragmentos posicionados estritamente após `[End OCR]*` **e** cujo texto concatenado corresponde geometricamente (sobreposição de caracteres) a uma linha não horizontal já lida por `page.get_text("dict")` na mesma página. Nenhum sinal isolado (direção sozinha, posição sozinha, contagem de caracteres sozinha) é seguro — cada um foi avaliado e descartado como critério único, pelas mesmas razões já documentadas no precedente arquivado para a rota `texto_nativo`.
- **Blast radius:** no corpus de controle completo (8 PDFs, 270 páginas), a rota `hibrido`/`ocr_integral` — único ramo onde `markitdown-ocr`/`pdfplumber` processa a página — ocorre em **exatamente 4 páginas, todas já no escopo deste diagnóstico**. As 266 páginas `texto_nativo` restantes (incluindo os 78 blocos/linhas verticais legítimos de `100-106-DECISÃO.pdf`, `001-007-Petição Inicial.pdf` e `086-096-CONTESTAÇÃO...pdf`) nunca entram no ramo de código onde a correção atuaria — blast radius zero nelas, por construção do ponto de intervenção, não por ausência de teste.
- **Ponto de intervenção recomendado:** `converter.py::convert_document`, ramo `hibrido`/`ocr_integral`, imediatamente após obter `raw_content` do OCR — sem modificar o pacote de terceiros, sem tocar a rota `texto_nativo`.
- **Limitação registrada:** o corpus de controle não tem uma segunda página `hibrido`/`ocr_integral` real para validar a generalização do critério — mitigada pela exigência de corroboração geométrica (não apenas posicional) no critério recomendado; uma implementação futura deve cobrir isso com fixtures sintéticas dedicadas.
- **Decisão em aberto para a implementação futura:** descartar o texto residual corroborado ou substituí-lo pela reconstrução geométrica limpa do PyMuPDF (recomendado, por consistência com `fix-rotated-digital-signature-noise` e para não perder o valor probatório do carimbo e-SAJ).

## Capabilities

### New Capabilities
(nenhuma — mudança diagnóstica, não implementa)

### Modified Capabilities
(nenhuma — mudança diagnóstica, não implementa; nenhuma configuração de OCR/roteamento/cleaner foi alterada)

## Impact

- Código: nenhum. `src/`, `tests/`, dependências, prompt, modelo, provider, cleaner, roteamento e arquitetura não foram tocados.
- Nenhuma chamada de OCR/LLM foi feita.
- Nenhum arquivo canônico (`output/`, `logs/`, corpus de `input/`) foi alterado ou reconvertido.
- Esta mudança permanece ativa (não arquivada), como candidata a uma futura mudança de implementação dedicada (Ponto C / Candidato E acima), aguardando aprovação humana explícita para avançar de diagnóstico para TDD + implementação.
