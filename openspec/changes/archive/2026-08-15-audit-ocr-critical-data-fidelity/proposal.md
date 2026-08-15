## Why

Duas mudanças reais já arquivadas (`validate-supervised-ocr-testamento-publico`, 2026-08-12; `fix-ocr-end-marker-leak`, 2026-08-14) validaram a qualidade textual geral do OCR real sobre `input/processos_auditoria/012-015-Testamento Publico.pdf` como "excelente" e "sem texto omitido, inventado ou duplicado". Esta mudança nasce de uma inspeção visual adicional do usuário que **contradiz parcialmente** essa conclusão para dois pontos específicos de dado crítico — um selo digital com um dígito a menos, e um número de telefone parcialmente ilegível — e pede um diagnóstico dedicado, exclusivamente à fidelidade de **dados críticos** (identificadores, números, datas, valores), não à qualidade textual geral já auditada.

Esta mudança é **exclusivamente diagnóstica**. Não implementa código, não cria/edita testes de produção, não altera prompt/modelo/provider, não executa nova chamada OCR/LLM, não corrige o Markdown já produzido, não arquiva e não faz push.

## Caso investigado

`input/processos_auditoria/012-015-Testamento Publico.pdf` (4 páginas, todas `hibrido`, ~150 DPI). Evidência: PDF original; `var/ocr_final/output/012-015-Testamento Publico.md` (última conversão OCR real, executada antes desta sessão); `openspec/changes/archive/2026-08-12-validate-supervised-ocr-testamento-publico/` e `openspec/changes/archive/2026-08-14-fix-ocr-*` como contexto de mudanças OCR já arquivadas. Nenhuma chamada real de OCR/LLM foi feita nesta investigação.

## Conclusão (resumo — evidência completa e tabela de inventário em `design.md`)

1. **Quantidade de dados críticos auditados**: ~70 ocorrências individuais, catalogadas em 13 classes (CPF, RG/CNH, número de processo, código de verificação, matrícula, selo digital, protocolo/ordem de serviço, data, valor monetário, CEP, medida/geometria, livro/folhas, telefone).
2. **Classificação**: **68 EXATA**, **1 DIVERGENTE confirmada**, **1 INCERTA VISUALMENTE**.
3. **Causa provável dos erros**:
   - **Selo digital (p.3, `CE`)**: omissão de um dígito `0` dentro de uma sequência de 8 zeros idênticos consecutivos — falha pontual de contagem de glifo repetido, não um problema de resolução (a mesma máquina, no mesmo documento, leu corretamente uma sequência de zeros idêntica no outro selo, `TE`, e leu corretamente o mesmo valor `CE` numa segunda ocorrência, na página 4). Não é sistemático nem ligado à composição do documento.
   - **Telefone (`FONE`)**: corte físico da margem inferior do scan de origem, confirmado nas duas páginas onde a linha aparece (1 e 3) — limitação da fonte, não do motor de OCR. O prefixo `3357` preservado pela OCR antes do marcador `[ilegível]` não pôde ser confirmado nem contestado pela inspeção visual (sinal insuficiente).
4. **Risco real para uso jurídico**: médio para a classe "selo digital" (identificador de verificação de autenticidade e-SAJ; um erro de um dígito, se publicado sem correção, produziria um código que não valida no site oficial) — mitigado neste caso específico pela redundância intra-documento, mas **não detectável de forma alguma** sem essa exploração deliberada da redundância (a auditoria visual anterior, já arquivada, havia declarado o campo correto). Baixo para o telefone (metadado de contato, sem valor probatório).
5. **Validações determinísticas possíveis**: checagem de comprimento fixo do Selo Digital (25 caracteres) — **teria detectado exatamente o erro real encontrado**, custo baixo, nenhum falso positivo observado; checksum CPF (módulo 11) — cobertura alta, falso negativo residual baixo mas não-zero; comparação de valores redundantes intra-documento — alto valor quando aplicável, mas não generalizável (a maioria dos campos não se repete). Checksum CNJ do número de processo (módulo 97/ISO 7064) é candidato teórico, **não confirmado nesta sessão** (tentativa de reprodução do algoritmo não bateu com o dígito verificador real — precisa de pesquisa da especificação oficial antes de qualquer implementação).
6. **Dados que devem ser apenas sinalizados** (sem validação determinística segura disponível): RG/CNH (sem checksum nacional padronizado), matrícula de imóvel, medidas/geometria, valores monetários, datas por extenso, e qualquer campo já contendo `[ilegível]` ou fisicamente próximo da borda do scan.
7. **O OCR pode ser considerado operacionalmente fechado?** **Não**, para fins de fidelidade de dados críticos — está maduro para estrutura, marcadores e ausência de invenção grosseira de conteúdo (confirmado pelas mudanças já arquivadas), mas esta auditoria encontrou um erro real e sutil de um dígito num identificador juridicamente sensível que uma auditoria visual anterior, documentada como cuidadosa, não havia detectado.
8. **A fidelidade crítica exige camada própria?** **Sim.** O achado central desta auditoria é que revisão visual isolada — humana ou por IA semântica — não teria pego este erro específico; só a comparação determinística entre duas ocorrências redundantes do mesmo dado o expôs. Uma camada de validação pós-OCR determinística (natural extensão do módulo `validator.py` já existente) é necessária como complemento independente, não substituível pela camada de revisão semântica já planejada (Fase 2, `docs/Pipeline_Conversao_Juridica_Corrigido.md` §20, ainda não implementada).
9. **Quantidade de futuras mudanças OpenSpec recomendadas**: **2** — (a) validação de formato/comprimento do Selo Digital + checksum CPF, como sinalização não corretiva em `validator.py`/relatório JSON; (b) comparação de valores redundantes intra-documento (ex. selo digital repetido), de escopo mais heurístico (exige mapear pares redundantes por tipo de documento).
10. **Prioridade**: (a) alta — achado real confirmado nesta auditoria, custo de implementação baixo, nenhum falso positivo esperado; (b) média — valor real, mas escopo mais amplo e menos generalizável.
11. **Arquivos apenas inspecionados** (nenhuma alteração): `input/processos_auditoria/012-015-Testamento Publico.pdf`; `var/ocr_final/output/012-015-Testamento Publico.md`; `var/ocr_final/logs/012-015-Testamento Publico.report.json`; `openspec/changes/archive/2026-08-12-validate-supervised-ocr-testamento-publico/**`; `openspec/changes/archive/2026-08-14-fix-ocr-rotated-text-fragmentation/**`; `openspec/changes/archive/2026-08-14-fix-ocr-end-marker-leak/**`; `openspec/specs/juridical-pdf-conversion/spec.md`; `LOOPS.md`; `docs/Pipeline_Conversao_Juridica_Corrigido.md` (§20). Nenhum arquivo em `src/`, `tests/`, `output/`, `logs/` canônicos foi alterado.
12. **`git status --short`** (ao final desta mudança, antes do commit local desta auditoria): ver `design.md`/commit desta mudança — as únicas novidades são `openspec/changes/audit-ocr-critical-data-fidelity/` (esta mudança, incluindo `evidence/` com os recortes de imagem usados como prova visual) e `var/ocr_final/` (pré-existente à sessão, execução real de 2026-08-14 anterior a este diagnóstico, não gerada por ele).

## Fora do escopo desta investigação

Implementação de qualquer validação; alteração de prompt/modelo/provider; nova chamada OCR/LLM; correção do Markdown já produzido em `var/ocr_final/`; arquivamento; push. Ver `design.md`, seção "Fora do escopo desta investigação", para detalhes adicionais (inclusive a tentativa não conclusiva de decodificação de QR Code/código de barras e de reprodução do checksum CNJ).

## Capabilities

### New Capabilities
(nenhuma — mudança exclusivamente diagnóstica, não implementa)

### Modified Capabilities
(nenhuma)

## Impact

- Código: nenhum. `src/`, `tests/`, dependências, prompt, modelo, provider, cleaner, roteamento e arquitetura não foram tocados.
- Nenhuma chamada real de OCR/LLM foi feita.
- Novo diretório `openspec/changes/audit-ocr-critical-data-fidelity/evidence/` com 5 recortes de imagem (extraídos e ampliados a partir da imagem nativa embutida no PDF, sem reamostragem além da necessária para leitura humana) usados como prova visual dos dois achados centrais.
- Duas ferramentas Python (`opencv-python-headless`, `zxing-cpp`) foram instaladas **apenas** num virtualenv descartável em `/tmp` (fora do `.venv` do projeto, fora de `uv`/`pyproject.toml`/`uv.lock`) para a tentativa de decodificação de QR Code/código de barras; não afetam o ambiente do projeto.
