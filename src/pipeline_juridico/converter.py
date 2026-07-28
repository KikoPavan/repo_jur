import time
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

import fitz

from .cleaner import (
    ILLEGIBLE_TEXT_MARKER,
    clean_markdown,
    ensure_illegible_marker_authorized,
    normalize_legal_symbols,
    recompose_native_paragraphs,
    remove_repetitive_margins,
)
from .config import RoutingConfig
from .engines import (
    create_native_engine,
    create_ocr_engine,
    verify_ocr_evidence,
)
from .hashing import sha256_bytes
from .inspector import inspect_source, isolated_page_workspace
from .models import (
    Metodo,
    Relatorio,
    SaidaInfo,
    StatusExecucao,
    TimingInfo,
)
from .report import (
    build_ocr_info,
    build_page_result,
    build_runtime_info,
    determine_final_status,
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


def _geometric_reading_order_text(page: fitz.Page) -> str:
    text_blocks = [
        block for block in page.get_text("blocks") if block[6] == 0
    ]
    ordered_blocks = sorted(
        text_blocks,
        key=lambda block: (round(block[1], 1), block[0]),
    )
    return "\n".join(block[4] for block in ordered_blocks)


def _sorted_native_text_blocks(
    page: fitz.Page,
) -> list[tuple[float, float, str]]:
    text_blocks = [
        block for block in page.get_text("blocks") if block[6] == 0
    ]
    ordered_blocks = sorted(
        text_blocks,
        key=lambda block: (round(block[1], 1), block[0]),
    )
    return [
        (block[1], block[3], block[4]) for block in ordered_blocks
    ]


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
                native_blocks = (
                    _sorted_native_text_blocks(page)
                    if method is Metodo.texto_nativo
                    else []
                )
            finally:
                doc.close()

            warnings: list[str] = []
            content = ""

            if method is Metodo.vazia:
                pass
            elif method is Metodo.texto_nativo:
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
                )
            elif not use_ocr:
                method = Metodo.erro
                warnings.append(
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
                    warnings.append(
                        "Falha técnica durante o processamento de OCR."
                    )
                else:
                    raw_content = result.text_content or ""
                    method, evidence_warnings = verify_ocr_evidence(
                        raw_content,
                        method,
                    )
                    warnings.extend(evidence_warnings)
                    content = "" if method is Metodo.erro else raw_content

            if method is Metodo.erro:
                content = ILLEGIBLE_TEXT_MARKER if allow_partial else ""

            status = (
                StatusExecucao.falha
                if method is Metodo.erro
                else StatusExecucao.sucesso
            )
            duration_ms = int(
                (time.monotonic() - page_started_at) * 1000
            )
            page_results.append(
                build_page_result(
                    number=page_number,
                    method=method,
                    status=status,
                    content=content,
                    duration_ms=duration_ms,
                    warnings=warnings,
                    error=None,
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
    raw_markdown = remove_repetitive_margins(raw_markdown)
    raw_markdown = normalize_legal_symbols(raw_markdown)
    final_markdown = clean_markdown(raw_markdown)

    ensure_illegible_marker_authorized(final_markdown, allow_partial)
    validate_page_markers(final_markdown, expected_page_count=len(blocks))
    validate_page_content(blocks, strict=not allow_partial)
    validate_markdown_matches_report(final_markdown, page_results)
    validate_encoding_and_line_endings(final_markdown)

    final_status = determine_final_status(page_results, allow_partial)
    finished_at = datetime.now(timezone.utc)
    total_duration_ms = int(
        (finished_at - started_at).total_seconds() * 1000
    )
    output_bytes = final_markdown.encode("utf-8")
    output_info = SaidaInfo(
        path=str(output_path),
        sha256=sha256_bytes(output_bytes),
    )
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
        run_id=str(uuid.uuid4()),
        status=final_status,
        source=source_info,
        output=output_info,
        runtime=runtime_info,
        ocr=ocr_info,
        timing=timing_info,
        pages=page_results,
    )
    return final_markdown, relatorio
