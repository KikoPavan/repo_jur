# Design: Juridical PDF Conversion Pipeline

## Context

A Fase 1 precisa produzir Markdown auditável para futura ingestão em uma base jurídica. O PDF pode conter texto nativo, páginas escaneadas, páginas mistas, carimbos e imagens. MarkItDown é adequado como motor de conversão orientado a análise textual, mas não oferece garantia absoluta de reprodução visual. O plugin `markitdown-ocr` usa um modelo de visão e pode continuar a conversão quando uma chamada ao modelo falha; por isso, o pipeline deve adicionar sua própria verificação estrita.

A solução deve funcionar em Python 3.12, ser gerenciada por `uv`, não alterar o PDF de origem e manter a futura etapa OKF desacoplada.

## Goals / Non-Goals

### Goals

- Produzir Markdown com rastreabilidade de todas as páginas.
- Tornar explícito quando texto veio de camada nativa, OCR integral ou composição híbrida.
- Impedir que falhas de OCR sejam tratadas como sucesso.
- Manter limpeza estritamente conservadora.
- Produzir relatório suficiente para auditoria e repetição seletiva.
- Permitir execução reproduzível pelo `uv.lock`.

### Non-Goals

- Reproduzir a aparência visual do PDF com fidelidade tipográfica.
- Corrigir erros do documento de origem.
- Resumir, interpretar ou classificar conteúdo jurídico.
- Adicionar YAML front matter ou estrutura OKF.
- Processar DOCX, imagens isoladas, planilhas, apresentações ou URLs.
- Implementar processamento em lote nesta mudança.

## Decisions

### 1. Layout Python padrão em `src/`

O pacote será `pipeline_juridico`, localizado em `src/pipeline_juridico/`.

**Rationale:** nomes de módulos Python não podem iniciar com número em imports normais. O layout `src` evita importação acidental do diretório de trabalho e facilita empacotamento e testes.

**Alternative considered:** manter `00_Pipeline/src/00_Pipeline`. Rejeitado porque `00_Pipeline` não é um identificador Python válido para instruções `import`.

### 2. Dependências mínimas e versões iniciais

```toml
[project]
name = "pipeline-conversao-juridica"
version = "0.1.0"
description = "Conversão auditável de PDFs jurídicos para Markdown"
readme = "README.md"
requires-python = ">=3.12,<3.13"
dependencies = [
    "markitdown[pdf]==0.1.6",
    "markitdown-ocr==0.1.0",
    "openai>=1.0.0",
    "pymupdf>=1.23.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
converter-juridico = "pipeline_juridico.cli:main"

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pipeline_juridico"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

O `uv.lock` será a fonte das versões transitivas exatas. Alterações de versão devem ocorrer em mudança OpenSpec específica, acompanhadas de testes de regressão.

### 3. Estrutura de diretórios

```text
repo_jur/
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
├── openspec/
│   ├── config.yaml
│   ├── specs/
│   └── changes/
├── docs/
│   └── pipeline-conversao-juridica.md
├── src/
│   └── pipeline_juridico/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── models.py
│       ├── inspector.py
│       ├── router.py
│       ├── engines.py
│       ├── converter.py
│       ├── cleaner.py
│       ├── validator.py
│       ├── report.py
│       └── hashing.py
├── tests/
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── contract/
├── input/
│   └── .gitkeep
├── output/
│   └── .gitkeep
├── logs/
│   └── .gitkeep
└── var/
    └── tmp/
        └── .gitkeep
```

### 4. Fragmentação por página

PyMuPDF abrirá o PDF uma vez e criará um PDF temporário de uma página para cada unidade processada.

**Rationale:** garante injeção correta do marcador, isolamento de falhas, repetição seletiva e limite de memória por unidade. A fragmentação não será descrita como correção obrigatória de vazamento de memória do MarkItDown, pois a versão adotada já contém correções nessa área.

**Alternative considered:** converter o PDF inteiro e tentar reconstruir a paginação posteriormente. Rejeitado porque a saída do conversor não garante um marcador confiável para cada página.

### 5. Dois motores MarkItDown

Serão mantidas duas instâncias:

- `native_engine`: MarkItDown com plugins desabilitados.
- `ocr_engine`: MarkItDown com plugins habilitados, `llm_client`, `llm_model` e prompt de transcrição literal.

O cliente deve ser instanciado pela classe `OpenAI`, admitindo `base_url` opcional para provedores OpenAI-compatible.

**Rationale:** separar os motores impede envio externo de páginas classificadas como exclusivamente nativas e torna o método escolhido auditável.

### 6. Roteamento por sinais combinados

O roteador não utilizará apenas um limite fixo de caracteres. Ele combinará:

- quantidade e qualidade do texto extraído por PyMuPDF;
- proporção de caracteres de substituição ou controle;
- existência e área relativa de imagens rasterizadas;
- presença de imagem semelhante a página inteira;
- dimensão e ocupação dos blocos textuais;
- resultado do primeiro estágio de conversão.

Os limites serão centralizados em configuração e cobertos por fixtures reais e sintéticas.

Estados:

- `texto_nativo`: camada textual utilizável, sem sinal relevante de conteúdo rasterizado não capturado;
- `ocr_integral`: página visual significativa sem camada textual utilizável;
- `hibrido`: texto nativo utilizável mais conteúdo rasterizado significativo que requer OCR;
- `vazia`: ausência comprovada de texto e conteúdo visual relevante;
- `erro`: falha de inspeção, conversão, OCR ou validação da página.

### 7. Contrato do Markdown

Cada página será composta assim:

```markdown
[[Pág. 1]]
<!-- método: texto_nativo -->

<conteúdo da página>
```

Métodos permitidos no comentário:

```text
texto_nativo
ocr_integral
hibrido
vazia
erro
```

O comentário é metadado operacional temporário desta fase e não é YAML front matter.

### 8. Verificação adicional do OCR

O plugin pode converter uma página mesmo quando a chamada ao modelo falha. Portanto, o pipeline deve:

1. capturar avisos e logs do conversor OCR durante cada página;
2. verificar que páginas `ocr_integral` ou `hibrido` contêm conteúdo OCR não vazio;
3. verificar a presença dos delimitadores OCR esperados quando aplicáveis;
4. promover qualquer aviso de falha da API, ausência de bloco ou retorno vazio para estado `erro`;
5. registrar mensagem técnica sanitizada no relatório.

O modo padrão é estrito. `--allow-partial` é a única forma de publicar documento com páginas em erro.

### 9. Prompt de OCR

O prompt deve solicitar transcrição literal e não interpretação. Requisitos mínimos:

- transcrever todo texto legível;
- preservar ordem de leitura e estrutura de tabelas quando possível;
- não resumir, corrigir ou completar trechos;
- usar `[ilegível]` apenas quando necessário;
- não adicionar explicações antes ou depois da transcrição.

O prompt deve ficar em arquivo versionado, por exemplo `prompts/ocr_literal_ptbr.txt`, e seu hash deve ser registrado no relatório.

### 10. Limpeza conservadora

A limpeza será idempotente e executará apenas:

- normalização `CRLF`/`CR` para `LF`;
- remoção de espaços e tabulações no fim das linhas;
- redução de três ou mais linhas vazias consecutivas para duas;
- garantia de uma única quebra de linha no final do arquivo.

Não serão removidos cabeçalhos repetidos, rodapés, marcas de autenticação, números de página originais, assinaturas ou caracteres aparentemente incorretos.

### 11. Validação em duas camadas

**Validação por página:**

- marcador e método válidos;
- conteúdo não vazio para estados não vazios;
- resultado OCR comprovado quando exigido;
- registro correspondente no relatório.

**Validação do documento:**

- contagem igual ao total do PDF;
- sequência exata de 1 a N;
- ausência de duplicidade;
- nenhum estado `erro` em modo estrito;
- correspondência entre métodos do Markdown e do JSON;
- UTF-8 e LF;
- hashes calculados após a limpeza.

### 12. Gravação atômica

Markdown e relatório serão escritos primeiro em `var/tmp/<run_id>/`. Após validação, serão promovidos com operação atômica para os destinos finais. Em caso de falha, uma saída anterior nunca será sobrescrita.

### 13. Relatório JSON

Estrutura mínima:

```json
{
  "schema_version": "1.0",
  "run_id": "uuid",
  "status": "sucesso|incompleto|falha",
  "source": {
    "path": "input/documento.pdf",
    "size_bytes": 0,
    "sha256": "...",
    "pages": 0
  },
  "output": {
    "path": "output/documento.md",
    "sha256": "..."
  },
  "runtime": {
    "python": "3.12.x",
    "markitdown": "0.1.6",
    "markitdown_ocr": "0.1.0",
    "pymupdf": "..."
  },
  "ocr": {
    "enabled": true,
    "provider": "openai-compatible",
    "model": "...",
    "prompt_sha256": "..."
  },
  "timing": {
    "started_at": "ISO-8601 com fuso",
    "finished_at": "ISO-8601 com fuso",
    "duration_ms": 0
  },
  "pages": [
    {
      "number": 1,
      "method": "texto_nativo",
      "status": "sucesso",
      "characters": 0,
      "duration_ms": 0,
      "warnings": [],
      "error": null
    }
  ]
}
```

As versões devem ser obtidas em tempo de execução por metadados do ambiente, e não escritas manualmente no código.

### 14. Configuração externa

`.env.example` proposto:

```dotenv
INPUT_DIR=input
OUTPUT_DIR=output
LOGS_DIR=logs
TEMP_DIR=var/tmp

OCR_ENABLED=true
OCR_API_KEY=
OCR_BASE_URL=
OCR_MODEL=
OCR_PROMPT_FILE=prompts/ocr_literal_ptbr.txt

NATIVE_MIN_TEXT_CHARS=50
FULL_PAGE_IMAGE_MIN_RATIO=0.70
SIGNIFICANT_IMAGE_MIN_RATIO=0.15
```

Os limites são defaults iniciais, não verdades jurídicas. Devem ser calibrados por testes e não podem ser espalhados pelo código.

### 15. CLI

Comando principal:

```bash
uv run converter-juridico caminho/documento.pdf
```

Opções mínimas:

```text
--overwrite       permite substituir saída existente após validação
--allow-partial   permite publicar páginas com $$TEXTO ILEGÍVEL$$
--no-ocr          proíbe qualquer chamada externa de OCR
--keep-temp       preserva temporários para diagnóstico
--log-level       define nível de log técnico
```

Códigos de saída:

```text
0  sucesso
1  falha de entrada ou configuração
2  falha de conversão ou OCR
3  falha de validação
4  conflito de saída existente
```

### 16. Segurança

- Usar a função de conversão local mais restrita disponível.
- Validar caminho e impedir escrita fora dos diretórios configurados.
- Nunca registrar credenciais ou corpo integral das páginas.
- Informar no relatório quais páginas foram enviadas ao OCR.
- Remover temporários por padrão.
- Manter `.env`, `input/*`, `output/*`, `logs/*` e `var/tmp/*` fora do Git, preservando apenas `.gitkeep`.
- Documentos sigilosos somente podem usar OCR remoto após decisão consciente do operador e conformidade com a política do provedor.

## Risks / Trade-offs

- **OCR por LLM pode variar entre execuções** → registrar modelo, prompt e hashes; não prometer determinismo absoluto.
- **O plugin pode continuar após falha de API** → capturar avisos e exigir evidência de OCR por página.
- **Roteamento pode classificar incorretamente páginas mistas** → usar sinais combinados, fixtures reais e opção futura de override manual.
- **Fragmentação aumenta I/O e chamadas ao conversor** → usar diretório temporário por execução e limpeza imediata; priorizar auditabilidade nesta fase.
- **OCR remoto envolve custo e privacidade** → enviar somente páginas necessárias, registrar páginas enviadas e permitir `--no-ocr`.
- **MarkItDown não é ferramenta de reprodução visual de alta fidelidade** → medir preservação textual e estrutural, não aparência tipográfica.

## Migration Plan

1. Criar o novo repositório ou estrutura limpa sem importar código do pipeline anterior.
2. Inicializar Python 3.12 e dependências com `uv`.
3. Implementar os módulos seguindo `tasks.md`.
4. Executar testes unitários, integração e contrato.
5. Validar a mudança com `openspec validate ... --strict`.
6. Testar com PDFs jurídicos digitais, escaneados e mistos.
7. Publicar a versão `0.1.0` somente após os critérios de aceite.
8. Arquivar a mudança OpenSpec e sincronizar a especificação principal.
