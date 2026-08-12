## ETAPA 0 — Baseline

- `git status --short` (antes): limpo.
- HEAD: `a228d6811d372b44b133c8d7b98749919e9d04f8` (`docs: record rotated-signature noise archival in LOOPS.md`).
- `uv run pytest tests/`: **364 passed** em 28.08s.
- `openspec validate --all --strict`: **1 passed, 0 failed** (`spec/juridical-pdf-conversion`; nenhuma mudança ativa pré-existente — `openspec list` retornou "No active changes found").

## ETAPA 1 — Inspeção do PDF via PyMuPDF (sem OCR)

`input/processos_auditoria/012-015-Testamento Publico.pdf`, 4 páginas. Métricas obtidas com `fitz` puro (dimensões, `page.get_images(full=True)`/`doc.extract_image`, `page.get_text("dict")`) e com as funções reais de roteamento do projeto (`inspect_native_text`, `inspect_raster_content`, `route_page` de `src/pipeline_juridico/router.py`), para eliminar qualquer divergência entre triagem manual e comportamento real do código.

| Pág. | Rect | Rotação | Imagens | Dimensão img. | DPI aprox. | Área img./página | Texto nativo (bruto) | Texto nativo (`inspect_native_text`, sem espaços) | Blocos texto |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 611×841pt | 0 | 1 (JPEG, RGB, 8bpc) | 1272×1752px | ≈150 | 99,92% | 386 chars | 337 chars | 2 |
| 2 | 611×841pt | 0 | 1 (JPEG, RGB, 8bpc) | 1272×1752px | ≈150 | 99,92% | 386 chars | 337 chars | 2 |
| 3 | 611×841pt | 0 | 1 (JPEG, RGB, 8bpc) | 1272×1752px | ≈150 | 99,92% | 386 chars | 337 chars | 2 |
| 4 | 611×841pt | 0 | 1 (JPEG, RGB, 8bpc) | 1272×1752px | ≈150 | 99,92% | 386 chars | 337 chars | 2 |

Texto nativo completo da página 1 (idêntico nas 4, exceto `fls. N`):

```
Para conferir o original, acesse o site https://esaj.tjsp.jus.br/pastadigital/pg/abrirConferenciaDocumento.do, informe o processo 1000386-85.2026.8.26.0136 e código ewt4TQYQ.
Este documento é cópia do original, assinado digitalmente por JOAO PIRES GAVIAO NETO e Tribunal de Justica do Estado de Sao Paulo, protocolado em 05/04/2026 às 18:09 , sob o número 10003868520268260136.
fls. 12
```

Não há nenhum caractere do corpo do testamento nessa camada — é exclusivamente a autenticação e-SAJ sobreposta à imagem digitalizada. As 4 páginas são, na prática, uma imagem de página inteira (99,92% da área) com uma etiqueta de autenticação em texto. Sem rotação, sem desenhos vetoriais, qualidade de imagem compatível com digitalização de cartório (~150 DPI). Nenhum conteúdo foi extraído por OCR nesta etapa — apenas inspeção geométrica/estrutural via PyMuPDF.

## ETAPA 2 — Estado atual do projeto

Arquivos inspecionados (leitura apenas, nenhuma alteração): `src/pipeline_juridico/inspector.py`, `router.py`, `engines.py`, `converter.py`, `config.py`, `cli.py`, `cleaner.py` (grep dirigido), `pyproject.toml`, `openspec/specs/juridical-pdf-conversion/spec.md`, `openspec/config.yaml`, `tests/test_engines.py`, `prompts/ocr_literal_ptbr.txt`, `LOOPS.md`, `CHANGELOG.md`, e os artefatos da mudança arquivada `openspec/changes/archive/2026-08-12-audit-judicial-process-pdf-support/{proposal.md,design.md,tasks.md}`.

### Roteamento (`router.py`)

`route_page` classifica com base em `NativeTextSignal` (contagem de caracteres/blocos sem espaço) e `RasterSignal` (proporção de área de imagem). Para `Testamento Publico.pdf`, executado diretamente com a config real (`RoutingConfig.from_env()`, valores default: `native_min_text_chars=50`, `full_page_image_min_ratio=0.70`, `significant_image_min_ratio=0.15`):

```
page 1: native_chars=337 blocks=2 raster=RasterSignal(image_count=1, total_image_area_ratio=0.9992, largest_image_area_ratio=0.9992) -> method=Metodo.hibrido
page 2: native_chars=337 blocks=2 raster=... -> method=Metodo.hibrido
page 3: native_chars=337 blocks=2 raster=... -> method=Metodo.hibrido
page 4: native_chars=337 blocks=2 raster=... -> method=Metodo.hibrido
```

As 4 páginas são `hibrido`, não `ocr_integral`: 337 caracteres nativos ≥ `native_min_text_chars` (50), mas < `native_min_text_chars * 10` (500) = `has_clearly_sufficient_native=False`; imagem cobre 99,92% ≥ `full_page_image_min_ratio` (70%) = `has_full_page_image=True`. `has_native=True` + `has_raster_signal=True` + `has_clearly_sufficient_native=False` → `hibrido` (não `texto_nativo`, apesar de haver texto nativo utilizável — corretamente, pois esse texto é só a autenticação, não o conteúdo substantivo).

### Como `--no-ocr` bloqueia a página (`converter.py`)

```python
elif not use_ocr:
    method = Metodo.erro
    warnings.append(
        "OCR desabilitado via --no-ocr; página não pôde ser processada."
    )
```

Esse ramo só é alcançado quando `method` (após `route_page`) **não** é `vazia` nem `texto_nativo` — ou seja, exatamente `hibrido`/`ocr_integral`. Para essas 4 páginas, `use_ocr=False` (via `--no-ocr`) força `erro` sem nunca instanciar o motor de OCR. Em modo estrito (`allow_partial=False`), `validate_page_content` (chamado em `convert_document`) recusa publicar qualquer página em `erro`: `MarkdownValidationError: "A página 1 está em erro; páginas em erro não são permitidas no modo estrito."`, propagado por `cli.py` como exit code 3. Nenhuma página é contornada; nenhum conteúdo é fabricado; o documento inteiro fica sem saída publicada.

### Infraestrutura de OCR já implementada (`engines.py`, `converter.py`, `cli.py`)

Contrariando a suposição implícita de que OCR "ainda precisa ser construído", o código já contém um caminho de OCR completo, não parcial e não legado:

- **`engines.py::create_ocr_engine(api_key, model, base_url, prompt)`**: valida presença de `api_key` e `model`, levantando `OcrConfigurationError` com mensagem explícita e sem vazar segredos (`"Configuração de OCR incompleta: GEMINI_API_KEY ausente, modelo (GEMINI_MODEL) ausente"`); constrói `openai.OpenAI(api_key=api_key, base_url=base_url)` e retorna `MarkItDown(enable_plugins=True, llm_client=client, llm_model=model, llm_prompt=prompt)`.
- **`cli.py`**: já resolve `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_BASE_URL` (default `https://generativelanguage.googleapis.com/v1beta/openai/`, o endpoint OpenAI-compatible oficial do Gemini) e `OCR_PROMPT_FILE` (default `prompts/ocr_literal_ptbr.txt`) a partir do ambiente (`.env` via `load_dotenv()`), e já sanitiza a chave de qualquer mensagem de log (`_sanitize_log_message`).
- **`converter.py::convert_document`**: para cada página cujo `method` seja `hibrido`/`ocr_integral` e `use_ocr=True`, cria o motor OCR de forma preguiçosa (`if ocr_engine is None: ...`, só na primeira página que precisar) e chama `ocr_engine.convert(page_path)` sobre o PDF de página isolada (1 página por arquivo, via `isolated_page_workspace`/`isolate_pages` de `inspector.py`) — ou seja, **OCR já é por página, não por documento inteiro**. O resultado passa por `verify_ocr_evidence`/`scan_ocr_warnings`, que varrem o texto retornado por strings-sentinela de falha (`[No text could be extracted from this page]`, `[Error processing page`, `[Error: Could not process scanned PDF]`) — necessário porque `markitdown-ocr` falha silenciosamente sem lançar exceção (comportamento já conhecido, ver memória do projeto). Qualquer falha ou ausência de evidência promove a página para `Metodo.erro` explicitamente; sucesso mantém o método `hibrido`/`ocr_integral` original.
- **Dependência declarada**: `markitdown-ocr>=0.1.0` já está em `pyproject.toml` (junto com `google-genai>=2.14.0` e `openai>=2.48.0`); nenhuma dependência nova seria necessária.
- **Prompt versionado**: `prompts/ocr_literal_ptbr.txt` já existe (transcrição literal, sem resumo/correção, preservando ordem de leitura e tabelas).
- **Spec já cobre o comportamento**: `openspec/specs/juridical-pdf-conversion/spec.md`, requisito "OCR controlado e verificável", já formaliza os 3 cenários (OCR configurado retorna conteúdo / OCR necessário sem configuração / serviço de OCR emite aviso ou omite conteúdo) — não é uma capability a ser criada, já está ativa e testada.
- **Testes já existem** (`tests/test_engines.py`, 11 testes específicos de OCR): cobrem criação do motor, validação de credenciais ausentes (chave, modelo, ambos), detecção de cada marcador de falha, sanitização de segredos/caminhos em mensagens de erro, e 5 cenários simulados de ponta a ponta com cliente LLM fake (sucesso, falha com aviso, resposta vazia, timeout, modelo indisponível) — todos passando (parte dos 364/364 da suíte completa).

**Conclusão desta etapa:** o OCR não está "acoplado" nem "ausente" — está **isolado e completo**. O caminho `texto_nativo` nunca instancia nem depende do motor OCR (`ocr_engine = None` inicial, só populado dentro do `else` que trata `hibrido`/`ocr_integral`). O único elemento nunca exercitado é uma chamada real à API do Gemini contra este documento específico — o que está fora do escopo desta auditoria por decisão de projeto (nenhum agente pode fazer OCR real sem aprovação humana) e por instrução explícita do usuário nesta mudança.

## ETAPA 3 — Reconfirmação com `--no-ocr` no HEAD atual

CLI oficial (`uv run converter-juridico`), saída isolada via `OUTPUT_DIR`/`LOGS_DIR` apontando para `openspec/changes/audit-scanned-pdf-ocr-support/audit_output/{strict,partial}` e `.../{logs_strict,logs_partial}` — nunca `output/`/`logs/`. Nenhuma variável de OCR foi setada além do que já existe em `.env`; `--no-ocr` esteve sempre presente; nenhuma chamada de rede/LLM ocorreu (confirmado por `ocr.enabled: false` no relatório).

| Execução | Resultado |
| --- | --- |
| `--no-ocr` (modo estrito) | `MarkdownValidationError`: "A página 1 está em erro; páginas em erro não são permitidas no modo estrito." — exit code 3, nenhum arquivo publicado |
| `--no-ocr --allow-partial` (só para evidência de auditoria) | exit code 0; relatório mostra 4/4 páginas `method: erro`, `status: falha`, aviso `"OCR desabilitado via --no-ocr; página não pôde ser processada."`; `ocr.enabled: false`; `ocr.model: gemini-3-flash-preview` registrado (do ambiente) mas nunca usado — nenhuma chamada foi feita |

Resultado idêntico, byte a byte na estrutura, ao documentado na auditoria anterior (`audit-judicial-process-pdf-support`) — o comportamento não mudou entre o HEAD daquela auditoria (`1f24617`) e o HEAD atual (`a228d68`), como esperado (nenhuma mudança arquivada nesse intervalo tocou roteamento ou OCR; `fix-rotated-digital-signature-noise` alterou apenas extração de blocos rotacionados duplicados em texto nativo, caminho não exercitado por este documento).

## ETAPA 4 — Arquitetura e opções

### Arquitetura mínima recomendada (já implementada)

```
PDF → isolamento por página (inspector.py)
    → roteamento por página (router.py: texto_nativo | hibrido | ocr_integral | vazia)
    → texto_nativo: MarkItDown nativo, nunca toca OCR
       hibrido/ocr_integral: OCR por página isolada (engines.py, motor criado sob demanda)
    → verificação de evidência de OCR (verify_ocr_evidence) → erro explícito se ausente/falho
    → composição do Markdown bruto com marcador [[Pág. N]] + <!-- método: ... --> por página
    → cleaners determinísticos (cleaner.py), aplicados uniformemente independente da origem
    → validação final (validator.py) → Markdown final
```

Isso já satisfaz cada critério pedido na ETAPA 3 do `/goal`:

- **OCR por página, não documento inteiro:** sim — `isolated_page_workspace` isola cada página em um PDF de 1 página antes de qualquer roteamento ou conversão.
- **Preservação de `[[Pág. N]]`:** sim — `format_page_marker`/`compose_document` emitem o marcador para toda página, independente do método.
- **Rastreabilidade de quais páginas usaram OCR:** sim — o comentário `<!-- método: hibrido -->`/`<!-- método: ocr_integral -->` no Markdown e o campo `method` por página no relatório JSON (`build_page_result`) já registram isso.
- **Falha explícita quando OCR não está disponível:** sim — `OcrConfigurationError` (credenciais ausentes) e `Metodo.erro` com aviso sanitizado (evidência ausente/falha técnica).
- **Possibilidade de reprocessamento:** sim, por reexecução do CLI sobre o mesmo PDF — não há cache que impeça isso, mas também não há cache que acelere isso (ver risco no proposal.md).
- **Idempotência após obtenção do texto OCR:** os cleaners determinísticos são aplicados de forma idêntica ao texto composto, independentemente de vir de `texto_nativo` ou de OCR — nenhuma branch por método em `cleaner.py` (confirmado por grep; a única referência a "método" ali é o regex que reconhece o comentário `<!-- método: ... -->` como marcador estrutural, não uma ramificação de comportamento). A parte não idempotente inerente é a própria chamada ao LLM (não determinística execução a execução), que está fora do controle do pipeline determinístico por natureza — não é um defeito de arquitetura.
- **Separação entre provider OCR e pipeline:** sim — `create_ocr_engine` encapsula toda a configuração de provedor (cliente OpenAI-compatible, modelo, base URL, prompt); `converter.py` só chama `.convert(page_path)` e trata o resultado por contrato (texto + verificação de evidência), sem conhecer detalhes do provedor.

### Opções comparadas (sem instalar/executar nada novo)

| Opção | Mudanças necessárias | Dependências novas | Impacto arquitetural | Custo/latência | Qualidade esperada (documento cartorial) | Privacidade | Determinismo | Manutenção |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **Reaproveitar infraestrutura existente (Gemini via `markitdown-ocr`)** | Nenhuma de código — só validação supervisionada | Nenhuma | Nenhum — já é o ponto de integração ativo, já coberto pela spec aceita | 1 chamada de visão por página (4 páginas) — custo/latência já assumidos no design aceito do projeto | Desconhecida empiricamente para ~150 DPI cartorial até validação real; prompt já pede transcrição literal com marcação de ilegibilidade | Já mitigado pelo padrão do projeto (chave nunca logada, conteúdo integral nunca registrado) | Não determinístico por chamada (inerente a LLM), mas já é o modelo de risco aceito pela spec ("Não prometer fidelidade absoluta ou determinismo para resultados produzidos por OCR baseado em LLM", `openspec/config.yaml`) | Já testado (mocks), já documentado, já com contrato de spec — custo de manutenção zero adicional |
| **OCR local (ex. Tesseract/outro motor offline)** | Novo motor, novo adapter, nova branch de configuração, spec nova ou modificada para descrever um segundo provedor | Sim (biblioteca OCR local) | Alto — duplicaria o mecanismo já existente e violaria a separação de responsabilidade já estabelecida ("provider OCR" único e já escolhido); contradiz a spec já aceita, que já formaliza um único caminho de OCR via LLM configurado externamente | Sem custo de API, mas processamento local; qualidade tipicamente inferior a OCR baseado em visão LLM para documentos com layout/carimbos complexos | Tipicamente pior que OCR baseado em LLM para documentos cartoriais com carimbos, selos e diagramação irregular (sem avaliação empírica direta neste repositório) | Melhor (processamento local, sem envio a terceiros) | Determinístico por execução (mesma imagem → mesmo resultado), ao contrário da opção LLM | Adicionaria uma segunda superfície de manutenção (dois motores de OCR) sem necessidade demonstrada |
| **Segundo provedor externo (não-Gemini)** | Novo adapter, nova validação de credenciais, possível nova spec | Sim (SDK do provedor) | Alto — mesma duplicação da opção anterior, sem justificativa: o projeto já escolheu e implementou um provedor único, documentado em `openspec/config.yaml` ("OCR: plugin markitdown-ocr com cliente OpenAI-compatible") | Variável por provedor | Desconhecida sem avaliação | Depende do provedor | Não determinístico (mesma classe de risco da opção 1) | Adicionaria segredo/config extra, sem ganho demonstrado sobre a opção já implementada |

A recomendação (opção 1) não é escolha por preferência de tecnologia — é a única opção consistente com o estado real do projeto: a spec já aceita, o código já implementado e testado, e a ausência de qualquer evidência (nesta auditoria ou na anterior) de que o provedor atual seja inadequado para o tipo de documento. Construir um segundo caminho de OCR sem antes validar o já existente seria especulativo.

## ETAPA 5 — Escopo futuro (separado por responsabilidade)

- **A. Mudanças necessárias para OCR:** nenhuma identificada nesta auditoria. Próximo passo é uma execução supervisionada e aprovada por humano (não uma mudança de código) chamando `converter-juridico` sem `--no-ocr` sobre `Testamento Publico.pdf`, usando a infraestrutura já existente.
- **B. Limpeza determinística pós-OCR:** não avaliável agora — depende do texto real que uma chamada de OCR retornaria, que esta auditoria não pode obter (fora de escopo). Se a validação supervisionada revelar padrões de ruído ou formatação específicos de OCR, isso justificaria uma mudança futura dedicada, seguindo o mesmo processo de diagnóstico → correção usado em `fix-rotated-digital-signature-noise`.
- **C. Revisão semântica por IA:** fora de escopo desta e de qualquer mudança futura de OCR — é uma camada distinta, não mencionada em nenhum requisito ativo de `openspec/specs/juridical-pdf-conversion/spec.md`.
- **D. Segmentação/YAML:** explicitamente fora do escopo da Fase 1 (`openspec/config.yaml`: "Open Knowledge Format e YAML front matter estão fora do escopo desta fase") — não deve ser misturada com nenhuma decisão de OCR.

## Verificação de não regressão

- `output/AINTARESP_1462304-PA.md`, `output/REsp_1704551-SP.md`, `output/Inf0024E.md`, `output/L10.406_CC_2002.md`, `output/001-007-Petição Inicial.md` (se presente), `output/086-096-CONTESTAÇÃO...md`, `output/100-106-DECISÃO.md`: não reconvertidos, não tocados por esta auditoria.
- Nenhuma chamada de OCR ou LLM foi realizada em nenhuma etapa (`ocr.enabled: false` confirmado nos relatórios gerados).
- `uv run pytest tests/`: 364/364 passou antes de qualquer ação desta auditoria; nenhum código foi alterado depois, portanto a suíte permanece válida.
- `openspec validate --all --strict`: 1 passado, 0 falhado, antes desta auditoria; esta mudança não adiciona nem modifica nenhuma spec.

## `git status --short` ao final

Ver saída no encerramento desta mudança (task 1.2) — o único diretório novo esperado é `openspec/changes/audit-scanned-pdf-ocr-support/` (esta mudança, incluindo `audit_output/`); nenhum arquivo em `src/`, `tests/`, `output/`, `logs/`, `openspec/specs/` ou no corpus canônico deve aparecer.
