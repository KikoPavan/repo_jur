> Nota de status: esta mudança é SOMENTE DIAGNÓSTICO. Nenhum código foi alterado, nenhum teste de produção foi criado. Conclusão: **A) CRITÉRIO SEGURO ENCONTRADO** — blast radius de 2/241 páginas, 0 falsos positivos, 0 falsos negativos (ver `design.md`). TDD e implementação aguardam aprovação humana explícita antes de começar.

## 1. Diagnóstico

- [x] 1.1 Localizar todas as ocorrências reais do defeito `RECURSO`/`ESPECIAL.` no corpus e inspecionar a estrutura nativa via `page.get_text("dict")` (página, bloco, linha, span, bbox, fonte, tamanho, flags, distância vertical/horizontal, relação com blocos vizinhos). Resultado: 2 ocorrências reais, `REsp_1704551-SP.pdf` páginas 1 e 6, mesmo conteúdo de ementa; documentado em `design.md`, ETAPA 1.
- [x] 1.2 Determinar se `RECURSO` e `ESPECIAL.` pertencem ao mesmo bloco, linhas diferentes ou blocos distintos. Resultado: mesmo bloco geométrico, mesma coordenada Y exata (339.75/351.75, sem diferença), mas o PyMuPDF já entrega como 7 registros de "linha" separados (um por palavra) devido ao espaçamento largo de texto justificado.
- [x] 1.3 Rastrear pelo pipeline (extração nativa, `compose_document`, `recompose_native_paragraphs`, cleaners posteriores) e determinar o PRIMEIRO estágio responsável, incluindo se é o PDF (A) ou o pipeline (B) que cria a separação. Resultado: **A** — o PDF, via extração do PyMuPDF, já entrega a estrutura fragmentada; o pipeline apenas deixa de recompor a primeira pseudo-linha, devido ao guard de proteção de rótulo (`native_label_pattern` + `previous_is_first`) em `recompose_native_paragraphs`. Documentado em `design.md`, ETAPA 2.
- [x] 1.4 Comparar com casos corretos nos 4 PDFs (mesma expressão unida corretamente; o mesmo mecanismo geométrico de base funcionando corretamente em outros contextos). Resultado: controle direto (página 12, mesma ementa, PyMuPDF não fragmenta, união correta); controle de mecanismo (76 ocorrências do mesmo padrão geométrico no corpus, 74 delas sendo o comportamento correto e já validado de proteção de rótulo genuíno). Documentado em `design.md`, ETAPA 3.
- [x] 1.5 Avaliar sinais estruturais candidatos (sem usar conteúdo jurídico como critério) e medir blast radius de cada um nos 4 PDFs via simulação da função real de produção. Resultado: critério de recuo consistente das linhas seguintes do bloco (x0) discrimina perfeitamente os 46 casos do corpus (44 rótulos genuínos vs. 2 falsos positivos), com blast radius medido de exatamente 2/241 páginas — 0 falsos positivos, 0 falsos negativos. Documentado em `design.md`, ETAPA 4.
- [x] 1.6 Verificar impacto do candidato em R01, 8 SUBTÍTULO, índice do CC, rodapés técnicos, thin-space, `SAIBA MAIS`, capa editorial e `Papel/Nome`. Resultado: confirmado por decorrência direta da simulação completa nos 4 PDFs — 0 páginas alteradas em `Inf0024E.pdf`, `AINTARESP_1462304-PA.pdf` e `L10.406_CC_2002.pdf`; nenhuma das 74 proteções de rótulo genuíno (incluindo `Papel/Nome`-adjacentes como `RECORRENTE`) foi afetada.
- [x] 1.7 Classificar a conclusão como A ou B conforme critério de aceitação da tarefa. Resultado: **A) CRITÉRIO SEGURO ENCONTRADO**, com proposta mínima documentada em `design.md`.
- [x] 1.8 Confirmar que nenhum código de `src/`/`tests/` foi alterado e que `git status --short` permanece limpo além dos artefatos desta mudança.

## 2. TDD (aguardando aprovação humana)

- [ ] 2.1 AGUARDANDO APROVAÇÃO — critério seguro encontrado e documentado (ver `design.md`), mas não autorizado a avançar para TDD sem decisão humana explícita, conforme instrução da tarefa ("Não implemente nada sem nova aprovação").

## 3. Implementação (aguardando aprovação humana)

- [ ] 3.1 AGUARDANDO APROVAÇÃO — mesma condição do item 2.1.
