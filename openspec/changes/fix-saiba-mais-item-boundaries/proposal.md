## Why

A auditoria do corpus encontrou, em `output/Inf0024E.md`, itens independentes da seção `SAIBA MAIS` fundidos indevidamente na mesma linha/parágrafo — por exemplo, dois títulos de "Jurisprudência em Teses" e um "Informativo de Jurisprudência n. 751" colados em uma única frase corrida, ou um precedente `CC 159976/SP, ... DJe 16/04/2019` colado ao "Informativo de Jurisprudência n. 474" seguinte. Diagnóstico geométrico via PyMuPDF (`page.get_text("dict")`, páginas 4, 14 e 18 de `input/Inf0024E.pdf`) confirmou a causa raiz: `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) estima a altura de cada linha física de um bloco PyMuPDF dividindo a altura total do bloco pelo número de linhas físicas (`line_height = (y1 - y0) / len(physical_lines)`), sem acesso à geometria real de cada linha. Para itens de `SAIBA MAIS` que quebram em 2 linhas físicas dentro de um único bloco, essa divisão uniforme superestima a altura real de cada linha (12,5pt interpolado vs. 10pt real, medido via bounding boxes reais de linha), inflando o limiar de junção da comparação seguinte (`gap <= previous_height * 1.2`) de ~12pt para exatamente 15pt — que coincide, ponto a ponto, com o espaçamento real de 15pt usado entre itens distintos da lista, causando a fusão indevida.

Duas correções mais amplas foram investigadas e descartadas por alterarem, sem necessidade, decisões de junção já em produção em outras partes do corpus (ver `design.md` para a evidência completa): (1) substituir a interpolação por geometria real de linha em todo o pipeline gera 44 mudanças de decisão de junção nos 4 PDFs do corpus, incluindo páginas do índice do Código Civil já protegidas por mudança arquivada anterior; (2) apertar o limiar de empate (`<=` para `<`) quebra uma continuação de parágrafo legítima em `AINTARESP_1462304-PA.pdf` (página 3) que depende do mesmo comportamento de interpolação. A correção adotada é local ao literal `SAIBA MAIS` — um cabeçalho editorial genérico de qualquer informativo do STJ (não específico deste arquivo, número de edição ou conteúdo de item), do mesmo tipo estrutural que os rótulos já reconhecidos por `native_label_pattern` (`PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `DESTAQUE`) — confirmando que a substring `SAIBA MAIS` não ocorre em nenhum dos outros 3 PDFs do corpus de regressão.

## What Changes

- Adicionar, dentro de `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), uma nova condição de exclusão à junção geométrica: dentro do intervalo delimitado por um bloco cuja única linha física é exatamente `SAIBA MAIS` (já reconhecido por `native_label_pattern`) e o próximo bloco cuja primeira linha física também corresponda a `native_label_pattern`, nunca unir dois blocos DIFERENTES entre si — apenas a quebra de linha física dentro do mesmo bloco (o mesmo item de lista) continua sendo unida normalmente.
- Nenhuma lista fixa de títulos, números de edição ou vocabulário de item (`Informativo`, `Jurisprudência em Teses`, `/`, `DJe`) é usada para decidir a fronteira — a fronteira é sempre a origem do bloco PyMuPDF (um item = um bloco, confirmado empiricamente nos 18 blocos `SAIBA MAIS` do corpus).
- Não altera a interpolação geométrica compartilhada (`line_height`), o extrator, o roteamento, o OCR, nem qualquer outro guard já existente em `recompose_native_paragraphs`.

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Recomposição geométrica de parágrafos" passa a cobrir também a preservação da separação entre itens independentes dentro da seção editorial `SAIBA MAIS`, sem depender do texto específico de cada item.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (`recompose_native_paragraphs`). Nenhuma outra área do pipeline (extrator, roteador, OCR, geometria de blocos em `converter.py`, demais funções de `cleaner.py`) é alterada.
- Testes: novos casos em `tests/` cobrindo os 3 casos reais do corpus (dois "Jurisprudência em Teses" + um "Informativo", "Jurisprudência em Teses" + "Informativo", precedente `CC ... DJe ...` + "Informativo"), variantes negativas (frases jurídicas com "Informativo"/"Jurisprudência"/"/"/"DJe"/números não são divididas; `PROCESSO`/`TEMA`/`DESTAQUE`/`INFORMAÇÕES DO INTEIRO TEOR` inalterados; R01, SUBTÍTULO, índice do CC, rodapés técnicos e thin-space preservados; Papel/Nome inalterado).
- Corpus de regressão: reconversão `--no-ocr` dos 4 PDFs, com diff completo explicado e idempotência confirmada. `AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf` e `L10.406_CC_2002.pdf` não contêm a substring `SAIBA MAIS` e portanto devem permanecer byte-idênticos.
