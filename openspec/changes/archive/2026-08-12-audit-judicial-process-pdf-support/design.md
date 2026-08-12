## ETAPA 1 — Baseline

Executado antes de qualquer conversão de auditoria.

- `git status --short` (antes): limpo (`(clean)`).
- HEAD: `1f24617bb13256a457a8dd924a78e9c1f12a107b` (`docs: formalize Papel/Nome as known limitation delegated to future semantic layer`).
- `uv run pytest tests/`: **354 passed** em 26.71s.
- `openspec validate --all --strict`: **1 passed, 0 failed** (`spec/juridical-pdf-conversion`; nenhuma mudança ativa pré-existente).

## ETAPA 2 — Inspeção dos 4 PDFs via PyMuPDF (sem OCR)

Métrica por página: caracteres de `page.get_text("text")` (bruto, não normalizado — usado só para triagem; a classificação real usa `inspect_native_text`/`route_page` de `src/pipeline_juridico/router.py`, aplicada na ETAPA 3), contagem/área de imagens (`page.get_image_info`/`get_images`), blocos, desenhos vetoriais, fontes.

### `001-007-Petição Inicial.pdf` — 7 páginas

| Pág. | Caracteres | Imagens | Área img. | Blocos |
| --- | --- | --- | --- | --- |
| 1 | 1284 | 0 | 0% | 4 |
| 2 | 1927 | 0 | 0% | 4 |
| 3 | 1793 | 0 | 0% | 5 |
| 4 | 1782 | 0 | 0% | 3 |
| 5 | 1807 | 0 | 0% | 4 |
| 6 | 1559 | 0 | 0% | 5 |
| 7 | 676 | 0 | 0% | 7 |

Nenhuma imagem; texto nativo abundante em todas as páginas. Rodapé de autenticação e-SAJ (`Para conferir o original, acesse o site https://esaj.tjsp.jus.br/...`) presente em todas as páginas, seguido do corpo da petição.

### `012-015-Testamento Publico.pdf` — 4 páginas

| Pág. | Caracteres | Imagens | Área img. | Blocos |
| --- | --- | --- | --- | --- |
| 1–4 | 385 (idêntico) | 1 | 100% | 2 |

Cada página é uma única imagem JPEG de página inteira, **1272×1752 px** sobre página de 611×841pt (≈150 DPI) — resolução compatível com digitalização de cartório, adequada a OCR (não avaliado aqui). Os 385 caracteres nativos por página são exclusivamente a camada de autenticação do sistema (`Para conferir o original... fls. 12/13/14/15`) sobreposta à imagem — **não há nenhum texto nativo do próprio testamento**, que existe apenas como pixels da imagem.

### `086-096-CONTESTAÇÃO ao Cumprimento de Testamento.pdf` — 11 páginas

| Pág. | Caracteres | Imagens | Área img. | Blocos |
| --- | --- | --- | --- | --- |
| 1 | 2178 | 3 | 18% | 31 |
| 2 | 2265 | 3 | 18% | 31 |
| 3 | 2430 | 3 | 18% | 33 |
| 4 | 2479 | 3 | 18% | 33 |
| 5 | 2264 | 3 | 18% | 31 |
| 6 | 2483 | 3 | 18% | 32 |
| 7 | 2292 | 3 | 18% | 32 |
| 8 | 2189 | 3 | 18% | 32 |
| 9 | 2170 | 3 | 18% | 37 |
| 10 | 2112 | 3 | 18% | 36 |
| 11 | 763 | 3 | 18% | 13 |

3 imagens por página (18% da área — abaixo do limiar de página cheia de 70%, mas acima do limiar de imagem significativa de 15%), texto nativo abundante (>2000 caracteres nas 10 primeiras páginas). 1 bloco vertical rotacionado por página (rodapé de autenticação e-SAJ), sem duplicação.

### `100-106-DECISÃO.pdf` — 7 páginas

| Pág. | Caracteres | Imagens | Área img. | Blocos | Desenhos |
| --- | --- | --- | --- | --- | --- |
| 1 | 2709 | 1 | 1% | 30 | 51 |
| 2 | 3207 | 1 | 1% | 37 | 0 |
| 3 | 3451 | 1 | 1% | 38 | 0 |
| 4 | 3435 | 1 | 1% | 38 | 9 |
| 5 | 2780 | 1 | 1% | 35 | 8 |
| 6 | 1417 | 1 | 1% | 11 | 8 |
| 7 | 928 | 0 | 0% | 8 | 1 |

Texto nativo abundante em todas as páginas; imagem irrelevante (1%, provavelmente um brasão/logo). Blocos rotacionados verticalmente (carimbos de assinatura digital): **5 blocos rotacionados nas páginas 1–5** (2 pares idênticos duplicados + 1 carimbo de anexação), **1 bloco rotacionado nas páginas 6–7** (só o carimbo de anexação, sem duplicação) — ver ETAPA 4/5, achado C.1.

## ETAPA 3 — Conversão com `--no-ocr`

CLI oficial (`uv run converter-juridico --no-ocr`), saída isolada via `OUTPUT_DIR`/`LOGS_DIR` apontando para `openspec/changes/audit-judicial-process-pdf-support/audit_output/{strict,partial}` e `.../{logs_strict,logs_partial}` — nunca `output/`/`logs/`. Nenhuma variável de OCR foi setada; `GEMINI_API_KEY` não foi usada; nenhuma chamada de rede/LLM ocorreu (confirmado por `ocr.enabled: false` em todos os relatórios).

| PDF | Modo estrito (`--no-ocr`) | Páginas bloqueadas |
| --- | --- | --- |
| `001-007-Petição Inicial.pdf` | ✅ sucesso, 7/7 `texto_nativo` | 0 |
| `012-015-Testamento Publico.pdf` | ❌ `MarkdownValidationError`: "A página 1 está em erro; páginas em erro não são permitidas no modo estrito." (exit code 3, **nenhum arquivo publicado**) | 4/4 (todas) |
| `086-096-CONTESTAÇÃO...pdf` | ✅ sucesso, 11/11 `texto_nativo` | 0 |
| `100-106-DECISÃO.pdf` | ✅ sucesso, 7/7 `texto_nativo` | 0 |

Nenhuma página bloqueada foi contornada. Para `Testamento Publico.pdf`, como o modo estrito não produz nenhuma saída (por design — `validate_page_content(strict=True)` recusa publicar qualquer página em `erro`), uma segunda conversão foi feita **somente para fins de auditoria**, com `--allow-partial` (flag já existente e documentada, não uma nova permissão): confirma as 4 páginas como `método: erro` com conteúdo vazio (sem `[[TEXTO ILEGÍVEL]]`, pois a página nunca chega a acionar OCR/erro de evidência — ela é recusada antes, por `use_ocr=False`). Nenhuma chamada de OCR foi feita nesse segundo run.

## ETAPA 4 — Auditoria página a página

### `Petição Inicial.pdf` — Categoria A (correto, sem alteração)

Diff de tokens (regex `\w+`, case-fold) entre `page.get_text("text")` de cada página do PDF e o conteúdo correspondente no Markdown final: **0 tokens ausentes, 0 tokens extras em todas as 7 páginas** (paridade exata). Verificado manualmente: cabeçalho de autenticação e-SAJ preservado página a página (varia por página — `fls. 1`...`fls. 7` — não é removido como margem, corretamente, pois não é verbatim-repetido); parágrafo interrompido entre página 3 (final: "temos um") e página 4 (início: "herdeiro filho...") é o comportamento esperado de página isolada, não um defeito; a grafia "soiteira" (página 4) foi confirmada como erro de digitação **já presente no PDF de origem** (`page.get_text` bruto), não introduzido pela conversão; assinatura final e OAB preservados.

### `Testamento Publico.pdf` — Categoria D (necessidade legítima de OCR)

100% do conteúdo substantivo (o corpo do testamento) existe apenas como pixels de imagem. Roteamento correto (`route_page`: `has_native=True` só pela camada de autenticação de 385 caracteres, mas `has_full_page_image=True` com `largest_image_area_ratio=1.0` ≥ `full_page_image_min_ratio=0.70`, e `has_clearly_sufficient_native=False` pois 385 < 500 — resultado: `hibrido`, que sob `use_ocr=False` vira `erro`). Bloqueio correto e completo; nenhum conteúdo fabricado; nenhum contorno.

### `CONTESTAÇÃO...pdf` — Categoria A (correto, comportamento já validado)

Diff de tokens por página: única diferença nas 11 páginas é a ausência, no Markdown, dos 25 tokens do timbre do escritório de advocacia (`Rua Dom Fernando Taddey, n. 1030, Centro – Jacarezinho-PR – CEP. 86400-000 / Celular: (43) 99974-7679 ou (43) 99915-6894 / E-mail: joaopadilhafilho@hotmail.com ou claudia_manfrep@hotmail.com`), repetido verbatim como primeiras linhas de conteúdo em 11/11 páginas (100%, acima do limiar de 60% de `remove_repetitive_margins`). Zero tokens extras em qualquer página — sem duplicação, sem fusão indevida. Este é exatamente o mecanismo de remoção de margem verbatim generalizado em `fix-repeated-header-cross-page-fusion` (arquivada em 2026-08-06), já validado no corpus canônico para cabeçalhos institucionais (`Superior Tribunal de Justiça`); aqui ele generaliza corretamente para um timbre particular de escritório, sem nenhum ajuste de código. Rodapé de autenticação e-SAJ (varia por página, carimbo vertical único, sem duplicação) preservado corretamente em todas as páginas.

### `DECISÃO.pdf` — 3 achados (2 novos determinísticos, 1 variação de limitação conhecida)

Diff de tokens por página: páginas 6–7 com paridade exata (0/0). Páginas 1–5 com token counts inflados no Markdown (ex. página 1: 436 tokens no PDF vs. 748 no Markdown) — ver achado C.1 abaixo.

Ver ETAPA 5 para a análise de impacto completa de cada achado.

## ETAPA 5 — Impacto no conversor (achados novos)

### Achado C.1 — Carimbo de assinatura digital duplicado e rotacionado vira ruído de caracteres (Categoria C, gravidade alta)

- **Arquivo/páginas:** `100-106-DECISÃO.pdf`, páginas 1, 2, 3, 4 e 5 (5 de 7 páginas do documento; páginas 6–7 não afetadas).
- **Causa raiz isolada:** o PDF de origem contém, no mesmo local geométrico, **duas cópias idênticas e sobrepostas** de um bloco de texto rotacionado 90° (o carimbo lateral de verificação "Este documento é cópia do original assinado digitalmente por MARCOS ROGÉRIO SANCHES CRUZ GERALDO..."), confirmado via `page.get_text("blocks")`: dois blocos com bbox idêntico (`(544.4, 202.8, 555.4, 785.3)` e `(554.8, 436.6, 565.8, 785.3)`) aparecem cada um duas vezes na lista de blocos da página. Um terceiro bloco vertical, não duplicado (o carimbo de anexação ao processo de inventário, "Para conferir o original... fls. 100"), extrai corretamente. Reproduzido **isoladamente**, chamando `create_native_engine().convert()` (MarkItDown) diretamente sobre a página isolada, **sem nenhum código deste pipeline entre a chamada e o resultado**: o texto bruto retornado já contém a mesma sequência de ~500 linhas de um caractere cada, alternando entre as duas cópias duplicadas e em ordem invertida (ex. a sequência final, lida de trás para frente e ignorando a duplicação, soletra "...MARCOS ROGÉRIO SANCHES CRUZ GERALDO..."). A causa está inteiramente em como o MarkItDown (via seu extrator interno baseado em `pdfminer`) ordena/agrupa caracteres de dois blocos de texto verticais idênticos e sobrepostos — **não em `recompose_native_paragraphs`, `remove_repetitive_margins` ou qualquer outra função deste pipeline**, que apenas recebem e propagam o resultado já corrompido.
- **Por que a rede de segurança existente não pega:** `converter.py` já tem uma verificação (`_has_native_reading_order_defect`) que substitui o texto do MarkItDown pelo texto geométrico (`_geometric_reading_order_text`) quando os dois têm os mesmos tokens em ordens diferentes — mas exige sobreposição lexical ≥98% entre os dois. Aqui os "tokens" produzidos pelo MarkItDown são caracteres isolados, não palavras: a sobreposição lexical com o texto geométrico correto é próxima de zero, então a condição de disparo da rede de segurança (feita para pegar reordenação, não fragmentação catastrófica em caracteres) nunca é satisfeita. Isso é uma lacuna de cobertura da salvaguarda existente, não uma regressão nela.
- **Trecho antes (no PDF, carimbo lateral rotacionado, ilegível na orientação normal da página) → depois (Markdown final, página 1, após "É o relatório do necessário."):**
  ```
  e
  e
  t
  t
  i
  i
  s
  s
  ...
  (≈500 linhas, 1 caractere cada, cada um duplicado em duas linhas consecutivas)
  ```
- **Geral ou específico:** o mecanismo de fundo (MarkItDown falha ao extrair blocos verticais duplicados/sobrepostos) é geral — qualquer PDF com esse padrão específico (dois carimbos de assinatura idênticos sobrepostos, rotacionados) dispararia o mesmo problema. Blocos verticais **não duplicados** (o caso mais comum — presente em todos os outros documentos deste corpus e no corpus canônico) extraem corretamente; o gatilho específico é a duplicação exata e sobreposta, não a rotação isoladamente.
- **Gravidade:** alta — o Markdown final fica poluído com centenas de linhas de ruído em 5 de 7 páginas do documento (o arquivo `100-106-DECISÃO.md` tem ~1000 linhas a mais do que teria sem o defeito). Mitigante: o conteúdo jurídico substantivo (o texto da decisão em si) não é perdido, truncado nem reordenado — o ruído aparece estritamente depois do conteúdo real de cada página, o que o torna visualmente separável, mas ainda assim compromete a fidelidade e a legibilidade da saída.
- **Critério determinístico:** plausível, mas não trivial — candidatos a investigar em uma mudança futura dedicada: (a) detectar blocos com bbox idêntico ou quase idêntico e descartar a duplicata antes de gerar o Markdown; (b) detectar, no texto já produzido pelo MarkItDown, um padrão anômalo de "muitas linhas de um único caractere, cada uma repetida" e, nesse caso, cair para o texto geométrico (`_geometric_reading_order_text`) mesmo com baixa sobreposição lexical — o que exigiria generalizar `_has_native_reading_order_defect` com uma segunda condição de disparo independente da sobreposição lexical.
- **Risco de regressão:** médio — qualquer alteração em `_has_native_reading_order_defect` ou na extração de blocos rotacionados toca um caminho já cuidadosamente calibrado contra o corpus canônico e contra 4 mudanças arquivadas anteriores sobre o mesmo código. Exigiria validação completa contra o corpus canônico (4 documentos, 241 páginas) antes de qualquer implementação.
- **Merece mudança OpenSpec própria:** sim.

### Achado C.2 — Espaçamento duplo sistemático entre palavras (Categoria C, gravidade baixa)

- **Arquivo/páginas:** `100-106-DECISÃO.pdf`, páginas 1–5 (as mesmas 5 páginas do achado C.1; não ocorre nas páginas 6–7).
- **Trecho antes/depois:** PyMuPDF (`page.get_text("blocks")`, geometria bruta) retorna `"Cuida-se de ação renovatória de locação com sentença já proferida às fls. \n"` (espaço simples); o texto nativo já devolvido pelo motor MarkItDown (antes de qualquer processamento deste pipeline, confirmado isoladamente) é `"Cuida-se  de  ação  renovatória  de  locação  com  sentença  já  proferida  às  fls.\n"` (espaço duplo entre praticamente todas as palavras). Confirmado por contagem: **68 ocorrências** de espaço duplo entre letras minúsculas em `100-106-DECISÃO.md`, **0 ocorrências** nos outros 2 documentos de texto nativo desta auditoria (`Petição Inicial.md`, `CONTESTAÇÃO...md`) e **0 ocorrências** nos 4 documentos do corpus canônico (`AINTARESP_1462304-PA.md`, `REsp_1704551-SP.md`, `Inf0024E.md`, `L10.406_CC_2002.md`).
- **Etapa provável responsável:** motor de extração nativo (MarkItDown/`pdfminer`), mesma etapa do achado C.1 — provavelmente a mesma fonte PDF (tipografia/justificação específica deste documento, gerado por software de tribunal diferente do usado nos documentos do corpus canônico) faz o extrator interpretar o espaçamento extra de texto justificado como espaço duplo. Não é introduzido por `recompose_native_paragraphs`, `clean_markdown` ou qualquer outra função deste pipeline (que preserva espaçamento interno de texto por design conservador — só normaliza CRLF→LF, espaços à direita e linhas vazias).
- **Geral ou específico:** possivelmente geral para documentos gerados pelo mesmo software de origem (a "DECISÃO" do 1º grau/TJSP, diferente do padrão STJ do corpus canônico); não observado nos outros 2 documentos desta auditoria mesmo sendo também TJSP, sugerindo que é sensível à fonte/geração específica do PDF, não ao tribunal.
- **Gravidade:** baixa — não há perda, duplicação ou reordenação de conteúdo; é um desvio cosmético de fidelidade ao espaçamento original de exibição (que já é, ele mesmo, uma reconstrução do PDF, não o "espaçamento real" do documento).
- **Critério determinístico:** plausível (colapsar `"  "` → `" "` dentro de texto nativo já recomposto), mas arriscado sem investigação adicional: precisaria confirmar que nenhum documento do corpus canônico ou de outros processos usa espaço duplo intencionalmente (ex. após ponto final, convenção tipográfica comum em alguns documentos jurídicos) antes de generalizar a normalização.
- **Risco de regressão:** baixo a médio — dependeria de onde a normalização for aplicada; se aplicada de forma ampla em `clean_markdown`, poderia colapsar espaçamento duplo intencional em outros documentos ainda não vistos.
- **Merece mudança OpenSpec própria:** sim, mas de prioridade menor que C.1; pode ser resolvida na mesma mudança futura, já que compartilha a causa raiz upstream (MarkItDown).

### Achado B.1 — Cabeçalho institucional não removido quando precedido por carimbo de página variável (Categoria B, variação nova de limitação já aceita)

- **Arquivo/páginas:** `100-106-DECISÃO.pdf`, todas as 7 páginas.
- **Descrição:** o cabeçalho institucional de 7 linhas (`TRIBUNAL DE JUSTIÇA DO ESTADO DE SÃO PAULO` / `COMARCA DE CERQUEIRA CÉSAR` / ... / `Horário de Atendimento ao Público...`) se repete verbatim, byte-idêntico, em 100% das páginas — muito acima do limiar de 60% de `remove_repetitive_margins` — mas **não é removido**.
- **Causa:** `remove_repetitive_margins` só examina a **primeira** e a **última** linha física de conteúdo de cada página (`content_indices[0]`/`content_indices[-1]` em `cleaner.py`). Nesta página, a primeira linha de conteúdo é o carimbo `fls. 517` (ou `518`, `519`... — varia legitimamente por página, portanto corretamente nunca removido), o que empurra o cabeçalho institucional, byte-idêntico entre páginas, para a **segunda** linha em diante — fora do alcance posicional do mecanismo de remoção, que não teria como saber que uma linha "no meio" do bloco também é uma margem repetitiva sem processar múltiplas linhas por página.
- **Por que é Categoria B, não C:** este é exatamente o mesmo tipo de limitação arquitetural já identificado, documentado e conscientemente aceito em `openspec/changes/archive/2026-08-09-fix-editorial-cover-structural-boundaries/design.md` (linha de edição/data recorrente do `Inf0024E.pdf`, corretamente removida em 28/29 páginas, mas "soterrada no meio de um parágrafo maior" na página 1 e por isso preservada ali) — o mesmo trade-off consciente entre um mecanismo simples e auditável (só primeira/última linha) e cobertura completa de qualquer posição. Não é uma regressão; é uma nova manifestação do mesmo limite de design já formalmente aceito.
- **Gravidade:** baixa — verbosidade (cabeçalho repetido 7 vezes em vez de 1), sem perda nem corrupção de conteúdo.
- **Critério determinístico:** o mesmo já usado para o caso original (não implementado por decisão consciente anterior de manter o mecanismo simples).
- **Merece mudança OpenSpec própria:** só se, cumulativamente com outros casos futuros parecidos, justificar generalizar `remove_repetitive_margins` para examinar mais de uma linha por posição — não recomendado isoladamente por este único caso.

## Verificação de não regressão do corpus canônico

- `output/AINTARESP_1462304-PA.md`, `output/REsp_1704551-SP.md`, `output/Inf0024E.md`, `output/L10.406_CC_2002.md`: **não reconvertidos**; hashes MD5 conferidos ao final da auditoria, sem alteração em relação ao estado anterior (HEAD `1f24617`).
- `git status --short` ao final: único diretório novo é `openspec/changes/audit-judicial-process-pdf-support/` (esta mudança); nenhum arquivo em `src/`, `tests/`, `output/`, `logs/`, `openspec/specs/` ou canônico foi tocado.
- Nenhuma chamada de OCR ou LLM foi realizada em nenhuma etapa desta auditoria.
