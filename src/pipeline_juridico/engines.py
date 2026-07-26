from markitdown import MarkItDown


def create_native_engine() -> MarkItDown:
    return MarkItDown(enable_plugins=False)
