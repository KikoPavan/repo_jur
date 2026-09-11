"""OCR Fidelity and Uncertainty Control module."""

from __future__ import annotations

import re
import unicodedata
import uuid

from .models import FidelityAudit, FidelityIssue


def _generate_issue_id() -> str:
    """Generate a non-content-derived unique identifier for an issue."""
    return str(uuid.uuid4())


def _normalize_entity(text: str) -> str:
    """Normalize entity for comparison: NFKD, casefold, no accents, collapsed whitespace."""
    text = unicodedata.normalize("NFKD", text)
    text = "".join([c for c in text if not unicodedata.combining(c)])
    text = text.casefold()
    return re.sub(r"\s+", " ", text).strip()


def _get_norm_map(text: str) -> tuple[str, list[int]]:
    """Normalize whitespace and return (normalized_text, norm_to_source_mapping)."""
    norm_chars = []
    mapping = []

    i = 0
    while i < len(text):
        if text[i].isspace():
            start_ws = i
            while i < len(text) and text[i].isspace():
                i += 1
            if norm_chars and i < len(text):
                norm_chars.append(" ")
                mapping.append(start_ws)
        else:
            norm_chars.append(text[i])
            mapping.append(i)
            i += 1

    return "".join(norm_chars), mapping


def detect_duplications(text: str, page_number: int) -> list[FidelityIssue]:
    """Detect substantial internal repetitions within a page using gap-based decision."""
    issues = []
    norm_text, mapping = _get_norm_map(text)

    min_len = 120
    seen_windows: dict[str, int] = {}

    step = 1
    for i in range(0, len(norm_text) - min_len + 1, step):
        window = norm_text[i : i + min_len]
        if window in seen_windows:
            prev_i = seen_windows[window]

            match_len = min_len
            while (
                i + match_len < len(norm_text)
                and prev_i + match_len < i
                and norm_text[i + match_len] == norm_text[prev_i + match_len]
            ):
                match_len += 1

            # Use source offsets for gap calculation
            source_prev_i = mapping[prev_i]
            source_i = mapping[i]
            source_match_end = mapping[prev_i + match_len - 1] + 1

            gap = source_i - source_match_end

            if match_len >= 120 and 0 <= gap <= 1.5 * match_len:
                issues.append(
                    FidelityIssue(
                        issue_id=_generate_issue_id(),
                        issue_type="duplication",
                        detector="internal_repetition_detector",
                        page_number=page_number,
                        size=match_len,
                        related_offsets=[source_prev_i, source_i],
                        resolution="flagged",
                    )
                )
                return issues

            seen_windows[window] = i
        else:
            seen_windows[window] = i

    return issues


def monitor_sensitive_tokens(text: str, page_number: int) -> list[FidelityIssue]:
    """Monitor specific deterministic patterns known to be OCR-sensitive."""
    issues = []

    suspicious_section_marker = re.finditer(r"\b8\s+(\d{1,3})\b", text)

    for m in suspicious_section_marker:
        start = max(0, m.start() - 60)
        prefix = text[start : m.start()]

        if re.search(
            r"(?i)\b(?:art(?:igo|\.)?|lei|fls\.?)\b\s*[\d\.]*[\s,]*$", prefix.strip()
        ):
            issues.append(
                FidelityIssue(
                    issue_id=_generate_issue_id(),
                    issue_type="sensitive_token_uncertainty",
                    detector="section_marker_confusion_detector",
                    page_number=page_number,
                    offset_start=m.start(),
                    offset_end=m.end(),
                    size=m.end() - m.start(),
                    resolution="flagged",
                )
            )

    return issues


def check_entity_consistency(
    text: str, page_number: int, global_entities: dict[str, tuple]
) -> list[FidelityIssue]:
    """Check for inconsistent variants of entities using structural comparison."""
    issues = []

    title_case_name = r"\b[A-Z][a-zà-ÿ]{1,}(?:\s+(?:da|de|do|dos|das|e)\s+[A-Z][a-zà-ÿ]{1,}|\s+[A-Z][a-zà-ÿ]{1,})+\b"
    all_caps_name = r"\b[A-Z]{2,}(?:\s+(?:DA|DE|DO|DOS|DAS|E)\s+[A-Z]{2,}|\s+[A-Z]{2,})+\b"

    found_spans: list[tuple[str, int, int]] = []

    for reg in [title_case_name, all_caps_name]:
        for m in re.finditer(reg, text):
            found_spans.append((m.group(0), m.start(), m.end()))

    for m in re.finditer(r"\b[A-Z]{4,5}\b", text):
        entity = m.group(0)
        vowels = len(re.findall(r"[AEIOU]", entity))
        if vowels <= 1:
            found_spans.append((entity, m.start(), m.end()))

    for span, start, end in found_spans:
        norm_span = _normalize_entity(span)
        tokens = norm_span.split()

        for seen_span, data in global_entities.items():
            if len(data) == 2:
                _seen_page, seen_offset = data
                seen_tokens = _normalize_entity(seen_span).split()
            else:
                _seen_page, seen_offset, seen_tokens = data

            norm_seen = _normalize_entity(seen_span)

            if norm_span == norm_seen:
                continue

            if len(tokens) == len(seen_tokens) and len(tokens) >= 2:
                diffs = 0
                for t1, t2 in zip(tokens, seen_tokens):
                    if t1 != t2:
                        if _levenshtein(t1, t2) == 1:
                            diffs += 1
                        else:
                            diffs = 100
                            break

                if diffs == 1:
                    issues.append(
                        FidelityIssue(
                            issue_id=_generate_issue_id(),
                            issue_type="entity_inconsistency",
                            detector="entity_consistency_checker",
                            page_number=page_number,
                            offset_start=start,
                            offset_end=end,
                            size=len(span),
                            related_offsets=[seen_offset],
                            resolution="flagged",
                        )
                    )

            elif (len(tokens) == 1 and len(seen_tokens) == 1 and
                  4 <= len(tokens[0]) <= 5 and len(tokens[0]) == len(seen_tokens[0]) and
                  _levenshtein(tokens[0], seen_tokens[0]) == 1):
                issues.append(
                    FidelityIssue(
                        issue_id=_generate_issue_id(),
                        issue_type="entity_inconsistency",
                        detector="entity_consistency_checker",
                        page_number=page_number,
                        offset_start=start,
                        offset_end=end,
                        size=len(span),
                        related_offsets=[seen_offset],
                        resolution="flagged",
                    )
                )

        if span not in global_entities:
            global_entities[span] = (page_number, start, tokens)

    return issues


def _levenshtein(s1: str, s2: str) -> int:
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def detect_visual_uncertainty(text: str, page_number: int) -> list[FidelityIssue]:
    """Detect words with suspicious alphanumeric mixing or high noise."""
    issues = []

    tech_context_pattern = r"(?i)\b(?:código|CRC|verificador|chave|autenticação|id|matrícula)\b"

    words = re.finditer(r"\b[A-Za-z0-9]{6,}\b", text)
    for m in words:
        word = m.group(0)

        if re.fullmatch(r"\d+", word):
            continue

        if any(c.isdigit() for c in word) and any(c.isalpha() for c in word):
            if word in ["ESCRITURA4", "DESPADEC1"]:
                continue
            if re.fullmatch(r"\d{12}v\d", word):
                continue
            if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", word):
                continue
            if re.fullmatch(r"[0-9a-f]{8}", word):
                continue

            transitions = 0
            for i in range(len(word) - 1):
                if word[i].isalpha() != word[i + 1].isalpha():
                    transitions += 1

            is_hex = re.fullmatch(r"[0-9a-fA-F]+", word)
            threshold = 6 if is_hex else 3

            if transitions >= threshold:
                context_start = max(0, m.start() - 50)
                context_end = min(len(text), m.end() + 50)
                context = text[context_start:context_end]

                if not re.search(tech_context_pattern, context):
                    issues.append(
                        FidelityIssue(
                            issue_id=_generate_issue_id(),
                            issue_type="visual_uncertainty",
                            detector="alphanumeric_mixing_detector",
                            page_number=page_number,
                            offset_start=m.start(),
                            offset_end=m.end(),
                            size=len(word),
                            resolution="flagged",
                        )
                    )

    lines = text.split("\n")
    offset = 0
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 20:
            # Strip ONLY structural markdown characters
            clean_line = re.sub(r"[#*_`~>\\[\]\(\)]", "", stripped)

            if len(clean_line) > 0:
                special = len(re.findall(r"[^\w\s\.,;:\-\/]", clean_line))
                if special / len(clean_line) > 0.3:
                    issues.append(
                        FidelityIssue(
                            issue_id=_generate_issue_id(),
                            issue_type="visual_uncertainty",
                            detector="line_noise_detector",
                            page_number=page_number,
                            offset_start=offset,
                            offset_end=offset + len(line),
                            size=len(line),
                            resolution="flagged",
                        )
                    )
        offset += len(line) + 1

    return issues


class FidelityManager:
    """Manages fidelity auditing and uncertainty control."""

    def __init__(self):
        self.entities: dict[str, tuple] = {}

    def apply_controls(
        self,
        markdown: str,
        page_number: int,
    ) -> tuple[str, FidelityAudit]:
        """Apply fidelity controls without automated mutation."""
        audit = FidelityAudit()

        audit.issues.extend(detect_visual_uncertainty(markdown, page_number))
        audit.issues.extend(detect_duplications(markdown, page_number))
        audit.issues.extend(monitor_sensitive_tokens(markdown, page_number))
        audit.issues.extend(
            check_entity_consistency(markdown, page_number, self.entities)
        )

        return markdown, audit
