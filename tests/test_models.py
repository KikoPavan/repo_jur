from dataclasses import asdict
from pipeline_juridico.models import (ArtifactsInfo, InputInfo, Metodo, Phase1Info,
    Relatorio, ResultadoInfo, ResultadoPagina, StatusExecucao)


def test_enums_are_stable():
    assert [m.value for m in Metodo] == ["texto_nativo", "ocr_integral", "hibrido", "vazia", "erro"]
    assert [s.value for s in StatusExecucao] == ["sucesso", "incompleto", "falha"]


def test_resultado_pagina_defaults():
    page = ResultadoPagina(1, Metodo.texto_nativo, 10)
    assert page.warnings == [] and page.errors == [] and page.truncated is False


def test_relatorio_wire_keys():
    report = Relatorio(execution_id="id", input=InputInfo("a", 1, 1), phase1=Phase1Info("p", "1", "1", "f"), result=ResultadoInfo("PASS"), artifacts=ArtifactsInfo("b"), pages=[ResultadoPagina(1, Metodo.vazia, 0)])
    assert set(asdict(report)) == {"schema_version", "execution_id", "input", "phase1", "result", "artifacts", "pages", "telemetry"}
    assert asdict(report)["pages"][0]["truncated"] is False


def test_relatorio_defaults():
    report = Relatorio()
    assert report.schema_version == "1.0" and report.telemetry == {}
