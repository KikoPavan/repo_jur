"""Canonical pre-delivery materialization and provenance validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .index import _write_atomic_json, parse_canonical_document


@dataclass(frozen=True)
class MaterializedConcept:
    concept_id: str
    metadata: Mapping[str, Any]
    body: str
    result: Mapping[str, Any]


class MaterializationError(ValueError):
    pass


def _record_condition(derived_root: Path | None, concept_id: str, condition: str) -> None:
    if derived_root is not None:
        _write_atomic_json(Path(derived_root) / "observability" / "last-materialization.json", {"concept_id": concept_id, "condition": condition})


def _provenance(metadata: Mapping[str, Any], body: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    sources = metadata.get("sources")
    if isinstance(sources, list) and sources:
        result["source_refs"] = sources
        pdfs = [source for source in sources if isinstance(source, dict) and (source.get("media_type") == "application/pdf" or str(source.get("type", "")).lower() == "pdf")]
        singular = metadata.get("repo_jur_pdf_hash")
        plural = metadata.get("repo_jur_pdf_hashes")
        if len(pdfs) == 1 and (pdfs[0].get("resource") or pdfs[0].get("path")) and (singular or pdfs[0].get("sha256")):
            result["source_pdf"] = pdfs[0].get("resource") or pdfs[0]["path"]
            result["repo_jur_pdf_hash"] = singular or pdfs[0]["sha256"]
        elif len(pdfs) >= 2:
            hashes = plural if isinstance(plural, dict) else {str(source["id"]): source["sha256"] for source in pdfs if source.get("id") and source.get("sha256")}
            if len(hashes) == len(pdfs):
                result["repo_jur_pdf_hashes"] = dict(hashes)
    import re
    pages = []
    for value in re.findall(r"\[\[Pág\.\s*(\d+)\]\]", body):
        page = int(value)
        if page not in pages:
            pages.append(page)
    if pages:
        result["page_refs"] = pages
    return result


def materialize(concept_id: str, bundle_root: Path, *, derived_root: Path | None = None) -> MaterializedConcept:
    root = Path(bundle_root).resolve()
    path = (root / f"{concept_id}.md").resolve()
    if not path.is_relative_to(root) or not path.is_file():
        _record_condition(derived_root, concept_id, "missing")
        raise MaterializationError("canonical concept is missing")
    metadata, body = parse_canonical_document(path.read_text(encoding="utf-8"))
    result: dict[str, Any] = {"concept_id": concept_id, "text_content": body}
    result.update({key: metadata[key] for key in ("type", "status", "tags") if key in metadata})
    result.update(_provenance(metadata, body))
    return MaterializedConcept(concept_id, metadata, body, result)
