"""Deterministic, read-only Legal Semantic Review seam."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Callable, Iterable, Mapping

from .contracts import GateState, Phase1Artifacts


class ReviewState(str, Enum):
    OK = "OK"
    WARNING = "WARNING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


@dataclass(frozen=True)
class LegalPatch:
    before: str
    after: str
    reason: str
    confidence: float
    page_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExtractedField:
    name: str
    value: str
    page_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClassificationSuggestion:
    type: str | None
    basis: str
    confidence: float


@dataclass(frozen=True)
class ReviewResult:
    state: ReviewState
    patches: tuple[LegalPatch, ...]
    extracted_fields: tuple[ExtractedField, ...]
    classification_suggestions: tuple[ClassificationSuggestion, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class LegalReviewRule:
    rule_id: str
    rule_version: str
    scope: str
    source: str
    validation_logic_version: str
    evaluate: Callable[[str], list[LegalPatch]]


@dataclass(frozen=True)
class LegalReviewProfile:
    profile_id: str
    profile_version: str
    enabled_rule_ids: tuple[str, ...]


class LegalSemanticReviewError(Exception):
    """Base error for the review boundary."""


class LegalSemanticReviewConfigurationError(LegalSemanticReviewError):
    """The rule registry or selected profile is invalid."""


class LegalSemanticReviewBlockedError(LegalSemanticReviewError):
    """The recorded technical outcome deterministically stops review."""

    def __init__(self, message: str, *, reason: str) -> None:
        super().__init__(message)
        self.reason = reason


_GATE_VOCABULARY = frozenset(state.value for state in GateState)
_ELIGIBLE_GATES = frozenset(
    {GateState.PASS, GateState.PASS_WITH_WARNINGS}
)


def _recorded_gate_outcome(report_json: str) -> GateState:
    if not isinstance(report_json, str):
        raise LegalSemanticReviewBlockedError(
            "technical report must be serialized JSON",
            reason="invalid_report",
        )
    try:
        report: object = json.loads(report_json)
    except (json.JSONDecodeError, TypeError, UnicodeDecodeError) as error:
        raise LegalSemanticReviewBlockedError(
            "technical report JSON is not parseable",
            reason="invalid_report",
        ) from error
    if not isinstance(report, dict):
        raise LegalSemanticReviewBlockedError(
            "technical report root must be an object",
            reason="invalid_report",
        )
    result = report.get("result")
    if not isinstance(result, dict):
        raise LegalSemanticReviewBlockedError(
            "technical report does not record a Quality Gate outcome",
            reason="invalid_report",
        )
    value = result.get("quality_gate")
    if not isinstance(value, str) or value not in _GATE_VOCABULARY:
        raise LegalSemanticReviewBlockedError(
            "technical report does not record a valid Quality Gate outcome",
            reason="invalid_report",
        )
    return GateState(value)


def _preserves_words(patch: LegalPatch) -> bool:
    return Counter(patch.before.split()) == Counter(patch.after.split())


def _deterministic_extract(markdown: str) -> list[ExtractedField]:
    MONTHS = {
        "janeiro": "01", "fevereiro": "02", "março": "03", "marco": "03",
        "abril": "04", "maio": "05", "junho": "06", "julho": "07",
        "agosto": "08", "setembro": "09", "outubro": "10", "novembro": "11",
        "dezembro": "12"
    }

    # 1. Split into pages to trace page_refs
    pages = []
    matches = list(re.finditer(r"\[\[Pág\.\s*(\d+)\]\]", markdown))
    if not matches:
        pages.append(("1", markdown))
    else:
        for i, match in enumerate(matches):
            page_num = match.group(1)
            start_pos = match.end()
            end_pos = matches[i+1].start() if i + 1 < len(matches) else len(markdown)
            page_text = markdown[start_pos:end_pos]
            pages.append((page_num, page_text))

    extracted = []

    # Let's extract Legislative fields
    tipo = None
    numero = None
    ano = None
    lei_page = None

    # Search page by page for legislative types
    for page_num, page_text in pages:
        # 1. Constituição
        if re.search(r"\bCONSTITUIÇÃO\b", page_text, re.IGNORECASE):
            tipo = "constituicao"
            lei_page = page_num
            # Try to find a year, e.g., "DE 1988"
            year_match = re.search(r"\b(?:DE\s+)?(\d{4})\b", page_text, re.IGNORECASE)
            if year_match:
                ano = year_match.group(1)
            break

        # 2. Lei Complementar
        lc_match = re.search(
            r"\bLEI\s+COMPLEMENTAR\s+(?:N[º°\.]?\s*)?([\d\.\-]+)\b(?:[,\s]+DE\s+(\d{1,2})\s+DE\s+([a-zA-ZçÇáéíóúÁÉÍÓÚ]+)\s+DE\s+(\d{4}))?",
            page_text,
            re.IGNORECASE
        )
        if lc_match:
            tipo = "complementar"
            numero = re.sub(r"[^\d\-]", "", lc_match.group(1))
            lei_page = page_num
            if lc_match.group(4):
                ano = lc_match.group(4)
            break

        # 3. Medida Provisória
        mp_match = re.search(
            r"\bMEDIDA\s+PROVISÓRIA\s+(?:N[º°\.]?\s*)?([\d\.\-]+)\b(?:[,\s]+DE\s+(\d{1,2})\s+DE\s+([a-zA-ZçÇáéíóúÁÉÍÓÚ]+)\s+DE\s+(\d{4}))?",
            page_text,
            re.IGNORECASE
        )
        if mp_match:
            tipo = "medida_provisoria"
            numero = re.sub(r"[^\d\-]", "", mp_match.group(1))
            lei_page = page_num
            if mp_match.group(4):
                ano = mp_match.group(4)
            break

        # 4. Decreto
        dec_match = re.search(
            r"\bDECRETO\s+(?:N[º°\.]?\s*)?([\d\.\-]+)\b(?:[,\s]+DE\s+(\d{1,2})\s+DE\s+([a-zA-ZçÇáéíóúÁÉÍÓÚ]+)\s+DE\s+(\d{4}))?",
            page_text,
            re.IGNORECASE
        )
        if dec_match:
            tipo = "decreto"
            numero = re.sub(r"[^\d\-]", "", dec_match.group(1))
            lei_page = page_num
            if dec_match.group(4):
                ano = dec_match.group(4)
            break

        # 5. Lei Ordinária (standard LEI)
        lei_match = re.search(
            r"\bLEI\s+(?:N[º°\.]?\s*)?([\d\.\-]+)\b(?:[,\s]+DE\s+(\d{1,2})\s+DE\s+([a-zA-ZçÇáéíóúÁÉÍÓÚ]+)\s+DE\s+(\d{4}))?",
            page_text,
            re.IGNORECASE
        )
        if lei_match:
            tipo = "ordinaria"
            numero = re.sub(r"[^\d\-]", "", lei_match.group(1))
            lei_page = page_num
            if lei_match.group(4):
                ano = lei_match.group(4)
            break

    if tipo:
        extracted.append(ExtractedField("repo_jur_lei_tipo", tipo, (lei_page,) if lei_page is not None else ()))
    if numero:
        extracted.append(ExtractedField("repo_jur_lei_numero", numero, (lei_page,) if lei_page is not None else ()))
    if ano:
        extracted.append(ExtractedField("repo_jur_lei_ano", ano, (lei_page,) if lei_page is not None else ()))

    # Legislative sphere:
    # Check for structural/header signals: "presidência da república", "casa civil", "diário oficial da união", "senado federal", "congresso nacional"
    for page_num, page_text in pages:
        text_lower = page_text.lower()
        has_signal = False
        for signal in ["presidência da república", "casa civil", "diário oficial da união", "senado federal", "congresso nacional"]:
            if signal in text_lower:
                has_signal = True
                break
        if has_signal:
            extracted.append(ExtractedField("repo_jur_lei_esfera", "federal", (page_num,)))
            break

    # Jurisprudência / Processo fields:
    # Prefer CNJ pattern first on the pages
    processo_num = None
    processo_page: str | None = None
    for page_num, page_text in pages:
        cnj_match = re.search(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b", page_text)
        if cnj_match:
            processo_num = cnj_match.group(0)
            processo_page = page_num
            break

    if not processo_num:
        # If no CNJ found, look for STJ/STF appellate case identifiers:
        # e.g., REsp 1.704.551 - SP or AgInt no AGRAVO EM RECURSO ESPECIAL Nº 1462304 - PA
        for page_num, page_text in pages:
            # Regex covering REsp, AREsp, AgInt, and register numbers
            appellate_match = re.search(
                r"(?i)\b(?:AgInt\s+no\s+)?(?:AREsp|REsp|AgInt|RE|ADI|ADC|ADPF|HC|MS|RMS|AgInt\s+no\s+AREsp|AgInt\s+no\s+REsp|AgInt\s+no\s+AGRAVO\s+EM\s+RECURSO\s+ESPECIAL|AGRAVO\s+EM\s+RECURSO\s+ESPECIAL|RECURSO\s+ESPECIAL)\s*(?:N[º°\.]?|No)?\s*[\d\.\-]+(?:\s*[-/]\s*[A-Z]{2})?\b",
                page_text
            )
            if appellate_match:
                processo_num = re.sub(r"\s+", " ", appellate_match.group(0)).strip()
                processo_page = page_num
                break

    if not processo_num:
        # Fallback to register number: 2017/0091244-2
        for page_num, page_text in pages:
            reg_match = re.search(r"\b\d{4}/\d{7}-\d\b", page_text)
            if reg_match:
                processo_num = reg_match.group(0)
                processo_page = page_num
                break

    if processo_num:
        extracted.append(ExtractedField("repo_jur_processo_numero", processo_num, (processo_page,) if processo_page is not None else ()))

    # Tribunal:
    tribunal = None
    tribunal_page: str | None = None
    for page_num, page_text in pages:
        if any(term in page_text.lower() for term in ["superior tribunal de justiça", "stj"]):
            tribunal = "STJ"
            tribunal_page = page_num
            break
        elif any(term in page_text.lower() for term in ["supremo tribunal federal", "stf"]):
            tribunal = "STF"
            tribunal_page = page_num
            break

    if tribunal:
        extracted.append(ExtractedField("repo_jur_tribunal", tribunal, (tribunal_page,) if tribunal_page is not None else ()))

    # Relator:
    # Matching Relator[a]?:\s*([A-Z\s]+)
    relator = None
    relator_page: str | None = None
    for page_num, page_text in pages:
        relator_match = re.search(
            r"(?i)RELATOR[A]?\s*[:\s]*(?:MINISTRO|MINISTRA)?\s*([A-ZÀ-ÿ\s\.\-]+)",
            page_text
        )
        if relator_match:
            relator_name = relator_match.group(1).strip()
            lines = relator_name.splitlines()
            if lines:
                first_line = lines[0].strip()
                first_line = re.sub(r"^[:\s]+", "", first_line).strip()
                if len(first_line) > 3:
                    # Clean up other fields like RECORRENTE
                    first_line = re.split(
                        r"(?i)\b(?:RECORRENTE|RECORRIDO|AGRAVANTE|AGRAVADO|ADVOGADO)\b",
                        first_line
                    )[0].strip()
                    # Make sure there is no lowercase word
                    first_line = re.split(r"\s*[a-z]\w*\s*", first_line)[0].strip()
                    if len(first_line) > 3:
                        relator = first_line.upper()
                        relator_page = page_num
                        break

    if relator:
        extracted.append(ExtractedField("repo_jur_relator", relator, (relator_page,) if relator_page is not None else ()))

    # Data Julgamento:
    data_julgamento = None
    data_page: str | None = None
    # Prioritize "(Data do Julgamento)" pattern
    for page_num, page_text in pages:
        match = re.search(
            r"(\d{1,2})\s+de\s+([a-zA-ZçÇáéíóúÁÉÍÓÚ]+)\s+de\s+(\d{4})\s*\(Data\s+do\s+Julgamento\)",
            page_text,
            re.IGNORECASE
        )
        if match:
            day = match.group(1).zfill(2)
            month_name = match.group(2).lower()
            year = match.group(3)
            month = MONTHS.get(month_name)
            if month:
                data_julgamento = f"{year}-{month}-{day}"
                data_page = page_num
                break

    if not data_julgamento:
        # Fallback to Portuguese date
        for page_num, page_text in pages:
            match = re.search(
                r"\b(\d{1,2})\s+de\s+([a-zA-ZçÇáéíóúÁÉÍÓÚ]+)\s+de\s+(\d{4})\b",
                page_text,
                re.IGNORECASE
            )
            if match:
                day = match.group(1).zfill(2)
                month_name = match.group(2).lower()
                year = match.group(3)
                month = MONTHS.get(month_name)
                if month:
                    data_julgamento = f"{year}-{month}-{day}"
                    data_page = page_num
                    break

    if data_julgamento:
        extracted.append(ExtractedField("repo_jur_data_julgamento", data_julgamento, (data_page,) if data_page is not None else ()))

    # Ramo do Direito:
    ramo = None
    ramo_page: str | None = None
    for page_num, page_text in pages:
        if "processual civil" in page_text.lower():
            ramo = "DIREITO PROCESSUAL CIVIL"
            ramo_page = page_num
            break
        elif "direito civil" in page_text.lower():
            ramo = "DIREITO CIVIL"
            ramo_page = page_num
            break

    if ramo:
        extracted.append(ExtractedField("repo_jur_ramo_direito", ramo, (ramo_page,) if ramo_page is not None else ()))

    # Tema:
    # Extract TemaJuridico fields:
    # Look for "Tema <numero>" or "Tema Repetitivo <numero>" or "Tema de Repercussão Geral <numero>"
    tema_num = None
    tema_page = None
    for page_num, page_text in pages:
        match = re.search(r"\bTema\s*(?:Repetitivo|de\s+Repercussão\s+Geral)?\s*(?:n[º°\.]?)?\s*(\d+)\b", page_text, re.IGNORECASE)
        if match:
            tema_num = match.group(1)
            tema_page = page_num
            break

    if tema_num:
        extracted.append(ExtractedField("repo_jur_tema_numero", tema_num, (tema_page,) if tema_page is not None else ()))
        if tribunal:
            extracted.append(ExtractedField("repo_jur_tribunal", tribunal, (tema_page,) if tema_page is not None else ()))

    # Precedente:
    # If there are precedents mentioned, extract them strictly from the text
    # e.g., Súmula n. 714/STF or Informativo de Jurisprudência n. 24
    for page_num, page_text in pages:
        sumula_match = re.search(r"Súmula\s*(?:n\.)?\s*(\d+)", page_text, re.IGNORECASE)
        if sumula_match:
            extracted.append(ExtractedField("repo_jur_precedente_numero", sumula_match.group(1), (page_num,)))
            if tribunal:
                extracted.append(ExtractedField("repo_jur_tribunal", tribunal, (page_num,)))

            # Check for deterministic status support with word boundaries
            status = None
            text_lower = page_text.lower()
            if re.search(r"\bcancelad[ao]s?\b", text_lower):
                status = "cancelado"
            elif re.search(r"\brevisad[ao]s?\b", text_lower):
                status = "revisado"
            elif re.search(r"\bativ[ao]s?\b|\bem\s+vigor\b|\bvigente\b", text_lower):
                status = "ativo"

            if status:
                extracted.append(ExtractedField("repo_jur_precedente_status", status, (page_num,)))
            break

    return extracted


@dataclass(frozen=True, init=False)
class LegalSemanticReviewEngine:
    _rules: Mapping[str, LegalReviewRule]

    def __init__(self, rules: Iterable[LegalReviewRule] = ()) -> None:
        registry: dict[str, LegalReviewRule] = {}
        required_fields = (
            "rule_id",
            "rule_version",
            "scope",
            "source",
            "validation_logic_version",
            "evaluate",
        )
        for rule in rules:
            if any(
                not getattr(rule, field_name, None)
                for field_name in required_fields
            ):
                raise LegalSemanticReviewConfigurationError(
                    "review rule is missing required provenance"
                )
            if rule.rule_id in registry:
                raise LegalSemanticReviewConfigurationError(
                    "review rule identifier is duplicated"
                )
            registry[rule.rule_id] = rule
        object.__setattr__(self, "_rules", MappingProxyType(registry))

    def review(
        self,
        phase1_artifacts: Phase1Artifacts,
        profile: LegalReviewProfile,
    ) -> ReviewResult:
        gate = _recorded_gate_outcome(phase1_artifacts.report_json)
        if gate not in _ELIGIBLE_GATES:
            raise LegalSemanticReviewBlockedError(
                "recorded Quality Gate outcome stops review",
                reason="fail_gate",
            )
        if not isinstance(profile, LegalReviewProfile):
            raise LegalSemanticReviewConfigurationError(
                "review profile must be a LegalReviewProfile"
            )
        if not profile.profile_id or not profile.profile_version:
            raise LegalSemanticReviewConfigurationError(
                "review profile is missing required provenance"
            )
        if len(profile.enabled_rule_ids) != len(set(profile.enabled_rule_ids)):
            raise LegalSemanticReviewConfigurationError(
                "review profile contains a duplicate rule identifier"
            )

        enabled: list[LegalReviewRule] = []
        for rule_id in profile.enabled_rule_ids:
            try:
                enabled.append(self._rules[rule_id])
            except KeyError as error:
                raise LegalSemanticReviewConfigurationError(
                    "review profile references an unregistered rule"
                ) from error

        accepted: list[LegalPatch] = []
        warnings: list[str] = []
        requires_review = False
        for rule in enabled:
            proposed = rule.evaluate(phase1_artifacts.markdown)
            if not isinstance(proposed, list) or any(
                not isinstance(patch, LegalPatch) for patch in proposed
            ):
                raise LegalSemanticReviewConfigurationError(
                    f"review rule {rule.rule_id} returned an invalid result"
                )
            for patch in proposed:
                if not _preserves_words(patch):
                    requires_review = True
                    warnings.append(
                        f"rule {rule.rule_id} produced a non-structural patch"
                    )
                    continue
                accepted.append(patch)

        if requires_review:
            state = ReviewState.REVIEW_REQUIRED
        elif accepted:
            state = ReviewState.WARNING
        else:
            state = ReviewState.OK

        extracted_fields = _deterministic_extract(phase1_artifacts.markdown)
        extracted_names = {f.name for f in extracted_fields}

        # Check if there's a numbered act pattern in the text but we are missing number or year
        has_numbered_act_pattern = False
        # Split markdown into pages to scan for numbered act patterns
        matches_pages = list(re.finditer(r"\[\[Pág\.\s*(\d+)\]\]", phase1_artifacts.markdown))
        pages_list = []
        if not matches_pages:
            pages_list.append(phase1_artifacts.markdown)
        else:
            for idx, match_p in enumerate(matches_pages):
                start_p = match_p.end()
                end_p = matches_pages[idx+1].start() if idx + 1 < len(matches_pages) else len(phase1_artifacts.markdown)
                pages_list.append(phase1_artifacts.markdown[start_p:end_p])

        for page_text in pages_list:
            if re.search(r"\b(?:LEI|DECRETO|MEDIDA\s+PROVIS[ÓO]RIA)\s*(?:COMPLEMENTAR\s*)?(?:N[º°\.]?|No|NUMERO)\b", page_text, re.IGNORECASE):
                has_numbered_act_pattern = True
                break

        if has_numbered_act_pattern:
            if "repo_jur_lei_numero" not in extracted_names or "repo_jur_lei_ano" not in extracted_names:
                state = ReviewState.REVIEW_REQUIRED

        return ReviewResult(
            state=state,
            patches=tuple(accepted),
            extracted_fields=tuple(extracted_fields),
            classification_suggestions=(),
            warnings=tuple(warnings),
        )
