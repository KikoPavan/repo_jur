import dataclasses
import uuid

from pipeline_juridico.fidelity import FidelityManager
from pipeline_juridico.models import (
    ArtifactsInfo,
    InputInfo,
    Metodo,
    Phase1Info,
    Relatorio,
    ResultadoInfo,
    ResultadoPagina,
)
from pipeline_juridico.report import validate_report_contract


# --- NEW PRECISION TESTS (MAINTAINED) ---

def test_duplication_precision_real_values():
    manager = FidelityManager()

    # Positive: True substantial duplication (ESCRITURA4 Page 2 equivalent)
    # match_len=201, distance=406, gap=205.
    # 205 <= 1.5 * 201 (301.5) -> POSITIVE
    block = "".join(chr(65 + (i % 26)) for i in range(201))
    padding = " " * (406 - 201)
    text_p2 = block + padding + block
    _, audit = manager.apply_controls(text_p2, 2)
    dups = [i for i in audit.issues if i.issue_type == "duplication"]
    assert len(dups) == 1
    off1, off2 = dups[0].related_offsets
    assert abs(off1 - 0) < 120
    assert abs(off2 - 406) < 120

    # Negative: Legitimate header repetition (ESCRITURA4 Page 8 equivalent)
    manager_p8 = FidelityManager()
    block_h = "".join(chr(70 + (i % 26)) for i in range(230))
    padding_h = " " * (1286 - 230)
    text_p8 = block_h + padding_h + block_h
    _, audit = manager_p8.apply_controls(text_p8, 8)
    dups = [i for i in audit.issues if i.issue_type == "duplication"]
    assert len(dups) == 0


def test_entity_consistency_precision_real_values():
    manager = FidelityManager()

    # Positive: True inconsistency (multi-token names)
    text_tp = "O Sr. FRANCICO CARLOS PAVAN comprou o imóvel. O Sr. FRANCISCO CARLOS PAVAN assinou."
    _, audit = manager.apply_controls(text_tp, 1)
    inconsistencies = [i for i in audit.issues if i.issue_type == "entity_inconsistency"]
    assert len(inconsistencies) >= 1

    # Negative: Differences only in case/accents
    manager_neg = FidelityManager()
    text_neg = "Em Águas de Santa Bárbara. Em AGUAS DE SANTA BARBARA. Cerqueira César e CERQUEIRA CESAR."
    _, audit = manager_neg.apply_controls(text_neg, 1)
    inconsistencies = [i for i in audit.issues if i.issue_type == "entity_inconsistency"]
    assert len(inconsistencies) == 0


def test_visual_uncertainty_precision_real_values():
    manager = FidelityManager()

    # Negative: Structured technical codes with NO context (but we whitelist them)
    codes = [
        "Documento ESCRITURA4.",
        "Código 610008437133v5.",
        "Hash 55cf8dbf.",
        "Ato DESPADEC1.",
        "ID 123e4567-e89b-41d3-a456-426614174000"
    ]
    for text in codes:
        _, audit = manager.apply_controls(text, 1)
        uncertainties = [i for i in audit.issues if i.issue_type == "visual_uncertainty" and i.detector == "alphanumeric_mixing_detector"]
        assert len(uncertainties) == 0, f"Flagged legitimate code: {text}"

    # Positive: Truly alternating without technical context
    text_mixed = "Encontramos d2Q0d989 no final da página."
    _, audit = manager.apply_controls(text_mixed, 6)
    uncertainties = [i for i in audit.issues if i.issue_type == "visual_uncertainty" and i.detector == "alphanumeric_mixing_detector"]
    assert len(uncertainties) == 1


def test_line_noise_markdown_headers_new():
    manager = FidelityManager()
    # Negative: Markdown headers should not be flagged as noise
    text = "### **DESPACHO/DECISÃO**\n" + "Conteúdo legítimo aqui."
    _, audit = manager.apply_controls(text, 1)
    noise = [i for i in audit.issues if i.issue_type == "visual_uncertainty" and i.detector == "line_noise_detector"]
    assert len(noise) == 0


def test_privacy_and_report_contract_new():
    manager = FidelityManager()
    text = "O Sr. FRANCISCO DA SILVA e FRANCICO DA SILVA. " + ("Repetição " * 100)
    _, audit = manager.apply_controls(text, 1)

    for issue in audit.issues:
        issue_dict = dataclasses.asdict(issue)
        assert 'fingerprint' not in issue_dict
        assert len(issue.issue_id) == 36
        uuid.UUID(issue.issue_id, version=4)
        for off in issue.related_offsets:
            assert isinstance(off, int)

    page = ResultadoPagina(
        page_number=1,
        method=Metodo.ocr_integral,
        char_count=len(text),
        fidelity_audit=audit
    )

    relatorio = Relatorio(
        execution_id="test-exec",
        input=InputInfo(sha256="a"*64, byte_size=100, page_count=1),
        phase1=Phase1Info("impl", "1.0", "1.0", "config"),
        result=ResultadoInfo("PASS_WITH_WARNINGS", [], []),
        artifacts=ArtifactsInfo(markdown_sha256="b"*64),
        pages=[page]
    )

    report_dict = dataclasses.asdict(relatorio)
    validate_report_contract(report_dict)


def test_markdown_byte_for_byte_new():
    manager = FidelityManager()
    text = "Conteúdo original com \n quebras e *marcação*."
    returned_text, _ = manager.apply_controls(text, 1)
    assert returned_text == text


# --- RESTORED INVARIANTS (REGRESSION) ---

def test_duplication_precision_restored():
    manager = FidelityManager()
    block = "O imóvel localizado na Rua das Palmeiras, nº 100, bairro Centro, possui área total de 500m2 e está registrado sob a matrícula 99.887 no Cartório de Registro de Imóveis da Capital. "
    text_tp = block + "\n\n" + block
    _, audit = manager.apply_controls(text_tp, 2)
    dups = [i for i in audit.issues if i.issue_type == "duplication"]
    assert len(dups) >= 1

    text_fp_varied = (
        "IMÓVEL: Um lote de terreno sob o nº 10 da quadra 20, situado na Rua das Flores. "
        "Matrícula nº 123.456 do Cartório de Registro de Imóveis. "
        "\n\n"
        "IMÓVEL: Um lote de terreno sob o nº 11 da quadra 20, situado na Rua das Flores. "
        "Matrícula nº 123.457 do Cartório de Registro de Imóveis. "
    )
    _, audit = manager.apply_controls(text_fp_varied, 5)
    dups = [i for i in audit.issues if i.issue_type == "duplication"]
    assert len(dups) == 0


def test_entity_inconsistency_precision_restored():
    manager = FidelityManager()
    text_tp = "O Sr. FRANCISCO DA SILVA comprou o imóvel. O Sr. FRANCICO DA SILVA assinou o contrato."
    _, audit = manager.apply_controls(text_tp, 1)
    inconsistencies = [i for i in audit.issues if i.issue_type == "entity_inconsistency"]
    assert len(inconsistencies) >= 1


def test_visual_uncertainty_precision_restored():
    manager = FidelityManager()
    codes = ["Documento ESCRITURA4.", "Código 610008437133v5.", "Hash 55cf8dbf."]
    for text in codes:
        _, audit = manager.apply_controls(text, 1)
        uncertainties = [i for i in audit.issues if i.issue_type == "visual_uncertainty"]
        assert len(uncertainties) == 0

    text_noise = "Texto normal seguido de A1B2C3D4E5 que parece corrompido."
    _, audit = manager.apply_controls(text_noise, 1)
    uncertainties = [i for i in audit.issues if i.issue_type == "visual_uncertainty"]
    assert len(uncertainties) >= 1


def test_sensitive_token_uncertainty_restored():
    manager = FidelityManager()
    text = "artigo 455, 8 12, CPC"
    _, audit = manager.apply_controls(text, 1)
    sensitive = [i for i in audit.issues if i.issue_type == "sensitive_token_uncertainty"]
    assert len(sensitive) >= 1
