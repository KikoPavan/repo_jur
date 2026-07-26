# Pipeline de Conversão Jurídica com MarkItDown

## Documento técnico corrigido — Fase 1

**Versão:** 1.0  
**Data:** 25 de julho de 2026  
**Status:** especificação para desenvolvimento  
**Gestão:** OpenSpec, esquema `spec-driven`

## 1. Objetivo

Desenvolver um pipeline reproduzível em Python 3.12, gerenciado por `uv`, para converter exclusivamente documentos jurídicos em PDF para Markdown UTF-8.

O pipeline deve preservar a rastreabilidade por página, tornar explícito o uso de OCR, aplicar limpeza conservadora e impedir que páginas omitidas ou falhas de OCR sejam classificadas como sucesso.

O objetivo é preservar conteúdo textual e estrutura útil para análise posterior. O projeto não promete reprodução visual ou tipográfica idêntica ao PDF e não considera resultados de OCR por LLM absolutamente determinísticos.

## 2. Escopo da Fase 1

Incluído:

- validação do PDF de entrada;
- inspeção e processamento página por página;
- conversão de texto nativo com MarkItDown;
- OCR controlado para páginas escaneadas ou mistas;
- marcadores explícitos de página;
- limpeza conservadora;
- validação de integridade;
- relatório técnico JSON;
- gravação atômica;
- CLI para um PDF por execução;
- testes unitários, integração e contrato.

Fora do escopo:

- YAML front matter;
- conformidade OKF completa;
- classificação ou interpretação jurídica;
- resumo, reescrita ou correção semântica;
- extração estruturada de entidades;
- identificação automática de jurisprudência;
- processamento de formatos diferentes de PDF;
- processamento em lote.

## 3. Princípios obrigatórios

1. O PDF original é somente leitura.
2. Cada página do PDF corresponde a exatamente um bloco no Markdown e um registro no JSON.
3. Nenhuma página pode desaparecer silenciosamente.
4. OCR necessário sem resultado verificável é falha.
5. A saída final só é publicada depois da validação completa.
6. Limpeza não pode alterar conteúdo jurídico.
7. Segredos e conteúdo integral não podem aparecer nos logs.
8. Funcionalidades futuras devem ser propostas em mudanças OpenSpec separadas.

## 4. Arquitetura

```text
PDF local
  ↓
Validação da entrada
  ↓
Inspeção PyMuPDF
  ↓
Fragmentação por página
  ↓
Roteamento da página
  ├─ texto_nativo → MarkItDown sem plugins
  ├─ ocr_integral → MarkItDown + markitdown-ocr
  ├─ hibrido      → MarkItDown + markitdown-ocr
  ├─ vazia        → bloco vazio controlado
  └─ erro         → falha estrita ou saída parcial autorizada
  ↓
Composição com [[Pág. N]]
  ↓
Limpeza conservadora
  ↓
Validação página/documento
  ↓
Markdown temporário + JSON temporário
  ↓
Promoção atômica para output/ e logs/
```

## 5. Estados por página

| Estado | Significado |
|---|---|
| `texto_nativo` | Texto extraível e utilizável, sem necessidade relevante de OCR |
| `ocr_integral` | Conteúdo visual significativo sem camada textual utilizável |
| `hibrido` | Texto nativo mais conteúdo rasterizado relevante que exige OCR |
| `vazia` | Ausência comprovada de texto e conteúdo visual significativo |
| `erro` | Falha de inspeção, conversão, OCR ou validação |

A classificação não pode depender apenas de um limite fixo de caracteres. Deve considerar qualidade textual, imagens, área ocupada, imagem semelhante a página inteira e resultado da conversão.

## 6. Contrato do Markdown

```markdown
[[Pág. 1]]
<!-- método: texto_nativo -->

Conteúdo da página.
```

Regras:

- marcador exato: `[[Pág. N]]`;
- numeração de 1 até o total de páginas;
- um único marcador por página;
- um único comentário de método por página;
- ordem idêntica ao PDF;
- codificação UTF-8;
- finais de linha LF;
- uma quebra de linha ao final.

## 7. OCR

O OCR usa `markitdown-ocr` com cliente OpenAI-compatible. O modelo, a chave e a URL base devem ser definidos por ambiente.

Páginas exclusivamente nativas não devem ser enviadas ao OCR externo.

O pipeline deve tratar como erro:

- OCR requerido sem configuração;
- erro ou aviso da API;
- retorno vazio;
- ausência de evidência de bloco OCR;
- modelo sem suporte a visão;
- timeout ou limite de cota.

O prompt de OCR deve solicitar transcrição literal, preservar ordem de leitura, proibir resumo e usar `[ilegível]` sem completar texto por inferência.

## 8. Limpeza conservadora

Permitido:

- converter CRLF e CR para LF;
- remover espaços e tabulações no fim das linhas;
- reduzir três ou mais linhas vazias para duas;
- garantir uma quebra de linha final.

Proibido:

- corrigir ortografia;
- recompor frases;
- remover cabeçalhos e rodapés repetidos;
- alterar datas, números, artigos, ementas ou assinaturas;
- reorganizar tabelas por interpretação;
- resumir ou classificar conteúdo.

## 9. Validação

A validação deve confirmar:

- total de marcadores igual ao total de páginas;
- sequência exata de 1 a N;
- ausência de duplicidade;
- método válido em cada página;
- conteúdo não vazio para estados diferentes de `vazia`;
- evidência de OCR em páginas OCR/híbridas;
- ausência de `erro` no modo estrito;
- correspondência entre Markdown e JSON;
- UTF-8, LF e quebra final;
- hashes calculados após a limpeza.

## 10. Política de falha

Modo padrão: estrito.

- Qualquer erro impede a publicação do Markdown final.
- O relatório recebe status `falha`.
- Uma saída anterior não é sobrescrita.

Modo parcial: somente com `--allow-partial`.

- Páginas em erro recebem `$$TEXTO ILEGÍVEL$$`.
- O relatório recebe status `incompleto`.
- Todas as páginas afetadas são listadas.

## 11. Saídas

```text
output/<nome>.md
logs/<nome>.report.json
```

O relatório deve conter:

- versão do esquema;
- identificador da execução;
- caminho, tamanho, hash e total de páginas do PDF;
- caminho e hash do Markdown;
- versões reais de Python e dependências;
- provedor, modelo e hash do prompt OCR;
- início, fim e duração;
- resultado individual por página;
- avisos e erros sanitizados;
- status `sucesso`, `incompleto` ou `falha`.

## 12. Estrutura do projeto

```text
repo_jur/
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── README.md
├── CHANGELOG.md
├── openspec/
├── docs/
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
├── input/.gitkeep
├── output/.gitkeep
├── logs/.gitkeep
└── var/tmp/.gitkeep
```

## 13. Dependências

```toml
[project]
name = "pipeline-conversao-juridica"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = [
    "markitdown[pdf]==0.1.6",
    "markitdown-ocr==0.1.0",
    "openai>=1.0.0",
    "pymupdf>=1.23.0",
    "python-dotenv>=1.0.0",
]
```

O `uv.lock` deve registrar as versões transitivas exatas.

## 14. Variáveis de ambiente

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

Os limites devem ser centralizados e calibrados por testes; não devem ser tratados como regra universal.

## 15. CLI

```bash
uv run converter-juridico caminho/documento.pdf
```

Opções:

```text
--overwrite
--allow-partial
--no-ocr
--keep-temp
--log-level
```

## 16. Matriz mínima de testes

1. PDF digital.
2. PDF integralmente escaneado.
3. PDF misto.
4. Página curta com texto nativo.
5. Página visualmente vazia.
6. Página com logotipo pequeno.
7. Página com imagem semelhante a página inteira.
8. OCR sem credencial.
9. OCR com aviso e retorno parcial.
10. OCR vazio.
11. PDF corrompido.
12. PDF protegido por senha.
13. Marcador ausente, duplicado e fora de ordem.
14. Falha após uma saída válida existente.
15. Preservação de datas, processos, artigos, ementas, tabelas e assinaturas.
16. Remoção dos temporários.
17. Proteção contra sobrescrita.
18. Correspondência integral entre Markdown e relatório.

## 17. Critérios de aceite

A versão 0.1.0 somente pode ser considerada concluída quando:

- todos os requisitos OpenSpec possuem testes correspondentes;
- os testes automatizados passam;
- PDFs reais digitais, escaneados e mistos foram validados;
- nenhuma falha de OCR resulta em status `sucesso`;
- cada página possui bloco e registro técnico;
- a saída final é atômica;
- o relatório contém hashes e versões reais;
- `openspec validate establish-juridical-pdf-conversion-pipeline --strict` passa sem erro;
- todas as tarefas da mudança estão marcadas como concluídas.

## 18. Fluxo OpenSpec

Terminal:

```bash
npm install -g @fission-ai/openspec@latest
openspec init
openspec update
openspec validate establish-juridical-pdf-conversion-pipeline --strict
openspec status --change establish-juridical-pdf-conversion-pipeline
```

Chat do agente:

```text
/opsx:apply establish-juridical-pdf-conversion-pipeline
/opsx:verify establish-juridical-pdf-conversion-pipeline
/opsx:archive establish-juridical-pdf-conversion-pipeline
```

`/opsx:verify` depende do perfil expandido. No perfil padrão, a verificação deve ser executada por testes e validação antes do arquivamento.

## 19. Referências oficiais consultadas

- OpenSpec: https://github.com/Fission-AI/OpenSpec
- Fluxo OPSX: https://github.com/Fission-AI/OpenSpec/blob/main/docs/opsx.md
- Esquema `spec-driven`: https://github.com/Fission-AI/OpenSpec/blob/main/schemas/spec-driven/schema.yaml
- MarkItDown: https://github.com/microsoft/markitdown
- Plugin MarkItDown OCR: https://github.com/microsoft/markitdown/blob/main/packages/markitdown-ocr/README.md
- Versão MarkItDown no PyPI: https://pypi.org/project/markitdown/
- Versão MarkItDown OCR no PyPI: https://pypi.org/project/markitdown-ocr/
