## ADDED Requirements

### Requirement: Substituição geométrica de resíduo de texto rotacionado fragmentado na rota híbrida/OCR

Em páginas roteadas como `hibrido` ou `ocr_integral`, quando o resultado bruto do motor de OCR contiver, após o(s) marcador(es) internos `[End OCR]*`, uma sequência de fragmentos majoritariamente muito curtos (até 2 caracteres cada, separados por linha em branco), e essa sequência corroborar geometricamente — por proximidade de tamanho total e por sobreposição de multiconjunto de caracteres, dentro de limiares determinísticos — pelo menos uma linha de texto com direção de escrita não horizontal já extraída da mesma página via a camada de texto nativa do PDF de origem, o sistema SHALL substituir essa sequência de fragmentos pela representação coerente (não fragmentada) dessa(s) linha(s) de texto, preservando o conteúdo textual em vez de descartá-lo.

O sistema SHALL preservar, sem alteração, todo o conteúdo do resultado bruto do motor de OCR que precede o(s) marcador(es) `[End OCR]*`.

O sistema SHALL preservar, sem remoção, o(s) próprio(s) marcador(es) `[End OCR]*` — sua presença ou remoção no Markdown final é um comportamento não afetado por este requisito.

O sistema SHALL NOT aplicar esta substituição quando a sequência de fragmentos não corroborar geometricamente com nenhuma linha de texto não horizontal da mesma página, ainda que essa sequência seja majoritariamente composta por fragmentos curtos.

O sistema SHALL NOT aplicar esta substituição a páginas roteadas como `texto_nativo`.

Esta detecção e substituição SHALL depender exclusivamente de sinais estruturais (posição relativa ao marcador `[End OCR]*`, comprimento dos fragmentos) e geométricos (direção de escrita e texto de linhas já extraídas via a camada de texto nativa do PDF de origem) — SHALL NOT depender do nome do documento de origem, de número de página ou de processo, de nome de pessoa, ou de qualquer texto literal específico de um padrão de autenticação.

Esta correção SHALL NOT modificar o pacote de terceiros usado para OCR, SHALL NOT introduzir nenhuma chamada adicional de OCR, e SHALL NOT alterar o roteamento da página.

#### Scenario: Resíduo vertical fragmentado corroborado geometricamente é substituído pela forma coerente

- **WHEN** uma página roteada como `hibrido` ou `ocr_integral` produz, após `[End OCR]*`, uma sequência de fragmentos majoritariamente de até 2 caracteres cada, cujo conteúdo concatenado corresponde (dentro dos limiares determinísticos de proporção de tamanho e sobreposição de caracteres) a uma linha de texto não horizontal já lida da mesma página
- **THEN** o conteúdo final dessa página contém, no lugar dessa sequência de fragmentos, a forma coerente e legível dessa linha de texto
- **AND** o conteúdo do resultado de OCR anterior ao marcador `[End OCR]*` permanece inalterado
- **AND** o próprio marcador `[End OCR]*` permanece presente

#### Scenario: Resíduo vertical legítimo e não fragmentado é preservado sem alteração

- **WHEN** o conteúdo após `[End OCR]*` já é uma representação coerente (não uma sequência de fragmentos majoritariamente curtos) de uma linha de texto não horizontal da mesma página
- **THEN** esse conteúdo permanece inalterado

#### Scenario: Resíduo horizontal legítimo não é afetado

- **WHEN** o conteúdo após `[End OCR]*` é texto horizontal legítimo, não fragmentado em uma sequência majoritariamente curta
- **THEN** esse conteúdo permanece inalterado, independentemente de existir ou não texto não horizontal na mesma página

#### Scenario: Sequência de fragmentos curtos sem corroboração geométrica não é removida

- **WHEN** uma sequência de fragmentos majoritariamente curtos aparece após `[End OCR]*`, mas a página não contém nenhuma linha de texto não horizontal, ou o conteúdo concatenado dos fragmentos não corresponde ao texto de nenhuma linha não horizontal da página dentro dos limiares determinísticos
- **THEN** essa sequência permanece inalterada no conteúdo final

#### Scenario: Páginas de texto nativo não são afetadas

- **WHEN** uma página é roteada como `texto_nativo`
- **THEN** esta substituição não é aplicada a essa página, independentemente do conteúdo da página

#### Scenario: Nenhuma chamada de OCR adicional é introduzida pela substituição

- **WHEN** a substituição geométrica descrita neste requisito é aplicada a uma página roteada como `hibrido` ou `ocr_integral`
- **THEN** nenhuma chamada adicional de OCR é realizada para essa página
- **AND** o método atribuído à página permanece `hibrido` ou `ocr_integral`, conforme já determinado pelo roteamento
