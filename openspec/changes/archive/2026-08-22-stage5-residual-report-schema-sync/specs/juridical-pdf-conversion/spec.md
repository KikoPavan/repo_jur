# juridical-pdf-conversion Specification — MODIFIED Requirements

## MODIFIED Requirements

### Requirement: Saída parcial somente por autorização explícita

O sistema SHALL operar em modo estrito por padrão e SHALL publicar saída parcial somente quando o operador fornecer a opção explícita `--allow-partial`. O desfecho da execução registrado no relatório técnico SHALL ser o resultado serializado do Quality Gate (`result.quality_gate`); saída parcial nunca recebe `PASS` ou `PASS_WITH_WARNINGS` e SHALL registrar `FAIL` no relatório, listando explicitamente as páginas afetadas.

#### Scenario: Falha sem autorização parcial

- **WHEN** uma ou mais páginas falham e `--allow-partial` não foi informado
- **THEN** o sistema não publica o Markdown final
- **AND** o relatório técnico registra `result.quality_gate` com valor `FAIL`

#### Scenario: Saída parcial autorizada

- **WHEN** uma ou mais páginas falham e `--allow-partial` foi informado
- **THEN** o sistema publica o Markdown com `[[TEXTO ILEGÍVEL]]` somente nas páginas afetadas
- **AND** o relatório técnico registra `result.quality_gate` com valor `FAIL` (saída parcial nunca recebe `PASS` ou `PASS_WITH_WARNINGS`)
- **AND** lista explicitamente todas as páginas afetadas

### Requirement: Relatório técnico auditável

O sistema SHALL gerar um relatório JSON (JSON técnico) no layout mínimo de blocos da FROZEN §6.3 (`technical-implementation-spec-repo-jur-v1.2-FROZEN.md` §6.3; `decision-memo-phase1-quality-gate-v1.0-FROZEN.md` §11.2), contendo obrigatoriamente: `schema_version` (versão do esquema); `execution_id` (identificador opaco não vazio da execução); `input` com `sha256` (SHA-256 da evidência PDF, hex minúsculo de 64 caracteres), `byte_size` (tamanho em bytes, inteiro não negativo) e `page_count` (total de páginas físicas, inteiro maior ou igual a 1); `phase1` com `implementation`, `implementation_version` e `logical_processing_version` (identificadores opacos não vazios que identificam a implementação da Fase 1, sua versão e a versão do processamento lógico, e que mudam quando a implementação/lógica correspondente muda) e `relevant_config_fingerprint` (fingerprint opaco determinístico sobre a configuração não secreta relevante para a conversão, idêntico para configuração idêntica e distinto quando essa configuração muda); `result` com `quality_gate` (exatamente um dos valores serializados `PASS`, `PASS_WITH_WARNINGS`, `FAIL` — o rótulo humano "PASS WITH WARNINGS" nunca é um valor serializado), `warnings` e `errors` (tuplas de warnings/errors do resultado do Quality Gate); `artifacts` com `markdown_sha256` (SHA-256 do Markdown literal da Fase 1 — artefato de fronteira com marcadores canônicos `[[Pág. N]]` e sem comentários técnicos de método no corpo, conforme `phase1-operational-spec-v1.1-FROZEN.md` §3 output 1 e §4.2, com hash obrigatório "quando houver saída final" per op-spec §9 e memo §11.3 — e somente desse artefato; o arquivo `.md` cru escrito pela CLI, que ainda contém os comentários `<!-- método: ... -->` adjacentes aos marcadores, NÃO é o artefato hasheado, o relatório não declara auditá-lo e a verificação do hash contra esse arquivo cru está fora do contrato — os bytes do arquivo cru diferem do literal exatamente pelas linhas de comentário de método); `pages` com exatamente uma entrada por página física, cada entrada contendo `page_number` (inteiro), `method` (vocabulário normalizado e engine-neutral de método/estado de extração, onde `vazia` marca página genuinamente vazia), `char_count` (inteiro não negativo, quantidade de caracteres ou métrica equivalente), `warnings` (lista), `errors` (lista) e `truncated` (booleano obrigatório, sempre presente em toda entrada de página emitida: sinal autoritativo explícito de truncamento conhecido da saída da página — derivado da condição fatal normativa de "truncamento conhecido", memo §3.4/§6 c.6/§8.2, op-spec §7.1/§7.3, tech-spec §8.5 `validate_no_known_truncation(report)`/§17, ESIC §11 cond. 4, com os nomes serializados delegados ao schema operacional, op-spec §6 "Os nomes serializados exatos podem ser definidos pelo schema operacional, mas devem permanecer engine-neutral" e memo §3.3; `true` = conhecimento autoritativo explícito de truncamento, `false` = ausência de tal conhecimento — a ausência do campo é violação de contrato (campo obrigatório ausente ⇒ FAIL), nunca equivale a `false` nem a "sem conhecimento explícito"); e `telemetry` (objeto que PODE ser vazio e PODE conter dados não normativos por execução — versões de dependências, configuração/provedor/modelo de OCR, tempos, caminhos de entrada/saída e durações por página — que nunca participam de decisão normativa e nunca são lidos pelo Quality Gate). O sistema SHALL registrar no relatório o resultado do Quality Gate (`result.quality_gate`) após a avaliação do gate e antes da emissão do artefato final, sem que o gate mute o relatório que avaliou.

#### Scenario: Relatório de sucesso

- **WHEN** a conversão é concluída, validada e o Quality Gate retorna `PASS`
- **THEN** o relatório contém `result.quality_gate` com valor `PASS`
- **AND** inclui `input.sha256` do PDF e `artifacts.markdown_sha256` do Markdown literal
- **AND** inclui o bloco `phase1` completo com fingerprint da configuração relevante
- **AND** o bloco `telemetry` pode incluir versões reais dos pacotes obtidas do ambiente e duração total e por página, sem participar de decisão normativa

#### Scenario: Truncamento conhecido registrado

- **WHEN** a pipeline possui conhecimento explícito e autoritativo de truncamento da saída de uma página
- **THEN** a entrada dessa página no relatório possui `truncated` com valor `true`
- **AND** o Quality Gate produz `FAIL` para esse artefato

#### Scenario: Sem conhecimento de truncamento

- **WHEN** a pipeline não possui conhecimento explícito e autoritativo de truncamento de nenhuma página
- **THEN** toda entrada de página emitida possui o campo obrigatório `truncated` com valor `false` (o campo está sempre presente em toda entrada emitida; ausência é violação de contrato, nunca equivale a `false`)
- **AND** nenhum sinal de truncamento é inferido a partir de outros observáveis

#### Scenario: Campo truncated ausente é violação de contrato

- **WHEN** uma entrada de página emitida não contém o campo obrigatório `truncated`
- **THEN** o relatório viola o contrato (campo obrigatório ausente)
- **AND** o Quality Gate registra `FAIL` (campo obrigatório ausente) — a ausência nunca é interpretada como `false` nem como "sem conhecimento explícito"

#### Scenario: O hash cobre somente o Markdown literal

- **WHEN** `artifacts.markdown_sha256` é verificado contra um artefato Markdown
- **THEN** a verificação é contra o Markdown literal da Fase 1 (marcadores canônicos, sem comentários técnicos de método no corpo)
- **AND** o arquivo `.md` cru escrito pela CLI (que ainda contém os comentários `<!-- método: ... -->` adjacentes aos marcadores) NÃO é o artefato hasheado — seus bytes diferem do literal exatamente pelas linhas de comentário de método
- **AND** o relatório não declara auditar esse arquivo cru, e a verificação do hash contra ele está fora do contrato

#### Scenario: Segredos e conteúdo sensível

- **WHEN** o relatório e os logs são gravados
- **THEN** chaves de API, tokens, conteúdo integral de páginas e variáveis secretas não são persistidos
