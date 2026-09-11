# Tasks: OCR Fidelity and Uncertainty Control ✨

- [x] T1: Adicionar `FidelityIssue` e `FidelityAudit` ao `models.py` e atualizar `Relatorio`.
- [x] T2: Implementar detecção de duplicações internas e tokens sensíveis determinísticos em `src/pipeline_juridico/fidelity.py`.
- [x] T3: Implementar verificação conservadora de consistência de entidades em `fidelity.py`.
- [x] T4: Implementar lógica de incerteza visual (mistura alfanumérica e ruído de linha).
- [x] T5: Integrar `FidelityManager` no fluxo do `converter.py` e atualizar o `report.py`.
- [x] T6: Atualizar `quality_gate.py` para validar a presença e o conteúdo do `fidelity_audit`.
- [x] T7: Criar fixtures sintéticos em `tests/fixtures/fidelity/` simulando os erros reais (E032, ESCRITURA4, CONTRSOCIAL8).
- [x] T8: Implementar testes unitários e E2E (sucesso, aviso de inconsistência, falha por incerteza, regressão).
- [x] T9: Verificação final, auditoria OpenSpec, arquivamento da change e commit.
