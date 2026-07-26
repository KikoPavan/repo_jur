from __future__ import annotations

from dataclasses import dataclass

import fitz


@dataclass
class NativeTextSignal:
    block_count: int
    char_count: int


def inspect_native_text(page: fitz.Page) -> NativeTextSignal:
    blocks = page.get_text("blocks")
    text_blocks = [b for b in blocks if len(b) > 6 and b[6] == 0]
    block_count = len(text_blocks)
    char_count = sum(
        len("".join(b[4].split())) for b in text_blocks
    )
    return NativeTextSignal(block_count=block_count, char_count=char_count)
