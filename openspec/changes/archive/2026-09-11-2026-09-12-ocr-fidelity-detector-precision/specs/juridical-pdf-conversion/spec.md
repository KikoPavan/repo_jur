# juridical-pdf-conversion Specification Delta

## MODIFIED Requirements

### Requirement: Controle de Fidelidade e Incerteza OCR
O sistema SHALL implementar mecanismos de detecção e sinalização de anomalias de fidelidade em conversões OCR, priorizando a preservação da incerteza sobre a correção por inferência sem suporte documental. A detecção deve ser conservadora e contextual.

#### Scenario: Duplicação suspeita é sinalizada conservadoramente
- **WHEN** o OCR produz repetição substancial interna (acima de 100 caracteres) na mesma página
- **AND** a repetição não corresponde a padrões de boilerplate legítimos (como descrições repetidas de imóveis ou identificação cartorária recorrente)
- **THEN** o sistema registra a ocorrência no relatório JSON como `duplication`
- **AND** preserva o conteúdo original sinalizado no Markdown

#### Scenario: Legitimate boilerplate is not flagged as duplication
- **WHEN** a page contains repeated legal formulas, property descriptions (as in ESCRITURA4 page 5), or notary headers (as in ESCRITURA4 page 8) that are structurally legitimate
- **THEN** the system does NOT record a `duplication` issue

#### Scenario: Variante inconsistente de entidade é sinalizada contextualmente
- **WHEN** identificadores ou nomes próprios (em Title Case ou ALL CAPS) aparecem com variações de exatamente 1 caractere no mesmo documento
- **AND** a variação não é uma variante lexical comum (ex: PESSOA/PESSOAS, TERCEIRA/TERCEIRO)
- **THEN** o sistema registra o conflito como `entity_inconsistency` no relatório JSON

#### Scenario: Lexical variants are not flagged as entity inconsistencies
- **WHEN** words like "PESSOA" and "PESSOAS" or "TERCEIRA" and "TERCEIRO" appear in the same document
- **THEN** the system does NOT record an `entity_inconsistency` issue

#### Scenario: Visual uncertainty ignores structured codes
- **WHEN** a token follows a legitimate structured code pattern (e.g., "ESCRITURA4", "E032")
- **THEN** it is NOT flagged as `visual_uncertainty` merely for being alphanumeric
