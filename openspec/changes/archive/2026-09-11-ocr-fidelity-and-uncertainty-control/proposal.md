## Why

A auditoria real identificou falhas críticas de fidelidade e controle de incerteza em conversões OCR que não são resolvidas por simples limpeza textual. Casos como E032 mostraram confusão entre caracteres e números (`§ 1º` -> `8 12`), ESCRITURA4 apresentou duplicações inexistentes e inferências inseguras em assinaturas, e CONTRSOCIAL8 gerou variantes plausíveis porém erradas de nomes e entidades (`JKMG` -> `JKMQ`).

Esses erros demonstram que o pipeline carece de mecanismos para detectar, sinalizar e gerenciar incertezas de OCR, especialmente em tokens juridicamente sensíveis e entidades repetidas. A falta desse controle compromete a integridade do documento final e pode levar a interpretações jurídicas equivocadas baseadas em dados "alucinados" ou mal transcritos pelo OCR.

## What Changes

* Implementar detecção conservadora de anomalias de fidelidade na Fase 1.
* Detectar e sinalizar duplicações suspeitas de parágrafos ou trechos significativos dentro de uma mesma página ou documento.
* Identificar variantes inconsistentes de nomes, entidades e identificadores (CPF/CNPJ, números de processo) que aparecem repetidamente no documento.
* Monitorar tokens juridicamente sensíveis: artigos, parágrafos, ordinais, valores monetários, datas e códigos registrais.
* Sinalizar trechos de alta incerteza visual no relatório técnico para auditoria humana ou processamento posterior, evitando mutações automáticas não autorizadas.
* Registrar todas as ocorrências de incerteza e sinalização no relatório técnico JSON.
* Garantir que nenhuma correção semântica ou inferência externa seja aplicada sem suporte documental explícito.

Fora do escopo:

* Correção automática baseada em conhecimento externo ou "bom senso".
* Resumo, interpretação ou classificação jurídica do conteúdo.
* Alterações no Producer, Retrieval, `concept_id`, Legal OKF ou estrutura de `bundle/`.
* Reconstrução de conteúdo deletado propositalmente ou ausente no PDF de origem.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

* `juridical-pdf-conversion`: Adicionar requisitos de controle de fidelidade, detecção de variantes inconsistentes e uso de `[[ilegível]]` para incertezas.
* `phase1-quality-gate`: Validar a presença de sinalizadores de incerteza e garantir que o relatório JSON contenha a auditoria de fidelidade.

## Impact

A mudança afeta o núcleo de processamento da Fase 1, especificamente o fluxo de OCR e a composição final do Markdown e do Relatório JSON. Melhora a confiabilidade do pipeline ao expor incertezas em vez de ocultá-las sob transcrições plausíveis mas incorretas.

Não altera a interface CLI principal ou o formato de entrada. A saída permanece Markdown UTF-8 com `[[Pág. N]]` e metadados JSON estendidos.
