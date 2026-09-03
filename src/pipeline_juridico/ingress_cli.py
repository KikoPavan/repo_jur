"""Operational ingress command for the Stage 6 Domain Router."""

from __future__ import annotations

import argparse
import json
import logging

from .config import IngressConfig, PreflightLimits
from .evidence import LocalFilesystemObjectStorageGateway
from .ingress import (
    ArchiveSecurityError,
    HandoffConflictError,
    IngressError,
    preflight_envelope,
)

EXIT_OK = 0
EXIT_INPUT = 1
EXIT_UNEXPECTED = 2


def run_ingress(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        config = IngressConfig.from_env()
        limits = PreflightLimits.from_env()
        storage = LocalFilesystemObjectStorageGateway(config.object_storage_root)

        result = preflight_envelope(
            envelope_path=args.envelope,
            config=config,
            limits=limits,
            storage=storage,
        )

        output = {
            "handoff_id": result.handoff_id,
            "official_evidence_sha256": result.official_evidence_sha256,
            "evidence_reference": result.evidence_reference,
            "reused": result.reused,
        }

        if args.json:
            print(json.dumps(output, ensure_ascii=False))
        else:
            print(f"Handoff ID: {result.handoff_id}")
            print(f"Official SHA-256: {result.official_evidence_sha256}")
            print(f"Evidence Reference: {result.evidence_reference}")
            if result.reused:
                print("Result reused from prior ingress.")

        return EXIT_OK
    except (ArchiveSecurityError, HandoffConflictError, IngressError) as exc:
        logger.error("Falha no preflight: %s", exc)
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return EXIT_INPUT
    except Exception as exc:
        logger.error("Falha inesperada no ingress: %s", exc)
        if args.json:
            print(json.dumps({"error": "Internal error"}, ensure_ascii=False))
        return EXIT_UNEXPECTED
