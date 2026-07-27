# Relatório do loop de melhoria da conversão — 2026-07-27

## 1. Linha de base

- Comando de conversão: `uv run converter-juridico <pdf>` →
  `pipeline_juridico.converter.convert_document`.
- Suíte de testes inicial: `uv run pytest tests/ -q` → **185 passed**.
- Corpus fixo de regressão (real, `input/`):

  | Arquivo | Páginas | Características |
  | --- | --- | --- |
  | `AINTARESP_1462304-PA.pdf` | 12 | acórdão STJ, texto nativo, blocos rótulo/valor, ementa centralizada |
  | `REsp_1704551-SP.pdf` | 14 | acórdão STJ, texto nativo, mesmo padrão rótulo/valor |
  | `Inf0024E.pdf` | 29 | informativo de jurisprudência, 1 página híbrida (logo + ícones decorativos), 28 nativas |

- Defeitos na linha de base: 19 + 32 linhas de tabela Markdown fabricadas
  (AINTARESP + REsp), inversão de ordem de leitura em blocos rótulo/valor
  (AINTARESP), e uma página roteada incorretamente para OCR por causa de
  ícones decorativos, com transcrição de OCR inserida no meio de uma frase
  nativa (Inf0024E).

## 2. Defeitos corrigidos, por ordem de prioridade

| # | Prioridade no `/goal` | Defeito | PDF/página | Status |
| --- | --- | --- | --- | --- |
| 1 | 4 — inversão de frases/colunas | Blocos rótulo/valor e ementa reordenados pelo motor nativo | AINTARESP p.1, p.4 | ACEITO |
| 2 | 6 — tabelas falsas | Tabelas Markdown fabricadas (coluna única ou linha única, sem inversão) | REsp p.1, p.6 | ACEITO |
| 3 | 5 — OCR usado sem necessidade / inserido em frase nativa | Página roteada a `hibrido` por ícones decorativos; OCR interrompendo frase nativa | Inf0024E p.1 | ACEITO |

Nenhum defeito de prioridade 1, 2 ou 3 (perda de conteúdo, páginas
vazias/ausentes, alteração de números/datas/valores/símbolos) foi
encontrado no corpus atual.

## 3. Testes adicionados

- `tests/test_converter_integration.py::test_convert_document_preserves_native_label_value_reading_order`
- `tests/test_converter_integration.py::test_convert_document_replaces_fabricated_native_tables`
- `tests/test_router.py::test_route_page_abundant_multiblock_text_with_small_images_stays_native`
- `tests/test_converter_integration.py::test_convert_inf0024e_first_page_uses_clean_native_output`

Todos os quatro foram confirmados como falhando antes da respectiva
correção (verificado de forma independente pelo orquestrador via
`git stash` da mudança de produção, não apenas relatado pelo
implementador).

## 4. Arquivos alterados

- `src/pipeline_juridico/converter.py` — salvaguardas de ordem de leitura e
  tabela fabricada para páginas `texto_nativo` (iterações 1 e 2).
- `src/pipeline_juridico/router.py` — guarda de roteamento para não
  promover a `hibrido` páginas com texto nativo claramente suficiente
  quando o sinal de imagem vem só de imagens pequenas somadas (iteração 3).
- `tests/test_converter_integration.py`, `tests/test_router.py` — testes
  de regressão correspondentes.
- `src/pipeline_juridico/config.py`, `src/pipeline_juridico/engines.py`:
  **não alterados** em nenhuma iteração.

## 5. Comparação objetiva antes/depois

| Métrica | Antes | Depois |
| --- | --- | --- |
| Linhas de tabela Markdown fabricadas (AINTARESP) | 19 | 0 |
| Linhas de tabela Markdown fabricadas (REsp) | 32 | 0 |
| Método da página 1 de Inf0024E | `hibrido` | `texto_nativo` |
| Blocos `[Image OCR]` na página 1 de Inf0024E | 3 | 0 |
| Marcadores `[[Pág. N]]` sequenciais | 12/12, 14/14, 29/29 | inalterado |
| Caractere de substituição `�` | 0 | 0 |
| Números de processo, datas, símbolos (§, º, ª) | preservados | preservados (idênticos) |
| Testes automatizados | 185 passed | 189 passed |
| Regressões em fixtures existentes (inclusive híbrido genuíno) | — | nenhuma |

## 6. Casos bloqueados ou esgotados

Nenhum. O único ponto que exigiu decisão humana (iteração 3 — como corrigir
o uso incorreto de OCR sem mexer na composição do caminho híbrido nem nos
limiares globais) foi resolvido com escopo explicitamente definido pelo
usuário antes da implementação.

## 7. Candidatos não perseguidos nesta rodada (fora do escopo objetivo)

- Espaçamento duplo entre palavras em texto justificado (ex.: "Ausência  de
  inércia") — presente em várias páginas nativas; não altera o conteúdo
  jurídico nem a ordem de leitura, portanto não atende ao critério de
  "defeito reproduzível com resultado esperado objetivamente definível"
  sem uma referência de formatação — evitar como melhoria subjetiva de
  aparência, conforme vedado no `/goal`.
- Cabeçalhos/rodapés repetitivos em `Inf0024E.pdf` ("Informativo de
  Jurisprudência n. 24...", numeração "N/29") — ruído de baixa prioridade
  (9), sem impacto em conteúdo jurídico; não perseguido nesta rodada.

## 8. Comandos exatos para reproduzir a validação

```bash
uv run pytest tests/ -q

uv run converter-juridico input/AINTARESP_1462304-PA.pdf --overwrite --no-ocr
uv run converter-juridico input/REsp_1704551-SP.pdf --overwrite --no-ocr
uv run converter-juridico input/Inf0024E.pdf --overwrite --no-ocr --allow-partial

grep -c "^|" output/AINTARESP_1462304-PA.md      # esperado: 0
grep -c "^|" output/REsp_1704551-SP.md           # esperado: 0
grep -n "método" output/Inf0024E.md | head -1    # esperado: texto_nativo
grep -c "\[Image OCR\]" output/Inf0024E.md        # esperado: 0 na página 1
grep -c "^\[\[Pág\." output/AINTARESP_1462304-PA.md  # esperado: 12
grep -c "^\[\[Pág\." output/REsp_1704551-SP.md       # esperado: 14
grep -c "^\[\[Pág\." output/Inf0024E.md              # esperado: 29
```

**Nota:** `--no-ocr --allow-partial` é usado propositalmente na
reconversão de `Inf0024E.pdf` para garantir que nenhuma chamada real de OCR
seja disparada durante a validação — a página que legitimamente ainda
possa precisar de OCR (se houver, em páginas 2-29) ficará marcada como
`[[TEXTO ILEGÍVEL]]` em vez de acionar a API do Gemini. Nenhuma das 29
páginas de `Inf0024E.pdf` precisou de OCR real além da já registrada
anteriormente (fora do escopo desta reconversão de validação).

## 9. Commits gerados (locais, sem push)

1. `48c7196` — fix: preserve reading order in native label/value legal blocks
2. `31986c6` — fix: strip fabricated native tables with no real tabular structure
3. `0aaabdf` — fix: don't route decorative-image pages to hybrid OCR
