from markitdown import MarkItDown

from pipeline_juridico.engines import create_native_engine


def test_create_native_engine_converts_plain_text(tmp_path):
    source = tmp_path / "documento.txt"
    source.write_text("Conteúdo jurídico simples.", encoding="utf-8")

    engine = create_native_engine()
    result = engine.convert(source)

    assert isinstance(engine, MarkItDown)
    assert result.text_content
    assert "Conteúdo jurídico simples." in result.text_content
