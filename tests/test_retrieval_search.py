from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from pipeline_juridico.config import PUBLIC_TO_CANONICAL_FIELD, RetrievalConfig
from pipeline_juridico.retrieval.index import SqliteFts5Index, enumerate_concepts
from pipeline_juridico.retrieval.search import FilterConfigurationError, search, search_diagnose, validate_filters


def _doc(body: str, **metadata: object) -> str:
    values = {"type": "legislacao", "status": "vigente", "tags": ["civil"]}; values.update(metadata)
    return "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in values.items()) + "\n---\n" + body


def _bundle(tmp_path: Path) -> Path:
    root = tmp_path / "bundle"
    docs = {
        "legislacao/a.md": _doc("Lei 10.406 expressão exata [[Pág. 2]] texto [[Pág. 3]] fim", repo_jur_lei_numero="10.406", sources=[{"id":"one","type":"pdf","path":"a.pdf","sha256":"a"*64}]),
        "jurisprudencia/b.md": _doc("REsp 1.704.551 processo 0001234-56.2024.8.26.0100 expressão exata", type="jurisprudencia", status="rascunho", tags=["civil","stj"], repo_jur_tribunal="STJ", sources=[{"id":"s1","type":"pdf","path":"1.pdf","sha256":"b"*64},{"id":"s2","type":"pdf","path":"2.pdf","sha256":"c"*64}]),
    }
    for name, content in docs.items():
        path = root / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8")
    return root


def _indexed(tmp_path: Path) -> tuple[Path, RetrievalConfig]:
    bundle = _bundle(tmp_path); config = RetrievalConfig(derived_root=tmp_path / "state")
    SqliteFts5Index(bundle, config).rebuild(enumerate_concepts(bundle), config)
    return bundle, config


def test_candidate_discovery_exact_identifiers_quotes_and_limit(tmp_path: Path) -> None:
    bundle, config = _indexed(tmp_path)
    for query in ("10.406", "0001234-56.2024.8.26.0100", '"expressão exata"', "1.704.551"):
        assert search(bundle, config.derived_root, query, config=config).results
    assert len(search(bundle, config.derived_root, "expressão", limit=1, config=config).results) == 1


def test_filters_short_names_tags_and_no_implicit_status_policy(tmp_path: Path) -> None:
    bundle, config = _indexed(tmp_path)
    assert validate_filters({"lei_numero":"10.406"}, config) == {"repo_jur_lei_numero":"10.406"}
    assert {r["status"] for r in search(bundle, config.derived_root, "expressão", config=config).results} == {"vigente", "rascunho"}
    assert [r["status"] for r in search(bundle, config.derived_root, "expressão", {"status":"rascunho"}, config=config).results] == ["rascunho"]
    for filters in ({"type":"jurisprudencia"},{"tags":["civil","stj"]},{"tribunal":"STJ"},{"lei_numero":"10.406"}):
        assert len(search(bundle, config.derived_root, "expressão", filters, config=config).results) == 1
    with pytest.raises(FilterConfigurationError): validate_filters({"verified": True}, config)


def test_every_approved_public_filter_is_accepted_and_mapped_to_canonical_fields() -> None:
    config = RetrievalConfig()
    normalized = validate_filters(
        {key: f"value-{index}" for index, key in enumerate(config.filter_vocabulary)},
        config,
    )
    expected_keys = {"type", "status", "tags", *PUBLIC_TO_CANONICAL_FIELD.values()}
    assert set(normalized) == expected_keys
    for public_key in ("lei_numero", "tribunal", "data_julgamento", "tema_numero", "processo_numero", "relator"):
        public_value = f"value-{config.filter_vocabulary.index(public_key)}"
        assert normalized[PUBLIC_TO_CANONICAL_FIELD[public_key]] == public_value


@pytest.mark.parametrize(
    "key",
    [*PUBLIC_TO_CANONICAL_FIELD.values(), "repo_jur_campo_nao_aprovado", "verified", "draft", "trust_tier", "made_up_key"],
)
def test_unknown_or_unauthorized_filters_are_configuration_errors(key: str) -> None:
    with pytest.raises(FilterConfigurationError, match="unknown retrieval filter"):
        validate_filters({key: "value"}, RetrievalConfig())


def test_materialization_current_literal_missing_observable_and_provenance(tmp_path: Path) -> None:
    bundle, config = _indexed(tmp_path)
    path = bundle / "legislacao/a.md"; path.write_text(_doc("CURRENT expressão exata [[Pág. 2]] x [[Pág. 3]] y", repo_jur_lei_numero="10.406", sources=[{"id":"one","type":"pdf","path":"a.pdf","sha256":"a"*64}]), encoding="utf-8")
    outcome = search(bundle, config.derived_root, "expressão", config=config)
    single = next(r for r in outcome.results if r["concept_id"] == "legislacao/a")
    assert single["text_content"].startswith("CURRENT") and single["page_refs"] == [2, 3]
    assert single["source_pdf"] == "a.pdf" and "repo_jur_pdf_hash" in single and "repo_jur_pdf_hashes" not in single
    multi = next(r for r in outcome.results if r["concept_id"] == "jurisprudencia/b")
    assert set(multi["repo_jur_pdf_hashes"]) == {"s1","s2"} and "repo_jur_pdf_hash" not in multi and multi["source_refs"]
    (bundle / "jurisprudencia/b.md").unlink()
    diagnosed = search_diagnose(bundle, config.derived_root, "expressão", config=config)
    assert diagnosed.materialization["missing"] >= 1 or diagnosed.fallback["used"]
    assert diagnosed.reranking == "disabled"


def test_limits_and_no_pagination_surface(tmp_path: Path) -> None:
    bundle, config = _indexed(tmp_path)
    assert len(search(bundle, config.derived_root, "expressão", config=config).results) <= 10
    with pytest.raises(FilterConfigurationError): search(bundle, config.derived_root, "expressão", limit=51, config=config)
    parameters = inspect.signature(search).parameters
    assert not ({"cursor", "offset", "page_token", "snapshot"} & set(parameters))
