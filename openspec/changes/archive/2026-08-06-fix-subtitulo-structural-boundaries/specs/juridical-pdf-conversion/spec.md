## MODIFIED Requirements

### Requirement: Recomposição geométrica de parágrafos

O sistema SHALL recompor, em páginas com camada textual nativa, blocos de linha consecutivos que pertençam ao mesmo parágrafo jurídico, usando posição geométrica (distância vertical, alinhamento) e continuidade textual entre blocos extraídos do PDF de origem.

O sistema SHALL NOT unir o bloco atual ao próximo quando o próximo bloco iniciar com marcador de Artigo, parágrafo, inciso, alínea ou item; com PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO; com o marcador de página `[[Pág. N]]`; ou com um novo bloco estrutural independente.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual terminar em uma referência jurisprudencial de fechamento (citação de julgamento com turma/seção/órgão julgador e data de publicação no `DJe`, opcionalmente seguida de anotação como "(Grifos acrescidos).") e o próximo bloco for uma linha inteiramente em caixa alta.

#### Scenario: Parágrafo fragmentado é recomposto

- **WHEN** um artigo como "Art. 2º A personalidade civil da pessoa começa do nascimento com vida; mas a lei põe a salvo, desde a concepção, os" é seguido, no mesmo bloco de página, por "direitos do nascituro."
- **THEN** o Markdown final contém um único parágrafo com o texto completo do artigo, sem quebra de linha intermediária

#### Scenario: Início de novo dispositivo não é unido ao anterior

- **WHEN** um bloco de texto termina um parágrafo e o próximo bloco inicia com "Art.", "§", "I -", "a)", "PARTE", "LIVRO", "TÍTULO", "SUBTÍTULO", "CAPÍTULO", "SEÇÃO", "SUBSEÇÃO" ou o marcador `[[Pág. N]]`
- **THEN** os blocos permanecem separados no Markdown final

#### Scenario: Marcador SUBTÍTULO não é anexado ao dispositivo anterior

- **WHEN** um artigo, um parágrafo, um inciso ou um cabeçalho `TÍTULO` já formado é seguido, no mesmo bloco de página, pelo marcador bare "SUBTÍTULO N" (ex. "SUBTÍTULO I")
- **THEN** o marcador `SUBTÍTULO N` permanece separado, como parágrafo próprio, do conteúdo anterior no Markdown final

#### Scenario: Dois precedentes jurisprudenciais consecutivos não são unidos

- **WHEN** um bloco termina com uma citação de julgamento como "(AgInt no REsp 1739440/SP, Rel. Ministra REGINA HELENA COSTA, PRIMEIRA TURMA, julgado em 08/11/2018, DJe 26/11/2018) (Grifos acrescidos)." e o bloco seguinte, no mesmo grupo geométrico, é uma linha inteiramente em caixa alta como "RECURSO ESPECIAL. INDENIZAÇÃO POR DANO MORAL. ..."
- **THEN** os dois blocos permanecem separados por quebra de parágrafo no Markdown final, sem fundir os dois precedentes em um único parágrafo

### Requirement: Reconhecimento de estrutura legislativa

O sistema SHALL reconhecer marcadores estruturais formais (PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO, SUBSEÇÃO) e, quando o título correspondente aparecer imediatamente a seguir dentro do mesmo bloco de página, SHALL uni-los em um único cabeçalho Markdown (`#` para PARTE, `##` para LIVRO, `###` para TÍTULO, `####` para SUBTÍTULO e CAPÍTULO, `#####` para SEÇÃO, `######` para SUBSEÇÃO). O sistema SHALL NOT converter texto comum em cabeçalho apenas por estar em maiúsculas.

#### Scenario: Marcador estrutural e título são unidos

- **WHEN** o Markdown contém "LIVRO I" seguido, na linha seguinte, por "DAS PESSOAS"
- **THEN** o Markdown final contém um único cabeçalho Markdown "## LIVRO I — DAS PESSOAS" ou equivalente que preserve ambos os textos originais

#### Scenario: SUBTÍTULO forma cabeçalho próprio no mesmo nível de CAPÍTULO

- **WHEN** o Markdown contém o marcador bare "SUBTÍTULO I" seguido, no mesmo bloco de página, por sua denominação (ex. "Do Casamento")
- **THEN** o Markdown final contém um único cabeçalho Markdown "#### SUBTÍTULO I — Do Casamento" ou equivalente que preserve ambos os textos originais

#### Scenario: Texto maiúsculo comum não vira título

- **WHEN** uma linha em maiúsculas não é precedida por um marcador estrutural formal (PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO)
- **THEN** essa linha permanece como texto comum no Markdown final
