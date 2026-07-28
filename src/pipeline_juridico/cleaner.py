"""Conservative Markdown cleanup."""

from collections import Counter
import re


ILLEGIBLE_TEXT_MARKER = "[[TEXTO ILEGÍVEL]]"

_PAGE_MARKER_PATTERN = re.compile(r"^\[\[Pág\. \d+\]\]$")
_METHOD_COMMENT_PATTERN = re.compile(r"^<!-- método: .+ -->$")
_LEGISLATIVE_MARKER_PATTERN = re.compile(
    r"^(PARTE|LIVRO|TÍTULO|TITULO|CAPÍTULO|CAPITULO|"
    r"SEÇÃO|SECAO|SUBSEÇÃO|SUBSECAO)\b\s*"
    r"(?:[IVXLCDM]+|ÚNICO|UNICO)?\s*$",
    flags=re.IGNORECASE,
)
_DIGIT_SEQUENCE_PATTERN = re.compile(r"\d+")
_PAGE_COUNTER = r"(?:\d+\s*/\s*\d+|Página\s*\d+\s*(?:de|/)\s*\d+)"
_URL = (
    r"(?:https?://\S+|"
    r"(?:[\w-]+\.)+[a-z]{2,}(?:\.[a-z]{2,})?/\S*)"
)
_REMOVABLE_MARGIN = (
    rf"(?:"
    rf"\d{{1,2}}/\d{{1,2}}/\d{{2,4}},?\s*"
    rf"\d{{1,2}}:\d{{2}}(?:\s+\S+)?|"
    rf"{_URL}(?:\s+{_PAGE_COUNTER})?|"
    rf"{_PAGE_COUNTER}"
    rf")"
)
_FIRST_MARGIN_PATTERN = re.compile(rf"^{_REMOVABLE_MARGIN}")
_LAST_MARGIN_PATTERN = re.compile(rf"{_REMOVABLE_MARGIN}$")


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

    def _is_uppercase_led(text: str) -> bool:
        return bool(text) and text[0].isupper()

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
            and not (
                _is_uppercase_led(current_text)
                and formal_structure_pattern.match(current_text)
            )
            and not (
                _is_uppercase_led(previous_text)
                and bare_structure_pattern.match(previous_text)
            )
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


def remove_repetitive_margins(markdown: str) -> str:
    """Remove only recognized headers and footers repeated across pages."""
    if not markdown:
        return markdown

    had_trailing_newline = markdown.endswith("\n")
    lines = markdown.splitlines()
    page_starts = [
        index
        for index, line in enumerate(lines)
        if _PAGE_MARKER_PATTERN.fullmatch(line)
    ]
    if not page_starts:
        return markdown

    pages: list[tuple[int, int, int, int]] = []
    for page_index, start in enumerate(page_starts):
        end = (
            page_starts[page_index + 1]
            if page_index + 1 < len(page_starts)
            else len(lines)
        )
        content_indices = [
            index
            for index in range(start, end)
            if lines[index].strip()
            and not _PAGE_MARKER_PATTERN.fullmatch(lines[index])
            and not _METHOD_COMMENT_PATTERN.fullmatch(lines[index])
        ]
        if content_indices:
            pages.append(
                (start, end, content_indices[0], content_indices[-1])
            )

    if not pages:
        return markdown

    minimum_occurrences = (3 * len(pages) + 4) // 5
    first_matches = {
        first: _FIRST_MARGIN_PATTERN.match(lines[first])
        for _, _, first, _ in pages
    }
    last_matches = {
        last: _LAST_MARGIN_PATTERN.search(lines[last])
        for _, _, _, last in pages
    }
    first_templates = Counter(
        re.sub(
            r"\s+",
            " ",
            _DIGIT_SEQUENCE_PATTERN.sub("#", match.group()),
        )
        for match in first_matches.values()
        if match
    )
    last_templates = Counter(
        re.sub(
            r"\s+",
            " ",
            _DIGIT_SEQUENCE_PATTERN.sub("#", match.group()),
        )
        for match in last_matches.values()
        if match
    )

    removals: dict[int, str] = {}
    for _, _, first, last in pages:
        first_line = lines[first]
        first_match = first_matches[first]
        if first_match:
            first_template = re.sub(
                r"\s+",
                " ",
                _DIGIT_SEQUENCE_PATTERN.sub("#", first_match.group()),
            )
            if first_templates[first_template] >= minimum_occurrences:
                removals[first] = first_line[first_match.end():].lstrip()

        last_line = removals.get(last, lines[last])
        last_match = last_matches[last]
        if last_match:
            last_template = re.sub(
                r"\s+",
                " ",
                _DIGIT_SEQUENCE_PATTERN.sub("#", last_match.group()),
            )
            if last_templates[last_template] >= minimum_occurrences:
                current_match = _LAST_MARGIN_PATTERN.search(last_line)
                if current_match:
                    removals[last] = (
                        last_line[:current_match.start()].rstrip()
                    )

    processed_lines = [
        removals.get(index, line)
        for index, line in enumerate(lines)
        if index not in removals or removals[index]
    ]
    result = "\n".join(processed_lines)
    if had_trailing_newline:
        result += "\n"
    return result


def normalize_legal_symbols(content: str) -> str:
    """Normalize OCR-split legal ordinal and number symbols."""
    content = re.sub(r"\b(Art\.\s*\d+)\s+o\b", r"\1º", content)
    content = re.sub(r"(?<!\w)(§\s*\d+)\s+o\b", r"\1º", content)
    content = re.sub(r"\b(Lei\s+n)\s+o\b", r"\1º", content)
    content = re.sub(
        r"\b([Pp]arágrafo\s+\d+)\s+o\b(?:\s+(?=,))?",
        r"\1º",
        content,
    )
    return content


def join_symbol_across_page_break(markdown: str) -> str:
    """Normalize a law-number symbol split across a page marker."""
    return re.sub(
        r"(Lei\s+n)(\n\n\[\[Pág\. \d+\]\]\n"
        r"<!-- método: [^\n]+ -->\n\n)o\s+(?=\d)",
        r"\1º\2",
        markdown,
    )


def build_legislative_headings(markdown: str) -> str:
    """Combine bare legislative markers and titles into Markdown headings."""
    heading_levels = {
        "parte": 1,
        "livro": 2,
        "título": 3,
        "titulo": 3,
        "capítulo": 4,
        "capitulo": 4,
        "seção": 5,
        "secao": 5,
        "subseção": 6,
        "subsecao": 6,
    }
    paragraphs = re.split(r"\n\n", markdown)
    processed: list[str] = []
    index = 0

    while index < len(paragraphs):
        marker_text = paragraphs[index].strip()
        marker_match = _LEGISLATIVE_MARKER_PATTERN.fullmatch(marker_text)
        if marker_match and index + 1 < len(paragraphs):
            title_text = paragraphs[index + 1].strip()
            title_is_excluded = (
                _PAGE_MARKER_PATTERN.fullmatch(title_text)
                or _METHOD_COMMENT_PATTERN.fullmatch(title_text)
                or _LEGISLATIVE_MARKER_PATTERN.fullmatch(title_text)
            )
            if not title_is_excluded:
                level = heading_levels[marker_match.group(1).casefold()]
                processed.append(
                    f"{'#' * level} {marker_text} — {title_text}"
                )
                index += 2
                continue

        processed.append(paragraphs[index])
        index += 1

    return "\n\n".join(processed)


def mark_final_index(markdown: str) -> str:
    """Mark a structurally dense final index after the document's last article."""
    paragraphs = re.split(r"\n\n", markdown)
    article_pattern = re.compile(r"^Art\.?\s*\d+")
    structural_pattern = re.compile(
        r"^(?:#{1,6}\s|"
        r"(?:PARTE|LIVRO|TÍTULO|TITULO|CAPÍTULO|CAPITULO|"
        r"SEÇÃO|SECAO|SUBSEÇÃO|SUBSECAO)\b)"
    )

    last_article_index = None
    for index in range(len(paragraphs) - 1, -1, -1):
        paragraph = paragraphs[index].strip()
        if (
            _PAGE_MARKER_PATTERN.fullmatch(paragraph)
            or _METHOD_COMMENT_PATTERN.fullmatch(paragraph)
        ):
            continue
        if article_pattern.match(paragraph):
            last_article_index = index
            break

    if last_article_index is None:
        return markdown

    structural_count = 0
    for paragraph in paragraphs[last_article_index + 1:]:
        stripped = paragraph.strip()
        if (
            _PAGE_MARKER_PATTERN.fullmatch(stripped)
            or _METHOD_COMMENT_PATTERN.fullmatch(stripped)
        ):
            continue
        if structural_pattern.match(stripped):
            structural_count += 1

    if structural_count < 3:
        return markdown

    paragraphs.insert(last_article_index + 1, "# ÍNDICE")
    return "\n\n".join(paragraphs)


def clean_markdown(text: str) -> str:
    """Normalize Markdown formatting without changing its content."""
    if text == "":
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+(?=\n|$)", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.rstrip("\n") + "\n"
