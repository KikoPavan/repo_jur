"""Conformance tests for the Stage 10 operational CLI tooling."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from pipeline_juridico import domain_router_cli


@pytest.mark.conformance
def test_5_1_conformance_cli_arguments() -> None:
    parser = domain_router_cli._build_parser()

    defaults = parser.parse_args(["test", "conformance"])
    assert defaults.command == "test"
    assert defaults.test_action == "conformance"
    assert defaults.json_report == "var/conformance/report.json"
    assert defaults.verbose is False

    overridden = parser.parse_args(
        ["test", "conformance", "--json-report", "result.json", "--verbose"]
    )
    assert overridden.json_report == "result.json"
    assert overridden.verbose is True


@pytest.mark.conformance
def test_5_2_cli_exit_codes_and_report_categories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(domain_router_cli, "_configuration_errors", lambda: [])
    monkeypatch.setattr(
        domain_router_cli, "validate_contract_imports", lambda _path=None: []
    )
    monkeypatch.setattr(
        domain_router_cli, "validate_no_vector_infrastructure", lambda: []
    )

    expected_commands = [
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "conformance",
            "tests/test_conformance/",
        ],
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "regression",
            "tests/test_conformance/",
        ],
    ]

    scenarios = (
        ((0, 0), 0, []),
        ((1, 0), 1, ["CONFORMANCE_FAILURE"]),
        ((0, 1), 1, ["REGRESSION_FAILURE"]),
    )
    for index, (return_codes, expected_exit, categories) in enumerate(scenarios):
        calls: list[list[str]] = []

        def fake_run(
            command: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            calls.append(command)
            code = return_codes[len(calls) - 1]
            return subprocess.CompletedProcess(command, code, "pytest output", "")

        monkeypatch.setattr(domain_router_cli.subprocess, "run", fake_run)
        report_path = tmp_path / f"report-{index}.json"
        assert domain_router_cli.main(
            ["test", "conformance", "--json-report", str(report_path)]
        ) == expected_exit
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["exit_code"] == expected_exit
        assert [failure["category"] for failure in report["failures"]] == categories
        assert calls == expected_commands

    monkeypatch.setattr(
        domain_router_cli,
        "_configuration_errors",
        lambda: ["pytest is not installed in the active Python environment"],
    )
    monkeypatch.setattr(
        domain_router_cli.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail(
            "pytest must not run after preflight failure"
        ),
    )
    report_path = tmp_path / "environment-error.json"
    assert domain_router_cli.main(
        ["test", "conformance", "--json-report", str(report_path)]
    ) == 2
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["exit_code"] == 2
    assert [failure["category"] for failure in report["failures"]] == [
        "ENVIRONMENT_CONFIGURATION_ERROR"
    ]


@pytest.mark.conformance
def test_5_3_contracts_source_import_inspection(tmp_path: Path) -> None:
    source = tmp_path / "contracts.py"
    source.write_text("from dataclasses import dataclass\n", encoding="utf-8")
    assert domain_router_cli.validate_contract_imports(source) == []

    source.write_text(
        "from pipeline_juridico.retrieval.index import SqliteFts5Index\n"
        "import pipeline_juridico.process_producer\n"
        "from . import legal_semantic_review\n",
        encoding="utf-8",
    )
    violations = domain_router_cli.validate_contract_imports(source)
    assert len(violations) == 3
    assert any("pipeline_juridico.retrieval.index" in item for item in violations)
    assert any("pipeline_juridico.process_producer" in item for item in violations)
    assert any("pipeline_juridico.legal_semantic_review" in item for item in violations)


@pytest.mark.conformance
def test_5_4_no_vector_infrastructure_invariant() -> None:
    assert domain_router_cli.validate_no_vector_infrastructure(
        installed_distributions={"pytest", "pymupdf"},
        loaded_modules={"pytest", "pipeline_juridico"},
    ) == []

    violations = domain_router_cli.validate_no_vector_infrastructure(
        installed_distributions={"sentence-transformers", "qdrant-client"},
        loaded_modules={"faiss", "sentence_transformers.models", "pinecone"},
    )
    assert any("sentence-transformers" in item for item in violations)
    assert any("qdrant-client" in item for item in violations)
    assert any("faiss" in item for item in violations)
    assert any("sentence_transformers" in item for item in violations)
    assert any("pinecone" in item for item in violations)
