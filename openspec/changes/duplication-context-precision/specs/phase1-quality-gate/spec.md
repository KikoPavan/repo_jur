# phase1-quality-gate Specification

<!--
STATUS: CLOSED WITHOUT IMPLEMENTATION — NOT AUTHORIZED FOR IMPLEMENTATION.

The delta below describes the previously proposed `internal_repetition_detector`
suppression rule (MARKER_PATTERN). That rule has been tested exploratorily and
REJECTED (TP=0, FP=2, TN=1, FN=3 — see ../../proposal.md "Rejected candidate rule"
and ../../design.md). Per the human decision recorded in ../../proposal.md
"Status" (Task 1 exit condition (b) met, re-verified 2026-09-13), NO behavior
change to detect_duplications may be implemented under this change. This delta
is retained ONLY because OpenSpec requires at least one structural delta for
`openspec validate --strict` to pass; it MUST NOT be treated as approved and
MUST NOT be implemented as-is. Codex must not act on this file. Reopening this
line of work requires a NEW change with a newly obtained positive control — not
a resumption of this change.
-->

## MODIFIED Requirements
### Requirement: Validação de Auditoria de Fidelidade

O Quality Gate SHALL validar que o relatório técnico JSON contém a auditoria de fidelidade e que as sinalizações de incerteza estão devidamente registradas. NENHUMA alteração de comportamento do `internal_repetition_detector` está autorizada nesta mudança, que foi encerrada sem implementação (ver `../../proposal.md` § Status); os cenários abaixo descrevem o comportamento ATUAL e permanecem inalterados.

#### Scenario: Relatório sem auditoria de fidelidade em OCR

- **WHEN** uma ou mais páginas são processadas pelos métodos `ocr_integral` ou `hibrido`
- **THEN** o Quality Gate verifica se cada entrada de página no relatório possui o bloco `fidelity_audit`
- **AND** falha (`FAIL`) se o bloco obrigatório de auditoria estiver ausente em páginas que utilizaram OCR

#### Scenario: Sinalização de incerteza gera aviso no Quality Gate

- **WHEN** o bloco `fidelity_audit` contém problemas sinalizados (`issue_type`) como duplicações, inconsistências de entidade ou incertezas em tokens sensíveis
- **THEN** o Quality Gate retorna o estado `PASS_WITH_WARNINGS` (ou `FAIL` em modo estrito se houver erros de conformidade graves)
- **AND** inclui as descrições dos problemas detectados na lista de `warnings` do resultado final

#### Scenario: Comportamento atual do detector de duplicação permanece inalterado enquanto BLOCKED

- **WHEN** o `internal_repetition_detector` encontra um par de ocorrências que satisfaz `match_len >= 120` e `0 <= gap <= 1.5 * match_len`
- **THEN** o detector emite um `FidelityIssue` do tipo `duplication`, exatamente como no comportamento hoje implementado em `src/pipeline_juridico/fidelity.py::detect_duplications`
- **AND** nenhuma supressão baseada em marcador de lista/checklist é aplicada, pois a regra candidata (`MARKER_PATTERN`) foi rejeitada e nenhuma regra substituta foi validada
