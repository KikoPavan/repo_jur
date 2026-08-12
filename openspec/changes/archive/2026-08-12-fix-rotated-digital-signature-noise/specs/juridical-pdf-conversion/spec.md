## ADDED Requirements

### Requirement: Deduplicação geométrica de texto rotacionado sobreposto

Em páginas roteadas como `texto_nativo`, quando o PDF de origem contiver duas ou mais linhas de texto com direção de escrita não horizontal, texto extraído idêntico entre si e geometria (bbox) coincidente dentro de uma tolerância determinística, o sistema SHALL tratar essas linhas como uma única ocorrência de conteúdo. O sistema SHALL, nesse caso, usar como fonte do conteúdo da página uma representação geométrica já deduplicada — obtida diretamente da camada de texto do PDF de origem, sem depender do motor de conversão nativo — em vez de repassar a duplicação ao motor de conversão nativo, evitando que esse motor produza fragmentação em caracteres isolados ou duplicação de texto na saída a partir desse padrão geométrico.

O sistema SHALL preservar, sem descartar, uma ocorrência única e não duplicada de texto com direção não horizontal, mesmo quando essa ocorrência coexistir, na mesma página, com um par de linhas duplicadas legitimamente tratado por este requisito.

O sistema SHALL NOT aplicar esta deduplicação a linhas de texto com direção horizontal, ainda que estas se repitam com texto e geometria idênticos entre si.

Esta detecção e deduplicação SHALL depender exclusivamente de sinais geométricos e do texto já extraído das próprias linhas (direção de escrita, coordenadas de bbox, igualdade de texto entre linhas) — SHALL NOT depender do nome do documento de origem, de número de página ou de processo, do conteúdo textual específico de uma assinatura, ou de nome de pessoa.

Esta correção SHALL NOT introduzir nenhuma chamada adicional de OCR, nem alterar o roteamento da página.

#### Scenario: Linhas verticais duplicadas e sobrepostas são deduplicadas

- **WHEN** uma página roteada como `texto_nativo` contém duas linhas de texto com direção de escrita não horizontal, texto extraído idêntico entre si e bbox coincidente dentro da tolerância determinística
- **THEN** o conteúdo final dessa página contém esse texto exatamente uma vez
- **AND** o conteúdo final não contém a sequência de linhas de caractere isolado que a duplicação geométrica produziria se repassada sem tratamento ao motor de conversão nativo

#### Scenario: Ocorrência única de texto rotacionado é preservada

- **WHEN** uma página contém uma linha de texto com direção não horizontal sem nenhuma outra linha correspondente (mesmo texto e bbox dentro da tolerância) na mesma página
- **THEN** essa linha permanece presente e inalterada no conteúdo final da página

#### Scenario: Texto horizontal duplicado não é afetado por esta regra

- **WHEN** uma página contém duas linhas de texto com direção de escrita horizontal, texto e geometria idênticos entre si
- **THEN** nenhuma das duas linhas é descartada ou tratada como duplicata por este requisito

#### Scenario: Linhas geometricamente distintas não são tratadas como duplicata

- **WHEN** duas linhas de texto com direção não horizontal têm texto idêntico mas bbox fora da tolerância determinística, ou têm bbox coincidente mas texto diferente entre si
- **THEN** nenhuma das duas linhas é descartada
- **AND** ambas permanecem presentes no conteúdo final da página

#### Scenario: Nenhuma chamada de OCR é introduzida pela deduplicação

- **WHEN** a deduplicação geométrica descrita neste requisito é aplicada a uma página roteada como `texto_nativo`
- **THEN** nenhuma chamada de OCR é realizada para essa página
- **AND** o método atribuído à página permanece `texto_nativo`
