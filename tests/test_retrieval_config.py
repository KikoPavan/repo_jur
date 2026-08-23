from __future__ import annotations

from pathlib import Path

import pytest

from pipeline_juridico.config import PUBLIC_TO_CANONICAL_FIELD, RetrievalConfig


EXPECTED_PUBLIC_TO_CANONICAL_FIELD = {
    "lei_numero": "repo_jur_lei_numero",
    "lei_ano": "repo_jur_lei_ano",
    "lei_esfera": "repo_jur_lei_esfera",
    "lei_tipo": "repo_jur_lei_tipo",
    "processo_numero": "repo_jur_processo_numero",
    "tribunal": "repo_jur_tribunal",
    "relator": "repo_jur_relator",
    "data_julgamento": "repo_jur_data_julgamento",
    "ramo_direito": "repo_jur_ramo_direito",
    "precedente_numero": "repo_jur_precedente_numero",
    "precedente_status": "repo_jur_precedente_status",
    "tema_numero": "repo_jur_tema_numero",
}
EXPECTED_FILTER_VOCABULARY = (
    "type",
    "status",
    "tags",
    "lei_numero",
    "lei_ano",
    "lei_esfera",
    "lei_tipo",
    "processo_numero",
    "tribunal",
    "relator",
    "data_julgamento",
    "ramo_direito",
    "precedente_numero",
    "precedente_status",
    "tema_numero",
)


def test_retrieval_config_defaults_to_derived_root_and_bounded_limits() -> None:
    config = RetrievalConfig()

    assert config.derived_root == Path("var/retrieval").resolve()
    assert config.search_default_limit == 10
    assert config.search_max_limit == 50
    assert config.filter_schema_version
    assert config.filter_vocabulary == EXPECTED_FILTER_VOCABULARY


def test_retrieval_public_to_canonical_mapping_is_internal_and_exact() -> None:
    config = RetrievalConfig()

    assert PUBLIC_TO_CANONICAL_FIELD == EXPECTED_PUBLIC_TO_CANONICAL_FIELD
    assert config.public_to_canonical_field == EXPECTED_PUBLIC_TO_CANONICAL_FIELD
    assert set(config.filter_vocabulary) == set(EXPECTED_FILTER_VOCABULARY)


def test_retrieval_config_reads_state_dir_from_environment(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    state_dir = tmp_path / "retrieval-state"
    monkeypatch.setenv("RETRIEVAL_STATE_DIR", str(state_dir))

    assert RetrievalConfig.from_env().derived_root == state_dir.resolve()


def test_retrieval_config_rejects_root_inside_canonical_bundle() -> None:
    repository_root = Path(__file__).resolve().parents[1]

    with pytest.raises(ValueError, match="outside bundle"):
        RetrievalConfig(derived_root=repository_root / "bundle" / "retrieval")


@pytest.mark.parametrize(
    ("default_limit", "maximum_limit"),
    [(0, 50), (51, 50), (10, 0)],
)
def test_retrieval_config_validates_search_limits(
    default_limit: int, maximum_limit: int
) -> None:
    with pytest.raises(ValueError, match="search"):
        RetrievalConfig(
            search_default_limit=default_limit,
            search_max_limit=maximum_limit,
        )
