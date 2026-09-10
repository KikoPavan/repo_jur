import json

from pipeline_juridico.contracts import GateState, Phase1Artifacts
from pipeline_juridico.quality_gate import evaluate


def build_valid_report(page_count=1, pages=None):
    if pages is None:
        pages = [
            {
                "page_number": i + 1,
                "method": "texto_nativo",
                "char_count": 100,
                "errors": [],
                "warnings": [],
                "truncated": False
            }
            for i in range(page_count)
        ]

    report = {
        "schema_version": "1",
        "execution_id": "test-uuid",
        "input": {
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "byte_size": 1024,
            "page_count": page_count
        },
        "phase1": {
            "implementation": "pipeline-juridico",
            "implementation_version": "1.0.0",
            "logical_processing_version": "1",
            "relevant_config_fingerprint": "abc"
        },
        "artifacts": {
            "markdown_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        },
        "pages": pages,
        "telemetry": {}
    }
    return json.dumps(report)

def test_qgate_fails_with_image_ocr_variants():
    # FAIL se resíduo estiver no início da linha (com ou sem indentação)
    report = build_valid_report()
    cases = [
        "[[Pág. 1]]\n*[Image OCR] Conteúdo",
        "[[Pág. 1]]\n *[Image OCR] Conteúdo",
        "[[Pág. 1]]\n\t*[Image OCR] Conteúdo",
    ]
    for markdown in cases:
        artifacts = Phase1Artifacts(markdown=markdown, report_json=report)
        result = evaluate(artifacts)
        assert result.state == GateState.FAIL, f"Failed to detect residue in: {markdown}"

def test_qgate_passes_with_image_ocr_in_middle():
    # PASS se resíduo estiver no meio da frase (preservado)
    markdown = "[[Pág. 1]]\nCitação de *[Image OCR] aqui."
    report = build_valid_report()
    artifacts = Phase1Artifacts(markdown=markdown, report_json=report)
    result = evaluate(artifacts)
    assert result.state == GateState.PASS

def test_qgate_fails_with_page_header_variants():
    # FAIL se header não canônico seguir a forma ## Page N
    report = build_valid_report()
    cases = [
        "[[Pág. 1]]\n## Page 1",
        "[[Pág. 1]]\n##  Page  1",
        "[[Pág. 1]]\n##\tPage\t1",
    ]
    for markdown in cases:
        artifacts = Phase1Artifacts(markdown=markdown, report_json=report)
        result = evaluate(artifacts)
        assert result.state == GateState.FAIL, f"Failed to detect header in: {markdown}"

def test_qgate_passes_with_allowed_variants():
    # PASS com variantes que não devem ser bloqueadas
    variants = [
        "##Page1",
        "##Page 1",
        "## Page1",
        "# Page 1",
        "### Page 1",
        "## Página 1",
        "## Page 1 - texto",
        "[[Pág. 1]]"
    ]
    report = build_valid_report()
    for variant in variants:
        if variant == "[[Pág. 1]]":
            markdown = f"{variant}\nConteúdo"
        else:
            markdown = f"[[Pág. 1]]\n{variant}\nConteúdo"
        artifacts = Phase1Artifacts(markdown=markdown, report_json=report)
        result = evaluate(artifacts)
        assert result.state == GateState.PASS, f"Incorrectly blocked {variant}"
