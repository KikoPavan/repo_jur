## Contexto

`remove_repetitive_margins` (`src/pipeline_juridico/cleaner.py`) já implementa toda a infraestrutura necessária para remover margens repetitivas por evidência estatística:

1. Calcula, para cada página, os índices da primeira e última linha de conteúdo não vazio (`pages: list[tuple[start, end, first, last]]`).
2. Testa a primeira/última linha de cada página contra `_FIRST_MARGIN_PATTERN`/`_LAST_MARGIN_PATTERN` — regex fixas que só reconhecem data/hora, URL e contador de página (`_REMOVABLE_MARGIN`).
3. Normaliza o trecho casado em um "template" (dígitos substituídos por `#`) e conta, via `Counter`, em quantas páginas cada template ocorre.
4. Só remove o trecho casado quando o template ocorre em pelo menos `minimum_occurrences = (3 * len(pages) + 4) // 5` páginas (60%, arredondado para cima).
5. Quando a linha inteira é a margem, ela é removida; quando a margem é apenas um prefixo/sufixo da linha (margem fundida ao conteúdo), apenas esse trecho é removido, preservando o resto.

Essa infraestrutura já resolve exatamente o problema relatado — **exceto** que o conjunto de candidatos elegíveis está hardcoded aos quatro padrões regex de `_REMOVABLE_MARGIN`. Um cabeçalho institucional textual como "Superior Tribunal de Justiça" não tem formato numérico/URL reconhecível e por isso nunca vira candidato, mesmo repetindo-se em 8 das 12 páginas de `AINTARESP_1462304-PA.pdf` (67%, acima do limiar de 60%).

Verificação de posição no pipeline: `recompose_native_paragraphs` roda por página, durante a composição (`converter.py`, chamada por página antes da montagem do documento completo), **antes** de `remove_repetitive_margins`, que roda uma única vez sobre o Markdown já composto (`converter.py`, linha ~310, depois de todas as páginas serem concatenadas). Isso confirma que o defeito não está em `recompose_native_paragraphs` (que só decide se duas linhas dentro da mesma página se unem geometricamente, sem noção de repetição entre páginas) nem antes dele (a extração de blocos por página está correta) — está inteiramente em `remove_repetitive_margins` não reconhecer esse tipo de margem, o que faz o cabeçalho permanecer como texto comum e ser fundido pela junção geométrica de `recompose_native_paragraphs` quando a página 5 (onde o cabeçalho de topo fica geometricamente próximo da continuação do item 6) é processada.

Ocorrências equivalentes confirmadas por inspeção de todas as primeiras/últimas linhas de conteúdo dos 4 PDFs do corpus (script ad hoc, não parte da suíte):

| Arquivo | Texto repetido | Posição | Ocorrências | Páginas | Limiar (60%) | Ação |
| --- | --- | --- | --- | --- | --- | --- |
| `AINTARESP_1462304-PA.pdf` | "Superior Tribunal de Justiça" | topo | 8 (5 isoladas + 3 fundidas) | 12 | 8 | Remover (caso relatado) |
| `AINTARESP_1462304-PA.pdf` | "Documento eletrônico VDA26866008 assinado..." | rodapé | 7 (todas isoladas) | 12 | 8 | Abaixo do limiar — preservado |
| `Inf0024E.pdf` | "Informativo de Jurisprudência n. 24 - Edição Extraordinária 28 de janeiro de 2025" | topo | 28 (todas isoladas) | 29 | 18 | Remover |
| `Inf0024E.pdf` | "ÁUDIO DO TEXTO" | rodapé | 9 (todas isoladas) | 29 | 18 | Abaixo do limiar — preservado |
| `REsp_1704551-SP.pdf` | "RECURSO ESPECIAL Nº 1.704.551 - SP (2017/0091244-2)" | topo | 4 (todas isoladas) | 14 | 9 | Abaixo do limiar — preservado |
| `REsp_1704551-SP.pdf` | "CERTIDÃO DE JULGAMENTO" | topo | 2 (todas isoladas) | 14 | 9 | Abaixo do limiar — preservado |
| `REsp_1704551-SP.pdf` | "Documento: 1807307 - Inteiro Teor do Acórdão..." | rodapé | 12 (todas isoladas) | 14 | 9 | Remover |
| `L10.406_CC_2002.pdf` | (nenhum candidato repetido) | — | — | 186 | — | Sem alteração |

## Decisão

Adicionar, dentro de `remove_repetitive_margins`, uma segunda etapa de detecção (além da já existente por regex numérica), operando sobre o resultado já processado pela primeira etapa:

1. Para a posição de topo (primeira linha de conteúdo de cada página) e, simetricamente, para a de rodapé (última linha), agrupar as páginas por texto **byte-idêntico** dessa linha.
2. Um texto candidato só é elegível se aparecer **sozinho** (like a linha de conteúdo inteira, sem nada mais) em pelo menos **duas** páginas diferentes — essa é a evidência de que se trata de uma unidade autônoma repetida (cabeçalho/rodapé), não uma coincidência isolada.
3. A frequência total do candidato (ocorrências isoladas + ocorrências em que a linha começa exatamente com `"<candidato> "` seguido de outro conteúdo) deve atingir o mesmo `minimum_occurrences` (60%) já usado pelos quatro padrões existentes.
4. Candidatos são avaliados do mais longo para o mais curto, e uma página já resolvida por um candidato mais longo não é reavaliada por um candidato mais curto (evita conflitos entre candidatos que sejam prefixo um do outro).
5. Quando o candidato satisfaz os critérios: nas páginas onde aparece isolado, a linha inteira é removida (mesmo comportamento das margens existentes); nas páginas onde aparece fundido como prefixo, apenas o prefixo do candidato (mais o espaço separador) é removido, preservando o restante da linha.

Isso reutiliza inteiramente a evidência de repetição e posição já disponível (não introduz nenhum sinal novo como caixa alta, comprimento de texto ou lista de nomes de tribunais) e opera com o mesmo limiar estatístico de 60% já validado pelas quatro categorias existentes — apenas generaliza o conjunto de candidatos elegíveis de "correspondem a um dos quatro formatos fixos" para "são um texto verbatim comprovadamente repetido, na mesma posição, através de uma fração alta das páginas, com pelo menos duas ocorrências isoladas confirmando seus limites exatos".

## Alternativas consideradas

- **Adicionar "Superior Tribunal de Justiça" como um quinto padrão fixo em `_REMOVABLE_MARGIN`**: rejeitada — viola diretamente a regra de não criar regra específica a este processo/tribunal/frase, e não generaliza para os outros dois casos equivalentes já identificados no corpus (`Inf0024E.pdf`, `REsp_1704551-SP.pdf`), que têm textos de cabeçalho/rodapé completamente diferentes.
- **Detectar apenas por caixa alta ou por linha curta no topo da página**: rejeitada explicitamente pela regra 10 do objetivo — texto legítimo (ementas, títulos de seção) também pode ser curto ou estar em maiúsculas; caixa alta/comprimento sozinhos não distinguem cabeçalho repetido de conteúdo jurídico legítimo.
- **Mover a remoção de margens para antes de `recompose_native_paragraphs`**: rejeitada — exigiria reestruturar a ordem do pipeline (proibido pelas regras: "não alterar... ordem de leitura ou arquitetura") e não é necessário, já que a estratégia de remover o prefixo já fundido (igual ao que já é feito para data/URL) resolve o problema sem mudar a ordem das etapas.
- **Exigir apenas 1 ocorrência isolada (em vez de 2) para estabelecer o candidato**: rejeitada por segurança — um único "acidente" de duas páginas terem a mesma linha de conteúdo completa por coincidência é mais fácil de ocorrer do que duas páginas distintas coincidirem; exigir 2 ocorrências isoladas reduz esse risco sem enfraquecer a detecção real (o caso relatado tem 5 ocorrências isoladas, muito acima do mínimo).

## Riscos

- Falso positivo: um trecho de conteúdo jurídico genuinamente idêntico entre páginas (ex. uma frase padrão repetida por coincidência) poderia ser removido se atingir o limiar de 60% E aparecer isolado em 2+ páginas. Mitigado pela mesma proteção já existente para os quatro padrões atuais — a detecção exige alta frequência estatística (60%+ das páginas do documento), o que é extremamente improvável para conteúdo jurídico de prosa comum, e a posição (linha inicial/final de bloco de página) exclui menções em meio a parágrafos.
- Falso negativo: cabeçalhos/rodapés que nunca aparecem isolados (sempre fundidos) não têm como ter seus limites exatos determinados por este mecanismo. Fora do escopo desta correção pontual — o objetivo cobre o padrão observado no corpus real, não uma cobertura exaustiva de todo formato possível de cabeçalho.
