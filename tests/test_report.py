import json
import re
from dataclasses import asdict

import pytest

from pipeline_juridico.hashing import sha256_file
from pipeline_juridico.models import (ArtifactsInfo, DocumentFidelityAudit,
    DocumentFidelityIssue, FidelityGroup, InputInfo, Metodo, NumericOccurrence,
    OcrInfo, Phase1Info, Relatorio, ResultadoInfo, ResultadoPagina, RuntimeInfo,
    StatusExecucao)
from pipeline_juridico.report import (ReportContractError, attach_gate_result,
    build_candidate_report_json, build_ocr_info, build_page_result,
    build_report_json, build_runtime_info, compute_relevant_config_fingerprint,
    determine_final_status, ocr_page_numbers, validate_report_contract)


def _candidate():
    return Relatorio(execution_id="id", input=InputInfo("a" * 64, 1, 1),
        phase1=Phase1Info("pipeline", "0.1", "1", "f"),
        artifacts=ArtifactsInfo("b" * 64),
        pages=[ResultadoPagina(1, Metodo.texto_nativo, 3)], telemetry={})


def _data():
    return json.loads(build_report_json(attach_gate_result(_candidate(), quality_gate="PASS")))


def test_synchronized_report_model_is_available():
    assert ArtifactsInfo(markdown_sha256="abc").markdown_sha256 == "abc"


def test_minimum_layout_and_page_wire_shape():
    data = _data()
    assert set(data) == {"schema_version", "execution_id", "input", "phase1", "result", "artifacts", "fidelity_audit", "pages", "telemetry"}
    assert data["schema_version"] == "1.2"
    assert data["fidelity_audit"] == {"issues": []}
    assert data["pages"][0] == {
        "page_number": 1,
        "method": "texto_nativo",
        "char_count": 3,
        "warnings": [],
        "errors": [],
        "truncated": False,
        "fidelity_audit": None,
    }
    validate_report_contract(data)


@pytest.mark.parametrize("path", ["input.sha256", "artifacts.markdown_sha256"])
@pytest.mark.parametrize(
    "value",
    ["a" * 63, "a" * 65, "g" + "a" * 63, "-" + "a" * 63, "A" * 64],
)
def test_sha256_fields_reject_non_lowercase_64_hex(path, value):
    data = _data()
    block, field = path.split(".")
    data[block][field] = value
    with pytest.raises(ReportContractError, match=path):
        validate_report_contract(data)


@pytest.mark.parametrize(
    ("input_sha256", "markdown_sha256"),
    [("0" * 64, "f" * 64), ("0123456789abcdef" * 4, "abcdef0123456789" * 4)],
)
def test_sha256_fields_accept_lowercase_64_hex(input_sha256, markdown_sha256):
    data = _data()
    data["input"]["sha256"] = input_sha256
    data["artifacts"]["markdown_sha256"] = markdown_sha256
    validate_report_contract(data)


@pytest.mark.parametrize("field", ["schema_version", "execution_id", "input", "phase1", "result", "artifacts", "fidelity_audit", "pages", "telemetry"])
def test_required_top_level_fields(field):
    data = _data(); del data[field]
    with pytest.raises(ReportContractError, match=field): validate_report_contract(data)


@pytest.mark.parametrize("value", ["PASS WITH WARNINGS", "sucesso", ""])
def test_gate_vocabulary_is_exact(value):
    data = _data(); data["result"]["quality_gate"] = value
    with pytest.raises(ReportContractError): validate_report_contract(data)


@pytest.mark.parametrize("value", [True, False])
def test_explicit_truncation_boolean_is_contract_valid(value):
    data = _data(); data["pages"][0]["truncated"] = value
    validate_report_contract(data)


@pytest.mark.parametrize("value", [None, 0, "false"])
def test_truncation_is_mandatory_exact_boolean(value):
    data = _data()
    if value is None: del data["pages"][0]["truncated"]
    else: data["pages"][0]["truncated"] = value
    with pytest.raises(ReportContractError, match="truncated"): validate_report_contract(data)


def test_candidate_invalid_final_valid_and_attachment_nonmutating():
    candidate = _candidate(); before = build_candidate_report_json(candidate)
    assert "result" not in json.loads(before)
    with pytest.raises(ReportContractError): validate_report_contract(json.loads(before))
    final = attach_gate_result(candidate, quality_gate="FAIL", warnings=("w",), errors=("e",))
    assert build_candidate_report_json(candidate) == before
    assert final.result == ResultadoInfo("FAIL", ["w"], ["e"])
    final_data = json.loads(build_report_json(final))
    assert final_data["result"]["quality_gate"] == "FAIL"
    validate_report_contract(final_data)


def test_telemetry_content_is_non_normative():
    data = _data(); data["telemetry"] = {"runtime": {"python": "x"}, "input_path": "/x", "page_durations_ms": [1]}
    validate_report_contract(data)
    data["telemetry"] = []
    with pytest.raises(ReportContractError, match="telemetry"): validate_report_contract(data)


def test_page_builder_counts_only_and_never_infers_truncation():
    page = build_page_result(1, Metodo.erro, "secret", warnings=["w"], errors=["e"])
    assert page.char_count == 6 and page.truncated is False
    assert "secret" not in str(asdict(page))


def test_runtime_info_contains_nonempty_versions():
    runtime = build_runtime_info()
    assert isinstance(runtime, RuntimeInfo)
    assert all((runtime.python, runtime.markitdown, runtime.markitdown_ocr,
                runtime.pymupdf))


def test_ocr_info_passes_configuration_and_hashes_prompt(tmp_path):
    prompt_path = tmp_path / "prompt.txt"
    prompt_path.write_text("prompt pequeno", encoding="utf-8")
    info = build_ocr_info(True, "provider", "model", prompt_path)
    assert isinstance(info, OcrInfo)
    assert (info.enabled, info.provider, info.model) == (True, "provider", "model")
    assert info.prompt_sha256 == sha256_file(prompt_path)


def test_page_builder_defaults_and_never_stores_content():
    content = "conteúdo confidencial"
    page = build_page_result(1, Metodo.texto_nativo, content)
    assert page.warnings == []
    assert page.errors == []
    assert page.truncated is False
    assert page.char_count == len(content)
    assert content not in str(asdict(page))


def test_helpers_follow_renamed_fields_and_internal_status():
    pages = [ResultadoPagina(3, Metodo.hibrido, 3),
             ResultadoPagina(2, Metodo.ocr_integral, 2),
             ResultadoPagina(1, Metodo.erro, 0)]
    assert ocr_page_numbers(pages) == [2, 3]
    assert determine_final_status(pages, False) is StatusExecucao.falha
    assert determine_final_status(pages, True) is StatusExecucao.incompleto


def test_ocr_page_numbers_empty_without_ocr_or_hybrid_pages():
    pages = [ResultadoPagina(1, Metodo.texto_nativo, 2),
             ResultadoPagina(2, Metodo.vazia, 0)]
    assert ocr_page_numbers(pages) == []


@pytest.mark.parametrize(
    ("pages", "allow_partial", "expected"),
    [
        ([], False, StatusExecucao.sucesso),
        ([ResultadoPagina(1, Metodo.texto_nativo, 1)], True,
         StatusExecucao.sucesso),
        ([ResultadoPagina(1, Metodo.erro, 0)], True,
         StatusExecucao.incompleto),
        ([ResultadoPagina(1, Metodo.erro, 0)], False,
         StatusExecucao.falha),
    ],
)
def test_determine_final_status(pages, allow_partial, expected):
    assert determine_final_status(pages, allow_partial) is expected


def test_invalid_page_method_names_offending_path():
    data = _data()
    data["pages"][0]["method"] = "metodo_que_nao_existe"
    with pytest.raises(ReportContractError, match=r"pages\[0\]\.method"):
        validate_report_contract(data)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        ("input.sha256", 1),
        ("input.page_count", "1"),
        ("input.byte_size", "1"),
        ("phase1.implementation", 1),
        ("result.warnings", "warning"),
        ("artifacts.markdown_sha256", 1),
        ("pages[0].page_number", "1"),
        ("pages[0].char_count", "3"),
        ("pages[0].warnings", "warning"),
    ],
)
def test_wrong_nested_field_types_name_offending_path(path, value):
    data = _data()
    if path.startswith("pages[0]."):
        data["pages"][0][path.removeprefix("pages[0].")] = value
    else:
        block, field = path.split(".")
        data[block][field] = value
    with pytest.raises(ReportContractError, match=re.escape(path)):
        validate_report_contract(data)


def test_schema_1_1_requires_document_fidelity_audit():
    data = _data()
    del data["fidelity_audit"]
    with pytest.raises(ReportContractError, match="fidelity_audit"):
        validate_report_contract(data)


def test_schema_1_2_with_document_fidelity_audit_is_valid():
    data = _data()
    data["schema_version"] = "1.2"

    validate_report_contract(data)


def test_legacy_schema_versions_remain_valid():
    schema_1_0 = _data()
    schema_1_0["schema_version"] = "1.0"
    del schema_1_0["fidelity_audit"]
    validate_report_contract(schema_1_0)

    schema_1_1 = _data()
    schema_1_1["schema_version"] = "1.1"
    schema_1_1["pages"][0]["fidelity_audit"] = {
        "issues": [
            {
                "issue_id": "123e4567-e89b-42d3-a456-426614174000",
                "detector": "internal_repetition_detector",
                "issue_type": "duplication",
                "page_number": 1,
                "resolution": "flagged",
                "offset_start": 0,
                "offset_end": 3,
                "size": 3,
                "related_offsets": [0],
            }
        ]
    }
    validate_report_contract(schema_1_1)


def test_result_warnings_remains_strictly_list_of_strings():
    data = _data()
    data["result"]["warnings"] = ["texto", {"issue_type": "entity_inconsistency"}]
    with pytest.raises(ReportContractError, match=r"result\.warnings\[1\]"):
        validate_report_contract(data)


def test_document_fidelity_contract_accepts_only_numeric_occurrences():
    report = _candidate()
    report.fidelity_audit = DocumentFidelityAudit(issues=[
        DocumentFidelityIssue(
            issue_id="123e4567-e89b-42d3-a456-426614174000",
            detector="entity_consistency_checker",
            issue_type="entity_inconsistency",
            resolution="flagged",
            groups=[FidelityGroup(group=0, occurrences=[
                NumericOccurrence(page_number=1, offset_start=0, offset_end=3, size=3)
            ])],
        )
    ])
    data = json.loads(build_report_json(attach_gate_result(report, quality_gate="PASS")))

    validate_report_contract(data)

    data["fidelity_audit"]["issues"][0]["groups"][0]["occurrences"][0]["text"] = "segredo"
    with pytest.raises(ReportContractError, match="occurrences"):
        validate_report_contract(data)


def test_document_fidelity_coordinate_must_fit_its_page():
    data = _data()
    data["fidelity_audit"]["issues"] = [{
        "issue_id": "123e4567-e89b-42d3-a456-426614174000",
        "detector": "entity_consistency_checker",
        "issue_type": "entity_inconsistency",
        "resolution": "flagged",
        "groups": [{"group": 0, "occurrences": [{
            "page_number": 1, "offset_start": 0, "offset_end": 4, "size": 4,
        }]}],
    }]
    with pytest.raises(ReportContractError, match="offset_end"):
        validate_report_contract(data)


def test_config_fingerprint_is_deterministic_and_sensitive():
    a = compute_relevant_config_fingerprint(allow_partial=False, use_ocr=True, routing_config=None)
    assert a == compute_relevant_config_fingerprint(allow_partial=False, use_ocr=True, routing_config=None)
    assert a != compute_relevant_config_fingerprint(allow_partial=True, use_ocr=True, routing_config=None)
