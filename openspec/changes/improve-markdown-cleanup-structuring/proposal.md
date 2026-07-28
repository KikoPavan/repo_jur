## Why

A limpeza atual (`clean_markdown`) é deliberadamente mínima: normaliza fim de linha, remove espaços finais e reduz linhas vazias, mas não recompõe parágrafos quebrados pela extração PDF→Markdown, não remove cabeçalhos/rodapés técnicos repetitivos, não normaliza símbolos jurídicos corrompidos pela extração (ex. "Art. 1 o") e não reconhece a hierarquia legislativa (PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO) nem separa o índice final. Isso deixa o Markdown produzido fragmentado e difícil de consumir por pipelines downstream (busca, RAG, leitura jurídica), mesmo quando o conteúdo está tecnicamente correto. A extração já expõe dados geométricos por bloco (PyMuPDF `get_text("blocks")`, usados hoje apenas como salvaguarda de ordem de leitura em `converter.py`), o que permite recompor parágrafos e detectar cabeçalhos/rodapés de forma determinística, sem LLM em runtime.

## What Changes

- Recompor parágrafos jurídicos fragmentados usando geometria de bloco/linha do PDF (distância vertical, alinhamento, continuidade textual), com listas de exceção explícitas para Artigo/§/inciso/alínea/item, títulos estruturais (PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO), marcador de página e novos blocos estruturais.
- Detectar e remover cabeçalhos/rodapés repetitivos (data/hora de impressão, nome técnico do arquivo, URL repetida, contador "N/186") por repetição entre páginas + posição geométrica semelhante, preservando `[[Pág. N]]` e qualquer conteúdo jurídico que apenas se repita por coincidência.
- Normalizar contextualmente símbolos jurídicos corrompidos pela extração ("Art. 1 o" → "Art. 1º", "§ 1 o" → "§ 1º", "Lei n o" → "Lei nº" e ordinais equivalentes inequívocos), sem tocar em números, datas, valores ou referências legais fora desses padrões.
- Reconhecer estrutura legislativa formal (PARTE/LIVRO/TÍTULO/CAPÍTULO/SEÇÃO/SUBSEÇÃO seguidos do título imediato) e emitir cabeçalhos Markdown `#` a `######` correspondentes, sem promover texto maiúsculo comum a título.
- Identificar o índice posterior ao encerramento do corpo normativo e separá-lo sob um cabeçalho `# ÍNDICE`, preservando integralmente seu conteúdo.
- **BREAKING** (spec-level, não runtime): relaxa a restrição atual do requisito "Limpeza conservadora", que hoje proíbe reorganizar conteúdo; a nova versão autoriza especificamente essas cinco transformações determinísticas e mantém a proibição para qualquer outra forma de reescrita/resumo/interpretação.

## Capabilities

### New Capabilities
(nenhuma — o trabalho estende a capacidade existente de conversão)

### Modified Capabilities
- `juridical-pdf-conversion`: o requisito "Limpeza conservadora" passa a autorizar recomposição de parágrafos, remoção de cabeçalhos/rodapés repetitivos, normalização contextual de símbolos jurídicos e reconhecimento de estrutura legislativa/índice, todos determinísticos e sem uso de LLM em runtime, mantendo a proibição de resumir, corrigir sentido, deduplicar por interpretação ou reescrever conteúdo jurídico.

## Impact

- Código: `src/pipeline_juridico/cleaner.py` (lógica principal) e, se necessário, um novo módulo estritamente de suporte (ex. `src/pipeline_juridico/structure.py`) para regras de estrutura/parágrafo — sem alterar `router.py`, `engines.py`, `inspector.py` ou a salvaguarda de ordem de leitura em `converter.py`.
- Dados de entrada para a limpeza: pode ser necessário passar informação geométrica de bloco (já calculada em `converter.py`) até a etapa de composição/limpeza, em vez de operar apenas sobre a string Markdown final — a ser detalhado em `design.md`.
- Testes: novos testes de regressão em `tests/test_cleaner.py` (ou arquivo dedicado) cobrindo cada uma das 5 regras, mais reconversão do corpus fixo (`input/L10.406_CC_2002.pdf`, `input/AINTARESP_1462304-PA.pdf`, `input/REsp_1704551-SP.pdf`, `input/Inf0024E.pdf`) para checagem de regressão.
- Dependências: nenhuma nova dependência; sem LLM em runtime.
- Fora de escopo: OCR, roteamento de página, engines de conversão, arquitetura geral do pipeline, Open Knowledge Format/YAML front matter.
