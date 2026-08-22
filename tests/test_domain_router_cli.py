from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from pipeline_juridico import cli
from pipeline_juridico import config as config_module
from pipeline_juridico import domain_router_cli
from pipeline_juridico.domain_router_cli import main


def _page(number: int) -> dict[str, object]:
    return {
        "page_number": number,
        "method": "texto_nativo",
        "char_count": 20,
        "warnings": [],
        "errors": [],
        "truncated": False,
    }


def _report(
    *,
    gate: str = "PASS",
    execution_id: str = "00000000-0000-0000-0000-000000000001",
    sha256: str = "a" * 64,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "execution_id": execution_id,
        "input": {
            "byte_size": 1234,
            "sha256": sha256,
            "page_count": 1,
        },
        "phase1": {
            "implementation": "pipeline-juridico",
            "implementation_version": "1.0",
            "logical_processing_version": "1.0",
            "relevant_config_fingerprint": "c" * 64,
        },
        "artifacts": {"markdown_sha256": "b" * 64},
        "telemetry": {},
        "pages": [_page(1)],
        "result": {"quality_gate": gate, "warnings": [], "errors": []},
    }


def _write_artifacts(
    tmp_path: Path,
    *,
    gate: str = "PASS",
    execution_id: str = "00000000-0000-0000-0000-000000000001",
    markdown: str = "[[Pág. 1]]\nConteúdo literal\n",
) -> tuple[Path, Path]:
    md_path = tmp_path / "fase1.md"
    report_path = tmp_path / "fase1.report.json"
    md_path.write_text(markdown, encoding="utf-8")
    report_path.write_text(
        json.dumps(_report(gate=gate, execution_id=execution_id), ensure_ascii=False),
        encoding="utf-8",
    )
    return md_path, report_path


def _write_context(tmp_path: Path, payload: object) -> Path:
    context_path = tmp_path / "context.json"
    context_path.write_text(json.dumps(payload), encoding="utf-8")
    return context_path


def _record_path(state_dir: Path) -> Path:
    return state_dir / "00000000-0000-0000-0000-000000000001.json"


# ---------------------------------------------------------------------------
# 3.1 Route command surface
# ---------------------------------------------------------------------------


def test_route_domain_legal_knowledge_reads_artifacts_and_writes_record(
    tmp_path,
    capsys,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "legal_knowledge",
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 0
    assert "decision: legal_knowledge" in capsys.readouterr().out
    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "legal_knowledge"


def test_route_domain_judicial_process_selects_judicial_process(
    tmp_path,
    capsys,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "judicial_process",
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 0
    assert "decision: judicial_process" in capsys.readouterr().out
    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "judicial_process"


def test_route_context_file_supplies_requested_domain(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, {"requested_domain": "legal_knowledge"})
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 0
    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "legal_knowledge"


def test_route_without_domain_or_context_yields_review_required(
    tmp_path,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    state_dir = tmp_path / "state"

    result = main(
        ["route", str(md_path), str(report_path), "--state-dir", str(state_dir)]
    )

    assert result == 0
    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "review_required"
    assert record["reason"] == "missing_routing_signal"


def test_route_empty_context_object_yields_review_required(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, {})
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 0
    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "review_required"


def test_route_disagreeing_domain_and_context_exit_3(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, {"requested_domain": "judicial_process"})
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "legal_knowledge",
            "--context",
            str(context_path),
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 3
    assert not _record_path(state_dir).exists()


def test_route_agreeing_domain_and_context_exit_0(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, {"requested_domain": "judicial_process"})
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "judicial_process",
            "--context",
            str(context_path),
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 0
    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "judicial_process"


def test_route_json_output_is_machine_readable(tmp_path, capsys) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "legal_knowledge",
            "--state-dir",
            str(state_dir),
            "--json",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "decision": "legal_knowledge",
        "reason": "requested_domain_legal_knowledge",
        "record_path": str(_record_path(state_dir).resolve()),
    }


def test_route_state_dir_defaults_to_var_routing_state(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ROUTING_STATE_DIR", raising=False)

    result = main(["route", str(md_path), str(report_path)])

    assert result == 0
    record = json.loads(
        (tmp_path / "var" / "routing" / "state" / _record_path(Path()).name)
        .read_text(encoding="utf-8")
    )
    assert record["decision"] == "review_required"


def test_route_state_dir_is_environment_overridable(
    tmp_path,
    monkeypatch,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    env_state = tmp_path / "env-state"
    monkeypatch.setenv("ROUTING_STATE_DIR", str(env_state))

    result = main(["route", str(md_path), str(report_path)])

    assert result == 0
    assert _record_path(env_state).is_file()


def test_route_state_dir_flag_overrides_environment(
    tmp_path,
    monkeypatch,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    env_state = tmp_path / "env-state"
    flag_state = tmp_path / "flag-state"
    monkeypatch.setenv("ROUTING_STATE_DIR", str(env_state))

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--state-dir",
            str(flag_state),
        ]
    )

    assert result == 0
    assert _record_path(flag_state).is_file()
    assert not _record_path(env_state).exists()


# ---------------------------------------------------------------------------
# 3.2 Route-command exit codes
# ---------------------------------------------------------------------------


def test_route_exit_0_records_decision(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)

    assert main(
        ["route", str(md_path), str(report_path), "--state-dir", str(tmp_path / "s")]
    ) == 0


def test_route_exit_3_for_unparseable_report(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    report_path.write_text("não é json", encoding="utf-8")

    assert main(
        ["route", str(md_path), str(report_path), "--state-dir", str(tmp_path / "s")]
    ) == 3


def test_route_exit_3_for_report_missing_gate_outcome(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    report = _report()
    report["result"] = {"warnings": [], "errors": []}
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert main(
        ["route", str(md_path), str(report_path), "--state-dir", str(tmp_path / "s")]
    ) == 3


def test_route_exit_3_for_report_missing_provenance_hash(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    report = _report()
    input_info = report["input"]
    assert isinstance(input_info, dict)
    input_info["sha256"] = ""
    report_path.write_text(json.dumps(report), encoding="utf-8")

    assert main(
        ["route", str(md_path), str(report_path), "--state-dir", str(tmp_path / "s")]
    ) == 3


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("execution_id", ""),
        ("phase1", {}),
        ("telemetry", []),
    ],
)
def test_route_exit_3_for_invalid_report_contract_surface(
    tmp_path, field: str, value: object
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    report = _report()
    report[field] = value
    report_path.write_text(json.dumps(report), encoding="utf-8")
    state_dir = tmp_path / "s"

    assert main(
        ["route", str(md_path), str(report_path), "--state-dir", str(state_dir)]
    ) == 3
    assert not state_dir.exists()


def test_route_exit_3_for_unknown_context_key(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, {"legal_hints": {"process_number": "x"}})

    assert main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 3


def test_route_exit_3_for_invalid_context_value(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, {"requested_domain": "review_required"})

    assert main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 3


def test_route_exit_3_for_malformed_context_file(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = tmp_path / "context.json"
    context_path.write_text("não é json", encoding="utf-8")

    assert main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 3


def test_route_exit_3_for_non_object_context_file(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, ["requested_domain"])

    assert main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 3


def test_route_exit_3_for_unreadable_context_file(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)

    assert main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(tmp_path / "ausente.json"),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 3


def test_route_exit_3_for_non_utf8_context_file(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = tmp_path / "context.json"
    context_path.write_bytes(b"\xff")

    assert main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 3


def test_route_exit_3_for_invalid_domain_flag_value(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)

    assert main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "review_required",
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 3


def test_route_exit_1_for_missing_markdown_file(tmp_path) -> None:
    _md_path, report_path = _write_artifacts(tmp_path)

    assert main(
        [
            "route",
            str(tmp_path / "ausente.md"),
            str(report_path),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 1


def test_route_exit_1_for_missing_report_file(tmp_path) -> None:
    md_path, _report_path = _write_artifacts(tmp_path)

    assert main(
        [
            "route",
            str(md_path),
            str(tmp_path / "ausente.report.json"),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    ) == 1


@pytest.mark.parametrize("artifact", ["markdown", "report"])
def test_route_exit_1_for_non_utf8_artifact(tmp_path, artifact: str) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    target = md_path if artifact == "markdown" else report_path
    target.write_bytes(b"\xff")

    assert main(
        ["route", str(md_path), str(report_path), "--state-dir", str(tmp_path / "s")]
    ) == 1


def test_route_exit_5_for_fail_gate_without_decision_or_record(
    tmp_path,
    capsys,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path, gate="FAIL")
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "legal_knowledge",
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 5
    output = capsys.readouterr().out
    assert "blocked:" in output
    assert "decision:" not in output
    assert not _record_path(state_dir).exists()
    assert not state_dir.exists()


def test_route_exit_5_json_emits_blocked_payload(tmp_path, capsys) -> None:
    md_path, report_path = _write_artifacts(tmp_path, gate="FAIL")
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--state-dir",
            str(state_dir),
            "--json",
        ]
    )

    assert result == 5
    payload = json.loads(capsys.readouterr().out)
    assert "decision" not in payload
    assert "FAIL" in payload["blocked_reason"]


def test_route_exit_2_for_unexpected_error(
    tmp_path,
    monkeypatch,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)

    def explode(*_args, **_kwargs):
        raise RuntimeError("falha inesperada simulada")

    monkeypatch.setattr(domain_router_cli, "route", explode)

    assert main(
        ["route", str(md_path), str(report_path), "--state-dir", str(tmp_path / "s")]
    ) == 2


# ---------------------------------------------------------------------------
# 3.3 The route command never mutates the artifacts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("gate", ["PASS", "FAIL"])
def test_route_never_mutates_artifact_files(tmp_path, gate: str) -> None:
    md_path, report_path = _write_artifacts(tmp_path, gate=gate)
    markdown_before = md_path.read_bytes()
    report_before = report_path.read_bytes()

    main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "legal_knowledge",
            "--state-dir",
            str(tmp_path / "s"),
        ]
    )

    assert md_path.read_bytes() == markdown_before
    assert report_path.read_bytes() == report_before


def test_route_rejects_record_path_collision_with_phase1_report(tmp_path) -> None:
    md_path, report_path = _write_artifacts(
        tmp_path,
        execution_id="fase1.report",
    )
    report_before = report_path.read_bytes()

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--state-dir",
            str(tmp_path),
        ]
    )

    assert result == 3
    assert report_path.read_bytes() == report_before


def test_route_error_path_never_mutates_artifact_files(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    context_path = _write_context(tmp_path, {"bad_key": 1})
    markdown_before = md_path.read_bytes()
    report_before = report_path.read_bytes()

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--context",
            str(context_path),
            "--state-dir",
            str(tmp_path / "s"),
        ]
    )

    assert result == 3
    assert md_path.read_bytes() == markdown_before
    assert report_path.read_bytes() == report_before


# ---------------------------------------------------------------------------
# 3.4 The route command never invokes conversion or OCR and never touches
#     the bundle
# ---------------------------------------------------------------------------


def test_route_cli_source_has_no_conversion_or_bundle_write_path() -> None:
    source = Path("src/pipeline_juridico/domain_router_cli.py").read_text()

    for forbidden in (
        ".converter",
        ".engines",
        ".inspector",
        ".router",
        "guard_legal_bundle_write",
        "ocr",
        "evidence",
    ):
        assert forbidden not in source

    assert "load_dotenv" not in source
    assert "from dotenv" not in source
    tree = ast.parse(source)
    imported_modules = {
        alias.name.rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").rsplit(".", 1)[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not imported_modules & {
        "converter",
        "conversion_engine",
        "engines",
        "inspector",
        "evidence",
        "ocr",
        "router",
    }


def test_route_never_writes_under_canonical_bundle_or_process_storage(
    tmp_path,
    monkeypatch,
) -> None:
    bundle_dir = tmp_path / "repo_jur" / "bundle"
    process_dir = tmp_path / "process-storage"
    bundle_dir.mkdir(parents=True)
    process_dir.mkdir()
    md_path, report_path = _write_artifacts(tmp_path)
    state_dir = tmp_path / "state"

    main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "legal_knowledge",
            "--state-dir",
            str(state_dir),
        ]
    )

    assert list(bundle_dir.rglob("*")) == []
    assert list(process_dir.rglob("*")) == []


# ---------------------------------------------------------------------------
# 3.5 Observability at the CLI level
# ---------------------------------------------------------------------------


def test_route_record_content_is_safe_and_complete(tmp_path) -> None:
    secret_content = "CONTEUDO-CONFIDENCIAL-98765"
    md_path, report_path = _write_artifacts(
        tmp_path,
        markdown=f"[[Pág. 1]]\n{secret_content}\n",
    )
    state_dir = tmp_path / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--domain",
            "legal_knowledge",
            "--state-dir",
            str(state_dir),
        ]
    )

    assert result == 0
    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "legal_knowledge"
    assert record["reason"] == "requested_domain_legal_knowledge"
    assert record["gate"] == "PASS"
    assert record["critical_status"] == "OK"
    assert record["provenance_sha256"] == "a" * 64
    assert record["routing_context_keys"] == ["requested_domain"]
    assert record["execution_id"] == "00000000-0000-0000-0000-000000000001"
    serialized = json.dumps(record, ensure_ascii=False)
    assert secret_content not in serialized
    assert '"requested_domain": "legal_knowledge"' not in serialized
    assert "0001234-56.2020.8.26.0100" not in serialized


def test_route_record_without_signal_records_no_signal_keys(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    state_dir = tmp_path / "state"

    main(
        ["route", str(md_path), str(report_path), "--state-dir", str(state_dir)]
    )

    record = json.loads(_record_path(state_dir).read_text(encoding="utf-8"))
    assert record["decision"] == "review_required"
    assert record["routing_context_keys"] == []


def test_route_state_dir_inside_canonical_bundle_is_rejected(tmp_path) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    bundle_root = (
        Path(config_module.__file__).resolve().parents[2] / "bundle"
    )
    bad_state = bundle_root / "routing" / "state"

    result = main(
        [
            "route",
            str(md_path),
            str(report_path),
            "--state-dir",
            str(bad_state),
        ]
    )

    assert result == 3
    assert not bad_state.exists()


def test_route_state_dir_env_inside_canonical_bundle_is_rejected(
    tmp_path,
    monkeypatch,
) -> None:
    md_path, report_path = _write_artifacts(tmp_path)
    bundle_root = (
        Path(config_module.__file__).resolve().parents[2] / "bundle"
    )
    monkeypatch.setenv("ROUTING_STATE_DIR", str(bundle_root / "state"))

    assert main(["route", str(md_path), str(report_path)]) == 3


# ---------------------------------------------------------------------------
# 3.6 CLI non-regression: converter-juridico surface unchanged
# ---------------------------------------------------------------------------


def test_converter_cli_surface_is_unchanged() -> None:
    parser = cli._build_parser()

    option_strings = {
        option
        for action in parser._actions
        for option in action.option_strings
    }
    assert {
        "--overwrite",
        "--allow-partial",
        "--no-ocr",
        "--keep-temp",
        "--log-level",
    } <= option_strings

    positionals = [
        action for action in parser._actions if not action.option_strings
    ]
    assert positionals[0].dest == "pdf_path"


def test_pyproject_registers_repo_jur_without_changing_converter_entry() -> None:
    pyproject = (
        Path(__file__).parents[1] / "pyproject.toml"
    ).read_text(encoding="utf-8")

    assert 'converter-juridico = "pipeline_juridico.cli:main"' in pyproject
    assert 'repo-jur = "pipeline_juridico.domain_router_cli:main"' in pyproject
