# juridical-pdf-conversion Specification Delta

<!--
STATUS: PROPOSED — documentation only. NOT AUTHORIZED FOR IMPLEMENTATION.
This delta corrects only causal/semantic wording and the persisted `issue_type`
value referenced by two scenarios under the existing Requirement "Controle de
Fidelidade e Incerteza OCR", and documents that the renamed value is emitted
under a new schema_version "1.2" (schema_version "1.1" is retained as a
legacy contract emitting the pre-rename value; see ../../design.md § Schema
Version Decision). It does NOT change the detection heuristic (min_len,
sliding-window match/extension, gap ratio) in
`src/pipeline_juridico/fidelity.py::detect_duplications`, and it does NOT
rename the Requirement itself (which also covers entity inconsistency,
sensitive token uncertainty, and visual uncertainty detectors, out of scope
here). Codex must not implement against this delta until the orchestrator
(Claude) explicitly authorizes an implementation phase for this change.
-->

## MODIFIED Requirements

### Requirement: Controle de Fidelidade e Incerteza OCR

O sistema SHALL implementar mecanismos de detecção e sinalização de anomalias de fidelidade em
conversões OCR, priorizando a preservação da incerteza sobre a correção por inferência sem suporte
documental. A detecção deve ser conservadora e contextual. Para o detector de repetição interna
especificamente, o sistema SHALL registrar exclusivamente o que foi observado no Markdown convertido; sob
`schema_version` `1.2`, o valor persistido é `internal_repetition` (sob a legada `schema_version` `1.1`,
o valor persistido é `duplication`) — o sistema SHALL NÃO afirmar, no relatório ou na documentação
normativa, que o OCR ou a conversão causou a repetição — essa é uma afirmação causal que exigiria
comparação explícita fonte-vs-saída, não realizada por este detector em tempo de execução.

#### Scenario: Repetição interna substancial é sinalizada conservadoramente

- **WHEN** o sistema detecta repetição substancial interna (acima de 100 caracteres) no Markdown
  convertido, na mesma página
- **AND** a repetição não corresponde a padrões de boilerplate legítimos (como descrições repetidas de
  imóveis ou identificação cartorária recorrente)
- **THEN** o sistema registra a ocorrência no relatório JSON, sob `schema_version` `1.2`, como
  `internal_repetition` (relatórios legados sob `schema_version` `1.1` registram `duplication`)
- **AND** preserva o conteúdo original sinalizado no Markdown
- **AND** esta sinalização NÃO afirma nem implica que o OCR ou a conversão introduziu a repetição; ela
  descreve exclusivamente o que foi observado no Markdown de saída. Atribuição causal (se a repetição já
  existia na fonte ou foi introduzida pela conversão) exige comparação explícita fonte-vs-saída, que este
  detector não realiza em tempo de execução.

#### Scenario: Legitimate boilerplate is not flagged as duplication

- **WHEN** a page contains repeated legal formulas, property descriptions (as in ESCRITURA4 page 5), or
  notary headers (as in ESCRITURA4 page 8) that are structurally legitimate
- **THEN** the system does NOT record an `internal_repetition` issue
