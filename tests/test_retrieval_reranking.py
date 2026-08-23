from __future__ import annotations

import ast
import json
from pathlib import Path

from pipeline_juridico.config import RetrievalConfig
from pipeline_juridico.retrieval.index import SqliteFts5Index, enumerate_concepts
from pipeline_juridico.retrieval.reranking import (
    FakePriorityAdapter,
    RERANK_STATES,
    RerankingProfile,
    rerank,
    should_rerank,
)
from pipeline_juridico.retrieval.search import search, search_diagnose


def _bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    for name, status in (("a", "draft"), ("b", "verified")):
        path = root / "legislacao" / f"{name}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "---\n"
            f'type: "legislacao"\nstatus: "{status}"\n'
            f'verified: {str(status == "verified").lower()}\n'
            'repo_jur_verification_history: ["audit-only"]\n'
            "---\ntermo comum\n",
            encoding="utf-8",
        )
    return root


def _indexed(tmp_path: Path) -> tuple[Path, RetrievalConfig]:
    bundle = _bundle(tmp_path)
    config = RetrievalConfig(derived_root=tmp_path / "state")
    SqliteFts5Index(bundle, config).rebuild(enumerate_concepts(bundle), config)
    return bundle, config


def test_disabled_default_and_public_seam_materialize_without_reranking(tmp_path: Path) -> None:
    bundle, config = _indexed(tmp_path)
    candidates = ["legislacao/a", "legislacao/b"]
    profile = RerankingProfile()
    assert not should_rerank("termo", candidates, profile)
    outcome = rerank("termo", candidates, profile)
    assert outcome.state == "disabled" and list(outcome.candidates) == candidates
    result = search(bundle, config.derived_root, "termo", config=config)
    assert result.rerank_state == "disabled"
    assert [item["concept_id"] for item in result.results] == candidates


def test_fail_open_applied_bypassed_and_states_are_distinct(tmp_path: Path) -> None:
    candidates = ["legislacao/a", "legislacao/b"]
    applied = rerank(
        "termo",
        candidates,
        RerankingProfile(enabled=True, adapter=FakePriorityAdapter(("legislacao/b", "legislacao/a"))),
    )
    assert applied.state == "applied"
    assert list(applied.candidates) == ["legislacao/b", "legislacao/a"]

    class Broken:
        def reorder(self, query: str, values: tuple[str, ...], timeout_seconds: float) -> tuple[str, ...]:
            raise TimeoutError("unavailable")

    failed = rerank("termo", candidates, RerankingProfile(enabled=True, adapter=Broken()))
    bypassed = rerank("termo", candidates, RerankingProfile(enabled=True, trigger_policy="never"))
    disabled = rerank("termo", candidates, RerankingProfile())
    assert failed.state == "failed_fallback" and list(failed.candidates) == candidates
    assert bypassed.state == "bypassed"
    assert {disabled.state, bypassed.state, applied.state, failed.state} == set(RERANK_STATES)

    bundle, config = _indexed(tmp_path)
    diagnosed = search_diagnose(
        bundle,
        config.derived_root,
        "termo",
        config=config,
        reranking_profile=RerankingProfile(enabled=True, adapter=Broken()),
    )
    assert diagnosed.reranking == "failed_fallback"
    assert len(diagnosed.outcome.results) == 2


def test_reranking_never_removes_or_mutates_canonical_or_index_content(tmp_path: Path) -> None:
    bundle, config = _indexed(tmp_path)
    before_bundle = {p: p.read_bytes() for p in bundle.rglob("*") if p.is_file()}
    database = config.derived_root / "index" / "lexical.sqlite3"
    before_index = database.read_bytes()
    profile = RerankingProfile(enabled=True, adapter=FakePriorityAdapter(("legislacao/b",)))
    outcome = search(bundle, config.derived_root, "termo", config=config, reranking_profile=profile)
    assert {item["concept_id"] for item in outcome.results} == {"legislacao/a", "legislacao/b"}
    assert database.read_bytes() == before_index
    assert {p: p.read_bytes() for p in bundle.rglob("*") if p.is_file()} == before_bundle


def test_no_provider_or_trust_ranking_references_in_execution_source() -> None:
    root = Path(__file__).parents[1] / "src/pipeline_juridico/retrieval"
    forbidden_calls = {"provider", "model", "api", "gpu", "trust_tier", "verified", "verification_history", "temporal_decay"}
    for name in ("reranking.py", "search.py"):
        tree = ast.parse((root / name).read_text(encoding="utf-8"))
        called = {
            node.func.id.casefold()
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert not (called & forbidden_calls)
