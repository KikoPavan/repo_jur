## Why

Após a correção do defeito R01 (`improve-markdown-cleanup-structuring`), a suíte de regressão do corpus fixo não cobria o caso de dois precedentes jurisprudenciais consecutivos no mesmo bloco de página. Em `input/AINTARESP_1462304-PA.pdf`, um precedente encerrado por citação de julgamento ("... julgado em 08/11/2018, DJe 26/11/2018) (Grifos acrescidos).") está sendo indevidamente unido, pela recomposição geométrica de parágrafos, ao início do precedente seguinte ("RECURSO ESPECIAL. INDENIZAÇÃO POR DANO MORAL. ..."), produzindo no Markdown final um único parágrafo fundido: "(Grifos acrescidos). RECURSO ESPECIAL. INDENIZAÇÃO...". Isso é uma fusão indevida de conteúdo jurídico distinto (dois precedentes diferentes), não coberta pelas exceções de não-junção existentes (`current_line_pattern`, `formal_structure_pattern`, marcador de página), porque nenhuma delas reconhece o fim de uma referência jurisprudencial nem o início de uma nova ementa em caixa alta.

## What Changes

- Adicionar, em `recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`), uma exceção adicional e mínima de não-junção: quando o bloco anterior terminar em referência jurisprudencial de fechamento (citação com turma/seção/órgão julgador e data de `DJe`, opcionalmente seguida de anotação como "(Grifos acrescidos).") e o bloco seguinte for uma linha inteiramente em caixa alta (assinatura típica de início de ementa/precedente), os dois blocos NÃO são unidos.
- Não alterar nenhuma das exceções já corrigidas em R01 (Art. 44 §2º, Art. 593, Art. 1.458, Art. 1.368-F) nem a lógica de `formal_structure_pattern`/`bare_structure_pattern`/`qualified_structure_pattern`.
- Não alterar extrator (`inspector.py`), roteamento (`router.py`), engines/OCR (`engines.py`) ou arquitetura geral do pipeline.

## Capabilities

### New Capabilities
(nenhuma — correção pontual da capacidade existente)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Recomposição geométrica de parágrafos" passa a listar explicitamente, entre as condições que bloqueiam a junção de blocos, o fim de uma referência jurisprudencial de fechamento seguido de um novo bloco em caixa alta com características de ementa/início de precedente.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (apenas a função `recompose_native_paragraphs`), sem tocar em `inspector.py`, `router.py`, `engines.py`, `converter.py` ou dependências.
- Testes: novo teste de regressão em `tests/test_cleaner.py` reproduzindo o caso exato relatado, mais verificação de que os 4 casos positivos do R01 continuam passando.
- Corpus: reconversão dos 4 PDFs fixos com `converter-juridico --no-ocr` para confirmar ausência de regressão e a separação correta dos dois precedentes em `AINTARESP_1462304-PA.pdf`.
- Fora de escopo: qualquer regra específica ao nome ou número deste processo; OCR real; arquivamento da mudança sem aprovação humana explícita.
