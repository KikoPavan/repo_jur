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

## 3. Correção adicional — margens recorrentes empilhadas (achado da validação de corpus)

Achado durante a primeira rodada de validação (seção 4): em `AINTARESP_1462304-PA.pdf`, toda
página com o rodapé GABGF09 também tem, ainda mais próxima da margem, uma assinatura eletrônica
legítima que também se repete o suficiente para satisfazer o critério de recorrência já aprovado.
`remove_repetitive_margins` só examina a última linha de conteúdo da página (calculada uma única
vez, a partir do texto original), então remove a assinatura (a mais externa) mas nunca chega a
examinar o GABGF09 (que fica "preso" logo abaixo dela) na mesma execução. Confirmado
empiricamente: uma segunda chamada da mesma função, sobre o resultado da primeira, remove o
GABGF09 corretamente; uma terceira chamada não altera mais nada (ponto fixo em 2 passagens). Ver
`design.md`, seção "Achado adicional durante a validação do corpus".

- [x] 3.1 Adicionar teste: página com duas margens recorrentes empilhadas na mesma borda (uma
  assinatura eletrônica recorrente como última linha, um rodapé técnico recorrente logo acima)
  tem AMBAS removidas em uma única chamada de `remove_repetitive_margins`, preservando o conteúdo
  jurídico substantivo anterior. Confirmar que esse teste falha (red) contra o código atual.
- [x] 3.2 Fazer `remove_repetitive_margins` reaplicar sua própria lógica (recálculo de páginas,
  quorum e candidatos a cada rodada) sobre o resultado da rodada anterior, até que uma rodada não
  produza nenhuma alteração (ponto fixo), com um teto de segurança de iterações. Não alterar o
  critério de recorrência, o cálculo de quorum, nem introduzir vocabulário ou listas fixas.
- [x] 3.3 Rodar a suíte completa e confirmar que o teste novo passa (green) e nenhum teste
  existente regride. Resultado: 311/311 passed (verificado de forma independente pelo orquestrador).

## 4. Validação do corpus

- [x] 4.1 Rodar `uv run pytest tests/` (suíte completa) e registrar o resultado. Resultado: 311/311 passed.
- [x] 4.2 Rodar `openspec validate --all --strict` e registrar o resultado. Resultado: 2 passed, 0 failed.
- [x] 4.3 Reconverter os 4 PDFs do corpus (`AINTARESP_1462304-PA.pdf`, `REsp_1704551-SP.pdf`, `Inf0024E.pdf`, `L10.406_CC_2002.pdf`) com `converter-juridico --no-ocr` e confirmar que nenhuma página exigiu OCR. Resultado: todas as páginas dos 4 arquivos roteadas como `texto_nativo`; nenhuma OCR.
- [x] 4.4 Confirmar as 8 ocorrências técnicas de `AINTARESP_1462304-PA.pdf` e as 3 ocorrências de `REsp_1704551-SP.pdf` corrigidas (antes/depois de cada uma), sem perda de token. Resultado: `GABGF09` e `Documento: 1807307` com 0 ocorrências residuais; diff contra uma reconversão com o código anterior a esta mudança mostra apenas remoção do texto do rodapé (144 tokens em AINT, 36 em REsp), 0 tokens adicionados, 0 tokens de conteúdo jurídico removidos.
- [x] 4.5 Confirmar que `Inf0024E.pdf` e `L10.406_CC_2002.pdf` (R01, 8 SUBTÍTULO, índice) permanecem sem alterações inesperadas. Resultado: 8 SUBTÍTULO, `# ÍNDICE` e os 4 marcadores R01 (Art. 44, Art. 593, Art. 1.458, Art. 1.368-F) presentes; nenhum dos dois arquivos contém o padrão de rodapé desta mudança (não acionam o mecanismo alterado).
- [x] 4.6 Confirmar marcadores `[[Pág. N]]` únicos e sequenciais em todos os 4 arquivos. Resultado: AINT=12, REsp=14, Inf0024E=29, CC=186, todos únicos e sequenciais.
- [x] 4.7 Reconverter novamente e confirmar idempotência (segunda reconversão byte-idêntica à primeira). Resultado: os 4 arquivos byte-idênticos entre a primeira e a segunda reconversão.
- [x] 4.8 Produzir e explicar o diff completo do corpus (todos os arquivos alterados e por quê). Resultado: apenas `AINTARESP_1462304-PA.pdf` e `REsp_1704551-SP.pdf` mudam (remoção do rodapé técnico, isolado e fundido); `Inf0024E.pdf` e `L10.406_CC_2002.pdf` inalterados (não contêm o padrão).

## 5. Encerramento do ciclo

- [x] 5.1 Claude revisa o diff, reexecuta os testes e valida o OpenSpec de forma independente antes de aprovar. Feito em cada subtarefa (commits `96b91cc`, `96c4f1c`, `d255d6f`, `633b8a0`).
- [x] 5.2 Commit local (sem push) após aprovação explícita de cada subtarefa aprovada pelo Codex. Feito.
- [x] 5.3 Atualizar `LOOPS.md` com o resultado desta mudança (sem arquivar sem aprovação humana). Feito (commit `5466a6f`); aprovação humana para arquivamento recebida em seguida.
