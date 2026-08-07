## Contexto

`build_legislative_headings` e `mark_final_index` (ambos em `src/pipeline_juridico/cleaner.py`) rodam em sequência dentro de `converter.py` (linhas 313-314): primeiro `build_legislative_headings`, depois `mark_final_index`. `build_legislative_headings` varre o documento inteiro (corpo + índice) sem qualquer noção de posição estrutural, usando duas heurísticas independentes:

1. Marcador bare seguido de título em parágrafo separado (`_LEGISLATIVE_MARKER_PATTERN` + `heading_levels`, produz `"{'#'*nível} {marcador} — {título}"`).
2. Texto inteiramente em maiúsculas com espaçamento entre letras (`letter_spaced_pattern`/`attached_letter_spaced_pattern` + `_letter_spaced_keyword`, produz `"{'#'*nível} {keyword} {resto}"`, sem travessão).

Inspeção do PDF de origem (`fitz`, `page.get_text()` da página 177 de `input/L10.406_CC_2002.pdf`) confirma:

```
ÍNDICE
P A R T E G E R A L
LIVRO I DAS PESSOAS
TÍTULO I DAS PESSOAS NATURAIS
CAPÍTULO I DA PERSONALIDADE E DA CAPACIDADE
...
```

Apenas "PARTE GERAL"/"PARTE ESPECIAL" chegam letter-spaced (heurística 2); "LIVRO I DAS PESSOAS" etc. chegam como uma única linha normal, não batendo em nenhuma das duas heurísticas — por isso permanecem texto comum tanto antes quanto depois desta mudança. Isso já foi confirmado em `output/L10.406_CC_2002.md`: dentro do índice (linhas 9172-9985), os únicos cabeçalhos Markdown existentes são `# ÍNDICE` (9172), `# PARTE GERAL` (9174) e `# PARTE ESPECIAL` (9271) — nível 1 os três, mesmo nível usado pelas duas ocorrências legítimas de PARTE no corpo (linhas 20 e 1162).

`mark_final_index` roda por último e é o único ponto do pipeline que sabe, com certeza, onde o índice começa (via `structural_pattern`/densidade de marcadores após o último artigo). Hoje ele só promove/insere `# ÍNDICE`; nunca reexamina o que `build_legislative_headings` já produziu depois desse ponto.

## Decisão

Adicionar, dentro de `mark_final_index`, um passo final que demove em exatamente um nível (`#` a mais, respeitando o teto de `######`) qualquer parágrafo que já seja um cabeçalho Markdown ATX (`^#{1,6}\s`) posicionado **depois** de `# ÍNDICE`. A decisão usa somente a posição do parágrafo em relação ao marcador do índice — nunca o texto "PARTE GERAL" — logo generaliza para qualquer marcador que, em outro documento, venha a virar cabeçalho dentro de um índice (preserva PARTE < LIVRO < TÍTULO < SUBTÍTULO/CAPÍTULO < SEÇÃO, cada um deslocado +1 em relação ao nível que o mesmo marcador teria no corpo).

Isso cobre os dois caminhos de retorno já existentes na função:

- Quando `# ÍNDICE` é promovido de um parágrafo bare `"ÍNDICE"` já existente (caso real do Código Civil): demover tudo estritamente após esse parágrafo.
- Quando `# ÍNDICE` é inserido como novo parágrafo antes de um bloco contendo "ÍNDICE" embutido: demover tudo estritamente após o parágrafo recém-inserido.

Nenhum cabeçalho novo é criado para entradas que hoje são texto comum (LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, Seção do índice) — isso está fora do escopo mínimo: a ambiguidade relatada é a competição de nível entre `# ÍNDICE` e os cabeçalhos que já existem, não a ausência de cabeçalhos para as demais entradas.

## Alternativas consideradas

- **Regra específica para o texto "PARTE GERAL"/"PARTE ESPECIAL"**: rejeitada explicitamente pelo requisito da tarefa ("não criar regra específica para PARTE GERAL") e não generalizaria para outro documento.
- **Ensinar `build_legislative_headings` a reconhecer o índice e aplicar níveis diferentes desde a origem**: rejeitada — exigiria duplicar em `build_legislative_headings` a mesma detecção de "índice denso após o último artigo" que `mark_final_index` já implementa via `structural_pattern`, e inverteria a ordem de dependência atual (hoje `mark_final_index` já depende do resultado de `build_legislative_headings`, não o contrário). Fazer o ajuste em `mark_final_index` é a menor mudança e reaproveita a detecção de posição do índice já existente e testada.
- **Suprimir totalmente os cabeçalhos "PARTE GERAL"/"PARTE ESPECIAL" dentro do índice (voltar a texto comum)**: rejeitada — contraria os requisitos positivos da tarefa ("elementos subordinados devem manter relação hierárquica coerente", "níveis legislativos relativos entre si devem ser preservados"), que pressupõem a existência de uma hierarquia dentro do índice, não sua ausência.
- **Offset configurável/genérico em vez de +1 fixo**: rejeitada — nenhuma evidência do corpus real exige mais de um nível de deslocamento hoje; +1 fixo já é suficiente para tornar `# PARTE GERAL`/`# PARTE ESPECIAL` (nível 1) estritamente subordinados a `# ÍNDICE` (nível 1), e é a menor correção generalizável.

## Riscos

- Documento futuro cujo índice já produza cabeçalhos em nível profundo (ex. nível 6, `######`) ficaria sem demoção adicional (teto do Markdown). Mitigado: nenhuma ocorrência real no corpus atual chega perto desse teto (índice do CC produz apenas nível 1); o teto é apenas uma salvaguarda defensiva.
- Falso positivo: nenhum — a demoção só age sobre parágrafos que já são cabeçalhos Markdown (`^#{1,6}\s`) E que estão estritamente depois do marcador do índice; nunca reinterpreta texto comum.
