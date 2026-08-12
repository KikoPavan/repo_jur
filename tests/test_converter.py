import fitz
import pytest
from types import SimpleNamespace

import pipeline_juridico.converter as converter_module
from pipeline_juridico.converter import (
    PageBlock,
    _geometric_reading_order_text,
    _page_has_large_text,
    compose_document,
    convert_document,
    format_page_marker,
)
from pipeline_juridico.models import Metodo


VERTICAL_BLOCK_TEXT = "Registro digital genérico para teste."
HORIZONTAL_BODY_TEXT = (
    "Texto horizontal normal do corpo com conteúdo suficiente para que a "
    "página sintética seja classificada como texto nativo."
)


def _insert_rotated_text(
    page: fitz.Page,
    text: str = VERTICAL_BLOCK_TEXT,
    *,
    x: float = 550,
    y: float = 700,
) -> None:
    page.insert_text((x, y), text, fontsize=8, rotate=90)


def _save_native_pdf_with_duplicated_rotated_block(path) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)
        document.save(path)
    finally:
        document.close()


def test_has_duplicated_rotated_block_detects_overlapping_vertical_duplicate(
) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is True
    finally:
        document.close()


def test_geometric_reading_order_text_deduplicates_repeated_vertical_block(
) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        result = _geometric_reading_order_text(page)

        assert result.count(VERTICAL_BLOCK_TEXT) == 1
    finally:
        document.close()


def test_convert_document_avoids_single_character_noise_from_rotated_duplicate(
    tmp_path,
) -> None:
    source = tmp_path / "bloco-vertical-duplicado.pdf"
    _save_native_pdf_with_duplicated_rotated_block(source)

    markdown, _report = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    single_character_lines = [
        line for line in markdown.splitlines() if len(line.strip()) == 1
    ]
    assert len(single_character_lines) < 5


def test_convert_document_bypasses_native_engine_for_rotated_duplicate(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "bloco-vertical-duplicado.pdf"
    _save_native_pdf_with_duplicated_rotated_block(source)

    class FailingNativeEngine:
        def convert(self, _page_path):
            raise AssertionError(
                "MarkItDown não deveria ser chamado nesta página"
            )

    monkeypatch.setattr(
        converter_module,
        "create_native_engine",
        lambda: FailingNativeEngine(),
    )

    markdown, _report = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert VERTICAL_BLOCK_TEXT in markdown


def test_has_duplicated_rotated_block_single_legitimate_vertical_block(
) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_ignores_horizontal_duplicate() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_different_text_same_position() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page, "Primeiro registro vertical genérico.")
        _insert_rotated_text(page, "Segundo registro vertical genérico.")

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_bbox_beyond_tolerance() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page, y=720)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_has_duplicated_rotated_block_bbox_within_tolerance() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page)
        _insert_rotated_text(page, y=701)

        assert converter_module._has_duplicated_rotated_block(page) is True
    finally:
        document.close()


def test_has_duplicated_rotated_block_absent_keeps_current_behavior() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        page.insert_text((72, 100), HORIZONTAL_BODY_TEXT, fontsize=10)

        assert converter_module._has_duplicated_rotated_block(page) is False
    finally:
        document.close()


def test_page_has_large_text_threshold_boundary() -> None:
    below_threshold_document = fitz.open()
    at_threshold_document = fitz.open()
    try:
        page_below_threshold = below_threshold_document.new_page()
        page_below_threshold.insert_text(
            (72, 72),
            "Texto abaixo do limiar",
            fontsize=19.9,
        )
        page_at_threshold = at_threshold_document.new_page()
        page_at_threshold.insert_text(
            (72, 72),
            "Texto no limiar",
            fontsize=20.0,
        )

        assert _page_has_large_text(page_below_threshold) is False
        assert _page_has_large_text(page_at_threshold) is True
    finally:
        below_threshold_document.close()
        at_threshold_document.close()


def test_format_page_marker_texto_nativo() -> None:
    assert (
        format_page_marker(1, Metodo.texto_nativo)
        == "[[Pág. 1]]\n<!-- método: texto_nativo -->"
    )


def test_format_page_marker_different_number_and_method() -> None:
    assert (
        format_page_marker(42, Metodo.ocr_integral)
        == "[[Pág. 42]]\n<!-- método: ocr_integral -->"
    )


@pytest.mark.parametrize("method", list(Metodo))
def test_format_page_marker_preserves_exact_method_value(method: Metodo) -> None:
    assert format_page_marker(1, method) == (
        f"[[Pág. 1]]\n<!-- método: {method.value} -->"
    )


def test_compose_document_single_block() -> None:
    result = compose_document(
        [
            PageBlock(
                number=1,
                method=Metodo.texto_nativo,
                content="Conteúdo da página um.",
            )
        ]
    )

    marker_index = result.index("[[Pág. 1]]")
    method_index = result.index("<!-- método: texto_nativo -->")
    content_index = result.index("Conteúdo da página um.")

    assert marker_index < method_index < content_index


def test_compose_document_orders_by_number_even_if_input_unordered() -> None:
    blocks = [
        PageBlock(3, Metodo.texto_nativo, "Página três."),
        PageBlock(1, Metodo.texto_nativo, "Página um."),
        PageBlock(2, Metodo.texto_nativo, "Página dois."),
    ]

    result = compose_document(blocks)

    assert (
        result.index("[[Pág. 1]]")
        < result.index("[[Pág. 2]]")
        < result.index("[[Pág. 3]]")
    )


def test_compose_document_separates_pages_without_leaking_context() -> None:
    blocks = [
        PageBlock(1, Metodo.texto_nativo, "- item a\n- item b"),
        PageBlock(2, Metodo.texto_nativo, "- item c"),
    ]

    result = compose_document(blocks)

    assert "- item b\n\n[[Pág. 2]]" in result


def test_compose_document_handles_empty_page_content() -> None:
    result = compose_document([PageBlock(1, Metodo.vazia, "")])

    assert "[[Pág. 1]]" in result
    assert "<!-- método: vazia -->" in result


OCR_END_MARKER = "[End OCR]*"
ROTATED_OCR_RESIDUAL_TEXT = "Autenticação genérica de teste 12345"
SUBSTANTIVE_OCR_TEXT = "Conteúdo OCR substantivo real."


def _fragment_text_as_noise(text: str) -> str:
    return "\n\n".join(reversed(list(text)))


def _full_page_pixmap() -> fitz.Pixmap:
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pixmap.set_rect(pixmap.irect, (255, 255, 255))
    return pixmap


def _save_page_with_rotated_text(path, text: str) -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        _insert_rotated_text(page, text)
        document.save(path)
    finally:
        document.close()


def _save_hybrid_pdf(path, page_count: int, vertical_text: str) -> None:
    document = fitz.open()
    try:
        for _ in range(page_count):
            page = document.new_page(width=595, height=842)
            page.insert_image(page.rect, pixmap=_full_page_pixmap())
            _insert_rotated_text(page, vertical_text)
        document.save(path)
    finally:
        document.close()


class _FakeFragmentingOcrEngine:
    def __init__(self, vertical_text: str):
        self._vertical_text = vertical_text
        self._page_number = 0

    def convert(self, _page_path):
        self._page_number += 1
        substantive_text = (
            f"{SUBSTANTIVE_OCR_TEXT} Página sintética {self._page_number}."
        )
        return SimpleNamespace(
            text_content=(
                f"{substantive_text}\n\n"
                "*[Image OCR]\n"
                f"{substantive_text}\n"
                f"{OCR_END_MARKER}\n"
                f"{_fragment_text_as_noise(self._vertical_text)}"
            )
        )


def test_split_ocr_tail_uses_last_marker() -> None:
    raw_content = (
        f"Primeira imagem\n{OCR_END_MARKER}\nresíduo intermediário\n"
        f"Segunda imagem\n{OCR_END_MARKER}\nresíduo final"
    )

    assert converter_module._split_ocr_tail(raw_content) == (
        raw_content.rsplit(OCR_END_MARKER, 1)[0] + OCR_END_MARKER,
        "\nresíduo final",
    )


def test_split_ocr_tail_returns_none_without_marker() -> None:
    assert converter_module._split_ocr_tail("Conteúdo sem marcador") is None


def test_tail_fragments_splits_blank_lines_and_discards_empty_items() -> None:
    tail = "\n A \n\n  \n\nBC\n\n\n D \n"

    assert converter_module._tail_fragments(tail) == ["A", "BC", "D"]


def test_is_degenerate_fragment_tail_accepts_realistic_short_fraction() -> None:
    fragments = ["A"] * 18 + ["BC"] + ["frase normal"]

    assert converter_module._is_degenerate_fragment_tail(fragments) is True


def test_is_degenerate_fragment_tail_rejects_normal_prose() -> None:
    fragments = [
        "Primeira frase completa de teste.",
        "Segunda frase completa de teste.",
        "Terceira frase completa de teste.",
    ]

    assert converter_module._is_degenerate_fragment_tail(fragments) is False


def test_non_horizontal_line_texts_returns_only_rotated_text() -> None:
    document = fitz.open()
    try:
        page = document.new_page(width=595, height=842)
        rotated_text = "Registro vertical sintético"
        _insert_rotated_text(page, rotated_text)
        page.insert_text((72, 100), "Rodapé horizontal sintético", fontsize=10)

        assert converter_module._non_horizontal_line_texts(page) == [
            rotated_text
        ]
    finally:
        document.close()


@pytest.mark.parametrize(
    ("left", "right", "expected"),
    [("abcabc", "abcabc", 1.0), ("abc", "XYZ", 0.0)],
)
def test_char_multiset_overlap(left: str, right: str, expected: float) -> None:
    assert converter_module._char_multiset_overlap(left, right) == expected


def test_geometrically_corroborated_vertical_residual_matches_multiset() -> None:
    vertical_text = "Registro vertical genérico 123"
    fragments = list(reversed(vertical_text.replace(" ", "")))

    assert converter_module._geometrically_corroborated_vertical_residual(
        fragments,
        [vertical_text],
    ) is True


def test_replace_fragmented_vertical_residual_reconstructs_text(tmp_path) -> None:
    page_path = tmp_path / "pagina-vertical.pdf"
    _save_page_with_rotated_text(page_path, ROTATED_OCR_RESIDUAL_TEXT)
    head_before_marker = (
        f"{SUBSTANTIVE_OCR_TEXT}\n\n"
        f"*[Image OCR]\n{SUBSTANTIVE_OCR_TEXT}\n"
    )
    raw_content = (
        f"{head_before_marker}{OCR_END_MARKER}\n"
        f"{_fragment_text_as_noise(ROTATED_OCR_RESIDUAL_TEXT)}"
    )

    result = converter_module._replace_fragmented_vertical_residual(
        raw_content,
        page_path,
    )

    assert result.split(OCR_END_MARKER, 1)[0] == head_before_marker
    assert OCR_END_MARKER in result
    assert ROTATED_OCR_RESIDUAL_TEXT in result
    short_lines = [
        line
        for line in result.split(OCR_END_MARKER)[-1].splitlines()
        if 0 < len(line.strip()) <= 2
    ]
    assert len(short_lines) < 5


def test_replace_keeps_coherent_vertical_residual_unchanged(tmp_path) -> None:
    page_path = tmp_path / "pagina-vertical-legitima.pdf"
    _save_page_with_rotated_text(page_path, ROTATED_OCR_RESIDUAL_TEXT)
    raw_content = (
        f"{SUBSTANTIVE_OCR_TEXT}\n{OCR_END_MARKER}\n"
        f"{ROTATED_OCR_RESIDUAL_TEXT}\n"
    )

    assert converter_module._is_degenerate_fragment_tail(
        [ROTATED_OCR_RESIDUAL_TEXT]
    ) is False
    assert converter_module._replace_fragmented_vertical_residual(
        raw_content,
        page_path,
    ) == raw_content


def test_replace_keeps_horizontal_residual_unchanged(tmp_path) -> None:
    page_path = tmp_path / "pagina-horizontal.pdf"
    document = fitz.open()
    try:
        page = document.new_page()
        page.insert_text((72, 100), "Rodapé horizontal legítimo de teste")
        document.save(page_path)
    finally:
        document.close()
    raw_content = (
        f"{SUBSTANTIVE_OCR_TEXT}\n{OCR_END_MARKER}\n"
        "Rodapé horizontal legítimo de teste\n"
    )

    assert converter_module._replace_fragmented_vertical_residual(
        raw_content,
        page_path,
    ) == raw_content


def test_replace_keeps_degenerate_tail_without_vertical_geometry(tmp_path) -> None:
    page_path = tmp_path / "pagina-sem-geometria-vertical.pdf"
    document = fitz.open()
    try:
        page = document.new_page()
        page.insert_text((72, 100), "Texto horizontal genérico")
        document.save(page_path)
    finally:
        document.close()
    raw_content = (
        f"{SUBSTANTIVE_OCR_TEXT}\n{OCR_END_MARKER}\n"
        f"{_fragment_text_as_noise('fragmento qualquer')}"
    )

    assert converter_module._replace_fragmented_vertical_residual(
        raw_content,
        page_path,
    ) == raw_content


def test_replace_keeps_degenerate_tail_with_mismatched_vertical_text(
    tmp_path,
) -> None:
    page_path = tmp_path / "pagina-geometria-divergente.pdf"
    _save_page_with_rotated_text(page_path, ROTATED_OCR_RESIDUAL_TEXT)
    raw_content = (
        f"{SUBSTANTIVE_OCR_TEXT}\n{OCR_END_MARKER}\n"
        f"{_fragment_text_as_noise('ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ')}"
    )

    assert converter_module._replace_fragmented_vertical_residual(
        raw_content,
        page_path,
    ) == raw_content


def test_replace_keeps_content_without_ocr_marker(tmp_path) -> None:
    page_path = tmp_path / "pagina-sem-marcador.pdf"
    _save_page_with_rotated_text(page_path, ROTATED_OCR_RESIDUAL_TEXT)
    raw_content = f"{SUBSTANTIVE_OCR_TEXT}\nA\n\nB\n\nC"

    assert converter_module._replace_fragmented_vertical_residual(
        raw_content,
        page_path,
    ) == raw_content


def test_convert_document_replaces_fragmented_vertical_residual_on_hybrid_pages(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "quatro-paginas-hibridas.pdf"
    vertical_text = (
        "Registro vertical fictício suficientemente longo para teste híbrido "
        "com autenticação sintética adicional e identificador genérico ABCDEF"
    )
    _save_hybrid_pdf(source, page_count=4, vertical_text=vertical_text)
    monkeypatch.setattr(
        converter_module,
        "create_ocr_engine",
        lambda **_kwargs: _FakeFragmentingOcrEngine(vertical_text),
    )

    markdown, report = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida-hibrida.md",
        temp_root=tmp_path / "temp-hibrido",
        use_ocr=True,
        ocr_api_key="fake",
        ocr_model="fake",
    )

    assert [page.method for page in report.pages] == [Metodo.hibrido] * 4
    assert markdown.count(SUBSTANTIVE_OCR_TEXT) == 8
    assert markdown.count(OCR_END_MARKER) == 4
    assert markdown.count(vertical_text) == 4
    for page_content in markdown.split("[[Pág. ")[1:]:
        tail = page_content.split(OCR_END_MARKER, 1)[-1]
        short_lines = [
            line
            for line in tail.splitlines()
            if 0 < len(line.strip()) <= 2
        ]
        assert len(short_lines) < 5


def test_document_replacement_runs_after_repetitive_margin_removal() -> None:
    vertical_text = (
        "Registro vertical fictício suficientemente longo para regressão com "
        "autenticação sintética adicional e identificador genérico ABCDEF"
    )
    fragmented_tail = _fragment_text_as_noise(vertical_text)
    blocks = [
        PageBlock(
            number=page_number,
            method=Metodo.hibrido,
            content=(
                f"Conteúdo substantivo distinto da página {page_number}.\n"
                f"{OCR_END_MARKER}\n{fragmented_tail}"
            ),
        )
        for page_number in range(1, 5)
    ]

    cleaned = converter_module.remove_repetitive_margins(
        compose_document(blocks)
    )
    result = converter_module._replace_fragmented_vertical_residuals_in_document(
        cleaned,
        blocks,
        {page_number: [vertical_text] for page_number in range(1, 5)},
    )

    assert result.count(OCR_END_MARKER) == 4
    assert result.count(vertical_text) == 4


@pytest.mark.parametrize(
    "method",
    [Metodo.texto_nativo, Metodo.vazia, Metodo.erro],
)
def test_document_replacement_ignores_ineligible_page_methods(method) -> None:
    vertical_text = "Registro vertical fictício para método não elegível"
    raw_content = (
        f"Conteúdo sintético.\n{OCR_END_MARKER}\n"
        f"{_fragment_text_as_noise(vertical_text)}"
    )
    block = PageBlock(number=1, method=method, content=raw_content)
    markdown = compose_document([block])

    result = converter_module._replace_fragmented_vertical_residuals_in_document(
        markdown,
        [block],
        {1: [vertical_text]},
    )

    assert result == markdown


def test_convert_document_native_path_does_not_replace_ocr_residual(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "pagina-nativa.pdf"
    _save_native_pdf_with_duplicated_rotated_block(source)

    def unexpected_replacement(_raw_content, _page_path):
        raise AssertionError(
            "Substituição de resíduo OCR não deve atuar em texto nativo"
        )

    monkeypatch.setattr(
        converter_module,
        "_replace_fragmented_vertical_residual",
        unexpected_replacement,
    )

    markdown, report = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida-nativa.md",
        temp_root=tmp_path / "temp-nativo",
        use_ocr=False,
    )

    assert report.pages[0].method is Metodo.texto_nativo
    assert VERTICAL_BLOCK_TEXT in markdown
