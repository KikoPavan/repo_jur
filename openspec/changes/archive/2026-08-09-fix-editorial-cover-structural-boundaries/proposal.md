## Why

A primeira página editorial de `Inf0024E.pdf` (e somente ela, no corpus de 4 PDFs) tem elementos estruturalmente distintos — título editorial estilizado ("Informativo" / "de Jurisprudência", 26pt), a linha de edição/data ("Informativo de Jurisprudência n. 24 - Edição Extraordinária ... 28 de janeiro de 2025"), o ramo do direito ("Direito Penal"), o aviso editorial ("Este periódico destaca teses...") e o cabeçalho de câmara julgadora ("CORTE ESPECIAL") — todos colapsados em uma única linha corrida no Markdown final:

```
Informativo de Jurisprudência Informativo de Jurisprudência n. 24 - Edição Extraordinária 28 de janeiro de 2025 Direito Penal Este periódico destaca teses jurisprudenciais e não consiste em repositório oficial de jurisprudência. CORTE ESPECIAL
```

## Diagnóstico e decisão (histórico desta mudança)

Esta mudança começou como diagnóstico puro. A causa raiz foi comprovada (ver `design.md`): `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) estima a posição de cada linha física de um bloco PyMuPDF dividindo a altura total do bloco pelo número de linhas **não-vazias**, sem ajustar para o espaço consumido pelas linhas em branco descartadas. No bloco de edição/data desta página (7 linhas em branco + 2 reais), isso produz um gap de junção **negativo**, tornando a fusão praticamente inevitável.

Um primeiro candidato de correção (interpolar sobre o número TOTAL de linhas físicas, incluindo as em branco) foi validado com blast radius de apenas 3 de ~241 páginas do corpus — mas 2 dessas páginas (`AINTARESP_1462304-PA.pdf` p.11, `REsp_1704551-SP.pdf` p.2) pertencem ao achado pendente `Papel/Nome`, já documentado e duas vezes investigado sem critério seguro geral (`openspec/changes/archive/2026-08-07-fix-role-name-list-cross-block-fusion/`), e explicitamente fora de escopo desta mudança.

Três alternativas foram comparadas empiricamente (ver `design.md`, "Próximos passos possíveis"). A alternativa aprovada por decisão humana — **Candidato 2b** — adiciona um gate: a correção de interpolação só é permitida em páginas que contenham pelo menos um bloco de texto com tamanho tipográfico **≥20pt**. Validado com blast radius de **1 de 241 páginas** (somente `Inf0024E.pdf` p.1), **0 alterações** em `AINTARESP_1462304-PA.pdf` e `REsp_1704551-SP.pdf`, 0 falsos positivos, 0 falsos negativos, 0 perda de token. O limiar de 20pt não é um número arbitrário: medição de ~13.500 spans de texto em todo o corpus mostra uma lacuna real de 10.5pt (15.0pt, o maior rótulo estrutural legítimo observado — `SAIBA MAIS`, `INFORMAÇÕES DO INTEIRO TEOR` etc. — até 25.5pt, o menor elemento de masthead/título observado) sem nenhuma ocorrência no meio; 20pt fica no centro dessa lacuna, com 5pt de margem para os dois lados (detalhes completos em `design.md`).

## What Changes

- Em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`): a interpolação de `line_height` passa a dividir pelo número TOTAL de linhas físicas do bloco (incluindo as em branco), preservando o índice original de cada linha real ao posicioná-la — em vez de dividir apenas pelas linhas sobreviventes após o filtro de linhas em branco.
- Essa correção de interpolação só é aplicada em páginas onde pelo menos um bloco de texto tem tamanho tipográfico ≥20pt (sinal obtido via geometria já disponível ao pipeline, sem nova extração). Fora desse contexto, o comportamento atual (sem correção) é preservado exatamente, byte a byte.
- Nenhuma lista de palavras, nome de arquivo, número de página ou vocabulário documental (`CORTE ESPECIAL`, `Informativo`, etc.) é usado como critério — apenas geometria (contagem de linhas físicas) e tipografia (tamanho de fonte).

## Fora do escopo (confirmado)

`Papel/Nome`, `RECURSO / ESPECIAL`, `SAIBA MAIS`, thin-space, rodapés técnicos, `SUBTÍTULO`, índice, R01 — nenhum desses deve ser alterado por esta mudança. Extrator, roteamento, OCR e dependências não são tocados. Nenhuma alteração em `AINTARESP_1462304-PA.md` ou `REsp_1704551-SP.md` é esperada ou aceitável.

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Recomposição geométrica de parágrafos" passa a cobrir também a preservação da separação entre elementos estruturalmente distintos de uma capa editorial estilizada (título, linha de edição/data, avisos, cabeçalho de câmara julgadora), quando o bloco correspondente contém linhas físicas em branco intercaladas, restrito a páginas com pelo menos um bloco de texto ≥20pt.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (`recompose_native_paragraphs`). Possível ajuste pontual em `converter.py`/`_sorted_native_text_blocks` apenas se necessário para disponibilizar o tamanho de fonte por bloco (a definir na implementação; sem alterar extrator, roteamento ou OCR).
- Testes: novos casos cobrindo a geometria real da página 1 do Inf0024E, a separação dos elementos hoje colapsados, os negativos obrigatórios (AINTARESP p.11 e REsp p.2 inalterados, página sem bloco ≥20pt não aciona a regra, controle próximo ao limiar, preservação de `[[Pág. N]]`).
- Corpus de regressão: reconversão `--no-ocr` dos 4 PDFs, diff completo explicado, idempotência confirmada.
