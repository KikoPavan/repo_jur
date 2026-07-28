"""Conservative Markdown cleanup."""

from collections import Counter
import re


ILLEGIBLE_TEXT_MARKER = "[[TEXTO ILEGÍVEL]]"


class UnauthorizedIllegibleMarkerError(Exception):
    """Raised when partial-output content appears without explicit authorization."""


def ensure_illegible_marker_authorized(text: str, allow_partial: bool) -> None:
    """Reject the illegible-text marker unless partial output was authorized."""
    if ILLEGIBLE_TEXT_MARKER in text and not allow_partial:
        raise UnauthorizedIllegibleMarkerError(
            f"{ILLEGIBLE_TEXT_MARKER} may only appear in output when "
            "--allow-partial is explicitly used."
        )


def recompose_native_paragraphs(
    content: str,
    blocks: list[tuple[float, float, str]],
) -> str:
    """Recompose native text lines when their geometry indicates continuity."""
    if not blocks or any(
        line.strip().startswith("|") for line in content.splitlines()
    ):
        return content
    if any(
        line.strip().startswith(":")
        for _, _, block_text in blocks
        for line in block_text.split("\n")
    ):
        return content

    lines: list[tuple[float, float, str]] = []
    for y0, y1, block_text in blocks:
        physical_lines = [
            re.sub(r"\s+", " ", line).strip()
            for line in block_text.split("\n")
            if line.strip()
        ]
        if not physical_lines:
            continue
        line_height = (y1 - y0) / len(physical_lines)
        for index, line in enumerate(physical_lines):
            line_y0 = y0 + index * line_height
            lines.append((line_y0, line_y0 + line_height, line))

    if not lines:
        return content

    current_line_pattern = re.compile(
        r"^(?:"
        r"Art\.?\s*\d+|"
        r"§\s*\d+|"
        r"Parágrafo\s+(?:único|\d+)|"
        r"[IVXLCDM]+\s*[-–—]|"
        r"[a-z]\)\s|"
        r"\d+[\.\)]\s|"
        r"\[\[Pág\."
        r")"
    )
    formal_structure_pattern = re.compile(
        r"^(?:PARTE|LIVRO|TÍTULO|TITULO|CAPÍTULO|CAPITULO|"
        r"SEÇÃO|SECAO|SUBSEÇÃO|SUBSECAO)\b",
        flags=re.IGNORECASE,
    )
    bare_structure_pattern = re.compile(
        r"^(?:PARTE|LIVRO|TÍTULO|TITULO|CAPÍTULO|CAPITULO|"
        r"SEÇÃO|SECAO|SUBSEÇÃO|SUBSECAO)\b\s*[\wºª°]*\s*$",
        flags=re.IGNORECASE,
    )
    native_label_pattern = re.compile(
        r"^[A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][A-ZÁÀÂÃÉÊÍÓÔÕÚÇ ]*$"
    )
    paragraphs = [lines[0][2]]
    previous_y0, previous_y1, previous_text = lines[0]
    for current_y0, current_y1, current_text in lines[1:]:
        gap = current_y0 - previous_y1
        previous_height = previous_y1 - previous_y0
        should_join = (
            not current_line_pattern.match(current_text)
            and not formal_structure_pattern.match(current_text)
            and not bare_structure_pattern.match(previous_text)
            and not native_label_pattern.match(previous_text)
            and gap <= previous_height * 1.2
        )
        if should_join:
            paragraphs[-1] = (
                f"{paragraphs[-1].rstrip()} {current_text.lstrip()}"
            )
        else:
            paragraphs.append(current_text)
        previous_y0, previous_y1, previous_text = (
            current_y0,
            current_y1,
            current_text,
        )

    geometric_text = "\n\n".join(paragraphs)
    geometric_tokens = re.findall(
        r"\w+", geometric_text.casefold(), flags=re.UNICODE
    )
    content_tokens = re.findall(
        r"\w+", content.casefold(), flags=re.UNICODE
    )
    largest_token_count = max(len(geometric_tokens), len(content_tokens))
    if not largest_token_count:
        overlap = 0.0
    else:
        common_token_count = sum(
            (Counter(geometric_tokens) & Counter(content_tokens)).values()
        )
        overlap = common_token_count / largest_token_count
    return geometric_text if overlap >= 0.98 else content


def clean_markdown(text: str) -> str:
    """Normalize Markdown formatting without changing its content."""
    if text == "":
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+(?=\n|$)", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.rstrip("\n") + "\n"
