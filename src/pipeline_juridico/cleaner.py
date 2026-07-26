"""Conservative Markdown cleanup."""

import re


def clean_markdown(text: str) -> str:
    """Normalize Markdown formatting without changing its content."""
    if text == "":
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+(?=\n|$)", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.rstrip("\n") + "\n"
