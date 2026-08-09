## Why

A primeira página editorial de `Inf0024E.pdf` (e somente ela, no corpus de 4 PDFs) tem elementos estruturalmente distintos — título editorial estilizado ("Informativo" / "de Jurisprudência", 26pt), a linha de edição/data ("Informativo de Jurisprudência n. 24 - Edição Extraordinária ... 28 de janeiro de 2025"), o ramo do direito ("Direito Penal"), o aviso editorial ("Este periódico destaca teses...") e o cabeçalho de câmara julgadora ("CORTE ESPECIAL") — todos colapsados em uma única linha corrida no Markdown final:

```
Informativo de Jurisprudência Informativo de Jurisprudência n. 24 - Edição Extraordinária 28 de janeiro de 2025 Direito Penal Este periódico destaca teses jurisprudenciais e não consiste em repositório oficial de jurisprudência. CORTE ESPECIAL
```

**Esta mudança é SOMENTE DIAGNÓSTICO** — nenhuma correção, teste de produção, arquivamento ou push foi realizado. `git status` permanece limpo além dos artefatos desta mudança (`openspec/changes/fix-editorial-cover-structural-boundaries/`).

## Conclusão do diagnóstico

**Causa raiz comprovada e primeiro estágio da fusão identificado com precisão** (ver `design.md` para a evidência completa, rastreada estágio a estágio). Um candidato de correção geral, determinístico e de blast radius extremamente baixo (3 de ~241 páginas do corpus) foi encontrado e validado empiricamente contra os 4 PDFs — mas ele **não é 100% isolado** ao defeito desta mudança: nas outras 2 páginas que ele afeta, o candidato também altera (corrigindo, não corrompendo) dois casos que pertencem ao achado pendente `Papel/Nome`, já documentado e duas vezes investigado sem critério seguro encontrado (`openspec/changes/archive/2026-08-07-fix-role-name-list-cross-block-fusion/`).

Por isso a conclusão é **A condicional**: existe um critério seguro e geral para o defeito desta mudança especificamente, mas sua implementação, tal como encontrada, requer uma decisão humana explícita sobre como tratar a sobreposição com o território já fechado de `Papel/Nome` — não é uma implementação "limpa" de um único defeito isolado. Nenhuma implementação foi feita; ver "Próximos passos possíveis" em `design.md`.

## Causa raiz (resumo — detalhes completos em `design.md`)

`recompose_native_paragraphs` (`src/pipeline_juridico/cleaner.py`) estima a posição vertical de cada linha física de um bloco PyMuPDF dividindo a altura total do bloco pelo número de linhas físicas **não-vazias** (`line_height = (y1 - y0) / len(physical_lines)`, após filtrar linhas em branco via `if line.strip()`). Quando um bloco contém linhas físicas em branco intercaladas com o conteúdo real — um padrão de espaçamento vertical usado neste PDF especificamente na capa, mas não específico deste arquivo em sua forma (blocos com linhas em branco dentro de um único frame de texto) — a altura de cada linha real fica catastroficamente distorcida, porque o divisor (contagem de linhas não-vazias) não reflete o numerador (altura total do bloco, que ainda inclui o espaço das linhas em branco descartadas). Em um caso extremo desta página (bloco com 7 linhas em branco + 2 linhas reais), isso produz um "gap" negativo entre o título e a linha de edição/data — uma junção estruturalmente inevitável, não apenas provável.

Confirmado que a extração nativa (MarkItDown/pdfminer) **já produz a separação correta** nesta página — o defeito é introduzido inteiramente dentro de `recompose_native_paragraphs`, que descarta essa segmentação correta em favor de sua própria reconstrução geométrica (defeituosa).

## Sinal discriminante e candidato avaliado

**Candidato aceito como mais promissor**: corrigir a interpolação de `line_height` para dividir pelo número TOTAL de linhas físicas do bloco (incluindo as em branco), preservando o índice original de cada linha real ao posicioná-la — em vez de dividir apenas pelas linhas sobreviventes após o filtro. Validado por simulação completa (função real `recompose_native_paragraphs`, com essa única alteração, rodada página a página nos 4 PDFs): produz diferença em exatamente 3 das ~241 páginas do corpus. Uma delas é o defeito-alvo desta mudança (corrigido integralmente, sem nenhum efeito colateral na mesma página). As outras duas (`AINTARESP_1462304-PA.pdf` p.11, `REsp_1704551-SP.pdf` p.2) share o mesmo mecanismo de causa raiz mas caem dentro do território já documentado de `Papel/Nome`.

**Candidatos descartados** (blast radius medido, ver `design.md`): substituir a interpolação por geometria real de linha em todo o pipeline (mesmo candidato já descartado na investigação de `SAIBA MAIS`, 44 decisões de junção alteradas); usar mudança de fonte/tamanho/cor como sinal de fronteira (91 de 329 junções atualmente corretas seriam quebradas, incluindo continuações legítimas de frase com ênfase em negrito ou citações em corpo menor).

## Fora do escopo (confirmado, não tocado nesta investigação)

`Papel/Nome`, `RECURSO / ESPECIAL`, `SAIBA MAIS`, thin-space, rodapés técnicos, `SUBTÍTULO`, índice, R01 — nenhum código foi alterado; nenhum teste de produção foi criado. Extrator, roteamento, OCR e dependências não foram tocados nem avaliados para alteração.

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
(nenhuma — diagnóstico apenas, nenhuma implementação)

## Impact

- Nenhum código de `src/` ou `tests/` foi alterado. Todos os scripts de investigação foram executados fora do repositório versionado (`/tmp/.../scratchpad/`).
- Achado registrado em `LOOPS.md` (após aprovação deste relatório), incluindo a sobreposição com `Papel/Nome` identificada, para que uma tentativa futura de implementação não precise refazer esta investigação.
