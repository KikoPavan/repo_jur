# Repository Implementation Map — Stage 0

Mudança: `audit-repository-implementation-map`. Diagnóstico exclusivo do estado físico real de `repo_jur` em 2026-08-15, HEAD `e1329aa` (branch `main`). Nenhum código, teste, configuração ou diretório foi criado, movido ou alterado por esta investigação.

## 0. Precheck

- **Branch / HEAD:** `main` @ `e1329aa53b221c054b0eeed10dfb97f6259091fe`.
- **`git status --short --untracked-files=all` (antes desta mudança):** apenas os 2 artefatos pré-existentes não rastreados de sempre — `var/ocr_final/logs/012-015-Testamento Publico.report.json` e `var/ocr_final/output/012-015-Testamento Publico.md` (execução real de 2026-08-14, anterior a qualquer investigação recente; não gerados por esta tarefa).
- **OpenSpec ativo:** nenhum (`openspec list` → "No active changes found" antes de esta mudança ser criada).
- **Baseline da suíte:** `uv run pytest tests/` → **391 passed**, 0 failed.
- **Baseline OpenSpec:** `openspec validate --all --strict` → **1 passed**, 0 failed (`spec/juridical-pdf-conversion`).
- **`pyproject.toml`:** projeto `repo-jur`, Python `>=3.12`, gerenciado por `uv`/hatchling, layout `src/pipeline_juridico`. Dependências: `google-genai`, `markitdown-ocr`, `markitdown[all]`, `openai`, `pillow`, `pymupdf`, `python-dotenv`. Dev: `pytest`, `pytest-cov`. Entry point único: `converter-juridico = "pipeline_juridico.cli:main"`.
- **`.env.example`:** `INPUT_DIR`, `OUTPUT_DIR`, `LOGS_DIR`, `TEMP_DIR`, `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_BASE_URL`, `OCR_ENABLED`, `OCR_PROMPT_FILE`, `NATIVE_MIN_TEXT_CHARS`, `FULL_PAGE_IMAGE_MIN_RATIO`, `SIGNIFICANT_IMAGE_MIN_RATIO` (nenhum valor de segredo lido ou registrado).
- **`/bundle/`:** não existe no repositório — nada a preservar/evitar nesta árvore.

## 1. Árvore física relevante (real, não a de nenhum diagrama)

```
repo_jur/
├── src/pipeline_juridico/        # único pacote de produção (2421 linhas, 11 módulos)
│   ├── cli.py                    # entrypoint converter-juridico
│   ├── config.py                 # RoutingConfig
│   ├── inspector.py              # abertura/validação de PDF, isolamento de páginas, hash de origem
│   ├── router.py                 # roteamento de MÉTODO de conversão por página
│   ├── engines.py                # fábricas MarkItDown nativo / OCR (cliente OpenAI-compatible)
│   ├── converter.py              # orquestração de conversão, composição, deduplicação geométrica
│   ├── cleaner.py                # limpeza/recomposição determinística de Markdown
│   ├── validator.py              # gate de qualidade Fase 1 (encoding, marcadores, conteúdo)
│   ├── report.py                 # contrato/serialização do relatório técnico JSON
│   ├── hashing.py                # SHA-256 utilitário + info de runtime
│   └── models.py                 # dataclasses: Relatorio, FonteInfo, SaidaInfo, OcrInfo, etc.
├── tests/                        # 14 arquivos, 1:1 com os módulos acima + acceptance/layout
├── prompts/ocr_literal_ptbr.txt  # prompt de OCR versionado
├── docs/Pipeline_Conversao_Juridica_Corrigido.md  # única baseline arquitetural commitada (Fase 1 completa + Fase 2 planejada §20)
├── openspec/
│   ├── specs/juridical-pdf-conversion/spec.md     # única spec normativa existente
│   └── changes/archive/                            # 21 mudanças arquivadas (2026-07-27 → 2026-08-15)
├── input/, output/, logs/, var/tmp/                # E/S da CLI (canônicos + corpus de auditoria)
├── var/ocr_final/                                  # artefato pré-existente não rastreado (não tocado)
└── LOOPS.md, AGENTS.md, CLAUDE.md, CHANGELOG.md, README.md
```

Não existe, em lugar nenhum do repositório: `pipeline/`, `shared_conversion/`, `ingress/`, `preflight/`, `domain_router/` (distinto de `router.py`), `legal/`, `process/`, `retrieval/`, `chunking/`, `storage/`, `/bundle/`. Nenhum desses diretórios foi criado por esta investigação — sua ausência é o próprio achado.

## 2. Achado transversal — divergência entre "baseline FROZEN" e estado físico real

A instrução desta tarefa presume a existência de baselines FROZEN vigentes cobrindo termos como `ITP`, `Preflight`, `Evidence Preservation`, `Shared Conversion Core`, `ConversionEngine`, `Domain Router`, `Legal Semantic Review`, `Legal Producer`, `Process Semantic Review`, `Process Producer`, `Process Storage`, `Legal Knowledge Retrieval`, `chunking/reranking`. Busca textual (`grep -ri`) por esses termos em todo o repositório (excluindo `.venv`, `node_modules`, `.git`) **não encontrou nenhuma ocorrência** em nenhum arquivo de documentação, spec ou config deste repositório. A única baseline arquitetural commitada em `repo_jur` é `docs/Pipeline_Conversao_Juridica_Corrigido.md`, que documenta integralmente a Fase 1 (conversão determinística PDF→Markdown, implementada) e, na §20, uma única camada futura ("revisor semântico por IA" + "YAML Frontmatter", ambos "planejado, não implementado") — sem nomear nenhuma das 23 capacidades lógicas desta tarefa por esses termos, e sem cobrir Domain Router, Legal/Process Producer, Process Storage, Legal Knowledge Retrieval ou chunking/reranking em nenhuma forma.

**Conclusão do achado:** a baseline FROZEN referenciada por esta tarefa é externa a este repositório (não está commitada em `repo_jur`). O mapeamento abaixo trata cada capacidade lógica pelo nome fornecido na tarefa e localiza o equivalente físico mais próximo já existente, sem presumir nenhum path documental — exatamente a regra principal desta tarefa (`INSPECT → REUSE → ADAPT IN PLACE → CREATE somente se realmente ausente`).

## 3. Tabela principal

| # | Capacidade lógica | Implementação física encontrada | Ação | Testes existentes | Lacuna | Justificativa |
|---|---|---|---|---|---|---|
| 1 | ITP / Ingress | `cli.py::main` (parsing de argv, `.env`, resolução de paths) + `inspector.py::validate_pdf_path`/`open_pdf` | ADAPT | `test_cli.py`, `test_inspector.py` | Sem estágio de ingresso formal separado do parsing de CLI; termo "ITP" não definido em nenhum documento do repo | Funcionalidade de ingresso (validação de caminho, arquivo, leitura de `.env`) já existe e é exercida em todo teste de aceitação; falta apenas nomear/isolar como estágio formal |
| 2 | Preflight | `inspector.open_pdf` (checa criptografia/páginas vazias), `RoutingConfig.from_env().__post_init__` (valida limites de roteamento) | ADAPT | `test_inspector.py`, `test_config.py` | Checagens existem inline no caminho de conversão, não como etapa nomeada e isolada antes do processamento | Pré-condições reais (PDF válido, não criptografado, não vazio; config de roteamento coerente) já são verificadas e falham cedo com exceções tipadas |
| 3 | official receiver SHA-256 | `hashing.sha256_file`/`sha256_bytes`, `inspector.inspect_source` → `FonteInfo.sha256`; `SaidaInfo.sha256` para a saída | REUSE | `test_hashing.py`, `test_inspector.py`, `test_report.py` | Nenhuma | Hash SHA-256 do PDF de origem é calculado no recebimento e registrado no relatório técnico; hash da saída também é registrado |
| 4 | Evidence Preservation | Princípio "pipeline não destrutivo" (§3 do doc), `inspector.isolated_page_workspace` (cópias isoladas por página, `--keep-temp` opcional), `validator.write_atomic` | ADAPT | `test_inspector.py`, `test_validator.py` | Preservação hoje é "não alterar o PDF de origem + escrita atômica de saída + hash no relatório", não um repositório de evidências com retenção/cadeia de custódia formal | As garantias centrais (fonte nunca é escrita, saída só é publicada após validação completa, hash de ambos registrado) já existem; um módulo de evidência dedicado seria uma extensão, não uma criação do zero |
| 5 | Shared Conversion Core | `src/pipeline_juridico/` inteiro (`converter.py` + `cleaner.py` + `engines.py` + `router.py`), único caminho de conversão usado por toda a CLI | REUSE | Toda a suíte de `tests/test_{converter,converter_integration,cleaner,engines,router}.py` | Nenhuma | O núcleo de conversão já é compartilhado por definição (um único pacote, um único entrypoint); **regra especial desta tarefa proíbe explicitamente criar `pipeline/shared_conversion/` só para casar com diagrama** — o alvo lógico já está fisicamente satisfeito sob outro nome |
| 6 | `ConversionEngine` / interface equivalente | `converter.py::convert_document` (orquestração completa) + `engines.py::create_native_engine`/`create_ocr_engine` (fábricas que retornam `MarkItDown` configurado) | ADAPT | `test_converter.py`, `test_converter_integration.py`, `test_engines.py` | Não existe classe/protocolo abstrato nomeado `ConversionEngine`; hoje há duas funções de fábrica concretas, não uma interface plugável | Equivalente funcional completo já existe e é testado; formalizar uma interface só se justificaria se um segundo motor de conversão (além de MarkItDown nativo/OCR) precisasse ser plugado — não há essa necessidade hoje |
| 7 | MarkItDown / markitdown-ocr | Dependências declaradas em `pyproject.toml`; `engines.py::create_native_engine` (`enable_plugins=False`) e `create_ocr_engine` (`enable_plugins=True`, `llm_client`) | REUSE | `test_engines.py` | Nenhuma | Motor principal e plugin de OCR já integrados exatamente como a única baseline commitada (`docs/...md` §7, §13) descreve |
| 8 | Gemini/OpenAI-compatible client | `engines.py::create_ocr_engine` (`openai.OpenAI(api_key=..., base_url=...)`), `cli.py::GEMINI_OPENAI_BASE_URL` | REUSE | `test_engines.py`, `test_cli.py` | Nenhuma | Cliente Gemini via endpoint OpenAI-compatible já configurado; nomenclatura de env vars é `GEMINI_*` (decisão já registrada em memória de projeto, diverge intencionalmente de um padrão `OCR_API_KEY`/`OCR_BASE_URL` genérico) |
| 9 | OCR routing | `router.py::route_page` + `inspect_native_text`/`inspect_raster_content`, `RoutingConfig` | REUSE | `test_router.py`, `test_config.py` | Nenhuma | Classificação `texto_nativo`/`hibrido`/`ocr_integral`/`vazia` por página já implementada e testada; **ver risco de nomenclatura na seção 6** — este módulo não deve ser confundido com a capacidade lógica 14 (Domain Router) |
| 10 | page markers | `converter.py::format_page_marker` (`[[Pág. N]]`), `validator.py::validate_page_markers` | REUSE | `test_converter.py`, `test_validator.py` | Nenhuma | Marcador canônico único e sequencial já implementado e validado em toda a suíte de aceite |
| 11 | Technical JSON/report | `report.py` (`build_report_json`, `validate_report_contract`, `schema_version="1.0"`), `models.py::Relatorio` e dataclasses aninhadas | REUSE | `test_report.py`, `test_models.py` | Nenhuma | Relatório técnico versionado, com contrato validado antes da escrita, já existe e cobre origem, saída, runtime, OCR, timing e páginas |
| 12 | Post-OCR Critical-Data Validation | Nenhuma implementação dedicada; `validator.py` cobre apenas integridade estrutural (encoding, marcadores, conteúdo vs. relatório) | CREATE | Nenhum | Total — nenhum checksum de identificador, nenhuma checagem de comprimento de selo, nenhuma comparação de valor redundante intra-documento | Busca confirmada em `validator.py`, `cleaner.py`, `report.py`: nenhuma função trata dado crítico (CPF, selo digital, etc.) especificamente. Esta lacuna já foi confirmada e documentada em detalhe pela auditoria arquivada nesta mesma sessão (`openspec/changes/archive/2026-08-15-audit-ocr-critical-data-fidelity/`, commit `4759696`): 1 divergência real de selo digital não capturada por nenhum mecanismo existente |
| 13 | Phase 1 Quality Gate | `validator.py` completo (`validate_encoding_and_line_endings`, `validate_page_content`, `validate_markdown_matches_report`, `validate_page_markers`), `cleaner.py::ensure_illegible_marker_authorized`, `report.py::validate_report_contract` — todos invocados em `cli.py::main` antes de `write_atomic` | REUSE | `test_validator.py`, `test_report.py`, `test_cli.py`, `test_acceptance.py` | Nenhuma | Gate de qualidade da Fase 1 já é exatamente esta cadeia de validações, documentada nas §9/§10 da baseline commitada, e é exercida ponta a ponta pela suíte de aceite |
| 14 | Domain Router | Nenhuma implementação — nenhum componente classifica um documento já convertido como domínio "Legal" vs. "Processual" | CREATE | Nenhum | Total | `router.py` existente roteia MÉTODO de conversão por página (texto_nativo/hibrido/ocr_integral/vazia), não DOMÍNIO do documento; confirmado por leitura completa de `router.py` — não há nenhuma lógica de classificação por tipo de peça jurídica em lugar nenhum do pacote |
| 15 | Legal Semantic Review | Nenhum código; arquitetura e 9 regras já planejadas em `docs/...md` §20 ("Fase 2, planejada, não implementada"), motivadas pelo achado Papel/Nome (`openspec/changes/archive/2026-08-07-fix-role-name-list-cross-block-fusion/`) | CREATE | Nenhum | Total (implementação); planejamento arquitetural já existe | A própria baseline commitada já rotula esta capacidade como não implementada — corrobora, não contradiz, esta classificação |
| 16 | Legal Producer | Nenhum código; §20.3 menciona "geração/extração de YAML Frontmatter" como etapa futura, também não implementada | CREATE | Nenhum | Total | Nenhum módulo produz um artefato "Legal" final além do Markdown fiel + relatório JSON já cobertos pelas capacidades 5–13 |
| 17 | Process Semantic Review | Nenhum código; nenhuma menção em `docs/...md` (que só planeja revisão semântica para o lado Legal, §20) | CREATE | Nenhum | Total — inclusive de decisão arquitetural, que ainda não existe para o lado Processual | Diferente da capacidade 15, esta nem tem arquitetura planejada na baseline commitada; precisaria de sua própria decisão arquitetural antes de qualquer mudança OpenSpec de implementação |
| 18 | Process Producer | Nenhum código | CREATE | Nenhum | Total | Mesma ausência da capacidade 16, sem nenhum planejamento prévio documentado |
| 19 | Process Storage | Nenhum código; `output/`/`logs/` são diretórios planos genéricos da CLI de conversão, sem separação por domínio | CREATE | Nenhum | Total | Nenhuma camada de armazenamento/indexação específica para processos judiciais existe; `output/`/`logs/` servem qualquer PDF convertido, Legal ou não |
| 20 | Legal Knowledge Retrieval | Nenhum código — nenhuma dependência de vetor/busca em `pyproject.toml`, nenhum módulo de indexação | CREATE | Nenhum | Total | Confirmado por ausência de dependências relevantes (`pyproject.toml` lista somente as 7 dependências de conversão) e ausência de qualquer módulo de busca/índice em `src/` |
| 21 | chunking/reranking | Nenhum código | CREATE | Nenhum | Total | Mesma confirmação da capacidade 20; nenhuma função de segmentação de texto para recuperação (distinta da segmentação de página/bloco já usada internamente pelo conversor) existe |
| 22 | observability/logging | `cli.py` (`logging.basicConfig`, `logger.error` com `_sanitize_log_message` — redação de segredos + truncamento em 500 chars), `report.py::TimingInfo`/`build_runtime_info` (duração e versões de runtime por execução) | ADAPT | `test_cli.py` | Sem agregação centralizada de logs, sem métricas/tracing distribuído; observabilidade hoje = log local por execução + timing no relatório JSON | Log estruturado básico com redação de segredos já existe e é testado (princípio "nunca registrar segredos" da baseline, §14, já cumprido); um estágio de observability completo (métricas, tracing) seria extensão, não criação do zero |
| 23 | schemas/contracts comuns, Legal e Process | `report.py::validate_report_contract` + `models.py` (dataclasses `Relatorio`, `FonteInfo`, `SaidaInfo`, `OcrInfo`, `TimingInfo`, `ResultadoPagina`) | ADAPT | `test_report.py`, `test_models.py` | Contrato existente é único e agnóstico de domínio (aplica-se a qualquer PDF convertido); não há schema separado para "Legal" vs. "Process" porque a capacidade 14 (Domain Router) que os distinguiria ainda não existe | O único contrato/schema real do repositório já é versionado (`schema_version`) e validado antes de cada escrita; uma eventual separação Legal/Process dependeria logicamente da capacidade 14 existir primeiro |

**Nota adicional (regra especial da tarefa, fora da numeração 1–23):** a instrução desta tarefa marca explicitamente `Judicial Process Retrieval` como `OUT_OF_SCOPE`. Nenhuma implementação foi encontrada nem investigada para essa capacidade — classificação aplicada exatamente como instruído, sem inspeção adicional.

## 4. Capacidades por estado

- **Completas (REUSE):** 3 (receiver SHA-256), 5 (Shared Conversion Core), 7 (MarkItDown/markitdown-ocr), 8 (cliente Gemini/OpenAI-compatible), 9 (OCR routing), 10 (page markers), 11 (Technical JSON/report), 13 (Phase 1 Quality Gate). — **8 de 23**, todas correspondentes integralmente à Fase 1 já implementada e coberta pela suíte `391/391`.
- **Parciais (ADAPT):** 1 (ITP/Ingress), 2 (Preflight), 4 (Evidence Preservation), 6 (ConversionEngine/interface), 22 (observability/logging), 23 (schemas/contracts comuns). — **6 de 23**, todas com funcionalidade real subjacente, mas sem a formalização/nomenclatura/generalização que a capacidade lógica describe.
- **Ausentes (CREATE):** 12 (Post-OCR Critical-Data Validation), 14 (Domain Router), 15 (Legal Semantic Review), 16 (Legal Producer), 17 (Process Semantic Review), 18 (Process Producer), 19 (Process Storage), 20 (Legal Knowledge Retrieval), 21 (chunking/reranking). — **9 de 23**, nenhuma com implementação equivalente identificável no repositório.
- **Fora de escopo (OUT_OF_SCOPE):** Judicial Process Retrieval, por instrução explícita da tarefa.

## 5. Overlaps e duplicações já existentes

- **Nenhuma duplicação de implementação foi encontrada** — cada capacidade REUSE/ADAPT mapeia para exatamente um módulo/função, sem lógica paralela concorrente.
- **Risco de colisão de nomenclatura (não uma duplicação real, mas um risco documentado):** `src/pipeline_juridico/router.py` já existe e é publicamente referenciado em toda a base de código e testes como o roteador de **método de conversão por página**. Se uma futura mudança OpenSpec para a capacidade 14 (Domain Router) criar um arquivo/classe também chamado apenas "router" sem qualificação, haverá ambiguidade de nome imediata dentro do mesmo pacote — recomenda-se, na mudança futura que implementar a capacidade 14, um nome explicitamente distinto (ex. `domain_router.py`, nunca `router.py` reaproveitado ou duplicado).

## 6. Riscos de arquitetura caso módulos paralelos sejam criados

1. **Criar uma árvore `pipeline/shared_conversion/` paralela a `src/pipeline_juridico/`** duplicaria o núcleo de conversão já testado (2421 linhas, 391 testes) sem necessidade — a regra especial desta tarefa já proíbe isso explicitamente, e esta investigação confirma que não há nenhuma justificativa técnica para tal duplicação: o pacote existente já cumpre integralmente o papel lógico de "Shared Conversion Core".
2. **Criar uma segunda função de hashing/relatório** para as futuras capacidades Legal/Process (16/18/19) sem reaproveitar `hashing.py`/`report.py`/`models.py` fragmentaria o contrato técnico único hoje existente (capacidade 23) — qualquer extensão Legal/Process deveria estender `Relatorio`/`validate_report_contract`, não recriá-los.
3. **Implementar Domain Router (14) sem revisar `router.py` existente** cria risco real de confusão de responsabilidade (roteamento de método de página vs. roteamento de domínio de documento) — ver seção 5.
4. **Implementar Post-OCR Critical-Data Validation (12) fora de `validator.py`** fragmentaria o gate de qualidade Fase 1 em dois pontos de decisão de publicação (estrutural em `validator.py`, crítico em outro lugar) — o achado da auditoria arquivada `audit-ocr-critical-data-fidelity` já recomenda `validator.py`/relatório JSON como extensão natural, não um módulo novo isolado.
5. **Qualquer criação de diretório `legal/`/`process/` antes de uma decisão arquitetural equivalente à §20 (hoje só existe para o lado Legal)** repetiria, para o lado Process, o mesmo erro que a decisão de 2026-08-10 já evitou para o lado Legal (tentar resolver semântica com heurística geométrica antes de uma camada dedicada) — recomenda-se que a capacidade 17 (Process Semantic Review) receba sua própria seção de decisão arquitetural, análoga à §20, antes de qualquer código.

## 7. Divergências entre baseline FROZEN e estado físico real

Ver seção 2 (achado transversal). Resumo: a baseline FROZEN referenciada por esta tarefa (com a terminologia ITP/Ingress, Preflight, Evidence Preservation, Domain Router, Legal/Process Producer, Process Storage, Legal Knowledge Retrieval, chunking/reranking) **não está commitada em `repo_jur`**; a única baseline arquitetural física é `docs/Pipeline_Conversao_Juridica_Corrigido.md`, que cobre integralmente a Fase 1 e apenas uma fração da Fase 2 (revisão semântica Legal + YAML Frontmatter, ambos "planejado, não implementado"). Qualquer mudança OpenSpec futura que implemente as capacidades 14–21 precisará **primeiro** registrar sua própria decisão arquitetural nesse documento (ou em um equivalente), seguindo o precedente já estabelecido pela §20.

## 8. Cobertura de testes existente

`391/391` testes passam na baseline desta investigação, distribuídos 1:1 com os módulos REUSE/ADAPT: `test_cli.py`, `test_config.py`, `test_engines.py`, `test_hashing.py`, `test_inspector.py`, `test_models.py`, `test_report.py`, `test_router.py`, `test_validator.py`, `test_cleaner.py`, `test_converter.py`, `test_converter_integration.py`, mais `test_acceptance.py` (ponta a ponta sobre o corpus canônico) e `test_project_layout.py` (estrutura de diretórios/arquivos obrigatórios). Nenhum teste existe, nem poderia existir hoje, para as 9 capacidades `CREATE` — não há código a testar.

## 9. Lacunas de testes (registradas, nenhum teste novo criado nesta tarefa)

- Nenhum teste cobre validação de dado crítico pós-OCR (capacidade 12) — consistente com sua ausência de implementação.
- Nenhum teste cobre classificação de domínio de documento (capacidade 14).
- Nenhum teste cobre observabilidade além da redação de segredos em log (`test_cli.py`) — não há teste de timing/duração do relatório isoladamente (`TimingInfo` é coberto indiretamente via `test_report.py`/`test_acceptance.py`, não testado por si só quanto a precisão).
- `test_project_layout.py` fixa a existência de `input/`, `output/`, `logs/`, `var/tmp/` e `.env.example` com chaves específicas — qualquer capacidade futura que precise de novos diretórios físicos (ex. armazenamento Process) precisará estender esse teste deliberadamente, não presumir que a estrutura atual já comporta.

## 10. Dependências entre capacidades

```
1 ITP/Ingress → 2 Preflight → 9 OCR routing → {7 MarkItDown/OCR, 8 cliente Gemini} → 6 ConversionEngine
                                            └→ 5 Shared Conversion Core → 10 page markers → 13 Phase 1 Quality Gate → 11 Technical JSON/report
13 Phase 1 Quality Gate → 12 Critical-Data Validation (futuro, estende 13)
5 Shared Conversion Core → 14 Domain Router (futuro) → {15 Legal Semantic Review, 17 Process Semantic Review}
15 Legal Semantic Review → 16 Legal Producer → 20 Legal Knowledge Retrieval → 21 chunking/reranking
17 Process Semantic Review → 18 Process Producer → 19 Process Storage
3 receiver SHA-256, 4 Evidence Preservation, 22 observability/logging, 23 schemas/contracts → transversais a todas as capacidades acima
```

A capacidade 14 (Domain Router) é a bifurcação estrutural: nada em 15–21 (lado Legal) ou 17–19 (lado Process) pode ser implementado de forma coerente sem ela existir primeiro, pois é ela quem decidiria qual documento segue qual ramo.

## 11. Ordem recomendada das futuras mudanças OpenSpec

1. **Post-OCR Critical-Data Validation (12)** — maior prioridade: já tem achado real confirmado (selo digital), critério de baixo custo já identificado (comprimento fixo + checksum CPF), extensão natural de `validator.py` já existente; nenhuma dependência de capacidade ainda ausente.
2. **Domain Router (14)** — pré-requisito estrutural para todo o resto (15–19); deve vir antes de qualquer trabalho Legal ou Process de nível semântico, exatamente porque bifurca o fluxo.
3. **Legal Semantic Review (15)** — já tem arquitetura e 9 regras pré-planejadas na baseline commitada (§20); menor risco de retrabalho por já ter sido pensada.
4. **Process Semantic Review (17)** — precisa primeiro de uma decisão arquitetural própria (análoga à §20), ainda inexistente; só depois de (2) e com essa decisão registrada.
5. **Legal Producer (16)** e **Process Producer (18)** — dependem de (3)/(4) respectivamente já estarem implementados e validados contra corpus real.
6. **Process Storage (19)** — depende de (18) definir o formato do artefato a armazenar.
7. **Legal Knowledge Retrieval (20)** e **chunking/reranking (21)** — última prioridade; dependem de (5) já ter um corpus de artefatos Legal Producer real para indexar; caso contrário qualquer decisão de chunking seria especulativa.

Capacidades ADAPT (1, 2, 4, 6, 22, 23) não precisam de mudança OpenSpec dedicada isoladamente — cada uma pode ser formalizada como parte da mudança que primeiro precisar da sua generalização (ex.: capacidade 23 se estende naturalmente dentro da mudança que implementar a capacidade 14).

## 12. Primeiro Stage seguro após aprovação deste mapa

**Post-OCR Critical-Data Validation (capacidade 12)** é o único candidato que satisfaz simultaneamente: (a) achado real já confirmado e evidenciado (auditoria arquivada `audit-ocr-critical-data-fidelity`, commit `4759696`), (b) zero dependência de capacidade ainda ausente, (c) extensão in-place de um módulo já existente e testado (`validator.py`), (d) escopo pequeno e mensurável (2 mudanças candidatas já detalhadas em `LOOPS.md`: comprimento fixo do selo digital + checksum CPF; comparação de valores redundantes intra-documento). Qualquer Stage que envolva Domain Router ou as camadas Legal/Process semânticas deveria vir depois, pois dependem de decisões arquiteturais ainda não registradas (seção 6, item 5).
