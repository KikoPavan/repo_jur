## ADDED Requirements

### Requirement: Não vazamento de marcadores internos do mecanismo de OCR para o Markdown final

Em páginas roteadas como `hibrido` ou `ocr_integral`, marcadores de formatação internos inseridos pelo mecanismo de OCR de terceiros para delimitar, dentro do próprio resultado bruto de OCR, onde termina um bloco de texto extraído de uma imagem, SHALL NOT aparecer no Markdown final publicado, depois que sua função estrutural interna já tiver sido consumida pelo restante do pipeline.

A remoção desses marcadores SHALL ocorrer somente depois de qualquer processamento deste pipeline que dependa de sua posição no texto para localizar ou reconstruir conteúdo — em particular, depois da substituição geométrica de resíduo de texto rotacionado fragmentado já formalizada no requisito "Substituição geométrica de resíduo de texto rotacionado fragmentado na rota híbrida/OCR". A remoção SHALL preservar, sem alteração, todo o conteúdo substantivo de OCR e todo o conteúdo nativo reconstruído ao redor do marcador — apenas a substring literal do marcador em si é removida.

Esta remoção SHALL depender exclusivamente do texto literal exato do marcador conhecido, restrita às páginas `hibrido`/`ocr_integral` — SHALL NOT remover texto que apenas se assemelhe ao marcador sem corresponder a ele exatamente, e SHALL NOT introduzir uma limpeza genérica de strings arbitrárias.

O sistema SHALL NOT aplicar esta remoção a páginas roteadas como `texto_nativo`, `vazia` ou `erro`.

#### Scenario: Marcador interno de OCR removido depois de consumida sua função estrutural

- **WHEN** uma página roteada como `hibrido` ou `ocr_integral` contém, no Markdown já composto, um ou mais marcadores internos de fim de bloco de OCR, depois que qualquer substituição de resíduo geométrico dependente desse marcador já foi aplicada
- **THEN** o Markdown final dessa página não contém nenhuma ocorrência desse marcador
- **AND** todo o conteúdo substantivo de OCR e toda a reconstrução geométrica de resíduo nativo ao redor do marcador permanecem presentes, byte a byte, exceto pela remoção do próprio marcador

#### Scenario: Múltiplas ocorrências do marcador na mesma página são todas removidas

- **WHEN** uma página `hibrido`/`ocr_integral` contém mais de uma ocorrência do marcador interno de OCR (por exemplo, por conter mais de uma imagem processada por OCR)
- **THEN** todas as ocorrências são removidas do Markdown final dessa página

#### Scenario: Texto literal semelhante mas não idêntico ao marcador não é removido

- **WHEN** o conteúdo de uma página `hibrido`/`ocr_integral` contém texto que menciona partes do marcador (por exemplo, a palavra "OCR" ou colchetes) sem corresponder exatamente à sua representação literal completa
- **THEN** esse texto permanece inalterado no Markdown final

#### Scenario: Páginas texto_nativo, vazia e erro não são afetadas

- **WHEN** uma página é roteada como `texto_nativo`, `vazia` ou `erro`
- **THEN** esta remoção não é aplicada a essa página, independentemente do conteúdo da página

#### Scenario: Ausência do marcador preserva o comportamento anterior

- **WHEN** uma página `hibrido`/`ocr_integral` não contém nenhuma ocorrência do marcador interno de OCR
- **THEN** o conteúdo dessa página permanece inalterado por esta remoção

#### Scenario: Nenhuma chamada de OCR adicional é introduzida pela remoção

- **WHEN** a remoção descrita neste requisito é aplicada a uma página roteada como `hibrido` ou `ocr_integral`
- **THEN** nenhuma chamada adicional de OCR é realizada para essa página
- **AND** o método atribuído à página permanece `hibrido` ou `ocr_integral`, conforme já determinado pelo roteamento
