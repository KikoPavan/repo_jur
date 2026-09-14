from pathlib import Path

import pytest

from pipeline_juridico.config import IngestConfig


def test_ingest_config_defaults() -> None:
    config = IngestConfig()
    root = Path.cwd()
    assert config.input_dir == root / "input/leis_jurisprudencia"
    assert config.candidates_dir == root / "var/producer/candidates"
    assert config.reports_dir == root / "var/ingest/reports"


@pytest.mark.parametrize("field", ["candidates_dir", "reports_dir"])
def test_ingest_outputs_cannot_target_canonical_bundle(field: str) -> None:
    with pytest.raises(ValueError):
        IngestConfig(**{field: Path("bundle/forbidden")})
