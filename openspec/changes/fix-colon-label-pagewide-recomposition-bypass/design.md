## Context

`recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) recebe `blocks: list[tuple[float, float, str]]`, os blocos geométricos do PyMuPDF já em ordem de leitura. Antes de montar a lista de linhas físicas para a junção geométrica, a função tem um guard de saída antecipada:

```python
if any(
    line.strip().startswith(":")
    for _, _, block_text in blocks
    for line in block_text.split("\n")
):
    return content
```

Esse guard existe para proteger campos estruturados no formato `RÓTULO\n: VALOR` (ex. `RELATOR\n: MINISTRO GURGEL DE FARIA`, `AGRAVANTE\n: NORTE ENERGIA S.A.`) de serem fundidos pela junção geométrica. O problema é que ele varre `blocks` (toda a página) e, ao encontrar QUALQUER linha `:` em QUALQUER bloco, retorna `content` sem processar a página inteira — mesmo quando outros blocos, geometricamente e semanticamente independentes do bloco que contém o `:`, precisariam ser recompostos.

Evidência geométrica real (`page.get_text("blocks")`):
- `AINTARESP_1462304-PA.pdf` p.1: bloco 0 (8 linhas: "RELATOR" / ": MINISTRO..." / "AGRAVANTE" / ": NORTE..." / "ADVOGADOS" / ": PRISCILA...") e bloco 1 (6 linhas, mais linhas `:`) contêm o padrão `:`. O bloco 7 (34 linhas, a ementa "PROCESSUAL CIVIL. DEMANDA INDENIZATÓRIA. / VALOR / DA / CAUSA. / PROVEITO / ...") é um bloco PyMuPDF totalmente distinto, sem nenhuma linha `:`, mas nunca é recomposto porque o guard já abortou a função para a página inteira.
- `AINTARESP_1462304-PA.pdf` p.4: mesmo padrão (blocos 1–3 com `:`, bloco 7 com 39 linhas de ementa/fundamentação sem `:`).
- `AINTARESP_1462304-PA.pdf` p.11: blocos 9, 14, 18, 21, 26 têm linhas `:` (campos AGRAVANTE/AGRAVADO/ASSUNTO); não há bloco de prosa longa fragmentada nesta página, mas o guard ainda assim desativa qualquer recomposição possível (ex. blocos curtos que poderiam se unir por continuidade geométrica).
- `REsp_1704551-SP.pdf` p.1, p.4, p.6, p.7: bloco 2 (18 linhas, campos RELATORA/RECORRENTE/ADVOGADO/RECORRIDO/ADVOGADOS) contém `:`. O bloco da ementa (33 linhas: "RECURSO / ESPECIAL. / PROCESSUAL / CIVIL. / ARBITRAGEM. / NULIDADE / DE / COMPROMISSO ARBITRAL...") e, na p.4, um bloco de 8 linhas ("Cuida-se / de / recurso / especial / interposto / por / DAIBY / S/A,") são blocos distintos sem nenhum `:`, mas ficam intactos pelo mesmo motivo.
- `REsp_1704551-SP.pdf` p.3, p.14: bloco 14 (15 linhas, campos RECORRENTE/ADVOGADO/RECORRIDO/ADVOGADOS) contém `:`; não há bloco de prosa longa fragmentada nestas duas páginas especificamente, mas o guard ainda bloqueia qualquer recomposição potencial.

Confirmação de independência da causa anterior: em `fix-vertical-fragmented-text-recomposition`, `recompose_native_paragraphs` EXECUTAVA normalmente e a decisão de junção linha-a-linha era incorreta (`native_label_pattern` sem checar posição no bloco). Aqui, a função nunca chega a montar a lista de linhas nem a avaliar nenhuma condição de junção — o retorno antecipado ocorre antes de qualquer lógica de junção rodar. São dois pontos de falha diferentes no mesmo função, confirmados por rastreamento manual: para as páginas listadas acima, o guard `:` dispara e a função retorna `content` inalterado independentemente do estado de `native_label_pattern`.

## Goals / Non-Goals

**Goals:**
- Restringir a proteção do padrão `:` à unidade estrutural correta: o bloco PyMuPDF de origem, não a página inteira.
- Preservar integralmente o comportamento de não fundir rótulo e valor (e campos consecutivos) em uma única linha.
- Permitir que blocos sem nenhuma linha `:` na mesma página sejam recompostos normalmente pelas regras geométricas já existentes.

**Non-Goals:**
- Alterar `native_label_pattern` ou sua lógica de posição no bloco (rule 7 do `/goal`; já implementada e correta, ver `fix-vertical-fragmented-text-recomposition`).
- Preservar byte-a-byte a formatação de todo par rótulo/valor tal como o guard antigo produzia — isso é arquiteturalmente impossível de forma geral (ver Decisão 2) e não é exigido pelo objetivo declarado.
- Alterar extrator, OCR, roteamento, dependências ou arquitetura.

## Decisions

**Decisão 1 — flag por bloco, não por linha isolada, propagada como um campo geométrico a mais em cada linha física.**
Hoje `lines` é construída como uma lista achatada de `(line_y0, line_y1, line_text, is_first_of_block)`. A correção adiciona, computado uma vez por bloco (`any(line.strip().startswith(":") for line in physical_lines)`), um quinto campo `belongs_to_colon_block: bool`, propagado a cada linha física originada daquele bloco. A condição de junção ganha uma nova cláusula: `and not (previous_belongs_to_colon_block or current_belongs_to_colon_block)`. Isso garante que nenhuma linha entre ou saia de um bloco `:`-marcado, em qualquer direção, mantendo blocos vizinhos sem `:` completamente sujeitos às regras normais.
Alternativas consideradas: (a) manter o bypass de página, mas restringi-lo a "blocos vizinhos ao bloco `:`" — rejeitada por exigir uma noção de vizinhança geométrica adicional não necessária, quando o próprio bloco já é a unidade correta e disponível; (b) checar `:` apenas na linha atual (não no bloco inteiro) — rejeitada porque, nos casos reais, o rótulo bare ("RELATOR", "AGRAVANTE") não começa com `:`, só o valor; tratar apenas a linha do valor deixaria a linha do rótulo sujeita à junção com o que vem antes dela (ex. fundir "RELATOR" ao fim do bloco anterior), o que reintroduziria fusão indevida.

**Decisão 2 — aceitar que o par rótulo/valor passe a ser representado como dois parágrafos (separados por linha em branco) em vez de duas linhas físicas adjacentes.**
A arquitetura de `recompose_native_paragraphs` só conhece dois estados de relação entre duas linhas consecutivas: unidas com espaço (`should_join=True`) ou separadas por parágrafo (`"\n\n".join(paragraphs)`, quando `should_join=False`). Não há um terceiro estado nativo de "manter como duas linhas físicas dentro do mesmo parágrafo, sem fundir". O guard antigo simulava esse terceiro estado apenas porque abortava a função inteira e devolvia o `content` original intacto (que por acaso preserva a quebra de linha simples original do MarkItDown). Ao escopar a proteção por bloco em vez de abortar a função, essa preservação byte-a-byte deixa de ser possível de forma geral — mas o requisito real (não fundir rótulo e valor em uma única linha/sentença) continua garantido pelo estado "separados por parágrafo", a mesma representação usada em toda a função para qualquer par de linhas que não deva se unir. O teste pré-existente `test_recompose_native_paragraphs_preserves_uppercase_label_and_value` é atualizado para refletir esse resultado (`"RELATOR\n\n: MINISTRO FULANO"` em vez de `"RELATOR\n: MINISTRO FULANO"`), sem que isso represente fusão de tokens ou perda de informação.
Alternativa considerada: reconstruir o parágrafo do bloco `:`-marcado diretamente a partir do texto bruto do bloco (`block_text`), preservando suas quebras de linha internas originais, e inseri-lo como uma única entrada em `paragraphs` — rejeitada por adicionar um segundo modo de formatação (linhas internas com `\n` simples dentro de uma mesma entrada de `paragraphs`) inconsistente com o resto da função, sem nenhum requisito do `/goal` que exija literalmente essa formatação (o `/goal` exige apenas "não fundidas", não "formatação idêntica ao original").

## Risks / Trade-offs

- [Risco] O teste pré-existente `test_recompose_native_paragraphs_preserves_uppercase_label_and_value` muda de asserção. → Mitigação: a mudança é documentada aqui e no proposal; o comportamento semântico protegido (rótulo e valor nunca fundidos em uma linha) continua garantido e coberto por teste; nenhum outro teste do arquivo depende dessa formatação específica (busca prévia confirmou que é o único teste com esse padrão).
- [Risco] Um bloco legítimo de prosa pode, por coincidência, conter uma linha começando com `:` (ex. uma citação "Vide: ...") e passar a ter TODAS as suas linhas protegidas contra junção, mesmo sem relação com um campo estruturado. → Mitigação: esse comportamento é idêntico ao do guard original (que já reagia a qualquer linha `:`, sem distinguir a natureza semântica), apenas com escopo reduzido de página para bloco — não é uma regressão introduzida por esta mudança, e nenhuma ocorrência desse tipo foi encontrada no corpus de 4 PDFs.

## Migration Plan

Mudança local, sem estado persistente ou API externa. Aplicar no branch de trabalho, validar com suíte + reconversão do corpus, aprovação humana antes de commit/arquivamento. Rollback trivial via `git revert` do commit da subtarefa, se necessário.
