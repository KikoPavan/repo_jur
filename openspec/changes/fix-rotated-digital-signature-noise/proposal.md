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
(nenhuma — mudança diagnóstica, não implementa)

### Modified Capabilities
(nenhuma — mudança diagnóstica, não implementa)

## Impact

- Código: nenhum. `src/`, `tests/`, dependências, roteamento, OCR, cleaner e arquitetura não foram tocados.
- Corpus canônico de regressão: não reconvertido, não alterado.
- Nenhuma chamada de OCR ou LLM foi realizada.
- Esta mudança permanece ativa (não arquivada) por instrução explícita do escopo — a "proposta mínima futura" é candidata a uma mudança OpenSpec própria, não implementada aqui.
