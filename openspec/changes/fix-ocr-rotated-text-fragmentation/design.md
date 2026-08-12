## Contexto

`012-015-Testamento Publico.pdf` (4 páginas, `input/processos_auditoria/`) converte com rota `hibrido` em 4/4 páginas. A validação supervisionada arquivada (`openspec/changes/archive/2026-08-12-validate-supervised-ocr-testamento-publico/`) já identificou que cada página traz, após o marcador interno `[End OCR]*`, um bloco de ~209 linhas de ruído de 1 caractere, e já apontou a causa provável no pacote de terceiros `markitdown-ocr` (via `pdfplumber`). Esta mudança é uma nova investigação, **independente**, que reproduz e verifica essa causa raiz com evidência direta (sem confiar apenas no relatório anterior), estende o rastreamento a todo o corpus de controle (8 PDFs, 270 páginas) e avalia formalmente critérios de correção candidatos — sem implementar nada.

Baseline confirmado antes do diagnóstico: `git status --short` limpo, HEAD `b30771d`, `uv run pytest tests/` = 364/364 passando, `openspec validate --all --strict` = 1 passed (`spec/juridical-pdf-conversion`), 1 failed (esta própria mudança, esperado — diagnóstica, sem deltas, mesmo padrão dos dois precedentes arquivados `audit-scanned-pdf-ocr-support` e `fix-rotated-digital-signature-noise`). Nenhuma chamada de OCR/LLM foi feita nesta investigação — toda a evidência vem de `page.get_text("dict")` (PyMuPDF), `page.chars`/`page.images` (pdfplumber) e leitura direta do código-fonte instalado de `markitdown_ocr`, reproduzindo localmente o algoritmo de agrupamento sem invocar nenhum serviço externo.

`[End OCR]*` (vazamento do marcador interno do plugin) permanece **fora de escopo**, assim como qualidade/prompt/modelo/provider de OCR e qualquer correção já arquivada (`fix-rotated-digital-signature-noise`, rota `texto_nativo`).

## ETAPA 1 — Estrutura real do texto vertical (PyMuPDF `page.get_text("dict")`)

Nas 4 páginas de `012-015-Testamento Publico.pdf` (todas roteadas `hibrido`), o texto nativo (não-imagem) da página é mínimo — 383 caracteres nativos por página — porque o conteúdo substantivo do testamento está inteiramente dentro de uma imagem de página inteira (por isso a rota é `hibrido`/OCR). Desses 383 caracteres nativos, **376 pertencem a exatamente 2 linhas verticais** (`dir=(0.0, -1.0)`, fonte `Helvetica`), idênticas nas 4 páginas em bbox e conteúdo (o mesmo carimbo de autenticação e-SAJ reaplicado página a página pelo sistema do tribunal):

| Linha | bbox (x0,y0,x1,y1) | Caracteres | Texto (início) |
| --- | --- | --- | --- |
| A | `(596.3, 129.7, 608.7, 836.0)` | 174 | `"Para conferir o original, acesse o site https://esaj.tjsp.ju..."` |
| B | `(585.3, 5.0, 597.7, 836.0)` | 202 | `"Este documento é cópia do original, assinado digitalmente po..."` |

O restante (`fls. NNN`, numeração de fólio) é texto horizontal curto, íntegro.

**Diferença crítica em relação ao achado já corrigido (`fix-rotated-digital-signature-noise`, C.1, rota `texto_nativo`, `100-106-DECISÃO.pdf`):** ali o defeito exigia **duas cópias idênticas e sobrepostas** do mesmo bloco vertical na mesma página. Aqui, cada uma das 2 linhas verticais ocorre **uma única vez** por página — não há duplicação geométrica alguma. `_has_duplicated_rotated_block` (já existente em `converter.py`), se fosse aplicada a estas páginas, retornaria `False` — não é o mesmo padrão e não seria coberta pela mesma salvaguarda mesmo que esta fosse estendida à rota `hibrido` sem alteração.

## ETAPA 2 — Rastreamento pdfplumber → markitdown-ocr → Markdown final

**2.1 — `page.chars` (pdfplumber) está correto.** Extraindo `page.chars` diretamente (sem passar pelo agrupamento do plugin), cada caractere individual tem texto e posição corretos — a mesma informação que o PyMuPDF lê corretamente como as 2 linhas verticais coerentes acima. **A extração de caracteres do pdfplumber não é a origem do defeito.**

**2.2 — O agrupamento em "linhas" do próprio `markitdown_ocr` é a origem.** Código instalado, `.venv/lib/python3.12/site-packages/markitdown_ocr/_pdf_converter_with_ocr.py`, dentro de `PdfConverterWithOCR.convert()`, ramo "há imagens na página" (linhas 197–227):

```python
chars = page.chars  # via pdfplumber
if chars:
    lines_with_y = []
    current_line = []
    current_y = None
    for char in sorted(chars, key=lambda c: (c["top"], c["x0"])):
        y = char["top"]
        if current_y is None:
            current_y = y
        elif abs(y - current_y) > 2:  # limiar fixo de 2pt para nova "linha"
            if current_line:
                text = "".join([c["text"] for c in current_line])
                lines_with_y.append({"y": current_y, "text": text.strip()})
            current_line = []
            current_y = y
        current_line.append(char)
    ...
```

Reproduzido localmente (sem chamar OCR), aplicando este algoritmo exato aos 383 caracteres nativos da página 1: **228 "linhas" produzidas** (115 de exatamente 1 caractere, 105 de 2–9 caracteres — todas fragmentos, nenhuma delas uma palavra completa —, 8 vazias). O agrupamento assume texto horizontal (variação de `top` pequena dentro de uma linha real); numa linha vertical, o `top` de cada caractere sucessivo varia ao longo de toda a extensão da linha (129,7 a 836,0pt), ultrapassando o limiar de 2pt a quase cada caractere. **Este é o primeiro estágio em que uma linha vertical legítima vira caracteres isolados** — não em `page.chars`, não no PyMuPDF, não na resposta do LLM.

Reconstrução determinística (concatenando os 115 fragmentos de 1 caractere, invertidos): produz fragmentos legíveis do mesmo texto das linhas A/B acima (`"...ú m e r o 1 0 0 0 3 8 6..."`, `"...c i a n f d r t d r e..."` etc.) — confirma que o ruído é a mesma informação já lida corretamente pelo PyMuPDF, apenas fragmentada.

**2.3 — Classificação da origem (A/B/C do objetivo):** **B) texto nativo residual.** O texto OCR da imagem (resposta do LLM, via `ocr_service.extract_text()`) e os fragmentos de `lines_with_y` são calculados por mecanismos totalmente independentes — o primeiro chama a API Gemini sobre a imagem extraída; o segundo processa `page.chars` do pdfplumber, sem nenhuma relação com a chamada LLM. Confirmado por leitura direta do código (linhas 236–277): `image_data` vem de `ocr_service.extract_text(img_info["stream"])`; `lines_with_y` vem inteiramente de `page.chars`. Não há como o ruído ser parte da resposta do OCR (A) nem produzido "na combinação" propriamente dita (C) — a combinação (2.4 abaixo) apenas decide a **posição relativa** dos fragmentos já corrompidos, não os produz.

**2.4 — Como OCR e texto nativo residual são combinados.** Código, linhas 253–277:

```python
content_items = [{"y_pos": item["y"], "text": item["text"], "type": "text"} for item in lines_with_y if item["text"]]
content_items.extend(image_data)          # cada imagem OCR'd vira 1 item {"type": "image", "y_pos": ...}
content_items.sort(key=lambda x: x["y_pos"])
for item in content_items:
    if item["type"] == "text":
        markdown_content.append(item["text"])
    else:
        markdown_content.append(f"\n\n*[Image OCR]\n{item['ocr_text']}\n[End OCR]*\n")
# ...
markdown = "\n\n".join(markdown_content).strip()
```

Reproduzido localmente para a página 1 (usando `_extract_images_from_page` do próprio plugin, sem chamar OCR — apenas a extração/posicionamento da imagem): **exatamente 1 imagem por página**, `y_pos≈0.04` (topo da página, pois a imagem cobre a página quase inteira). Todos os 220 fragmentos de texto não-vazios (`lines_with_y` filtrados) têm `y_pos` maior que o da imagem — **100% deles ordenam-se depois do item de imagem**. Isso reproduz exatamente o padrão observado no Markdown real: conteúdo OCR legível primeiro, `[End OCR]*`, depois a íntegra do ruído — sem nenhum fragmento intercalado *dentro* do texto substantivo. (A contagem de 220 aqui vs. "~209" da validação anterior é uma diferença de contagem aproximada/visual daquele relatório, não uma divergência de mecanismo — a ordem de grandeza e o padrão são idênticos.)

**2.5 — Confirmação em `converter.py` (pipeline local):** O resultado de `ocr_engine.convert(page_path)` (já com o ruído embutido, produzido inteiramente dentro do pacote de terceiros) entra em `convert_document` como `raw_content` (linha 420) e passa direto para `content` (linha 426: `content = "" if method is Metodo.erro else raw_content`) sem qualquer verificação de qualidade além de `verify_ocr_evidence`/`scan_ocr_warnings` (`engines.py`) — que só reconhecem 3 marcadores-sentinela de falha total (`OCR_NO_TEXT_MARKER`, `OCR_PAGE_ERROR_MARKER`, `OCR_FATAL_ERROR_MARKER`), nenhum dos quais é acionado por este padrão de ruído. A salvaguarda geométrica já existente (`_has_duplicated_rotated_block`, `_geometric_reading_order_text`, linhas 365–369 e 379) só é calculada/aplicada quando `method is Metodo.texto_nativo` — nunca no ramo `hibrido`/`ocr_integral` (linhas 403–426), confirmado por leitura direta do código-fonte local (não apenas do relatório anterior).

## ETAPA 3 — Critérios candidatos avaliados

| Candidato | Descrição | Avaliação |
| --- | --- | --- |
| Direção não horizontal isolada | `dir != (1.0, 0.0)` via PyMuPDF, sozinho | Só está disponível **antes** de chamar `markitdown-ocr` (a string final não carrega geometria). Sozinho, marcaria como suspeitas todas as páginas com qualquer texto vertical, incluindo as 76 linhas verticais legítimas de outros PDFs do corpus (ETAPA 4) — mas só teria efeito real se o critério fosse aplicado fora do ramo `hibrido`/`ocr_integral`, o que não é necessário (ver Candidato E). |
| Sequência de linhas de 1 caractere no texto já produzido | Padrão textual no `raw_content` (linhas curtas separadas por linha em branco) | Detecta o sintoma corretamente (confirmado: 115 linhas de exatamente 1 char + 105 de 2–9 chars na página 1), mas **sozinho** não distingue com segurança um documento legitimamente denso em siglas/números isolados de um caso de corrupção — mesma limitação já identificada e descartada como critério único no diagnóstico C.1 arquivado. Necessita corroboração. |
| Mesma coordenada/eixo (x aproximadamente constante) | As linhas verticais A/B têm `x0` quase fixo (596–609 e 585–598) | Sinal geométrico verdadeiro, mas só disponível a partir de `page.get_text("dict")`/`page.chars` — não do `raw_content` final. Útil apenas se o critério operar antes/junto da chamada ao plugin, ou como parte da corroboração geométrica (Candidato E). |
| Continuidade espacial / proximidade geométrica | Fragmentos consecutivos com `top` próximo entre si (mesmo antes do limiar de 2pt) | Já é, na prática, o próprio mecanismo do defeito (o limiar de 2pt é uma forma de "proximidade"); não serve como critério de *correção* porque é a causa, não o efeito a distinguir. |
| Origem em texto nativo residual (não-imagem) | Marcar como suspeito todo item `{"type": "text"}` do `content_items` do plugin | Correto em princípio (é exatamente a origem, ETAPA 2.3), mas não é observável de fora do plugin — só a string final (`raw_content`) chega ao pipeline. Reformulado operacionalmente como Candidato E (posição estrutural + corroboração geométrica). |
| Relação com região de imagem/OCR (posição relativa ao marcador `[End OCR]*`) | Conteúdo estritamente após o(s) marcador(es) `[End OCR]*` no `raw_content` | Estruturalmente seguro **apenas quando combinado** com um segundo sinal: texto nativo horizontal legítimo que por acaso esteja posicionado abaixo da imagem (`y_pos` maior) também ordenaria depois de `[End OCR]*` e seria erroneamente removido por este sinal isolado. Não descartado, mas insuficiente sozinho — ver Candidato E. |
| **Candidato E — combinação (recomendado): posição estrutural + corroboração geométrica** | (i) fragmento(s) posicionados estritamente após o(s) marcador(es) `[End OCR]*` da página, **e** (ii) o texto desses fragmentos concatenados (na ordem observada ou invertida) tem alta correspondência de caracteres com pelo menos uma linha não horizontal (`dir != (1.0, 0.0)`) já lida corretamente por `page.get_text("dict")` (PyMuPDF) na mesma página — reabrindo/reutilizando a mesma página que o roteador já abre | Só remove quando **ambos** os sinais concordam; texto nativo horizontal legítimo (que não corresponde a nenhuma linha vertical do PyMuPDF) nunca é removido, mesmo se posicionado após o marcador. Não usa nome de documento, número de página/processo, texto de assinatura, nomes próprios nem remove texto vertical genericamente — apenas geometria (direção de escrita) e correspondência de caracteres, mesmo espírito de `_lexical_overlap`/`_has_native_reading_order_defect` já existentes em `converter.py`, mas em nível de caractere (os fragmentos raramente formam palavras/tokens completos). |

**Sinais explicitamente não usados**, conforme restrição do objetivo: texto literal `e-SAJ`, nome do arquivo/documento, número de página, nomes próprios, remoção genérica de todo texto vertical (o Candidato E preserva texto vertical **não correspondente** a fragmentação, se algum dia existir tal caso).

## ETAPA 4 — Controles e blast radius (8 PDFs, 270 páginas)

Roteamento (`route_page`, config padrão) de todas as páginas do corpus de controle:

| PDF | Páginas | Rota(s) | Linhas verticais (PyMuPDF, `dir != (1,0)`) |
| --- | --- | --- | --- |
| `001-007-Petição Inicial.pdf` | 7 | 7× `texto_nativo` | 14 (carimbos e-SAJ legítimos, não duplicados) |
| `012-015-Testamento Publico.pdf` | 4 | **4× `hibrido`** | 8 (2 por página, não duplicados — objeto deste diagnóstico) |
| `086-096-CONTESTAÇÃO...pdf` | 11 | 11× `texto_nativo` | 22 (carimbos e-SAJ legítimos, não duplicados) |
| `100-106-DECISÃO.pdf` | 7 | 7× `texto_nativo` | 34 (inclui os pares duplicados já corrigidos por `fix-rotated-digital-signature-noise`, páginas 1–5, e os carimbos únicos legítimos das páginas 6–7) |
| `AINTARESP_1462304-PA.pdf` | 12 | 12× `texto_nativo` | 0 |
| `REsp_1704551-SP.pdf` | 14 | 14× `texto_nativo` | 0 |
| `Inf0024E.pdf` | 29 | 29× `texto_nativo` | 0 |
| `L10.406_CC_2002.pdf` | 186 | 186× `texto_nativo` | 0 |
| **Total** | **270** | **266× `texto_nativo`, 4× `hibrido`, 0× `ocr_integral`** | **78** |

**Achado central de blast radius:** em todo o corpus de controle, a rota `hibrido`/`ocr_integral` — o único ramo do pipeline onde `markitdown-ocr`/`pdfplumber` chega a processar a página — ocorre em **exatamente 4 páginas, todas em `012-015-Testamento Publico.pdf`, todas já no escopo deste diagnóstico**. Nenhuma outra página do corpus (nem as 34 linhas verticais de `100-106-DECISÃO.pdf`, nem as 14+22 de `001-007`/`086-096`) passa por este ramo — logo, qualquer correção **implementada dentro do ramo `hibrido`/`ocr_integral`** (Candidato E) tem, por construção, blast radius zero sobre as 266 páginas `texto_nativo` do corpus, independentemente do critério interno usado.

Verificação explícita dos controles pedidos:
- **Carimbos verticais legítimos da DECISÃO (páginas 6–7, únicos, não duplicados) e das páginas 1–5 (já deduplicados por `fix-rotated-digital-signature-noise`):** rota `texto_nativo` — nunca entram no ramo onde o Candidato E atuaria. Blast radius: 0.
- **Correção arquivada de blocos rotacionados duplicados (`fix-rotated-digital-signature-noise`):** opera em função e condição (`method is Metodo.texto_nativo`) totalmente disjunta do ponto de intervenção recomendado abaixo (`method is Metodo.hibrido/ocr_integral`). As duas correções não colidem nem se sobrepõem.
- **Textos horizontais legítimos:** o Candidato E só atua sobre fragmentos que correspondem a uma linha **não horizontal** do PyMuPDF — texto horizontal nunca corresponde a essa corroboração, preservado por construção mesmo se posicionado após `[End OCR]*`.
- **Páginas `texto_nativo`:** 266/270 páginas — 0 tocadas (ramo de código diferente).
- **Páginas híbridas:** as 4 candidatas são as mesmas 4 já diagnosticadas; nenhuma página híbrida adicional existe no corpus para testar generalização, o que é registrado como limitação (ver "Riscos" na conclusão).

Nenhum falso positivo ou falso negativo adicional foi medido porque não há, no corpus atual, nenhuma página `hibrido`/`ocr_integral` fora do escopo já diagnosticado contra a qual testar o Candidato E.

## ETAPA 5 — Ponto de intervenção

| Opção | Descrição | Avaliação |
| --- | --- | --- |
| A. Antes do `markitdown-ocr` | Bypassar a chamada ao plugin para páginas `hibrido`/`ocr_integral` e reimplementar a extração de imagem + composição no próprio pipeline | Resolveria na origem, mas exige reimplementar orquestração de OCR já existente no plugin (extração de imagem, chamada ao serviço, composição) — escopo e blast radius de código desproporcionais ao defeito, e reintroduz risco de regressão em toda a rota `hibrido`/`ocr_integral`, não apenas no ruído. Descartado como não-mínimo. |
| B. Composição OCR+nativo dentro do plugin | Corrigir o agrupamento por Y do próprio `markitdown_ocr` | Proibido pelo escopo ("não modificar pacote de terceiros diretamente") e frágil a atualizações da dependência. Descartado. |
| **C. Pós-processar somente o residual geométrico comprovado (recomendado)** | Em `converter.py`, dentro do ramo `else` (`hibrido`/`ocr_integral`) de `convert_document`, imediatamente após `raw_content = result.text_content or ""` (linha 420) e antes de `content = ... raw_content` (linha 426): aplicar o Candidato E — remover apenas fragmentos posicionados após `[End OCR]*` cujo texto concatenado corresponda (por sobreposição de caracteres) a uma linha não horizontal já lida por `page.get_text("dict")` na mesma página | Não toca o pacote de terceiros; não toca a rota `texto_nativo` (blast radius zero nela, por construção); preserva 100% do texto OCR substantivo (que, no caso real, ordena sempre antes do marcador); usa apenas geometria e correspondência de caracteres, nenhum sinal proibido. |

**Recomendação: Ponto C**, com o Candidato E como critério.

## CONCLUSÃO

**A) CRITÉRIO SEGURO ENCONTRADO**

- **Causa raiz:** o algoritmo de agrupamento de caracteres em "linhas" por proximidade de coordenada `top` (limiar fixo de 2pt), interno ao pacote de terceiros `markitdown-ocr` (`_pdf_converter_with_ocr.py::PdfConverterWithOCR.convert()`, linhas 199–227), assume implicitamente texto horizontal. Para uma linha de texto rotacionada 90° (`dir=(0,-1)` no PyMuPDF), a coordenada `top` de caracteres sucessivos varia ao longo de toda a extensão da linha, ultrapassando o limiar a quase cada caractere. `page.chars` (pdfplumber) já fornece os caracteres corretos; o defeito não está na extração, está exclusivamente neste agrupamento heurístico downstream, aplicado sem verificar direção de escrita.
- **Estágio/função exatos:** `markitdown_ocr/_pdf_converter_with_ocr.py`, dentro de `PdfConverterWithOCR.convert()`, bloco `if chars:` (linhas 197–227) — primeiro estágio em que uma linha vertical legítima (confirmada íntegra em `page.chars` e em `page.get_text("dict")`) se torna caracteres isolados.
- **Origem do ruído:** B) texto nativo residual — confirmado por leitura de código (2.3), não apenas inferido do resultado.
- **Combinação OCR+nativo:** `content_items` (fragmentos de texto + blocos `*[Image OCR]...[End OCR]*`) ordenados unicamente por `y_pos` e concatenados com `"\n\n".join`; reproduzido localmente e confirmado byte a byte contra o padrão real (1 imagem por página, `y_pos≈0`, 100% dos 220 fragmentos ordenando-se depois dela).
- **Critério (Candidato E):** fragmento(s) de texto posicionados estritamente após o(s) marcador(es) `[End OCR]*` no `raw_content` de uma página `hibrido`/`ocr_integral`, **e** cujo texto concatenado corresponde (sobreposição de caracteres) a uma linha não horizontal já lida corretamente por `page.get_text("dict")` na mesma página. Ambos os sinais são obrigatórios; nenhum opera sozinho.
- **Blast radius:** 4 de 270 páginas do corpus são sequer elegíveis (único universo onde o ramo de código relevante executa); as 4 são as já diagnosticadas. 0 páginas `texto_nativo` tocadas, por construção do ponto de intervenção. **Limitação registrada:** o corpus de controle não contém nenhuma página `hibrido`/`ocr_integral` adicional (fora das 4 já diagnosticadas) para validar a generalização do critério contra um segundo caso real — a corroboração geométrica (segundo sinal do Candidato E) existe precisamente para mitigar esse risco de generalização não testada, mas uma implementação futura deve tratar isso como cobertura de teste sintética obrigatória (fixtures cobrindo: página `hibrido` com texto horizontal legítimo abaixo da imagem; página `hibrido` com múltiplas imagens/múltiplos marcadores `[End OCR]*`; página `hibrido` sem nenhum texto vertical).
- **Proposta mínima futura (não implementada aqui):** nova mudança OpenSpec dedicada, TDD, implementando o Candidato E no Ponto C (`converter.py::convert_document`, ramo `hibrido`/`ocr_integral`, imediatamente após obter `raw_content`). Decisão em aberto a resolver nessa mudança, não aqui: **descartar** o texto residual corroborado geometricamente ou **substituí-lo** pelo texto geometricamente reconstruído do PyMuPDF (mesmo padrão de substituição já usado por `fix-rotated-digital-signature-noise` para a rota `texto_nativo`) — a segunda opção preserva o valor probatório (protocolo, assinante digital, data/hora) que a validação arquivada explicitamente registrou como "efetivamente perdido" hoje, e é a opção recomendada por consistência com o precedente já implementado.

## Verificação de não regressão (fase de diagnóstico)

Nenhum arquivo de `src/`, `tests/`, `output/`, `logs/`, `prompts/`, dependências ou do corpus canônico foi alterado. Nenhuma chamada de OCR/LLM foi feita — toda a evidência vem de `page.get_text("dict")`/`page.images` (PyMuPDF), `page.chars`/`page.images`/`_extract_images_from_page` (pdfplumber, incluindo a função já existente do próprio `markitdown_ocr`, chamada apenas para posicionamento de imagem, nunca para OCR) e leitura direta do código-fonte instalado. Scripts de investigação ficaram fora do repositório, no diretório de scratchpad da sessão (`/tmp/claude-*/.../scratchpad/`), nunca em `src/`/`tests/`.

## `git status --short` ao final

Ver saída no encerramento desta mudança — os únicos arquivos novos esperados são os de `openspec/changes/fix-ocr-rotated-text-fragmentation/` (esta mudança); nenhum arquivo em `src/`, `tests/`, `output/`, `logs/`, `openspec/specs/` ou no corpus de `input/` deve aparecer.
