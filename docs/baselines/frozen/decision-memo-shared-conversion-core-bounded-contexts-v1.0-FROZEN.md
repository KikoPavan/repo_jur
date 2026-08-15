# DECISION MEMO — SHARED CONVERSION CORE & BOUNDED CONTEXTS

**Versão:** 1.0  
**Data:** 15 de agosto de 2026  
**Status:** APPROVED — CLOSED — FROZEN

## Decision

Adotar um único **Shared Conversion Core** para PDF → Markdown, reutilizável pelos dois bounded contexts oficiais.

Após Phase 1 / Quality Gate, separar obrigatoriamente:

### Legal Knowledge Pipeline

Escopo:

- legislação;
- jurisprudência;
- temas;
- precedentes.

Canonical storage:

```text
repo_jur/bundle/
```

Somente este bounded context usa o Legal OKF Profile atual e publica no bundle.

### Judicial Process Pipeline

Escopo:

- petições;
- contestações;
- decisões processuais;
- procurações;
- testamentos;
- anexos;
- demais documentos processuais.

Esse bounded context possui:

- armazenamento próprio;
- schemas próprios;
- enrichment próprio;
- producer próprio;
- lifecycle/domain rules próprias quando definidas.

Ele não publica em `repo_jur/bundle/`.

## Shared Contracts

Podem ser compartilhados apenas contratos realmente comuns:

- evidence reference;
- official SHA-256;
- physical page markers;
- Phase 1 technical report envelope;
- Quality Gate states;
- engine abstraction;
- technical observability.

## Prohibited Coupling

Não compartilhar automaticamente entre domínios:

- YAML schemas específicos;
- semantic extraction schemas;
- domain-specific classifications;
- lifecycle policies;
- canonical storage;
- concept identity rules;
- Producer logic.

## Converter Reuse

O conversor existente deve ser reutilizado atrás de:

```python
ConversionEngine
```

Nenhuma reescrita é exigida por esta decisão.

## Invariants

1. Existe um único Shared Conversion Core.
2. O split de domínio ocorre após Phase 1 / Quality Gate.
3. `repo_jur/bundle/` permanece exclusivo da base jurídica canônica.
4. Judicial Process não usa o mesmo bundle.
5. Schemas de domínio são separados.
6. Shared contracts são limitados ao que for realmente comum.
7. Producer-only publication authority permanece válida.

**Decision Status: APPROVED — CLOSED — FROZEN**
