## ADDED Requirements

### Requirement: Validação de Auditoria de Fidelidade

O Quality Gate SHALL validar que o relatório técnico JSON contém a auditoria de fidelidade e que as sinalizações de incerteza estão devidamente registradas.

#### Scenario: Relatório sem auditoria de fidelidade em OCR

- **WHEN** uma ou mais páginas são processadas pelos métodos `ocr_integral` ou `hibrido`
- **THEN** o Quality Gate verifica se cada entrada de página no relatório possui o bloco `fidelity_audit`
- **AND** falha (`FAIL`) se o bloco obrigatório de auditoria estiver ausente em páginas que utilizaram OCR

#### Scenario: Sinalização de incerteza gera aviso no Quality Gate

- **WHEN** o bloco `fidelity_audit` contém problemas sinalizados (`issue_type`) como duplicações, inconsistências de entidade ou incertezas em tokens sensíveis
- **THEN** o Quality Gate retorna o estado `PASS_WITH_WARNINGS` (ou `FAIL` em modo estrito se houver erros de conformidade graves)
- **AND** inclui as descrições dos problemas detectados na lista de `warnings` do resultado final
