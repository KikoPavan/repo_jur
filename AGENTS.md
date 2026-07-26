# Pipeline Jurídico — Guia do Agente

## Topologia Multi-Agente

- **Orquestrador — Claude Code:** lê `tasks.md` e `LOOPS.md`, seleciona a próxima subtarefa, prepara a instrução de execução e solicita aprovação humana quando necessário. Não implementa código.
- **Implementador — OpenCode:** cria os testes e implementa somente o código necessário para a subtarefa atual.
- **Verificador — Codex:** revisa as alterações, executa os testes e valida o OpenSpec. Não implementa código nem corrige diretamente os arquivos.
- **Gemini API:** serviço utilizado pelo pipeline para OCR e processamento multimodal. Não participa como agente do fluxo de desenvolvimento.

Nenhum agente executa `git push`, arquiva mudanças ou realiza OCR real sem aprovação humana.

## Stack

| Item | Detalhe |
| --- | --- |
| Python | 3.12 (`.venv` ativo, `python3 --version` confirma) |
| Gerenciador | `uv` (não pip/poetry). `uv run`, `uv add`, `uv sync` |
| Layout | `src/` (pacote `pipeline_juridico`) |
| CLI | `converter-juridico` (console script) |
| Deps-chave | `markitdown[all]`, `markitdown-ocr`, `pymupdf`, `pillow`, `google-genai`, `python-dotenv` |
| Teste | `pytest` em `tests/` |
| Design | `docs/Pipeline_Conversao_Juridica_Corrigido.md` |
| .env | Requer `GEMINI_API_KEY`; nunca exibir, registrar ou versionar seu valor (já preenchida) |

## Comandos essenciais

```bash
uv sync                    # Sincronizar ambiente
uv run pytest tests/       # rodar testes
uv run pytest tests/ -k "nome"  # teste específico
uv run converter-juridico ...   # executar pipeline
uv add <pacote>            # adicionar dependência
#  Não usar `pip install`, Poetry ou edição manual do `uv.lock`
```

## Workflow OpenSpec

1. Claude identifica a mudança ativa com `openspec list`.
2. Claude lê `LOOPS.md` e `openspec/changes/<change-id>/tasks.md`.
3. Claude seleciona somente a primeira subtarefa não concluída.
4. OpenCode cria ou atualiza os testes necessários para a subtarefa.
5. OpenCode implementa somente o código necessário para fazer os testes passarem.
6. OpenCode executa os testes relacionados e informa os arquivos alterados.
7. Codex revisa as alterações, executa os testes e valida o OpenSpec.
8. Somente após aprovação do Codex, Claude marca a subtarefa como concluída.
9. O ciclo reinicia na próxima subtarefa.

Após duas tentativas sem progresso na mesma subtarefa, interromper a execução, não marcar a tarefa e registrar o erro, os comandos executados e os resultados obtidos.

## Arquitetura do pipeline

Módulos planejados em `src/pipeline_juridico/`:
- `models.py` — tipos: status, método, resultado, relatório
- `inspector.py` — extração de texto/imagem via PyMuPDF
- `router.py` — classifica página: `texto_nativo`, `ocr_integral`, `hibrido`, `vazia`, `erro`
- `engines.py` — MarkItDown nativo + OCR
- `converter.py` — orquestra fragmento → conversão → composição
- `cleaner.py` — limpeza conservadora (CRLF→LF, trailing spaces, linhas vazias)
- `validator.py` — valida marcadores, conteúdo, hashes
- `report.py` — relatório JSON versionado
- `cli.py` — entrypoint `converter-juridico`
- `config.py` — limites de roteamento centralizados
- `hashing.py` — SHA-256 utilitário

Marcador canônico de página:

`[[Pág. N]]` seguido de `<!-- método: <método_de_conversão> -->`.

Métodos permitidos: `texto_nativo`, `ocr_integral`, `hibrido`, `vazia` e `erro`.

## Regras de implementação

- Código de implementação deve ficar em `src/pipeline_juridico/` e testes em `tests/`
- Outros arquivos, como `pyproject.toml`, `prompts/`, `docs/` e `openspec/`, somente podem ser alterados quando a tarefa exigir
- Não refatorar código adjacente que não esteja quebrado
- Nunca registrar segredos ou conteúdo integral de documentos em logs
- Limpeza Markdown: idempotente, conservadora (não remover cabeçalhos/rodapés/números/assinaturas)
- Prompt de OCR em arquivo versionado (`prompts/ocr_literal_ptbr.txt`)
- `--allow-partial` é o único modo que permite publicar páginas contendo `[[TEXTO ILEGÍVEL]]`
- OpenCode deve seguir a sequência teste → implementação → execução dos testes
- OpenCode não pode marcar tarefas como concluídas
- OpenCode não pode alterar requisitos, design ou escopo para fazer testes passarem
