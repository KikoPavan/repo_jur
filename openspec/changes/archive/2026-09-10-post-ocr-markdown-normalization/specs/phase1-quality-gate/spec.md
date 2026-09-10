## MODIFIED Requirements

### Requirement: Bloqueio de artefatos técnicos

O Quality Gate SHALL impedir a publicação de Markdown que contenha artefatos técnicos residuais inequivocamente proibidos.

#### Scenario: Falha ao encontrar resíduo técnico
- **GIVEN** um Markdown normalizado que ainda contenha `*[Image OCR]`
- **WHEN** o Quality Gate avalia os artefatos
- **THEN** o estado do gate é `FAIL`
- **AND** o erro é registrado no diagnóstico
