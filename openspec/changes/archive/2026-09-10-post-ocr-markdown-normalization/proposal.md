## Why

A saída Markdown de páginas processadas por OCR ainda pode preservar artefatos técnicos produzidos pelo conversor ou pelo mecanismo de OCR, como marcadores auxiliares e cabeçalhos de página não canônicos. Esses resíduos prejudicam a qualidade estrutural do Markdown e precisam ser removidos de forma conservadora, sem resumir, interpretar, classificar ou reescrever o conteúdo jurídico.

## What Changes

* Normalizar o Markdown resultante da conversão antes da publicação final da Fase 1.
* Remover somente artefatos técnicos conhecidos e inequivocamente introduzidos pelo pipeline, incluindo marcadores auxiliares de OCR e cabeçalhos de página não canônicos.
* Preservar obrigatoriamente o marcador canônico `[[Pág. N]]` e a correspondência entre conteúdo e página de origem.
* Preservar integralmente o texto jurídico produzido pela extração ou OCR, sem correção semântica, resumo, interpretação ou reescrita.
* Aplicar a mesma normalização independentemente de a página ter sido processada por extração nativa, OCR ou fluxo misto, quando o artefato técnico estiver presente.
* Validar que o Markdown final não contenha os artefatos técnicos explicitamente proibidos pelo contrato.
* Manter no relatório JSON a rastreabilidade técnica necessária sem transferir metadados operacionais para o conteúdo Markdown.
* Não prometer correção determinística de erros de transcrição produzidos por OCR baseado em LLM.

Fora do escopo:

* correção automática de nomes, números, datas ou termos jurídicos possivelmente transcritos incorretamente pelo OCR;
* reconstrução semântica de parágrafos;
* resumo, classificação ou interpretação jurídica;
* alterações no Producer, Retrieval, identidade `concept_id`, Legal OKF ou estrutura de `bundle/`;
* alteração do PDF de origem.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

* `juridical-pdf-conversion`: definir a normalização conservadora do Markdown pós-conversão, a remoção de artefatos técnicos conhecidos e a preservação do marcador canônico `[[Pág. N]]` e do conteúdo jurídico.
* `phase1-quality-gate`: validar que a saída final preserve a rastreabilidade por página e não contenha artefatos técnicos explicitamente proibidos, sem transformar incertezas de transcrição do OCR em correções semânticas automáticas.

## Impact

A mudança afeta o processamento final da Fase 1, especialmente os componentes responsáveis por limpeza/normalização do Markdown, composição da saída, validação de integridade e testes de conversão nativa, OCR e documentos mistos.

Não altera a interface principal `converter-juridico`, o formato do PDF de entrada, a identidade dos conceitos jurídicos, o Producer, o Retrieval ou os contratos Legal OKF. A saída continua sendo Markdown UTF-8 com `[[Pág. N]]` e relatório técnico JSON.
