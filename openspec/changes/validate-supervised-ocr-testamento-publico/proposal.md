## Why

O diagnóstico anterior (`audit-scanned-pdf-ocr-support`, arquivado em 2026-08-12) concluiu que a infraestrutura de OCR do pipeline já existe, já está implementada e testada com clientes LLM simulados — mas nenhuma chamada real ao Gemini jamais tinha sido feita contra `012-015-Testamento Publico.pdf`. Esta mudança executa, pela primeira vez e com aprovação humana explícita do usuário, essa validação operacional real, sem alterar nenhuma configuração (prompt, modelo, provider, cleaner, roteamento).

Esta mudança é **exclusivamente de validação operacional**. Não implementa correções, não altera prompt/modelo/provider/cleaner/roteamento/arquitetura, não instala dependências, não arquiva e não faz push. Uma única chamada real de OCR foi feita (4 páginas do mesmo documento, sem repetição).

## Pré-voo (evidência completa em `design.md`)

- `git status --short`: limpo. `git log --oneline -5`: HEAD `c802d23`. `openspec validate --all --strict`: 1 passed, 0 failed. `uv run pytest tests/`: 364 passed.
- Provider/modelo confirmados **sem imprimir a credencial**: Gemini via endpoint OpenAI-compatible (`GEMINI_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/`), `GEMINI_MODEL=gemini-3-flash-preview`, `GEMINI_API_KEY` presente (39 caracteres, valor nunca exibido), prompt `prompts/ocr_literal_ptbr.txt` (`prompt_sha256` idêntico ao registrado na auditoria anterior — não alterado).
- Comando executado, saída isolada de `output/`/`logs/` via `OUTPUT_DIR`/`LOGS_DIR` apontando para `openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/{output,logs}`:

```
OUTPUT_DIR=openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/output \
LOGS_DIR=openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/logs \
TEMP_DIR=var/tmp \
uv run converter-juridico --allow-partial "input/processos_auditoria/012-015-Testamento Publico.pdf"
```

(`--allow-partial` usado por precaução diagnóstica — para capturar evidência mesmo em caso de falha parcial; na prática as 4 páginas tiveram sucesso e nenhum marcador de texto ilegível de bloqueio foi necessário.)

## Execução (uma única chamada real)

- Início: `2026-08-12T20:08:06.450848+00:00`. Fim: `2026-08-12T20:09:35.829578+00:00`. Duração total: 89.378s.
- 4 requisições HTTP `POST .../chat/completions` — exatamente uma por página, todas `200 OK`, sem retries, sem erros.
- As 4 páginas foram roteadas como `hibrido` (confirmado no diagnóstico anterior) e todas as 4 chamaram OCR — nenhuma página adicional, nenhum outro PDF processado.
- Status final do CLI: exit code 0, `status: sucesso` no relatório.

| Pág. | Rota | Chamou OCR | Status | Caracteres | Duração |
| --- | --- | --- | --- | --- | --- |
| 1 | hibrido | sim | sucesso | 4104 | 18.338s |
| 2 | hibrido | sim | sucesso | 4212 | 43.548s |
| 3 | hibrido | sim | sucesso | 3877 | 22.756s |
| 4 | hibrido | sim | sucesso | 1036 | 4.569s |

## Conclusão (resumo — evidência completa e comparação visual página a página em `design.md`)

**B) APROVADO COM RESSALVAS.**

- **Qualidade textual do conteúdo substantivo: excelente.** Comparação visual de cada uma das 4 páginas (imagem renderizada do PDF original a 150 DPI) contra o Markdown produzido não encontrou nenhum texto omitido, inventado ou duplicado no corpo do testamento: nomes próprios, CPFs, RGs, endereços, CEPs, datas, valores monetários, números de matrícula de imóveis, coordenadas/medidas do imóvel, número de protocolo e selos digitais — todos conferidos e corretos. Formatação em negrito/sublinhado reflete fielmente a ênfase visual do documento original. 6 ocorrências de `[ilegível]` foram usadas de forma criteriosa, exatamente onde uma rubrica/assinatura manuscrita sobrepõe o texto impresso ou onde um elemento é puramente gráfico (selo, ícone) — nenhum uso indevido nem excessivo.
- **Defeito técnico sistemático e significativo, presente nas 4/4 páginas:** cada página traz, após o marcador interno `[End OCR]*` do plugin `markitdown-ocr`, um bloco de ~209 linhas de ruído — caracteres isolados, um por linha, que ao serem concatenados e invertidos reconstroem a etiqueta de autenticação e-SAJ (a mesma camada de texto nativo vertical/rotacionado já lida corretamente pelo PyMuPDF nas auditorias anteriores). Isso quase dobra o número de linhas de cada bloco de página (~47–49% de linhas de ruído) e faz com que o conteúdo da etiqueta e-SAJ — que tem valor probatório (protocolo, assinante digital, data/hora) — fique efetivamente perdido como texto legível (nem transcrito corretamente, nem marcado honestamente como `[ilegível]`).
- **Causa raiz isolada e reproduzida:** não está em `src/pipeline_juridico/` — está inteiramente dentro do pacote de terceiros `markitdown-ocr` (`_pdf_converter_with_ocr.py`), que usa `pdfplumber` para agrupar caracteres nativos da página em "linhas" por proximidade de coordenada Y (limiar fixo de 2pt) antes de intercalá-los com o resultado do OCR de imagem por posição vertical. Esse agrupamento por Y quebra cataclismicamente para texto rotacionado (vertical): como cada caractere de uma linha vertical tem uma coordenada Y diferente do caractere anterior (variando bem além do limiar de 2pt), quase todo caractere vira sua própria "linha" de 1 caractere. É a mesma classe de defeito já corrigida em `fix-rotated-digital-signature-noise` (achado C.1) — mas nesta rota (`hibrido`/OCR), diferente daquela (`texto_nativo`), o gatilho não exige duas cópias sobrepostas e duplicadas: **uma única linha rotacionada não duplicada já é suficiente** para produzir o mesmo padrão de fragmentação, porque o mecanismo de proteção existente (`_has_duplicated_rotated_block`, `_geometric_reading_order_text` em `converter.py`) só é aplicado quando `method is Metodo.texto_nativo` — nunca é chamado no ramo `hibrido`/`ocr_integral`, que delega inteiramente ao texto já produzido pelo `markitdown-ocr`.
- **Problema do OCR vs. problema do cleaner:** é inteiramente um problema do motor/plugin de OCR (comportamento de terceiros, fora de `src/pipeline_juridico/`), não do cleaner. `clean_markdown`/`remove_repetitive_margins` não têm como remover esse ruído: cada linha de 1 caractere é tecnicamente única (não é margem verbatim-repetida entre páginas — o `remove_repetitive_margins` já testado não teria como reconhecer "6", "3", "1" como uma margem), e o cleaner nunca foi projetado para reconhecer esse padrão de fragmentação char-por-linha.
- **Achado secundário (severidade baixa):** o marcador de escopo interno do plugin (`[End OCR]*`) vaza para o Markdown final publicado — é um artefato de implementação do `markitdown-ocr`, não conteúdo do documento, e não deveria aparecer na saída.
- **Achado observacional (severidade muito baixa, esperado):** pequena variação não determinística entre páginas na transcrição do mesmo texto estático de rodapé (`"Fundado em 1948"` na pág. 1 vs. `"Fundada em 1948"` na pág. 3, para a mesma faixa lateral verde "União Internacional do Notariado Latino") — consistente com o risco já aceito pela spec de que chamadas a LLM não são estritamente determinísticas.
- **Classificação por página:** 4/4 páginas **APROVADA COM RESSALVAS** (conteúdo jurídico substantivo íntegro e correto; ressalva sistemática e idêntica nas 4 páginas — o ruído de fragmentação pós-`[End OCR]*`). 0 REPROVADA, 0 APROVADA sem ressalvas.
- **Prioridade dos achados:** (1) alta — ruído de fragmentação char-por-linha na rota `hibrido`/OCR (afeta 4/4 páginas, ~47–49% de poluição de linhas, perde a etiqueta e-SAJ como texto legível); (2) baixa — vazamento do marcador `[End OCR]*` para a saída publicada; (3) muito baixa/observacional — variação não determinística de transcrição de texto de rodapé estático entre páginas.
- **Correção futura necessária:** sim, para o achado de prioridade alta — candidato a mudança OpenSpec dedicada (`fix-...`), fora do escopo desta validação. Nenhuma implementação foi feita aqui.

## Capabilities

### New Capabilities
(nenhuma — mudança de validação operacional, não implementa)

### Modified Capabilities
(nenhuma — mudança de validação operacional, não implementa; nenhuma configuração de OCR foi alterada)

## Impact

- Código: nenhum. `src/`, `tests/`, dependências, prompt, modelo, provider, cleaner, roteamento e arquitetura não foram tocados.
- Uma única chamada real de OCR foi feita, aprovada explicitamente pelo usuário via `/goal`, contra 1 documento (4 páginas) — nenhum outro PDF processado, nenhuma chamada adicional para tentar melhorar o texto.
- Novo diretório `openspec/changes/validate-supervised-ocr-testamento-publico/audit_output/{output,logs}/` (esta mudança): saída real da conversão, isolada via `OUTPUT_DIR`/`LOGS_DIR`, nunca escrita em `output/`/`logs/` canônicos.
- Esta mudança permanece ativa (não arquivada) por instrução explícita do usuário.
