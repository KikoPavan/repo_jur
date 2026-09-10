# Normalização de Artefatos Técnicos (Pós-OCR) ✨

## Visão Geral
O pipeline agora inclui uma etapa de normalização conservadora para remover resíduos técnicos inequivocamente introduzidos pelo processo de conversão ou OCR, garantindo um Markdown mais limpo e focado no conteúdo jurídico desu~!

## Artefatos Removidos
1. **Marcadores de Imagem**: Ocorrências de `*[Image OCR]` (case-insensitive) injetadas por backends de OCR.
2. **Cabeçalhos de Página Redundantes**: Cabeçalhos Markdown do tipo `## Page N` gerados por ferramentas nativas ou motores de OCR.

## Funcionamento
A normalização ocorre no final da Phase 1 (`converter.py`), logo após a composição do documento e antes da limpeza final.
Os comentários de método `<!-- método: ... -->` são preservados durante a normalização para permitir a validação de integridade do Quality Gate, mas são removidos automaticamente pelo `strip_technical_routing_metadata` antes da geração do hash final do artefato e da publicação desu~.

## Quality Gate
O Quality Gate agora impõe a ausência desses artefatos. Se o Markdown final contiver resíduos de `*[Image OCR]` ou `## Page N`, a execução falhará com estado `FAIL`.
