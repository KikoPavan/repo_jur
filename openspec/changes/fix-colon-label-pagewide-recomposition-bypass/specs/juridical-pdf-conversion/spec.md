## MODIFIED Requirements

### Requirement: Recomposição geométrica de parágrafos

O sistema SHALL recompor, em páginas com camada textual nativa, blocos de linha consecutivos que pertençam ao mesmo parágrafo jurídico, usando posição geométrica (distância vertical, alinhamento) e continuidade textual entre blocos extraídos do PDF de origem.

O sistema SHALL NOT unir o bloco atual ao próximo quando o próximo bloco iniciar com marcador de Artigo, parágrafo, inciso, alínea ou item; com PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO; com o marcador de página `[[Pág. N]]`; ou com um novo bloco estrutural independente.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual terminar em uma referência jurisprudencial de fechamento (citação de julgamento com turma/seção/órgão julgador e data de publicação no `DJe`, opcionalmente seguida de anotação como "(Grifos acrescidos).") e o próximo bloco for uma linha inteiramente em caixa alta.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual for inteiramente em maiúsculas, sem dígito ou pontuação, e for a primeira linha física do seu bloco geométrico de origem no PDF — comportamento que protege rótulos de campo (por exemplo "PROCESSO", "RAMO DO DIREITO", "TEMA", "DESTAQUE") de serem fundidos ao valor que os segue. O sistema SHALL permitir a união quando essa mesma forma textual (linha inteiramente em maiúsculas, sem dígito ou pontuação) ocorrer no meio de um bloco geométrico já em fluxo — ou seja, não for a primeira linha física do bloco — desde que as demais condições de junção geométrica e estrutural sejam satisfeitas, mesmo que a linha seja curta ou formada por uma única palavra.

O sistema SHALL NOT unir duas linhas físicas quando qualquer uma das duas pertencer a um bloco geométrico de origem que contenha, em qualquer de suas linhas físicas, texto iniciado por `:` (formato de campo estruturado "RÓTULO" seguido de "`: VALOR`", usado por exemplo em RELATOR, AGRAVANTE, AGRAVADO, ADVOGADOS, RECORRENTE, RECORRIDO). Essa proteção SHALL se aplicar apenas às linhas do bloco geométrico que contém o padrão `:`, e SHALL NOT desativar a recomposição geométrica de outros blocos da mesma página que não contenham esse padrão.

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

#### Scenario: Rótulo de campo real permanece separado do valor que o segue

- **WHEN** uma linha como "TEMA", "PROCESSO", "RAMO DO DIREITO" ou "DESTAQUE" é a primeira linha física do seu bloco geométrico de origem e é seguida por linhas de conteúdo do respectivo campo
- **THEN** a linha-rótulo permanece separada, como parágrafo próprio, do conteúdo do campo no Markdown final

#### Scenario: Título ou ementa fragmentado em palavras isoladas é recomposto

- **WHEN** uma ementa ou título em caixa alta é extraído do PDF como sequência de linhas de uma ou poucas palavras cada (por exemplo "PROVEITO" / "ECONÔMICO" / "DA" / "DEMANDA." em sequência), e nenhuma dessas linhas é a primeira linha física do seu bloco geométrico
- **THEN** essas linhas são recompostas em um único parágrafo de texto corrido no Markdown final, sem perda, adição ou reordenação de tokens

#### Scenario: Campo temático fragmentado em palavras isoladas é recomposto

- **WHEN** o valor de um campo temático como "RAMO DO DIREITO" é extraído do PDF, dentro do mesmo bloco geométrico do rótulo, como sequência de linhas de uma ou poucas palavras cada (por exemplo "DIREITO" / "PROCESSUAL" / "PENAL," / "DIREITO" / "DA" / "PESSOA" / "COM" / "DEFICIÊNCIA")
- **THEN** a linha-rótulo permanece separada como parágrafo próprio
- **AND** as linhas do valor, por não serem a primeira linha física do bloco, são recompostas em um único parágrafo de texto corrido, sem perda, adição ou reordenação de tokens

#### Scenario: Campo "RÓTULO / : VALOR" permanece separado, sem impedir a recomposição de outros blocos da página

- **WHEN** uma página contém um bloco geométrico com o padrão "RÓTULO" seguido por "`: VALOR`" (por exemplo "RELATOR" / ": MINISTRO FULANO") e, em outro bloco geométrico da mesma página sem nenhuma linha `:`, um parágrafo ou ementa fragmentado em várias linhas físicas
- **THEN** o rótulo e o valor não são fundidos em uma única linha no Markdown final
- **AND** o parágrafo ou ementa do outro bloco, sem relação com o campo `:`, é recomposto normalmente em um único parágrafo de texto corrido

#### Scenario: Múltiplos campos "RÓTULO / : VALOR" consecutivos no mesmo bloco permanecem distintos

- **WHEN** um único bloco geométrico contém vários pares consecutivos de rótulo e valor (por exemplo "AGRAVANTE" / ": NORTE ENERGIA S.A." / "ADVOGADOS" / ": PRISCILA SANTOS ARTIGAS - PR022529")
- **THEN** nenhum desses rótulos ou valores é fundido com o rótulo, valor ou campo vizinho em uma única linha no Markdown final
