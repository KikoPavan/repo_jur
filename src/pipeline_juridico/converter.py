from dataclasses import dataclass

from .models import Metodo


@dataclass
class PageBlock:
    number: int
    method: Metodo
    content: str


def format_page_marker(number: int, method: Metodo) -> str:
    return f"[[Pág. {number}]]\n<!-- método: {method.value} -->"


def compose_document(blocks: list[PageBlock]) -> str:
    ordered_blocks = sorted(blocks, key=lambda b: b.number)
    formatted_blocks = [
        f"{format_page_marker(block.number, block.method)}\n\n{block.content}"
        for block in ordered_blocks
    ]
    return "\n\n".join(formatted_blocks)
