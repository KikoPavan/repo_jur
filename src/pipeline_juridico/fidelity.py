"""OCR Fidelity and Uncertainty Control module."""

from __future__ import annotations

import hashlib
import re

from .models import FidelityAudit, FidelityIssue


def get_fingerprint(text: str) -> str:
    """Generate a privacy-safe fingerprint for a text snippet."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def detect_duplications(text: str, page_number: int) -> list[FidelityIssue]:
    """Detect substantial internal repetitions within a page."""
    issues = []
    # Normalize whitespace only
    norm_text = re.sub(r"\s+", " ", text).strip()

    # Minimum length for a duplication to be considered "substantial"
    min_len = 100

    # Use step=1 to ensure we don't miss any overlapping windows
    # for a typical page (3-5k chars), this is ~3000-5000 iterations, which is fine.
    seen_windows: dict[str, int] = {}

    for i in range(len(norm_text) - min_len + 1):
        window = norm_text[i : i + min_len]
        if window in seen_windows:
            prev_i = seen_windows[window]
            if i - prev_i >= min_len:
                issues.append(
                    FidelityIssue(
                        issue_type="duplication",
                        detector="internal_repetition_detector",
                        page_number=page_number,
                        size=len(window),
                        fingerprint=get_fingerprint(window),
                        resolution="flagged",
                    )
                )
                # Found one, skip to avoid spamming the same block
                return issues
        else:
            seen_windows[window] = i

    return issues


def monitor_sensitive_tokens(text: str, page_number: int) -> list[FidelityIssue]:
    """Monitor specific deterministic patterns known to be OCR-sensitive."""
    issues = []

    # Pattern: 8 followed by digits (common OCR error for §)
    # Requires legal context: near 'art', 'artigo', ',', CPC, CC, etc.
    legal_context_pattern = r"(?i)art(?:igo|\.)?|CPC|CC|CPP|CLT|CP|Lei|STF|STJ|TJMG|TJSP|,\s*8|8\s+\d+,"

    suspicious_section_marker = re.finditer(r"\b8\s+(\d{1,3})\b", text)
    for m in suspicious_section_marker:
        # Check context around the match (20 chars window)
        start = max(0, m.start() - 20)
        end = min(len(text), m.end() + 20)
        context = text[start:end]

        if re.search(legal_context_pattern, context):
            issues.append(
                FidelityIssue(
                    issue_type="sensitive_token_uncertainty",
                    detector="section_marker_confusion_detector",
                    page_number=page_number,
                    offset_start=m.start(),
                    offset_end=m.end(),
                    size=m.end() - m.start(),
                    fingerprint=get_fingerprint(m.group(0)),
                    resolution="flagged",
                )
            )

    return issues


def check_entity_consistency(
    text: str, page_number: int, global_entities: dict[str, int]
) -> list[FidelityIssue]:
    """Check for inconsistent variants of entities (Names, Process IDs)."""
    issues = []

    legal_keywords = {
        "ACÓRDÃO", "RELATÓRIO", "EMENTA", "DECISÃO", "SENTENÇA", "PROCESSO",
        "TRIBUNAL", "JUSTIÇA", "FEDERAL", "ESTADUAL", "RECURSO", "APELAÇÃO",
        "AGRAVO", "ORDEM", "HABEAS", "CORPUS", "SUPREMO", "CONSELHO",
        "ESTADO", "MUNICÍPIO", "UNIÃO", "MINISTÉRIO", "PÚBLICO", "DEFENSORIA",
        "ADVOGADO", "PROCURADOR", "ESCRIVÃO", "CARTÓRIO", "REGISTRO", "IMÓVEIS"
    }

    # Title Case candidates (Allowing connectors)
    title_case_regex = r"\b[A-Z][a-zà-ÿ]{1,}(?:\s+(?:da|de|do|dos|das|e)\s+[A-Z][a-zà-ÿ]{1,}|\s+[A-Z][a-zà-ÿ]{1,}){1,}\b"
    candidates = re.findall(title_case_regex, text)

    # ALL CAPS candidates (4+ chars for siglas like JKMG/JKMQ)
    candidates.extend(re.findall(r"\b[A-Z]{4,}\b", text))

    unique_candidates = set(candidates)

    # Legitimate abbreviations/vocabulary protection
    legitimate_abbreviations = {
        "TJMG", "TJSP", "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "STJ", "STF",
        "OAB", "CNJ", "MPF", "MPE", "IPCA", "IGPM", "INPC", "IRPJ", "CSLL",
        "FGTS", "INSS", "PIS", "COFINS", "PAG", "DOC", "REF", "MOD", "VOL",
        "CAP", "ART", "CPC", "CPP", "CLT", "NCPC"
    }

    for entity in unique_candidates:
        if entity.upper() in legal_keywords or entity.upper() in legitimate_abbreviations:
            continue

        if any(kw in entity.upper() for kw in ["ARTIGO", "PARÁGRAFO", "LEI N"]):
            continue

        for seen_entity in global_entities:
            if entity == seen_entity:
                continue

            # Compare only same length or very close (diff <= 1)
            if abs(len(entity) - len(seen_entity)) <= 1:
                dist = _levenshtein(entity, seen_entity)
                if dist == 1:
                    issues.append(
                        FidelityIssue(
                            issue_type="entity_inconsistency",
                            detector="entity_consistency_checker",
                            page_number=page_number,
                            fingerprint=f"{get_fingerprint(entity)}/{get_fingerprint(seen_entity)}",
                            resolution="flagged",
                        )
                    )

        if entity not in global_entities:
            global_entities[entity] = page_number

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

    legitimate_prefix = r"^(?:Art|P[áa]g|Lei|fls|doc|n[º°ª]|ID|Ref|Mod|V)[0-9]"

    words = re.finditer(r"\b[A-Za-z0-9]{6,}\b", text)
    for m in words:
        word = m.group(0)
        if (
            any(c.isdigit() for c in word)
            and any(c.isalpha() for c in word)
            and not re.match(legitimate_prefix, word, re.IGNORECASE)
        ):
            issues.append(
                    FidelityIssue(
                        issue_type="visual_uncertainty",
                        detector="alphanumeric_mixing_detector",
                        page_number=page_number,
                        offset_start=m.start(),
                        offset_end=m.end(),
                        size=len(word),
                        fingerprint=get_fingerprint(word),
                        resolution="flagged",
                    )
                )

    lines = text.split("\n")
    offset = 0
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 20:
            special = len(re.findall(r"[^\w\s\.,;:\(\)\[\]\-]", stripped))
            if special / len(stripped) > 0.3:
                issues.append(
                    FidelityIssue(
                        issue_type="visual_uncertainty",
                        detector="line_noise_detector",
                        page_number=page_number,
                        offset_start=offset,
                        offset_end=offset + len(line),
                        size=len(line),
                        fingerprint=get_fingerprint(line),
                        resolution="flagged",
                    )
                )
        offset += len(line) + 1

    return issues


class FidelityManager:
    """Manages fidelity auditing and uncertainty control."""

    def __init__(self):
        self.entities: dict[str, int] = {}

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
