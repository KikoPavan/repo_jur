import time
import uuid
from dataclasses import asdict
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

import fitz

from .cleaner import (
    ILLEGIBLE_TEXT_MARKER,
    build_legislative_headings,
    clean_markdown,
    ensure_illegible_marker_authorized,
    join_symbol_across_page_break,
    mark_final_index,
    normalize_legal_symbols,
    normalize_thin_space_entities,
    recompose_native_paragraphs,
    remove_repetitive_margins,
)
from .config import RoutingConfig
from .engines import (
    create_native_engine,
    create_ocr_engine,
    verify_ocr_evidence,
)
from . import __version__
from .hashing import sha256_bytes
from .inspector import inspect_source, isolated_page_workspace
from .models import (
    ArtifactsInfo,
    InputInfo,
    Metodo,
    Phase1Info,
    Relatorio,
    TimingInfo,
)
from .report import (
    build_ocr_info,
    build_page_result,
    build_runtime_info,
    compute_relevant_config_fingerprint,
    strip_technical_routing_metadata,
)
from .router import route_page


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


def _line_direction(line: dict) -> tuple[float, float]:
    return tuple(round(value, 2) for value in line.get("dir", (1.0, 0.0)))


def _line_text(line: dict) -> str:
    return "".join(span.get("text", "") for span in line.get("spans", []))


def _bbox_within_tolerance(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
    tolerance: float,
) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(left, right))


def _deduplicated_text_blocks_with_line_x0s(
    page: fitz.Page,
    tolerance: float = 2.0,
) -> list[tuple[tuple[float, float, float, float, str], list[float]]]:
    dict_blocks = [
        block
        for block in page.get_text("dict")["blocks"]
        if block.get("type") == 0
    ]
    seen_non_horizontal: list[
        tuple[tuple[float, float, float, float], str]
    ] = []
    deduplicated = []
    for block in dict_blocks:
        kept_line_texts: list[str] = []
        line_x0s: list[float] = []
        removed_line = False
        for line in block.get("lines", []):
            text = _line_text(line)
            if _line_direction(line) != (1.0, 0.0):
                bbox = tuple(round(value, 1) for value in line["bbox"])
                is_duplicate = any(
                    text == seen_text
                    and _bbox_within_tolerance(
                        bbox,
                        seen_bbox,
                        tolerance,
                    )
                    for seen_bbox, seen_text in seen_non_horizontal
                )
                if is_duplicate:
                    removed_line = True
                    continue
                seen_non_horizontal.append((bbox, text))
            kept_line_texts.append(text)
            line_x0s.append(line["bbox"][0])
        if not kept_line_texts:
            continue
        block_bbox = block["bbox"]
        text_block = (
            block_bbox[0],
            block_bbox[1],
            block_bbox[2],
            block_bbox[3],
            "\n".join(kept_line_texts) + "\n",
        )
        deduplicated.append((text_block, [] if removed_line else line_x0s))
    return deduplicated


def _deduplicated_text_blocks(
    page: fitz.Page,
    tolerance: float = 2.0,
) -> list[tuple[float, float, float, float, str]]:
    """Return text blocks after dropping duplicate non-horizontal lines."""
    return [
        block
        for block, _ in _deduplicated_text_blocks_with_line_x0s(
            page,
            tolerance,
        )
    ]


def _has_duplicated_rotated_block(
    page: fitz.Page,
    tolerance: float = 2.0,
) -> bool:
    dict_blocks = [
        block
        for block in page.get_text("dict")["blocks"]
        if block.get("type") == 0
    ]
    seen: list[tuple[tuple[float, float, float, float], str]] = []
    for block in dict_blocks:
        for line in block.get("lines", []):
            if _line_direction(line) == (1.0, 0.0):
                continue
            text = _line_text(line)
            bbox = tuple(round(value, 1) for value in line["bbox"])
            if any(
                text == seen_text
                and _bbox_within_tolerance(bbox, seen_bbox, tolerance)
                for seen_bbox, seen_text in seen
            ):
                return True
            seen.append((bbox, text))
    return False


def _geometric_reading_order_text(page: fitz.Page) -> str:
    text_blocks = _deduplicated_text_blocks(page)
    ordered_blocks = sorted(
        text_blocks,
        key=lambda block: (round(block[1], 1), block[0]),
    )
    return "\n".join(block[4] for block in ordered_blocks)


def _sorted_native_text_blocks(
    page: fitz.Page,
) -> list[tuple[float, float, str, list[float]]]:
    blocks_with_line_x0s = _deduplicated_text_blocks_with_line_x0s(page)
    ordered_blocks = sorted(
        blocks_with_line_x0s,
        key=lambda item: (round(item[0][1], 1), item[0][0]),
    )
    normalized_blocks = []
    for block, line_x0s in ordered_blocks:
        raw_lines = block[4].split("\n")
        if raw_lines and raw_lines[-1] == "":
            raw_lines.pop()
        if len(line_x0s) != len(raw_lines):
            line_x0s = []
        normalized_blocks.append((block[1], block[3], block[4], line_x0s))
    return normalized_blocks


def _page_has_large_text(
    page: fitz.Page,
    threshold: float = 20.0,
) -> bool:
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                if (
                    span.get("text", "").strip()
                    and span.get("size", 0.0) >= threshold
                ):
                    return True
    return False


def _reading_order_tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def _lexical_overlap(left: str, right: str) -> float:
    left_tokens = _reading_order_tokens(left)
    right_tokens = _reading_order_tokens(right)
    largest_token_count = max(len(left_tokens), len(right_tokens))
    if not largest_token_count:
        return 0.0
    common_token_count = sum(
        (Counter(left_tokens) & Counter(right_tokens)).values()
    )
    return common_token_count / largest_token_count


def _has_native_reading_order_defect(
    native_content: str,
    reference_content: str,
) -> bool:
    native_tokens = _reading_order_tokens(native_content)
    reference_tokens = _reading_order_tokens(reference_content)
    return (
        bool(native_tokens)
        and native_tokens != reference_tokens
        and _lexical_overlap(native_content, reference_content) >= 0.98
    )


def _markdown_table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_markdown_separator(cells: list[str]) -> bool:
    return bool(cells) and all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in cells
    )


def _has_fabricated_table_structure(content: str) -> bool:
    lines = content.splitlines()
    index = 0
    while index < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue

        table_lines: list[str] = []
        while index < len(lines) and lines[index].lstrip().startswith("|"):
            table_lines.append(lines[index])
            index += 1

        rows = [_markdown_table_cells(line) for line in table_lines]
        if len(rows) < 2 or not _is_markdown_separator(rows[1]):
            continue
        column_count = len(rows[0])
        if column_count < 2 or any(
            len(row) != column_count for row in rows
        ):
            continue

        data_rows = rows[2:]
        single_row_table = not data_rows
        disguised_single_column = bool(data_rows) and all(
            row[0] and all(not cell for cell in row[1:])
            for row in data_rows
        )
        if single_row_table or disguised_single_column:
            return True

    return False


def _has_fabricated_native_table(
    native_content: str,
    reference_content: str,
) -> bool:
    return (
        _has_fabricated_table_structure(native_content)
        and _lexical_overlap(native_content, reference_content) >= 0.98
    )


def _split_ocr_tail(
    raw_content: str,
    marker: str = "[End OCR]*",
) -> tuple[str, str] | None:
    idx = raw_content.rfind(marker)
    if idx == -1:
        return None
    split_at = idx + len(marker)
    return raw_content[:split_at], raw_content[split_at:]


def _tail_fragments(tail: str) -> list[str]:
    return [
        fragment.strip()
        for fragment in tail.split("\n\n")
        if fragment.strip()
    ]


def _is_degenerate_fragment_tail(
    fragments: list[str],
    max_fragment_chars: int = 2,
    min_short_fraction: float = 0.9,
) -> bool:
    if not fragments:
        return False
    short = sum(
        1 for fragment in fragments if len(fragment) <= max_fragment_chars
    )
    return (short / len(fragments)) >= min_short_fraction


def _non_horizontal_line_texts(page: fitz.Page) -> list[str]:
    texts = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            if _line_direction(line) != (1.0, 0.0):
                texts.append(_line_text(line))
    return texts


def _char_multiset_overlap(a: str, b: str) -> float:
    counter_a, counter_b = Counter(a), Counter(b)
    largest = max(sum(counter_a.values()), sum(counter_b.values()))
    if not largest:
        return 0.0
    common = sum((counter_a & counter_b).values())
    return common / largest


def _geometrically_corroborated_vertical_residual(
    fragments: list[str],
    vertical_line_texts: list[str],
    length_ratio_bounds: tuple[float, float] = (0.5, 1.2),
    min_char_overlap: float = 0.80,
) -> bool:
    if not vertical_line_texts:
        return False
    tail_chars = "".join("".join(fragment.split()) for fragment in fragments)
    combined_vertical = "".join(vertical_line_texts)
    if not tail_chars or not combined_vertical:
        return False
    ratio = len(tail_chars) / len(combined_vertical)
    if not (length_ratio_bounds[0] <= ratio <= length_ratio_bounds[1]):
        return False
    return (
        _char_multiset_overlap(tail_chars, combined_vertical)
        >= min_char_overlap
    )


def _replace_fragmented_vertical_residual(
    raw_content: str,
    page_path,
) -> str:
    doc = fitz.open(page_path)
    try:
        vertical_line_texts = _non_horizontal_line_texts(doc[0])
    finally:
        doc.close()
    return _replace_fragmented_vertical_residual_in_text(
        raw_content,
        vertical_line_texts,
    )


def _replace_fragmented_vertical_residual_in_text(
    raw_content: str,
    vertical_line_texts: list[str],
) -> str:
    split = _split_ocr_tail(raw_content)
    if split is None:
        return raw_content
    head, tail = split
    if not tail.strip():
        return raw_content
    fragments = _tail_fragments(tail)
    if not _is_degenerate_fragment_tail(fragments):
        return raw_content
    if not _geometrically_corroborated_vertical_residual(
        fragments,
        vertical_line_texts,
    ):
        return raw_content
    return f"{head}\n\n" + "\n".join(vertical_line_texts) + "\n"


_PAGE_MARKER_SPLIT_PATTERN = re.compile(r"(?=\[\[Pág\. \d+\]\])")
_PAGE_MARKER_NUMBER_PATTERN = re.compile(r"\[\[Pág\. (\d+)\]\]")


def _replace_fragmented_vertical_residuals_in_document(
    markdown: str,
    blocks: list[PageBlock],
    vertical_geometry_by_page: dict[int, list[str]],
) -> str:
    eligible_numbers = {
        block.number
        for block in blocks
        if block.method in (Metodo.hibrido, Metodo.ocr_integral)
    }
    if not eligible_numbers:
        return markdown

    segments = _PAGE_MARKER_SPLIT_PATTERN.split(markdown)
    updated_segments = []
    for segment in segments:
        match = _PAGE_MARKER_NUMBER_PATTERN.match(segment)
        if not match:
            updated_segments.append(segment)
            continue
        page_number = int(match.group(1))
        vertical_line_texts = vertical_geometry_by_page.get(page_number, [])
        if page_number not in eligible_numbers or not vertical_line_texts:
            updated_segments.append(segment)
            continue
        updated_segments.append(
            _replace_fragmented_vertical_residual_in_text(
                segment,
                vertical_line_texts,
            )
        )
    return "".join(updated_segments)


def _strip_internal_ocr_markers(
    markdown: str,
    blocks: list[PageBlock],
    marker: str = "[End OCR]*",
) -> str:
    eligible_numbers = {
        block.number
        for block in blocks
        if block.method in (Metodo.hibrido, Metodo.ocr_integral)
    }
    if not eligible_numbers:
        return markdown

    segments = _PAGE_MARKER_SPLIT_PATTERN.split(markdown)
    updated_segments = []
    for segment in segments:
        match = _PAGE_MARKER_NUMBER_PATTERN.match(segment)
        if not match or int(match.group(1)) not in eligible_numbers:
            updated_segments.append(segment)
            continue
        updated_segments.append(segment.replace(marker, ""))
    return "".join(updated_segments)


def convert_document(
    pdf_path: str | Path,
    *,
    output_path: str | Path,
    temp_root: str | Path,
    allow_partial: bool = False,
    use_ocr: bool = True,
    ocr_api_key: str | None = None,
    ocr_model: str | None = None,
    ocr_base_url: str | None = None,
    ocr_prompt_path: str | Path = "prompts/ocr_literal_ptbr.txt",
    routing_config: RoutingConfig | None = None,
    keep_temp: bool = False,
) -> tuple[str, Relatorio]:
    from .validator import (
        validate_encoding_and_line_endings,
        validate_markdown_matches_report,
        validate_page_content,
        validate_page_markers,
    )

    started_at = datetime.now(timezone.utc)
    source_info = inspect_source(pdf_path)
    native_engine = create_native_engine()
    ocr_engine = None
    page_results = []
    blocks: list[PageBlock] = []
    vertical_geometry_by_page: dict[int, list[str]] = {}
    page_durations_ms: list[int] = []

    with isolated_page_workspace(
        pdf_path,
        temp_root,
        keep_temp=keep_temp,
    ) as page_paths:
        for index, page_path in enumerate(page_paths):
            page_number = index + 1
            page_started_at = time.monotonic()

            doc = fitz.open(page_path)
            try:
                page = doc[0]
                method = route_page(page, routing_config)
                reference_content = (
                    _geometric_reading_order_text(page)
                    if method is Metodo.texto_nativo
                    else ""
                )
                native_blocks_with_x0 = (
                    _sorted_native_text_blocks(page)
                    if method is Metodo.texto_nativo
                    else []
                )
                native_blocks = [
                    (y0, y1, text)
                    for y0, y1, text, _ in native_blocks_with_x0
                ]
                native_line_x0s = [
                    line_x0s
                    for _, _, _, line_x0s in native_blocks_with_x0
                ]
                page_has_large_text = (
                    _page_has_large_text(page)
                    if method is Metodo.texto_nativo
                    else False
                )
                has_duplicated_rotated_block = (
                    _has_duplicated_rotated_block(page)
                    if method is Metodo.texto_nativo
                    else False
                )
                vertical_line_texts = (
                    _non_horizontal_line_texts(page)
                    if method in (Metodo.hibrido, Metodo.ocr_integral)
                    else []
                )
            finally:
                doc.close()
            vertical_geometry_by_page[page_number] = vertical_line_texts

            warnings: list[str] = []
            errors: list[str] = []
            content = ""

            if method is Metodo.vazia:
                pass
            elif method is Metodo.texto_nativo:
                if has_duplicated_rotated_block:
                    content = reference_content
                else:
                    result = native_engine.convert(page_path)
                    content = result.text_content or ""
                    if _has_native_reading_order_defect(
                        content,
                        reference_content,
                    ) or _has_fabricated_native_table(
                        content,
                        reference_content,
                    ):
                        content = reference_content
                content = recompose_native_paragraphs(
                    content,
                    native_blocks,
                    page_has_large_text=page_has_large_text,
                    line_x0s=native_line_x0s,
                )
            elif not use_ocr:
                method = Metodo.erro
                errors.append(
                    "OCR desabilitado via --no-ocr; página não pôde ser processada."
                )
            else:
                if ocr_engine is None:
                    prompt_text = Path(ocr_prompt_path).read_text(encoding="utf-8")
                    ocr_engine = create_ocr_engine(
                        api_key=ocr_api_key,
                        model=ocr_model,
                        base_url=ocr_base_url,
                        prompt=prompt_text,
                    )
                try:
                    result = ocr_engine.convert(page_path)
                except Exception:
                    method = Metodo.erro
                    errors.append(
                        "Falha técnica durante o processamento de OCR."
                    )
                else:
                    raw_content = result.text_content or ""
                    method, evidence_warnings = verify_ocr_evidence(
                        raw_content,
                        method,
                    )
                    if method is Metodo.erro:
                        errors.extend(evidence_warnings)
                    else:
                        warnings.extend(evidence_warnings)
                    content = "" if method is Metodo.erro else raw_content

            if method is Metodo.erro:
                content = ILLEGIBLE_TEXT_MARKER if allow_partial else ""

            duration_ms = int(
                (time.monotonic() - page_started_at) * 1000
            )
            page_durations_ms.append(duration_ms)
            page_results.append(
                build_page_result(
                    page_number=page_number,
                    method=method,
                    content=content,
                    warnings=warnings,
                    errors=errors,
                    truncated=False,
                )
            )
            blocks.append(
                PageBlock(
                    number=page_number,
                    method=method,
                    content=content,
                )
            )

    raw_markdown = compose_document(blocks)
    raw_markdown = normalize_thin_space_entities(raw_markdown)
    raw_markdown = remove_repetitive_margins(raw_markdown)
    raw_markdown = _replace_fragmented_vertical_residuals_in_document(
        raw_markdown,
        blocks,
        vertical_geometry_by_page,
    )
    raw_markdown = _strip_internal_ocr_markers(raw_markdown, blocks)
    raw_markdown = join_symbol_across_page_break(raw_markdown)
    raw_markdown = normalize_legal_symbols(raw_markdown)
    raw_markdown = build_legislative_headings(raw_markdown)
    raw_markdown = mark_final_index(raw_markdown)
    final_markdown = clean_markdown(raw_markdown)

    ensure_illegible_marker_authorized(final_markdown, allow_partial)
    validate_page_markers(final_markdown, expected_page_count=len(blocks))
    validate_page_content(blocks, strict=not allow_partial)
    validate_markdown_matches_report(final_markdown, page_results)
    validate_encoding_and_line_endings(final_markdown)

    finished_at = datetime.now(timezone.utc)
    total_duration_ms = int(
        (finished_at - started_at).total_seconds() * 1000
    )
    literal = strip_technical_routing_metadata(final_markdown)
    runtime_info = build_runtime_info()
    ocr_info = build_ocr_info(
        enabled=use_ocr,
        provider="openai-compatible",
        model=ocr_model or "",
        prompt_path=ocr_prompt_path,
    )
    timing_info = TimingInfo(
        started_at=started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_ms=total_duration_ms,
    )
    relatorio = Relatorio(
        execution_id=str(uuid.uuid4()),
        input=InputInfo(
            sha256=source_info.sha256,
            byte_size=source_info.size_bytes,
            page_count=source_info.pages,
        ),
        phase1=Phase1Info(
            implementation="pipeline-juridico",
            implementation_version=__version__,
            logical_processing_version="1",
            relevant_config_fingerprint=compute_relevant_config_fingerprint(
                allow_partial=allow_partial,
                use_ocr=use_ocr,
                routing_config=routing_config,
            ),
        ),
        artifacts=ArtifactsInfo(
            markdown_sha256=sha256_bytes(literal.encode("utf-8"))
        ),
        pages=page_results,
        telemetry={
            "runtime": asdict(runtime_info),
            "ocr": asdict(ocr_info),
            "timing": asdict(timing_info),
            "input_path": str(pdf_path),
            "output_path": str(output_path),
            "page_durations_ms": page_durations_ms,
        },
    )
    return final_markdown, relatorio
