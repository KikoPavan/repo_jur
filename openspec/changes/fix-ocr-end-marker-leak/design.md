# Diagnóstico — vazamento do marcador interno `[End OCR]*`

Mudança **exclusivamente diagnóstica** (instrução via `/goal`: "SOMENTE DIAGNÓSTICO"). Não implementa código, não cria testes de produção, não executa OCR/LLM novo, não altera prompt/modelo/provider, não arquiva e não faz push.

## Contexto

Achado já registrado (severidade baixa) em `validate-supervised-ocr-testamento-publico` (arquivada, 2026-08-12) e reafirmado em `fix-ocr-rotated-text-fragmentation` (arquivada, 2026-08-14): o marcador interno `*[Image OCR]...[End OCR]*` do plugin de terceiros `markitdown-ocr` vaza para o Markdown final publicado nas 4 páginas `hibrido` de `input/processos_auditoria/012-015-Testamento Publico.pdf` — o único caso `hibrido`/`ocr_integral` de todo o corpus de controle. Este diagnóstico isola a causa raiz do vazamento (por que `[End OCR]*` sobrevive quando praticamente todo o resto do artefato de formatação do plugin não sobrevive), rastreia o fluxo completo, avalia a interação com a correção já arquivada de `fix-ocr-rotated-text-fragmentation`, e compara três pontos de intervenção candidatos — sem implementar nada.

Toda a investigação foi feita por leitura de código instalado (`markitdown_ocr`, `markitdown`), leitura de `src/pipeline_juridico/`, leitura de artefatos já arquivados (Markdown real produzido em `validate-supervised-ocr-testamento-publico`), leitura de testes existentes, e reprodução local determinística (scripts no scratchpad da sessão, fora do repositório) usando texto sintético equivalente ao formato real do plugin — **nenhuma chamada de OCR/LLM foi feita**.

## ETAPA 1 — Rastreamento: origem, representação, ocorrências, dependências

### Origem exata

`[End OCR]*` é produzido inteiramente pelo pacote de terceiros `markitdown-ocr` (instalado em `.venv/lib/python3.12/site-packages/markitdown_ocr/`), nunca por `src/pipeline_juridico/`. Três pontos de emissão em `_pdf_converter_with_ocr.py`, todos com a mesma representação literal:

| Linha | Contexto | f-string exata |
| --- | --- | --- |
| 275 | `PdfConverterWithOCR.convert()`, ramo com imagens detectadas na página (usado pela rota `hibrido` do pipeline) | `f"\n\n*[Image OCR]\n{ocr_text}\n[End OCR]*\n"` |
| 374 | `_ocr_full_pages()` (fallback de página inteira digitalizada, pdfplumber) | `f"*[Image OCR]\n{text}\n[End OCR]*"` |
| 407 | `_ocr_full_pages()` (fallback de página inteira, ramo PyMuPDF quando pdfplumber falha) | `f"*[Image OCR]\n{text}\n[End OCR]*"` |

Representação sempre idêntica byte a byte: `[End OCR]*` (colchete, "End OCR", colchete, asterisco — o asterisco de fechamento de itálico Markdown do bloco `*[Image OCR]...[End OCR]*`, que nunca é interpretado como itálico porque o conteúdo entre os dois marcadores contém quebras de linha). O caso real do Testamento usa a linha 275 (rota `hibrido`, imagem detectada por página); as linhas 374/407 (`ocr_integral`, página inteira digitalizada sem nenhum texto nativo residual) não têm nenhuma ocorrência no corpus de controle atual (nenhuma página do corpus é `ocr_integral`, ver ETAPA 4).

### Pode ocorrer mais de uma vez por página?

Sim, estruturalmente: o plugin insere um bloco `*[Image OCR]\n...\n[End OCR]*` **por imagem detectada na página** (linha 275, dentro do loop `for img_info in images_on_page`). Uma página com múltiplas imagens produziria múltiplos marcadores. **Não observado no corpus atual** — as 4 páginas do Testamento têm exatamente 1 imagem cada (reconfirmado nesta investigação por leitura do diagnóstico já arquivado de `fix-ocr-rotated-text-fragmentation`, que reproduziu isso localmente sem OCR real). Nenhuma página `ocr_integral` existe no corpus (ver ETAPA 4), então as linhas 374/407 (que também só produzem 1 marcador por página, pois operam sobre a página inteira como uma única "imagem") nunca são exercitadas.

### Algum código atual depende dele?

Sim, um único ponto: `src/pipeline_juridico/converter.py::_split_ocr_tail` (linha 301-309):

```python
def _split_ocr_tail(raw_content, marker="[End OCR]*"):
    idx = raw_content.rfind(marker)
    if idx == -1:
        return None
    split_at = idx + len(marker)
    return raw_content[:split_at], raw_content[split_at:]
```

Usa `rfind` — localiza a **última** ocorrência do marcador no texto recebido. Se houvesse múltiplas ocorrências na mesma página, apenas o texto após a última seria tratado como "cauda" candidata a substituição geométrica; ocorrências anteriores ficariam embutidas em `head` (preservadas verbatim, nunca reexaminadas). É chamado por `_replace_fragmented_vertical_residual_in_text` (linha 389-407), que é a lógica pura da correção já arquivada `fix-ocr-rotated-text-fragmentation`, orquestrada por `_replace_fragmented_vertical_residuals_in_document` (linha 414-445) dentro de `convert_document`.

Nenhum outro módulo depende do marcador: `cleaner.py` (busca confirmada — nenhuma referência), `router.py`, `engines.py` (usa sentinelas próprias e distintas: `OCR_NO_TEXT_MARKER`, `OCR_PAGE_ERROR_MARKER`, `OCR_FATAL_ERROR_MARKER`, nenhuma relacionada a `[End OCR]*`), `validator.py`, `report.py` — nenhum menciona `[End OCR]*`.

### Quando sua função estrutural termina?

No momento em que `_replace_fragmented_vertical_residuals_in_document` termina de processar o documento inteiro (linha 615-619 de `convert_document`, dentro do `raw_markdown`). A partir daí, `[End OCR]*` nunca mais é lido, buscado ou usado como referência posicional por nenhum código deste pipeline — sua permanência na string a partir desse ponto é puramente incidental (não removido, não porque é necessário, mas porque nada o remove).

## Descoberta empírica adicional: por que só `[End OCR]*` "vaza" e não `*[Image OCR]`/`## Page N`

Ao comparar o Markdown real arquivado (`validate-supervised-ocr-testamento-publico/audit_output/output/012-015-Testamento Publico.md`) com o código-fonte do plugin, uma discrepância aparente surgiu: o plugin sempre emite um cabeçalho `## Page N` (linha 189 de `_pdf_converter_with_ocr.py`, incondicional) e o marcador de abertura `*[Image OCR]` — nenhum dos dois aparece no Markdown final publicado, apenas `[End OCR]*` aparece. Isso foi investigado e reproduzido localmente (script no scratchpad, sem OCR real), usando texto sintético no formato exato do plugin, através de `remove_repetitive_margins` (`cleaner.py`) — a mesma função já usada pela correção arquivada `fix-repeated-header-cross-page-fusion`.

**Causa identificada:** `isolated_page_workspace` (`inspector.py`) processa cada página como um PDF de página única isolada. Como consequência, o loop interno do plugin (`for page_num, page in enumerate(pdf.pages, 1)`) sempre reinicia em `page_num=1` para cada página real do documento — ou seja, **`## Page 1` é byte-idêntico em todas as páginas `hibrido`/`ocr_integral` do documento**, independentemente do número real da página. O mesmo vale para `*[Image OCR]`, que é um literal fixo. Como essas duas strings são a **primeira linha de conteúdo não vazia** de cada página elegível, e são idênticas em 100% das páginas do Testamento (4/4, acima do limiar de 60% de `remove_repetitive_margins`), o mecanismo de detecção verbatim já existente (`remove_verbatim_margins`, adicionado por `fix-repeated-header-cross-page-fusion`, 2026-08-06) as remove como se fossem um cabeçalho institucional repetido — **efeito colateral não intencional de um mecanismo genérico, não uma supressão desenhada para este marcador**.

`[End OCR]*`, ao contrário, **não é a primeira nem a última linha de conteúdo** da página quando existe qualquer resíduo após ele (o ruído de fragmentação característico deste caso, ou — após a correção já arquivada — o texto vertical reconstruído). Por estar embutido no meio do conteúdo, fica fora do escopo de `remove_repetitive_margins`, que só examina a primeira e a última linha de cada página. **Reproduzido e confirmado empiricamente**: em um segundo teste sintético sem nenhum resíduo após o marcador (cenário hipotético, não observado no corpus real), `[End OCR]*` torna-se a última linha de conteúdo e É removido pelo mesmo mecanismo verbatim — confirmando que a causa do vazamento é estritamente posicional (meio de conteúdo vs. início/fim), não uma imunidade do marcador em si.

**Implicação para qualquer correção futura:** a supressão atual de `## Page N`/`*[Image OCR]` é um efeito colateral frágil, não uma salvaguarda desenhada — só funciona porque o Testamento é 100% `hibrido` (4/4 páginas). Em um documento hipotético com maioria de páginas `texto_nativo` e uma minoria `hibrido`/`ocr_integral`, esse efeito colateral não atingiria o limiar de 60% e **todos os artefatos do plugin vazariam**, não apenas `[End OCR]*`. Isso não muda o escopo desta mudança (que trata exclusivamente de `[End OCR]*`, por instrução explícita), mas é evidência relevante de que depender de `remove_repetitive_margins` para este propósito seria arquitetura acidental, não desenhada — reforça a recomendação por um mecanismo dedicado e explícito (ver ETAPA 3).

Também existe hoje um teste unitário que **fixa o comportamento atual de preservação** desses marcadores: `tests/test_cleaner.py::test_clean_markdown_preserves_ocr_delimiters` afirma que `clean_markdown` (chamada isoladamente, sem o contexto multi-página de `remove_repetitive_margins`) preserva `*[Image OCR]...[End OCR]*` verbatim. Qualquer correção futura que remova o marcador **dentro de `clean_markdown`** entraria em conflito direto com esse teste existente e exigiria atualizá-lo; uma correção que remova o marcador em um ponto **fora de `clean_markdown`** (ver Candidato A, ETAPA 3) não toca esse teste.

## ETAPA 2 — Interação com correções existentes

- **`_split_ocr_tail`:** único consumidor real do marcador (ver ETAPA 1). Qualquer remoção do marcador **antes** deste consumidor rodar quebra silenciosamente `fix-ocr-rotated-text-fragmentation` — `rfind` retornaria `-1`, `_split_ocr_tail` retornaria `None`, e `_replace_fragmented_vertical_residual_in_text` devolveria o conteúdo inalterado, deixando o ruído de fragmentação (a razão original da correção arquivada) reaparecer silenciosamente. **Confirmado por reprodução local**: reproduzir o marcador ausente antes da chamada de `_split_ocr_tail` faz a substituição geométrica nunca disparar.
- **Reconstrução do residual vertical (`_replace_fragmented_vertical_residual_in_text`):** depende do marcador apenas como ponto de corte (`_split_ocr_tail`); depois de obter `head`/`tail`, nunca mais examina o texto do marcador em si. O `head` retornado por essa função **inclui o marcador** (o `split_at` de `_split_ocr_tail` é calculado como `idx + len(marker)`), portanto qualquer remoção do marcador deve acontecer **depois** que esta função já rodou para a página, nunca antes.
- **`remove_repetitive_margins`:** já demonstrado (ver acima) que não depende do marcador nem o teria como alvo intencional; opera apenas na primeira/última linha de conteúdo por página, usando padrões regex de data/hora/URL/contador de página ou correspondência verbatim exata — nenhum dos dois mecanismos foi escrito pensando em `[End OCR]*`. É chamada **antes** de `_replace_fragmented_vertical_residuals_in_document` em `convert_document` (linha 614 antes de 615), então qualquer correção futura para `[End OCR]*` que rode depois desse ponto na pipeline nunca interage com `remove_repetitive_margins` na mesma execução (a ordem já é fixa).
- **Composição dos marcadores `[[Pág. N]]`:** `_replace_fragmented_vertical_residuals_in_document` já reutiliza `_PAGE_MARKER_SPLIT_PATTERN`/`_PAGE_MARKER_NUMBER_PATTERN` para segmentar o documento composto por página e restringir a atuação às páginas elegíveis (`method in (hibrido, ocr_integral)`, via `blocks`). Qualquer correção futura para `[End OCR]*` pode reutilizar exatamente esse mesmo mecanismo de segmentação, sem necessidade de reconstruir lógica de fatiamento por página. Os próprios marcadores `[[Pág. N]]`/`<!-- método: ... -->` nunca contêm nem colidem com o texto `[End OCR]*`.

**Conclusão da ETAPA 2:** existe exatamente um ponto de não-retorno — a chamada a `_replace_fragmented_vertical_residuals_in_document` (linha 615-619 de `convert_document`). Qualquer remoção do marcador deve acontecer estritamente **depois** desse ponto.

## ETAPA 3 — Critérios candidatos

| Candidato | Ponto exato | Acoplamento | Risco de remover texto legítimo | Impacto sobre o residual vertical | Blast radius | Idempotência | Precisa reconhecer o marcador por texto literal? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **A — remover imediatamente após consumir a função interna** | Em `convert_document`, logo após a chamada a `_replace_fragmented_vertical_residuals_in_document` (linha 619) e antes de `join_symbol_across_page_break` (linha 620); reaproveitando a mesma segmentação por `[[Pág. N]]` e a mesma lista `eligible_numbers` (método `hibrido`/`ocr_integral`) já usada por essa função | Mínimo — nova função pequena, mesmo módulo (`converter.py`), reaproveita segmentação já existente, não toca `cleaner.py` | Nenhum identificado: a remoção ocorre estritamente **depois** que `_split_ocr_tail` já consumiu o marcador para localizar a cauda; o marcador em si nunca faz parte do conteúdo substantivo (nem da transcrição OCR, nem da reconstrução geométrica) | Nenhum — a reconstrução já terminou; remover o marcador não altera `head` nem a reconstrução, apenas descarta a substring do marcador | Confinado às páginas `hibrido`/`ocr_integral` (4 de 270 no corpus atual); zero páginas `texto_nativo` tocadas, por construção (mesma restrição de elegibilidade já usada pela correção arquivada) | Sim — segunda execução sobre um documento sem o marcador é no-op (nenhuma ocorrência para remover) | Sim, mas apenas o literal já usado por `_split_ocr_tail` (`[End OCR]*`), reaproveitando a mesma constante — nenhum sinal novo |
| **B — remover no estágio final de composição da página OCR** (por página, ao finalizar `raw_content`/`content`, linha ~574-580, antes de `blocks.append`/`compose_document`) | Alto — mexe no ponto onde `content` é atribuído por página, antes de qualquer composição do documento | Nenhum risco de conteúdo legítimo isoladamente, mas **quebra `fix-ocr-rotated-text-fragmentation`**: `_split_ocr_tail` roda depois, sobre o documento já composto — sem o marcador, `rfind` retorna `-1`, a substituição geométrica nunca dispara, e o ruído de fragmentação (a razão original daquela correção) reaparece silenciosamente | **Regressivo, confirmado por reprodução local** — anula a correção já arquivada | Mesmo escopo de páginas, mas com efeito colateral que invalida uma correção já validada e arquivada | Não avaliável de forma útil — já é rejeitado pela quebra de dependência | Precisaria do mesmo literal, mas no ponto errado |
| **C — pós-processar o documento final** (após `clean_markdown`, linha 624, ou dentro de `clean_markdown`) | Médio — se implementado como nova função chamada após `clean_markdown`, acoplamento baixo; se implementado dentro de `clean_markdown`, conflita com o teste existente `test_clean_markdown_preserves_ocr_delimiters` (que passaria a falhar e precisaria ser atualizado como parte da futura implementação) | Mesma ausência de risco que A (marcador já não tem função a essa altura), mas o marcador sobrevive por mais etapas do pipeline (`join_symbol_across_page_break`, `normalize_legal_symbols`, `build_legislative_headings`, `mark_final_index`, `clean_markdown`) sem necessidade — nenhuma dessas etapas foi verificada linha a linha nesta investigação por não ser o caminho mais direto | Nenhum, pelo mesmo motivo de A | Mesmo escopo de páginas, se implementado com a mesma restrição de elegibilidade por método | Sim, mesma lógica | Sim, mesmo literal |

**Nenhum candidato foi descartado por exigir "limpeza global de strings arbitrárias"**: todos os três operam sobre um único literal conhecido e fixo (`[End OCR]*`), não uma classe aberta de padrões — a diferença entre eles é exclusivamente o **ponto de execução** na pipeline já existente, não o mecanismo de busca.

## ETAPA 4 — Blast radius (8 PDFs conhecidos)

Roteamento reexecutado nesta investigação (sem OCR, apenas `route_page` sobre os PDFs originais), independente de qualquer relatório anterior:

| PDF | Páginas | Método(s) |
| --- | --- | --- |
| `AINTARESP_1462304-PA.pdf` | 12 | `texto_nativo` × 12 |
| `Inf0024E.pdf` | 29 | `texto_nativo` × 29 |
| `L10.406_CC_2002.pdf` | 186 | `texto_nativo` × 186 |
| `REsp_1704551-SP.pdf` | 14 | `texto_nativo` × 14 |
| `001-007-Petição Inicial.pdf` | 7 | `texto_nativo` × 7 |
| `012-015-Testamento Publico.pdf` | 4 | `hibrido` × 4 |
| `086-096-CONTESTAÇÃO ao Cumprimento de Testamento.pdf` | 11 | `texto_nativo` × 11 |
| `100-106-DECISÃO.pdf` | 7 | `texto_nativo` × 7 |
| **Total** | **270** | **266 `texto_nativo` + 4 `hibrido` + 0 `ocr_integral`** |

Confirmado (idêntico ao já documentado em `fix-ocr-rotated-text-fragmentation`, agora reproduzido de forma independente nesta investigação):

- **Páginas `texto_nativo` não são afetadas por nenhum candidato**: os 3 candidatos restringem-se por construção às páginas com `method in (hibrido, ocr_integral)` (Candidato A reaproveita a mesma lista `eligible_numbers` já usada pela correção arquivada; B e C usariam a mesma restrição se implementados corretamente). Nenhum candidato tem qualquer caminho de código que toque páginas `texto_nativo`.
- **Somente páginas `hibrido`/`ocr_integral` podem entrar no ramo**: confirmado — são as únicas 4 páginas do corpus onde `[End OCR]*` sequer existe.
- **Marcadores `[[Pág. N]]` permanecem intactos**: nenhum candidato toca o padrão `_PAGE_MARKER_SPLIT_PATTERN`/`_PAGE_MARKER_NUMBER_PATTERN`; a remoção proposta (Candidato A) opera apenas no conteúdo interno de cada segmento de página, nunca no próprio marcador de página.
- **Conteúdo OCR substantivo permanece byte a byte**: o texto transcrito pelo LLM (`ocr_text`) nunca é tocado por nenhum candidato — apenas a substring literal do marcador de formatação é removida, nunca texto adjacente.
- **Resíduo vertical reconstruído permanece intacto**: a reconstrução geométrica (`fix-ocr-rotated-text-fragmentation`) é produzida e inserida **antes** do ponto de remoção recomendado (Candidato A); remover o marcador depois não afeta o texto reconstruído, que já está fixado em `head`/no documento composto.

**Limitação do corpus (idêntica à já registrada em `fix-ocr-rotated-text-fragmentation`)**: o corpus de controle não contém nenhuma página `hibrido`/`ocr_integral` adicional além das 4 já diagnosticadas, nem nenhum caso real de página com múltiplas imagens (múltiplos marcadores `[End OCR]*` na mesma página). Uma implementação futura deve tratar isso como cobertura de teste sintética obrigatória, não como generalização já validada contra um segundo caso real.

## CONCLUSÃO

### A) CRITÉRIO SEGURO ENCONTRADO

- **Origem:** `markitdown_ocr/_pdf_converter_with_ocr.py`, três pontos de emissão (linhas 275, 374, 407), todos produzindo a f-string literal `[End OCR]*` como delimitador de fechamento de um bloco `*[Image OCR]\n...\n[End OCR]*` — artefato de formatação do plugin de terceiros, nunca conteúdo do documento.
- **Função exata:** delimitar, dentro do próprio plugin, onde termina o texto de OCR de uma imagem antes de eventual texto nativo residual ser interlaçado por posição Y. Dentro de `src/pipeline_juridico/`, sua única função é servir de ponto de corte para `_split_ocr_tail` (usado pela correção já arquivada `fix-ocr-rotated-text-fragmentation`, via `_replace_fragmented_vertical_residual_in_text`/`_replace_fragmented_vertical_residuals_in_document`).
- **Momento em que deixa de ser necessário:** imediatamente após `_replace_fragmented_vertical_residuals_in_document` terminar de processar o documento composto inteiro (linha 619 de `convert_document`) — a partir daí, nenhum código deste pipeline volta a buscar ou depender do marcador.
- **Ponto mínimo de remoção (recomendado — Candidato A):** uma nova função em `converter.py`, chamada em `convert_document` imediatamente após a linha 619 (`_replace_fragmented_vertical_residuals_in_document`) e antes da linha 620 (`join_symbol_across_page_break`), que remove todas as ocorrências literais de `[End OCR]*` restritas aos segmentos de página com `method in (hibrido, ocr_integral)` (reaproveitando a mesma segmentação `_PAGE_MARKER_SPLIT_PATTERN` e a mesma verificação de elegibilidade já usadas pela função vizinha). Não toca `cleaner.py`, não introduz o teste `test_clean_markdown_preserves_ocr_delimiters` em conflito algum (esse teste continua válido, pois `clean_markdown` isolada não é alterada).
- **Blast radius:** confinado às 4 páginas `hibrido` de `012-015-Testamento Publico.pdf`, único caso do corpus de 270 páginas / 8 PDFs; 0 páginas `texto_nativo` tocadas, por construção.
- **Proposta futura (não implementada nesta mudança):** implementação TDD mínima seguindo o padrão já usado em `fix-ocr-rotated-text-fragmentation` — testes cobrindo: remoção do marcador em página `hibrido` de exemplo; preservação de páginas `texto_nativo`/`vazia`/`erro`; não-interferência com a reconstrução geométrica já existente (marcador removido só depois da reconstrução ter sido inserida); múltiplas ocorrências do marcador na mesma página (fixture sintética, já que o corpus real não cobre esse caso); ausência do marcador (no-op); regressão explícita garantindo que `_split_ocr_tail`/a substituição geométrica continuam funcionando com o novo passo presente. Fora de escopo dessa proposta futura: o marcador de abertura `*[Image OCR]` (não pedido neste `/goal`) e qualquer outra limpeza.

Ver `proposal.md` para o resumo executivo.
