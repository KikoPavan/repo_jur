## ADDED Requirements

### Requirement: Controle de Fidelidade e Incerteza OCR

O sistema SHALL implementar mecanismos de detecção e sinalização de anomalias de fidelidade em conversões OCR, priorizando a preservação da incerteza sobre a correção por inferência sem suporte documental.

#### Scenario: Duplicação suspeita é sinalizada

- **WHEN** o OCR produz repetição substancial interna (acima de 100 caracteres) na mesma página, inclusive inserida em blocos maiores
- **THEN** o sistema registra a ocorrência no relatório JSON como `duplication`
- **AND** preserva o conteúdo original sinalizado no Markdown

#### Scenario: Variante inconsistente de entidade é sinalizada

- **WHEN** identificadores repetidos aparecem com variações de exatamente 1 caractere entre ocorrências no mesmo documento, excluindo palavras jurídicas comuns
- **THEN** o sistema registra o conflito como `entity_inconsistency` no relatório JSON
- **AND** preserva as variantes exatamente como transcritas

#### Scenario: Token sensível com baixa fidelidade é sinalizada

- **WHEN** padrões determinísticos conhecidos como sensíveis ao OCR (ex: confusão entre § e 8) são detectados
- **THEN** o sistema sinaliza como `sensitive_token_uncertainty` no relatório JSON
- **AND** preserva o conteúdo original no Markdown

#### Scenario: Uso de [[ilegível]] para incerteza insuperável

- **WHEN** o processamento de uma região da página produz conteúdo com alta densidade de ruído (excesso de caracteres especiais) ou mistura alfanumérica suspeita
- **THEN** o sistema sinaliza como `visual_uncertainty` no relatório JSON
- **AND** mantém o texto original (não destrutivo) no Markdown, a menos que autorizado explicitamente por outros mecanismos (detect-first)
