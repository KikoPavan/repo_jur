## Status

**2026-08-12 — Implementada e validada.** Usuário aprovou avançar do diagnóstico para TDD + implementação mínima nesta mesma mudança. Codex implementou (TDD: 10 testes RED → GREEN); Claude verificou: suíte completa 364/364, `openspec validate --all --strict` limpo (exceto esta própria mudança sem deltas, esperado), reconversão real dos 8 PDFs de referência com `--no-ocr` confirmando blast radius de exatamente 5 páginas (as já diagnosticadas), zero perda de conteúdo, zero OCR, idempotência byte a byte. Ver `design.md`, seções "Autorização de implementação" e "Implementação (2026-08-12)", para o critério exato, o refinamento de nível de linha descoberto durante a revisão dos testes, e a evidência completa de validação. Mudança permanece não arquivada, sem push.

## Why

O diagnóstico `audit-judicial-process-pdf-support` (arquivado em 2026-08-12) identificou, em `100-106-DECISÃO.pdf`, dois defeitos determinísticos novos (achados C.1 e C.2) concentrados nas páginas 1–5: centenas de linhas espúrias de caracteres isolados (C.1) e espaçamento duplo sistemático entre palavras (C.2), ambos ausentes nas páginas 6–7 do mesmo documento e no resto do corpus auditado. Esse diagnóstico prévio já apontava a causa provável (carimbo de assinatura digital rotacionado e duplicado, mal interpretado pelo MarkItDown) mas não isolava a causa raiz com evidência reproduzível nem avaliava um critério de correção contra o corpus completo.

Esta mudança é **exclusivamente diagnóstica**, por instrução explícita do usuário. Não implementa nenhuma correção, não cria testes de produção, não altera `src/`, `tests/`, dependências, roteamento, OCR ou arquitetura, e não é arquivada ao final. Ela está concluída tanto se um critério determinístico seguro de correção for encontrado quanto se nenhum critério seguro for encontrado — o critério de sucesso é a completude e o rigor do diagnóstico, não um resultado específico.

## Escopo

Exclusivamente os achados C.1 (ruído de caracteres isolados) e C.2 (espaçamento duplo) em `100-106-DECISÃO.pdf`, páginas 1–5.

Fora do escopo: OCR/Testamento Público, segmentação de peças, YAML, a limitação conhecida Papel/Nome, o achado B.1 (cabeçalho institucional não removido — já registrado, não arquivado, mas de categoria e causa raiz diferentes), e qualquer correção já arquivada. Roteamento, OCR, dependências e arquitetura não são alterados.

## Conclusão (resumo — evidência completa em `design.md`)

**A) CRITÉRIO SEGURO ENCONTRADO.**

- **Causa raiz:** o PDF de origem contém, nas páginas 1–5, duas cópias idênticas e sobrepostas (mesmo bbox, mesmo texto) de um bloco de texto vertical (rotação 90°, `dir=(0,-1)`) — o carimbo lateral "Este documento é cópia do original assinado digitalmente por...". O extrator nativo do MarkItDown (baseado em `pdfminer`) intercala os caracteres dos dois blocos sobrepostos em ordem de leitura corrompida, produzindo ~500 linhas de um caractere cada. Essa mesma corrupção (tokens viram caracteres isolados, não palavras) derruba a sobreposição lexical entre o texto do MarkItDown e qualquer referência geométrica correta para ~0,49 — bem abaixo do limiar de 0,98 usado pelas duas salvaguardas já existentes no pipeline (`_has_native_reading_order_defect` em `converter.py` e o *fallback* geométrico interno de `recompose_native_paragraphs` em `cleaner.py`) — então nenhuma delas dispara, e o texto bruto e não normalizado do MarkItDown atravessa o pipeline sem qualquer limpeza.
- **Critério determinístico:** geométrico, calculado com `page.get_text("dict")` antes mesmo de chamar o MarkItDown — duas ou mais linhas de texto não horizontais (`dir != (1.0, 0.0)`) na mesma página com bbox quase idêntico (tolerância ~2pt). Testado contra os 8 PDFs de referência (4 processuais + 4 canônicos, 270 páginas no total): dispara exclusivamente nas páginas 1–5 de `100-106-DECISÃO.pdf` (5 páginas), zero falsos positivos em todas as demais 265 páginas, incluindo as páginas 6–7 do próprio `100-106-DECISÃO.pdf` (que têm um bloco vertical não duplicado e já são tratadas corretamente pela salvaguarda existente).
- **Ponto de implementação:** `convert_document()` em `converter.py`, no ponto onde `native_blocks_with_x0`/`reference_content` já são calculados para páginas `texto_nativo`, antes de chamar `native_engine.convert()`.
- **Relação C.1/C.2:** mesma causa raiz — confirmado quantitativamente (não apenas por proximidade visual). O espaçamento duplo (C.2) só sobrevive nas mesmas 5 páginas porque a mesma corrupção de C.1 impede as duas salvaguardas de normalização de disparar; nas páginas 6–7, onde a salvaguarda dispara (a única diferença é a ausência da duplicação), o espaçamento duplo desaparece como efeito colateral, sem nenhuma regra dedicada. C.2 não exige critério próprio.
- **Proposta mínima futura:** ver `design.md`, seção "Proposta mínima futura", para a mudança OpenSpec de implementação sugerida (fora do escopo desta mudança diagnóstica).

## Capabilities

### New Capabilities
(nenhuma nova capacidade de usuário final — correção interna e conservadora do conversor)

### Modified Capabilities
- Conversão de texto nativo (`converter.py`): páginas com blocos de texto não horizontais duplicados (mesmo bbox, dentro de tolerância, e mesmo texto) deixam de ser processadas pelo MarkItDown e passam a usar diretamente o texto geométrico do PyMuPDF, já deduplicado. Sem efeito em páginas sem esse padrão geométrico.

## Impact

- Código: `src/pipeline_juridico/converter.py` (nova lógica de detecção/dedup geométrica, ponto de decisão em `convert_document`). `src/pipeline_juridico/cleaner.py` só é tocado se a implementação exigir (a avaliar por Codex/verificação — ver `tasks.md`).
- Testes: novos testes em `tests/` cobrindo positivos e negativos (ver `tasks.md`, seção TDD).
- Corpus canônico de regressão: reconvertido para validação, esperado byte-idêntico (0 páginas afetadas fora de `100-106-DECISÃO.pdf`).
- Roteamento, OCR e dependências: não alterados.
- Esta mudança permanece ativa (não arquivada) por instrução explícita do usuário.
