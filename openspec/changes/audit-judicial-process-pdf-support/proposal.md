## Why

O pipeline (`src/pipeline_juridico/`) até agora só foi validado contra um corpus de regressão de 4 documentos de tribunais superiores/legislação (`AINTARESP_1462304-PA`, `REsp_1704551-SP`, `Inf0024E`, `L10.406_CC_2002`). Antes de considerar o conversor pronto para processar **processos judiciais de 1º grau** (peças de parte, decisões interlocutórias, documentos escaneados de cartório), é preciso saber, com evidência concreta e não com suposição, se a arquitetura atual (roteamento nativo/OCR, recomposição geométrica, remoção de margens repetitivas) generaliza para esse tipo de documento — e onde ela não generaliza.

Esta mudança é **exclusivamente diagnóstica**. Não implementa nenhuma correção, não altera `src/`, testes, dependências, roteamento, OCR, cleaner ou arquitetura, e não reconverte nem toca o corpus de regressão canônico. Ela está concluída tanto se o conversor se mostrar adequado quanto se defeitos ou bloqueios forem encontrados — o critério de sucesso é a qualidade e completude do diagnóstico, não um resultado específico.

## Corpus auditado

`input/processos_auditoria/` (excluído do corpus de regressão canônico, não referenciado por nenhum teste em `tests/`):

- `001-007-Petição Inicial.pdf` (7 páginas) — petição inicial de inventário judicial com testamento, TJSP.
- `012-015-Testamento Publico.pdf` (4 páginas) — cópia digitalizada (imagem) do testamento público lavrado em cartório de notas.
- `086-096-CONTESTAÇÃO ao Cumprimento de Testamento.pdf` (11 páginas) — habilitação e contestação apresentada por herdeiros.
- `100-106-DECISÃO.pdf` (7 páginas) — decisão interlocutória de um processo conexo (renovatória de locação), juntada como anexo ao processo de inventário.

## Conclusão (resumo — evidência completa em `design.md`)

**O conversor já é adequado como base para processos judiciais de 1º grau em texto nativo, com duas ressalvas concretas e delimitadas, nenhuma delas bloqueante para uso supervisionado.**

- 2 dos 4 documentos (`Petição Inicial`, 7/7 páginas) convertem com paridade perfeita de tokens em relação ao texto nativo do PDF — nenhuma perda, duplicação ou defeito determinístico novo encontrado.
- 1 documento (`CONTESTAÇÃO`, 11/11 páginas) converte corretamente; a única diferença em relação ao PDF é a remoção do cabeçalho/rodapé (endereço, telefone, e-mail do escritório) repetido verbatim em todas as páginas — comportamento **já existente e já validado** de `remove_repetitive_margins`, generalizando corretamente para um timbre de escritório particular (não apenas cabeçalhos institucionais de tribunal, único caso testado até então).
- 1 documento (`Testamento Público`, 4/4 páginas) é uma cópia digitalizada — as 4 páginas são imagem de página inteira (>=150 DPI), sem nenhum texto nativo substantivo (só a camada de autenticação do sistema). O roteador classifica corretamente essas páginas como dependentes de OCR; sob `--no-ocr`, a conversão em modo estrito é corretamente **bloqueada por inteiro** (nenhuma saída é publicada, nenhum conteúdo é fabricado) — comportamento correto e esperado, não um defeito.
- 1 documento (`DECISÃO`, 7 páginas) revela **1 defeito novo determinístico de gravidade alta** (Categoria C): em 5 das 7 páginas, um padrão específico e raro do PDF de origem — duas cópias idênticas e sobrepostas de um carimbo lateral rotacionado de assinatura digital — faz o motor de extração nativo (MarkItDown) produzir centenas de linhas de ruído (caracteres únicos duplicados e invertidos) anexadas ao final da página, sem perda do conteúdo jurídico substantivo. Um segundo defeito novo determinístico, de gravidade baixa (espaçamento duplo sistemático entre palavras nas mesmas 5 páginas), tem a mesma origem upstream. Um terceiro achado é uma **variação nova de uma limitação já conhecida e já aceita** (cabeçalho institucional não removido quando um carimbo de página que varia legitimamente ocupa a primeira linha de conteúdo) — não é regressão, é o mesmo trade-off arquitetural conservador já documentado em `fix-editorial-cover-structural-boundaries`.

Nenhum dos achados exige mudança de roteamento, de OCR ou de arquitetura. Ver `design.md` para o diagnóstico completo, evidência reproduzível e análise de impacto de cada achado (ETAPA 5).

## Capabilities

### New Capabilities
(nenhuma — mudança diagnóstica, não implementa)

### Modified Capabilities
(nenhuma — mudança diagnóstica, não implementa)

## Impact

- Código: nenhum. `src/`, `tests/`, dependências, roteamento, OCR, cleaner e arquitetura não foram tocados.
- Corpus canônico de regressão (`output/AINTARESP_1462304-PA.md`, `output/REsp_1704551-SP.md`, `output/Inf0024E.md`, `output/L10.406_CC_2002.md`): não reconvertido, não alterado (hashes conferidos antes e depois — ver `design.md`, ETAPA 1).
- Novo diretório `openspec/changes/audit-judicial-process-pdf-support/audit_output/` (esta mudança): saídas da conversão de auditoria dos 4 PDFs de `input/processos_auditoria/`, isoladas via `OUTPUT_DIR`/`LOGS_DIR`, nunca escritas em `output/`/`logs/`.
- Nenhuma chamada de OCR ou LLM foi realizada (todas as conversões usaram `--no-ocr`; `GEMINI_API_KEY` não foi utilizada).
- Esta mudança permanece ativa (não arquivada) por instrução explícita do escopo — os achados da ETAPA 5 são candidatos a **futuras** mudanças OpenSpec próprias, não implementadas aqui.
