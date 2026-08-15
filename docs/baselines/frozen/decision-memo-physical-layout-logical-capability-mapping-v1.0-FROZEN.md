# DECISION MEMO — PHYSICAL LAYOUT & LOGICAL CAPABILITY MAPPING

**Versão:** 1.0  
**Data:** 15 de agosto de 2026  
**Status:** APPROVED — CLOSED — FROZEN

## Decision

Documentary paths such as `pipeline/`, `producer/`, `shared_conversion/`, `semantic_review/` and similar names are **logical capability targets**, not mandatory physical package paths.

The current repository implementation must be inventoried before any relocation or new module creation.

## Current confirmed physical fact

The existing stabilized conversion implementation is located under:

`src/pipeline_juridico/`

This implementation must be preferred for reuse/adaptation when it already satisfies a logical capability.

## Required workflow

```text
logical capability
    ↓
inspect repository
    ↓
existing implementation?
    ├─ yes → REUSE → ADAPT IN PLACE → TEST
    └─ no  → create minimal implementation in justified location
```

## Prohibited behavior

- creating `pipeline/shared_conversion/` only to mirror a diagram;
- moving `src/pipeline_juridico/` only to match documentation terminology;
- duplicating a converter, quality gate, producer or retrieval module already present;
- treating a logical package map as a filesystem migration plan;
- relocation without explicit technical justification and reviewed change.

## Repository Implementation Map

Before code modification, record:

- logical capability;
- physical implementation found;
- reuse/adapt/create decision;
- tests already covering it;
- migration/relocation, if any, with explicit justification.

## Invariant

Architecture defines **boundaries and authority**, not mandatory Python package names.

The canonical physical requirement that remains strict is the protection and bounded-context exclusivity of `repo_jur/bundle/`.

**Decision Status: APPROVED — CLOSED — FROZEN**
