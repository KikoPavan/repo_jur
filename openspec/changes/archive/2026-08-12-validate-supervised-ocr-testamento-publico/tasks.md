> Mudança exclusivamente de validação operacional (instrução explícita do usuário via `/goal`: "SOMENTE VALIDAÇÃO OPERACIONAL"). Conclusão: **B) APROVADO COM RESSALVAS**. Conteúdo jurídico substantivo transcrito com excelente fidelidade nas 4/4 páginas; achado de prioridade alta identificado e isolado (ruído de fragmentação char-por-linha do texto vertical e-SAJ, causa raiz no pacote de terceiros `markitdown-ocr`, não em `src/pipeline_juridico/`), candidato a mudança futura dedicada. Nenhuma correção foi implementada aqui. Ver `design.md` para a evidência completa e `proposal.md` para o resumo executivo.

## 0. Validação operacional (concluída)

- [x] 0.1 Pré-voo: `git status --short`, `git log --oneline -5`, `openspec validate --all --strict`, `uv run pytest tests/`; confirmar provider/model/config e presença da credencial sem imprimi-la; mostrar comando exato; isolar saída de `output/`/`logs/`. `design.md`, "Pré-voo".
- [x] 0.2 Executar UMA única conversão real de `012-015-Testamento Publico.pdf` sem `--no-ocr`, registrando horário de início/fim, status por página, rota, páginas que chamaram OCR, provider/model, erros/retries, duração por página e total, status final do CLI. `design.md`, "Execução".
- [x] 0.3 Auditoria página a página: comparação visual de cada página renderizada (150 DPI) contra o Markdown, avaliando omissão/invenção/duplicação/ilegibilidade/nomes/números/datas/pontuação/títulos/parágrafos/assinaturas/ordem de leitura/caracteres corrompidos/conteúdo residual e-SAJ/marcadores `[[Pág. N]]`, sem correção manual. Classificação: 4/4 páginas APROVADA COM RESSALVAS. `design.md`, "Auditoria página a página".
- [x] 0.4 Validação estrutural: 4 marcadores únicos e ordenados, OCR usado somente nas páginas necessárias, nenhum arquivo canônico ou código alterado. `design.md`, "Validação estrutural".
- [x] 0.5 Isolar e reproduzir a causa raiz do ruído de fragmentação (reconstrução determinística das linhas de ruído, localização no código-fonte instalado de `markitdown-ocr`), e separar problemas do OCR de problemas do cleaner. `design.md`, "Causa raiz" e "Problemas do OCR vs. problemas do cleaner".
- [x] 0.6 Classificar o OCR atual (A/B/C) e priorizar achados para mudanças futuras, sem implementar nenhuma correção nem alterar configuração. `proposal.md`, "Conclusão".

## 1. Encerramento do ciclo

- [x] 1.1 Claude (orquestrador) executou toda a validação diretamente (sem Codex/OpenCode), por se tratar de tarefa de auditoria/validação operacional, não de implementação de código em `src/`/`tests/` — consistente com `AGENTS.md`.
- [x] 1.2 Nenhum código, teste, dependência, prompt, configuração de OCR ou corpus canônico foi alterado; commit local (sem push) desta mudança e de seus artefatos de validação, sem arquivar (instrução explícita do usuário).
- [x] 1.3 Atualizar `LOOPS.md` com o resultado desta validação e o achado de prioridade alta como candidato a mudança futura.
