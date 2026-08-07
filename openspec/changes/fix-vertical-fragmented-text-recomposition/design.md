## Context

`recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) recebe, para páginas de texto nativo, a lista de blocos geométricos do PyMuPDF (`(y0, y1, block_text)`, já ordenados em ordem de leitura) e o texto já extraído pelo motor nativo. Ela decompõe cada bloco em linhas físicas, estima a altura de linha dividindo a altura do bloco pelo número de linhas físicas, e decide se cada linha deve se juntar à anterior com base em um conjunto de condições: padrão de início de dispositivo/estrutura formal, gap vertical vs. altura de linha anterior, fechamento jurisprudencial, e — a condição relevante aqui — `not native_label_pattern.match(previous_text)`, que bloqueia a junção sempre que a linha anterior for inteiramente maiúscula/espaços (sem dígito ou pontuação), para proteger rótulos de campo (`PROCESSO`, `TEMA`, `RAMO DO DIREITO`, `DESTAQUE`, `ACÓRDÃO`, `RELATÓRIO`, `VOTO`, cabeçalhos legislativos bare, etc.) de serem fundidos ao conteúdo seguinte.

Essa condição é avaliada apenas sobre a forma textual da linha, sem nenhuma informação de onde ela está posicionada dentro do bloco geométrico de origem. Análise da geometria real (`page.get_text("blocks")`) nos quatro PDFs do corpus mostra uma distinção estrutural consistente: em toda ocorrência legítima de rótulo (177 em `Inf0024E.pdf`, 252 em `L10.406_CC_2002.pdf`, mais os casos de `AINTARESP`/`REsp`), a linha-rótulo é a primeira linha física do seu bloco. Em toda ocorrência do defeito relatado (`AINTARESP` p.7/p.9, `Inf0024E` p.4, `REsp` p.12), a palavra que bloqueia a junção está no meio de um bloco já em fluxo — é a continuação de um valor cuja primeira linha (o verdadeiro rótulo, quando existe, ou a primeira palavra do próprio valor) já foi processada anteriormente.

## Goals / Non-Goals

**Goals:**
- Fazer `native_label_pattern` só bloquear a junção quando a linha candidata for a primeira linha física do bloco geométrico em que se originou — usando informação estrutural já disponível no pipeline (blocos do PyMuPDF), não uma lista de palavras.
- Preservar integralmente as demais condições de `recompose_native_paragraphs` (gap, `current_line_pattern`, `formal_structure_pattern`/`bare_structure_pattern`/`qualified_structure_pattern`, fechamento jurisprudencial, early-returns de tabela `|` e de linha `:`).

**Non-Goals:**
- Corrigir o early-return de linhas iniciadas por `:` (mecanismo distinto, fora de escopo — ver `LOOPS.md`).
- Alterar o cálculo de `line_height`/`gap`, o extrator, o roteamento, o OCR ou qualquer outro módulo.
- Introduzir qualquer heurística baseada em conteúdo (lista de palavras, nomes de tribunal, tamanho de linha, caixa alta) para decidir rótulo vs. continuação.

## Decisions

**Decisão 1 — usar a posição física dentro do bloco como sinal, não o conteúdo textual.**
A lista `lines` hoje é montada em `recompose_native_paragraphs` como uma sequência achatada de tuplas `(line_y0, line_y1, line_text)`, uma por linha física, perdendo a informação de a qual bloco geométrico cada linha pertence. A correção passa a acompanhar, para cada linha, se ela é a primeira linha física (`index == 0`) do bloco do qual foi extraída. `native_label_pattern` só bloqueia a junção quando essa marca for verdadeira para `previous_text`.
Alternativas consideradas: (a) manter uma lista de palavras/rótulos conhecidos — rejeitada por violar a regra de não criar regra específica por palavra e por não generalizar para rótulos não previstos; (b) usar o comprimento da linha (curta = rótulo) — rejeitada explicitamente pela regra 2 do objetivo ("não recompor apenas por linhas curtas"); (c) usar apenas o gap vertical para blocos que já têm `line_height` artificialmente pequeno (caso `Inf0024E` p.4, onde um único bloco de 25pt contém 9 linhas) — insuficiente sozinho, pois nesse caso o gap entre todas as linhas do bloco é uniformemente pequeno e não distingue rótulo de continuação; a posição física (`idx==0`) resolve exatamente esse caso porque o rótulo é sempre a primeira linha do bloco, mesmo quando rótulo e valor compartilham o mesmo bloco.

**Decisão 2 — não alterar a estrutura de retorno da função nem sua assinatura pública.**
A marca de "primeira linha do bloco" é um detalhe interno da construção da lista `lines`; não precisa ser exposta fora de `recompose_native_paragraphs`.

## Risks / Trade-offs

- [Risco] Um bloco geométrico pode, por artefato de extração do PyMuPDF, agrupar duas expressões não relacionadas em sequência sem quebra de bloco, fazendo a segunda "aparentar" ser continuação da primeira. → Mitigação: as demais condições de junção (gap, marcadores de dispositivo/estrutura formal, fechamento jurisprudencial) continuam se aplicando; a mudança apenas remove um bloqueio incondicional, não adiciona uma nova permissão incondicional.
- [Risco] Regressão em algum rótulo de campo real que, por algum motivo, não seja a primeira linha do seu bloco no corpus (ainda não observado). → Mitigação: suíte de regressão cobre explicitamente `PROCESSO`, `RAMO DO DIREITO`, `TEMA`, `DESTAQUE` e os marcadores legislativos formais/`SUBTÍTULO`, além de reconversão completa do corpus com inspeção de diff.

## Migration Plan

Mudança local, sem estado persistente ou API externa. Aplicar no branch de trabalho, validar com suíte + reconversão do corpus, aprovação humana antes de commit/arquivamento. Rollback trivial via `git revert` do commit da subtarefa, se necessário.
