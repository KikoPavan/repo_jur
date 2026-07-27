# Pipeline de Conversão Jurídica

Conversor de PDFs jurídicos para Markdown UTF-8 auditável. O pipeline processa o
documento página por página, registra o método usado em cada uma e gera um
relatório JSON com metadados de execução, hashes e resultados de validação.

## Instalação

O projeto requer Python 3.12 e usa `uv` para gerenciar o ambiente e as
dependências:

```bash
uv sync
```

O comando de console é `converter-juridico`. No ambiente gerenciado pelo
projeto, execute-o com `uv run converter-juridico`; se o pacote já estiver
instalado e o ambiente estiver ativo, ele também pode ser chamado diretamente.

## Variáveis de ambiente

Copie o arquivo de exemplo para `.env`:

```bash
cp .env.example .env
```

Preencha a configuração antes da execução. A CLI carrega o `.env`
automaticamente.

| Variável | Finalidade |
| --- | --- |
| `INPUT_DIR` | Diretório convencional para PDFs de entrada. A CLI atual não lê essa variável: o caminho do PDF é informado como argumento posicional. |
| `OUTPUT_DIR` | Diretório no qual o Markdown convertido é gravado; o padrão usado na ausência da variável é `output`. |
| `LOGS_DIR` | Diretório no qual o relatório técnico `.report.json` é gravado; o padrão é `logs`. |
| `TEMP_DIR` | Raiz dos diretórios temporários criados para os PDFs isolados por página; o padrão é `var/tmp`. |
| `GEMINI_API_KEY` | Credencial usada nas chamadas de OCR ao endpoint compatível com OpenAI. É obrigatória quando uma página exige OCR e o OCR está habilitado. |
| `GEMINI_MODEL` | Nome do modelo multimodal usado pelo OCR. É obrigatório quando uma página exige OCR e o OCR está habilitado. |
| `GEMINI_BASE_URL` | URL base do serviço Gemini compatível com a API OpenAI. Se a variável não existir, a CLI usa `https://generativelanguage.googleapis.com/v1beta/openai/`. |
| `OCR_ENABLED` | Habilita o OCR quando o valor, sem distinção entre maiúsculas e minúsculas, é `true`; qualquer outro valor o desabilita. |
| `OCR_PROMPT_FILE` | Caminho do prompt versionado de transcrição literal; o padrão é `prompts/ocr_literal_ptbr.txt`. |
| `NATIVE_MIN_TEXT_CHARS` | Quantidade mínima inicial de caracteres usada como um dos sinais de texto nativo; o padrão é `50`. |
| `FULL_PAGE_IMAGE_MIN_RATIO` | Proporção mínima da página ocupada por uma imagem para tratá-la como imagem de página inteira; o padrão é `0.70`. |
| `SIGNIFICANT_IMAGE_MIN_RATIO` | Proporção mínima da página ocupada por uma imagem para considerá-la significativa no roteamento; o padrão é `0.15`. |

Os três limites de roteamento são parâmetros técnicos iniciais, não regras
jurídicas universais. Os valores de proporção devem ficar entre `0.0` e `1.0`,
e `SIGNIFICANT_IMAGE_MIN_RATIO` não pode ser maior que
`FULL_PAGE_IMAGE_MIN_RATIO`.

Não versione o arquivo `.env` nem divulgue `GEMINI_API_KEY`.

## Privacidade e OCR externo

Páginas classificadas como `ocr_integral` ou `hibrido` têm sua imagem enviada
à API externa do Gemini para transcrição. Isso é uma chamada de rede para um
serviço de terceiros. Antes de executar OCR real, o operador deve confirmar que
tem autorização para enviar o conteúdo do documento a esse serviço e que o uso
está de acordo com as políticas aplicáveis e com a política do provedor.

Use `--no-ocr` para impedir qualquer chamada externa. Nesse modo, uma página
que dependa de OCR não poderá ser processada e causará falha no modo estrito,
ou será registrada como ilegível quando `--allow-partial` também for usado.
Páginas classificadas como `texto_nativo` são processadas localmente.

O relatório e os logs técnicos nunca armazenam o conteúdo integral das páginas
nem a chave da API. Eles registram somente informações técnicas sanitizadas e
metadados, como contagens de caracteres, métodos, durações, avisos e hashes.

## Execução

Converta um PDF por execução:

```bash
uv run converter-juridico caminho/documento.pdf
```

Opções disponíveis:

- `--overwrite`: permite substituir arquivos de saída existentes.
- `--allow-partial`: permite publicar páginas com texto ilegível, marcadas com
  `[[TEXTO ILEGÍVEL]]`.
- `--no-ocr`: desabilita chamadas de OCR.
- `--keep-temp`: preserva os arquivos temporários para diagnóstico.
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: define o nível do log
  técnico; o padrão é `INFO`.

Por padrão, uma falha impede a publicação da nova saída, e arquivos existentes
não são substituídos.

## Códigos de saída

| Código | Significado |
| ---: | --- |
| `0` | Sucesso |
| `1` | Falha de entrada ou configuração |
| `2` | Falha de conversão ou OCR |
| `3` | Falha de validação |
| `4` | Conflito de saída existente |

## Saídas e diagnóstico

Para um PDF chamado `documento.pdf`, a execução grava:

```text
OUTPUT_DIR/documento.md
LOGS_DIR/documento.report.json
```

O Markdown mantém um bloco para cada página e identifica o método de conversão.
O relatório de mesmo nome-base registra o estado da execução e de cada página,
além de metadados, versões e hashes úteis para auditoria.

Use `--log-level` para controlar a verbosidade dos logs técnicos. Em caso de
problema, `--keep-temp` preserva em um subdiretório de `TEMP_DIR` os PDFs de
página única criados durante a execução, permitindo inspeção manual. Sem essa
opção, esses temporários são removidos ao final.

## Finalidade do MarkItDown e fidelidade visual

O MarkItDown, biblioteca usada na conversão, é direcionado a pipelines de
análise textual e extração de conteúdo. Ele não garante reprodução visual fiel
do PDF original, incluindo layout, formatação exata ou posicionamento dos
elementos. O Markdown produzido destina-se a sistemas de análise de texto,
indexação e busca; ele não substitui o documento original como representação
visual.

## Especificação do projeto

As decisões de arquitetura e os artefatos de planejamento permanecem em
`docs/` e `openspec/`. A implementação e este guia de uso são a referência
operacional da ferramenta.
