from __future__ import annotations

import fitz

from pipeline_juridico.inspector import open_pdf


def test_open_pdf_valid_one_page(tmp_path) -> None:
    pdf_path = tmp_path / "valid.pdf"
    doc = fitz.open()
    doc.new_page()
    doc.save(pdf_path)
    doc.close()

    result = open_pdf(str(pdf_path))
    assert result.page_count == 1
    result.close()
