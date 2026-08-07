## MODIFIED Requirements

### Requirement: Separação do índice final

O sistema SHALL identificar o índice posicionado após o encerramento do corpo normativo e SHALL inserir um cabeçalho `# ÍNDICE` imediatamente antes do início do conteúdo identificado como índice, sem excluir ou reordenar esse conteúdo. O sistema SHALL demover, em exatamente um nível de cabeçalho Markdown adicional (respeitando o teto de `######`), qualquer cabeçalho Markdown que já exista estritamente após `# ÍNDICE`, de modo que nenhum cabeçalho dentro do índice compartilhe o mesmo nível de `# ÍNDICE` ou o ultrapasse. Essa demoção SHALL se basear exclusivamente na posição do cabeçalho em relação a `# ÍNDICE`, nunca em seu texto ou palavra-chave específica, e SHALL NOT alterar nenhum cabeçalho posicionado antes de `# ÍNDICE`.

#### Scenario: Índice é identificado e demarcado

- **WHEN** o documento contém, após o último artigo do corpo normativo, um bloco de páginas cujo conteúdo é predominantemente uma lista de títulos e números de página
- **THEN** o Markdown final contém o cabeçalho `# ÍNDICE` imediatamente antes desse bloco
- **AND** todo o conteúdo original do índice permanece presente e na mesma ordem

#### Scenario: Ausência de índice detectável

- **WHEN** o documento não contém um padrão de índice identificável após o corpo normativo
- **THEN** o sistema NÃO insere o cabeçalho `# ÍNDICE`
- **AND** nenhum conteúdo é removido ou alterado

#### Scenario: Cabeçalho dentro do índice é subordinado a `# ÍNDICE`

- **WHEN** um marcador legislativo (por exemplo "PARTE GERAL") já foi convertido em cabeçalho Markdown de nível 1 pelo reconhecimento de estrutura legislativa, e esse cabeçalho está posicionado dentro do bloco identificado como índice
- **THEN** o Markdown final contém esse cabeçalho em um nível estritamente maior que `# ÍNDICE` (por exemplo `## PARTE GERAL`)
- **AND** o texto do cabeçalho permanece inalterado, apenas o nível Markdown muda

#### Scenario: Cabeçalhos do corpo antes do índice não são afetados

- **WHEN** um cabeçalho Markdown de qualquer nível é gerado a partir de um marcador legislativo no corpo normativo, antes do início do índice
- **THEN** esse cabeçalho permanece exatamente no nível originalmente atribuído pelo reconhecimento de estrutura legislativa
