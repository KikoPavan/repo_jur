## 1. Testes (TDD, antes de qualquer implementação)

- [x] 1.1 Adicionar teste: rodapé AINT (`GABGF09 AREsp 1462304 Petição : ...`) isolado como linha própria em ≥2 páginas é removido, preservando `[[Pág. N]]`.
- [x] 1.2 Adicionar teste: rodapé AINT fundido ao final de um parágrafo (ex. "6. Afastado o óbice ... GABGF09 ... Documento") é removido sem perder nenhum token do texto substantivo anterior.
- [x] 1.3 Adicionar teste: rodapé REsp (`Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019`) fundido entre `Paulo de` e a página seguinte iniciando em `Tarso Sanseverino` é removido; a página anterior termina em `Paulo de` e a página seguinte permanece inalterada.
- [x] 1.4 Adicionar teste: caso equivalente de rodapé fundido imediatamente antes de um marcador `[[Pág. N]]` (fim de página) é removido corretamente.
- [x] 1.5 Adicionar teste negativo: assinatura eletrônica legítima que não atinge o limiar de recorrência (poucas ocorrências) não é removida.
- [x] 1.6 Adicionar teste negativo: citação jurídica contendo palavras "Documento", "Página", "DJe" ou similar, sem satisfazer o critério de recorrência verbatim, não é removida.
- [x] 1.7 Adicionar teste negativo: cabeçalhos já corrigidos por `fix-repeated-header-cross-page-fusion` (caso de prefixo) continuam corretos após a mudança (cobertura: testes pré-existentes reexecutados sem regressão).
- [x] 1.8 Adicionar teste negativo: os 4 casos R01, os 8 SUBTÍTULO, o índice do Código Civil e campos `RÓTULO / : VALOR` permanecem intactos.
- [x] 1.9 Adicionar teste negativo: o defeito `Papel/Nome` (fusão geométrica de listas "Papel/Nome" sem `:`) permanece inalterado — não deve ser corrigido incidentalmente por esta mudança.
- [x] 1.10 Rodar a suíte e confirmar que os novos testes falham (red) antes da implementação.

## 2. Implementação

- [x] 2.1 Estender `remove_verbatim_margins` (dentro de `remove_repetitive_margins`, `src/pipeline_juridico/cleaner.py`) para reconhecer um candidato recorrente também como sufixo (`linha.endswith(" " + candidato)`) de uma linha de conteúdo, além dos casos já existentes de igualdade e prefixo, removendo apenas o trecho correspondente ao candidato.
- [x] 2.2 Rodar a suíte completa e confirmar que os testes novos e existentes passam (green). Resultado: 310/310 passed (verificado de forma independente pelo orquestrador).

## 3. Validação do corpus

- [ ] 3.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado.
- [ ] 3.2 Rodar `openspec validate --all --strict` e registrar o resultado.
- [ ] 3.3 Reconverter os 4 PDFs do corpus (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, `L10.406_CC_2002.pdf`) com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR.
- [ ] 3.4 Confirmar as 8 ocorrências técnicas de `AINTARESP_1462304-PA.pdf` e as 3 ocorrências de `REsp_1704551-SP.pdf` corrigidas (antes/depois de cada uma), sem perda de token.
- [ ] 3.5 Confirmar que `Inf0024E.pdf` e `L10.406_CC_2002.pdf` (R01, 8 SUBTÍTULO, índice) permanecem sem alterações inesperadas.
- [ ] 3.6 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais em todos os 4 arquivos.
- [ ] 3.7 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira).
- [ ] 3.8 Produzir e explicar o diff completo do corpus (todos os arquivos alterados e por quê).

## 4. Encerramento do ciclo

- [ ] 4.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar.
- [ ] 4.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex.
- [ ] 4.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana).
