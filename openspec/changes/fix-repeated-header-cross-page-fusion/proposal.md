## Why

Em `output/AINTARESP_1462304-PA.md`, após `[[Pág. 5]]`, o conteúdo é:

`Superior Tribunal de Justiça agravada, pois demonstrado o rebate do fundamento da falta de interesse recursal em impugnar o valor da causa.`

O correto é remover o cabeçalho institucional repetido `Superior Tribunal de Justiça` e preservar apenas a continuação do item 6, iniciado na página anterior: `agravada, pois demonstrado o rebate do fundamento da falta de interesse recursal em impugnar o valor da causa.`

Causa raiz: `remove_repetitive_margins` (`src/pipeline_juridico/cleaner.py`) já implementa detecção de margens repetitivas por posição (primeira/última linha de conteúdo de cada bloco de página) e frequência (limiar de ocorrência em pelo menos 60% das páginas), mas seus candidatos de remoção estão **limitados** a quatro padrões fixos por regex: data/hora de impressão, nome técnico de arquivo, URL e contador de página "N/total" (`_REMOVABLE_MARGIN`). Um cabeçalho institucional textual puro como "Superior Tribunal de Justiça" — que se repete no topo de 8 das 12 páginas do documento (5 vezes sozinho, 3 vezes fundido ao início do conteúdo real da página) — não corresponde a nenhum desses quatro padrões e por isso nunca é reconhecido nem removido. Como `remove_repetitive_margins` roda **depois** de `recompose_native_paragraphs` (que já compôs cada página em parágrafos, unindo o cabeçalho não removido ao texto seguinte quando geometricamente próximos), o cabeçalho permanece grudado ao início do conteúdo real da página seguinte no Markdown final.

Ocorrências equivalentes confirmadas no corpus: o mesmo padrão ocorre uma segunda vez no próprio `AINTARESP_1462304-PA.pdf` (página com "Superior Tribunal de Justiça impossibilidade de estimá-lo, ensejaria..."); em `Inf0024E.pdf`, o cabeçalho "Informativo de Jurisprudência n. 24 - Edição Extraordinária 28 de janeiro de 2025" se repete, sempre isolado, em 28 das 29 páginas, sem nunca ser removido pelo mesmo motivo; em `REsp_1704551-SP.pdf`, o rodapé técnico "Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019" se repete, sempre isolado, em 12 das 14 páginas. `L10.406_CC_2002.pdf` não apresenta nenhum candidato equivalente (texto de lei sem cabeçalho/rodapé de tribunal).

## What Changes

- Generalizar `remove_repetitive_margins` (`src/pipeline_juridico/cleaner.py`) para reconhecer, além dos quatro padrões fixos já existentes, um quinto tipo de margem: um texto de cabeçalho/rodapé **verbatim** (byte-idêntico) que (a) aparece sozinho, como a linha de conteúdo completa, em pelo menos duas páginas do documento, e (b) cuja frequência total (ocorrências isoladas + ocorrências fundidas como prefixo de outra linha de conteúdo) atinge o mesmo limiar de 60% já usado para os padrões existentes.
- Quando esse texto aparecer fundido como prefixo de uma linha de conteúdo (`"<cabeçalho> <continuação>"`), remover apenas o prefixo do cabeçalho e preservar a continuação, exatamente como já é feito para os padrões numéricos existentes (ex. data/URL fundidos ao conteúdo).
- Não alterar `recompose_native_paragraphs`, a proteção de fechamento jurisprudencial, `build_legislative_headings`, `mark_final_index`, o extrator, o roteamento, o OCR ou a arquitetura geral.
- Não criar nenhuma regra específica a este processo, a este tribunal ou a esta frase — a detecção depende inteiramente de evidência de repetição verbatim e posição, já reutilizando a mesma infraestrutura (`pages`, `minimum_occurrences`) que os quatro padrões existentes.

## Capabilities

### New Capabilities
(nenhuma — correção pontual da capacidade existente)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Remoção de cabeçalhos e rodapés repetitivos" passa a incluir, na lista fechada de padrões marginais autorizados, um cabeçalho/rodapé textual repetido verbatim e confirmado por posição e frequência, inclusive quando fundido ao início do conteúdo textual real da página seguinte.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (apenas `remove_repetitive_margins`), sem tocar em `inspector.py`, `router.py`, `engines.py`, `converter.py` ou dependências.
- Testes: novos testes de regressão em `tests/test_cleaner.py` cobrindo o caso relatado (cabeçalho fundido ao início de item continuado) e os casos negativos exigidos (cabeçalho isolado sem continuação, menção legítima ao mesmo texto no corpo, continuação normal sem cabeçalho, conteúdo abaixo do limiar de frequência, e confirmação de que as correções anteriores — R01, separações jurisprudenciais, cabeçalhos SUBTÍTULO — permanecem intactas).
- Corpus: reconversão dos 4 PDFs fixos com `converter-juridico --no-ocr`, incluindo verificação explícita das ocorrências equivalentes em `Inf0024E.pdf` e `REsp_1704551-SP.pdf`.
- Fora de escopo: qualquer regra específica ao nome do tribunal, ao número do processo ou à frase exata relatada; reabertura de mudanças arquivadas; OCR real; arquivamento sem aprovação humana explícita.
