import re

from .converter import PageBlock
from .models import Metodo, ResultadoPagina


class MarkdownValidationError(Exception):
    pass


_PAGE_WITH_METHOD_PATTERN = re.compile(
    r"\[\[Pág\. (\d+)\]\]\n<!-- método: (\w+) -->"
)


def validate_page_content(
    blocks: list[PageBlock],
    strict: bool = True,
) -> None:
    for block in blocks:
        if block.method is Metodo.erro:
            if strict:
                raise MarkdownValidationError(
                    f"A página {block.number} está em erro; páginas em erro não são "
                    "permitidas no modo estrito. Use --allow-partial para autorizar "
                    "saída parcial."
                )
            continue

        has_content = bool(block.content.strip())
        if block.method is Metodo.vazia:
            if has_content:
                raise MarkdownValidationError(
                    f"A página {block.number} está marcada como vazia, mas contém "
                    "conteúdo."
                )
            continue

        if not has_content:
            raise MarkdownValidationError(
                f"A página {block.number} com método {block.method.value} deveria "
                "ter conteúdo, mas está vazia."
            )


def validate_markdown_matches_report(
    markdown: str,
    pages: list[ResultadoPagina],
) -> None:
    markdown_pages = {
        int(page_number): method
        for page_number, method in _PAGE_WITH_METHOD_PATTERN.findall(markdown)
    }
    report_pages = {page.number: page.method.value for page in pages}

    missing_in_report = sorted(markdown_pages.keys() - report_pages.keys())
    missing_in_markdown = sorted(report_pages.keys() - markdown_pages.keys())
    if missing_in_report or missing_in_markdown:
        raise MarkdownValidationError(
            "Números de página divergentes: "
            f"presentes no Markdown e ausentes no relatório: {missing_in_report}; "
            f"presentes no relatório e ausentes no Markdown: {missing_in_markdown}."
        )

    for page_number, markdown_method in markdown_pages.items():
        report_method = report_pages[page_number]
        if markdown_method != report_method:
            raise MarkdownValidationError(
                f"Método divergente na página {page_number}: "
                f"Markdown={markdown_method}, relatório={report_method}."
            )


def validate_page_markers(markdown: str, expected_page_count: int) -> None:
    matches = _PAGE_WITH_METHOD_PATTERN.findall(markdown)
    page_numbers = [int(page_number) for page_number, _method in matches]

    marker_count = markdown.count("[[Pág. ")
    method_comment_count = markdown.count("<!-- método: ")
    if (
        marker_count != method_comment_count
        or marker_count != expected_page_count
        or method_comment_count != expected_page_count
    ):
        raise MarkdownValidationError(
            "Cada marcador de página deve ter exatamente um comentário de método "
            "imediatamente associado: "
            f"esperados {expected_page_count}, encontrados {marker_count} "
            f"marcadores e {method_comment_count} comentários de método."
        )

    if len(matches) != expected_page_count:
        raise MarkdownValidationError(
            f"Esperados {expected_page_count} marcadores de página com método, "
            f"mas foram encontrados {len(matches)}."
        )

    duplicate_page_numbers = sorted(
        {
            page_number
            for page_number in page_numbers
            if page_numbers.count(page_number) > 1
        }
    )
    if duplicate_page_numbers:
        duplicates = ", ".join(str(number) for number in duplicate_page_numbers)
        raise MarkdownValidationError(
            f"Números de página duplicados encontrados: {duplicates}."
        )

    expected_sequence = list(range(1, expected_page_count + 1))
    if page_numbers != expected_sequence:
        raise MarkdownValidationError(
            "A sequência de páginas está incorreta ou fora de ordem: "
            f"esperada {expected_sequence}, encontrada {page_numbers}."
        )
