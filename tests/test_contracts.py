from pathlib import Path

import pytest

from pipeline_juridico.contracts import (
    CriticalValidationResult,
    CriticalValidationStatus,
    GateState,
    RouteTarget,
    guard_legal_bundle_write,
    parse_actor,
    resolve_safe_path,
    validate_actor,
)


@pytest.mark.parametrize(
    ("raw", "kind", "identifier", "version"),
    [
        ("human:operator-1", "human", "operator-1", None),
        ("process:ingress_worker", "process", "ingress_worker", None),
        ("collector-service/1.2.0", "producer", "collector-service", "1.2.0"),
        # No invented character whitelist: accents and symbols are valid
        # identifier characters under the structural Actor convention.
        ("human:operador-ção", "human", "operador-ção", None),
        ("process:coletor@2", "process", "coletor@2", None),
        ("Ministério-Público/1.0", "producer", "Ministério-Público", "1.0"),
    ],
)
def test_actor_valid_forms(raw, kind, identifier, version):
    actor = validate_actor(raw)

    assert actor == parse_actor(raw)
    assert actor.value == raw
    assert actor.kind == kind
    assert actor.identifier == identifier
    assert actor.version == version


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "human:",
        "process:",
        "robot:worker",
        "collector",
        "/1.0",
        "collector/",
        "collector/1.0/extra",
        "human:operator/1.0",
        "human operator",
    ],
)
def test_actor_invalid_forms(raw):
    with pytest.raises(ValueError, match="Actor"):
        validate_actor(raw)


def test_safe_path_accepts_relative_within_root(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()

    assert resolve_safe_path(root, "evidence/document.pdf") == (
        root / "evidence/document.pdf"
    ).resolve()


@pytest.mark.parametrize("reference", ["/absolute/document.pdf", "../escape.pdf", "a/../b.pdf"])
def test_safe_path_rejects_traversal_and_absolute(tmp_path, reference):
    with pytest.raises(ValueError, match="safe relative path"):
        resolve_safe_path(tmp_path, reference)


def test_safe_path_rejects_symlink_escape(tmp_path):
    root = tmp_path / "allowed"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="allowed root"):
        resolve_safe_path(root, "linked/document.pdf")


def test_gate_state_values():
    assert [state.value for state in GateState] == [
        "PASS",
        "PASS_WITH_WARNINGS",
        "FAIL",
    ]


def test_critical_validation_result_shape():
    first = CriticalValidationResult(status=CriticalValidationStatus.OK)
    second = CriticalValidationResult(status=CriticalValidationStatus.WARNING)

    assert first.findings == []
    assert second.findings == []
    assert first.findings is not second.findings


def test_critical_validation_result_status_values():
    assert [status.value for status in CriticalValidationStatus] == [
        "OK",
        "WARNING",
        "REVIEW_REQUIRED",
    ]


def test_route_target_values():
    assert [target.value for target in RouteTarget] == [
        "legal_knowledge",
        "judicial_process",
        "review_required",
    ]


@pytest.mark.parametrize(
    "domain",
    [RouteTarget.JUDICIAL_PROCESS, RouteTarget.REVIEW_REQUIRED],
)
def test_zero_write_guard_rejects_non_legal_domains_into_legal_bundle(tmp_path, domain):
    bundle = tmp_path / "repo_jur" / "bundle"

    with pytest.raises(PermissionError, match="legal_knowledge"):
        guard_legal_bundle_write(
            acting_domain=domain,
            target=bundle / "document.md",
            legal_bundle_root=bundle,
        )


def test_zero_write_guard_allows_non_legal_domain_outside_legal_bundle(tmp_path):
    outside = tmp_path / "process-storage" / "document.md"

    assert guard_legal_bundle_write(
        acting_domain=RouteTarget.JUDICIAL_PROCESS,
        target=outside,
        legal_bundle_root=tmp_path / "repo_jur" / "bundle",
    ) == outside.resolve()


def test_zero_write_guard_allows_legal_into_legal_bundle(tmp_path):
    bundle = tmp_path / "repo_jur" / "bundle"
    target = bundle / "document.md"

    assert guard_legal_bundle_write(
        acting_domain=RouteTarget.LEGAL_KNOWLEDGE,
        target=target,
        legal_bundle_root=bundle,
    ) == target.resolve()


def test_contracts_module_has_no_legal_or_process_schema_import():
    source = (
        Path(__file__).parents[1] / "src/pipeline_juridico/contracts.py"
    ).read_text(encoding="utf-8")

    assert "legal_schema" not in source.lower()
    assert "process_schema" not in source.lower()
    assert "okf" not in source.lower()
