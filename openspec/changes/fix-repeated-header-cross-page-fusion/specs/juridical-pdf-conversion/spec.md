## MODIFIED Requirements

### Requirement: Remoção de cabeçalhos e rodapés repetitivos

O sistema SHALL remover, de cada bloco de página, apenas linhas marginais comprovadamente repetitivas entre páginas e com posição semelhante (topo ou rodapé do bloco), limitadas a: data e hora de impressão; nome técnico do arquivo de origem; URL repetida; contador de página no formato "N/total"; e texto de cabeçalho ou rodapé repetido verbatim (byte-idêntico), confirmado por aparecer isolado como linha de conteúdo completa em pelo menos duas páginas e por atingir, em frequência total, o mesmo limiar estatístico usado para os demais padrões. O sistema SHALL remover apenas o trecho correspondente ao cabeçalho/rodapé repetido quando este estiver fundido ao início do conteúdo textual real da página seguinte, preservando integralmente esse conteúdo. O sistema SHALL preservar o marcador `[[Pág. N]]` em todas as páginas e SHALL NOT remover conteúdo jurídico apenas por ele se repetir entre páginas.

#### Scenario: Rodapé técnico é removido

- **WHEN** uma linha contendo data/hora de impressão, nome de arquivo técnico, URL ou contador "N/186" aparece de forma repetida na mesma posição (topo ou rodapé) em uma fração alta das páginas
- **THEN** essa linha é removida do bloco de cada página em que aparece
- **AND** o marcador `[[Pág. N]]` correspondente permanece intacto

#### Scenario: Cabeçalho repetido fundido à continuação da página seguinte é separado

- **WHEN** um cabeçalho institucional (ex. "Superior Tribunal de Justiça") aparece isolado, como linha de conteúdo completa, em pelo menos duas páginas, e em outra página aparece fundido ao início do conteúdo textual real que continua um dispositivo iniciado na página anterior (ex. "Superior Tribunal de Justiça agravada, pois demonstrado o rebate do fundamento...")
- **THEN** o cabeçalho é removido e o conteúdo textual real permanece, iniciando corretamente pela continuação (ex. "agravada, pois demonstrado o rebate do fundamento...")

#### Scenario: Cabeçalho ou rodapé abaixo do limiar de frequência é preservado

- **WHEN** uma linha repetida na posição de topo ou rodapé do bloco não atinge o limiar estatístico de frequência já usado para as demais margens, ou nunca aparece isolada como linha de conteúdo completa em pelo menos duas páginas
- **THEN** essa linha permanece inalterada em todas as páginas em que aparece

#### Scenario: Conteúdo jurídico repetido é preservado

- **WHEN** um trecho de conteúdo jurídico (ex. cabeçalho de seção, ementa) se repete entre páginas mas não corresponde a nenhum dos padrões marginais autorizados
- **THEN** o trecho permanece inalterado em todas as páginas em que aparece
