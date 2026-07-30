## Contexto

`recompose_native_paragraphs` decide se une a linha atual (`current_text`) ao parágrafo anterior (`previous_text`) com base em uma série de padrões de exceção (`should_join` em `src/pipeline_juridico/cleaner.py`). Nenhuma dessas exceções considera o conteúdo semântico de fechamento de uma citação jurisprudencial (turma/seção julgadora + data de publicação no `DJe`), nem o início de uma nova ementa em caixa alta. Como resultado, quando o layout do PDF deixa um espaçamento vertical pequeno (`gap <= previous_height * 1.2`) entre o fim de um precedente e o início do próximo, os dois são fundidos.

Verificação no corpus de regressão (`input/L10.406_CC_2002.pdf`, `input/AINTARESP_1462304-PA.pdf`, `input/REsp_1704551-SP.pdf`, `input/Inf0024E.pdf`, reconvertidos com `--no-ocr`): a combinação exata "linha termina em citação de julgamento/DJe" seguida por "linha seguinte inteiramente em caixa alta" ocorre uma única vez nos 4 PDFs, no caso relatado (`AINTARESP_1462304-PA.md`, entre "... julgado em 08/11/2018, DJe 26/11/2018) (Grifos acrescidos)." e "RECURSO ESPECIAL. INDENIZAÇÃO POR DANO MORAL...").

## Decisão

Adicionar duas expressões regulares e uma condição adicional em `should_join`:

1. `jurisprudence_closing_pattern`: reconhece o fim de uma referência jurisprudencial de fechamento — uma citação parentética contendo `DJe dd/mm/aaaa)` e/ou referência a turma/seção/órgão julgador (ex. "TURMA", "SEÇÃO", "CORTE ESPECIAL"), opcionalmente seguida de uma anotação como "(Grifos acrescidos)." — ancorada ao final de `previous_text`.
2. Reaproveitar `current_text.isupper()` (já usado em outro ponto da função) como sinal de que o bloco seguinte é uma nova linha inteiramente em caixa alta — assinatura comum de início de ementa/precedente nesses documentos.
3. Bloquear a junção quando ambas as condições forem verdadeiras: `jurisprudence_closing_pattern.search(previous_text) and current_text.isupper()`.

Esta é a menor generalização possível: não depende do número do processo, do nome das partes ou de qualquer identificador específico ao caso relatado — apenas do padrão estrutural (fechamento de citação + novo bloco em caixa alta), que é a mesma classe de problema descrita no objetivo.

## Alternativas consideradas

- **Bloquear junção sempre que `previous_text` contiver "DJe"**: rejeitada — "DJe" pode aparecer no meio de uma frase que legitimamente continua (ex. citação intercalada em prosa), e o requisito pede a condição *combinada* (fechamento de referência + novo bloco em caixa alta), não qualquer menção a "DJe" isoladamente.
- **Bloquear junção sempre que `current_text` for caixa alta**: rejeitada — já existe uso legítimo de linhas em caixa alta unidas ao parágrafo anterior em outros contextos (ex. nomes de signatários), e o teste `test_recompose_native_paragraphs_separates_federal_law_closing` depende de comportamento específico para isso; a condição precisa ser combinada com o fechamento jurisprudencial para não reintroduzir regressão.
- **Detectar apenas a string literal "(Grifos acrescidos)."**: rejeitada — não generaliza para variações razoáveis do mesmo padrão (ex. ausência da anotação de grifos, outras turmas/seções), e o objetivo pede proteção contra a classe do problema, não a string exata do caso relatado.

## Riscos

- Falso positivo: um bloco legitimamente contínuo que termine, por coincidência, em uma citação com "DJe"/turma e seja seguido por uma linha em caixa alta que não seja início de ementa. Mitigação: escopo restrito às 4 exceções de R01 (não tocadas) e verificação de que a reconversão do corpus completo não introduz nenhuma separação indevida adicional.
- Falso negativo: variações de citação jurisprudencial fora do padrão coberto (ex. sem "DJe", apenas "julgado em"). Fora do escopo desta correção pontual — o objetivo cobre especificamente o caso reproduzível e a proteção esperada descrita, não uma cobertura exaustiva de todos os formatos de citação.
