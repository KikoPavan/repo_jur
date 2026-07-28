## MODIFIED Requirements

### Requirement: Limpeza conservadora

O sistema SHALL limitar a limpeza a transformações determinísticas e reversíveis quanto ao conteúdo semântico: normalização de fim de linha, remoção de espaços finais, redução de três ou mais linhas vazias consecutivas para duas, recomposição geométrica de parágrafos fragmentados, remoção de cabeçalhos/rodapés técnicos repetitivos, normalização contextual de símbolos jurídicos, reconhecimento de hierarquia legislativa formal e separação do índice final. O sistema SHALL aplicar cada uma dessas transformações somente nas condições descritas nos requisitos específicos desta capacidade e SHALL rejeitar qualquer regra de limpeza que resuma, corrija sentido, deduplique por interpretação ou reescreva conteúdo jurídico.

#### Scenario: Conteúdo jurídico é preservado

- **WHEN** a limpeza é aplicada
- **THEN** datas, números processuais, artigos, incisos, alíneas, ementas, assinaturas, tabelas, marcadores de página e blocos OCR permanecem semanticamente inalterados
- **AND** nenhum texto é perdido, duplicado ou alterado em seu conteúdo lexical

#### Scenario: Transformação semântica é solicitada

- **WHEN** uma regra de limpeza implicar resumir, corrigir, reorganizar por interpretação, deduplicar cabeçalhos por julgamento de conteúdo ou interpretar conteúdo jurídico
- **THEN** a regra é rejeitada nesta fase

## ADDED Requirements

### Requirement: Recomposição geométrica de parágrafos

O sistema SHALL recompor, em páginas com camada textual nativa, blocos de linha consecutivos que pertençam ao mesmo parágrafo jurídico, usando posição geométrica (distância vertical, alinhamento) e continuidade textual entre blocos extraídos do PDF de origem.

O sistema SHALL NOT unir o bloco atual ao próximo quando o próximo bloco iniciar com marcador de Artigo, parágrafo, inciso, alínea ou item; com PARTE, LIVRO, TÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO; com o marcador de página `[[Pág. N]]`; ou com um novo bloco estrutural independente.

#### Scenario: Parágrafo fragmentado é recomposto

- **WHEN** um artigo como "Art. 2º A personalidade civil da pessoa começa do nascimento com vida; mas a lei põe a salvo, desde a concepção, os" é seguido, no mesmo bloco de página, por "direitos do nascituro."
- **THEN** o Markdown final contém um único parágrafo com o texto completo do artigo, sem quebra de linha intermediária

#### Scenario: Início de novo dispositivo não é unido ao anterior

- **WHEN** um bloco de texto termina um parágrafo e o próximo bloco inicia com "Art.", "§", "I -", "a)", "PARTE", "LIVRO", "TÍTULO", "CAPÍTULO", "SEÇÃO", "SUBSEÇÃO" ou o marcador `[[Pág. N]]`
- **THEN** os blocos permanecem separados no Markdown final

### Requirement: Remoção de cabeçalhos e rodapés repetitivos

O sistema SHALL remover, de cada bloco de página, apenas linhas marginais comprovadamente repetitivas entre páginas e com posição semelhante (topo ou rodapé do bloco), limitadas a: data e hora de impressão; nome técnico do arquivo de origem; URL repetida; e contador de página no formato "N/total". O sistema SHALL preservar o marcador `[[Pág. N]]` em todas as páginas e SHALL NOT remover conteúdo jurídico apenas por ele se repetir entre páginas.

#### Scenario: Rodapé técnico é removido

- **WHEN** uma linha contendo data/hora de impressão, nome de arquivo técnico, URL ou contador "N/186" aparece de forma repetida na mesma posição (topo ou rodapé) em uma fração alta das páginas
- **THEN** essa linha é removida do bloco de cada página em que aparece
- **AND** o marcador `[[Pág. N]]` correspondente permanece intacto

#### Scenario: Conteúdo jurídico repetido é preservado

- **WHEN** um trecho de conteúdo jurídico (ex. cabeçalho de seção, ementa) se repete entre páginas mas não corresponde a nenhum dos padrões marginais autorizados
- **THEN** o trecho permanece inalterado em todas as páginas em que aparece

### Requirement: Normalização contextual de símbolos jurídicos

O sistema SHALL normalizar exclusivamente os padrões jurídicos corrompidos pela extração explicitamente autorizados: "Art. N o" para "Art. Nº", "§ N o" para "§ Nº", "Lei n o" para "Lei nº", e ordinais jurídicos equivalentes quando o contexto for inequívoco. O sistema SHALL NOT substituir ocorrências da letra "o" isoladas após números fora desses contextos, e SHALL preservar números, datas, valores monetários e referências legais não abrangidos por esses padrões.

#### Scenario: Símbolo jurídico corrompido é normalizado

- **WHEN** o Markdown extraído contém "Art. 1 o" ou "§ 1 o" ou "Lei n o"
- **THEN** o Markdown final contém, respectivamente, "Art. 1º", "§ 1º" e "Lei nº"

#### Scenario: Números e datas fora de contexto não são alterados

- **WHEN** o Markdown contém números, datas, valores monetários ou referências legais que não correspondem a nenhum padrão autorizado de normalização
- **THEN** esse conteúdo permanece byte-idêntico ao extraído

### Requirement: Reconhecimento de estrutura legislativa

O sistema SHALL reconhecer marcadores estruturais formais (PARTE, LIVRO, TÍTULO, CAPÍTULO, SEÇÃO, SUBSEÇÃO) e, quando o título correspondente aparecer imediatamente a seguir dentro do mesmo bloco de página, SHALL uni-los em um único cabeçalho Markdown (`#` para PARTE até `######` para SUBSEÇÃO). O sistema SHALL NOT converter texto comum em cabeçalho apenas por estar em maiúsculas.

#### Scenario: Marcador estrutural e título são unidos

- **WHEN** o Markdown contém "LIVRO I" seguido, na linha seguinte, por "DAS PESSOAS"
- **THEN** o Markdown final contém um único cabeçalho Markdown "## LIVRO I — DAS PESSOAS" ou equivalente que preserve ambos os textos originais

#### Scenario: Texto maiúsculo comum não vira título

- **WHEN** uma linha em maiúsculas não é precedida por um marcador estrutural formal (PARTE, LIVRO, TÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO)
- **THEN** essa linha permanece como texto comum no Markdown final

### Requirement: Separação do índice final

O sistema SHALL identificar o índice posicionado após o encerramento do corpo normativo e SHALL inserir um cabeçalho `# ÍNDICE` imediatamente antes do início do conteúdo identificado como índice, sem excluir ou reordenar esse conteúdo.

#### Scenario: Índice é identificado e demarcado

- **WHEN** o documento contém, após o último artigo do corpo normativo, um bloco de páginas cujo conteúdo é predominantemente uma lista de títulos e números de página
- **THEN** o Markdown final contém o cabeçalho `# ÍNDICE` imediatamente antes desse bloco
- **AND** todo o conteúdo original do índice permanece presente e na mesma ordem

#### Scenario: Ausência de índice detectável

- **WHEN** o documento não contém um padrão de índice identificável após o corpo normativo
- **THEN** o sistema NÃO insere o cabeçalho `# ÍNDICE`
- **AND** nenhum conteúdo é removido ou alterado
