import hashlib
import json
from pathlib import Path

import fitz

from pipeline_juridico.contracts import GateState, Phase1Artifacts
from pipeline_juridico.config import IngestConfig
from pipeline_juridico.ingest_orchestrator import discover_pdfs, run_ingest
from pipeline_juridico.legal_producer import (
    build_candidates,
    parse_candidate_text,
    validate_candidate,
    validate_producer_context,
)
from pipeline_juridico.legal_semantic_review import (
    ExtractedField,
    ReviewResult,
    ReviewState,
)
from pipeline_juridico.legal_source_segmentation import (
    Segment,
    SegmentationOutcome,
    SegmentationResult,
)
from pipeline_juridico.quality_gate import QualityGateResult


def _config(tmp_path: Path, input_dir: Path) -> IngestConfig:
    return IngestConfig(
        input_dir=input_dir,
        bundle_root=tmp_path / "bundle",
        state_dir=tmp_path / "state",
        candidates_dir=tmp_path / "candidates",
        reports_dir=tmp_path / "reports",
    )


def _pdf(path: Path, text: str) -> None:
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        f"Presidencia da Republica\n{text}\nConteudo juridico material da fixture.",
    )
    document.save(path)
    document.close()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree_snapshot(root: Path) -> dict[str, tuple[str, int]] | None:
    if not root.exists():
        return None
    return {
        str(path.relative_to(root)): (_sha256(path), path.stat().st_mtime_ns)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _review(fields: tuple[ExtractedField, ...] = ()) -> ReviewResult:
    return ReviewResult(ReviewState.OK, (), fields, (), ())


def _legislation_fields() -> tuple[ExtractedField, ...]:
    return (
        ExtractedField("repo_jur_lei_esfera", "federal", ("1",)),
        ExtractedField("repo_jur_lei_numero", "10406", ("1",)),
        ExtractedField("repo_jur_lei_ano", "2002", ("1",)),
        ExtractedField("repo_jur_lei_tipo", "ordinaria", ("1",)),
        ExtractedField("publication_ramo_principal", "direito_civil", ("1",)),
    )


def _segments() -> tuple[Segment, Segment]:
    return (
        Segment(
            "segment-0001", "Tema Repetitivo 692", "Tema Repetitivo 692\n[[Pág. 1]]\nConteúdo A.\n",
            1, 1, "precedentes-qualificados-tema-repetitivo-v1",
        ),
        Segment(
            "segment-0002", "Tema Repetitivo 1016", "Tema Repetitivo 1016\n[[Pág. 1]]\nConteúdo B.\n",
            1, 1, "precedentes-qualificados-tema-repetitivo-v1",
        ),
    )


def _patch_segments(monkeypatch, segments: tuple[Segment, ...]) -> None:
    import pipeline_juridico.legal_producer as producer
    import pipeline_juridico.legal_source_segmentation as segmentation

    result = SegmentationResult(SegmentationOutcome.SEGMENTS, segments, None)
    monkeypatch.setattr(producer, "segment_markdown", lambda *_: result)
    monkeypatch.setattr(segmentation, "segment_markdown", lambda *_: result)


def test_discovery_is_nonrecursive_sorted_and_includes_non_pdf(tmp_path: Path) -> None:
    root = tmp_path / "leis"
    root.mkdir()
    (root / "z.txt").write_text("not opened")
    (root / "a.pdf").write_bytes(b"not opened")
    nested = root / "nested"
    nested.mkdir()
    (nested / "LEG_hidden.pdf").write_bytes(b"not opened")
    assert [path.name for path in discover_pdfs(root)] == ["a.pdf", "z.txt"]


def test_reserved_processo_is_not_discovered_or_reported(tmp_path: Path) -> None:
    root = tmp_path / "input" / "leis_jurisprudencia"
    root.mkdir(parents=True)
    (root / "invalid.pdf").write_bytes(b"untouched")
    processo = tmp_path / "input" / "processo"
    processo.mkdir()
    (processo / "LEG_secret.pdf").write_bytes(b"untouched")
    report = run_ingest(_config(tmp_path, root))
    assert [item.filename for item in report.files] == ["invalid.pdf"]


def test_gitkeep_is_excluded_from_report_and_summary(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "input" / "leis_jurisprudencia"
    root.mkdir(parents=True)
    (root / ".gitkeep").write_bytes(b"")
    source = root / "LEG_codigo_civil.pdf"
    _pdf(source, "LEI Nº 10.406, DE 10 DE JANEIRO DE 2002")
    monkeypatch.setattr(
        "pipeline_juridico.legal_producer.LegalSemanticReviewEngine.review",
        lambda *_: _review(_legislation_fields()),
    )

    report = run_ingest(_config(tmp_path, root))

    assert [item.filename for item in report.files] == [source.name]
    assert report.summary == {
        "total": 1,
        "READY_TO_PUBLISH": 1,
        "REVIEW_REQUIRED": 0,
        "BLOCKED": 0,
        "ERROR": 0,
    }


def test_other_dotfile_remains_blocked_and_counted(tmp_path: Path) -> None:
    root = tmp_path / "input" / "leis_jurisprudencia"
    root.mkdir(parents=True)
    (root / ".hidden_notes.pdf").write_bytes(b"must not be opened")

    report = run_ingest(_config(tmp_path, root))

    assert [(item.filename, item.status, item.reason) for item in report.files] == [
        (".hidden_notes.pdf", "BLOCKED", "invalid_or_missing_prefix")
    ]
    assert report.summary == {
        "total": 1,
        "READY_TO_PUBLISH": 0,
        "REVIEW_REQUIRED": 0,
        "BLOCKED": 1,
        "ERROR": 0,
    }


def test_blocked_files_are_reported_without_being_opened(tmp_path: Path) -> None:
    root = tmp_path / "leis"
    root.mkdir()
    pdf = root / "invalid.pdf"
    text = root / "LEG_notes.txt"
    pdf.write_bytes(b"invalid but must not be opened")
    text.write_bytes(b"must not be opened")
    before = {
        item.name: (item.resolve(), item.read_bytes(), _sha256(item))
        for item in (pdf, text)
    }
    report = run_ingest(_config(tmp_path, root))
    assert [(item.filename, item.reason) for item in report.files] == [
        ("LEG_notes.txt", "unsupported_media_type"),
        ("invalid.pdf", "invalid_or_missing_prefix"),
    ]
    assert report.summary["BLOCKED"] == 2
    assert before == {
        item.name: (item.resolve(), item.read_bytes(), _sha256(item))
        for item in (pdf, text)
    }
    persisted = json.loads(Path(report.report_path).read_text())
    assert persisted["summary"] == report.summary


def test_native_legislation_builds_valid_candidate_without_publication(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "input" / "leis_jurisprudencia"
    root.mkdir(parents=True)
    source = root / "LEG_codigo_civil.pdf"
    document = fitz.open()
    page = document.new_page()
    page.insert_text(
        (72, 72),
        "Presidencia da Republica\nLEI Nº 10.406, DE 10 DE JANEIRO DE 2002\nInstitui o Codigo Civil.",
    )
    document.save(source)
    document.close()
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    monkeypatch.setattr(
        "pipeline_juridico.legal_producer.LegalSemanticReviewEngine.review",
        lambda *_: _review(_legislation_fields()),
    )
    config = _config(tmp_path, root)
    before = (source.resolve(), source.read_bytes(), _sha256(source))
    report = run_ingest(config)
    assert report.files[0].status == "READY_TO_PUBLISH", report.files[0]
    assert len(report.files[0].candidates) == 1
    candidate_path = Path(report.files[0].candidates[0]["candidate_path"])
    candidate = parse_candidate_text(candidate_path.read_text(), candidate_path)
    validate_candidate(candidate)
    assert len(list(config.state_dir.glob("*.json"))) == 1
    assert list(bundle.iterdir()) == []
    assert (source.resolve(), source.read_bytes(), _sha256(source)) == before


def test_pre_segments_match_direct_build_candidates_field_for_field(
    tmp_path: Path, monkeypatch
) -> None:
    from pipeline_juridico.legal_segment_identity import IdentityResolution, IdentityStatus

    monkeypatch.chdir(tmp_path)
    root = tmp_path / "input" / "leis_jurisprudencia"
    root.mkdir(parents=True)
    source = root / "PRE_temas_repetitivos.pdf"
    _pdf(source, "Tema Repetitivo 692 e Tema Repetitivo 1016")
    segments = _segments()
    _patch_segments(monkeypatch, segments)
    monkeypatch.setattr(
        "pipeline_juridico.legal_producer.LegalSemanticReviewEngine.review",
        lambda *_: _review(),
    )
    identities = {
        "segment-0001": {"repo_jur_precedente_numero": "692", "repo_jur_tribunal": "STJ"},
        "segment-0002": {"repo_jur_precedente_numero": "1016", "repo_jur_tribunal": "STJ"},
    }
    for fields in identities.values():
        fields["repo_jur_precedente_status"] = "afetado"
    monkeypatch.setattr(
        "pipeline_juridico.legal_producer.resolve_segment_identity",
        lambda _, segment: IdentityResolution(IdentityStatus.RESOLVED, identities[segment.segment_id], None),
    )
    config = _config(tmp_path, root)

    report = run_ingest(config)

    artifacts = Phase1Artifacts(
        (tmp_path / "output" / "PRE_temas_repetitivos.md").read_text(),
        (tmp_path / "logs" / "PRE_temas_repetitivos.report.json").read_text(),
    )
    direct = build_candidates(
        artifacts,
        validate_producer_context({
            "type": "PrecedenteVinculante", "evidence_resource": str(source),
        }),
        config.bundle_root,
        all_segments=True,
        segment_id=None,
    )
    item = report.files[0]
    assert item.status == "READY_TO_PUBLISH"
    assert item.blocked_segments == direct.blocked_segments == []
    assert [candidate["segment_id"] for candidate in item.candidates] == [
        segment.segment_id for segment, _ in direct.built
    ]
    for persisted, (segment, expected) in zip(item.candidates, direct.built, strict=True):
        candidate_path = Path(persisted["candidate_path"])
        actual = parse_candidate_text(candidate_path.read_text(), expected.path)
        assert (actual.type, actual.frontmatter, actual.body, actual.path) == (
            expected.type, expected.frontmatter, expected.body, expected.path,
        )
        assert json.loads(Path(persisted["record_path"]).read_text())["concept_path"] == str(expected.path)


def test_tem_unresolved_segment_reports_review_and_builds_only_resolved(
    tmp_path: Path, monkeypatch
) -> None:
    from pipeline_juridico.legal_segment_identity import IdentityResolution, IdentityStatus

    monkeypatch.chdir(tmp_path)
    root = tmp_path / "leis"
    root.mkdir()
    source = root / "TEM_temas.pdf"
    _pdf(source, "Temas jurídicos segmentados")
    segments = _segments()
    _patch_segments(monkeypatch, segments)
    monkeypatch.setattr(
        "pipeline_juridico.legal_producer.LegalSemanticReviewEngine.review",
        lambda *_: _review(),
    )

    def resolve(_, segment):
        if segment.segment_id == "segment-0002":
            return IdentityResolution(IdentityStatus.AMBIGUOUS, {}, "missing")
        return IdentityResolution(
            IdentityStatus.RESOLVED,
            {"repo_jur_tema_numero": "692", "repo_jur_tribunal": "STJ"},
            None,
        )

    monkeypatch.setattr("pipeline_juridico.legal_producer.resolve_segment_identity", resolve)
    item = run_ingest(_config(tmp_path, root)).files[0]
    assert item.status == "REVIEW_REQUIRED"
    assert item.blocked_segments == [
        {"segment_id": "segment-0002", "reason": "identity_unresolved"}
    ]
    assert [candidate["segment_id"] for candidate in item.candidates] == ["segment-0001"]


def test_quality_gate_fail_is_error_without_candidate_or_state_and_preserves_source(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "leis"
    root.mkdir()
    source = root / "LEG_gate_fail.pdf"
    _pdf(source, "Documento destinado ao quality gate")
    before = (source.resolve(), source.read_bytes(), _sha256(source))
    monkeypatch.setattr(
        "pipeline_juridico.ingest_orchestrator.evaluate",
        lambda *_: QualityGateResult(GateState.FAIL, (), ("forced failure",)),
    )
    config = _config(tmp_path, root)

    item = run_ingest(config).files[0]

    assert (item.status, item.reason, item.candidates) == ("ERROR", "quality_gate_fail", [])
    assert not config.candidates_dir.exists() or not list(config.candidates_dir.iterdir())
    assert not config.state_dir.exists() or not list(config.state_dir.iterdir())
    assert (source.resolve(), source.read_bytes(), _sha256(source)) == before


def test_mixed_rerun_is_byte_identical_and_never_touches_bundle_or_retrieval(
    tmp_path: Path, monkeypatch
) -> None:
    import pipeline_juridico.legal_producer as producer
    import pipeline_juridico.legal_source_segmentation as segmentation
    from pipeline_juridico.legal_segment_identity import IdentityResolution, IdentityStatus
    from pipeline_juridico.quality_gate import evaluate as real_evaluate

    monkeypatch.chdir(tmp_path)
    root = tmp_path / "leis"
    root.mkdir()
    _pdf(root / "LEG_ready.pdf", "LEI Nº 10.406, DE 10 DE JANEIRO DE 2002")
    _pdf(root / "JUR_gate_fail.pdf", "FORCE_GATE_FAIL")
    _pdf(root / "TEM_review.pdf", "MIXED_REVIEW")
    (root / "invalid.pdf").write_bytes(b"must remain unopened")
    config = _config(tmp_path, root)
    config.bundle_root.mkdir()
    (config.bundle_root / "sentinel.txt").write_bytes(b"canonical bundle sentinel")
    retrieval = tmp_path / "var" / "retrieval"
    retrieval.mkdir(parents=True)
    (retrieval / "sentinel.idx").write_bytes(b"retrieval sentinel")
    monkeypatch.setattr(producer.LegalSemanticReviewEngine, "review", lambda _, artifacts, __: (
        _review() if "MIXED_REVIEW" in artifacts.markdown
        else _review(_legislation_fields())
    ))
    real_segment = producer.segment_markdown
    segment_result = SegmentationResult(SegmentationOutcome.SEGMENTS, _segments(), None)

    def segment(markdown, registry):
        return segment_result if "MIXED_REVIEW" in markdown else real_segment(markdown, registry)

    monkeypatch.setattr(producer, "segment_markdown", segment)
    monkeypatch.setattr(segmentation, "segment_markdown", segment)
    monkeypatch.setattr(producer, "resolve_segment_identity", lambda _, item: (
        IdentityResolution(IdentityStatus.AMBIGUOUS, {}, "missing")
        if item.segment_id == "segment-0002"
        else IdentityResolution(
            IdentityStatus.RESOLVED,
            {"repo_jur_tema_numero": "692", "repo_jur_tribunal": "STJ"},
            None,
        )
    ))

    def gate(artifacts):
        result = real_evaluate(artifacts)
        if "FORCE_GATE_FAIL" in artifacts.markdown:
            return QualityGateResult(GateState.FAIL, (), ("forced failure",))
        return result

    monkeypatch.setattr("pipeline_juridico.ingest_orchestrator.evaluate", gate)
    bundle_before = _tree_snapshot(config.bundle_root)
    retrieval_before = _tree_snapshot(retrieval)

    first = run_ingest(config)
    first_candidates = {
        path.name: path.read_bytes() for path in config.candidates_dir.glob("*.md")
    }
    second = run_ingest(config)
    second_candidates = {
        path.name: path.read_bytes() for path in config.candidates_dir.glob("*.md")
    }

    expected_statuses = {"READY_TO_PUBLISH", "REVIEW_REQUIRED", "BLOCKED", "ERROR"}
    assert {item.status for item in first.files} == expected_statuses
    assert {item.status for item in second.files} == expected_statuses
    assert first_candidates and second_candidates == first_candidates
    assert _tree_snapshot(config.bundle_root) == bundle_before
    assert _tree_snapshot(retrieval) == retrieval_before


def test_existing_materially_different_concept_requires_review_without_bundle_write(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    root = tmp_path / "leis"
    root.mkdir()
    source = root / "LEG_conflict.pdf"
    _pdf(source, "LEI Nº 10.406, DE 10 DE JANEIRO DE 2002")
    config = _config(tmp_path, root)
    monkeypatch.setattr(
        "pipeline_juridico.legal_producer.LegalSemanticReviewEngine.review",
        lambda *_: _review(_legislation_fields()),
    )
    initial = run_ingest(config).files[0]
    state = json.loads(Path(initial.candidates[0]["record_path"]).read_text())
    concept_path = Path(state["concept_path"])
    generated = Path(initial.candidates[0]["candidate_path"]).read_text()
    concept_path.parent.mkdir(parents=True, exist_ok=True)
    # This is a pre-existing bundle fixture, written directly by the test.
    concept_path.write_text(generated + "\nConteúdo material preexistente e divergente.\n")
    before = _tree_snapshot(config.bundle_root)

    item = run_ingest(config).files[0]

    assert (item.status, item.reason) == ("REVIEW_REQUIRED", "existing_concept_conflict")
    assert _tree_snapshot(config.bundle_root) == before
