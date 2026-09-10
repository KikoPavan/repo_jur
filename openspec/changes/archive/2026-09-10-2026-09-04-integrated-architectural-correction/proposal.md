# Proposal: Correção Arquitetural Integrada — Legal Knowledge / Intake

**ID:** 2026-09-04-integrated-architectural-correction
**Author:** Hermes Agent
**Status:** APPROVED

## 1. Contexto

Foram identificadas divergências entre a implementação em andamento e as baselines FROZEN, especialmente na identidade dos concepts, estrutura física do bundle, proveniência de evidências e integração do Intake com o Shared Conversion Core.

Esta mudança deve corrigir essas divergências sem introduzir novas decisões arquiteturais não autorizadas.

## 2. Objetivos

1. Preservar `concept_id` como identidade posicional derivada do caminho.
2. Corrigir geração de slugs e estrutura física do Legal Knowledge.
3. Manter evidências PDF fora do bundle em Object Storage, sem definir novo esquema URI.
4. Produzir frontmatter YAML convencional e compatível com field ownership.
5. Reutilizar o único Shared Conversion Core no Intake.
6. Sincronizar Producer e Retrieval com a identidade canônica.
7. Incorporar decisões HUMAN posteriores explicitamente registradas nesta mudança.

## 3. Restrições

- não introduzir `evidence://`;
- não criar Stable ID adicional;
- não alterar `status` autonomamente;
- não reorganizar Jurisprudencia, TemaJuridico ou PrecedenteVinculante por nova taxonomia física;
- não substituir nem reescrever o conversor existente;
- não executar migração destrutiva ou publicação sem validação e aprovação HUMAN.

## 4. Impacto previsto

- correção do contrato de paths e filenames;
- correção do Producer;
- sincronização do Retrieval;
- integração correta do Intake com `ConversionEngine`;
- atualização dos testes de conformidade;
- eventual migração controlada de concepts existentes somente após validação específica.
