## ADDED Requirements

### Requirement: Normalização de entidades HTML de espaçamento fino

O sistema SHALL substituir entidades HTML literais equivalentes ao caractere THIN SPACE (U+2009) — `&#8201;` (decimal), `&#x2009;`/`&#X2009;` (hexadecimal) e `&thinsp;` (nomeada, case-insensitive) — por um único espaço ASCII regular (U+0020), absorvendo qualquer espaço ou tabulação horizontal já adjacente à entidade para não duplicar espaços. O sistema SHALL NOT alterar nenhuma outra entidade HTML (ex. `&amp;`, `&lt;`, `&gt;`, `&nbsp;`), SHALL NOT remover ou alterar caracteres alfanuméricos ou pontuação adjacentes à entidade, e SHALL NOT consumir quebras de linha ao redor da entidade. A normalização SHALL ser idempotente.

#### Scenario: Entidade colada entre palavras é substituída por um espaço

- **WHEN** o Markdown extraído contém `na&#8201;realidade`
- **THEN** o Markdown final contém `na realidade`, sem espaço duplicado e sem perda de caracteres

#### Scenario: Entidade adjacente a um espaço já existente não duplica o espaço

- **WHEN** o Markdown extraído contém `apreensão de &#8201;37 gramas` (espaço antes da entidade, colada ao número seguinte)
- **THEN** o Markdown final contém `apreensão de 37 gramas`, com exatamente um espaço entre "de" e "37"

#### Scenario: Variantes equivalentes de THIN SPACE são normalizadas da mesma forma

- **WHEN** o Markdown extraído contém `&#x2009;`, `&#X2009;` ou `&thinsp;` (em qualquer capitalização) na mesma posição em que `&#8201;` ocorreria
- **THEN** o Markdown final contém um único espaço ASCII no lugar da entidade, com o mesmo comportamento de não duplicação de espaço

#### Scenario: Outras entidades HTML permanecem inalteradas

- **WHEN** o Markdown contém entidades HTML sem relação com espaçamento fino (ex. `&amp;`, `&lt;`, `&gt;`, `&nbsp;`)
- **THEN** essas entidades permanecem byte-idênticas ao extraído

#### Scenario: Pontuação e marcadores estruturais permanecem intactos

- **WHEN** a entidade de espaçamento fino aparece adjacente a pontuação (ex. `n.&#8201;11.343`) ou em um documento que também contém `[[Pág. N]]` e comentários `<!-- método: ... -->`
- **THEN** a pontuação permanece inalterada e os marcadores de página e método permanecem intactos
