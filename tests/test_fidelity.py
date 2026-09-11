"""Unit tests for OCR Fidelity and Uncertainty Control."""

from pipeline_juridico.fidelity import (
    FidelityManager,
    check_entity_consistency,
    detect_duplications,
    detect_visual_uncertainty,
    monitor_sensitive_tokens,
)


def test_detect_duplications_internal():
    # Sequence of 100+ chars repeated inside a larger text
    snippet = "ESTA É UMA ESCRITURA PÚBLICA DE COMPRA E VENDA QUE SERÁ REGISTRADA NO CARTÓRIO COMPETENTE CONFORME AS NORMAS VIGENTES DO ESTADO."
    text = f"Início do documento. {snippet} Meio do documento. {snippet} Fim."
    issues = detect_duplications(text, page_number=1)
    assert len(issues) >= 1
    assert issues[0].issue_type == "duplication"
    assert issues[0].detector == "internal_repetition_detector"
    assert issues[0].fingerprint is not None


def test_detect_duplications_negative_short():
    # Repetition shorter than 100 chars should not be flagged (boilerplate/headers)
    text = "Página 1 de 10. " * 5
    issues = detect_duplications(text, page_number=1)
    assert len(issues) == 0


def test_monitor_sensitive_tokens_e032_deterministic_with_context():
    # 8 12 is suspicious near 'artigo'
    text = "conforme artigo 357, 8 12, CPC. 8 2026. Data legítima."
    issues = monitor_sensitive_tokens(text, page_number=1)
    # Should detect 8 12 because of context, but not 8 2026
    assert len(issues) == 1
    assert issues[0].issue_type == "sensitive_token_uncertainty"
    assert issues[0].detector == "section_marker_confusion_detector"

def test_monitor_sensitive_tokens_8_62_context():
    # Should detect 8 62 in legal context
    text = "nos termos do artigo 455, 8 62, CPC."
    issues = monitor_sensitive_tokens(text, 1)
    assert any(iss.issue_type == "sensitive_token_uncertainty" for iss in issues)

def test_monitor_sensitive_tokens_8_62_no_context():
    # Should NOT detect if no legal context is present
    text = "O valor total é de 8 62 reais."
    issues = monitor_sensitive_tokens(text, 1)
    assert len(issues) == 0


def test_check_entity_consistency_with_accents_and_title_case():
    text_p1 = "O senhor João da Silva foi citado."
    text_p2 = "O senhor Joao da Silva foi citado."  # Missing accent

    global_entities = {}
    issues_p1 = check_entity_consistency(text_p1, 1, global_entities)
    assert len(issues_p1) == 0

    issues_p2 = check_entity_consistency(text_p2, 2, global_entities)
    # João vs Joao is 1 char difference
    assert len(issues_p2) == 1
    assert issues_p2[0].issue_type == "entity_inconsistency"


def test_check_entity_consistency_siglas_jkmg_jkmq():
    # JKMG vs JKMQ (dist 1, 4 chars)
    global_entities = {"JKMG": 1}
    text = "O documento foi assinado por JKMQ."
    issues = check_entity_consistency(text, 1, global_entities)
    assert len(issues) == 1
    assert issues[0].issue_type == "entity_inconsistency"

def test_check_entity_consistency_siglas_negatives():
    # TJMG vs TJSP (dist 2: MG vs SP) -> No issue
    # NCPC vs CPC (dist 1, but lengths 4 and 3) -> No issue (my code uses [A-Z]{4,})
    global_entities = {"TJMG": 1}
    text = "Decisão do TJSP conforme NCPC."
    issues = check_entity_consistency(text, 1, global_entities)
    # NCPC is ignored (legitimate), TJSP vs TJMG dist is 2.
    assert len(issues) == 0


def test_check_entity_consistency_false_positives():
    # Distinct acronyms with more than 1 char difference should NOT be flagged
    text_p1 = "PROCESSO ADMINISTRATIVO"
    text_p2 = "RECURSO EXTRAORDINÁRIO"

    global_entities = {}
    check_entity_consistency(text_p1, 1, global_entities)
    issues_p2 = check_entity_consistency(text_p2, 2, global_entities)
    assert len(issues_p2) == 0


def test_check_entity_consistency_legal_keywords():
    # Common legal words should not be flagged even if they vary slightly in Case
    text_p1 = "MINISTÉRIO PÚBLICO FEDERAL"
    text_p2 = "Ministério Público Federal"

    global_entities = {}
    check_entity_consistency(text_p1, 1, global_entities)
    issues_p2 = check_entity_consistency(text_p2, 2, global_entities)
    assert len(issues_p2) == 0


def test_detect_visual_uncertainty_mixed_alphanumeric():
    # Suspicious mixed alphanumeric
    text = "A 4DM1N1STR4D0R4 declara que..."
    issues = detect_visual_uncertainty(text, 1)
    assert any(i.detector == "alphanumeric_mixing_detector" for i in issues)


def test_detect_visual_uncertainty_negative_legitimate():
    # Legitimate mixed alphanumeric identifiers
    text = "Art123, Pág4, Lei10806, fls55, doc12, nº44, ID999, Ref_A1."
    issues = detect_visual_uncertainty(text, 1)
    # None of these should be flagged by the alphanumeric detector
    # (assuming they don't trigger line noise)
    alpha_issues = [i for i in issues if i.detector == "alphanumeric_mixing_detector"]
    assert len(alpha_issues) == 0


def test_detect_visual_uncertainty_line_noise():
    text = "Linha com excesso de ruído: ~~~~!!!^^^^||||||||\\\\\\\\////////"
    issues = detect_visual_uncertainty(text, 1)
    assert any(i.detector == "line_noise_detector" for i in issues)


def test_fidelity_manager_no_double_check():
    # FidelityManager should NOT have _revalidate_issues or use Tesseract
    manager = FidelityManager()
    assert not hasattr(manager, "_revalidate_issues")

    text = "conforme artigo 357, 8 12, CPC. " + "Repetição" * 50 # 450 chars
    # Should not raise error or try to run Tesseract even if we passed a path (if we could)
    new_text, audit = manager.apply_controls(text, 1)
    assert text == new_text
    assert len(audit.issues) >= 2 # 8 12 (with context) and duplication
