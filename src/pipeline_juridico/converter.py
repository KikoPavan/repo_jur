from .models import Metodo


def format_page_marker(number: int, method: Metodo) -> str:
    return f"[[Pág. {number}]]\n<!-- método: {method.value} -->"
