"""Conservative Markdown cleanup."""

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


def clean_markdown(text: str) -> str:
    """Normalize Markdown formatting without changing its content."""
    if text == "":
        return ""

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+(?=\n|$)", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.rstrip("\n") + "\n"
