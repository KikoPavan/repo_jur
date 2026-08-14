## Purpose

Estabelecer uma conversão auditável de PDFs jurídicos para Markdown, preservando a rastreabilidade por página e tornando explícitas falhas, uso de OCR e limitações da saída.
## Requirements
### Requirement: Entrada PDF validada

O sistema SHALL aceitar somente um arquivo PDF local por execução e SHALL validar existência, extensão, abertura, criptografia e quantidade de páginas antes de iniciar a conversão.

#### Scenario: PDF válido é aceito

- **WHEN** o operador fornece um PDF existente, legível e não bloqueado por senha
- **THEN** o sistema inicia a inspeção das páginas
- **AND** registra a quantidade total de páginas

#### Scenario: Entrada inválida é rejeitada

- **WHEN** o caminho não existe, o arquivo não é PDF, está corrompido ou requer senha não fornecida
- **THEN** o sistema encerra a execução com status de falha
- **AND** não cria Markdown final
- **AND** registra a causa no relatório técnico

### Requirement: Fonte original preservada

O sistema SHALL tratar o PDF de origem como somente leitura e SHALL impedir qualquer alteração destrutiva no arquivo recebido.

#### Scenario: Conversão não altera a origem

- **WHEN** uma conversão termina com sucesso, falha ou interrupção
- **THEN** o hash SHA-256 do PDF de origem permanece inalterado

### Requirement: Processamento isolado por página

O sistema SHALL processar cada página como uma unidade isolada e SHALL manter correspondência de um para um entre páginas do PDF, blocos do Markdown e registros do relatório.

#### Scenario: PDF com várias páginas

- **WHEN** um PDF com N páginas é processado
- **THEN** o Markdown contém exatamente N blocos de página na ordem original
- **AND** o relatório contém exatamente N registros de página

### Requirement: Roteamento explícito da página

O sistema SHALL classificar cada página como `texto_nativo`, `ocr_integral`, `hibrido`, `vazia` ou `erro` com base em sinais verificáveis da camada textual, conteúdo rasterizado e resultado da conversão.

#### Scenario: Página com texto nativo suficiente

- **WHEN** a página possui camada textual utilizável e não apresenta evidência relevante de conteúdo escaneado não extraído
- **THEN** a página é processada como `texto_nativo`

#### Scenario: Página escaneada

- **WHEN** a página não possui camada textual utilizável e contém conteúdo visual significativo
- **THEN** a página é roteada como `ocr_integral`

#### Scenario: Página mista

- **WHEN** a página possui texto nativo utilizável e também contém conteúdo visual significativo que exige transcrição
- **THEN** a página é roteada como `hibrido`

#### Scenario: Página visualmente vazia

- **WHEN** a página não possui texto nem conteúdo visual significativo
- **THEN** a página é registrada como `vazia`
- **AND** não é tratada como falha

### Requirement: Conversão nativa com MarkItDown

O sistema SHALL usar MarkItDown como motor principal para converter páginas roteadas como `texto_nativo` sem realizar interpretação, resumo ou classificação jurídica.

#### Scenario: Conversão de texto nativo

- **WHEN** uma página é roteada como `texto_nativo`
- **THEN** o texto retornado pelo motor é inserido no bloco correspondente da página
- **AND** nenhuma chamada de OCR externo é realizada para essa página

### Requirement: OCR controlado e verificável

O sistema SHALL executar OCR baseado em visão somente para páginas roteadas como `ocr_integral` ou `hibrido`, usando cliente e modelo configurados externamente.

#### Scenario: OCR configurado retorna conteúdo

- **WHEN** uma página exige OCR e o cliente, o modelo e as credenciais estão configurados
- **THEN** o sistema executa o OCR
- **AND** confirma a presença de conteúdo OCR não vazio
- **AND** registra provedor, modelo e método sem registrar a chave de acesso

#### Scenario: OCR necessário sem configuração

- **WHEN** uma página exige OCR e o cliente, o modelo ou a credencial obrigatória não está configurado
- **THEN** a página é registrada como `erro`
- **AND** a execução falha no modo estrito

#### Scenario: Serviço de OCR emite aviso ou omite conteúdo

- **WHEN** a chamada de OCR falha, retorna aviso técnico, retorna bloco vazio ou não produz evidência verificável de transcrição
- **THEN** a página é registrada como `erro`
- **AND** a execução não pode ser classificada como sucesso

### Requirement: Paginação canônica

O sistema SHALL iniciar cada bloco de página com o marcador exato `[[Pág. N]]`, seguido de um comentário técnico com o método atribuído.

#### Scenario: Bloco de página válido

- **WHEN** a página 7 é composta no Markdown
- **THEN** o bloco inicia com `[[Pág. 7]]`
- **AND** contém exatamente um comentário `<!-- método: ... -->`

#### Scenario: Sequência inválida

- **WHEN** um marcador estiver ausente, duplicado, fora de ordem ou com numeração diferente da página correspondente
- **THEN** a validação final falha

### Requirement: Limpeza conservadora

O sistema SHALL limitar a limpeza a transformações determinísticas e reversíveis quanto ao conteúdo semântico: normalização de fim de linha, remoção de espaços finais, redução de três ou mais linhas vazias consecutivas para duas, recomposição geométrica de parágrafos fragmentados, remoção de cabeçalhos/rodapés técnicos repetitivos, normalização contextual de símbolos jurídicos, reconhecimento de hierarquia legislativa formal e separação do índice final. O sistema SHALL aplicar cada uma dessas transformações somente nas condições descritas nos requisitos específicos desta capacidade e SHALL rejeitar qualquer regra de limpeza que resuma, corrija sentido, deduplique por interpretação ou reescreva conteúdo jurídico.

#### Scenario: Conteúdo jurídico é preservado

- **WHEN** a limpeza é aplicada
- **THEN** datas, números processuais, artigos, incisos, alíneas, ementas, assinaturas, tabelas, marcadores de página e blocos OCR permanecem semanticamente inalterados
- **AND** nenhum texto é perdido, duplicado ou alterado em seu conteúdo lexical

#### Scenario: Transformação semântica é solicitada

- **WHEN** uma regra de limpeza implicar resumir, corrigir, reorganizar por interpretação, deduplicar cabeçalhos por julgamento de conteúdo ou interpretar conteúdo jurídico
- **THEN** a regra é rejeitada nesta fase

### Requirement: Validação estrita de integridade

O sistema SHALL validar a correspondência entre PDF, Markdown e relatório antes de publicar a saída final.

#### Scenario: Documento íntegro

- **WHEN** todas as páginas possuem marcador único, sequência correta, método válido e conteúdo compatível com seu estado
- **THEN** a validação é aprovada

#### Scenario: Página com erro no modo estrito

- **WHEN** qualquer página estiver com método ou estado `erro`
- **THEN** a validação falha
- **AND** o Markdown final não é publicado

#### Scenario: Página não vazia sem conteúdo

- **WHEN** uma página diferente de `vazia` não possuir conteúdo textual verificável
- **THEN** a validação falha

### Requirement: Saída parcial somente por autorização explícita

O sistema SHALL operar em modo estrito por padrão e SHALL publicar saída parcial somente quando o operador fornecer a opção explícita `--allow-partial`.

#### Scenario: Falha sem autorização parcial

- **WHEN** uma ou mais páginas falham e `--allow-partial` não foi informado
- **THEN** o sistema não publica o Markdown final
- **AND** grava relatório com status `falha`

#### Scenario: Saída parcial autorizada

- **WHEN** uma ou mais páginas falham e `--allow-partial` foi informado
- **THEN** o sistema publica o Markdown com `[[TEXTO ILEGÍVEL]]` somente nas páginas afetadas
- **AND** o relatório recebe status `incompleto`
- **AND** lista explicitamente todas as páginas afetadas

### Requirement: Gravação atômica

O sistema SHALL escrever artefatos temporários, executar todas as validações e somente então promover o Markdown e o relatório aos caminhos finais.

#### Scenario: Validação falha após conversão

- **WHEN** a conversão termina mas a validação final falha
- **THEN** nenhum Markdown definitivo substitui uma saída anterior válida
- **AND** os artefatos temporários são removidos ou isolados para diagnóstico

### Requirement: Relatório técnico auditável

O sistema SHALL gerar um relatório JSON com versão de esquema, identificação da origem, hashes, versões de dependências, configuração não secreta, tempos, status global e resultado individual de cada página.

#### Scenario: Relatório de sucesso

- **WHEN** a conversão é concluída e validada
- **THEN** o relatório contém status `sucesso`
- **AND** inclui SHA-256 do PDF e do Markdown
- **AND** inclui versões reais dos pacotes obtidas do ambiente
- **AND** inclui duração total e por página

#### Scenario: Segredos e conteúdo sensível

- **WHEN** o relatório e os logs são gravados
- **THEN** chaves de API, tokens, conteúdo integral de páginas e variáveis secretas não são persistidos

### Requirement: Privacidade do OCR externo

O sistema SHALL tornar explícito que páginas roteadas para OCR podem ser transmitidas a um serviço externo e SHALL exigir configuração consciente do operador.

#### Scenario: OCR externo desabilitado

- **WHEN** o operador desabilita OCR externo
- **THEN** nenhuma imagem de página é enviada a provedor remoto
- **AND** páginas que dependem de OCR falham ou são tratadas conforme `--allow-partial`

### Requirement: Codificação e formato da saída

O sistema SHALL produzir Markdown em UTF-8, com finais de linha LF e uma quebra de linha no final do arquivo.

#### Scenario: Saída validada

- **WHEN** o Markdown final é publicado
- **THEN** ele pode ser decodificado integralmente como UTF-8
- **AND** usa finais de linha LF
- **AND** termina com uma única quebra de linha

### Requirement: Sobrescrita protegida

O sistema SHALL recusar sobrescrever uma saída existente, salvo quando o operador fornecer `--overwrite`.

#### Scenario: Saída já existe

- **WHEN** o caminho final já existe e `--overwrite` não foi informado
- **THEN** o sistema encerra sem alterar o arquivo existente

### Requirement: Escopo limitado da Fase 1

O sistema SHALL excluir desta fase YAML front matter, conformidade OKF completa, classificação semântica, resumo, correção jurídica, identificação autônoma de jurisprudência e extração estruturada de entidades.

#### Scenario: Recurso fora do escopo

- **WHEN** uma solicitação exigir qualquer recurso reservado às fases futuras
- **THEN** o recurso não é implementado nesta mudança
- **AND** deve ser tratado em uma mudança OpenSpec separada

### Requirement: Recomposição geométrica de parágrafos

O sistema SHALL recompor, em páginas com camada textual nativa, blocos de linha consecutivos que pertençam ao mesmo parágrafo jurídico, usando posição geométrica (distância vertical, alinhamento) e continuidade textual entre blocos extraídos do PDF de origem.

O sistema SHALL NOT unir o bloco atual ao próximo quando o próximo bloco iniciar com marcador de Artigo, parágrafo, inciso, alínea ou item; com PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO; com o marcador de página `[[Pág. N]]`; ou com um novo bloco estrutural independente.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual terminar em uma referência jurisprudencial de fechamento (citação de julgamento com turma/seção/órgão julgador e data de publicação no `DJe`, opcionalmente seguida de anotação como "(Grifos acrescidos).") e o próximo bloco for uma linha inteiramente em caixa alta.

O sistema SHALL NOT unir o bloco atual ao próximo quando o bloco atual for inteiramente em maiúsculas, sem dígito ou pontuação, e for a primeira linha física do seu bloco geométrico de origem no PDF — comportamento que protege rótulos de campo (por exemplo "PROCESSO", "RAMO DO DIREITO", "TEMA", "DESTAQUE") de serem fundidos ao valor que os segue. O sistema SHALL permitir a união quando essa mesma forma textual (linha inteiramente em maiúsculas, sem dígito ou pontuação) ocorrer no meio de um bloco geométrico já em fluxo — ou seja, não for a primeira linha física do bloco — desde que as demais condições de junção geométrica e estrutural sejam satisfeitas, mesmo que a linha seja curta ou formada por uma única palavra.

Essa proteção de rótulo SHALL ser refinada quando o bloco de origem da linha candidata a rótulo tiver outras linhas físicas além dela: a proteção só permanece ativa quando o bloco não tiver nenhuma outra linha física (mantendo o comportamento acima, sem alteração), OU quando mais da metade dessas outras linhas físicas do mesmo bloco tiverem coordenada horizontal (x0) diferente por 2pt ou mais da coordenada x0 da própria linha candidata a rótulo — sinal de uma coluna de valor genuinamente recuada (estrutura "rótulo: valor"). Quando mais da metade dessas outras linhas físicas do bloco compartilham a mesma coordenada x0 (dentro de 2pt) da linha candidata — sinal de que a linha é, na verdade, a primeira palavra de um parágrafo justificado comum, fragmentada pela extração em uma pseudo-linha própria apesar de pertencer à mesma linha visual do texto seguinte — a proteção SHALL ser desativada, permitindo a junção normal segundo as demais condições geométricas e estruturais. Esse refinamento SHALL NOT se basear em nenhuma palavra específica (como "RECURSO", "PROCESSO" ou qualquer outro vocabulário jurídico), nome de arquivo, número de página ou de processo — apenas na geometria (contagem e posição x0 das linhas físicas do bloco).

O sistema SHALL NOT unir duas linhas físicas quando qualquer uma das duas pertencer a um bloco geométrico de origem que contenha, em qualquer de suas linhas físicas, texto iniciado por `:` (formato de campo estruturado "RÓTULO" seguido de "`: VALOR`", usado por exemplo em RELATOR, AGRAVANTE, AGRAVADO, ADVOGADOS, RECORRENTE, RECORRIDO). Essa proteção SHALL se aplicar apenas às linhas do bloco geométrico que contém o padrão `:`, e SHALL NOT desativar a recomposição geométrica de outros blocos da mesma página que não contenham esse padrão.

O sistema SHALL NOT unir dois blocos geométricos de origem diferentes entre si quando ambos estiverem dentro do intervalo delimitado por um bloco cuja única linha física seja exatamente o rótulo "SAIBA MAIS" (início do intervalo) e o próximo bloco cuja primeira linha física corresponda a um rótulo de campo inteiramente em maiúsculas (fim do intervalo) — preservando cada item editorial de referência (por exemplo um "Informativo de Jurisprudência", um item de "Jurisprudência em Teses" ou um precedente citado) como parágrafo próprio, independentemente de quantas linhas físicas o item ocupe dentro do seu próprio bloco de origem. Essa proteção SHALL NOT se basear no texto específico de cada item (títulos, números de edição, palavras como "Informativo" ou "Jurisprudência", barras `/` ou datas), apenas na origem do bloco geométrico e no rótulo fixo "SAIBA MAIS", e SHALL NOT impedir a recomposição normal das linhas físicas internas de um único item (por exemplo um precedente cuja citação de Relator e data ocupam duas linhas físicas do mesmo bloco).

Ao estimar a posição vertical de cada linha física dentro de um bloco geométrico de origem, em páginas onde pelo menos um bloco de texto tiver tamanho tipográfico maior ou igual a 20pt, o sistema SHALL calcular essa posição dividindo a altura total do bloco pelo número TOTAL de linhas físicas do bloco (incluindo linhas em branco), preservando o índice original de cada linha não-vazia ao posicioná-la — em vez de dividir apenas pelo número de linhas não-vazias. Fora dessas páginas, o sistema SHALL manter o cálculo já existente (divisão apenas pelas linhas não-vazias). Essa correção SHALL NOT depender do nome do arquivo, do número da página, ou de qualquer palavra ou rótulo específico presente no conteúdo.

#### Scenario: Parágrafo fragmentado é recomposto

- **WHEN** um artigo como "Art. 2º A personalidade civil da pessoa começa do nascimento com vida; mas a lei põe a salvo, desde a concepção, os" é seguido, no mesmo bloco de página, por "direitos do nascituro."
- **THEN** o Markdown final contém um único parágrafo com o texto completo do artigo, sem quebra de linha intermediária

#### Scenario: Início de novo dispositivo não é unido ao anterior

- **WHEN** um bloco de texto termina um parágrafo e o próximo bloco inicia com "Art.", "§", "I -", "a)", "PARTE", "LIVRO", "TÍTULO", "SUBTÍTULO", "CAPÍTULO", "SEÇÃO", "SUBSEÇÃO" ou o marcador `[[Pág. N]]`
- **THEN** os blocos permanecem separados no Markdown final

#### Scenario: Marcador SUBTÍTULO não é anexado ao dispositivo anterior

- **WHEN** um artigo, um parágrafo, um inciso ou um cabeçalho `TÍTULO` já formado é seguido, no mesmo bloco de página, pelo marcador bare "SUBTÍTULO N" (ex. "SUBTÍTULO I")
- **THEN** o marcador `SUBTÍTULO N` permanece separado, como parágrafo próprio, do conteúdo anterior no Markdown final

#### Scenario: Dois precedentes jurisprudenciais consecutivos não são unidos

- **WHEN** um bloco termina com uma citação de julgamento como "(AgInt no REsp 1739440/SP, Rel. Ministra REGINA HELENA COSTA, PRIMEIRA TURMA, julgado em 08/11/2018, DJe 26/11/2018) (Grifos acrescidos)." e o bloco seguinte, no mesmo grupo geométrico, é uma linha inteiramente em caixa alta como "RECURSO ESPECIAL. INDENIZAÇÃO POR DANO MORAL. ..."
- **THEN** os dois blocos permanecem separados por quebra de parágrafo no Markdown final, sem fundir os dois precedentes em um único parágrafo

#### Scenario: Rótulo de campo real permanece separado do valor que o segue

- **WHEN** uma linha como "TEMA", "PROCESSO", "RAMO DO DIREITO" ou "DESTAQUE" é a primeira linha física do seu bloco geométrico de origem, é seguida por linhas de conteúdo do respectivo campo, e essas linhas de conteúdo têm coordenada x0 consistentemente diferente da linha-rótulo
- **THEN** a linha-rótulo permanece separada, como parágrafo próprio, do conteúdo do campo no Markdown final

#### Scenario: Palavra maiúscula isolada no início de um parágrafo justificado é recomposta corretamente

- **WHEN** a extração nativa fragmenta a primeira palavra de uma linha totalmente justificada (por exemplo "RECURSO" seguido de "ESPECIAL. PROCESSUAL CIVIL. ...") em uma pseudo-linha própria, apesar de pertencer à mesma linha visual do restante do texto, e as demais linhas físicas do mesmo bloco geométrico retornam à mesma coordenada x0 dessa primeira palavra (sem coluna de valor recuada)
- **THEN** a palavra isolada é recomposta normalmente com o restante da linha e do parágrafo, sem perda, adição ou reordenação de tokens, e sem depender do texto específico da palavra

#### Scenario: Título ou ementa fragmentado em palavras isoladas é recomposto

- **WHEN** uma ementa ou título em caixa alta é extraído do PDF como sequência de linhas de uma ou poucas palavras cada (por exemplo "PROVEITO" / "ECONÔMICO" / "DA" / "DEMANDA." em sequência), e nenhuma dessas linhas é a primeira linha física do seu bloco geométrico
- **THEN** essas linhas são recompostas em um único parágrafo de texto corrido no Markdown final, sem perda, adição ou reordenação de tokens

#### Scenario: Campo temático fragmentado em palavras isoladas é recomposto

- **WHEN** o valor de um campo temático como "RAMO DO DIREITO" é extraído do PDF, dentro do mesmo bloco geométrico do rótulo, como sequência de linhas de uma ou poucas palavras cada (por exemplo "DIREITO" / "PROCESSUAL" / "PENAL," / "DIREITO" / "DA" / "PESSOA" / "COM" / "DEFICIÊNCIA")
- **THEN** a linha-rótulo permanece separada como parágrafo próprio
- **AND** as linhas do valor, por não serem a primeira linha física do bloco, são recompostas em um único parágrafo de texto corrido, sem perda, adição ou reordenação de tokens

#### Scenario: Campo "RÓTULO / : VALOR" permanece separado, sem impedir a recomposição de outros blocos da página

- **WHEN** uma página contém um bloco geométrico com o padrão "RÓTULO" seguido por "`: VALOR`" (por exemplo "RELATOR" / ": MINISTRO FULANO") e, em outro bloco geométrico da mesma página sem nenhuma linha `:`, um parágrafo ou ementa fragmentado em várias linhas físicas
- **THEN** o rótulo e o valor não são fundidos em uma única linha no Markdown final
- **AND** o parágrafo ou ementa do outro bloco, sem relação com o campo `:`, é recomposto normalmente em um único parágrafo de texto corrido

#### Scenario: Múltiplos campos "RÓTULO / : VALOR" consecutivos no mesmo bloco permanecem distintos

- **WHEN** um único bloco geométrico contém vários pares consecutivos de rótulo e valor (por exemplo "AGRAVANTE" / ": NORTE ENERGIA S.A." / "ADVOGADOS" / ": PRISCILA SANTOS ARTIGAS - PR022529")
- **THEN** nenhum desses rótulos ou valores é fundido com o rótulo, valor ou campo vizinho em uma única linha no Markdown final

#### Scenario: Itens independentes de "SAIBA MAIS" que quebram em duas linhas físicas não são fundidos entre si

- **WHEN** um item de "Jurisprudência em Teses" cujo título quebra em duas linhas físicas do seu próprio bloco geométrico (por exemplo "Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 117: INTERCEPTAÇÃO" / "TELEFÔNICA - I") é seguido, na seção "SAIBA MAIS", por outro item independente em um bloco geométrico distinto (por exemplo outro "Jurisprudência em Teses" ou um "Informativo de Jurisprudência n. 751")
- **THEN** as duas linhas físicas do primeiro item permanecem unidas em uma só linha dentro do mesmo parágrafo
- **AND** o item seguinte permanece em parágrafo próprio, separado do primeiro item, no Markdown final

#### Scenario: Precedente com Relator e data em duas linhas não funde o "Informativo" seguinte

- **WHEN** um precedente citado dentro de "SAIBA MAIS" tem a citação de Relator e data de julgamento fragmentada em duas linhas físicas do mesmo bloco geométrico (por exemplo "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA SEÇÃO, julgado em" / "10/04/2019, DJe 16/04/2019") e é seguido, em outro bloco geométrico, por um "Informativo de Jurisprudência n. 474"
- **THEN** a citação do precedente permanece unida em um único parágrafo, incluindo a data
- **AND** o "Informativo de Jurisprudência n. 474" permanece em parágrafo próprio, separado do precedente

#### Scenario: Fusão entre itens de "SAIBA MAIS" não afeta blocos fora da seção

- **WHEN** um bloco de duas linhas físicas fora de qualquer seção "SAIBA MAIS" é seguido por outro bloco geométrico dentro da distância vertical normalmente exigida para junção
- **THEN** a decisão de unir ou não esses blocos segue exclusivamente a lógica geométrica e estrutural já existente, sem qualquer efeito do rótulo "SAIBA MAIS"

#### Scenario: Elementos de uma capa editorial estilizada permanecem separados

- **WHEN** uma página contém um bloco de texto com tamanho tipográfico ≥20pt (por exemplo um título estilizado de capa) e, em outro bloco geométrico da mesma página, linhas físicas em branco intercaladas com conteúdo real (por exemplo uma linha de edição/data precedida de várias linhas em branco de espaçamento)
- **THEN** o conteúdo real desse bloco permanece separado do bloco anterior e do bloco seguinte, cada elemento estrutural (título, linha de edição/data, aviso editorial, cabeçalho de câmara julgadora) em parágrafo próprio, sem perda, adição ou reordenação de tokens

#### Scenario: Página sem bloco de texto ≥20pt preserva o comportamento já existente

- **WHEN** uma página não contém nenhum bloco de texto com tamanho tipográfico ≥20pt, mesmo que algum bloco geométrico contenha linhas físicas em branco intercaladas com conteúdo real
- **THEN** a posição de cada linha física continua sendo calculada dividindo a altura do bloco apenas pelas linhas não-vazias (comportamento pré-existente, sem alteração)

#### Scenario: Bloco sem outras linhas físicas mantém a proteção de rótulo

- **WHEN** uma linha candidata a rótulo (inteiramente maiúscula, sem dígito ou pontuação, primeira linha física do seu bloco) pertence a um bloco geométrico que não tem nenhuma outra linha física além dela
- **THEN** a proteção de rótulo permanece ativa exatamente como antes deste refinamento, sem depender de dado de x0

### Requirement: Remoção de cabeçalhos e rodapés repetitivos

O sistema SHALL remover, de cada bloco de página, apenas linhas marginais comprovadamente repetitivas entre páginas e com posição semelhante (topo ou rodapé do bloco), limitadas a: data e hora de impressão; nome técnico do arquivo de origem; URL repetida; contador de página no formato "N/total"; e texto de cabeçalho ou rodapé repetido verbatim (byte-idêntico), confirmado por aparecer isolado como linha de conteúdo completa em pelo menos duas páginas e por atingir, em frequência total, o mesmo limiar estatístico usado para os demais padrões. O sistema SHALL remover apenas o trecho correspondente ao cabeçalho/rodapé repetido quando este estiver fundido ao início do conteúdo textual real da página seguinte, preservando integralmente esse conteúdo. O sistema SHALL remover apenas o trecho correspondente ao cabeçalho/rodapé repetido quando este estiver fundido ao final do conteúdo textual real da página anterior, preservando integralmente esse conteúdo. Quando mais de uma margem recorrente distinta estiver empilhada na mesma borda de uma página (ex. uma assinatura eletrônica legítima recorrente acima de um rodapé técnico também recorrente), o sistema SHALL remover cada uma delas, reaplicando o mesmo critério de recorrência e limiar até que nenhuma margem adicional seja identificada, preservando integralmente o conteúdo jurídico substantivo entre elas. O sistema SHALL preservar o marcador `[[Pág. N]]` em todas as páginas e SHALL NOT remover conteúdo jurídico apenas por ele se repetir entre páginas, e SHALL NOT remover uma linha apenas por conter palavras isoladas semelhantes a um padrão marginal conhecido (ex. "Documento", "Página", data) sem que o texto correspondente já satisfaça o critério de recorrência verbatim exigido neste requisito.

#### Scenario: Rodapé técnico é removido

- **WHEN** uma linha contendo data/hora de impressão, nome de arquivo técnico, URL ou contador "N/186" aparece de forma repetida na mesma posição (topo ou rodapé) em uma fração alta das páginas
- **THEN** essa linha é removida do bloco de cada página em que aparece
- **AND** o marcador `[[Pág. N]]` correspondente permanece intacto

#### Scenario: Cabeçalho repetido fundido à continuação da página seguinte é separado

- **WHEN** um cabeçalho institucional (ex. "Superior Tribunal de Justiça") aparece isolado, como linha de conteúdo completa, em pelo menos duas páginas, e em outra página aparece fundido ao início do conteúdo textual real que continua um dispositivo iniciado na página anterior (ex. "Superior Tribunal de Justiça agravada, pois demonstrado o rebate do fundamento...")
- **THEN** o cabeçalho é removido e o conteúdo textual real permanece, iniciando corretamente pela continuação (ex. "agravada, pois demonstrado o rebate do fundamento...")

#### Scenario: Rodapé técnico fundido ao final de um parágrafo é separado

- **WHEN** um rodapé técnico (ex. "GABGF09 AREsp 1462304 Petição : 592169/2020 ... Documento") aparece isolado, como linha de conteúdo completa, em pelo menos duas páginas, e em outra página aparece fundido ao final do conteúdo textual real de um parágrafo que termina naquela página (ex. "6. Afastado o óbice da Súmula 283 do STF, empregado na decisão GABGF09 AREsp 1462304 Petição : 592169/2020 ... Documento")
- **THEN** o rodapé é removido e o conteúdo textual real permanece, terminando corretamente no ponto em que o parágrafo real termina (ex. "6. Afastado o óbice da Súmula 283 do STF, empregado na decisão")

#### Scenario: Rodapé técnico fundido interrompe um nome entre páginas

- **WHEN** um rodapé técnico (ex. "Documento: 1807307 - Inteiro Teor do Acórdão - Site certificado - DJe: 04/04/2019") aparece isolado, como linha de conteúdo completa, em pelo menos duas páginas, e em outra página aparece fundido entre o final de um nome próprio iniciado antes do rodapé (ex. "Os Srs. Ministros Paulo de") e o marcador `[[Pág. N]]` seguinte, cujo conteúdo continua o mesmo nome (ex. "Tarso Sanseverino...")
- **THEN** o rodapé é removido, a página anterior termina corretamente no ponto em que o nome é interrompido (ex. "Os Srs. Ministros Paulo de") e a página seguinte permanece inalterada, iniciando por sua continuação (ex. "Tarso Sanseverino...")

#### Scenario: Margens recorrentes empilhadas são removidas em conjunto

- **WHEN** uma página termina com duas margens recorrentes distintas empilhadas (ex. um rodapé técnico recorrente imediatamente seguido, mais abaixo, por uma assinatura eletrônica legítima que também se repete verbatim em frequência suficiente), de modo que a assinatura ocupa a posição de última linha de conteúdo e o rodapé técnico fica na posição imediatamente anterior
- **THEN** tanto a assinatura quanto o rodapé técnico são removidos, e o conteúdo jurídico substantivo que os precede permanece intacto, terminando corretamente no ponto em que o texto real termina

#### Scenario: Cabeçalho ou rodapé abaixo do limiar de frequência é preservado

- **WHEN** uma linha repetida na posição de topo ou rodapé do bloco não atinge o limiar estatístico de frequência já usado para as demais margens, ou nunca aparece isolada como linha de conteúdo completa em pelo menos duas páginas
- **THEN** essa linha permanece inalterada em todas as páginas em que aparece

#### Scenario: Assinatura eletrônica legítima não recorrente é preservada

- **WHEN** uma linha de assinatura eletrônica legítima (ex. "Documento eletrônico VDA... assinado eletronicamente...") aparece em menos ocorrências do que o limiar estatístico de frequência total exigido para remoção de margens
- **THEN** essa linha permanece inalterada, mesmo contendo palavras como "Documento" ou datas

#### Scenario: Conteúdo jurídico repetido é preservado

- **WHEN** um trecho de conteúdo jurídico (ex. cabeçalho de seção, ementa) se repete entre páginas mas não corresponde a nenhum dos padrões marginais autorizados
- **THEN** o trecho permanece inalterado em todas as páginas em que aparece

### Requirement: Normalização contextual de símbolos jurídicos

O sistema SHALL normalizar exclusivamente os padrões jurídicos corrompidos pela extração explicitamente autorizados: "Art. N o" para "Art. Nº", "§ N o" para "§ Nº", "Lei n o" para "Lei nº", e ordinais jurídicos equivalentes quando o contexto for inequívoco. O sistema SHALL NOT substituir ocorrências da letra "o" isoladas após números fora desses contextos, e SHALL preservar números, datas, valores monetários e referências legais não abrangidos por esses padrões.

#### Scenario: Símbolo jurídico corrompido é normalizado

- **WHEN** o Markdown extraído contém "Art. 1 o" ou "§ 1 o" ou "Lei n o"
- **THEN** o Markdown final contém, respectivamente, "Art. 1º", "§ 1º" e "Lei nº"

#### Scenario: Números e datas fora de contexto não são alterados

- **WHEN** o Markdown contém números, datas, valores monetários ou referências legais que não correspondem a nenhum padrão autorizado de normalização
- **THEN** esse conteúdo permanece byte-idêntico ao extraído

### Requirement: Reconhecimento de estrutura legislativa

O sistema SHALL reconhecer marcadores estruturais formais (PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO, SUBSEÇÃO) e, quando o título correspondente aparecer imediatamente a seguir dentro do mesmo bloco de página, SHALL uni-los em um único cabeçalho Markdown (`#` para PARTE, `##` para LIVRO, `###` para TÍTULO, `####` para SUBTÍTULO e CAPÍTULO, `#####` para SEÇÃO, `######` para SUBSEÇÃO). O sistema SHALL NOT converter texto comum em cabeçalho apenas por estar em maiúsculas.

#### Scenario: Marcador estrutural e título são unidos

- **WHEN** o Markdown contém "LIVRO I" seguido, na linha seguinte, por "DAS PESSOAS"
- **THEN** o Markdown final contém um único cabeçalho Markdown "## LIVRO I — DAS PESSOAS" ou equivalente que preserve ambos os textos originais

#### Scenario: SUBTÍTULO forma cabeçalho próprio no mesmo nível de CAPÍTULO

- **WHEN** o Markdown contém o marcador bare "SUBTÍTULO I" seguido, no mesmo bloco de página, por sua denominação (ex. "Do Casamento")
- **THEN** o Markdown final contém um único cabeçalho Markdown "#### SUBTÍTULO I — Do Casamento" ou equivalente que preserve ambos os textos originais

#### Scenario: Texto maiúsculo comum não vira título

- **WHEN** uma linha em maiúsculas não é precedida por um marcador estrutural formal (PARTE, LIVRO, TÍTULO, SUBTÍTULO, CAPÍTULO, SEÇÃO ou SUBSEÇÃO)
- **THEN** essa linha permanece como texto comum no Markdown final

### Requirement: Separação do índice final

O sistema SHALL identificar o índice posicionado após o encerramento do corpo normativo e SHALL inserir um cabeçalho `# ÍNDICE` imediatamente antes do início do conteúdo identificado como índice, sem excluir ou reordenar esse conteúdo. O sistema SHALL demover, em exatamente um nível de cabeçalho Markdown adicional (respeitando o teto de `######`), qualquer cabeçalho Markdown que já exista estritamente após `# ÍNDICE`, de modo que nenhum cabeçalho dentro do índice compartilhe o mesmo nível de `# ÍNDICE` ou o ultrapasse. Essa demoção SHALL se basear exclusivamente na posição do cabeçalho em relação a `# ÍNDICE`, nunca em seu texto ou palavra-chave específica, e SHALL NOT alterar nenhum cabeçalho posicionado antes de `# ÍNDICE`.

#### Scenario: Índice é identificado e demarcado

- **WHEN** o documento contém, após o último artigo do corpo normativo, um bloco de páginas cujo conteúdo é predominantemente uma lista de títulos e números de página
- **THEN** o Markdown final contém o cabeçalho `# ÍNDICE` imediatamente antes desse bloco
- **AND** todo o conteúdo original do índice permanece presente e na mesma ordem

#### Scenario: Ausência de índice detectável

- **WHEN** o documento não contém um padrão de índice identificável após o corpo normativo
- **THEN** o sistema NÃO insere o cabeçalho `# ÍNDICE`
- **AND** nenhum conteúdo é removido ou alterado

#### Scenario: Cabeçalho dentro do índice é subordinado a `# ÍNDICE`

- **WHEN** um marcador legislativo (por exemplo "PARTE GERAL") já foi convertido em cabeçalho Markdown de nível 1 pelo reconhecimento de estrutura legislativa, e esse cabeçalho está posicionado dentro do bloco identificado como índice
- **THEN** o Markdown final contém esse cabeçalho em um nível estritamente maior que `# ÍNDICE` (por exemplo `## PARTE GERAL`)
- **AND** o texto do cabeçalho permanece inalterado, apenas o nível Markdown muda

#### Scenario: Cabeçalhos do corpo antes do índice não são afetados

- **WHEN** um cabeçalho Markdown de qualquer nível é gerado a partir de um marcador legislativo no corpo normativo, antes do início do índice
- **THEN** esse cabeçalho permanece exatamente no nível originalmente atribuído pelo reconhecimento de estrutura legislativa

### Requirement: Normalização de entidades HTML de espaçamento fino

O sistema SHALL substituir entidades HTML literais equivalentes ao caractere THIN SPACE (U+2009) — `&#8201;` (decimal), `&#x2009;`/`&#X2009;` (hexadecimal) e `&thinsp;` (nomeada, case-insensitive) — por um único espaço ASCII regular (U+0020), absorvendo qualquer espaço ou tabulação horizontal já adjacente à entidade para não duplicar espaços. O sistema SHALL NOT alterar nenhuma outra entidade HTML (ex. `&amp;`, `&lt;`, `&gt;`, `&nbsp;`), SHALL NOT remover ou alterar caracteres alfanuméricos ou pontuação adjacentes à entidade, e SHALL NOT consumir quebras de linha ao redor da entidade. A normalização SHALL ser idempotente.

#### Scenario: Entidade colada entre palavras é substituída por um espaço

- **WHEN** o Markdown extraído contém `na&#8201;realidade`
- **THEN** o Markdown final contém `na realidade`, sem espaço duplicado e sem perda de caracteres

#### Scenario: Entidade adjacente a um espaço já existente não duplica o espaço

- **WHEN** o Markdown extraído contém `apreensão de &#8201;37 gramas` (espaço antes da entidade, colada ao número seguinte)
- **THEN** o Markdown final contém `apreensão de 37 gramas`, com exatamente um espaço entre "de" e "37"

#### Scenario: Variantes equivalentes de THIN SPACE são normalizadas da mesma forma

- **WHEN** o Markdown extraído contém `&#x2009;`, `&#X2009;` ou `&thinsp;` (em qualquer capitalização) na mesma posição em que `&#8201;` ocorreria
- **THEN** o Markdown final contém um único espaço ASCII no lugar da entidade, com o mesmo comportamento de não duplicação de espaço

#### Scenario: Outras entidades HTML permanecem inalteradas

- **WHEN** o Markdown contém entidades HTML sem relação com espaçamento fino (ex. `&amp;`, `&lt;`, `&gt;`, `&nbsp;`)
- **THEN** essas entidades permanecem byte-idênticas ao extraído

#### Scenario: Pontuação e marcadores estruturais permanecem intactos

- **WHEN** a entidade de espaçamento fino aparece adjacente a pontuação (ex. `n.&#8201;11.343`) ou em um documento que também contém `[[Pág. N]]` e comentários `<!-- método: ... -->`
- **THEN** a pontuação permanece inalterada e os marcadores de página e método permanecem intactos

### Requirement: Deduplicação geométrica de texto rotacionado sobreposto

Em páginas roteadas como `texto_nativo`, quando o PDF de origem contiver duas ou mais linhas de texto com direção de escrita não horizontal, texto extraído idêntico entre si e geometria (bbox) coincidente dentro de uma tolerância determinística, o sistema SHALL tratar essas linhas como uma única ocorrência de conteúdo. O sistema SHALL, nesse caso, usar como fonte do conteúdo da página uma representação geométrica já deduplicada — obtida diretamente da camada de texto do PDF de origem, sem depender do motor de conversão nativo — em vez de repassar a duplicação ao motor de conversão nativo, evitando que esse motor produza fragmentação em caracteres isolados ou duplicação de texto na saída a partir desse padrão geométrico.

O sistema SHALL preservar, sem descartar, uma ocorrência única e não duplicada de texto com direção não horizontal, mesmo quando essa ocorrência coexistir, na mesma página, com um par de linhas duplicadas legitimamente tratado por este requisito.

O sistema SHALL NOT aplicar esta deduplicação a linhas de texto com direção horizontal, ainda que estas se repitam com texto e geometria idênticos entre si.

Esta detecção e deduplicação SHALL depender exclusivamente de sinais geométricos e do texto já extraído das próprias linhas (direção de escrita, coordenadas de bbox, igualdade de texto entre linhas) — SHALL NOT depender do nome do documento de origem, de número de página ou de processo, do conteúdo textual específico de uma assinatura, ou de nome de pessoa.

Esta correção SHALL NOT introduzir nenhuma chamada adicional de OCR, nem alterar o roteamento da página.

#### Scenario: Linhas verticais duplicadas e sobrepostas são deduplicadas

- **WHEN** uma página roteada como `texto_nativo` contém duas linhas de texto com direção de escrita não horizontal, texto extraído idêntico entre si e bbox coincidente dentro da tolerância determinística
- **THEN** o conteúdo final dessa página contém esse texto exatamente uma vez
- **AND** o conteúdo final não contém a sequência de linhas de caractere isolado que a duplicação geométrica produziria se repassada sem tratamento ao motor de conversão nativo

#### Scenario: Ocorrência única de texto rotacionado é preservada

- **WHEN** uma página contém uma linha de texto com direção não horizontal sem nenhuma outra linha correspondente (mesmo texto e bbox dentro da tolerância) na mesma página
- **THEN** essa linha permanece presente e inalterada no conteúdo final da página

#### Scenario: Texto horizontal duplicado não é afetado por esta regra

- **WHEN** uma página contém duas linhas de texto com direção de escrita horizontal, texto e geometria idênticos entre si
- **THEN** nenhuma das duas linhas é descartada ou tratada como duplicata por este requisito

#### Scenario: Linhas geometricamente distintas não são tratadas como duplicata

- **WHEN** duas linhas de texto com direção não horizontal têm texto idêntico mas bbox fora da tolerância determinística, ou têm bbox coincidente mas texto diferente entre si
- **THEN** nenhuma das duas linhas é descartada
- **AND** ambas permanecem presentes no conteúdo final da página

#### Scenario: Nenhuma chamada de OCR é introduzida pela deduplicação

- **WHEN** a deduplicação geométrica descrita neste requisito é aplicada a uma página roteada como `texto_nativo`
- **THEN** nenhuma chamada de OCR é realizada para essa página
- **AND** o método atribuído à página permanece `texto_nativo`

### Requirement: Substituição geométrica de resíduo de texto rotacionado fragmentado na rota híbrida/OCR

Em páginas roteadas como `hibrido` ou `ocr_integral`, quando o resultado bruto do motor de OCR contiver, após o(s) marcador(es) internos `[End OCR]*`, uma sequência de fragmentos majoritariamente muito curtos (até 2 caracteres cada, separados por linha em branco), e essa sequência corroborar geometricamente — por proximidade de tamanho total e por sobreposição de multiconjunto de caracteres, dentro de limiares determinísticos — pelo menos uma linha de texto com direção de escrita não horizontal já extraída da mesma página via a camada de texto nativa do PDF de origem, o sistema SHALL substituir essa sequência de fragmentos pela representação coerente (não fragmentada) dessa(s) linha(s) de texto, preservando o conteúdo textual em vez de descartá-lo.

O sistema SHALL preservar, sem alteração, todo o conteúdo do resultado bruto do motor de OCR que precede o(s) marcador(es) `[End OCR]*`.

O sistema SHALL preservar, sem remoção, o(s) próprio(s) marcador(es) `[End OCR]*` — sua presença ou remoção no Markdown final é um comportamento não afetado por este requisito.

O sistema SHALL NOT aplicar esta substituição quando a sequência de fragmentos não corroborar geometricamente com nenhuma linha de texto não horizontal da mesma página, ainda que essa sequência seja majoritariamente composta por fragmentos curtos.

O sistema SHALL NOT aplicar esta substituição a páginas roteadas como `texto_nativo`.

Esta detecção e substituição SHALL depender exclusivamente de sinais estruturais (posição relativa ao marcador `[End OCR]*`, comprimento dos fragmentos) e geométricos (direção de escrita e texto de linhas já extraídas via a camada de texto nativa do PDF de origem) — SHALL NOT depender do nome do documento de origem, de número de página ou de processo, de nome de pessoa, ou de qualquer texto literal específico de um padrão de autenticação.

Esta correção SHALL NOT modificar o pacote de terceiros usado para OCR, SHALL NOT introduzir nenhuma chamada adicional de OCR, e SHALL NOT alterar o roteamento da página.

#### Scenario: Resíduo vertical fragmentado corroborado geometricamente é substituído pela forma coerente

- **WHEN** uma página roteada como `hibrido` ou `ocr_integral` produz, após `[End OCR]*`, uma sequência de fragmentos majoritariamente de até 2 caracteres cada, cujo conteúdo concatenado corresponde (dentro dos limiares determinísticos de proporção de tamanho e sobreposição de caracteres) a uma linha de texto não horizontal já lida da mesma página
- **THEN** o conteúdo final dessa página contém, no lugar dessa sequência de fragmentos, a forma coerente e legível dessa linha de texto
- **AND** o conteúdo do resultado de OCR anterior ao marcador `[End OCR]*` permanece inalterado
- **AND** o próprio marcador `[End OCR]*` permanece presente

#### Scenario: Resíduo vertical legítimo e não fragmentado é preservado sem alteração

- **WHEN** o conteúdo após `[End OCR]*` já é uma representação coerente (não uma sequência de fragmentos majoritariamente curtos) de uma linha de texto não horizontal da mesma página
- **THEN** esse conteúdo permanece inalterado

#### Scenario: Resíduo horizontal legítimo não é afetado

- **WHEN** o conteúdo após `[End OCR]*` é texto horizontal legítimo, não fragmentado em uma sequência majoritariamente curta
- **THEN** esse conteúdo permanece inalterado, independentemente de existir ou não texto não horizontal na mesma página

#### Scenario: Sequência de fragmentos curtos sem corroboração geométrica não é removida

- **WHEN** uma sequência de fragmentos majoritariamente curtos aparece após `[End OCR]*`, mas a página não contém nenhuma linha de texto não horizontal, ou o conteúdo concatenado dos fragmentos não corresponde ao texto de nenhuma linha não horizontal da página dentro dos limiares determinísticos
- **THEN** essa sequência permanece inalterada no conteúdo final

#### Scenario: Páginas de texto nativo não são afetadas

- **WHEN** uma página é roteada como `texto_nativo`
- **THEN** esta substituição não é aplicada a essa página, independentemente do conteúdo da página

#### Scenario: Nenhuma chamada de OCR adicional é introduzida pela substituição

- **WHEN** a substituição geométrica descrita neste requisito é aplicada a uma página roteada como `hibrido` ou `ocr_integral`
- **THEN** nenhuma chamada adicional de OCR é realizada para essa página
- **AND** o método atribuído à página permanece `hibrido` ou `ocr_integral`, conforme já determinado pelo roteamento

