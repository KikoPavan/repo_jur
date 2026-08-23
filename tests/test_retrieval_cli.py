from __future__ import annotations

import json
from pathlib import Path

from pipeline_juridico.domain_router_cli import _build_parser, main


def _bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    path = root / "legislacao" / "codigo.md"
    path.parent.mkdir(parents=True)
    path.write_text(
        '---\ntype: "legislacao"\nstatus: "vigente"\ntags: ["civil"]\n'
        'repo_jur_lei_numero: "10.406"\n'
        'sources: [{"id":"pdf-1","type":"pdf","path":"codigo.pdf","sha256":"' + "a" * 64 + '"}]\n'
        "---\nCódigo Civil termo pesquisável\n",
        encoding="utf-8",
    )
    return root


def _snapshot(root: Path) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in root.rglob("*") if path.is_file()}


def test_sync_rebuild_search_are_zero_write_and_return_provenance(tmp_path: Path, capsys) -> None:
    bundle = _bundle(tmp_path)
    state = tmp_path / "state"
    before = _snapshot(bundle)
    for operation in ("sync", "rebuild"):
        assert main(["retrieval", operation, "--bundle-root", str(bundle), "--state-dir", str(state), "--json"]) == 0
    assert _snapshot(bundle) == before
    assert main(["search", "Código", "--bundle-root", str(bundle), "--state-dir", str(state), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out.splitlines()[-1])
    result = payload["results"][0]
    assert result["concept_id"] == "legislacao/codigo"
    assert result["text_content"] == "Código Civil termo pesquisável\n"
    assert result["repo_jur_pdf_hash"] == "a" * 64
    assert _snapshot(bundle) == before


def test_cli_config_errors_missing_bundle_filters_limits_and_derived_inside_bundle(tmp_path: Path, caplog) -> None:
    bundle = _bundle(tmp_path)
    state = tmp_path / "state"
    assert main(["retrieval", "sync", "--bundle-root", str(tmp_path / "missing"), "--state-dir", str(state)]) == 1
    assert main(["search", "Código", "--bundle-root", str(bundle), "--state-dir", str(state), "--filter", "unknown=x"]) == 3
    assert main(["search", "Código", "--bundle-root", str(bundle), "--state-dir", str(state), "--filter", "repo_jur_lei_numero=10.406"]) == 3
    assert main(["search", "Código", "--bundle-root", str(bundle), "--state-dir", str(state), "--limit", "51"]) == 3
    assert main(["retrieval", "sync", "--bundle-root", str(bundle), "--state-dir", str(bundle / "derived")]) == 3
    assert "unknown retrieval filter" in caplog.text


def test_cli_accepts_approved_short_filter_for_search_and_diagnose(tmp_path: Path) -> None:
    bundle = _bundle(tmp_path)
    state = tmp_path / "state"

    for command in ("search", "search-diagnose"):
        assert main([command, "Código", "--bundle-root", str(bundle), "--state-dir", str(state), "--filter", "lei_numero=10.406"]) == 0


def test_search_diagnose_reports_all_stage_states(tmp_path: Path, capsys) -> None:
    bundle = _bundle(tmp_path)
    state = tmp_path / "state"
    assert main(["search-diagnose", "Código", "--bundle-root", str(bundle), "--state-dir", str(state), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) >= {"candidate_discovery", "filter_application", "materialization", "fallback", "reranking", "results"}
    assert payload["fallback"]["used"] is True
    record = json.loads((state / "observability" / "last-query.json").read_text(encoding="utf-8"))
    assert "Código Civil termo pesquisável" not in json.dumps(record, ensure_ascii=False)


def test_parser_help_lists_additive_surface_and_no_pagination(capsys) -> None:
    parser = _build_parser()
    help_text = parser.format_help()
    for command in ("route", "producer", "process", "retrieval", "search", "search-diagnose"):
        assert command in help_text
    search_parser = next(action for action in parser._actions if action.dest == "command").choices["search"]
    assert not ({"--cursor", "--offset", "--page-token", "--snapshot"} & {flag for action in search_parser._actions for flag in action.option_strings})
