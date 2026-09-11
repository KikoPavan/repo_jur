"""Tests for the Fidelity and Uncertainty Control module."""

import pytest
from pipeline_juridico.fidelity import (
    FidelityManager,
    _levenshtein,
    check_entity_consistency,
    detect_duplications,
    detect_visual_uncertainty,
    monitor_sensitive_tokens,
)
from pipeline_juridico.models import FidelityIssue


# --- NEW PRECISION TESTS (MAINTAINED) ---

def test_levenshtein():
    assert _levenshtein("casa", "casa") == 0
    assert _levenshtein("casa", "cara") == 1
    assert _levenshtein("casa", "casas") == 1
    assert _levenshtein("FRANCICO", "FRANCISCO") == 1
    assert _levenshtein("JKMG", "JKMQ") == 1
    assert _levenshtein("BARBARA", "BÁRBARA") == 1


def test_detect_duplications_basic():
    # True duplication (large block)
    block = "A" * 150
    text = block + " " + block
    issues = detect_duplications(text, 1)
    assert len(issues) == 1
    assert issues[0].issue_type == "duplication"

    # Minimal distance/stutter (overlap) - should not flag as substantial duplication
    stutter = "A" * 240
    issues_stutter = detect_duplications(stutter, 1)
    assert len(issues_stutter) == 0


def test_detect_duplications_real_gap_logic():
    # match_len=201, distance=406, gap=205.
    # 205 <= 1.5 * 201 (301.5) -> POSITIVE
    block = "".join(chr(65 + (i % 26)) for i in range(201))
    padding = " " * (406 - 201)
    text_p2 = block + padding + block
    issues_p2 = detect_duplications(text_p2, 2)
    assert len(issues_p2) == 1

    # match_len=230, distance=1286, gap=1056.
    # 1056 > 345 -> NEGATIVE
    block_h = "".join(chr(70 + (i % 26)) for i in range(230))
    padding_h = " " * (1286 - 230)
    text_p8 = block_h + padding_h + block_h
    issues_p8 = detect_duplications(text_p8, 8)
    assert len(issues_p8) == 0


def test_monitor_sensitive_tokens():
    # Positive: 'artigo 455, 8 12, CPC'
    text_pos = "Conforme o artigo 455, 8 12, CPC."
    issues_pos = monitor_sensitive_tokens(text_pos, 1)
    assert len(issues_pos) == 1

    # Negative: isolated '8 62'
    text_neg = "Havia 8 62 pessoas na sala."
    issues_neg = monitor_sensitive_tokens(text_neg, 1)
    assert len(issues_neg) == 0


def test_check_entity_consistency_names():
    global_entities = {}
    text1 = "O Sr. FRANCISCO CARLOS PAVAN."
    check_entity_consistency(text1, 1, global_entities)

    # Positive: FRANCICO vs FRANCISCO
    text2 = "O Sr. FRANCICO CARLOS PAVAN assinou."
    issues = check_entity_consistency(text2, 2, global_entities)
    assert len(issues) == 1
    assert issues[0].issue_type == "entity_inconsistency"

    # Negative: Bárbara vs BARBARA (normalized are same)
    global_entities = {}
    check_entity_consistency("Águas de Santa Bárbara", 1, global_entities)
    issues_neg = check_entity_consistency("AGUAS DE SANTA BARBARA", 2, global_entities)
    assert len(issues_neg) == 0


def test_check_entity_consistency_siglas():
    global_entities = {"JKMG": (1, 0, ["jkmg"])}
    text = "O identificador JKMQ."
    issues = check_entity_consistency(text, 1, global_entities)
    assert len(issues) == 1


def test_detect_visual_uncertainty_mixed_alphanumeric_new():
    # Positive: Truly alternating without context
    text_mixed = "O valor d2Q0d989 foi encontrado."
    issues = detect_visual_uncertainty(text_mixed, 1)
    assert any(i.detector == "alphanumeric_mixing_detector" for i in issues)

    # Negative: With context
    text_ctx = "O código verificador é d2Q0d989."
    issues_ctx = detect_visual_uncertainty(text_ctx, 1)
    assert not any(i.detector == "alphanumeric_mixing_detector" for i in issues_ctx)

    # Negative: Whitelisted patterns
    for word in ["ESCRITURA4", "DESPADEC1", "610008437133v5", "55cf8dbf"]:
        issues = detect_visual_uncertainty(f"Ref {word}", 1)
        assert len(issues) == 0


def test_detect_visual_uncertainty_line_noise_new():
    # Negative: Markdown header
    text_md = "### **DESPACHO/DECISÃO**"
    issues_md = detect_visual_uncertainty(text_md, 1)
    assert len(issues_md) == 0

    # Positive: High noise
    text_noise = "Linha com ruído: %%%%$$$$####@@@@!!!!^^^^"
    issues_noise = detect_visual_uncertainty(text_noise, 1)
    assert any(i.detector == "line_noise_detector" for i in issues_noise)


def test_fidelity_manager_e2e():
    manager = FidelityManager()
    text = "O Sr. FRANCISCO DA SILVA comprou. O Sr. FRANCICO DA SILVA assinou."
    _, audit = manager.apply_controls(text, 1)
    assert any(i.issue_type == "entity_inconsistency" for i in audit.issues)


# --- RESTORED INVARIANTS (REGRESSION) ---

def test_detect_duplications_internal():
    # Sequence of 120+ chars repeated inside a larger text with a gap
    snippet = "ESTA É UMA ESCRITURA PÚBLICA DE COMPRA E VENDA QUE SERÁ REGISTRADA NO CARTÓRIO COMPETENTE CONFORME AS NORMAS VIGENTES DO ESTADO."
    assert len(snippet) >= 120
    padding = " " * 200
    text = f"Início do documento. {snippet} {padding} {snippet} Fim."
    issues = detect_duplications(text, page_number=1)
    assert len(issues) >= 1
    assert issues[0].issue_type == "duplication"
    assert issues[0].detector == "internal_repetition_detector"
    assert issues[0].issue_id is not None


def test_detect_duplications_negative_short():
    # Repetition shorter than 120 chars should not be flagged
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


def test_check_entity_consistency_with_accents_and_title_case_restored():
    # New behavior: accents and case are IGNORED (normalized)
    text_p1 = "O Sr. JOÃO FRANCISCO SILVA foi citado."
    text_p2 = "O Sr. JOÃO FRANCICO SILVA foi citado."  # Inconsistent (Levenshtein 1)

    global_entities = {}
    check_entity_consistency(text_p1, 1, global_entities)
    issues = check_entity_consistency(text_p2, 2, global_entities)
    assert len(issues) >= 1
    assert issues[0].issue_type == "entity_inconsistency"


def test_check_entity_consistency_siglas_jkmg_jkmq_restored():
    # JKMG vs JKMQ (dist 1, 4 chars)
    global_entities = {"JKMG": (1, 0, ["jkmg"])}
    text = "O documento foi assinado por JKMQ."
    issues = check_entity_consistency(text, 1, global_entities)
    assert len(issues) == 1
    assert issues[0].issue_type == "entity_inconsistency"


def test_check_entity_consistency_siglas_negatives_restored():
    # TJMG vs TJSP (dist 2: MG vs SP) -> No issue
    global_entities = {"TJMG": (1, 0, ["tjmg"])}
    text = "Decisão do TJSP conforme NCPC."
    issues = check_entity_consistency(text, 1, global_entities)
    assert len(issues) == 0


def test_check_entity_consistency_false_positives_restored():
    # Distinct acronyms with more than 1 char difference should NOT be flagged
    text_p1 = "PROCESSO ADMINISTRATIVO"
    text_p2 = "RECURSO EXTRAORDINÁRIO"

    global_entities = {}
    check_entity_consistency(text_p1, 1, global_entities)
    issues_p2 = check_entity_consistency(text_p2, 2, global_entities)
    assert len(issues_p2) == 0


def test_check_entity_consistency_legal_keywords_restored():
    # Common legal words should not be flagged even if they vary slightly in Case
    text_p1 = "MINISTÉRIO PÚBLICO FEDERAL"
    text_p2 = "Ministério Público Federal"

    global_entities = {}
    check_entity_consistency(text_p1, 1, global_entities)
    issues_p2 = check_entity_consistency(text_p2, 2, global_entities)
    assert len(issues_p2) == 0


def test_detect_visual_uncertainty_mixed_alphanumeric_restored():
    # Suspicious mixed alphanumeric
    text = "A 4DM1N1STR4D0R4 declara que..."
    issues = detect_visual_uncertainty(text, 1)
    assert any(i.detector == "alphanumeric_mixing_detector" for i in issues)


def test_detect_visual_uncertainty_negative_legitimate_restored():
    # Legitimate mixed alphanumeric identifiers
    text = "Art123, Pág4, Lei10806, fls55, doc12, nº44, ID999, Ref_A1."
    issues = detect_visual_uncertainty(text, 1)
    alpha_issues = [i for i in issues if i.detector == "alphanumeric_mixing_detector"]
    assert len(alpha_issues) == 0


def test_detect_visual_uncertainty_line_noise_restored():
    # Increased noise to ensure ratio > 0.3
    text = "Linha com excesso de ruído: %%%%$$$$####@@@@!!!!^^^^||||||||\\\\\\\\////////"
    issues = detect_visual_uncertainty(text, 1)
    assert any(i.detector == "line_noise_detector" for i in issues)


def test_fidelity_manager_no_double_check_restored():
    # FidelityManager should NOT have _revalidate_issues or use Tesseract
    manager = FidelityManager()
    assert not hasattr(manager, "_revalidate_issues")

    snippet = "ESTA É UMA ESCRITURA PÚBLICA DE COMPRA E VENDA QUE SERÁ REGISTRADA NO CARTÓRIO COMPETENTE CONFORME AS NORMAS VIGENTES DO ESTADO."
    padding = " " * 200
    text = "conforme artigo 357, 8 12, CPC. " + snippet + padding + snippet
    new_text, audit = manager.apply_controls(text, 1)
    assert text == new_text
    assert len(audit.issues) >= 2  # 8 12 (with context) and duplication


def test_duplication_cases_p2_p5_p6_p8_restored():
    # Long header (120+ chars)
    long_header = "CÓDIGO DE NORMAS DA CORREGEDORIA GERAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS - TABELIONATO DE NOTAS - ESCRITURA PÚBLICA DE COMPRA E VENDA"
    assert len(long_header) >= 120

    # p2: Accidental OCR repeat (with gap)
    padding = " " * 100
    p2_text = f"{long_header} {padding} {long_header} Outro conteúdo."
    issues_p2 = detect_duplications(p2_text, 2)
    assert len(issues_p2) >= 1

    # p8, p5, p6: Legitimate repetition (separated by large content)
    unique_content = "".join([f"Texto único número {i}. " for i in range(100)])
    p8_text = f"{long_header}\n\n{unique_content}\n\n{long_header}"
    issues_p8 = detect_duplications(p8_text, 8)
    assert len(issues_p8) == 0


def test_entity_consistency_blocker_regressions_restored():
    # 1. PESSOA/PESSOAS: Negative
    global_entities = {}
    check_entity_consistency("Lista de PESSOAS.", 1, global_entities)
    assert "PESSOAS" not in global_entities

    # 2. TERCEIRA/TERCEIRO: Negative
    global_entities = {}
    check_entity_consistency("O TERCEIRO elemento.", 1, global_entities)
    assert "TERCEIRO" not in global_entities

    # 3. JKMG/JKMQ: Positive
    global_entities = {"JKMG": (1, 0, ["jkmg"])}
    issues = check_entity_consistency("Assinado por JKMQ.", 1, global_entities)
    assert any(iss.issue_type == "entity_inconsistency" for iss in issues)

    # 4. FRANCICO/FRANCISCO: Positive
    global_entities = {}
    check_entity_consistency("JOÃO FRANCISCO SILVA", 1, global_entities)
    issues = check_entity_consistency("JOÃO FRANCICO SILVA", 2, global_entities)
    assert any(iss.issue_type == "entity_inconsistency" for iss in issues)

    # 5. ALL CAPS 6+ single word: Negative
    global_entities = {}
    check_entity_consistency("O DOCUMENTO ESTÁ DISPONÍVEL.", 1, global_entities)
    assert "DOCUMENTO" not in global_entities


def test_check_entity_consistency_offset_precision_with_repeated_tokens_restored():
    text = "O Sr. FRANCISCO CARLOS PAVAN foi citado. Mais tarde, outro Sr. FRANCISCO CARLOS PAVAN apareceu."
    global_entities = {}
    check_entity_consistency(text, 1, global_entities)
    assert "FRANCISCO CARLOS PAVAN" in global_entities
    _, offset, _ = global_entities["FRANCISCO CARLOS PAVAN"]
    assert offset == 6

    text_v2 = "O Sr. FRANCICO CARLOS PAVAN foi citado."
    global_entities_v2 = {"FRANCISCO CARLOS PAVAN": (1, 6, ["francisco", "carlos", "pavan"])}
    issues = check_entity_consistency(text_v2, 2, global_entities_v2)
    inconsistencies = [iss for iss in issues if iss.offset_start == 6]
    assert len(inconsistencies) == 1
    assert inconsistencies[0].related_offsets == [6]
