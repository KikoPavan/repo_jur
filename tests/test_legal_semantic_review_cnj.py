from __future__ import annotations

from pathlib import Path

from pipeline_juridico.legal_semantic_review import (
    ExtractedField,
    _deterministic_extract,
)


def _field(markdown: str, name: str) -> ExtractedField | None:
    return next(
        (field for field in _deterministic_extract(markdown) if field.name == name),
        None,
    )


def test_preserves_checksum_valid_canonical_cnj() -> None:
    field = _field("[[Pág. 3]]\n0311049-09.2016.8.24.0018\n", "repo_jur_processo_numero")

    assert field == ExtractedField(
        "repo_jur_processo_numero",
        "0311049-09.2016.8.24.0018",
        ("3",),
    )


def test_normalizes_checksum_valid_standalone_20_digit_cnj() -> None:
    field = _field("[[Pág. 4]]\n03110490920168240018\n", "repo_jur_processo_numero")

    assert field == ExtractedField(
        "repo_jur_processo_numero",
        "0311049-09.2016.8.24.0018",
        ("4",),
    )


def test_prefers_valid_cnj_over_appellate_header() -> None:
    markdown = (
        "[[Pág. 1]]\nAgInt no RECURSO ESPECIAL Nº 1833684 - SC\n"
        "[[Pág. 6]]\nNúmero de Origem: 03110490920168240018\n"
    )

    field = _field(markdown, "repo_jur_processo_numero")

    assert field == ExtractedField(
        "repo_jur_processo_numero",
        "0311049-09.2016.8.24.0018",
        ("6",),
    )


def test_omits_process_number_for_appellate_header_alone() -> None:
    markdown = "[[Pág. 1]]\nAgInt no REsp 1.833.684/SC\n"

    assert _field(markdown, "repo_jur_processo_numero") is None


def test_omits_process_number_for_internal_register_alone() -> None:
    markdown = "[[Pág. 1]]\nNúmero Registro: 2019/0251395-0\n"

    assert _field(markdown, "repo_jur_processo_numero") is None


def test_omits_process_number_for_conflicting_valid_cnjs() -> None:
    markdown = (
        "[[Pág. 2]]\n00134589020148260100\n"
        "[[Pág. 8]]\n22019934120158260000\n"
    )

    assert _field(markdown, "repo_jur_processo_numero") is None


def test_rejects_canonical_cnj_with_invalid_check_digits() -> None:
    markdown = "[[Pág. 1]]\n0311049-10.2016.8.24.0018\n"

    assert _field(markdown, "repo_jur_processo_numero") is None


def test_airesp_unrelated_jurisprudencia_fields_remain_unchanged() -> None:
    markdown = Path("output/AIRESP-1833684-2020-02-12.md").read_text(encoding="utf-8")
    relevant = tuple(
        field
        for field in _deterministic_extract(markdown)
        if field.name
        in {
            "repo_jur_tribunal",
            "repo_jur_relator",
            "repo_jur_data_julgamento",
        }
    )

    assert relevant == (
        ExtractedField("repo_jur_tribunal", "STJ", ("1",)),
        ExtractedField("repo_jur_relator", "REGINA HELENA COSTA", ("1",)),
        ExtractedField("repo_jur_data_julgamento", "2020-02-10", ("1",)),
        ExtractedField("repo_jur_tribunal", "STJ", ("9",)),
    )
