## Purpose

Estabelecer uma conversão auditável de PDFs jurídicos para Markdown, preservando a rastreabilidade por página e tornando explícitas falhas, uso de OCR e limitações da saída.
## Requirements
### Requirement: Entrada PDF validada

O sistema SHALL aceitar somente um arquivo PDF local por execução e SHALL validar existência, extensão, abertura, criptografia e quantidade de páginas antes de iniciar a conversão.

#### Scenario: PDF válido é aceito

- **WHEN** o operador fornece um PDF existente, legível e não bloqueado por senha
- **THEN** o sistema inicia a inspeção das páginas
- **AND** registra a quantidade total de páginas

#### Scenario: Entrada inválida é rejeitada

- **WHEN** o caminho não existe, o arquivo não é PDF, está corrompido ou requer senha não fornecida
- **THEN** o sistema encerra a execução com status de falha
- **AND** não cria Markdown final
- **AND** registra a causa no relatório técnico

### Requirement: Fonte original preservada

O sistema SHALL tratar o PDF de origem como somente leitura e SHALL impedir qualquer alteração destrutiva no arquivo recebido.

#### Scenario: Conversão não altera a origem

- **WHEN** uma conversão termina com sucesso, falha ou interrupção
- **THEN** o hash SHA-256 do PDF de origem permanece inalterado

### Requirement: Processamento isolado por página

O sistema SHALL processar cada página como uma unidade isolada e SHALL manter correspondência de um para um entre páginas do PDF, blocos do Markdown e registros do relatório.

#### Scenario: PDF com várias páginas

- **WHEN** um PDF com N páginas é processado
- **THEN** o Markdown contém exatamente N blocos de página na ordem original
- **AND** o relatório contém exatamente N registros de página

### Requirement: Roteamento explícito da página

O sistema SHALL classificar cada página como `texto_nativo`, `ocr_integral`, `hibrido`, `vazia` ou `erro` com base em sinais verificáveis da camada textual, conteúdo rasterizado e resultado da conversão.

#### Scenario: Página com texto nativo suficiente

- **WHEN** a página possui camada textual utilizável e não apresenta evidência relevante de conteúdo escaneado não extraído
- **THEN** a página é processada como `texto_nativo`

#### Scenario: Página escaneada

- **WHEN** a página não possui camada textual utilizável e contém conteúdo visual significativo
- **THEN** a página é roteada como `ocr_integral`

#### Scenario: Página mista

- **WHEN** a página possui texto nativo utilizável e também contém conteúdo visual significativo que exige transcrição
- **THEN** a página é roteada como `hibrido`

#### Scenario: Página visualmente vazia

- **WHEN** a página não possui texto nem conteúdo visual significativo
- **THEN** a página é registrada como `vazia`
- **AND** não é tratada como falha

### Requirement: Conversão nativa com MarkItDown

O sistema SHALL usar MarkItDown como motor principal para converter páginas roteadas como `texto_nativo` sem realizar interpretação, resumo ou classificação jurídica.

#### Scenario: Conversão de texto nativo

- **WHEN** uma página é roteada como `texto_nativo`
- **THEN** o texto retornado pelo motor é inserido no bloco correspondente da página
- **AND** nenhuma chamada de OCR externo é realizada para essa página

### Requirement: OCR controlado e verificável

O sistema SHALL executar OCR baseado em visão somente para páginas roteadas como `ocr_integral` ou `hibrido`, usando cliente e modelo configurados externamente.

#### Scenario: OCR configurado retorna conteúdo

- **WHEN** uma página exige OCR e o cliente, o modelo e as credenciais estão configurados
- **THEN** o sistema executa o OCR
- **AND** confirma a presença de conteúdo OCR não vazio
- **AND** registra provedor, modelo e método sem registrar a chave de acesso

#### Scenario: OCR necessário sem configuração

- **WHEN** uma página exige OCR e o cliente, o modelo ou a credencial obrigatória não está configurado
- **THEN** a página é registrada como `erro`
- **AND** a execução falha no modo estrito

#### Scenario: Serviço de OCR emite aviso ou omite conteúdo

- **WHEN** a chamada de OCR falha, retorna aviso técnico, retorna bloco vazio ou não produz evidência verificável de transcrição
- **THEN** a página é registrada como `erro`
- **AND** a execução não pode ser classificada como sucesso

### Requirement: Paginação canônica

O sistema SHALL iniciar cada bloco de página com o marcador exato `[[Pág. N]]`, seguido de um comentário técnico com o método atribuído.

#### Scenario: Bloco de página válido

- **WHEN** a página 7 é composta no Markdown
- **THEN** o bloco inicia com `[[Pág. 7]]`
- **AND** contém exatamente um comentário `<!-- método: ... -->`

#### Scenario: Sequência inválida

- **WHEN** um marcador estiver ausente, duplicado, fora de ordem ou com numeração diferente da página correspondente
- **THEN** a validação final falha

### Requirement: Limpeza conservadora

O sistema SHALL limitar a limpeza a transformações determinísticas e reversíveis quanto ao conteúdo semântico: normalização de fim de linha, remoção de espaços finais, redução de três ou mais linhas vazias consecutivas para duas, recomposição geométrica de parágrafos fragmentados, remoção de cabeçalhos/rodapés técnicos repetitivos, normalização contextual de símbolos jurídicos, reconhecimento de hierarquia legislativa formal e separação do índice final. O sistema SHALL aplicar cada uma dessas transformações somente nas condições descritas nos requisitos específicos desta capacidade e SHALL rejeitar qualquer regra de limpeza que resuma, corrija sentido, deduplique por interpretação ou reescreva conteúdo jurídico.

#### Scenario: Conteúdo jurídico é preservado

- **WHEN** a limpeza é aplicada
- **THEN** datas, números processuais, artigos, incisos, alíneas, ementas, assinaturas, tabelas, marcadores de página e blocos OCR permanecem semanticamente inalterados
- **AND** nenhum texto é perdido, duplicado ou alterado em seu conteúdo lexical

#### Scenario: Transformação semântica é solicitada

- **WHEN** uma regra de limpeza implicar resumir, corrigir, reorganizar por interpretação, deduplicar cabeçalhos por julgamento de conteúdo ou interpretar conteúdo jurídico
- **THEN** a regra é rejeitada nesta fase

### Requirement: Validação estrita de integridade

O sistema SHALL validar a correspondência entre PDF, Markdown e relatório antes de publicar a saída final.

#### Scenario: Documento íntegro

- **WHEN** todas as páginas possuem marcador único, sequência correta, método válido e conteúdo compatível com seu estado
- **THEN** a validação é aprovada

#### Scenario: Página com erro no modo estrito

- **WHEN** qualquer página estiver com método ou estado `erro`
- **THEN** a validação falha
- **AND** o Markdown final não é publicado

#### Scenario: Página não vazia sem conteúdo

- **WHEN** uma página diferente de `vazia` não possuir conteúdo textual verificável
- **THEN** a validação falha

### Requirement: Saída parcial somente por autorização explícita

O sistema SHALL operar em modo estrito por padrão e SHALL publicar saída parcial somente quando o operador fornecer a opção explícita `--allow-partial`.

#### Scenario: Falha sem autorização parcial

- **WHEN** uma ou mais páginas falham e `--allow-partial` não foi informado
- **THEN** o sistema não publica o Markdown final
- **AND** grava relatório com status `falha`

#### Scenario: Saída parcial autorizada

- **WHEN** uma ou mais páginas falham e `--allow-partial` foi informado
- **THEN** o sistema publica o Markdown com `[[TEXTO ILEGÍVEL]]` somente nas páginas afetadas
- **AND** o relatório recebe status `incompleto`
- **AND** lista explicitamente todas as páginas afetadas

### Requirement: Gravação atômica

O sistema SHALL escrever artefatos temporários, executar todas as validações e somente então promover o Markdown e o relatório aos caminhos finais.

#### Scenario: Validação falha após conversão

- **WHEN** a conversão termina mas a validação final falha
- **THEN** nenhum Markdown definitivo substitui uma saída anterior válida
- **AND** os artefatos temporários são removidos ou isolados para diagnóstico

### Requirement: Relatório técnico auditável

O sistema SHALL gerar um relatório JSON com versão de esquema, identificação da origem, hashes, versões de dependências, configuração não secreta, tempos, status global e resultado individual de cada página.

#### Scenario: Relatório de sucesso

- **WHEN** a conversão é concluída e validada
- **THEN** o relatório contém status `sucesso`
- **AND** inclui SHA-256 do PDF e do Markdown
- **AND** inclui versões reais dos pacotes obtidas do ambiente
- **AND** inclui duração total e por página

#### Scenario: Segredos e conteúdo sensível

- **WHEN** o relatório e os logs são gravados
- **THEN** chaves de API, tokens, conteúdo integral de páginas e variáveis secretas não são persistidos

### Requirement: Privacidade do OCR externo

O sistema SHALL tornar explícito que páginas roteadas para OCR podem ser transmitidas a um serviço externo e SHALL exigir configuração consciente do operador.

#### Scenario: OCR externo desabilitado

- **WHEN** o operador desabilita OCR externo
- **THEN** nenhuma imagem de página é enviada a provedor remoto
- **AND** páginas que dependem de OCR falham ou são tratadas conforme `--allow-partial`

### Requirement: Codificação e formato da saída

O sistema SHALL produzir Markdown em UTF-8, com finais de linha LF e uma quebra de linha no final do arquivo.

#### Scenario: Saída validada

- **WHEN** o Markdown final é publicado
- **THEN** ele pode ser decodificado integralmente como UTF-8
- **AND** usa finais de linha LF
- **AND** termina com uma única quebra de linha

### Requirement: Sobrescrita protegida

O sistema SHALL recusar sobrescrever uma saída existente, salvo quando o operador fornecer `--overwrite`.

#### Scenario: Saída já existe

- **WHEN** o caminho final já existe e `--overwrite` não foi informado
- **THEN** o sistema encerra sem alterar o arquivo existente

### Requirement: Escopo limitado da Fase 1

O sistema SHALL excluir desta fase YAML front matter, conformidade OKF completa, classificação semântica, resumo, correção jurídica, identificação autônoma de jurisprudência e extração estruturada de entidades.

#### Scenario: Recurso fora do escopo

- **WHEN** uma solicitação exigir qualquer recurso reservado às fases futuras
- **THEN** o recurso não é implementado nesta mudança
- **AND** deve ser tratado em uma mudança OpenSpec separada

### Requirement: Recomposição geométrica de parágrafos

O sistema SHALL recompor, em páginas com camada textual nativa, blocos de linha consecutivos que pertençam ao mesmo parágrafo jurídico, usando posição geométrica (distância vertical, alinhamento) e continuidade textual entre blocos extraídos do PDF de origem.

O sistema SHALL NOT unir o bloco atual ao próximo quando o próximo bloco iniciar com marcador de Artigo, parágrafo, inciso, alínea ou item; com PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO; com o marcador de página `[[Pág. N]]`; ou com um novo bloco estrutural independente.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual terminar em uma referência jurisprudencial de fechamento (citação de julgamento com turma/seção/órgão julgador e data de publicação no `DJe`, opcionalmente seguida de anotação como "(Grifos acrescidos).") e o próximo bloco for uma linha inteiramente em caixa alta.

#### Scenario: Parágrafo fragmentado é recomposto

- **WHEN** um artigo como "Art. 2º A personalidade civil da pessoa começa do nascimento com vida; mas a lei põe a salvo, desde a concepção, os" é seguido, no mesmo bloco de página, por "direitos do nascituro."
- **THEN** o Markdown final contém um único parágrafo com o texto completo do artigo, sem quebra de linha intermediária

#### Scenario: Início de novo dispositivo não é unido ao anterior

- **WHEN** um bloco de texto termina um parágrafo e o próximo bloco inicia com "Art.", "§", "I -", "a)", "PARTE", "LIVRO", "TÍTULO", "SUBTÍTULO", "CAPÍTULO", "SEÇÃO", "SUBSEÇÃO" ou o marcador `[[Pág. N]]`
- **THEN** os blocos permanecem separados no Markdown final

#### Scenario: Marcador SUBTÍTULO não é anexado ao dispositivo anterior

- **WHEN** um artigo, um parágrafo, um inciso ou um cabeçalho `TÍTULO` já formado é seguido, no mesmo bloco de página, pelo marcador bare "SUBTÍTULO N" (ex. "SUBTÍTULO I")
- **THEN** o marcador `SUBTÍTULO N` permanece separado, como parágrafo próprio, do conteúdo anterior no Markdown final

#### Scenario: Dois precedentes jurisprudenciais consecutivos não são unidos

- **WHEN** um bloco termina com uma citação de julgamento como "(AgInt no REsp 1739440/SP, Rel. Ministra REGINA HELENA COSTA, PRIMEIRA TURMA, julgado em 08/11/2018, DJe 26/11/2018) (Grifos acrescidos)." e o bloco seguinte, no mesmo grupo geométrico, é uma linha inteiramente em caixa alta como "RECURSO ESPECIAL. INDENIZAÇÃO POR DANO MORAL. ..."
- **THEN** os dois blocos permanecem separados por quebra de parágrafo no Markdown final, sem fundir os dois precedentes em um único parágrafo

### Requirement: Remoção de cabeçalhos e rodapés repetitivos

O sistema SHALL remover, de cada bloco de página, apenas linhas marginais comprovadamente repetitivas entre páginas e com posição semelhante (topo ou rodapé do bloco), limitadas a: data e hora de impressão; nome técnico do arquivo de origem; URL repetida; e contador de página no formato "N/total". O sistema SHALL preservar o marcador `[[Pág. N]]` em todas as páginas e SHALL NOT remover conteúdo jurídico apenas por ele se repetir entre páginas.

#### Scenario: Rodapé técnico é removido

- **WHEN** uma linha contendo data/hora de impressão, nome de arquivo técnico, URL ou contador "N/186" aparece de forma repetida na mesma posição (topo ou rodapé) em uma fração alta das páginas
- **THEN** essa linha é removida do bloco de cada página em que aparece
- **AND** o marcador `[[Pág. N]]` correspondente permanece intacto

#### Scenario: Conteúdo jurídico repetido é preservado

- **WHEN** um trecho de conteúdo jurídico (ex. cabeçalho de seção, ementa) se repete entre páginas mas não corresponde a nenhum dos padrões marginais autorizados
- **THEN** o trecho permanece inalterado em todas as páginas em que aparece

### Requirement: Normalização contextual de símbolos jurídicos

O sistema SHALL normalizar exclusivamente os padrões jurídicos corrompidos pela extração explicitamente autorizados: "Art. N o" para "Art. Nº", "§ N o" para "§ Nº", "Lei n o" para "Lei nº", e ordinais jurídicos equivalentes quando o contexto for inequívoco. O sistema SHALL NOT substituir ocorrências da letra "o" isoladas após números fora desses contextos, e SHALL preservar números, datas, valores monetários e referências legais não abrangidos por esses padrões.

#### Scenario: Símbolo jurídico corrompido é normalizado

- **WHEN** o Markdown extraído contém "Art. 1 o" ou "§ 1 o" ou "Lei n o"
- **THEN** o Markdown final contém, respectivamente, "Art. 1º", "§ 1º" e "Lei nº"

#### Scenario: Números e datas fora de contexto não são alterados

- **WHEN** o Markdown contém números, datas, valores monetários ou referências legais que não correspondem a nenhum padrão autorizado de normalização
- **THEN** esse conteúdo permanece byte-idêntico ao extraído

### Requirement: Reconhecimento de estrutura legislativa

O sistema SHALL reconhecer marcadores estruturais formais (PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO, SUBSEÇÃO) e, quando o título correspondente aparecer imediatamente a seguir dentro do mesmo bloco de página, SHALL uni-los em um único cabeçalho Markdown (`#` para PARTE, `##` para LIVRO, `###` para TÍTULO, `####` para SUBTÍTULO e CAPÍTULO, `#####` para SEÇÃO, `######` para SUBSEÇÃO). O sistema SHALL NOT converter texto comum em cabeçalho apenas por estar em maiúsculas.

#### Scenario: Marcador estrutural e título são unidos

- **WHEN** o Markdown contém "LIVRO I" seguido, na linha seguinte, por "DAS PESSOAS"
- **THEN** o Markdown final contém um único cabeçalho Markdown "## LIVRO I — DAS PESSOAS" ou equivalente que preserve ambos os textos originais

#### Scenario: SUBTÍTULO forma cabeçalho próprio no mesmo nível de CAPÍTULO

- **WHEN** o Markdown contém o marcador bare "SUBTÍTULO I" seguido, no mesmo bloco de página, por sua denominação (ex. "Do Casamento")
- **THEN** o Markdown final contém um único cabeçalho Markdown "#### SUBTÍTULO I — Do Casamento" ou equivalente que preserve ambos os textos originais

#### Scenario: Texto maiúsculo comum não vira título

- **WHEN** uma linha em maiúsculas não é precedida por um marcador estrutural formal (PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO)
- **THEN** essa linha permanece como texto comum no Markdown final

### Requirement: Separação do índice final

O sistema SHALL identificar o índice posicionado após o encerramento do corpo normativo e SHALL inserir um cabeçalho `# ÍNDICE` imediatamente antes do início do conteúdo identificado como índice, sem excluir ou reordenar esse conteúdo.

#### Scenario: Índice é identificado e demarcado

- **WHEN** o documento contém, após o último artigo do corpo normativo, um bloco de páginas cujo conteúdo é predominantemente uma lista de títulos e números de página
- **THEN** o Markdown final contém o cabeçalho `# ÍNDICE` imediatamente antes desse bloco
- **AND** todo o conteúdo original do índice permanece presente e na mesma ordem

#### Scenario: Ausência de índice detectável

- **WHEN** o documento não contém um padrão de índice identificável após o corpo normativo
- **THEN** o sistema NÃO insere o cabeçalho `# ÍNDICE`
- **AND** nenhum conteúdo é removido ou alterado

