# Tarefas de implementação

## 1. Fundação do projeto

- [x] 1.1 Inicializar o repositório com Python 3.12 usando `uv` e criar o `pyproject.toml` com as dependências aprovadas.
- [x] 1.2 Configurar o pacote `src/pipeline_juridico/` e o comando de console `converter-juridico`.
- [x] 1.3 Criar diretórios operacionais, arquivos `.gitkeep`, `.gitignore`, `.env.example`, README e changelog.
- [x] 1.4 Adicionar modelos tipados para status da execução, método da página, resultado da página e esquema do relatório.
- [x] 1.5 Adicionar descoberta das versões das dependências e utilitários SHA-256.

## 2. Inspeção da entrada e isolamento de páginas

- [x] 2.1 Implementar validação do caminho PDF, abertura segura, detecção de criptografia e contagem de páginas.
- [x] 2.2 Registrar tamanho e SHA-256 do arquivo de origem antes do processamento.
- [x] 2.3 Implementar criação de PDFs isolados de uma página no diretório temporário específico da execução.
- [x] 2.4 Garantir tratamento somente leitura da origem e limpeza dos temporários em sucesso e falha.
- [x] 2.5 Adicionar testes para entradas ausentes, inválidas, corrompidas, criptografadas e sem páginas utilizáveis.

## 3. Roteamento de páginas

- [x] 3.1 Implementar inspeção da qualidade do texto nativo usando blocos PyMuPDF e métricas de caracteres.
- [x] 3.2 Implementar inspeção de conteúdo rasterizado usando quantidade de imagens, proporção de área e sinais de imagem de página inteira.
- [x] 3.3 Implementar roteamento para `texto_nativo`, `ocr_integral`, `hibrido`, `vazia` ou `erro`.
- [x] 3.4 Centralizar limites de roteamento na configuração e validar seus intervalos.
- [x] 3.5 Adicionar testes unitários para páginas nativas curtas, escaneadas, mistas, vazias, com logotipos e assinaturas.

## 4. Motores de conversão

- [x] 4.1 Implementar o motor MarkItDown nativo com plugins desabilitados.
- [x] 4.2 Implementar o motor MarkItDown OCR com `OpenAI`, `base_url` opcional, modelo e prompt versionado de transcrição literal.
- [x] 4.3 Falhar na configuração quando OCR for necessário e cliente, chave ou modelo estiver indisponível.
- [x] 4.4 Capturar avisos do OCR e sanitizar mensagens de erro.
- [x] 4.5 Verificar evidência OCR não vazia para cada página `ocr_integral` e `hibrido`.
- [x] 4.6 Adicionar testes simulados para OCR bem-sucedido, falha emitida apenas como aviso, resposta vazia, timeout e modelo indisponível.

## 5. Composição e limpeza do Markdown

- [x] 5.1 Implementar o marcador exato `[[Pág. N]]` e o contrato do comentário de método.
- [x] 5.2 Compor blocos na ordem numérica original sem vazamento de contexto entre páginas.
- [x] 5.3 Implementar limpeza conservadora e idempotente para finais de linha, espaços finais, linhas vazias e quebra final.
- [x] 5.4 Preservar tabelas Markdown, delimitadores OCR, citações legais, datas, números processuais e assinaturas nos testes de limpeza.
- [x] 5.5 Implementar `[[TEXTO ILEGÍVEL]]` somente para saída parcial explicitamente autorizada.

## 6. Validação e saída atômica

- [x] 6.1 Validar quantidade, sequência exata, unicidade dos marcadores e um comentário de método por página.
- [x] 6.2 Validar presença de conteúdo conforme o estado e rejeitar erros no modo estrito.
- [x] 6.3 Validar correspondência entre blocos do Markdown e registros de página do JSON.
- [x] 6.4 Validar UTF-8, finais de linha LF e quebra de linha final.
- [x] 6.5 Implementar gravação temporária e promoção atômica após aprovação de todas as validações.
- [x] 6.6 Proteger saída existente salvo quando `--overwrite` for informado.
- [x] 6.7 Adicionar testes com injeção de falha comprovando que uma saída válida anterior nunca é corrompida.

## 7. Relatório técnico

- [x] 7.1 Implementar relatório JSON versionado com origem, saída, runtime, OCR, tempos e dados por página.
- [x] 7.2 Registrar em runtime as versões instaladas e o SHA-256 do prompt.
- [x] 7.3 Registrar quais páginas foram transmitidas ao OCR sem persistir o conteúdo das páginas.
- [x] 7.4 Implementar os estados finais `sucesso`, `incompleto` e `falha`.
- [x] 7.5 Adicionar JSON Schema ou testes de contrato equivalentes para campos obrigatórios e tipos de dados.

## 8. CLI e comportamento operacional

- [x] 8.1 Implementar o argumento posicional PDF e as opções `--overwrite`, `--allow-partial`, `--no-ocr`, `--keep-temp` e `--log-level`.
- [x] 8.2 Implementar os códigos de saída documentados para entrada, conversão, validação e conflito de saída.
- [x] 8.3 Garantir que logs nunca exponham chaves, tokens ou conteúdo integral do documento.
- [x] 8.4 Adicionar testes de integração da CLI para sucesso estrito, falha estrita, saída parcial e proteção de sobrescrita.

## 9. Testes de aceite

- [x] 9.1 Converter um PDF jurídico totalmente digital e verificar que nenhuma chamada OCR ocorra.
- [x] 9.2 Converter um PDF jurídico totalmente escaneado e verificar evidência OCR em todas as páginas não vazias.
- [x] 9.3 Converter um PDF jurídico misto e verificar o registro correto de páginas nativas, híbridas, escaneadas e vazias.
- [x] 9.4 Verificar que cada página de origem possui exatamente um bloco Markdown e um registro no relatório.
- [x] 9.5 Verificar que falha de OCR nunca produz status global `sucesso`.
- [x] 9.6 Verificar presença dos hashes da origem e da saída e das versões dos pacotes no relatório.
- [x] 9.7 Comparar conteúdo jurídico representativo com a origem para datas, números processuais, citações, títulos, tabelas e assinaturas.

## 10. Documentação e conclusão OpenSpec

- [x] 10.1 Documentar instalação, variáveis de ambiente, aviso de privacidade, execução, códigos de saída e diagnóstico no README.
- [x] 10.2 Documentar que o MarkItDown é direcionado a pipelines de análise textual, não à reprodução visual do PDF.
- [x] 10.3 Executar a suíte completa de testes e registrar o resultado.
- [x] 10.4 Executar `openspec validate establish-juridical-pdf-conversion-pipeline --strict` e resolver todos os apontamentos.
- [x] 10.5 Executar `/opsx:verify establish-juridical-pdf-conversion-pipeline` quando o fluxo expandido estiver habilitado. (N/A: `/opsx:verify` não existe neste ambiente — só opsx:apply/archive/explore/propose/sync/update estão instalados; a condição do próprio item não foi atendida.)
- [x] 10.6 Marcar todas as tarefas concluídas, sincronizar as especificações e arquivar a mudança somente após aprovação dos critérios de aceite.
