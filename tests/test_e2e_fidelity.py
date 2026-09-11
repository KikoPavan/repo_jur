"""E2E/Integration tests for Fidelity Audit validation."""

import json
import pytest
from pipeline_juridico.quality_gate import evaluate
from pipeline_juridico.contracts import Phase1Artifacts, GateState


def test_quality_gate_fails_missing_fidelity_audit():
    report = {
        "schema_version": "1.0",
        "execution_id": "test-uuid",
        "input": {"sha256": "a" * 64, "byte_size": 100, "page_count": 1},
        "phase1": {
            "implementation": "test",
            "implementation_version": "1.0",
            "logical_processing_version": "1",
            "relevant_config_fingerprint": "f" * 64
        },
        "result": {"quality_gate": "PASS", "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": "m" * 64},
        "pages": [
            {
                "page_number": 1,
                "method": "ocr_integral",
                "char_count": 10,
                "warnings": [],
                "errors": [],
                "truncated": False
                # fidelity_audit is missing!
            }
        ],
        "telemetry": {}
    }
    
    artifacts = Phase1Artifacts(
        markdown="[[Pág. 1]]\nContent",
        report_json=json.dumps(report)
    )
    
    result = evaluate(artifacts)
    assert result.state == GateState.FAIL
    assert any("missing required fidelity_audit" in err for err in result.errors)


def test_quality_gate_warns_on_flagged_fidelity_issue():
    report = {
        "schema_version": "1.0",
        "execution_id": "test-uuid",
        "input": {"sha256": "a" * 64, "byte_size": 100, "page_count": 1},
        "phase1": {
            "implementation": "test",
            "implementation_version": "1.0",
            "logical_processing_version": "1",
            "relevant_config_fingerprint": "f" * 64
        },
        "result": {"quality_gate": "PASS", "warnings": [], "errors": []},
        "artifacts": {"markdown_sha256": "m" * 64},
        "pages": [
            {
                "page_number": 1,
                "method": "ocr_integral",
                "char_count": 10,
                "warnings": [],
                "errors": [],
                "truncated": False,
                "fidelity_audit": {
                    "issues": [
                        {
                            "issue_type": "duplication",
                            "detector": "test_detector",
                            "page_number": 1,
                            "resolution": "flagged"
                        }
                    ]
                }
            }
        ],
        "telemetry": {}
    }
    
    artifacts = Phase1Artifacts(
        markdown="[[Pág. 1]]\nContent",
        report_json=json.dumps(report)
    )
    
    result = evaluate(artifacts)
    assert result.state == GateState.PASS_WITH_WARNINGS
    assert any("Fidelity issue" in warn for warn in result.warnings)
