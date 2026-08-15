# DECISION MEMO — RETRIEVAL BOUNDED-CONTEXT SCOPE

**Versão:** 1.0  
**Data:** 15 de agosto de 2026  
**Status:** APPROVED — CLOSED — FROZEN

## Decision

The current `repo_jur` Retrieval Contract applies exclusively to the **Legal Knowledge** bounded context and its canonical `repo_jur/bundle/`.

## Covered corpus

- legislação;
- jurisprudência;
- temas;
- precedentes;
- any future Legal Knowledge concept explicitly admitted to the Legal bundle by a controlled decision.

## Not covered

`Judicial Process Retrieval` is out of scope of this baseline.

It requires a separate future contract/decision before indexing or searching process-domain canonical storage.

## Isolation

Do not create a shared index that mixes:

- Legal Knowledge concepts;
- judicial-process documents.

Legal retrieval artifacts must be derived only from the Legal Knowledge bundle.

## Preserved decisions

Search Execution Path, Chunking Strategy, Reranking Pipeline, Zero-Write and canonical materialization remain unchanged for Legal Knowledge.

**Decision Status: APPROVED — CLOSED — FROZEN**
