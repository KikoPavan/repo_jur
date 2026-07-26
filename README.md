# Pipeline de Conversão Jurídica — pacote OpenSpec

Este pacote contém a documentação corrigida e os artefatos de planejamento do pipeline PDF → Markdown, estruturados conforme o fluxo `spec-driven` do OpenSpec.

## Conteúdo

```text
openspec/
├── config.yaml
└── changes/
    └── establish-juridical-pdf-conversion-pipeline/
        ├── .openspec.yaml
        ├── proposal.md
        ├── design.md
        ├── tasks.md
        └── specs/
            └── juridical-pdf-conversion/
                └── spec.md
docs/
└── Pipeline_Conversao_Juridica_Corrigido.md
```

## Uso com OpenSpec

No terminal, dentro do repositório do projeto:

```bash
npm install -g @fission-ai/openspec@latest
openspec init
openspec update
```

Copie a pasta `openspec/` deste pacote para a raiz do projeto e valide:

```bash
openspec validate establish-juridical-pdf-conversion-pipeline --strict
openspec status --change establish-juridical-pdf-conversion-pipeline
```

No chat do agente de desenvolvimento:

```text
/opsx:apply establish-juridical-pdf-conversion-pipeline
```

Após implementação e verificação:

```text
/opsx:archive establish-juridical-pdf-conversion-pipeline
```

> Os comandos `/opsx:*` são executados no chat do agente. Os comandos `openspec ...` são executados no terminal.
