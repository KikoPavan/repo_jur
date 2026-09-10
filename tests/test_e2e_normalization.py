import fitz
import pytest

from pipeline_juridico.contracts import GateState, Phase1Artifacts
from pipeline_juridico.converter import convert_document
from pipeline_juridico.models import Metodo
from pipeline_juridico.quality_gate import evaluate
from pipeline_juridico.report import (
    build_candidate_report_json,
    strip_technical_routing_metadata,
)


@pytest.fixture
def dummy_pdf(tmp_path):
    path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Content")
    doc.save(path)
    doc.close()
    return path

@pytest.fixture
def dummy_pdf_2pages(tmp_path):
    path = tmp_path / "test_2p.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path

class MockEngine:
    def __init__(self, text="Default Content"):
        self.text_content = text
    def convert(self, _path):
        from types import SimpleNamespace
        return SimpleNamespace(text_content=self.text_content)

def test_e2e_native_flow_with_normalization(dummy_pdf, tmp_path, monkeypatch):
    # Rota: Nativa
    # Engine injeta resíduo
    monkeypatch.setattr("pipeline_juridico.converter.create_native_engine",
                        lambda: MockEngine("*[Image OCR] Texto Nativo"))
    monkeypatch.setattr("pipeline_juridico.converter.route_page",
                        lambda *args: Metodo.texto_nativo)

    out_path = tmp_path / "out.md"
    markdown, report = convert_document(
        pdf_path=dummy_pdf,
        output_path=out_path,
        temp_root=tmp_path / "temp",
        use_ocr=False
    )

    # Verificação
    assert "*[Image OCR]" not in markdown
    assert "Texto Nativo" in markdown

    # Quality Gate proof
    literal = strip_technical_routing_metadata(markdown)
    candidate_json = build_candidate_report_json(report)
    gate_result = evaluate(Phase1Artifacts(markdown=literal, report_json=candidate_json))
    assert gate_result.state == GateState.PASS

def test_e2e_ocr_flow_with_normalization(dummy_pdf, tmp_path, monkeypatch):
    # Rota: OCR
    # Engine OCR injeta resíduo
    monkeypatch.setattr("pipeline_juridico.converter.create_ocr_engine",
                        lambda **kwargs: MockEngine("## Page 1\nTexto OCR"))
    monkeypatch.setattr("pipeline_juridico.converter.route_page",
                        lambda *args: Metodo.ocr_integral)
    # Mock verify_ocr_evidence to pass
    monkeypatch.setattr("pipeline_juridico.converter.verify_ocr_evidence",
                        lambda content, method: (method, []))

    out_path = tmp_path / "out_ocr.md"
    markdown, report = convert_document(
        pdf_path=dummy_pdf,
        output_path=out_path,
        temp_root=tmp_path / "temp",
        use_ocr=True,
        ocr_api_key="dummy"
    )

    assert "## Page 1" not in markdown
    assert "Texto OCR" in markdown

    literal = strip_technical_routing_metadata(markdown)
    candidate_json = build_candidate_report_json(report)
    gate_result = evaluate(Phase1Artifacts(markdown=literal, report_json=candidate_json))
    assert gate_result.state == GateState.PASS

def test_e2e_mixed_flow_preservation(dummy_pdf_2pages, tmp_path, monkeypatch):
    # Página 1: Nativa, Página 2: OCR
    def mock_route(page, config):
        # page number is not directly available here, but we can count calls
        if not hasattr(mock_route, "calls"): mock_route.calls = 0
        mock_route.calls += 1
        return Metodo.texto_nativo if mock_route.calls == 1 else Metodo.ocr_integral

    monkeypatch.setattr("pipeline_juridico.converter.route_page", mock_route)
    monkeypatch.setattr("pipeline_juridico.converter.create_native_engine",
                        lambda: MockEngine("Conteúdo Nativo"))
    monkeypatch.setattr("pipeline_juridico.converter.create_ocr_engine",
                        lambda **kwargs: MockEngine("Conteúdo OCR"))
    monkeypatch.setattr("pipeline_juridico.converter.verify_ocr_evidence",
                        lambda content, method: (method, []))

    out_path = tmp_path / "out_mixed.md"
    markdown, report = convert_document(
        pdf_path=dummy_pdf_2pages,
        output_path=out_path,
        temp_root=tmp_path / "temp",
        use_ocr=True,
        ocr_api_key="dummy"
    )

    assert "[[Pág. 1]]" in markdown
    assert "Conteúdo Nativo" in markdown
    assert "[[Pág. 2]]" in markdown
    assert "Conteúdo OCR" in markdown

    literal = strip_technical_routing_metadata(markdown)
    candidate_json = build_candidate_report_json(report)
    gate_result = evaluate(Phase1Artifacts(markdown=literal, report_json=candidate_json))
    assert gate_result.state == GateState.PASS
