import pytest

from pipeline_juridico import cli, __version__


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_main_exists_and_callable() -> None:
    assert callable(cli.main)


def test_main_runs_without_error() -> None:
    with pytest.raises(SystemExit):
        cli.main([])
