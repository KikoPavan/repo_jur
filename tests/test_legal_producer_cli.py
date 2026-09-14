from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pipeline_juridico.domain_router_cli import main


MARKDOWN = "[[Pág. 1]]\n<!-- método: texto_nativo -->\nPresidência da República\nLEI Nº 10.406, DE 10 DE JANEIRO DE 2002\nInstitui o Código Civil.\nSegredo literal XYZ\n"


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


def _write_multi_artifacts(tmp_path: Path, markdown_text: str) -> tuple[Path, Path, Path]:
    markdown, report, evidence = _write_artifacts(tmp_path)
    markdown.write_text(markdown_text, encoding="utf-8")
    return markdown, report, evidence


def _precedent_unit(
    number: int, page: int, *, tribunal: bool = True, page_marker: bool = True
) -> str:
    court = f"Registro relativo ao Tema {number}/STJ.\n" if tribunal else ""
    marker = f"[[Pág. {page}]]\n" if page_marker else ""
    return marker + (
        f"Tema Repetitivo {number}  Situação Afetado  Órgão Primeira Seção\n"
        f"{court}conteúdo {number}\n"
    )


def test_analyze_single_is_read_only_and_requires_type(tmp_path: Path, capsys) -> None:
    markdown, report, _ = _write_artifacts(tmp_path)
    bundle, state = tmp_path / "bundle", tmp_path / "state"
    assert main(["producer", "analyze", str(markdown), str(report), "--type", "Legislacao",
                 "--bundle-root", str(bundle), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "single" and payload["segment_count"] == 1
    assert not bundle.exists() and not state.exists()
    assert main(["producer", "analyze", str(markdown), str(report)]) == 3


def test_analyze_segments_reports_identity_and_ambiguous_has_no_list(tmp_path: Path, capsys) -> None:
    body = _precedent_unit(692, 1) + _precedent_unit(
        1016, 1, tribunal=False, page_marker=False
    )
    markdown, report, _ = _write_multi_artifacts(tmp_path, body)
    assert main(["producer", "analyze", str(markdown), str(report), "--type",
                 "PrecedenteVinculante", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["outcome"] == "segments" and payload["segment_count"] == 2
    assert payload["segments"][0]["identity_status"] == "resolved"
    assert payload["segments"][0]["identity_fields"]["repo_jur_precedente_numero"] == "692"
    assert payload["segments"][1]["identity_status"] == "requires_operator_metadata"
    assert "identity_reason" in payload["segments"][1]
    for item in payload["segments"]:
        assert {"segment_id", "source_unit_label", "page_start", "page_end", "boundary_rule_id"} <= item.keys()

    markdown.write_text(
        "Edição n. 171 Brasília, 1 de junho de 2021\n[[Pág. 1]]\nx\n"
        + _precedent_unit(692, 2), encoding="utf-8",
    )
    assert main(["producer", "analyze", str(markdown), str(report), "--type", "TemaJuridico", "--json"]) == 0
    ambiguous = json.loads(capsys.readouterr().out)
    assert ambiguous["outcome"] == "ambiguous"
    assert "ambiguity_reason" in ambiguous and "segments" not in ambiguous


def test_segmented_build_selection_all_and_fail_closed(tmp_path: Path, capsys) -> None:
    body = _precedent_unit(692, 1) + _precedent_unit(
        1016, 1, tribunal=False, page_marker=False
    )
    markdown, report, evidence = _write_multi_artifacts(tmp_path, body)
    base = ["producer", "build", str(markdown), str(report), "--type", "PrecedenteVinculante",
            "--evidence-resource", str(evidence), "--bundle-root", str(tmp_path / "bundle"),
            "--state-dir", str(tmp_path / "state"), "--json"]
    assert main(base) == 5
    assert json.loads(capsys.readouterr().out) == {"blocked": True, "reason": "segmentation_multi_concept"}
    assert main(base + ["--segment", "segment-0001"]) == 0
    selected = json.loads(capsys.readouterr().out)
    assert "conteúdo 692" in selected["candidate"] and "conteúdo 1016" not in selected["candidate"]
    assert main(base + ["--segment", "segment-0002"]) == 5
    blocked = json.loads(capsys.readouterr().out)
    assert blocked == {"blocked": True, "reason": "identity_unresolved"}
    assert main(base + ["--all-segments"]) == 0
    all_payload = json.loads(capsys.readouterr().out)
    assert len(all_payload["candidates"]) == 1
    assert all_payload["blocked_segments"] == [{"segment_id": "segment-0002", "reason": "identity_unresolved"}]
    assert not (tmp_path / "bundle").exists()


def test_segment_flags_rejected_for_single_and_ambiguous_blocks(tmp_path: Path) -> None:
    markdown, report, evidence = _write_artifacts(tmp_path)
    base = ["producer", "build", str(markdown), str(report), "--type", "Legislacao",
            "--evidence-resource", str(evidence), "--bundle-root", str(tmp_path / "bundle")]
    assert main(base + ["--segment", "segment-0001"]) == 3
    assert main(base + ["--all-segments"]) == 3
    markdown.write_text(
        "Edição n. 171 Brasília, 1 de junho de 2021\n[[Pág. 1]]\nx\n"
        + _precedent_unit(692, 2), encoding="utf-8",
    )
    assert main(base + ["--all-segments"]) == 5


def test_single_build_keeps_exact_legacy_json_keys(tmp_path: Path, capsys) -> None:
    code, _, _, _ = _build(tmp_path)
    assert code == 0
    assert set(json.loads(capsys.readouterr().out)) == {"candidate", "concept_path", "record_path"}


def test_candidate_gate_accepts_multiple_segment_records_for_same_hash(tmp_path: Path) -> None:
    from pipeline_juridico.legal_producer_cli import _candidate_gate

    state = tmp_path / "state"
    state.mkdir()
    provenance = "a" * 64
    for index, gate in enumerate(("FAIL", "PASS_WITH_WARNINGS"), 1):
        (state / f"segment-{index}.json").write_text(json.dumps({
            "record_type": "producer.build",
            "provenance_sha256": provenance,
            "gate": gate,
        }))
    assert _candidate_gate(state, provenance) == "PASS_WITH_WARNINGS"


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
    assert outcome["candidate"].startswith("---\ntype: Legislacao")
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
