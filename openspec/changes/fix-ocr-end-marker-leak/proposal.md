## Why

`validate-supervised-ocr-testamento-publico` (arquivada, 2026-08-12) e `fix-ocr-rotated-text-fragmentation` (arquivada, 2026-08-14) registraram, como achado secundário de baixa prioridade, o vazamento do marcador interno `[End OCR]*` do plugin de terceiros `markitdown-ocr` para o Markdown final publicado nas 4 páginas `hibrido` de `input/processos_auditoria/012-015-Testamento Publico.pdf`. Ambas as mudanças recomendaram tratar esse achado separadamente, em mudança própria — este `/goal` abre essa mudança, **exclusivamente diagnóstica**: rastreia a origem e o fluxo completo do marcador, verifica a interação com a correção geométrica já arquivada, e avalia formalmente os pontos de intervenção candidatos, sem implementar nada.

Não implementa código, não cria testes de produção, não executa OCR/LLM novo, não altera modelo/provider/prompt, não arquiva e não faz push.

## Caso investigado

`input/processos_auditoria/012-015-Testamento Publico.pdf` (4 páginas, único caso `hibrido`/`ocr_integral` de todo o corpus de controle de 270 páginas / 8 PDFs, reconfirmado nesta investigação por reexecução independente do roteamento). Evidência reaproveitada: Markdown real já produzido e arquivado em `validate-supervised-ocr-testamento-publico/audit_output/output/012-015-Testamento Publico.md`, e a implementação/testes já arquivados de `fix-ocr-rotated-text-fragmentation`. Nenhuma chamada real de OCR/LLM foi feita nesta investigação.

## Conclusão (resumo — evidência completa em `design.md`)

**A) CRITÉRIO SEGURO ENCONTRADO.**

- **Origem:** `markitdown_ocr/_pdf_converter_with_ocr.py` (pacote de terceiros instalado), três pontos de emissão (linhas 275, 374, 407), sempre a f-string literal `...[End OCR]*` fechando o bloco `*[Image OCR]\n{texto}\n[End OCR]*` — artefato de formatação do plugin, nunca conteúdo do documento. No corpus atual, só a linha 275 é exercitada (rota `hibrido`, 1 imagem por página; nenhuma página `ocr_integral` existe).
- **Único consumidor real dentro deste pipeline:** `converter.py::_split_ocr_tail` (via `_replace_fragmented_vertical_residual_in_text`/`_replace_fragmented_vertical_residuals_in_document`), parte da correção já arquivada `fix-ocr-rotated-text-fragmentation` — usa `rfind` para localizar a última ocorrência do marcador como ponto de corte da reconstrução geométrica do resíduo vertical.
- **Achado colateral relevante:** o cabeçalho `## Page N` e o marcador de abertura `*[Image OCR]` — também emitidos pelo plugin — **já não aparecem** no Markdown final hoje, mas não por design: são removidos como efeito colateral do mecanismo genérico e já existente `remove_repetitive_margins` (`cleaner.py`, de `fix-repeated-header-cross-page-fusion`), porque `isolated_page_workspace` faz cada página ser processada como PDF isolado — o contador interno do plugin sempre reinicia em `page_num=1`, tornando `## Page 1`/`*[Image OCR]` byte-idênticos e posicionados como primeira linha em 100% das páginas do Testamento (acima do limiar de 60% do mecanismo). `[End OCR]*` escapa dessa supressão porque, quando existe qualquer resíduo depois dele (o próprio ruído de fragmentação, ou — pós-correção — a reconstrução geométrica), ele deixa de ser a primeira **ou** última linha de conteúdo da página, e `remove_repetitive_margins` só examina essas duas posições. Confirmado por reprodução local: em um cenário sintético sem resíduo após o marcador, ele também seria removido pelo mesmo mecanismo. Existe hoje um teste (`tests/test_cleaner.py::test_clean_markdown_preserves_ocr_delimiters`) que fixa a preservação atual do marcador quando `clean_markdown` é chamada isoladamente.
- **Ponto de não-retorno:** a chamada a `_replace_fragmented_vertical_residuals_in_document` em `convert_document` (linha ~615-619) — qualquer remoção do marcador **antes** desse ponto quebra silenciosamente `fix-ocr-rotated-text-fragmentation` (confirmado por reprodução local: sem o marcador, `_split_ocr_tail` retorna `None` e a substituição geométrica nunca dispara).
- **Ponto mínimo e seguro recomendado (Candidato A):** nova função em `converter.py`, chamada em `convert_document` imediatamente **depois** de `_replace_fragmented_vertical_residuals_in_document` e antes de `join_symbol_across_page_break`, removendo todas as ocorrências literais de `[End OCR]*` restritas às páginas `hibrido`/`ocr_integral` (reaproveitando a mesma segmentação por `[[Pág. N]]` já usada pela função vizinha). Não toca `cleaner.py`; não entra em conflito com o teste existente de preservação (que testa `clean_markdown` isoladamente, não alterada).
- **Candidato B (remover no fim da composição por página, antes de `compose_document`) foi avaliado e rejeitado**: quebra a correção já arquivada `fix-ocr-rotated-text-fragmentation`, confirmado por reprodução local.
- **Candidato C (pós-processar o documento final, após `clean_markdown`) é tecnicamente seguro quanto à ordem, mas estritamente inferior ao A**: deixa o marcador sobreviver por mais etapas do pipeline sem necessidade, e — se implementado dentro de `clean_markdown` em vez de uma função separada — colidiria com o teste existente de preservação.
- **Blast radius:** confinado às 4 páginas `hibrido` de `012-015-Testamento Publico.pdf` (roteamento reexecutado nesta investigação, independente: 266 `texto_nativo` + 4 `hibrido` + 0 `ocr_integral` em 270 páginas / 8 PDFs); 0 páginas `texto_nativo` tocadas, por construção; marcadores `[[Pág. N]]`, conteúdo OCR substantivo e o resíduo vertical já reconstruído permanecem intactos em todos os candidatos avaliados.

## Fora do escopo desta investigação

Nova chamada OCR; qualidade de OCR; prompt/modelo/provider; ruído vertical já corrigido (`fix-ocr-rotated-text-fragmentation`); marcador de abertura `*[Image OCR]`; Papel/Nome; YAML/segmentação; qualquer outra limpeza. Nenhuma implementação foi feita nesta fase de diagnóstico — a proposta futura descrita em `design.md`, "CONCLUSÃO", exigiu nova aprovação humana explícita para avançar à TDD/implementação, seguindo o mesmo padrão já usado em `fix-ocr-rotated-text-fragmentation`. Ver seção "Implementação" abaixo para o relato completo dessa fase, autorizada em 2026-08-14.

## Implementação

Autorizada por `/goal` explícito em 2026-08-14, confirmando o Candidato A (ponto de intervenção, escopo e restrições) exatamente como recomendado no diagnóstico. Codex implementou (testes + código); Claude (orquestrador) revisou o diff, executou os testes e validou o OpenSpec.

**Helper criado** em `src/pipeline_juridico/converter.py`:

```python
def _strip_internal_ocr_markers(
    markdown: str,
    blocks: list[PageBlock],
    marker: str = "[End OCR]*",
) -> str:
```

Reaproveita `_PAGE_MARKER_SPLIT_PATTERN`/`_PAGE_MARKER_NUMBER_PATTERN` (mesma segmentação por `[[Pág. N]]` já usada por `_replace_fragmented_vertical_residuals_in_document`) e a mesma lista de elegibilidade (`method in (Metodo.hibrido, Metodo.ocr_integral)`). Para cada segmento de página elegível, remove **todas** as ocorrências literais do marcador (`segment.replace(marker, "")`) — não apenas a última; páginas não elegíveis são retornadas inalteradas.

**Ponto de integração** em `convert_document`, exatamente como aprovado:

```python
    raw_markdown = _replace_fragmented_vertical_residuals_in_document(
        raw_markdown, blocks, vertical_geometry_by_page,
    )
    raw_markdown = _strip_internal_ocr_markers(raw_markdown, blocks)
    raw_markdown = join_symbol_across_page_break(raw_markdown)
```

**Testes:** 6 testes novos em `tests/test_converter.py` (positivos: remoção de múltiplas ocorrências do marcador preservando texto substantivo anterior, resíduo reconstruído posterior e `[[Pág. N]]`; negativos: páginas `texto_nativo`/`vazia`/`erro` inalteradas mesmo com o marcador real presente, texto literal semelhante mas sem o asterisco de fechamento preservado, ausência do marcador é no-op). O teste de integração existente `test_convert_document_replaces_fragmented_vertical_residual_on_hybrid_pages` (de `fix-ocr-rotated-text-fragmentation`) foi estendido com `assert markdown.count(OCR_END_MARKER) == 0`, cobrindo a não-regressão daquela correção com o novo passo presente. `uv run pytest tests/test_converter.py -v`: RED inicial 42/49 (7 falhas esperadas por `AttributeError`); após implementação, **49/49**. `uv run pytest tests/`: **391/391** (385 baseline + 6 novos).

**Validação com dados 100% reais do Testamento** (texto substantivo por página do Markdown já auditado + resíduo fragmentado reproduzido localmente via pdfplumber sobre o PDF real, OCR mockado — nenhuma chamada real): 4/4 páginas `hibrido`, `status: sucesso`; `[End OCR]*` = **0** (baseline: 4); `[[Pág. N]]` = 4; texto substantivo presente byte a byte em cada página; resíduo vertical reconstruído (protocolo, URL, assinante digital do carimbo e-SAJ) presente e intacto imediatamente após o texto substantivo, sem o marcador entre eles. Idempotência confirmada (segunda execução do mesmo dry run produziu Markdown byte-idêntico). Regressão dos 4 PDFs canônicos com `--no-ocr`: byte-idênticos aos já commitados em `output/`. Regressão dos 3 PDFs restantes de `processos_auditoria/` com `--no-ocr`: sucesso, zero OCR; `100-106-DECISÃO.md` manteve 94 linhas / 0 linhas de 1 caractere (`fix-rotated-digital-signature-noise` intacta). Testamento sob `--no-ocr` continua corretamente bloqueado (`exit=3`).

**Delta spec** adicionado a `openspec/specs/juridical-pdf-conversion/spec.md` (requisito "Não vazamento de marcadores internos do mecanismo de OCR para o Markdown final"). `openspec validate fix-ocr-end-marker-leak --strict`: válida. `openspec validate --all --strict`: **2 passed, 0 failed**.

**Blast radius real:** confinado às 4 páginas `hibrido` de `012-015-Testamento Publico.pdf`; as 266 páginas `texto_nativo` do corpus permanecem sem alteração. `cleaner.py`, `router.py`, `engines.py`, prompt, modelo, provider e dependências não foram tocados. Nenhuma chamada real de OCR/LLM foi feita em nenhuma etapa.
