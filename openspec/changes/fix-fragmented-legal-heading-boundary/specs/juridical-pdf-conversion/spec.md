## MODIFIED Requirements

### Requirement: Recomposição geométrica de parágrafos

O sistema SHALL recompor, em páginas com camada textual nativa, blocos de linha consecutivos que pertençam ao mesmo parágrafo jurídico, usando posição geométrica (distância vertical, alinhamento) e continuidade textual entre blocos extraídos do PDF de origem.

O sistema SHALL NOT unir o bloco atual ao próximo quando o próximo bloco iniciar com marcador de Artigo, parágrafo, inciso, alínea ou item; com PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO; com o marcador de página `[[Pág. N]]`; ou com um novo bloco estrutural independente.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual terminar em uma referência jurisprudencial de fechamento (citação de julgamento com turma/seção/órgão julgador e data de publicação no `DJe`, opcionalmente seguida de anotação como "(Grifos acrescidos).") e o próximo bloco for uma linha inteiramente em caixa alta.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual for inteiramente em maiúsculas, sem dígito ou pontuação, e for a primeira linha física do seu bloco geométrico de origem no PDF — comportamento que protege rótulos de campo (por exemplo "PROCESSO", "RAMO DO DIREITO", "TEMA", "DESTAQUE") de serem fundidos ao valor que os segue. O sistema SHALL permitir a união quando essa mesma forma textual (linha inteiramente em maiúsculas, sem dígito ou pontuação) ocorrer no meio de um bloco geométrico já em fluxo — ou seja, não for a primeira linha física do bloco — desde que as demais condições de junção geométrica e estrutural sejam satisfeitas, mesmo que a linha seja curta ou formada por uma única palavra.

Essa proteção de rótulo SHALL ser refinada quando o bloco de origem da linha candidata a rótulo tiver outras linhas físicas além dela: a proteção só permanece ativa quando o bloco não tiver nenhuma outra linha física (mantendo o comportamento acima, sem alteração), OU quando mais da metade dessas outras linhas físicas do mesmo bloco tiverem coordenada horizontal (x0) diferente por 2pt ou mais da coordenada x0 da própria linha candidata a rótulo — sinal de uma coluna de valor genuinamente recuada (estrutura "rótulo: valor"). Quando mais da metade dessas outras linhas físicas do bloco compartilham a mesma coordenada x0 (dentro de 2pt) da linha candidata — sinal de que a linha é, na verdade, a primeira palavra de um parágrafo justificado comum, fragmentada pela extração em uma pseudo-linha própria apesar de pertencer à mesma linha visual do texto seguinte — a proteção SHALL ser desativada, permitindo a junção normal segundo as demais condições geométricas e estruturais. Esse refinamento SHALL NOT se basear em nenhuma palavra específica (como "RECURSO", "PROCESSO" ou qualquer outro vocabulário jurídico), nome de arquivo, número de página ou de processo — apenas na geometria (contagem e posição x0 das linhas físicas do bloco).

O sistema SHALL NOT unir duas linhas físicas quando qualquer uma das duas pertencer a um bloco geométrico de origem que contenha, em qualquer de suas linhas físicas, texto iniciado por `:` (formato de campo estruturado "RÓTULO" seguido de "`: VALOR`", usado por exemplo em RELATOR, AGRAVANTE, AGRAVADO, ADVOGADOS, RECORRENTE, RECORRIDO). Essa proteção SHALL se aplicar apenas às linhas do bloco geométrico que contém o padrão `:`, e SHALL NOT desativar a recomposição geométrica de outros blocos da mesma página que não contenham esse padrão.

O sistema SHALL NOT unir dois blocos geométricos de origem diferentes entre si quando ambos estiverem dentro do intervalo delimitado por um bloco cuja única linha física seja exatamente o rótulo "SAIBA MAIS" (início do intervalo) e o próximo bloco cuja primeira linha física corresponda a um rótulo de campo inteiramente em maiúsculas (fim do intervalo) — preservando cada item editorial de referência (por exemplo um "Informativo de Jurisprudência", um item de "Jurisprudência em Teses" ou um precedente citado) como parágrafo próprio, independentemente de quantas linhas físicas o item ocupe dentro do seu próprio bloco de origem. Essa proteção SHALL NOT se basear no texto específico de cada item (títulos, números de edição, palavras como "Informativo" ou "Jurisprudência", barras `/` ou datas), apenas na origem do bloco geométrico e no rótulo fixo "SAIBA MAIS", e SHALL NOT impedir a recomposição normal das linhas físicas internas de um único item (por exemplo um precedente cuja citação de Relator e data ocupam duas linhas físicas do mesmo bloco).

Ao estimar a posição vertical de cada linha física dentro de um bloco geométrico de origem, em páginas onde pelo menos um bloco de texto tiver tamanho tipográfico maior ou igual a 20pt, o sistema SHALL calcular essa posição dividindo a altura total do bloco pelo número TOTAL de linhas físicas do bloco (incluindo linhas em branco), preservando o índice original de cada linha não-vazia ao posicioná-la — em vez de dividir apenas pelo número de linhas não-vazias. Fora dessas páginas, o sistema SHALL manter o cálculo já existente (divisão apenas pelas linhas não-vazias). Essa correção SHALL NOT depender do nome do arquivo, do número da página, ou de qualquer palavra ou rótulo específico presente no conteúdo.

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

- **WHEN** uma linha como "TEMA", "PROCESSO", "RAMO DO DIREITO" ou "DESTAQUE" é a primeira linha física do seu bloco geométrico de origem, é seguida por linhas de conteúdo do respectivo campo, e essas linhas de conteúdo têm coordenada x0 consistentemente diferente da linha-rótulo
- **THEN** a linha-rótulo permanece separada, como parágrafo próprio, do conteúdo do campo no Markdown final

#### Scenario: Palavra maiúscula isolada no início de um parágrafo justificado é recomposta corretamente

- **WHEN** a extração nativa fragmenta a primeira palavra de uma linha totalmente justificada (por exemplo "RECURSO" seguido de "ESPECIAL. PROCESSUAL CIVIL. ...") em uma pseudo-linha própria, apesar de pertencer à mesma linha visual do restante do texto, e as demais linhas físicas do mesmo bloco geométrico retornam à mesma coordenada x0 dessa primeira palavra (sem coluna de valor recuada)
- **THEN** a palavra isolada é recomposta normalmente com o restante da linha e do parágrafo, sem perda, adição ou reordenação de tokens, e sem depender do texto específico da palavra

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

#### Scenario: Itens independentes de "SAIBA MAIS" que quebram em duas linhas físicas não são fundidos entre si

- **WHEN** um item de "Jurisprudência em Teses" cujo título quebra em duas linhas físicas do seu próprio bloco geométrico (por exemplo "Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 117: INTERCEPTAÇÃO" / "TELEFÔNICA - I") é seguido, na seção "SAIBA MAIS", por outro item independente em um bloco geométrico distinto (por exemplo outro "Jurisprudência em Teses" ou um "Informativo de Jurisprudência n. 751")
- **THEN** as duas linhas físicas do primeiro item permanecem unidas em uma só linha dentro do mesmo parágrafo
- **AND** o item seguinte permanece em parágrafo próprio, separado do primeiro item, no Markdown final

#### Scenario: Precedente com Relator e data em duas linhas não funde o "Informativo" seguinte

- **WHEN** um precedente citado dentro de "SAIBA MAIS" tem a citação de Relator e data de julgamento fragmentada em duas linhas físicas do mesmo bloco geométrico (por exemplo "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA SEÇÃO, julgado em" / "10/04/2019, DJe 16/04/2019") e é seguido, em outro bloco geométrico, por um "Informativo de Jurisprudência n. 474"
- **THEN** a citação do precedente permanece unida em um único parágrafo, incluindo a data
- **AND** o "Informativo de Jurisprudência n. 474" permanece em parágrafo próprio, separado do precedente

#### Scenario: Fusão entre itens de "SAIBA MAIS" não afeta blocos fora da seção

- **WHEN** um bloco de duas linhas físicas fora de qualquer seção "SAIBA MAIS" é seguido por outro bloco geométrico dentro da distância vertical normalmente exigida para junção
- **THEN** a decisão de unir ou não esses blocos segue exclusivamente a lógica geométrica e estrutural já existente, sem qualquer efeito do rótulo "SAIBA MAIS"

#### Scenario: Elementos de uma capa editorial estilizada permanecem separados

- **WHEN** uma página contém um bloco de texto com tamanho tipográfico ≥20pt (por exemplo um título estilizado de capa) e, em outro bloco geométrico da mesma página, linhas físicas em branco intercaladas com conteúdo real (por exemplo uma linha de edição/data precedida de várias linhas em branco de espaçamento)
- **THEN** o conteúdo real desse bloco permanece separado do bloco anterior e do bloco seguinte, cada elemento estrutural (título, linha de edição/data, aviso editorial, cabeçalho de câmara julgadora) em parágrafo próprio, sem perda, adição ou reordenação de tokens

#### Scenario: Página sem bloco de texto ≥20pt preserva o comportamento já existente

- **WHEN** uma página não contém nenhum bloco de texto com tamanho tipográfico ≥20pt, mesmo que algum bloco geométrico contenha linhas físicas em branco intercaladas com conteúdo real
- **THEN** a posição de cada linha física continua sendo calculada dividindo a altura do bloco apenas pelas linhas não-vazias (comportamento pré-existente, sem alteração)

#### Scenario: Bloco sem outras linhas físicas mantém a proteção de rótulo

- **WHEN** uma linha candidata a rótulo (inteiramente maiúscula, sem dígito ou pontuação, primeira linha física do seu bloco) pertence a um bloco geométrico que não tem nenhuma outra linha física além dela
- **THEN** a proteção de rótulo permanece ativa exatamente como antes deste refinamento, sem depender de dado de x0
