## Purpose

Estabelecer uma conversão auditável de PDFs jurídicos para Markdown, preservando a rastreabilidade por página e tornando explícitas falhas, uso de OCR e limitações da saída.

## ADDED Requirements

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

O sistema SHALL limitar a limpeza à normalização de fim de linha, remoção de espaços finais e redução de três ou mais linhas vazias consecutivas para duas linhas vazias.

#### Scenario: Conteúdo jurídico é preservado

- **WHEN** a limpeza é aplicada
- **THEN** datas, números processuais, artigos, ementas, assinaturas, tabelas, marcadores de página e blocos OCR permanecem semanticamente inalterados

#### Scenario: Transformação semântica é solicitada

- **WHEN** uma regra de limpeza implicar resumir, corrigir, reorganizar, deduplicar cabeçalhos ou interpretar conteúdo jurídico
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
