import re


class MarkdownValidationError(Exception):
    pass


_PAGE_WITH_METHOD_PATTERN = re.compile(
    r"\[\[Pág\. (\d+)\]\]\n<!-- método: (\w+) -->"
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
