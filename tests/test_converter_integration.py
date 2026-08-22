from pathlib import Path
import re
from types import SimpleNamespace

import fitz
import pytest

from pipeline_juridico.cleaner import ILLEGIBLE_TEXT_MARKER
from pipeline_juridico.converter import convert_document
from pipeline_juridico.engines import OcrConfigurationError
from pipeline_juridico.models import Metodo, Relatorio, StatusExecucao
from pipeline_juridico.validator import MarkdownValidationError


def _create_native_pdf(path, page_count: int = 2) -> None:
    document = fitz.open()
    for number in range(1, page_count + 1):
        page = document.new_page()
        page.insert_text(
            (50, 50),
            "Conteúdo jurídico nativo suficientemente longo para superar o "
            f"limite mínimo de caracteres úteis da página {number}.",
        )
    document.save(path)
    document.close()


def _isolate_first_page(source, target, page_index: int = 0) -> None:
    with fitz.open(source) as source_document:
        isolated_document = fitz.open()
        isolated_document.insert_pdf(
            source_document,
            from_page=page_index,
            to_page=page_index,
        )
        isolated_document.save(target)
        isolated_document.close()


def _isolate_page_range(
    source,
    target,
    start_index: int,
    end_index: int,
) -> None:
    with fitz.open(source) as source_document:
        isolated_document = fitz.open()
        isolated_document.insert_pdf(
            source_document,
            from_page=start_index,
            to_page=end_index,
        )
        isolated_document.save(target)
        isolated_document.close()


def _normalize_whitespace(markdown: str) -> str:
    normalized_lines = "\n".join(
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    )
    return " ".join(normalized_lines.split())


def _create_scanned_pdf(path) -> None:
    document = fitz.open()
    page = document.new_page()
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 100, 100))
    pixmap.set_rect(pixmap.irect, (255, 0, 0))
    page.insert_image(page.rect, pixmap=pixmap)
    document.save(path)
    document.close()


def test_convert_document_all_native_pages(tmp_path) -> None:
    source = tmp_path / "nativo.pdf"
    _create_native_pdf(source)

    result = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        allow_partial=False,
        use_ocr=True,
    )

    assert isinstance(result, tuple)
    markdown, relatorio = result
    assert isinstance(markdown, str)
    assert isinstance(relatorio, Relatorio)
    assert "[[Pág. 1]]" in markdown
    assert "[[Pág. 2]]" in markdown
    assert all(not page.errors for page in relatorio.pages)
    assert len(relatorio.pages) == 2
    assert all(
        page.method == Metodo.texto_nativo for page in relatorio.pages
    )


def test_convert_document_preserves_native_label_value_reading_order(
    tmp_path,
) -> None:
    source = tmp_path / "rotulos-valores.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    )
    _isolate_first_page(corpus_pdf, source)

    markdown, relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert relatorio.pages[0].method == Metodo.texto_nativo
    # A proteção do padrão ":" agora é por bloco geométrico, não mais um
    # bypass de página inteira; rótulo e valor continuam nunca fundidos em
    # uma única linha, mas passam a ficar em parágrafos separados.
    assert "RELATOR\n\n: MINISTRO GURGEL DE FARIA\n\nAGRAVANTE" in markdown
    assert "AGRAVANTE\n\n: NORTE ENERGIA S.A.\n\nADVOGADOS" in markdown


def test_convert_aintaresp_preserves_repeated_legal_header(tmp_path) -> None:
    source = tmp_path / "aintaresp-paginas-1-a-3.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    )
    _isolate_page_range(corpus_pdf, source, start_index=0, end_index=2)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert "Superior Tribunal de Justiça" in markdown
    page_markers = ["[[Pág. 1]]", "[[Pág. 2]]", "[[Pág. 3]]"]
    assert all(marker in markdown for marker in page_markers)
    assert [markdown.index(marker) for marker in page_markers] == sorted(
        markdown.index(marker) for marker in page_markers
    )


def test_convert_document_replaces_fabricated_native_tables(
    tmp_path,
) -> None:
    source = tmp_path / "tabelas-fabricadas.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "REsp_1704551-SP.pdf"
    )
    _isolate_first_page(corpus_pdf, source)

    markdown, relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert not any(line.startswith("|") for line in markdown.splitlines())
    # Ver comentário equivalente em test_convert_document_preserves_native_label_value_reading_order.
    assert "RELATORA\n\n: MINISTRA NANCY ANDRIGHI" in markdown
    assert relatorio.pages[0].method == Metodo.texto_nativo


def test_convert_resp_removes_repetitive_page_counters(tmp_path) -> None:
    source = tmp_path / "resp-paginas-1-a-4.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "REsp_1704551-SP.pdf"
    )
    _isolate_page_range(corpus_pdf, source, start_index=0, end_index=3)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert re.search(r"Página\s*\d+\s*de\s*\d+", markdown) is None
    page_markers = [
        "[[Pág. 1]]",
        "[[Pág. 2]]",
        "[[Pág. 3]]",
        "[[Pág. 4]]",
    ]
    assert all(marker in markdown for marker in page_markers)
    assert [markdown.index(marker) for marker in page_markers] == sorted(
        markdown.index(marker) for marker in page_markers
    )
    assert "RECURSO ESPECIAL" in markdown


def _assert_convert_resp_unifies_recurso_especial_heading(tmp_path, page_index):
    source = tmp_path / f"resp-pagina-{page_index + 1}.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "REsp_1704551-SP.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=page_index)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]
    heading = (
        "RECURSO ESPECIAL. PROCESSUAL CIVIL. ARBITRAGEM. NULIDADE DE "
        "COMPROMISSO ARBITRAL E DE SENTENÇA ARBITRAL. OMISSÃO, CONTRADIÇÃO OU "
        "ERRO MATERIAL. AUSÊNCIA. VALOR DA CAUSA. IMPUGNAÇÃO. MENSURAÇÃO DO "
        "CONTEÚDO ECONÔMICO. CONDENAÇÃO EM SENTENÇA ARBITRAL. POSSIBILIDADE."
    )

    assert heading in normalized_lines
    assert "RECURSO" not in normalized_lines


def test_convert_resp_page_1_unifies_recurso_especial_heading(tmp_path) -> None:
    _assert_convert_resp_unifies_recurso_especial_heading(tmp_path, page_index=0)


def test_convert_resp_page_6_unifies_recurso_especial_heading(tmp_path) -> None:
    _assert_convert_resp_unifies_recurso_especial_heading(tmp_path, page_index=5)


def test_convert_aintaresp_page_11_agravante_agravado_assunto_unaffected(
    tmp_path,
) -> None:
    source = tmp_path / "aintaresp-pagina-11-campos.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=10)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]

    for label in ("AGRAVANTE", "AGRAVADO", "ASSUNTO"):
        assert label in normalized_lines
    assert "NORTE ENERGIA" not in next(
        line for line in normalized_lines if line == "AGRAVANTE"
    )


def _assert_convert_resp_recorrente_unaffected(tmp_path, page_index):
    source = tmp_path / f"resp-pagina-{page_index + 1}-recorrente.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "REsp_1704551-SP.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=page_index)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]

    assert "RECORRENTE" in normalized_lines
    assert ": DAIBY S/A" in normalized_lines
    assert "RECORRENTE : DAIBY S/A" not in normalized_lines


def test_convert_resp_page_3_recorrente_unaffected(tmp_path) -> None:
    _assert_convert_resp_recorrente_unaffected(tmp_path, page_index=2)


def test_convert_resp_page_14_recorrente_unaffected(tmp_path) -> None:
    _assert_convert_resp_recorrente_unaffected(tmp_path, page_index=13)


def test_convert_aintaresp_does_not_add_final_index(tmp_path) -> None:
    source = tmp_path / "aintaresp-sem-indice-final.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    )
    _isolate_page_range(corpus_pdf, source, start_index=0, end_index=2)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert "# ÍNDICE" not in markdown


def test_convert_resp_does_not_add_final_index(tmp_path) -> None:
    source = tmp_path / "resp-sem-indice-final.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "REsp_1704551-SP.pdf"
    )
    _isolate_page_range(corpus_pdf, source, start_index=0, end_index=3)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert "# ÍNDICE" not in markdown


def test_convert_inf0024e_first_page_uses_clean_native_output(tmp_path) -> None:
    source = tmp_path / "inf0024e-pagina-1.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_first_page(corpus_pdf, source)

    markdown, relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert relatorio.pages[0].method == Metodo.texto_nativo
    normalized_lines = "\n".join(
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    )
    normalized_text = " ".join(normalized_lines.split())
    assert "Ausência de inércia do Ministério Público" in normalized_text
    assert "PROCESSO\nProcesso em segredo" in normalized_lines
    assert "RAMO DO DIREITO\nDIREITO PENAL" in normalized_lines
    assert "TEMA\nAção penal privada" in normalized_lines
    assert not any("[Image OCR]" in line for line in markdown.splitlines())


def test_convert_inf0024e_page_1_separates_editorial_cover_elements(tmp_path) -> None:
    source = tmp_path / "inf0024e-capa.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=0)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]
    elements = [
        "Informativo de Jurisprudência",
        "Informativo de Jurisprudência n. 24 - Edição Extraordinária",
        "Este periódico destaca teses jurisprudenciais",
        "CORTE ESPECIAL",
    ]

    assert all(element in _normalize_whitespace(markdown) for element in elements)
    title_line = next(
        line
        for line in normalized_lines
        if elements[0] in line and elements[1] not in line
    )
    edition_line = next(line for line in normalized_lines if elements[1] in line)
    notice_line = next(line for line in normalized_lines if elements[2] in line)
    court_line = next(line for line in normalized_lines if elements[3] in line)

    assert "Direito Penal" in edition_line
    assert len({title_line, edition_line, notice_line, court_line}) == 4
    assert elements[2] not in edition_line
    assert elements[3] not in notice_line


def test_convert_inf0024e_video_do_julgamento_unaffected(tmp_path) -> None:
    source = tmp_path / "inf0024e-pagina-4-video-julgamento.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=3)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]

    assert "VÍDEO DO JULGAMENTO" in normalized_lines
    assert "ÁUDIO DO TEXTO" in normalized_lines
    assert "VÍDEO DO JULGAMENTO ÁUDIO DO TEXTO" not in normalized_lines


def test_convert_aintaresp_page_11_papel_nome_unaffected(tmp_path) -> None:
    source = tmp_path / "aintaresp-pagina-11.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=10)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert (
        "Sessão Virtual de 20/10/2020 a 26/10/2020 Relator do AgInt Exmo. "
        "Sr. Ministro GURGEL DE FARIA Presidente da Sessão Exmo. Sr. "
        "Ministro GURGEL DE FARIA"
    ) in _normalize_whitespace(markdown)


def test_convert_resp_page_2_signature_block_unaffected(tmp_path) -> None:
    source = tmp_path / "resp-pagina-2.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "REsp_1704551-SP.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=1)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert (
        "Tarso Sanseverino, Ricardo Villas Bôas Cueva, Marco Aurélio Bellizze "
        "e Moura Ribeiro votaram com a Sra. Ministra Relatora. Dr(a). FÁBIO "
        "LIMA QUINTAS, pela parte RECORRIDA: ITAU UNIBANCO S.A. Brasília "
        "(DF), 02 de abril de 2019(Data do Julgamento) MINISTRA NANCY ANDRIGHI"
    ) in _normalize_whitespace(markdown)


def test_convert_inf0024e_removes_repetitive_url_footer(tmp_path) -> None:
    source = tmp_path / "inf0024e-paginas-1-a-3.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_page_range(corpus_pdf, source, start_index=0, end_index=2)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert (
        "processo.stj.jus.br/jurisprudencia/externo/informativo/"
        not in markdown
    )
    page_markers = ["[[Pág. 1]]", "[[Pág. 2]]", "[[Pág. 3]]"]
    assert all(marker in markdown for marker in page_markers)
    assert [markdown.index(marker) for marker in page_markers] == sorted(
        markdown.index(marker) for marker in page_markers
    )
    assert (
        "A competência da Justiça Federal para julgar crimes ambientais"
        in markdown
    )


def test_convert_inf0024e_preserves_repeated_legal_title(tmp_path) -> None:
    source = tmp_path / "inf0024e-titulo-paginas-1-a-3.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_page_range(corpus_pdf, source, start_index=0, end_index=2)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert "Informativo de Jurisprudência n. 24" in markdown
    assert (
        "processo.stj.jus.br/jurisprudencia/externo/informativo/"
        not in markdown
    )
    page_markers = ["[[Pág. 1]]", "[[Pág. 2]]", "[[Pág. 3]]"]
    assert all(marker in markdown for marker in page_markers)
    assert [markdown.index(marker) for marker in page_markers] == sorted(
        markdown.index(marker) for marker in page_markers
    )


def test_convert_inf0024e_page_14_separates_saiba_mais_items(tmp_path) -> None:
    source = tmp_path / "inf0024e-pagina-14.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=13)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]
    items = [
        "Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 117: "
        "INTERCEPTAÇÃO TELEFÔNICA - I",
        "Jurisprudência em Teses / DIREITO PROCESSUAL PENAL - EDIÇÃO N. 69",
        "Informativo de Jurisprudência n. 751",
    ]

    assert all(item in _normalize_whitespace(markdown) for item in items)
    for item in items:
        item_line = next(line for line in normalized_lines if item in line)
        assert all(other not in item_line for other in items if other != item)


def test_convert_inf0024e_page_18_separates_saiba_mais_items(tmp_path) -> None:
    source = tmp_path / "inf0024e-pagina-18.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=17)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]
    thesis = (
        "Jurisprudência em Teses / DIREITO PENAL - EDIÇÃO N. 57: CRIMES "
        "CONTRA A ADMINISTRAÇÃO PÚBLICA"
    )
    informativo = "Informativo de Jurisprudência n. 388"

    assert thesis in _normalize_whitespace(markdown)
    assert informativo in _normalize_whitespace(markdown)
    thesis_line = next(line for line in normalized_lines if thesis in line)
    informativo_line = next(
        line for line in normalized_lines if informativo in line
    )
    assert informativo not in thesis_line
    assert thesis not in informativo_line


def test_convert_inf0024e_page_4_separates_precedent_from_next_informativo(
    tmp_path,
) -> None:
    source = tmp_path / "inf0024e-pagina-4.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=3)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]
    precedent = (
        "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA "
        "SEÇÃO, julgado em 10/04/2019, DJe 16/04/2019"
    )
    informativos = [
        "Informativo de Jurisprudência n. 135",
        "Informativo de Jurisprudência n. 474",
        "Informativo de Jurisprudência n. 346",
        "Informativo de Jurisprudência n. 174",
    ]

    precedent_line = next(line for line in normalized_lines if precedent in line)
    assert "Informativo de Jurisprudência n. 474" not in precedent_line
    for item in informativos:
        item_line = next(line for line in normalized_lines if item in line)
        assert all(other not in item_line for other in informativos if other != item)


def test_convert_inf0024e_page_4_saiba_mais_items_remain_separated(
    tmp_path,
) -> None:
    source = tmp_path / "inf0024e-pagina-4.pdf"
    corpus_pdf = Path(__file__).parents[1] / "input" / "Inf0024E.pdf"
    _isolate_first_page(corpus_pdf, source, page_index=3)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )
    normalized_lines = [
        " ".join(line.split()) for line in markdown.splitlines() if line.strip()
    ]
    items = [
        "Informativo de Jurisprudência n. 135",
        "CC 159976/SP, Rel. Ministro ANTONIO SALDANHA PALHEIRO, TERCEIRA "
        "SEÇÃO, julgado em 10/04/2019, DJe 16/04/2019",
        "Informativo de Jurisprudência n. 474",
        "Informativo de Jurisprudência n. 346",
        "Informativo de Jurisprudência n. 174",
    ]

    item_line_indexes = [
        next(index for index, line in enumerate(normalized_lines) if item in line)
        for item in items
    ]
    assert len(set(item_line_indexes)) == len(items)


def test_convert_cc_2002_page_1_recomposes_art_2_paragraph(tmp_path) -> None:
    source = tmp_path / "codigo-civil-pagina-1.pdf"
    _isolate_first_page(
        Path("input/L10.406_CC_2002.pdf"),
        source,
        page_index=0,
    )

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    # Esperado falhar hoje: o Art. 2º ainda é fragmentado entre parágrafos.
    assert (
        "Art. 2º A personalidade civil da pessoa começa do nascimento com "
        "vida; mas a lei põe a salvo, desde a concepção, os direitos do "
        "nascituro."
    ) in markdown


def test_convert_cc_2002_removes_repetitive_print_header_and_footer(
    tmp_path,
) -> None:
    source = tmp_path / "codigo-civil-paginas-1-a-3.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "L10.406_CC_2002.pdf"
    )
    _isolate_page_range(corpus_pdf, source, start_index=0, end_index=2)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert "30/11/24, 19:06 L10406compilada" not in markdown
    assert (
        "https://www.planalto.gov.br/ccivil_03/leis/2002/"
        "l10406compilada.htm"
        not in markdown
    )
    page_markers = ["[[Pág. 1]]", "[[Pág. 2]]", "[[Pág. 3]]"]
    assert all(marker in markdown for marker in page_markers)
    assert [markdown.index(marker) for marker in page_markers] == sorted(
        markdown.index(marker) for marker in page_markers
    )
    assert "Art. 2" in markdown


def test_convert_cc_2002_marks_final_index_section(tmp_path) -> None:
    source = tmp_path / "codigo-civil-paginas-175-a-180.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "L10.406_CC_2002.pdf"
    )
    _isolate_page_range(corpus_pdf, source, start_index=174, end_index=179)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    assert "# ÍNDICE" in markdown.splitlines()
    article_index = markdown.index("Art. 2.046")
    index_heading = markdown.index("# ÍNDICE")
    assert article_index < index_heading

    index_content = markdown[index_heading:]
    assert (
        "LIVRO I DAS PESSOAS" in index_content
        or "P A R T E" in index_content
    )
    assert "Todas as remissões, em diplomas legislativos" in markdown


def test_convert_aintaresp_page_3_preserves_paragraph_reading_order(
    tmp_path,
) -> None:
    source = tmp_path / "aintaresp-pagina-3.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    )
    _isolate_first_page(corpus_pdf, source, page_index=2)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    normalized_text = _normalize_whitespace(markdown)
    first = "Requer, ao final, o provimento do especial com a atribuição do valor de"
    second = "R$ 10.000,00 (dez mil reais) à causa."
    assert normalized_text.index(first) < normalized_text.index(second)


def test_convert_aintaresp_page_7_preserves_contiguous_text(
    tmp_path,
) -> None:
    source = tmp_path / "aintaresp-pagina-7.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    )
    _isolate_first_page(corpus_pdf, source, page_index=6)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    normalized_text = _normalize_whitespace(markdown)
    assert (
        "ORIENTAÇÃO PACIFICADA NO STJ. DIVERGÊNCIA JURISPRUDENCIAL NÃO "
        "CARACTERIZADA"
    ) in normalized_text
    assert "interpretação jurídica" in normalized_text


def test_convert_aintaresp_page_10_preserves_paragraph_reading_order(
    tmp_path,
) -> None:
    source = tmp_path / "aintaresp-pagina-10.pdf"
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    )
    _isolate_first_page(corpus_pdf, source, page_index=9)

    markdown, _relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    normalized_text = _normalize_whitespace(markdown)
    first = "Diante do exposto, DOU PARCIAL PROVIMENTO ao agravo"
    second = "interno, apenas para afastar a Súmula 283 do STF."
    assert normalized_text.index(first) < normalized_text.index(second)


def test_convert_complete_aintaresp_preserves_native_reading_order(
    tmp_path,
) -> None:
    corpus_pdf = (
        Path(__file__).parents[1] / "input" / "AINTARESP_1462304-PA.pdf"
    )

    markdown, _relatorio = convert_document(
        pdf_path=corpus_pdf,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
    )

    normalized_text = _normalize_whitespace(markdown)
    page_3_first = (
        "Requer, ao final, o provimento do especial com a atribuição do valor de"
    )
    page_3_second = "R$ 10.000,00 (dez mil reais) à causa."
    page_10_first = "Diante do exposto, DOU PARCIAL PROVIMENTO ao agravo"
    page_10_second = "interno, apenas para afastar a Súmula 283 do STF."

    assert normalized_text.index(page_3_first) < normalized_text.index(
        page_3_second
    )
    assert (
        "ORIENTAÇÃO PACIFICADA NO STJ. DIVERGÊNCIA JURISPRUDENCIAL NÃO "
        "CARACTERIZADA"
    ) in normalized_text
    assert "interpretação jurídica" in normalized_text
    assert normalized_text.index(page_10_first) < normalized_text.index(
        page_10_second
    )
    for page_number in range(1, 13):
        assert f"[[Pág. {page_number}]]" in markdown


def test_convert_document_with_ocr_page_success(
    tmp_path,
    monkeypatch,
) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)
    simulated_text = "Texto extraído com sucesso pelo OCR simulado."
    fake_engine = SimpleNamespace(
        convert=lambda _path: SimpleNamespace(text_content=simulated_text)
    )
    monkeypatch.setattr(
        "pipeline_juridico.converter.create_ocr_engine",
        lambda **_kwargs: fake_engine,
    )

    markdown, relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=True,
        ocr_api_key="fake-key-for-tests",
        ocr_model="gemini-2.0-flash",
    )

    assert all(not page.errors for page in relatorio.pages)
    assert relatorio.pages[0].method == Metodo.ocr_integral
    assert simulated_text in markdown


def test_convert_document_ocr_needed_but_no_ocr_flag(tmp_path) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)

    with pytest.raises(MarkdownValidationError):
        convert_document(
            pdf_path=source,
            output_path=tmp_path / "saida.md",
            temp_root=tmp_path / "temp",
            use_ocr=False,
        )


def test_convert_document_ocr_needed_no_ocr_flag_with_allow_partial(
    tmp_path,
) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)

    markdown, relatorio = convert_document(
        pdf_path=source,
        output_path=tmp_path / "saida.md",
        temp_root=tmp_path / "temp",
        use_ocr=False,
        allow_partial=True,
    )

    assert relatorio.pages[0].method is Metodo.erro
    assert relatorio.pages[0].errors
    assert ILLEGIBLE_TEXT_MARKER in markdown


def test_convert_document_missing_ocr_config_raises(tmp_path) -> None:
    source = tmp_path / "digitalizado.pdf"
    _create_scanned_pdf(source)

    with pytest.raises(OcrConfigurationError):
        convert_document(
            pdf_path=source,
            output_path=tmp_path / "saida.md",
            temp_root=tmp_path / "temp",
            use_ocr=True,
        )
