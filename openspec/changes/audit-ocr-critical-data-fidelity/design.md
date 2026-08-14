# Design — audit-ocr-critical-data-fidelity

Mudança **exclusivamente diagnóstica** (instrução explícita via `/goal`: "SOMENTE DIAGNÓSTICO"). Nenhum código foi alterado, nenhuma chamada real de OCR/LLM foi feita, nenhum arquivo de `output/`/`logs/` canônico foi tocado, nenhum arquivamento ou push foi executado.

## Caso e evidência usada

`input/processos_auditoria/012-015-Testamento Publico.pdf` (4 páginas, todas roteadas `hibrido`, 150 DPI nativo confirmado por extração da imagem embutida via PyMuPDF: `1272x1752px` sobre página `611x841pt` ⇒ `1272/8.49in ≈ 150 DPI`).

- **PDF original**: `input/processos_auditoria/012-015-Testamento Publico.pdf`.
- **Markdown da última conversão OCR real**: `var/ocr_final/output/012-015-Testamento Publico.md` (execução real, não rastreada pelo git — `?? var/ocr_final/` no `git status` desde o início da sessão —, `run_id=0eb25096…`, `started_at=2026-08-14T14:48:54Z`, `finished_at=2026-08-14T14:49:55Z`, ou seja, executada **antes** desta sessão diagnóstica, não por ela). Log correspondente: `var/ocr_final/logs/012-015-Testamento Publico.report.json`.
- **Mudanças OCR já arquivadas usadas como contexto**: `openspec/changes/archive/2026-08-12-validate-supervised-ocr-testamento-publico/` (primeira validação real, 2026-08-12, com comparação visual página a página já documentada) e `openspec/changes/archive/2026-08-14-fix-ocr-rotated-text-fragmentation/` + `openspec/changes/archive/2026-08-14-fix-ocr-end-marker-leak/` (correções de ruído de fragmentação e vazamento do marcador `[End OCR]*`, ambas já aplicadas ao pipeline).
- **Confirmação de que `var/ocr_final` reflete as correções já arquivadas**: `diff` entre `var/ocr_final/output/012-015-Testamento Publico.md` e o Markdown arquivado em `validate-supervised-ocr-testamento-publico/audit_output/output/` mostra texto substantivo **idêntico** por página; a única diferença estrutural é que a versão de 2026-08-12 (pré-correção) ainda contém o bloco de ruído `[End OCR]*` + ~209 linhas de 1 caractere por página, ausente na versão atual — confirmando visualmente, com dados reais, que as duas correções já arquivadas continuam efetivas hoje.

## ETAPA 1 — Inventário (PDF × Markdown, sem nova chamada OCR)

Classificação: **EXATA** (visualmente confirmado idêntico ao PDF) / **DIVERGENTE** (visualmente confirmado diferente) / **INCERTA VISUALMENTE** (fonte não permite confirmação seura, positiva ou negativa).

| Classe | Ocorrências no documento | Classificação | Evidência |
| --- | --- | --- | --- |
| CPF | 6 (Juraci `793.933.908-78`; Jonas `041.996.388-06`; Vânia `049.807.668-70`; Francisco Carlos `835.259.478-87`; Philipp `315.733.428-07`; Maria Eulina `296.322.408-71`) | **EXATA** (6/6) | Herdada da comparação visual página a página já arquivada em `validate-supervised-ocr-testamento-publico/proposal.md` ("CPFs... todos conferidos e corretos"), reconfirmada nesta sessão porque o texto substantivo do Markdown de 2026-08-12 e o de `var/ocr_final` (2026-08-14) são byte-idênticos nesses trechos (ver `diff` acima). Reforçada por checksum determinístico nesta sessão — ver Etapa 3.A. |
| RG / CNH | 6 RGs + 1 CNH | **EXATA** (7/7) | Mesma herança da comparação visual de 2026-08-12; sem checksum nacional padronizado disponível para confirmação determinística independente (ver Etapa 3.A). |
| Número de processo (CNJ) | `1000386-85.2026.8.26.0136` — 4 ocorrências (uma por página, rodapé) | **EXATA** (4/4) | Texto **nativo** do PDF (não OCR): `page.get_text()` via PyMuPDF extrai exatamente esse bloco (386 caracteres) nas 4 páginas, byte-idêntico ao que aparece no Markdown — o `hibrido` corretamente preservou o texto nativo do rodapé em vez de re-OCR'á-lo. |
| Código de verificação e-SAJ | `ewt4TQYQ` — 4 ocorrências | **EXATA** (4/4) | Mesma origem nativa acima. |
| Matrícula de imóvel | `7.013`; `907` | **EXATA** (2/2) | Herdada da comparação visual de 2026-08-12. |
| Selo digital | `1233981TE000000009055623E` (selo do testamento original, p.3); `1233981CE000000001844626I` (selo da certidão/cópia, ocorre 2×: p.3 em texto corrido, p.4 isolado abaixo do QR Code) | **1 EXATA + 1 DIVERGENTE + 1 EXATA** (ver detalhamento abaixo) | Verificação pixel-a-pixel própria desta sessão — ver Etapa 2. |
| Protocolo / Ordem de Serviço | `Protocolo nº 6214`; `Ordem de Serviço nº 8283` | **EXATA** (2/2) | Herdada da comparação visual de 2026-08-12. |
| Datas | 10 datas distintas (ex.: `18/12/2023`, `05/11/1932`, `26/12/2023`, `09/03/2026`, `05/04/2026`, …) | **EXATA** (10/10) | Herdada da comparação visual de 2026-08-12. |
| Valores monetários | 18 valores (`R$ 1.306,98` … `R$ 95,12`) | **EXATA** (18/18) | Herdada da comparação visual de 2026-08-12. |
| CEP | 5 CEPs distintos (`18760-037`, `18760-063`, `18760-047`, `18760-394`, `18780-304`) | **EXATA** (5/5) | Herdada da comparação visual de 2026-08-12. |
| Medidas / geometria | Área (`2.352,00 m²`), 6 comprimentos, 4 rumos (`51°07'SE` etc.) | **EXATA** | Herdada da comparação visual de 2026-08-12. |
| Livro / Folhas | `Livro 132, fls. 043/045`; `Livro 127, fls. 090/093` | **EXATA** | Herdada da comparação visual de 2026-08-12. |
| Telefone (FONE) | `FONE: (14) 3357-[ilegível]` — aparece (parcialmente) nas págs. 1 e 3 | **INCERTA VISUALMENTE** | Verificação própria desta sessão — ver Etapa 2. |

O Markdown **não foi corrigido** em nenhum ponto desta auditoria.

## ETAPA 2 — Causa (as duas divergências investigadas em detalhe)

### 2.1 Selo digital da página 3 (`CE`) — DIVERGENTE confirmado

- **Texto visual original** (lido diretamente do PDF, fonte em negrito nítida, sem ambiguidade): `1233981CE000000001844626I` — **8 zeros** entre `CE` e `1844626I` (25 caracteres). Confirmado por segmentação de caracteres por projeção vertical de pixels (largura de caractere ≈ 12px, consistente e monoespaçada nessa região) sobre a imagem nativa extraída do PDF (1272×1752px, sem reamostragem). Evidência: `evidence/p3_selo_CE_ocr_error_zoom.png`.
- **OCR produzido** (`var/ocr_final`, linha 71 do Markdown): `1233981CE00000001844626I` — **7 zeros** (24 caracteres).
- **Tipo de erro**: **omissão** de um caractere `0` dentro de uma sequência de 8 zeros idênticos consecutivos.
- **Contexto visual**: fonte impressa em negrito, nítida, bem contrastada, sem sobreposição de assinatura/rubrica nessa linha específica — **não é** um caso de baixa legibilidade local.
- **Tamanho/resolução**: mesma página, mesmos ~150 DPI de todo o documento.
- **Redundância no próprio documento**: **sim** — o mesmo valor `1233981CE000000001844626I` está impresso novamente, isolado, logo abaixo do QR Code na página 4 (bloco de verificação de autenticidade e-SAJ, distinto do parágrafo da certidão). A OCR da página 4 (linha 100 do Markdown) produziu `1233981CE000000001844626I` — **8 zeros, correto**, confirmado pela mesma técnica de segmentação (`evidence/p4_selo_CE_correct_zoom.png`).
- **Achado de controle (não solicitado, mas relevante)**: o segundo selo digital do documento — `1233981TE000000009055623E`, referente ao **testamento original** (datado de 26/12/2023, distinto da certidão/cópia de 09/03/2026) — foi conferido pixel a pixel com a mesma técnica e está **exato**: 8 zeros no PDF, 8 zeros na OCR (`evidence/p3_selo_TE_correct_zoom.png`). Ou seja, o erro não é sistemático em todo campo "Selo Digital" da página 3 — é uma falha pontual de uma única ocorrência.
- **Achado de meta-auditoria relevante para a Conclusão**: a validação real anterior (`validate-supervised-ocr-testamento-publico`, 2026-08-12) já havia feito uma comparação visual página a página completa e concluído "selos digitais... todos conferidos e corretos" — **essa conclusão estava incorreta** para esta ocorrência específica. O erro só foi capturado agora, e apenas porque o mesmo dado está redundantemente impresso em dois lugares do documento e a comparação cruzada entre as duas ocorrências expôs a divergência — não pela releitura visual isolada de cada ocorrência (que, isoladamente, "parece" plausível nos dois casos: `...00000001844626I` e `...000000001844626I` diferem por um único caractere numa sequência já longa de zeros, o tipo de erro mais fácil de um revisor humano ou de IA deixar passar por saturação visual).
- **Tentativa de leitura via QR Code / código de barras (checagem independente adicional)**: tentei decodificar programaticamente tanto o QR Code da página 4 quanto o código de barras linear da página 3 (que, por design do e-SAJ, deveriam codificar o mesmo identificador) usando `opencv` (`QRCodeDetector`) e `zxing-cpp`, a partir da imagem JPEG nativa embutida no PDF (não da renderização reamostrada). **Ambos falharam ao decodificar** — a imagem nativa é uma única imagem JPEG de página inteira a ~150 DPI; a região do QR Code equivale a apenas ~250×250px reais (mais compressão JPEG), resolução insuficiente para os módulos finos do QR. Esse resultado é, em si, um achado relevante para a Etapa 3: **não há hoje uma checagem de código de barras/QR viável a partir do scan de origem**, na resolução em que ele é produzido.

### 2.2 `FONE: (14) 3357-[ilegível]` (página 3, com equivalente parcial na página 1) — INCERTA VISUALMENTE

- **Achado**: a linha `FONE: (14) ...` do rodapé **é fisicamente cortada pela margem inferior do scan** — não é uma questão de resolução/nitidez do OCR, é um corte físico do próprio PDF de origem. Confirmado nas páginas 1 e 3 (as únicas onde esse rodapé aparece dentro da área capturada): em ambas, a imagem termina a poucos pixels do topo dos glifos dessa linha — apenas fragmentos ínfimos (poucos pixels de altura, "topos" de caracteres) são visíveis antes do limite inferior da imagem (`evidence/p1_fone_truncated.png`, `evidence/p3_fone_truncated.png`). Não há nenhuma página no documento em que essa linha apareça completa — ou seja, **não existe, no PDF fornecido, nenhuma cópia legível deste dado para servir de redundância** (diferente do caso do selo CE).
- **Avaliação do "3357" transcrito pela OCR**: mesmo o prefixo `3357` que o OCR preservou (antes de marcar o resto como `[ilegível]`) não pôde ser **confirmado com segurança** nesta inspeção visual — os fragmentos de pixel visíveis são compatíveis com múltiplas leituras e insuficientes para uma leitura independente positiva. Isso é diferente de uma alucinação comprovada (não há evidência visual que **contradiga** `3357`), mas também diferente de uma leitura visualmente sustentada — daí a classificação **INCERTA VISUALMENTE**, não DIVERGENTE nem EXATA.
- **Tipo de erro (se houver)**: não classificável com confiança — candidato a **invenção parcial** (o modelo pode ter completado um prefixo plausível de DDD `14` + operadora a partir de um traço mínimo de pixels) ou a uma leitura genuinamente correta de um fragmento real; a evidência disponível no PDF de origem não permite decidir.
- **Contraste com o comportamento correto observado no resto do documento**: a auditoria de 2026-08-12 já havia registrado 6 usos de `[ilegível]` "de forma criteriosa, exatamente onde uma rubrica/assinatura manuscrita sobrepõe o texto impresso ou onde um elemento é puramente gráfico" — ou seja, o mecanismo de marcação de ilegibilidade **existe e funciona** para trechos totalmente inacessíveis. O caso do `FONE` é mais sutil: um trecho **parcialmente** visível (poucos pixels de topo de glifo), onde o comportamento observado foi transcrever um prefixo específico em vez de marcar o campo inteiro como incerto. Isso é uma lacuna de comportamento distinta da omissão de dígito do selo (2.1) — não é um erro de contagem de caracteres repetidos, é uma questão de **quanto de sinal visual mínimo é suficiente para o modelo "se comprometer" com dígitos específicos**.

## ETAPA 3 — Validações candidatas (avaliação, sem implementar)

### A. Validação de formato/checksum

| Método | Classes cobertas | Falsos positivos | Falsos negativos | Risco de alterar conteúdo legítimo |
| --- | --- | --- | --- | --- |
| **Checksum CPF (módulo 11)** | CPF (6/6 no corpus real testados nesta sessão — todos válidos, script Python ad hoc, dígitos verificadores conferidos) | Praticamente zero (algoritmo público, determinístico, sem ambiguidade) | Não-zero, mas baixo: uma troca de dígito que, por coincidência aritmética, ainda produz DV válido não é capturada (ordem de grandeza da literatura: falha em detectar ~9% das trocas de dígito único, quando aplicada isoladamente sem constraints adicionais) | Nenhum, se usada apenas para **sinalizar**, nunca para reescrever o valor |
| **Comprimento fixo do Selo Digital (25 caracteres)** | Selo digital | Zero observado: as 3 ocorrências reais do corpus (TE + CE×2) têm exatamente 25 caracteres quando corretas | Não captura substituição de um dígito por outro dígito válido dentro do comprimento correto (ex.: não teria pego um erro que trocasse `1`→`7` sem alterar a contagem) — mas **teria capturado exatamente o erro real encontrado nesta auditoria** (24 vs. 25 caracteres) | Nenhum, apenas sinalização |
| **Checksum do número de processo (padrão CNJ, Resolução 65/2008, módulo 97 / ISO 7064)** | Número de processo | Não avaliado com confiança — **tentativa de reprodução do algoritmo nesta sessão não bateu** com o dígito verificador real (`85`) usando a ordem de concatenação mais comumente documentada (`NNNNNNN+AAAA+J+TR+OOOO`); não foi possível confirmar a implementação exata sem consultar a especificação oficial completa. **Risco de falso positivo por má implementação do algoritmo é real e não descartado** — não deve ser adotado sem essa confirmação prévia | — | — |
| **Formato CEP (`NNNNN-NNN`)** | CEP | Zero | Alto — não captura troca de dígito válido por outro | Nenhum |
| **RG/CNH** | RG, CNH | N/A | Não há checksum nacional padronizado (varia por SSP/UF); apenas validação de formato/comprimento é possível, com poder discriminativo baixo | Nenhum |

### B. Comparação de valores repetidos no mesmo documento

- **Cobertura real neste documento**: número de processo (4 ocorrências, nativas, já idênticas), código de verificação e-SAJ (4 ocorrências, nativas, já idênticas), e — o caso que efetivamente importa — **Selo Digital CE** (2 ocorrências OCR'adas independentemente, p.3 e p.4). Foi exatamente essa comparação, feita manualmente nesta sessão, que expôs a divergência da Etapa 2.1.
- **Falsos positivos**: baixo — se duas leituras independentes do mesmo dado divergem, isso é um sinal real (a menos que o dado *deva* legitimamente diferir, ex.: os dois selos digitais distintos deste documento, TE vs. CE, que **não** devem ser comparados entre si).
- **Falsos negativos**: alto para o documento como um todo — a maioria dos dados críticos (CPFs, RGs, matrículas, valores, o próprio FONE) aparece **uma única vez** no documento; não há redundância a explorar para eles.
- **Risco de alterar conteúdo legítimo**: nenhum, se usada apenas para sinalizar divergência entre ocorrências supostamente idênticas — mas **exige um mapeamento prévio de quais campos são esperados como redundantes** por tipo/seção de documento; não é uma checagem genérica "de graça".

### C. Detecção de divergência entre OCR e texto nativo residual

- **Cobertura real neste documento**: muito baixa. `page.get_text()` (PyMuPDF) retorna apenas 386 caracteres nativos por página — exclusivamente o rodapé de verificação e-SAJ (idêntico nas 4 páginas), que já é tratado corretamente pela rota `hibrido` (reproduzido no Markdown byte a byte). **Nenhum outro dado crítico deste documento tem camada de texto nativo residual** para servir de contraponto — CPFs, RGs, selos digitais e todo o corpo do testamento existem apenas como imagem.
- **Conclusão**: método de baixo valor para documentos totalmente escaneados como este; só se aplica quando há coexistência de texto nativo parcial e imagem na mesma região, o que não é o caso aqui além do rodapé já validado.

### D. Regras de comprimento/padrão

- Mesma avaliação da linha "Comprimento fixo do Selo Digital" em A — é, na prática, a validação de maior custo-benefício encontrada nesta auditoria: **barata, sem falso positivo observado, e teria detectado o único erro real confirmado**.
- CPF (11 dígitos), CEP (8 dígitos) já têm formato regular esperado; útil como guarda de sanidade mínima, mas não substitui checksum.

### E. Marcação para revisão quando não houver confirmação determinística

- O pipeline **já implementa** esse princípio parcialmente via o marcador `[ilegível]`, usado de forma criteriosa (confirmado na auditoria de 2026-08-12) quando um trecho está **totalmente** inacessível (rubrica sobreposta, elemento gráfico).
- **Lacuna identificada nesta sessão** (caso 2.2, `FONE`): quando um trecho está **parcialmente** visível (poucos pixels de sinal, fisicamente cortado pela borda do scan), o comportamento observado foi produzir um prefixo específico plausível em vez de marcar o campo inteiro como incerto. Isso não foi objeto de alteração aqui (mudar esse comportamento envolveria o prompt, explicitamente fora de escopo deste `/goal`), mas é um candidato relevante para uma futura mudança de prompt/pipeline — a ser tratado em mudança própria, nunca nesta.

## ETAPA 4 — Responsabilidade (classificação, sem gerar YAML)

| Achado / candidato de validação | Classificação | Justificativa |
| --- | --- | --- |
| Checagem de comprimento fixo do Selo Digital (25 caracteres) | **A. Pipeline determinístico** | Regra mecânica, sem necessidade de julgamento; naturalmente uma extensão do módulo `validator.py` já existente no projeto (hoje descrito como responsável por "validar marcadores, conteúdo, hashes"). |
| Checksum CPF (módulo 11) | **A. Pipeline determinístico** | Mesmo raciocínio; algoritmo público e determinístico. |
| Comparação de valores redundantes intra-documento (ex. selo digital repetido) | **A. Pipeline determinístico**, com componente de **B. camada de validação pós-OCR** | Mecânico depois de mapeado quais campos são redundantes por tipo de documento; esse mapeamento em si é uma decisão de design (não de julgamento por documento), portanto ainda determinístico, mas de escopo maior que uma checagem isolada. |
| Checksum CNJ do número de processo | **A/B, condicionado** | Só deve avançar para implementação após confirmação da especificação oficial exata do dígito verificador — tentativa nesta sessão não validou o algoritmo. Tratar como spike de pesquisa antes de virar regra determinística. |
| Decidir se um valor sinalizado (ex. divergência entre duas leituras do mesmo selo) deve ser corrigido automaticamente para a versão "mais provável" | **D. Revisão humana obrigatória** — nunca C nem A | O projeto já proíbe explicitamente autocorreção/invenção de dados (`AGENTS.md`, `--allow-partial` é o único modo que permite publicar `[ilegível]`); mesmo com redundância apontando para um valor, a decisão de publicar uma correção em um documento com valor jurídico probatório não deve ser automática. |
| Avaliar se um trecho parcialmente visível (tipo `FONE`) deveria ter sido marcado como incerto em vez de parcialmente transcrito | **C. Revisor semântico por IA** (arquitetura já planejada, Fase 2, `docs/Pipeline_Conversao_Juridica_Corrigido.md` §20 — não implementada) e, no limite, **D. Revisão humana** | Exige julgamento contextual sobre "quanto sinal visual é suficiente para se comprometer com um dígito", não uma regra mecânica; alinhado à camada semântica já prevista e ainda não implementada, mencionada em `LOOPS.md` (decisão arquitetural de 2026-08-10 sobre Papel/Nome). |
| RG/CNH sem checksum nacional | **D. Revisão humana obrigatória** (quando o processo exigir alta confiança) | Não há validação determinística de alto poder discriminativo disponível; camada semântica também não resolveria (não há como uma IA "confirmar" um RG sem uma fonte externa). |

## Meta-achado transversal (o mais importante desta auditoria)

A comparação visual humana/manual anterior, já arquivada e documentada como cuidadosa (`validate-supervised-ocr-testamento-publico`, 2026-08-12), declarou os selos digitais "todos conferidos e corretos" — e essa conclusão estava incorreta para a ocorrência da página 3. O erro só foi exposto nesta sessão porque (a) o mesmo dado calha de estar redundantemente impresso em outro ponto do documento, e (b) essa redundância foi explorada deliberadamente por comparação cruzada, não por releitura visual isolada de cada ocorrência.

Isso é evidência direta e concreta, com um caso real, de que **revisão visual isolada — humana ou por IA semântica — não é suficiente, sozinha, para garantir fidelidade de dados críticos em identificadores longos com dígitos repetidos**. Validação determinística (comprimento, checksum, comparação de redundância) não é uma camada opcional/complementar nesse cenário: é a única categoria de checagem que, neste caso real, efetivamente teria pego o erro sem depender de sorte de layout (a existência de uma segunda cópia do mesmo dado).

## Fora do escopo desta investigação

Implementação de qualquer validação; alteração de prompt/modelo/provider; nova chamada OCR/LLM; correção do Markdown já produzido; arquivamento; push; pesquisa aprofundada do algoritmo oficial do dígito verificador CNJ (apenas uma tentativa rápida foi feita, sem sucesso, registrada em Etapa 3.A como limitação, não como conclusão definitiva de inviabilidade).
