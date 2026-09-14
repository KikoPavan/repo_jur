"""Command-line adapter for legal-knowledge ingestion."""

import argparse
import json
import logging
from pathlib import Path

from .config import IngestConfig
from .ingest_orchestrator import run_ingest


def build_ingest_parser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "ingest", help="Prepara candidatos jurídicos sem publicá-los."
    )
    parser.add_argument(
        "--input-dir", default="input/leis_jurisprudencia", metavar="DIR"
    )
    parser.add_argument("--bundle-root", default="bundle", metavar="DIR")
    parser.add_argument(
        "--state-dir", default="var/producer/state", metavar="DIR"
    )
    parser.add_argument(
        "--candidates-dir", default="var/producer/candidates", metavar="DIR"
    )
    parser.add_argument(
        "--reports-dir", default="var/ingest/reports", metavar="DIR"
    )
    parser.add_argument(
        "--log-level", default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument("--json", action="store_true")


def run(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        config = IngestConfig(
            input_dir=Path(args.input_dir),
            bundle_root=Path(args.bundle_root),
            state_dir=Path(args.state_dir),
            candidates_dir=Path(args.candidates_dir),
            reports_dir=Path(args.reports_dir),
        )
        report = run_ingest(config)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        logger.error("Falha de entrada: %s", exc)
        return 1
    except (OSError, ValueError) as exc:
        logger.error("Falha ao preparar ingestão: %s", exc)
        return 2
    payload = report.to_dict()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False))
    else:
        for item in report.files:
            print(f"{item.filename}: {item.status}")
        print(f"summary: {report.summary}")
    return 0
