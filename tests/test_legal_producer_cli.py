from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pipeline_juridico.domain_router_cli import main


MARKDOWN = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nPresidência da República\nLEI Nº 10.406, DE 10 DE JANEIRO DE 2002\nSegredo literal XYZ\n"


def _write_artifacts(tmp_path: Path, *, gate: str = "PASS") -> tuple[Path, Path, Path]:
    evidence = tmp_path / "Lei 10.pdf"
    evidence.write_bytes(b"pdf evidence")
    markdown = tmp_path / "phase1.md"
    markdown.write_text(MARKDOWN, encoding="utf-8")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    report = {
        "schema_version": "1.0",
        "execution_id": "producer-execution-1",
        "input": {"sha256": digest, "byte_size": evidence.stat().st_size, "page_count": 1},
        "phase1": {
            "implementation": "shared-core",
            "implementation_version": "1.0",
            "logical_processing_version": "1.0",
            "relevant_config_fingerprint": "config-a",
        },
        "result": {"quality_gate": gate, "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": hashlib.sha256(MARKDOWN.encode()).hexdigest()},
        "pages": [{
            "page_number": 1, "method": "texto_nativo", "char_count": len(MARKDOWN),
            "warnings": [], "errors": [], "truncated": False,
        }],
        "telemetry": {},
    }
    report_path = tmp_path / "phase1.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return markdown, report_path, evidence


def _build(tmp_path: Path, *, extra: list[str] | None = None) -> tuple[int, Path, Path, Path]:
    markdown, report, evidence = _write_artifacts(tmp_path)
    bundle = tmp_path / "bundle"
    state = tmp_path / "state"
    args = [
        "producer", "build", str(markdown), str(report), "--type", "Legislacao",
        "--evidence-resource", str(evidence), "--bundle-root", str(bundle),
        "--state-dir", str(state), "--json",
    ]
    result = main(args + (extra or []))
    return result, bundle, state, markdown


def test_build_surface_context_merge_json_record_and_no_bundle_write(tmp_path: Path, capsys) -> None:
    markdown, report, evidence = _write_artifacts(tmp_path)
    context = tmp_path / "context.json"
    context.write_text(json.dumps({"type": "Legislacao", "evidence_resource": str(evidence)}))
    bundle, state = tmp_path / "bundle", tmp_path / "state"
    before = (markdown.read_bytes(), report.read_bytes())

    code = main(["producer", "build", str(markdown), str(report), "--type", "Legislacao",
                 "--evidence-resource", str(evidence), "--context", str(context),
                 "--bundle-root", str(bundle), "--state-dir", str(state), "--json"])

    assert code == 0
    outcome = json.loads(capsys.readouterr().out)
    assert outcome["candidate"].startswith("---\ntype: \"Legislacao\"")
    assert not bundle.exists()
    assert before == (markdown.read_bytes(), report.read_bytes())
    record = json.loads((state / "producer-execution-1.json").read_text())
    assert record["record_type"] == "producer.build"
    assert record["provenance_sha256"] == hashlib.sha256(evidence.read_bytes()).hexdigest()
    assert record["gate"] == "PASS" and record["routing_decision"] == "legal_knowledge"
    assert record["review"] == {"patch_count": 0, "review_required": False}
    assert record["publication_result"] == "blocked"
    serialized = json.dumps(record)
    assert "Segredo literal XYZ" not in serialized and "patch_body" not in serialized
    assert "token" not in serialized.lower() and "secret" not in serialized.lower()


@pytest.mark.parametrize("payload", [
    {"type": "Other"}, {"type": "Legislacao", "unknown": True}, [],
    {"type": "Legislacao", "evidence_resource": 4},
])
def test_build_invalid_context_is_configuration_error(tmp_path: Path, payload: object) -> None:
    markdown, report, evidence = _write_artifacts(tmp_path)
    context = tmp_path / "context.json"
    context.write_text(json.dumps(payload))
    assert main(["producer", "build", str(markdown), str(report), "--context", str(context),
                 "--evidence-resource", str(evidence), "--bundle-root", str(tmp_path / "bundle")]) == 3


def test_context_disagreement_invalid_type_and_missing_evidence_exit_three(tmp_path: Path) -> None:
    markdown, report, _ = _write_artifacts(tmp_path)
    context = tmp_path / "context.json"
    context.write_text(json.dumps({"type": "Jurisprudencia"}))
    base = ["producer", "build", str(markdown), str(report), "--bundle-root", str(tmp_path / "b")]
    assert main(base + ["--type", "Legislacao", "--context", str(context)]) == 3
    assert main(base + ["--type", "Invalid"]) == 3
    assert main(base + ["--type", "Legislacao"]) == 3


def test_input_contract_blocked_and_unexpected_exit_codes(tmp_path: Path, monkeypatch) -> None:
    assert main(["producer", "validate", str(tmp_path / "missing.md")]) == 1
    markdown, report, evidence = _write_artifacts(tmp_path, gate="FAIL")
    args = ["producer", "build", str(markdown), str(report), "--type", "Legislacao",
            "--evidence-resource", str(evidence), "--bundle-root", str(tmp_path / "b"),
            "--state-dir", str(tmp_path / "state")]
    assert main(args) == 5
    blocked = json.loads((tmp_path / "state" / "producer-execution-1.json").read_text())
    assert blocked["record_type"] == "producer.review_required"
    assert blocked["publication_result"] == "blocked"
    import pipeline_juridico.legal_producer_cli as module
    monkeypatch.setattr(module, "_run_build", lambda args, logger: (_ for _ in ()).throw(RuntimeError("boom")))
    assert main(args) == 2


def test_validate_full_contract_and_never_writes_bundle(tmp_path: Path, capsys) -> None:
    code, bundle, _, _ = _build(tmp_path)
    candidate = tmp_path / "candidate.md"
    candidate.write_text(json.loads(capsys.readouterr().out)["candidate"])
    assert main(["producer", "validate", str(candidate), "--bundle-root", str(bundle), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["valid"] is True
    assert not bundle.exists()
    candidate.write_text("---\ntype: \"Legislacao\"\n---\nbad")
    assert main(["producer", "validate", str(candidate), "--bundle-root", str(bundle)]) == 3


def test_publish_revalidates_guards_writes_atomically_and_records(tmp_path: Path, capsys, monkeypatch) -> None:
    code, bundle, state, _ = _build(tmp_path)
    candidate = tmp_path / "candidate.md"
    candidate.write_text(json.loads(capsys.readouterr().out)["candidate"])
    import pipeline_juridico.legal_producer_cli as module
    calls: list[object] = []
    original = module.guard_legal_bundle_write
    def guard(**kwargs):
        calls.append(kwargs["acting_domain"])
        return original(**kwargs)
    monkeypatch.setattr(module, "guard_legal_bundle_write", guard)

    assert main(["producer", "publish", str(candidate), "--bundle-root", str(bundle),
                 "--state-dir", str(state), "--json"]) == 0
    outcome = json.loads(capsys.readouterr().out)
    target = Path(outcome["concept_path"])
    assert target.read_text() == candidate.read_text()
    assert calls and calls[0].value == "legal_knowledge"
    digest = hashlib.sha256((tmp_path / "Lei 10.pdf").read_bytes()).hexdigest()
    record = json.loads((state / f"{digest}.json").read_text())
    assert record["record_type"] == "producer.publish"
    assert record["resolution_outcome"] == "new_concept"
    assert record["publication_result"] == "published"


def test_publish_human_review_blocks_without_record_or_write(tmp_path: Path, capsys) -> None:
    _, bundle, state, _ = _build(tmp_path)
    candidate = tmp_path / "candidate.md"
    candidate.write_text(json.loads(capsys.readouterr().out)["candidate"])
    first = bundle / "legislacao" / "lei_10.md"
    first.parent.mkdir(parents=True)
    first.write_text(candidate.read_text().replace("Segredo literal XYZ", "material antigo"))
    (state / "producer-execution-1.json").unlink()
    assert main(["producer", "publish", str(candidate), "--bundle-root", str(bundle),
                 "--state-dir", str(state)]) == 5
    assert "material antigo" in first.read_text()
    assert not (state / "producer-execution-1.json").exists()


def test_state_dir_inside_canonical_bundle_is_rejected(tmp_path: Path) -> None:
    markdown, report, evidence = _write_artifacts(tmp_path)
    canonical = Path(__file__).resolve().parents[1] / "bundle" / "state"
    assert main(["producer", "build", str(markdown), str(report), "--type", "Legislacao",
                 "--evidence-resource", str(evidence), "--state-dir", str(canonical)]) == 3


def test_environment_state_dir_and_route_non_regression(tmp_path: Path, monkeypatch) -> None:
    markdown, report, evidence = _write_artifacts(tmp_path)
    state = tmp_path / "env-state"
    monkeypatch.setenv("PRODUCER_STATE_DIR", str(state))
    assert main(["producer", "build", str(markdown), str(report), "--type", "Legislacao",
                 "--evidence-resource", str(evidence), "--bundle-root", str(tmp_path / "b")]) == 0
    assert (state / "producer-execution-1.json").exists()
    route_state = tmp_path / "route-state"
    assert main(["route", str(markdown), str(report), "--domain", "legal_knowledge",
                 "--state-dir", str(route_state)]) == 0


def test_cli_source_has_no_conversion_ocr_or_unguarded_write_imports() -> None:
    import ast
    source = Path("src/pipeline_juridico/legal_producer_cli.py").read_text()
    imports = [node.module or "" for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.ImportFrom)]
    for prohibited in ("converter", "engines", "inspector", "ocr", "evidence"):
        assert all(prohibited not in module for module in imports)
    assert "guard_legal_bundle_write" in source
