## Context

`AINTARESP_1462304-PA.pdf` traz um rodapé técnico de sistema de peticionamento (`GABGF09 AREsp 1462304 Petição : 592169/2020 ... Documento Página N de 8`) 8 vezes; `REsp_1704551-SP.pdf` traz `Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019` em todas as 14 páginas. Em ambos, algumas ocorrências permanecem isoladas no Markdown final e outras aparecem fundidas ao final de uma frase jurídica real — no caso mais crítico (REsp, página 1→2), a fusão corta um nome próprio ao meio: `...Os Srs. Ministros Paulo de Documento: 1807307 - ...` seguido, após `[[Pág. 2]]`, por `Tarso Sanseverino...`.

### Rastreamento da causa raiz (evidência empírica)

1. **Arquitetura de página isolada.** `convert_document` (`converter.py:203-227`) processa cada página como um PDF de página única independente (`isolated_page_workspace`); `recompose_native_paragraphs` só recebe os blocos geométricos dessa única página. Ele nunca tem visibilidade sobre outras páginas e, portanto, não pode saber que um bloco é um "rodapé recorrente" — esse sinal só existe depois, quando `remove_repetitive_margins` roda sobre o `raw_markdown` já composto (`converter.py:309-310`). Essa arquitetura de duas fases (recomposição geométrica por página → remoção de margens recorrentes no corpus completo) é preexistente e não é alterada por esta mudança.

2. **Geometria do rodapé, medida diretamente via PyMuPDF (`page.get_text("blocks")`):**
   - Em `AINTARESP_1462304-PA.pdf`, o rodapé ocupa um bloco isolado com bbox quase idêntica em 6 das 8 páginas em que aparece (`y0=765.5, y1=793.53`). Nas outras 2 páginas (índices 6 e 8, 0-based), o **próprio PyMuPDF já funde o bloco do rodapé ao bloco do parágrafo anterior** (bbox única cobrindo `y0≈635.8` até `y1=793.53`), porque o parágrafo ocupa a página quase até a margem, sem folga suficiente para o clustering de blocos do PyMuPDF separá-los.
   - Em `REsp_1704551-SP.pdf`, o rodapé é sempre um bloco PyMuPDF isolado e consistente (bbox ≈ `y0=772.8–775.0, y1=781.8–783.6`) nas 14 páginas. Nas 3 páginas onde a fusão ocorre no Markdown final, ela acontece no passo seguinte: `recompose_native_paragraphs` funde o bloco do rodapé ao parágrafo anterior porque o `gap` entre o fim do parágrafo e o início do bloco do rodapé é pequeno o bastante (`gap <= previous_height * 1.2`) — nenhuma das proteções existentes (`current_line_pattern`, marcadores estruturais, bloco `:`, linhas de promulgação, fechamento de jurisprudência) reconhece esse texto como algo que não deveria ser unido.

3. **Por que a remoção atual falha mesmo nos casos isolados.** `remove_repetitive_margins` roda em duas etapas sobre a primeira/última linha de conteúdo de cada página:
   - Uma etapa por regex (`_FIRST_MARGIN_PATTERN`/`_LAST_MARGIN_PATTERN`, já existente) reconhece o contador `Página N de N` (via `_PAGE_COUNTER`) e o remove **mesmo quando a linha já está fundida** — confirmado executando `remove_repetitive_margins` isoladamente sobre o corpus: o sufixo numérico é removido em todas as 8/8 (AINT) e todas as 14/14 (REsp) ocorrências, fundidas ou não.
   - A etapa seguinte, `remove_verbatim_margins` (adicionada por `fix-repeated-header-cross-page-fusion`), reconhece o texto restante apenas quando a linha inteira é **igual** ao candidato recorrente ou quando o candidato aparece como **prefixo** (`line.startswith(candidato + " ")`) — o caso de um cabeçalho colado ao **início** do conteúdo real da página seguinte, já corrigido anteriormente. Não existe nenhum caso simétrico para quando o candidato aparece como **sufixo** de uma linha mais longa — exatamente a geometria de um rodapé colado ao **final** do parágrafo anterior.
   - Em `AINTARESP_1462304-PA.pdf` isso tem um efeito composto: das 8 ocorrências, apenas 6 permanecem isoladas (as outras 2 já chegam fundidas desde a extração do PyMuPDF, ver item 2). O limiar de quorum (`minimum_occurrences = (3 * total_paginas + 4) // 5`, com 12 páginas = 8) exige 8 ocorrências idênticas; com apenas 6 candidatos isolados reconhecidos, o quorum nunca é atingido e **nenhuma** ocorrência é removida — nem mesmo as isoladas. Em `REsp_1704551-SP.pdf`, o quorum (9 de 14) já é atingido pelas 11 ocorrências isoladas, por isso essas 11 já são removidas hoje; restam exatamente as 3 fundidas, que o mecanismo de sufixo ausente não alcança.

### Critério discriminante generalizável

O texto marginal já precisa satisfazer, antes de qualquer remoção, o critério de recorrência **verbatim** já aprovado (aparecer, byte-idêntico, como candidato ≥ 2 vezes e atingir o mesmo limiar estatístico de frequência total já usado por todos os outros padrões de margem). A única lacuna é posicional: o candidato pode aparecer colado como **prefixo** (já tratado) ou como **sufixo** (não tratado) de uma linha de conteúdo maior, e ambos os casos devem remover apenas o trecho correspondente ao candidato, preservando o restante da linha. Nenhuma parte do critério depende do texto específico do rodapé (não há lista de números de processo/documento, nem checagem de palavras como "Documento", "Página", "DJe" ou "GABGF09" isoladamente) — a assinatura é puramente recorrência + posição de borda (início/fim de linha na borda superior/inferior da página).

## Goals / Non-Goals

**Goals:**
- Reconhecer e remover um rodapé/cabeçalho técnico recorrente quando ele aparece como sufixo colado ao final da última linha de conteúdo de uma página, simetricamente ao prefixo já tratado.
- Preservar 100% do texto substantivo anterior ao rodapé, sem perda de tokens.
- Manter o critério livre de listas fixas de processo/documento/código e de remoção por palavra-chave isolada.

**Non-Goals:**
- Recompor um parágrafo/nome que ficou naturalmente dividido entre duas páginas depois que o rodapé é removido (ex. unir "Paulo de" da página N com "Tarso Sanseverino" da página N+1 em uma única frase). Isso exigiria lógica de continuidade de parágrafo entre páginas — algo que hoje não existe em nenhum outro ponto do pipeline (cada página é uma unidade Markdown separada pelo marcador `[[Pág. N]]`) e que constituiria uma alteração ampla na recomposição, fora do escopo desta correção mínima. Remover o rodapé apenas restaura a adjacência que já existiria no restante do corpus para qualquer texto legitimamente dividido por uma quebra de página.
- Qualquer alteração em `recompose_native_paragraphs`, no extrator, no roteamento ou no OCR.
- Resolver `Papel/Nome`, `ASSUNTO → AGRAVO INTERNO`, `SUSTENTAÇÃO ORAL → CERTIDÃO`, `RECURSO / ESPECIAL`, `SAIBA MAIS` ou `&#8201;`.

## Decisions

- **Onde corrigir:** dentro de `remove_verbatim_margins` (função interna de `remove_repetitive_margins`, `cleaner.py`), adicionando um modo de correspondência por sufixo (`line.endswith(" " + candidato)`) simétrico ao já existente por prefixo, aplicado tanto a `first_lines` quanto a `last_lines` (mesma função é reusada para ambos os conjuntos hoje). Alternativa descartada: tornar `recompose_native_paragraphs` ciente de recorrência entre páginas — exigiria processar múltiplas páginas juntas, contrariando a arquitetura de página isolada already usada por todo o pipeline (rule "não alterar arquitetura").
- **Critério de correspondência:** um candidato já estabelecido pela contagem verbatim existente (`Counter`, ≥ 2 ocorrências) passa a casar com uma linha também quando `linha == candidato`, `linha.startswith(candidato + " ")` (já existente) ou `linha.endswith(" " + candidato)` (novo). A remoção, no caso de sufixo, corta exatamente `len(" " + candidato)` caracteres do final da linha, preservando o restante. Isso não introduz nenhuma dependência de vocabulário específico do documento.
- **Quorum inalterado:** o limiar estatístico (`minimum_occurrences`) permanece o mesmo já aprovado; o novo modo de correspondência apenas amplia quais linhas contam como instância do mesmo candidato recorrente, sem afrouxar o limiar em si.

## Risks / Trade-offs

- [Risco] Um candidato de sufixo poderia, em teoria, coincidir com o final de uma citação jurídica legítima não recorrente. → Mitigação: o candidato só existe se já ocorrer ≥ 2 vezes verbatim e atingir o mesmo quorum de frequência total já usado para todas as margens; uma citação não recorrente nunca vira candidato.
- [Risco] Uma linha poderia coincidir simultaneamente com prefixo e sufixo do mesmo candidato. → Mitigação: ordem determinística de checagem (igualdade → prefixo → sufixo) evita ambiguidade; nenhum dos casos reais do corpus atual aciona essa condição.
- [Trade-off] Nomes/frases legitimamente cortados por uma quebra de página não são recompostos nesta mudança — ver Non-Goals. Isso é aceito como comportamento consistente com o resto do pipeline (qualquer texto que naturalmente atravesse `[[Pág. N]]` já fica em fragmentos separados).

## Migration Plan

Mudança aditiva e local a uma função pura; sem migração de dados. Validação: suíte completa, `openspec validate --all --strict`, reconversão `--no-ocr` dos 4 PDFs do corpus de regressão, com diff completo explicado e segunda reconversão byte-idêntica (idempotência). Sem archive nem push sem aprovação humana.

## Open Questions

Nenhuma pendente — a causa raiz e o critério foram confirmados empiricamente contra os dois arquivos citados antes desta implementação.
