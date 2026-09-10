from pipeline_juridico.cleaner import normalize_technical_artifacts


def test_normalize_image_ocr_variants():
    # Removido se for início de linha, aceitando indentação horizontal
    # Casos solicitados:
    # *[Image OCR] Texto -> recognized
    #  *[Image OCR] Texto -> recognized
    # 	*[Image OCR] Texto -> recognized
    # * [Image OCR] Texto -> recognized
    cases = [
        ("*[Image OCR] Texto", "Texto"),
        (" *[Image OCR] Texto", "Texto"),
        ("\t*[Image OCR] Texto", "Texto"),
        ("* [Image OCR] Texto", "Texto"),
        ("*[Image OCR]", ""),
        ("  *[Image OCR]  ", ""),
    ]
    for input_text, expected in cases:
        normalized = normalize_technical_artifacts(input_text)
        assert normalized.strip() == expected.strip(), f"Failed for {input_text!r}"

def test_normalize_image_ocr_preserves_middle_of_sentence():
    # Preservado se no meio da frase
    # Caso solicitado: Texto *[Image OCR] permanece intacto
    text = "Texto *[Image OCR]"
    assert normalize_technical_artifacts(text) == text

def test_normalize_image_ocr_preserves_posterior_content():
    # Conteúdo posterior ao marcador continua preservado
    text = "*[Image OCR] Este conteúdo deve ficar."
    normalized = normalize_technical_artifacts(text)
    assert normalized.strip() == "Este conteúdo deve ficar."

def test_normalize_page_header_structural_line():
    # Removido se for linha estrutural própria (## Page N)
    cases = [
        ("## Page 1", ""),
        ("##  Page  1", ""),
        ("##\tPage\t1", ""),
    ]
    for input_text, expected in cases:
        normalized = normalize_technical_artifacts(input_text)
        assert normalized.strip() == expected.strip()

def test_normalize_preserves_non_conforming_headers():
    # Preservar se não seguir a estrutura exata ## Page N
    variants = [
        "##Page1",
        "##Page 1",
        "## Page1",
        "# Page 1",
        "### Page 1",
        "## Página 1",
        "## Page 1 - texto",
    ]
    for variant in variants:
        assert normalize_technical_artifacts(variant) == variant

def test_normalize_no_generic_newline_collapse():
    # Não deve colapsar newlines extras por si só
    text = "Linha 1\n\n\n\nLinha 2"
    assert normalize_technical_artifacts(text) == text
