from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pipeline_juridico.domain_router_cli import _build_parser, main


MARKDOWN = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nSentença judicial de mérito\nTribunal de Justiça\nSegredo de justiça literal XYZ\n"


def _write_artifacts(tmp_path: Path, gate: str = "PASS") -> tuple[Path, Path, Path, dict]:
    evidence = tmp_path / "Decisão.pdf"
    evidence.write_bytes(b"pdf evidence")
    markdown = tmp_path / "phase1.md"
    markdown.write_text(MARKDOWN, encoding="utf-8")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    report = {
        "schema_version": "1.0", "execution_id": "process-execution-1",
        "input": {"sha256": digest, "byte_size": evidence.stat().st_size,
                  "page_count": 1},
        "phase1": {"implementation": "shared-core",
                   "implementation_version": "1.0",
                   "logical_processing_version": "1.0",
                   "relevant_config_fingerprint": "config-a"},
        "result": {"quality_gate": gate, "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": hashlib.sha256(MARKDOWN.encode()).hexdigest()},
        "pages": [{"page_number": 1, "method": "texto_nativo",
                   "char_count": len(MARKDOWN), "warnings": [], "errors": [],
                   "truncated": False}], "telemetry": {},
    }
    report_path = tmp_path / "phase1.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return markdown, report_path, evidence, report


def _write_routing_record(tmp_path: Path, report: dict,
                          decision: str = "judicial_process") -> Path:
    state = tmp_path / "routing"
    state.mkdir(parents=True)
    reason = ("requested_domain_judicial_process" if decision == "judicial_process"
              else "requested_domain_legal_knowledge")
    (state / f'{report["execution_id"]}.json').write_text(json.dumps(
        {"schema_version": "1.0", "record_type": "routing",
         "provenance_sha256": report["input"]["sha256"],
         "decision": decision, "reason": reason}
    ))
    return state


def test_process_cli_is_registered() -> None:
    args = _build_parser().parse_args(["process", "validate", "candidate.md"])
    assert args.command == "process" and args.process_command == "validate"


def test_build_reads_route_emits_candidate_record_and_never_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path)
    routing = _write_routing_record(tmp_path, report)
    monkeypatch.setenv("ROUTING_STATE_DIR", str(routing))
    process_root, state = tmp_path / "process", tmp_path / "state"
    before = markdown.read_bytes(), report_path.read_bytes()
    code = main(["process", "build", str(markdown), str(report_path),
                 "--type", "Decisao", "--evidence-resource", str(evidence),
                 "--process-root", str(process_root), "--state-dir", str(state),
                 "--json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["candidate"].startswith('---\ntype: "Decisao"')
    assert not process_root.exists()
    assert before == (markdown.read_bytes(), report_path.read_bytes())
    record = json.loads((state / "process-execution-1.json").read_text())
    assert record["record_type"] == "process.build"
    assert record["routing_decision"] == "judicial_process"
    assert record["review"] == {"patch_count": 0, "review_required": False}
    assert "Segredo de justiça literal XYZ" not in json.dumps(record)


def test_absent_or_non_process_route_is_blocked_and_recorded(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path)
    empty = tmp_path / "routing-empty"
    empty.mkdir()
    monkeypatch.setenv("ROUTING_STATE_DIR", str(empty))
    state = tmp_path / "state"
    before = markdown.read_bytes(), report_path.read_bytes()
    base = ["process", "build", str(markdown), str(report_path), "--type",
            "Decisao", "--evidence-resource", str(evidence), "--state-dir", str(state)]
    assert main(base) == 5
    assert (state / "process-execution-1.json").is_file()
    assert before == (markdown.read_bytes(), report_path.read_bytes())
    routing = _write_routing_record(tmp_path / "legal", report, "legal_knowledge")
    monkeypatch.setenv("ROUTING_STATE_DIR", str(routing))
    assert main(base) == 5
    assert before == (markdown.read_bytes(), report_path.read_bytes())


@pytest.mark.parametrize(
    ("field", "value", "remove"),
    [
        ("provenance_sha256", "0" * 64, False),
        ("provenance_sha256", None, True),
        ("provenance_sha256", "A" * 64, False),
        ("record_type", "process.build", False),
        ("schema_version", "2.0", False),
    ],
    ids=["provenance-mismatch", "missing-provenance", "malformed-provenance",
         "wrong-record-type", "unsupported-schema-version"],
)
def test_invalid_routing_record_is_configuration_error_without_mutating_phase1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    field: str, value: object, remove: bool,
) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path)
    routing = _write_routing_record(tmp_path, report)
    record_path = routing / "process-execution-1.json"
    record = json.loads(record_path.read_text())
    if remove:
        del record[field]
    else:
        record[field] = value
    record_path.write_text(json.dumps(record))
    monkeypatch.setenv("ROUTING_STATE_DIR", str(routing))
    before = markdown.read_bytes(), report_path.read_bytes()

    assert main(["process", "build", str(markdown), str(report_path), "--type",
                 "Decisao", "--evidence-resource", str(evidence),
                 "--state-dir", str(tmp_path / "state")]) == 3
    assert before == (markdown.read_bytes(), report_path.read_bytes())


def test_build_then_validate_then_publish_is_single_storage_write_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path)
    routing = _write_routing_record(tmp_path, report)
    monkeypatch.setenv("ROUTING_STATE_DIR", str(routing))
    root, state = tmp_path / "process", tmp_path / "state"
    args = ["process", "build", str(markdown), str(report_path), "--type",
            "Decisao", "--evidence-resource", str(evidence), "--process-root",
            str(root), "--state-dir", str(state), "--json"]
    assert main(args) == 0
    candidate = tmp_path / "candidate.md"
    candidate.write_text(json.loads(capsys.readouterr().out)["candidate"])
    assert main(["process", "validate", str(candidate), "--process-root", str(root)]) == 0
    assert not root.exists()
    capsys.readouterr()
    assert main(["process", "publish", str(candidate), "--process-root", str(root),
                 "--state-dir", str(state), "--json"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["publication_result"] == "published"
    assert (root / "decisao" / "decisao.md").is_file()
    publish_record = json.loads((state / f'{report["input"]["sha256"]}.json').read_text())
    assert publish_record["record_type"] == "process.publish"


@pytest.mark.parametrize("payload", [{"type": "Other"},
    {"type": "Decisao", "unknown": True}, []])
def test_invalid_context_is_configuration_error(
    tmp_path: Path, payload: object
) -> None:
    markdown, report_path, evidence, _ = _write_artifacts(tmp_path)
    context = tmp_path / "context.json"
    context.write_text(json.dumps(payload))
    assert main(["process", "build", str(markdown), str(report_path),
                 "--context", str(context), "--evidence-resource", str(evidence)]) == 3


def test_state_dir_inside_process_or_bundle_is_configuration_error(tmp_path: Path) -> None:
    markdown, report_path, evidence, _ = _write_artifacts(tmp_path)
    root = tmp_path / "process"
    base = ["process", "build", str(markdown), str(report_path), "--type",
            "Decisao", "--evidence-resource", str(evidence),
            "--process-root", str(root)]
    assert main(base + ["--state-dir", str(root / "state")]) == 3


def test_build_gate_fail_is_blocked_with_review_required_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path, gate="FAIL")
    routing = _write_routing_record(tmp_path, report)
    monkeypatch.setenv("ROUTING_STATE_DIR", str(routing))
    state = tmp_path / "state"
    assert main(["process", "build", str(markdown), str(report_path), "--type",
                 "Decisao", "--evidence-resource", str(evidence),
                 "--state-dir", str(state)]) == 5
    record = json.loads((state / "process-execution-1.json").read_text())
    assert record["record_type"] == "process.review_required"
    assert record["publication_result"] == "blocked"
    assert not (tmp_path / "process").exists()


def test_publish_human_review_blocks_without_write_or_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys
) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path)
    routing = _write_routing_record(tmp_path, report)
    monkeypatch.setenv("ROUTING_STATE_DIR", str(routing))
    root, state = tmp_path / "process", tmp_path / "state"
    assert main(["process", "build", str(markdown), str(report_path), "--type",
                 "Decisao", "--evidence-resource", str(evidence),
                 "--process-root", str(root), "--state-dir", str(state),
                 "--json"]) == 0
    candidate = tmp_path / "candidate.md"
    candidate.write_text(json.loads(capsys.readouterr().out)["candidate"])
    target = root / "decisao" / "decisao.md"
    target.parent.mkdir(parents=True)
    target.write_text(candidate.read_text().replace("Segredo de justiça literal XYZ",
                                                    "material antigo"))
    (state / "process-execution-1.json").unlink()
    assert main(["process", "publish", str(candidate), "--process-root",
                 str(root), "--state-dir", str(state)]) == 5
    assert "material antigo" in target.read_text()
    assert not (state / "process-execution-1.json").exists()
    assert not (state / f'{report["input"]["sha256"]}.json').exists()


def test_unexpected_error_exits_two(tmp_path: Path, monkeypatch) -> None:
    import pipeline_juridico.process_producer_cli as module
    monkeypatch.setattr(module, "_run_build",
                        lambda args, logger: (_ for _ in ()).throw(RuntimeError("boom")))
    assert main(["process", "build", "a.md", "b.json"]) == 2


def test_publish_record_is_content_safe(tmp_path: Path, capsys) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path)
    candidate = tmp_path / "candidate.md"
    digest = report["input"]["sha256"]
    frontmatter_lines = [
        "---",
        'type: "Decisao"',
        'generated: {"by":"repo_jur_process_producer/1.0"}',
        'sources: [{"id":"pdf_1","resource":"' + str(evidence) +
        '","media_type":"application/pdf"}]',
        'repo_jur_pdf_hash: "' + digest + '"',
        'repo_jur_evidence_sha256: "' + digest + '"',
        'repo_jur_phase1: {"implementation":"shared-core",'
        '"implementation_version":"1.0",'
        '"logical_processing_version":"1.0",'
        '"relevant_config_fingerprint":"config-a",'
        '"quality_gate":"PASS"}',
        "---",
        "Segredo de justiça literal XYZ",
        "",
    ]
    candidate.write_text("\n".join(frontmatter_lines), encoding="utf-8")
    state = tmp_path / "state"
    assert main(["process", "publish", str(candidate),
                 "--process-root", str(tmp_path / "process"),
                 "--state-dir", str(state)]) == 0
    record = json.loads((state / f"{digest}.json").read_text())
    assert record["record_type"] == "process.publish"
    assert record["routing_decision"] == "judicial_process"
    assert record["publication_result"] == "published"
    assert "Segredo de justiça literal XYZ" not in json.dumps(record)
    assert "CPF" not in json.dumps(record) and "selo" not in json.dumps(record)
    assert "patch_body" not in json.dumps(record)
    assert "token" not in json.dumps(record).lower()


# 5.14 — CLI source-inspection: no conversion/OCR/evidence coupling, and the
# only guarded write path is process publication.
def test_cli_source_has_no_conversion_coupling_and_guarded_write_only() -> None:
    import ast
    source = Path("src/pipeline_juridico/process_producer_cli.py").read_text()
    imports = [node.module or "" for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.ImportFrom)]
    for prohibited in ("converter", "conversion_engine", "engines",
                       "inspector", "ocr", "evidence"):
        assert all(prohibited not in module for module in imports)
    assert "guard_process_write" in source
    assert "guard_legal_bundle_write" not in source


# 5.16 — CLI non-regression: route and producer surfaces still work through the
# same entry point; converter-juridico entry point is untouched.
def test_route_and_producer_surfaces_are_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    markdown, report_path, evidence, report = _write_artifacts(tmp_path)
    assert main(["route", str(markdown), str(report_path), "--domain",
                 "judicial_process", "--state-dir",
                 str(tmp_path / "routing")]) == 0

    # Supply a Legal Knowledge Markdown specifically for the producer surface test
    lk_markdown = tmp_path / "lk_phase1.md"
    lk_markdown.write_text(
        "[[Pág. 1]]\n<!-- método: texto_nativo -->\nPresidência da República\nLEI COMPLEMENTAR Nº 123, DE 10 DE JANEIRO DE 2002\nConteúdo legal desu",
        encoding="utf-8"
    )
    lk_report = dict(report)
    lk_report["artifacts"] = {"markdown_sha256": hashlib.sha256(lk_markdown.read_bytes()).hexdigest()}
    lk_report_path = tmp_path / "lk_phase1.json"
    lk_report_path.write_text(json.dumps(lk_report), encoding="utf-8")

    assert main(["producer", "build", str(lk_markdown), str(lk_report_path),
                 "--type", "Legislacao", "--evidence-resource", str(evidence),
                 "--bundle-root", str(tmp_path / "bundle"),
                 "--state-dir", str(tmp_path / "pstate")]) == 0
