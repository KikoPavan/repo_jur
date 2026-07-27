from pathlib import Path

import fitz
import pytest

from pipeline_juridico import cli, __version__


def _configure_directories(monkeypatch, tmp_path) -> tuple[Path, Path]:
    output_dir = tmp_path / "output"
    logs_dir = tmp_path / "logs"
    monkeypatch.setenv("OUTPUT_DIR", str(output_dir))
    monkeypatch.setenv("LOGS_DIR", str(logs_dir))
    monkeypatch.setenv("TEMP_DIR", str(tmp_path / "temp"))
    return output_dir, logs_dir


def _create_native_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (50, 50),
        "Conteúdo jurídico nativo suficientemente longo para superar o "
        "limite mínimo de caracteres úteis da página.",
    )
    document.save(path)
    document.close()


def _create_scanned_pdf(path: Path) -> None:
    document = fitz.open()
    page = document.new_page()
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pixmap.set_rect(pixmap.irect, (255, 0, 0))
    page.insert_image(page.rect, pixmap=pixmap)
    document.save(path)
    document.close()


def test_version() -> None:
    assert __version__ == "0.1.0"


def test_main_exists_and_callable() -> None:
    assert callable(cli.main)


def test_main_runs_without_error() -> None:
    with pytest.raises(SystemExit):
        cli.main([])


def test_main_returns_1_for_missing_pdf(tmp_path, monkeypatch) -> None:
    _configure_directories(monkeypatch, tmp_path)

    result = cli.main(["/caminho/que/nao/existe.pdf"])

    assert result == 1


def test_main_returns_0_for_successful_native_conversion(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "nativo.pdf"
    _create_native_pdf(source)
    output_dir, logs_dir = _configure_directories(monkeypatch, tmp_path)

    result = cli.main([str(source)])

    assert result == 0
    assert (output_dir / "nativo.md").is_file()
    assert (logs_dir / "nativo.report.json").is_file()


def test_main_returns_4_when_output_exists_without_overwrite(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "nativo.pdf"
    _create_native_pdf(source)
    output_dir, _logs_dir = _configure_directories(monkeypatch, tmp_path)
    output_dir.mkdir()
    (output_dir / "nativo.md").write_text(
        "conteúdo prévio",
        encoding="utf-8",
    )

    result = cli.main([str(source)])

    assert result == 4


def test_main_returns_3_for_strict_validation_failure(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)
    _configure_directories(monkeypatch, tmp_path)

    result = cli.main([str(source), "--no-ocr"])

    assert result == 3


def test_main_returns_2_for_unexpected_conversion_error(
    tmp_path,
    monkeypatch,
) -> None:
    _configure_directories(monkeypatch, tmp_path)

    def raise_unexpected_error(**_kwargs) -> None:
        raise RuntimeError("falha inesperada simulada")

    monkeypatch.setattr(cli, "convert_document", raise_unexpected_error)

    result = cli.main([str(tmp_path / "qualquer.pdf")])

    assert result == 2
