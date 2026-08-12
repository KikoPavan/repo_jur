## Pré-voo

- `git status --short`: limpo.
- `git log --oneline -5`:
  ```
  c802d23 docs: record audit-scanned-pdf-ocr-support archival in LOOPS.md
  ae37446 chore(openspec): archive audit-scanned-pdf-ocr-support
  de1bf36 docs(openspec): add diagnostic audit-scanned-pdf-ocr-support change
  a228d68 docs: record rotated-signature noise archival in LOOPS.md
  381579d chore(openspec): archive fix-rotated-digital-signature-noise
  ```
- `openspec validate --all --strict`: `1 passed, 0 failed` (`spec/juridical-pdf-conversion`).
- `uv run pytest tests/`: `364 passed`.
- Provider/modelo/configuração confirmados sem imprimir a credencial:
  ```
  GEMINI_API_KEY present: True (length: 39)
  GEMINI_MODEL: gemini-3-flash-preview
  GEMINI_BASE_URL: https://generativelanguage.googleapis.com/v1beta/openai/
  OCR_PROMPT_FILE: prompts/ocr_literal_ptbr.txt
  OCR_ENABLED: true
  ```
- Prompt não alterado: `prompt_sha256` no relatório desta execução (`34c6b4c284bc3ec8070ea7f8523684067c8471f6d820d83ab97c76b9e7dc6233`) é idêntico ao registrado na auditoria `--no-ocr` anterior (mesma mudança arquivada `audit-scanned-pdf-ocr-support`).
- Saída isolada via `OUTPUT_DIR=openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/output`, `LOGS_DIR=.../audit_output/logs`, nunca `output/`/`logs/` canônicos.

## Execução

Comando único, executado uma vez, sem `--no-ocr`:

```
OUTPUT_DIR=openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/output \
LOGS_DIR=openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/logs \
TEMP_DIR=var/tmp \
uv run converter-juridico --allow-partial "input/processos_auditoria/012-015-Testamento Publico.pdf"
```

- Início: `2026-08-12T20:08:06.450848+00:00` — Fim: `2026-08-12T20:09:35.829578+00:00` — Duração total: `89.378s`.
- 4 requisições HTTP `POST https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`, todas `200 OK`. Nenhum retry, nenhum erro de API.
- `ocr.enabled: true`, `ocr.provider: openai-compatible`, `ocr.model: gemini-3-flash-preview` (relatório completo em `audit_output/logs/012-015-Testamento Publico.report.json`).
- Status final do CLI: exit code `0`; `status: sucesso` no relatório.

| Pág. | Método (rota) | Chamou OCR | Status | Caracteres | Duração | Avisos/Erros |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | hibrido | sim | sucesso | 4104 | 18.338s | nenhum |
| 2 | hibrido | sim | sucesso | 4212 | 43.548s | nenhum |
| 3 | hibrido | sim | sucesso | 3877 | 22.756s | nenhum |
| 4 | hibrido | sim | sucesso | 1036 | 4.569s | nenhum |

Soma das durações por página: 89.211s; overhead de inspeção/composição/validação: ~167ms.

## Auditoria página a página

Metodologia: cada página do PDF original foi renderizada a 150 DPI (`page.get_pixmap(dpi=150)`, PyMuPDF, sem OCR) e comparada visualmente, linha a linha, com o bloco correspondente do Markdown gerado (`openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/output/012-015-Testamento Publico.md`). Nenhuma correção manual foi feita no Markdown.

### Página 1 (`[[Pág. 1]]`, linhas 1–447) — **APROVADA COM RESSALVAS**

- **Conteúdo substantivo (linhas 4–26):** cabeçalho do cartório (Oficial de Registro Civil, Manduri-SP, Comarca de Piraju, Silvio da Silva Brandini Junior), "LIVRO 132 CERTIDÃO PÁGINAS 043/045", título "TESTAMENTO PÚBLICO QUE FAZ JURACI PIRES PAVAN", e o corpo inicial do ato (qualificação completa da testadora — RG 4.294.873-SSP/SP, CPF 793.933.908-78, endereço, CEP — e das duas testemunhas — Jonas Elias Petito e Vânia de Fátima Giardullo, com RGs/CPFs/endereços/CEPs completos) — **conferido, 100% correto contra a imagem**, incluindo pontuação, negrito/sublinhado nos termos de destaque (`OUTORGANTE TESTADORA`, `JURACI PIRES PAVAN`, `JONAS ELIAS PETITO`, `VÂNIA DE FÁTIMA GIARDULLO`). O parágrafo é corretamente interrompido no meio da frase "...inscrito no" — ponto exato em que a página 1 termina na imagem original, continuando naturalmente no início da página 2.
- **Texto omitido:** nenhum no corpo substantivo.
- **Texto inventado:** nenhum.
- **Duplicações:** nenhuma no corpo substantivo.
- **Nomes próprios/números/datas:** todos conferidos e corretos (ver acima).
- **Rótulos `[Margem Esquerda]:`/`[Rodapé]:`** (linhas 16–24): o modelo optou por identificar e rotular os elementos periféricos da página — "REPÚBLICA FEDERATIVA DO BRASIL / VALIDO EM TODO TERRITÓRIO NACIONAL..." (marca d'água lateral esquerda) e "União Internacional do Notariado Latino (Fundado em 1948) / AVENIDA FRANCISCO ZANARDO, 1215 - RESIDENCIAL CLÉLIA / MANDURI - SP - CEP: 18780-304" (rodapé) — conteúdo correto, rótulos não fazem parte do prompt mas não introduzem erro nem invenção de conteúdo jurídico.
- **`[ilegível]` (linha 25):** usado corretamente para uma linha de rodapé (provável telefone) cortada/ilegível na imagem original.
- **RESSALVA (linhas 28–447):** após `[End OCR]*` (linha 26), **209 linhas de ruído de 1 caractere cada** (`.`, `6`, `3`, `1`, `fls. 120`, `6`, `2`, `8`, ... até a linha 447). Concatenadas e invertidas, essas linhas reconstroem a etiqueta de autenticação e-SAJ vertical da página (confirmado por reconstrução determinística, ver seção "Causa raiz" abaixo) — ou seja, **não é conteúdo inventado**, é a mesma etiqueta e-SAJ já lida corretamente pelo PyMuPDF nas auditorias anteriores, mas corrompida pelo motor. Como consequência prática, essa etiqueta (que contém protocolo, assinante digital e data/hora — informação com valor probatório) **fica efetivamente perdida como texto legível** nesta saída: não está transcrita corretamente, nem foi marcada como `[ilegível]`.
- **`[[Pág. 1]]`:** presente, correto, único.

### Página 2 (`[[Pág. 2]]`, linhas 448–876) — **APROVADA COM RESSALVAS**

- **Conteúdo substantivo (linhas 451–454):** continuação exata do parágrafo interrompido na página 1 ("CPF/MF sob o n° 835.259.478-87..."), descrição completa do imóvel urbano (lote, área 2.352,00 m², rumos e distâncias — 51°07'SE 42,00m, 38°53'NE 56,00m, 51°07'NW 42,00m, 38°53'SW 56,00m —, matrícula n° 7.013), da casa (dois pavimentos, treze cômodos, matrícula n° 907), cláusulas QUARTA e QUINTA, substituição testamentária por Philipp Holzhausen Pavan (CNH 02321419911-DETRAN/SP, RG 32293003-SSP/SP, CPF 315.733.428-07, endereço completo) — **conferido, 100% correto contra a imagem**, incluindo os símbolos de grau/minuto (°/') das medidas geodésicas e a formatação em negrito/sublinhado dos itens a)/b)/c).
- **Texto omitido/inventado/duplicado:** nenhum no corpo substantivo.
- **RESSALVA (linhas 457–876):** mesmo padrão de ruído da página 1 — 209 linhas de 1 caractere após `[End OCR]*` (linha 455), mesma causa raiz.
- **`[[Pág. 2]]`:** presente, correto, único.

### Página 3 (`[[Pág. 3]]`, linhas 877–1326) — **APROVADA COM RESSALVAS**

- **Conteúdo substantivo (linhas 880–904):** cabeçalho do cartório repetido (correto — não é removido pelo cleaner, pois não é um cabeçalho verbatim-repetido isolado no início de cada bloco de conteúdo, mas parte do conteúdo transcrito por OCR desta página específica), continuação do parágrafo (qualificação de Maria Eulina Holzhausen Pavan), cláusula SEXTA (nomeação de testamenteiro), valores da escritura (todos os 9 valores — Tabelião R$ 1.306,98, Estado R$ 371,46, Sefaz R$ 254,24, ISS R$ 65,34, MP R$ 62,74, Reg. Civil R$ 68,79, Trib. Justiça R$ 89,70, Santa Casa R$ 13,07, Total R$ 2.232,32 — conferidos, 100% corretos), protocolo n° 6214, selo digital, assinaturas nomeadas (Juraci Pires Pavan, Jonas Elias Petito, Vânia de Fátima Giardullo), certidão final (todos os 9 emolumentos — R$ 55,70/15,83/10,83/2,78/2,67/2,93/3,82/0,56/95,12 — conferidos, corretos), data "Manduri/SP, 02 de março de 2.026", Ordem de Serviço n° 8283, Selo Digital n° 1233981CE000000001844626I, Guia 09/03/2026 — **conferido, 100% correto contra a imagem**.
- **`[ilegível]` (5 ocorrências, linhas 885, 891, 893, 895, 904):** todas criteriosas — (885) elemento gráfico/selo no topo da página, sem texto associado na imagem; (891, embutido no parágrafo) rubrica manuscrita sobre o nome do escrevente na assinatura; (893) `"EM TEST [ilegível] DA VERDADE"` — a rubrica manuscrita cruza exatamente sobre a palavra que seria "TESTEMUNHO" na fórmula notarial padrão; observação de severidade muito baixa: embora "TESTEMUNHO" seja uma fórmula fixa e inequívoca neste contexto, o modelo optou pela transcrição mais conservadora (marcar como ilegível em vez de completar por inferência) — consistente com a instrução do prompt de não completar trechos, não é um erro; (895, 904) rubrica sobre o nome da escrevente e rodapé cortado, mesmo padrão da página 1.
- **Texto omitido/inventado/duplicado:** nenhum no corpo substantivo.
- **RESSALVA (linhas 907–1326):** mesmo padrão de ruído — 209 linhas de 1 caractere após `[End OCR]*` (linha 905), mesma causa raiz.
- **`[[Pág. 3]]`:** presente, correto, único.

### Página 4 (`[[Pág. 4]]`, linhas 1327–1758) — **APROVADA COM RESSALVAS**

- **Conteúdo substantivo (linhas 1330–1337):** página quase inteiramente em branco na imagem original (apenas cabeçalho "REPÚBLICA FEDERATIVA DO BRASIL / Estado de São Paulo", um QR Code e o texto abaixo dele) — corretamente transcrita apenas com o texto real: número do selo digital "1233981CE000000001844626I" e a instrução "Para conferir a procedência deste documento efetue a leitura do QR Code impresso ou acesse o endereço eletrônico https://selodigital.tjsp.jus.br" — **conferido, 100% correto**. O modelo corretamente **não tentou decodificar o conteúdo do QR Code** (não é texto) nem inventou texto para a grande área em branco/marca d'água/rabisco de assinatura visível na imagem.
- **Texto omitido/inventado/duplicado:** nenhum.
- **RESSALVA (linhas 1340–1758):** mesmo padrão de ruído — 209 linhas de 1 caractere após `[End OCR]*` (linha 1338), mesma causa raiz.
- **`[[Pág. 4]]`:** presente, correto, único.

## Validação estrutural

| Critério | Resultado |
| --- | --- |
| 1. Exatamente 4 marcadores `[[Pág. N]]` | ✅ confirmado (`grep -c` = 4) |
| 2. Ordem 1→4 | ✅ confirmado (linhas 1, 448, 877, 1327, nessa ordem) |
| 3. Nenhuma página ausente | ✅ (1, 2, 3, 4 todas presentes) |
| 4. Nenhuma página duplicada | ✅ (nenhum número repetido) |
| 5. OCR usado somente nas 4 páginas necessárias | ✅ (as 4 páginas do único PDF processado, todas roteadas `hibrido`; nenhum outro PDF do corpus foi tocado) |
| 6. Nenhum arquivo canônico alterado | ✅ (`git status --short output/ logs/` vazio; saída isolada em `openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/`) |
| 7. Nenhum código alterado | ✅ (`git status --short src/ tests/` vazio) |
| `[[TEXTO ILEGÍVEL]]` (marcador de bloqueio) | 0 ocorrências — nenhuma página precisou de bloqueio |
| `[ilegível]` (marcação pontual do prompt) | 6 ocorrências, todas criteriosas (ver auditoria por página) |

## Causa raiz do ruído de fragmentação (evidência reproduzível)

Isolado e reproduzido sem qualquer código deste pipeline entre a chamada e o resultado — a corrupção já está presente no texto devolvido pelo pacote de terceiros `markitdown-ocr` antes de qualquer processamento de `src/pipeline_juridico/`.

**Reconstrução determinística:** concatenando e invertendo as 209 linhas de ruído da página 1, o resultado contém, em ordem, fragmentos legíveis da etiqueta e-SAJ real da página (`rierntoooér icgiónpiala,daoceorsisgienoal,sitasesihtntapds://...esaj.tjsp.jus.br/pastadigital/pg/abrirConferenciaDocumento.do...processo...1000386...protocolado...2026...18:09...número1000386`) — confirmando que o ruído não é conteúdo inventado, é a mesma etiqueta de autenticação vertical já lida corretamente pelo PyMuPDF puro (auditorias anteriores), porém fragmentada caractere a caractere e em ordem revertida.

**Localização da causa, no código-fonte instalado do pacote `markitdown-ocr` (`_pdf_converter_with_ocr.py`, não em `src/pipeline_juridico/`):**

```python
# markitdown_ocr/_pdf_converter_with_ocr.py, dentro de convert(), ramo "há imagens na página":
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

Esse agrupamento por coordenada Y (via `pdfplumber`) assume texto horizontal: para uma linha de texto **rotacionada 90°** (o carimbo lateral e-SAJ), a coordenada `top` de cada caractere sucessivo varia amplamente ao longo da própria linha (porque a linha "anda" verticalmente na página), ultrapassando o limiar de 2pt quase a cada caractere — produzindo uma "linha" de 1 caractere por caractere real. Esses fragmentos são então ordenados por posição Y e intercalados com o bloco `*[Image OCR]\n...\n[End OCR]*` da transcrição real por LLM — como a maior parte dos fragmentos de 1 caractere acaba posicionada, na ordenação final, após o bloco de OCR de imagem, o resultado observado é: conteúdo OCR legível primeiro, seguido do bloco de ruído.

**Relação com o achado C.1 já corrigido (`fix-rotated-digital-signature-noise`):** mesma classe de defeito (extração de texto rotacionado quebrando por biblioteca de terceiros), mas:
- C.1 (corrigido): ocorria no caminho `texto_nativo`, no motor MarkItDown nativo (via `pdfminer` diretamente), e **exigia duas cópias idênticas e sobrepostas** da mesma linha rotacionada para disparar a corrupção (confirmado no design da mudança arquivada).
- Este achado (novo, não corrigido): ocorre no caminho `hibrido`/`ocr_integral`, dentro do plugin de terceiros `markitdown-ocr` (via `pdfplumber`, biblioteca diferente de `pdfminer` direto), e **não exige duplicação** — uma única linha rotacionada já é suficiente, porque o mecanismo de agrupamento por Y do `pdfplumber` é ainda mais sensível a texto vertical do que o motor usado no caminho nativo.
- A salvaguarda já implementada em `converter.py` (`_has_duplicated_rotated_block`, `_geometric_reading_order_text`) só é chamada quando `method is Metodo.texto_nativo` (ver `convert_document`, linhas ~365–369 e ~379) — nunca no ramo `hibrido`/`ocr_integral`, que usa `content = "" if method is Metodo.erro else raw_content` diretamente sobre o resultado do `ocr_engine.convert(...)`, sem nenhuma verificação de qualidade além de `verify_ocr_evidence`/`scan_ocr_warnings` (que só detectam ausência total de conteúdo ou marcadores de falha explícitos do plugin — não detectam ruído de fragmentação char-por-linha, que tecnicamente não dispara nenhum dos 3 marcadores-sentinela existentes).

## Problemas do OCR vs. problemas do cleaner

- **OCR (motor/plugin, fora de `src/pipeline_juridico/`):** o ruído de fragmentação em si — 100% atribuível ao `markitdown-ocr`/`pdfplumber`, conforme reproduzido acima.
- **Pipeline (`src/pipeline_juridico/`):** ausência de uma salvaguarda equivalente à já existente para `texto_nativo` no ramo `hibrido`/`ocr_integral` — não é um bug introduzido pelo pipeline, é uma lacuna de cobertura (a proteção existe, mas só para uma das duas rotas que podem produzir texto a partir da mesma classe de defeito upstream).
- **Cleaner (`cleaner.py`):** não aplicável — `clean_markdown`/`remove_repetitive_margins` não têm mecanismo para reconhecer nem remover esse padrão (linhas de 1 caractere, não-repetitivas verbatim entre páginas de forma que o mecanismo de margem já existente reconheça). Não é um defeito do cleaner; é um tipo de ruído fora do escopo do que o cleaner foi desenhado para tratar.

## Achados secundários

- **Vazamento do marcador interno `[End OCR]*`** (severidade baixa): esse token é um artefato de formatação do plugin `markitdown-ocr` (usado para delimitar internamente onde termina um bloco de OCR de imagem), não faz parte do conteúdo do documento, e aparece nas 4 páginas do Markdown final publicado.
- **Variação não determinística observacional** (severidade muito baixa, esperada): o mesmo texto estático de rodapé ("União Internacional do Notariado Latino") foi transcrito como "(Fundado em 1948)" na página 1 e "(Fundada em 1948)" na página 3 — consistente com o risco já formalmente aceito pela spec do projeto ("Não prometer fidelidade absoluta ou determinismo para resultados produzidos por OCR baseado em LLM").

## Verificação de não regressão

- `src/`, `tests/`, `prompts/ocr_literal_ptbr.txt`, `pyproject.toml`, roteamento, cleaner, `openspec/specs/`: não tocados.
- `output/`, `logs/` (canônicos): não tocados — toda a saída desta validação está isolada em `openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/`.
- Nenhum outro PDF de `input/processos_auditoria/` foi processado.
- Nenhuma segunda chamada de OCR foi feita para tentar melhorar ou confirmar o resultado (instrução explícita do usuário: "Nesta etapa faça apenas UMA conversão real").

## `git status --short` ao final

Ver saída no encerramento desta mudança — o único diretório novo esperado é `openspec/changes/validate-supervised-ocr-testamento-publico/` (esta mudança, incluindo `audit_output/`); nenhum arquivo em `src/`, `tests/`, `output/`, `logs/`, `openspec/specs/` ou no corpus canônico deve aparecer.
