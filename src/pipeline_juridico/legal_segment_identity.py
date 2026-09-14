"""Fail-closed legal identity resolution for structural source segments."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from .legal_semantic_review import _deterministic_extract
from .legal_source_segmentation import PRECEDENT_HEADER_PATTERN, Segment


class IdentityStatus(str, Enum):
    RESOLVED = "resolved"
    REQUIRES_OPERATOR_METADATA = "requires_operator_metadata"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class IdentityResolution:
    status: IdentityStatus
    fields: Mapping[str, object]
    reason: str | None


_REQUIRED_IDENTITY = {
    "Legislacao": ("repo_jur_lei_tipo", "repo_jur_lei_numero", "repo_jur_lei_ano", "repo_jur_lei_esfera"),
    "Jurisprudencia": ("repo_jur_processo_numero", "repo_jur_tribunal"),
    "TemaJuridico": ("repo_jur_tema_numero", "repo_jur_tribunal"),
    "PrecedenteVinculante": ("repo_jur_precedente_numero", "repo_jur_tribunal"),
}

_TRIBUNAL_NAME = r"(?:STJ|STF|Superior Tribunal de Justiça|Supremo Tribunal Federal)"
_SELF_CITATION = re.compile(
    r"\bTema(?:\s+Repetitivo)?\s+(?P<number>\d+)\s*/\s*(?P<tribunal>STJ|STF)\b",
    re.IGNORECASE,
)
_SELF_REFERENTIAL_TRIBUNAL = re.compile(
    rf"(?:{_TRIBUNAL_NAME}[^\r\n.!?]{{0,180}}\b(?:no|neste|sobre o) "
    rf"presente Tema Repetitivo\b|"
    rf"\b(?:julgamento|decisão|afetação) d[oa] (?:tema|matéria) "
    rf"(?:pelo|pela|no|na|perante)\s+{_TRIBUNAL_NAME})",
    re.IGNORECASE,
)
_STJ_INSTITUTIONAL_ORGAN = re.compile(
    r"\b(?:Primeira Seção|Segunda Seção|Corte Especial|Vice-Presidência do STJ)\b",
    re.IGNORECASE,
)
_STF_INSTITUTIONAL_ORGAN = re.compile(
    r"\b(?:Plenário do STF|Plenário do Supremo Tribunal Federal)\b",
    re.IGNORECASE,
)
_INSTITUTIONAL_ACT = re.compile(
    r"\b(?:afet(?:a|ado|ou|ação)|admit(?:e|iu)|sobrest(?:a|ado|ou)|decid(?:e|iu)|"
    r"acolh(?:e|eu)|julg(?:a|ou|amento)|embargos? de declaração|tese jurídica firmada)\b",
    re.IGNORECASE,
)


def _precedent_own_evidence_tribunals(body: str, own_number: str) -> frozenset[str]:
    """Collect tribunals supported by evidence about this precedent itself."""
    tribunals: set[str] = set()

    for match in _SELF_CITATION.finditer(body):
        if match.group("number") != own_number:
            continue
        line_prefix = body[body.rfind("\n", 0, match.start()) + 1:match.start()]
        if re.search(r"(?:\bVide\s+|\bRepercussão Geral\s+)$", line_prefix, re.IGNORECASE):
            continue
        tribunals.add(match.group("tribunal").upper())

    # Structural anchor: a tribunal mention and an unnumbered self-reference must
    # occur in the same sentence. Real examples are “o julgamento do tema pelo
    # STJ” (Tema 731) and “Superior Tribunal de Justiça ... no presente Tema
    # Repetitivo” (Tema 1016).
    for match in _SELF_REFERENTIAL_TRIBUNAL.finditer(body):
        phrase = match.group(0)
        if re.search(r"\b(?:STJ|Superior Tribunal de Justiça)\b", phrase, re.IGNORECASE):
            tribunals.add("STJ")
        if re.search(r"\b(?:STF|Supremo Tribunal Federal)\b", phrase, re.IGNORECASE):
            tribunals.add("STF")

    # Institutional acts count only when the sentence does not name a foreign
    # Tema as the act's object (or names this record's own number).
    for sentence in re.split(r"(?<=[.!?])\s+|[\r\n]+", body):
        # The fixed header's status/Órgão labels are identity-neutral by
        # themselves: “Tema Repetitivo” does not automatically imply STJ.
        if PRECEDENT_HEADER_PATTERN.fullmatch(sentence):
            continue
        if not _INSTITUTIONAL_ACT.search(sentence):
            continue
        cited_numbers = {
            match.group("number") for match in _SELF_CITATION.finditer(sentence)
        }
        if cited_numbers and cited_numbers != {own_number}:
            continue
        if (
            re.search(r"\bVice-Presidência do STJ\b", sentence, re.IGNORECASE)
            and re.search(r"\b(?:REsp|RE|processo|recurso extraordinário)\b", sentence, re.IGNORECASE)
            and not re.search(
                rf"\b(?:presente Tema Repetitivo|tema\s+{re.escape(own_number)}\b)",
                sentence,
                re.IGNORECASE,
            )
        ):
            continue
        if _STJ_INSTITUTIONAL_ORGAN.search(sentence):
            tribunals.add("STJ")
        if _STF_INSTITUTIONAL_ORGAN.search(sentence):
            tribunals.add("STF")
    return frozenset(tribunals)


def resolve_segment_identity(
    concept_type: object,
    segment_body: str | Segment,
    *,
    boundary_rule_id: str | None = None,
) -> IdentityResolution:
    """Resolve canonical fields from one segment body, never its operational label."""
    type_name = getattr(concept_type, "value", concept_type)
    if type_name not in _REQUIRED_IDENTITY:
        return IdentityResolution(
            IdentityStatus.REQUIRES_OPERATOR_METADATA,
            MappingProxyType({}),
            "unsupported_concept_type",
        )
    if isinstance(segment_body, Segment):
        body = segment_body.body
        rule_id = segment_body.boundary_rule_id
        leading_page: str | int | None = segment_body.page_start
    else:
        body = segment_body
        rule_id = boundary_rule_id
        leading_page = None

    if (
        type_name == "TemaJuridico"
        and (
            rule_id == "jurisprudencia-em-teses-edicao-v1"
            or re.search(r"^Edição n\. \d+ Brasília, \d{1,2} de [^\W\d_]+ de \d{4}\s*$", body, re.MULTILINE)
        )
    ):
        return IdentityResolution(
            IdentityStatus.REQUIRES_OPERATOR_METADATA,
            MappingProxyType({}),
            "jurisprudencia_em_teses_edicao_not_valid_temajuridico",
        )

    if isinstance(segment_body, Segment):
        extracted = _deterministic_extract(body, leading_page=leading_page)
    else:
        extracted = _deterministic_extract(body)
    values: dict[str, list[object]] = {}
    for field in extracted:
        values.setdefault(field.name, [])
        if field.value not in values[field.name]:
            values[field.name].append(field.value)

    if type_name == "PrecedenteVinculante":
        header_values = list(PRECEDENT_HEADER_PATTERN.finditer(body))
        own_numbers = list(dict.fromkeys(match.group(1) for match in header_values))
        if len(own_numbers) > 1:
            return IdentityResolution(
                IdentityStatus.AMBIGUOUS,
                MappingProxyType({}),
                "conflicting_identity_field:repo_jur_precedente_numero",
            )
        if len(own_numbers) == 1:
            values["repo_jur_precedente_numero"] = own_numbers
            statuses = list(dict.fromkeys(match.group(2).lower() for match in header_values))
            if len(statuses) == 1:
                values["repo_jur_precedente_status"] = statuses
            own_tribunals = _precedent_own_evidence_tribunals(body, own_numbers[0])
            if len(own_tribunals) > 1:
                return IdentityResolution(
                    IdentityStatus.AMBIGUOUS,
                    MappingProxyType({}),
                    "conflicting_identity_field:repo_jur_tribunal",
                )
            # PrecedenteVinculante deliberately replaces the generic scanner's
            # substring/first-occurrence result. Other concept types retain it;
            # improving that generic heuristic is separate architectural debt.
            values.pop("repo_jur_tribunal", None)
            if own_tribunals:
                values["repo_jur_tribunal"] = list(own_tribunals)

    required = _REQUIRED_IDENTITY[str(type_name)]
    for name in required:
        if len(values.get(name, ())) > 1:
            return IdentityResolution(
                IdentityStatus.AMBIGUOUS,
                MappingProxyType({}),
                f"conflicting_identity_field:{name}",
            )
    missing = [name for name in required if len(values.get(name, ())) != 1]
    if missing:
        return IdentityResolution(
            IdentityStatus.REQUIRES_OPERATOR_METADATA,
            MappingProxyType({}),
            "missing_identity_fields:" + ",".join(missing),
        )
    fields = {name: values[name][0] for name in required}
    if type_name == "PrecedenteVinculante" and len(values.get("repo_jur_precedente_status", ())) == 1:
        fields["repo_jur_precedente_status"] = values["repo_jur_precedente_status"][0]
    return IdentityResolution(IdentityStatus.RESOLVED, MappingProxyType(fields), None)
