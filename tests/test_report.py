import json
from dataclasses import asdict

from pipeline_juridico.hashing import sha256_file
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
from pipeline_juridico.report import (
    build_ocr_info,
    build_page_result,
    build_report_json,
    build_runtime_info,
    determine_final_status,
    ocr_page_numbers,
)


def _complete_report() -> Relatorio:
    return Relatorio(
        schema_version="1.0",
        run_id="uuid-teste",
        status=StatusExecucao.sucesso,
        source=FonteInfo(
            path="input/doc.pdf",
            size_bytes=1000,
            sha256="abc123",
            pages=2,
        ),
        output=SaidaInfo(path="output/doc.md", sha256="def456"),
        runtime=RuntimeInfo(
            python="3.12.11",
            markitdown="0.1.5",
            markitdown_ocr="0.1.0",
            pymupdf="1.28.0",
        ),
        ocr=OcrInfo(
            enabled=True,
            provider="openai-compatible",
            model="gemini-2.0-flash",
            prompt_sha256="xyz789",
        ),
        timing=TimingInfo(
            started_at="2026-07-26T10:00:00-03:00",
            finished_at="2026-07-26T10:00:05-03:00",
            duration_ms=5000,
        ),
        pages=[
            ResultadoPagina(
                number=1,
                method=Metodo.texto_nativo,
                status=StatusExecucao.sucesso,
                characters=100,
                duration_ms=50,
                warnings=[],
                error=None,
            )
        ],
    )


def test_build_report_json_produces_valid_json():
    result = build_report_json(_complete_report())

    assert isinstance(result, str)
    json.loads(result)


def test_build_report_json_contains_all_top_level_keys():
    data = json.loads(build_report_json(_complete_report()))

    assert set(data) == {
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


def test_build_report_json_preserves_enum_values_as_strings():
    data = json.loads(build_report_json(_complete_report()))

    assert data["status"] == "sucesso"
    assert data["pages"][0]["method"] == "texto_nativo"


def test_build_report_json_page_record_has_expected_fields():
    page = json.loads(build_report_json(_complete_report()))["pages"][0]

    assert page == {
        "number": 1,
        "method": "texto_nativo",
        "status": "sucesso",
        "characters": 100,
        "duration_ms": 50,
        "warnings": [],
        "error": None,
    }


def test_build_runtime_info_returns_runtime_info_instance():
    result = build_runtime_info()

    assert isinstance(result, RuntimeInfo)
    assert isinstance(result.python, str) and result.python
    assert isinstance(result.markitdown, str) and result.markitdown
    assert isinstance(result.markitdown_ocr, str) and result.markitdown_ocr
    assert isinstance(result.pymupdf, str) and result.pymupdf


def test_build_ocr_info_computes_prompt_hash(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("Transcreva literalmente.")

    result = build_ocr_info(
        enabled=True,
        provider="openai-compatible",
        model="gemini-2.0-flash",
        prompt_path=prompt_path,
    )

    assert isinstance(result, OcrInfo)
    assert result.enabled is True
    assert result.provider == "openai-compatible"
    assert result.model == "gemini-2.0-flash"
    assert result.prompt_sha256 == sha256_file(prompt_path)


def test_build_page_result_records_character_count_not_content():
    content = "Segredo jurídico confidencial de 42 caracteres."

    result = build_page_result(
        number=1,
        method=Metodo.ocr_integral,
        status=StatusExecucao.sucesso,
        content=content,
        duration_ms=100,
    )

    assert result.characters == 47
    assert not hasattr(result, "content")
    assert content not in str(asdict(result))


def test_build_page_result_defaults_warnings_to_empty_list():
    result = build_page_result(
        number=1,
        method=Metodo.ocr_integral,
        status=StatusExecucao.sucesso,
        content="Texto convertido.",
        duration_ms=100,
    )

    assert result.warnings == []
    assert result.error is None


def test_ocr_page_numbers_filters_correctly():
    pages = [
        ResultadoPagina(1, Metodo.texto_nativo, StatusExecucao.sucesso, 10, 10),
        ResultadoPagina(2, Metodo.ocr_integral, StatusExecucao.sucesso, 20, 20),
        ResultadoPagina(3, Metodo.vazia, StatusExecucao.sucesso, 0, 30),
        ResultadoPagina(4, Metodo.hibrido, StatusExecucao.sucesso, 40, 40),
        ResultadoPagina(5, Metodo.erro, StatusExecucao.falha, 0, 50),
    ]

    assert ocr_page_numbers(pages) == [2, 4]


def test_ocr_page_numbers_empty_when_no_ocr_pages():
    pages = [
        ResultadoPagina(1, Metodo.texto_nativo, StatusExecucao.sucesso, 10, 10),
        ResultadoPagina(2, Metodo.vazia, StatusExecucao.sucesso, 0, 20),
    ]

    assert ocr_page_numbers(pages) == []


def test_determine_final_status_sucesso_when_no_failures():
    pages = [
        ResultadoPagina(1, Metodo.texto_nativo, StatusExecucao.sucesso, 10, 10),
        ResultadoPagina(2, Metodo.ocr_integral, StatusExecucao.sucesso, 20, 20),
    ]

    assert (
        determine_final_status(pages, allow_partial=False)
        == StatusExecucao.sucesso
    )


def test_determine_final_status_incompleto_when_failures_and_allow_partial():
    pages = [
        ResultadoPagina(1, Metodo.texto_nativo, StatusExecucao.sucesso, 10, 10),
        ResultadoPagina(2, Metodo.erro, StatusExecucao.falha, 0, 20),
    ]

    assert (
        determine_final_status(pages, allow_partial=True)
        == StatusExecucao.incompleto
    )


def test_determine_final_status_falha_when_failures_and_not_allow_partial():
    pages = [
        ResultadoPagina(1, Metodo.texto_nativo, StatusExecucao.sucesso, 10, 10),
        ResultadoPagina(2, Metodo.erro, StatusExecucao.falha, 0, 20),
    ]

    assert (
        determine_final_status(pages, allow_partial=False)
        == StatusExecucao.falha
    )


def test_determine_final_status_empty_pages_is_sucesso():
    assert determine_final_status([], allow_partial=False) == StatusExecucao.sucesso


def test_determine_final_status_never_sucesso_with_any_failure():
    pages = [
        ResultadoPagina(1, Metodo.erro, StatusExecucao.falha, 0, 10),
    ]

    for allow_partial in [True, False]:
        result = determine_final_status(pages, allow_partial=allow_partial)

        assert result != StatusExecucao.sucesso
