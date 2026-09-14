import argparse
import json
import logging

from pipeline_juridico.ingest_cli import run
from pipeline_juridico.ingest_orchestrator import IngestFileRecord, IngestRunReport


def _args(tmp_path, **changes):
    values = dict(
        input_dir=str(tmp_path / "input"), bundle_root=str(tmp_path / "bundle"),
        state_dir=str(tmp_path / "state"), candidates_dir=str(tmp_path / "candidates"),
        reports_dir=str(tmp_path / "reports"), json=True,
    )
    values.update(changes)
    return argparse.Namespace(**values)


def test_json_shape_and_error_entries_still_exit_zero(tmp_path, monkeypatch, capsys) -> None:
    record = IngestFileRecord(
        "JUR_broken.pdf", "JUR_", "Jurisprudencia", "ERROR", "failure",
        None, None, [], [],
    )
    expected = IngestRunReport(
        "1.0", "run", str(tmp_path / "input"), [record],
        {"total": 1, "READY_TO_PUBLISH": 0, "REVIEW_REQUIRED": 0, "BLOCKED": 0, "ERROR": 1},
    )
    monkeypatch.setattr("pipeline_juridico.ingest_cli.run_ingest", lambda _: expected)
    assert run(_args(tmp_path), logging.getLogger("test")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {"schema_version", "run_id", "input_dir", "files", "summary"}
    assert payload["summary"]["ERROR"] == 1


def test_missing_input_dir_exits_one(tmp_path) -> None:
    assert run(_args(tmp_path), logging.getLogger("test")) == 1
