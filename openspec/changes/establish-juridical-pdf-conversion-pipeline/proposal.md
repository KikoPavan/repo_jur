# Establish Juridical PDF Conversion Pipeline

## Why

O projeto precisa de uma base limpa e reproduzível para converter PDFs jurídicos em Markdown antes das etapas futuras de estruturação em Open Knowledge Format. A documentação anterior misturava requisitos comportamentais com código ainda não validado, utilizava uma estrutura de pacote Python inválida e permitia que falhas de OCR fossem tratadas como sucesso.

## What Changes

- Criar um pipeline Python 3.12 gerenciado por `uv`, com layout `src` e responsabilidades separadas.
- Validar o PDF de entrada antes do processamento e preservar o arquivo original.
- Processar cada página de forma isolada para obter paginação, rastreabilidade e repetição seletiva.
- Usar MarkItDown como motor principal de PDF para Markdown.
- Encaminhar somente páginas classificadas como candidatas a OCR para o mecanismo `markitdown-ocr`.
- Registrar por página o método efetivamente escolhido: `texto_nativo`, `ocr_integral`, `hibrido`, `vazia` ou `erro`.
- Adotar o marcador canônico `[[Pág. N]]` e comentário técnico de método.
- Aplicar limpeza conservadora limitada a normalização de quebras de linha, espaços finais e excesso de linhas vazias.
- Validar sequência, quantidade, estado e conteúdo de todas as páginas antes de publicar a saída.
- Gravar Markdown e relatório JSON de forma atômica.
- Falhar por padrão quando OCR obrigatório não estiver configurado, não retornar conteúdo verificável ou produzir aviso de falha.
- Permitir saída parcial apenas por opção explícita da CLI, com status `incompleto` e marcador de ilegibilidade.
- Registrar hashes, versões, modelo OCR, tempos e resultado por página sem expor chaves ou conteúdo jurídico integral nos logs.

## Capabilities

### New Capabilities

- `juridical-pdf-conversion`: Conversão auditável de PDFs jurídicos para Markdown, com roteamento por página, OCR controlado, limpeza conservadora, validação estrita e relatório técnico.

### Modified Capabilities

- None.

## Impact

- Novo pacote Python em `src/pipeline_juridico/`.
- Novos comandos de linha de comando para conversão e validação.
- Dependências principais: `markitdown[pdf]`, `markitdown-ocr`, `openai`, `pymupdf` e `python-dotenv`.
- Novos diretórios operacionais: `input/`, `output/`, `logs/` e `var/tmp/`.
- Novos testes unitários, de integração e de contrato de saída.
- Possível envio externo apenas de imagens de páginas roteadas para OCR; o uso depende de autorização e configuração do operador.
- Nenhuma implementação de YAML front matter, classificação jurídica, resumo, extração semântica ou conformidade OKF completa nesta mudança.
