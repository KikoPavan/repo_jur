from dataclasses import asdict
from datetime import datetime, timezone

from pipeline_juridico.models import (
    FonteInfo,
    Metodo,
    OcrInfo,
    Relatorio,
    ResultadoPagina,
    RuntimeInfo,
    SaidaInfo,
    StatusExecucao,
    TimingInfo,
)


def test_metodo_enum_has_five_values():
    assert len(Metodo) == 5
    assert Metodo.texto_nativo.value == "texto_nativo"
    assert Metodo.ocr_integral.value == "ocr_integral"
    assert Metodo.hibrido.value == "hibrido"
    assert Metodo.vazia.value == "vazia"
    assert Metodo.erro.value == "erro"


def test_status_execucao_enum_has_three_values():
    assert len(StatusExecucao) == 3
    assert StatusExecucao.sucesso.value == "sucesso"
    assert StatusExecucao.incompleto.value == "incompleto"
    assert StatusExecucao.falha.value == "falha"


def test_resultado_pagina_defaults():
    r = ResultadoPagina(
        number=1,
        method=Metodo.texto_nativo,
        status=StatusExecucao.sucesso,
        characters=1000,
        duration_ms=150,
    )
    assert r.warnings == []
    assert r.error is None


def test_resultado_pagina_with_warnings_and_error():
    r = ResultadoPagina(
        number=2,
        method=Metodo.ocr_integral,
        status=StatusExecucao.incompleto,
        characters=500,
        duration_ms=3000,
        warnings=["low confidence"],
        error="partial failure",
    )
    assert r.warnings == ["low confidence"]
    assert r.error == "partial failure"


def test_relatorio_asdict_keys():
    now = datetime.now(timezone.utc).isoformat()
    pagina = ResultadoPagina(
        number=1,
        method=Metodo.texto_nativo,
        status=StatusExecucao.sucesso,
        characters=1000,
        duration_ms=150,
    )
    relatorio = Relatorio(
        schema_version="1.0",
        run_id="test-uuid",
        status=StatusExecucao.sucesso,
        source=FonteInfo(
            path="/input/doc.pdf",
            size_bytes=1024,
            sha256="abc123",
            pages=1,
        ),
        output=SaidaInfo(path="/output/doc.md", sha256="def456"),
        runtime=RuntimeInfo(
            python="3.12.0",
            markitdown="0.1.6",
            markitdown_ocr="0.1.0",
            pymupdf="1.23.0",
        ),
        ocr=OcrInfo(
            enabled=True,
            provider="openai-compatible",
            model="gpt-4o",
            prompt_sha256="prompt-hash",
        ),
        timing=TimingInfo(
            started_at=now,
            finished_at=now,
            duration_ms=5000,
        ),
        pages=[pagina],
    )
    d = asdict(relatorio)
    expected_keys = {
        "schema_version",
        "run_id",
        "status",
        "source",
        "output",
        "runtime",
        "ocr",
        "timing",
        "pages",
    }
    assert set(d.keys()) == expected_keys
    assert d["schema_version"] == "1.0"
    assert d["status"] == "sucesso"
    assert d["source"]["path"] == "/input/doc.pdf"
    assert d["runtime"]["markitdown_ocr"] == "0.1.0"
    assert d["pages"][0]["method"] == "texto_nativo"
    assert d["pages"][0]["error"] is None


def test_relatorio_default_schema_version():
    r = Relatorio()
    assert r.schema_version == "1.0"
