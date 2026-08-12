## Contexto

`100-106-DECISÃO.pdf` (7 páginas, `input/processos_auditoria/`) converte com texto nativo em 7/7 páginas. Nas páginas 1–5, o Markdown final contém centenas de linhas espúrias de um caractere cada (achado C.1, `audit-judicial-process-pdf-support/design.md`, ETAPA 5) e espaçamento duplo sistemático entre palavras (achado C.2). Páginas 6–7 não são afetadas. Esta mudança isola a causa raiz com evidência reproduzível e avalia um critério de correção contra o corpus completo, sem implementar nada.

Baseline confirmado antes do diagnóstico: `git status --short` limpo, HEAD `881d9cd`, `uv run pytest tests/` = 354/354 passando, `openspec validate --all --strict` = 1/1 spec válida (a própria mudança em progresso, sem deltas, é esperada falhar a validação de `change` — mudança diagnóstica, sem capacidades novas/modificadas, mesmo padrão do precedente `audit-judicial-process-pdf-support`).

## ETAPA 1 — Estrutura nativa do PDF (`page.get_text("dict")` / `"blocks"`)

Todas as 7 páginas têm 595×842pt (páginas 1–6) ou 595×842pt com pequena variação de canto (página 7), sem rotação de página (`page.rotation == 0` em todas).

Blocos de texto verticais (`dir=(0.0, -1.0)`, fonte `Helvetica`) encontrados por página:

| Página | Blocos verticais | bbox únicos | Duplicados (bbox+texto idênticos) |
| --- | --- | --- | --- |
| 1 | 5 | 3 | 2 pares: `(544.4, 202.8, 555.4, 785.3)` × 2 e `(554.8, 436.6, 565.8, 785.3)` × 2 |
| 2 | 5 | 3 | idem (mesmos bbox, mesmo padrão) |
| 3 | 5 | 3 | idem |
| 4 | 5 | 3 | idem |
| 5 | 5 | 3 | idem |
| 6 | 1 | 1 | nenhum |
| 7 | 1 | 1 | nenhum |

Nas páginas 1–5, os blocos duplicados são, cada um, **duas ocorrências byte-idênticas** na lista de blocos da página (mesmo bbox arredondado a 0,1pt, mesmo texto extraído por `page.get_text("dict")`):
- `(544.4, 202.8, 555.4, 785.3)`, 146 caracteres, começando com `"Este documento é cópia do original assinado digitalmente por"`.
- `(554.8, 436.6, 565.8, 785.3)`, 96 caracteres, começando com `"https://esaj.tjsp.jus.br/esaj, informe o processo 1000718-23..."`.

Um terceiro bloco vertical, **não duplicado**, existe em todas as 7 páginas: `(569.9, 130.4, 593.3, 837.3)` (páginas 1–5) / bbox equivalente nas páginas 6–7, 301–323 caracteres, `"Para conferir o original, acesse o site https://esaj.tjsp.jus.br/..."` — o carimbo de anexação ao processo de inventário, presente e correto em todas as páginas, nunca duplicado.

**Comparação páginas 1–5 vs. 6–7:** a única diferença estrutural é a presença, exclusivamente nas páginas 1–5, de duas cópias idênticas e sobrepostas do bloco de assinatura do juiz (`"Este documento é cópia do original assinado digitalmente por MARCOS ROGÉRIO..."`). Páginas 6–7 são certidões de cartório (`ATO ORDINATÓRIO`, `CERTIDÃO DE REMESSA`) assinadas por um escrevente (`Nelson Ricardo Gomes`) e não carregam esse carimbo específico — apenas o carimbo de anexação, sempre único. Isso explica por que o defeito é delimitado exatamente às páginas da decisão judicial em si, não a todo o documento.

## ETAPA 2 — Saída do MarkItDown antes dos cleaners

Chamando `create_native_engine().convert()` isoladamente sobre a página isolada (sem nenhum código deste pipeline entre a chamada e o resultado):

- **Página 1 (afetada):** 3204 caracteres, 531 linhas, **426 linhas de um único caractere**. As últimas ~430 linhas antes da linha final alternam um caractere por linha (ex.: `'e'`, `'e'`, `'t'`, `'t'`, `'i'`, `'i'`, `'s'`, `'s'`, ...) — cada caractere aparece duas vezes consecutivas (uma vez por cópia duplicada do bloco), em ordem invertida. A última linha do bloco contém a sentença completa e correta uma única vez: `"Para conferir o original, acesse o site https://esaj.tjsp.jus.br/... .Este documento é cópia do original, assinado digitalmente por Nelson Ricardo Gomes, ... .fls. 100"` — na verdade a extração do carimbo NÃO-duplicado (o de anexação, referenciando o escrevente, não o juiz) funciona perfeitamente; é só a leitura dos DOIS blocos duplicados do juiz que degenera em caracteres isolados.
- **Página 6 (não afetada):** 1456 caracteres, 44 linhas, **0 linhas de caractere único**. O mesmo tipo de carimbo vertical (bloco único, não duplicado) extrai como texto corrido legível, na última linha do documento.
- Contagem por página (1–7): linhas de caractere único = `426, 426, 426, 426, 426, 0, 0` — idêntico nas 5 páginas afetadas (mesmo padrão geométrico, mesmo comprimento de texto duplicado: 146+96 = 242 caracteres × 2 cópias × ~2 linhas por caractere ≈ 426 após deduplicação da contagem exata do algoritmo do MarkItDown).
- Ocorrências de espaço duplo entre letras minúsculas (regex `[a-zà-ú] {2}[a-zà-ú]`) no texto bruto do MarkItDown, por página (1–7): `61, 103, 144, 123, 71, 16, 0`. **Achado novo desta investigação:** ao contrário do que o diagnóstico anterior presumiu ("0 ocorrências nas páginas 6–7"), a página 6 **também** tem espaçamento duplo no texto bruto do MarkItDown (16 ocorrências) — a extração de texto justificado do MarkItDown/`pdfminer` produz espaço duplo de forma geral, não é exclusiva das páginas com o carimbo duplicado. A página 6 só não exibe esse defeito no **Markdown final** porque, nela, uma salvaguarda já existente no pipeline substitui o texto bruto do MarkItDown pelo texto geométrico do PyMuPDF (ver ETAPA 3) — o que não acontece nas páginas 1–5, cuja causa raiz é isolada abaixo.
- Relação geométrica com o carimbo: confirmada — a origem exata das ~426 linhas de caractere único é a extração vertical (`dir=(0,-1)`) dos dois blocos duplicados; nenhuma outra parte do texto (o corpo da decisão, extraído de blocos horizontais não duplicados) produz esse padrão.

## ETAPA 3 — Rastreamento pelo pipeline

Em `converter.py::convert_document`, para páginas `Metodo.texto_nativo`:

```python
reference_content = _geometric_reading_order_text(page)      # PyMuPDF, blocos brutos
...
result = native_engine.convert(page_path)                     # MarkItDown — AQUI o ruído já existe
content = result.text_content or ""
if _has_native_reading_order_defect(content, reference_content) or ...:
    content = reference_content                                # salvaguarda 1 (baseada em overlap léxico)
content = recompose_native_paragraphs(content, native_blocks, ...)  # salvaguarda 2 (fallback geométrico interno)
```

Instrumentado diretamente (sem nenhuma alteração de código, apenas chamadas às funções já existentes, importadas):

| Página | `_lexical_overlap(content, reference_content)` | `_has_native_reading_order_defect` | `recompose_native_paragraphs` usa geométrico? | Espaço duplo sobrevive? |
| --- | --- | --- | --- | --- |
| 1 (afetada) | **0,4893** | `False` (overlap < 0,98) | Não | Sim (61 ocorrências, idêntico ao bruto) |
| 6 (não afetada) | **1,0000** | `True` (mesmos tokens, ordem diferente) | Sim | Não (0 — colapsado para espaço simples) |

**Primeiro estágio em que o ruído aparece:** dentro do próprio `native_engine.convert()` (MarkItDown/`pdfminer`) — confirmado isoladamente, sem nenhum código deste pipeline envolvido. Nenhuma função de `cleaner.py` ou `converter.py` introduz, agrava ou deveria remover esse ruído; elas apenas recebem e (nesta página) propagam o resultado já corrompido, porque suas condições de disparo não são satisfeitas.

**Por que as salvaguardas existentes não disparam:** ambas comparam contagem/sobreposição de tokens (regex `\w+`) entre o texto candidato e uma referência geométrica. Nas páginas 1–5, o MarkItDown não reordena palavras (o que a salvaguarda foi desenhada para pegar) — ele fragmenta ~242 caracteres em ~426 "tokens" de um caractere cada. Isso não é uma reordenação de tokens iguais; é uma inflação do universo de tokens. Testado explicitamente: mesmo removendo as duas cópias duplicadas da lista de blocos brutos do PyMuPDF *antes* de gerar o texto de referência (simulando uma correção geométrica upstream), a sobreposição léxica entre o texto bruto do MarkItDown e essa referência deduplicada permanece em **0,4813** — estatisticamente idêntica a 0,4893. **Conclusão importante:** o mecanismo de salvaguarda existente (comparação por sobreposição léxica) não pode ser "consertado" ajustando a referência geométrica; ele é estruturalmente incapaz de detectar este padrão, porque o denominador da fração já está dominado pelo próprio ruído de caracteres isolados presente no texto do MarkItDown, não pela referência. Qualquer critério de correção precisa disparar a partir da geometria do PDF (que já indica a causa) e não da comparação de tokens pós-extração.

**Ponto tecnicamente correto para futura intervenção:** o ponto onde `native_blocks_with_x0`/`reference_content` já são calculados, em `converter.py`, imediatamente antes de `native_engine.convert()` ser chamado — um novo sinal de disparo, independente de sobreposição léxica, calculado unicamente a partir da geometria dos blocos do PyMuPDF (disponível antes mesmo de invocar o MarkItDown).

## ETAPA 4 — Critérios candidatos e blast radius

Avaliados contra os 8 PDFs (4 processuais + 4 canônicos, 270 páginas):

| PDF | Páginas | Blocos verticais totais (`dir != (1,0)`) | Páginas com blocos verticais de bbox quase-idêntico duplicado (tolerância 2pt) |
| --- | --- | --- | --- |
| `001-007-Petição Inicial.pdf` | 7 | 7 | — |
| `012-015-Testamento Publico.pdf` | 4 | 4 | — |
| `086-096-CONTESTAÇÃO...pdf` | 11 | 11 | — |
| `100-106-DECISÃO.pdf` | 7 | 27 | **páginas 1, 2, 3, 4, 5** (2 pares por página) |
| `AINTARESP_1462304-PA.pdf` | 12 | 0 | — |
| `REsp_1704551-SP.pdf` | 14 | 0 | — |
| `Inf0024E.pdf` | 29 | 0 | — |
| `L10.406_CC_2002.pdf` | 186 | 0 | — |

**Candidato A — rotação/direção isolada (`dir != (1,0)`):** presente em 4 dos 8 PDFs (todos os processuais têm ao menos 1 carimbo vertical por página — comportamento normal e correto do padrão e-SAJ/TJSP). **Blast radius se usado isoladamente: alto e incorreto** — atingiria as 29 páginas processuais inteiras, incluindo as páginas 6–7 de `100-106-DECISÃO.pdf` que já são corretamente processadas hoje. **Descartado.**

**Candidato B — sequência de muitos caracteres isolados no texto já produzido pelo MarkItDown (ex.: >N linhas de 1 caractere):** plausível como sinal *complementar*, mas não teria como distinguir com segurança um documento legitimamente denso em siglas/números isolados de um caso de corrupção — não avaliado como critério único porque o Candidato D (abaixo) já resolve o problema na origem, com geometria disponível antes mesmo de chamar o MarkItDown.

**Candidato C — posição marginal (bbox próximo da borda direita da página):** presente em todos os 4 PDFs processuais (o padrão e-SAJ sempre carimba na margem direita) — mesmo problema de blast radius do Candidato A. **Descartado isoladamente.**

**Candidato D — duplicação geométrica de blocos não horizontais (rotação + bbox quase-idêntico) — critério escolhido:** exige simultaneamente (i) `dir != (1.0, 0.0)` e (ii) outro bloco na mesma página com bbox igual em até ~2pt nas 4 coordenadas. Testado nos 8 PDFs (270 páginas): dispara **exclusivamente** nas páginas 1–5 de `100-106-DECISÃO.pdf` (5 páginas de 270, 1,85%). Zero ocorrências nas páginas 6–7 do mesmo documento, zero nos outros 3 PDFs processuais (22 páginas com blocos verticais legítimos e não duplicados), zero nos 4 PDFs canônicos (241 páginas, nenhum bloco vertical). **Não usa** nome do documento, número de página, texto da assinatura, nomes de pessoas ou número do processo — apenas geometria (direção de escrita + coincidência de posição). **Critério recomendado.**

**Trechos que seriam alterados pelo Candidato D:** apenas `100-106-DECISÃO.pdf`, páginas 1, 2, 3, 4 e 5 — em cada uma, os dois blocos verticais duplicados (`(544.4, 202.8, 555.4, 785.3)` e `(554.8, 436.6, 565.8, 785.3)`) teriam uma das duas cópias descartada antes da extração nativa. Nenhum outro trecho, de nenhum dos 8 PDFs, seria tocado.

## ETAPA 5 — Relação entre C.1 e C.2

Verificação direta (não por proximidade visual): comparando o texto de referência geométrico do PyMuPDF (`_geometric_reading_order_text`, usado como *fallback* quando a salvaguarda dispara) contra o texto bruto do MarkItDown na página 1, o texto de referência **já não tem espaçamento duplo** (1 ocorrência residual, um espaço à direita antes de quebra de linha — não é espaçamento interno de palavra) — ou seja, o espaçamento duplo é uma característica exclusiva da extração do MarkItDown/`pdfminer`, nunca do PyMuPDF.

Na página 6, onde a salvaguarda já dispara hoje (overlap = 1,0, `_has_native_reading_order_defect` = `True`), o conteúdo é substituído pelo texto geométrico do PyMuPDF, e o espaçamento duplo desaparece (16 → 0 ocorrências) **sem nenhuma regra dedicada a espaçamento** — é um efeito colateral de `recompose_native_paragraphs` normalizar `\s+` → espaço único ao reconstruir cada linha física a partir da geometria.

Na página 1, como demonstrado na ETAPA 3, nem a salvaguarda de `converter.py` nem o *fallback* interno de `recompose_native_paragraphs` disparam (overlap = 0,49 em ambos os casos), então o conteúdo bruto do MarkItDown — com o ruído de caracteres isolados **e** o espaçamento duplo — atravessa o pipeline sem qualquer normalização.

**Conclusão da ETAPA 5: (A)** — o espaçamento duplo desaparece naturalmente ao corrigir corretamente C.1, porque ambos compartilham não apenas a causa raiz upstream (extração do MarkItDown/`pdfminer`), mas o **mesmo mecanismo de não-correção** (as duas salvaguardas de *fallback* geométrico do pipeline, ambas neutralizadas pela mesma inflação de tokens). Uma correção que restaure o disparo do *fallback* geométrico nas páginas 1–5 (Candidato D) resolve os dois achados com uma única regra, sem necessidade de uma segunda regra específica para espaçamento.

## CONCLUSÃO

**A) CRITÉRIO SEGURO ENCONTRADO**

- **Causa raiz:** duas cópias idênticas e sobrepostas de um bloco de texto vertical (rotação 90°, `dir=(0,-1)`) no PDF de origem, nas páginas 1–5 de `100-106-DECISÃO.pdf`. O extrator nativo do MarkItDown (`pdfminer`) intercala os caracteres dos dois blocos sobrepostos em ordem corrompida (~426 linhas de um caractere cada, cada um duplicado, em ordem invertida). A mesma corrupção neutraliza as duas salvaguardas de *fallback* geométrico já existentes no pipeline, porque ambas dependem de sobreposição léxica de tokens (limiar 0,98) e a fragmentação em caracteres isolados derruba essa sobreposição para ~0,49 — não é possível "consertar" a referência geométrica para recuperar esse limiar; o mecanismo de comparação léxica é estruturalmente incapaz de cobrir este padrão.
- **Critério:** geométrico — duas ou mais linhas de texto não horizontal (`dir != (1.0, 0.0)`) na mesma página com bbox quase idêntico (tolerância ~2pt), calculado a partir de `page.get_text("dict")` **antes** de chamar o MarkItDown.
- **Ponto de implementação:** `convert_document()` em `converter.py`, junto ao cálculo já existente de `native_blocks_with_x0`/`reference_content` para páginas `Metodo.texto_nativo`, antes de `native_engine.convert()`.
- **Positivos:** resolve C.1 e C.2 simultaneamente com uma única regra geométrica; zero dependência de nome de documento, número de página, texto de assinatura, nome de pessoa ou número de processo; zero falsos positivos medidos nas 270 páginas do corpus de 8 PDFs avaliado; generaliza um padrão arquitetural já existente e validado (disparo de *fallback* geométrico) em vez de introduzir um mecanismo novo.
- **Negativos/riscos:** (1) qualquer alteração no caminho de *fallback* geométrico toca um código já calibrado por 4 mudanças arquivadas anteriores contra o corpus canônico — exigiria regressão completa do corpus canônico (241 páginas) antes de qualquer implementação; (2) a tolerância de ~2pt para "bbox quase idêntico" é um novo limiar ajustável, validado contra apenas uma instância real do padrão — um documento futuro com posicionamento ligeiramente diferente entre as duas cópias poderia escapar da detecção — direção de erro segura (falso negativo), não falso positivo; (3) descartar um bloco duplicado pressupõe que a duplicata é sempre uma repetição redundante do mesmo conteúdo — recomenda-se exigir bbox **e** texto idênticos (já satisfeito no caso observado) antes de descartar, não bbox isoladamente.
- **Blast radius:** 5 de 270 páginas avaliadas (100-106-DECISÃO.pdf, páginas 1–5); zero alteração nas páginas 6–7 do mesmo documento e nos outros 7 PDFs.
- **Relação C.1/C.2:** mesma causa raiz e mesmo mecanismo de não-correção (ETAPA 5); C.2 não exige critério próprio.
- **Proposta mínima futura (não implementada aqui):** nova mudança OpenSpec dedicada, com testes de regressão que reproduzam a geometria exata (dois blocos verticais sobrepostos, bbox e texto idênticos) como fixture mínima, implementando uma função `_has_duplicated_rotated_block(page) -> bool` (ou equivalente) em `converter.py` que, quando `True`, descarta a chamada a `native_engine.convert()` para a página e usa o texto geométrico do PyMuPDF (com os blocos duplicados já deduplicados) como `content` antes de `recompose_native_paragraphs`. Validar contra o corpus canônico completo (241 páginas, 4 documentos) para garantir zero regressão, e contra os 3 outros PDFs processuais (22 páginas com carimbos verticais legítimos e não duplicados) para confirmar que nenhum deles é afetado.

## Verificação de não regressão (fase de diagnóstico)

Nenhum arquivo de `src/`, `tests/`, `output/`, `logs/` ou do corpus canônico foi alterado ou reconvertido durante o diagnóstico. Todas as inspeções usaram cópias de página isoladas em diretórios temporários (`tempfile.mkdtemp()`), nunca sobrescrevendo `input/` nem `output/`. `git status --short` ao final da fase de diagnóstico listou apenas os três arquivos novos de `openspec/changes/fix-rotated-digital-signature-noise/` (`proposal.md`, `design.md`, `tasks.md`), commitados localmente (`93a077d`), sem push, sem arquivar.

## Autorização de implementação (2026-08-12)

Usuário aprovou explicitamente, via `/goal`, avançar de diagnóstico para TDD + implementação mínima **nesta mesma mudança** (não criar mudança OpenSpec separada). Decisões confirmadas na aprovação, todas já sustentadas pela evidência das ETAPAS 1–5 acima:

- **Causa raiz confirmada:** duas cópias sobrepostas e byte-idênticas de um bloco vertical de assinatura digital (`dir=(0,-1)`, Helvetica 8pt) nas páginas 1–5 de `100-106-DECISÃO.pdf`; MarkItDown/`pdfminer` intercala os caracteres dos dois blocos em ordem corrompida.
- **C.1/C.2 = mesmo defeito:** confirmado quantitativamente na ETAPA 5 — quando a salvaguarda geométrica correta é usada (como já acontece hoje na página 6), ambos desaparecem sem regra específica de espaçamento. Esta implementação não cria nenhuma regra separada para C.2.
- **Critério aprovado (Candidato D da ETAPA 4):** detectar duplicação geométrica de blocos **não horizontais** (`dir != (1.0, 0.0)`) com bbox praticamente idêntico/sobreposto (tolerância ~2pt) na mesma página, exigindo também texto idêntico entre o par (recomendação de segurança do "Negativos/riscos" item 3 da CONCLUSÃO, para não descartar por bbox isoladamente).
- **Alternativas descartadas (ETAPA 4), reconfirmadas nesta aprovação:** rotação/direção isolada (Candidato A) e posição marginal isolada (Candidato C) — blast radius alto, atingiriam os carimbos verticais legítimos e não duplicados presentes nas 29 páginas dos 4 PDFs processuais; sequência de caracteres isolados no texto do MarkItDown (Candidato B) — não avaliado como critério único por não ter como distinguir com segurança de conteúdo legitimamente denso em siglas/números.
- **Blast radius medido, reconfirmado:** 8 PDFs, 270 páginas, 5 páginas afetadas (`100-106-DECISÃO.pdf`, páginas 1–5), 0 falsos positivos nas outras 265.
- **Ponto de implementação:** `convert_document()` em `converter.py`, junto ao cálculo já existente de `reference_content`/`native_blocks_with_x0` para páginas `Metodo.texto_nativo`, **antes** de `native_engine.convert()` ser chamado — de forma que, quando a duplicação geométrica é detectada, o MarkItDown nunca é invocado para aquela página (o `content` é montado diretamente a partir do texto geométrico do PyMuPDF, já deduplicado). Isso evita qualquer reescrita/reconstrução do PDF (fora de escopo) e reaproveita a mesma correlação já usada e validada em `_sorted_native_text_blocks` (ordenar `page.get_text("blocks")` e `page.get_text("dict")["blocks"]` pela mesma chave `(round(y0,1), x0)` e cruzar por posição) — confirmado empiricamente 0 desalinhamentos nos 30 blocos da página 1.
- **Testes e validações exigidos (registrados como tarefas em `tasks.md`):** testes unitários novos em `tests/test_converter.py` (função de detecção geométrica e a decisão de bypass do MarkItDown) e em `tests/test_cleaner.py`/`tests/test_converter_integration.py` se aplicável; suíte completa; `openspec validate --all --strict`; reconversão dos 4 PDFs de `input/processos_auditoria/` e regressão byte-a-byte dos 4 PDFs canônicos de `output/`, todos com `--no-ocr`; segunda reconversão para confirmar idempotência.
