from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

from pipeline_juridico.config import RetrievalConfig
from pipeline_juridico.retrieval.fallback import filesystem_search
from pipeline_juridico.retrieval.search import search


def _write_concept(bundle: Path) -> None:
    path = bundle / "legislacao" / "codigo.md"
    path.parent.mkdir(parents=True)
    metadata = {"type": "legislacao", "status": "vigente", "sources": [{"id": "pdf-1", "type": "pdf", "path": "fontes/codigo.pdf", "sha256": "a" * 64}]}
    path.write_text("---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in metadata.items()) + "\n---\nLei especial\n", encoding="utf-8")


def _hashes(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def test_filesystem_fallback_is_read_only_canonical_and_observable(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"; _write_concept(bundle)
    config = RetrievalConfig(derived_root=tmp_path / "state")
    before = _hashes(bundle)
    outcome = filesystem_search(bundle, "especial", {}, 10, config=config, reason="index_absent")
    assert outcome.degraded is True and outcome.reason == "index_absent"
    assert outcome.results[0]["concept_id"] == "legislacao/codigo"
    assert outcome.results[0]["source_pdf"] == "fontes/codigo.pdf"
    assert "index_score" not in outcome.results[0]
    assert _hashes(bundle) == before
    assert (config.derived_root / "observability" / "last-search.json").is_file()


def test_search_falls_back_for_absent_incompatible_corrupt_and_initialization_failure(tmp_path: Path, monkeypatch) -> None:
    bundle = tmp_path / "bundle"; _write_concept(bundle)
    for mode in ("absent", "corrupt"):
        config = RetrievalConfig(derived_root=tmp_path / mode)
        if mode == "corrupt":
            db = config.derived_root / "index" / "lexical.sqlite3"; db.parent.mkdir(parents=True); db.write_text("bad", encoding="utf-8")
        assert search(bundle, config.derived_root, "especial", config=config).degraded
    from pipeline_juridico.retrieval import search as module
    monkeypatch.setattr(module.SqliteFts5Index, "state", lambda *args: (_ for _ in ()).throw(RuntimeError("rebuild lock")))
    assert search(bundle, tmp_path / "failed", "especial", config=RetrievalConfig(derived_root=tmp_path / "failed")).degraded
