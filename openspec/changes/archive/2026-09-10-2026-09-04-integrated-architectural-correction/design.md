# Design: Correção Arquitetural Integrada — Legal Knowledge / Intake

## 1. Identidade e estrutura física

O `concept_id` continua estritamente posicional: caminho relativo do Markdown a partir de `bundle/`, sem `.md`. Ele não é persistido no frontmatter.

As quatro árvores canônicas permanecem obrigatórias:

- `bundle/legislacao/`
- `bundle/jurisprudencia/`
- `bundle/temas/`
- `bundle/precedentes/`

Slugs usam somente `[a-z0-9_]`, com transliteração para ASCII e `_` como separador lógico.

### Legislação

Por decisão HUMAN posterior às baselines FROZEN, `Legislacao` será organizada fisicamente pelo ramo jurídico principal:

`bundle/legislacao/<ramo_principal>/<tipo_norma>_<numero_norma>_<ano>.md`

Exemplo:

`bundle/legislacao/direito_civil/lei_10406_2002.md`

`repo_jur_lei_esfera` permanece metadado. Ambiguidade quanto ao ramo principal exige HUMAN REVIEW.

### Jurisprudência, Temas e Precedentes

Não criar novas subpastas por tribunal, órgão, ramo ou outra taxonomia sem decisão normativa específica.

Aplicar as convenções de filename da baseline FROZEN, usando somente identificadores oficiais efetivamente disponíveis e fallback determinístico quando necessário.

## 2. Evidência e resource

O PDF original permanece fora do Git/bundle, preservado em Object Storage.

`sources[].resource` deve identificar de forma estável e resolvível a evidência efetivamente utilizada pelo pipeline.

Esta correção NÃO define novo esquema URI. Em particular, `evidence://` não é autorizado por esta mudança.

O campo OKF `resource`, quando aplicável, mantém sua semântica própria de identificação do ativo subjacente e não deve ser confundido automaticamente com `sources[].resource`.

## 3. Frontmatter YAML

- usar YAML mapping convencional;
- não serializar mappings como JSON scalar;
- preservar campos Human-Owned existentes;
- `type` é obrigatório;
- `title` é recomendado, não obrigatório;
- `generated` é obrigatório para concepts produzidos pelo pipeline;
- `status` permanece Human-Owned;
- não impor ordenação alfabética como requisito normativo.

## 4. Relações jurídicas estruturadas

Jurisprudencia, TemaJuridico e PrecedenteVinculante podem registrar normas referenciadas por:

`repo_jur_normas_referenciadas`

Cada relação deve apontar para `concept_id` de `Legislacao` e, quando sustentado pela fonte, listar artigos identificados. Não inventar relações ou artigos.

`repo_jur_ramo_direito` deverá evoluir de forma controlada para representação multivalorada, preservando compatibilidade durante a migração.

## 5. Intake e Shared Conversion Core

Existe um único Shared Conversion Core.

O Intake deve reutilizar `ConversionEngine`; não deve reimplementar a conversão.

O split de domínio ocorre após Phase 1 / Quality Gate.

O core compartilhado não incorpora schemas, classificação semântica, canonical storage, regras de concept identity ou lógica específica de Producer.

Os `Phase1Artifacts` publicados para consumidores devem conter Markdown sanitizado, enquanto metadados técnicos permanecem no relatório JSON.
