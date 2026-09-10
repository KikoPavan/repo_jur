## MODIFIED Requirements

### Requirement: Normalização conservadora pós-conversão

O sistema SHALL aplicar uma normalização conservadora no Markdown final para remover artefatos técnicos inequivocamente introduzidos pelo pipeline ou pelo processo de OCR.

#### Scenario: Remoção de artefatos de OCR
- **GIVEN** um Markdown contendo `[[Pág. 1]]` e o texto `*[Image OCR] Conteúdo Jurídico`
- **WHEN** a normalização é executada
- **THEN** o Markdown final contém `[[Pág. 1]]` e `Conteúdo Jurídico`
- **AND** a string `*[Image OCR]` é removida

#### Scenario: Remoção de cabeçalhos redundantes
- **GIVEN** um Markdown contendo `## Page 1`
- **WHEN** a normalização é executada
- **THEN** o cabeçalho `## Page 1` é removido
