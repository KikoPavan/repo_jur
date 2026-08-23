"""Operational read-only CLI surface for Legal Knowledge retrieval."""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

from .config import RetrievalConfig
from .retrieval.index import SqliteFts5Index, enumerate_concepts
from .retrieval.search import FilterConfigurationError, search, search_diagnose

DEFAULT_BUNDLE_ROOT = Path("bundle")
DEFAULT_STATE_DIR = "var/retrieval"
STATE_DIR_ENV = "RETRIEVAL_STATE_DIR"

EXIT_OK = 0
EXIT_INPUT = 1
EXIT_UNEXPECTED = 2
EXIT_CONFIG = 3
EXIT_BLOCKED = 5


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bundle-root", default=str(DEFAULT_BUNDLE_ROOT), metavar="DIR")
    parser.add_argument("--state-dir", metavar="DIR")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    parser.add_argument("--json", action="store_true")


def build_retrieval_parsers(subparsers: argparse._SubParsersAction) -> None:
    retrieval = subparsers.add_parser("retrieval", help="Sincroniza o índice jurídico derivado.")
    children = retrieval.add_subparsers(dest="retrieval_command", required=True)
    for command in ("sync", "rebuild"):
        child = children.add_parser(command)
        _common(child)
    for command in ("search", "search-diagnose"):
        child = subparsers.add_parser(command, help="Pesquisa o bundle jurídico canônico.")
        child.add_argument("query")
        child.add_argument("--filter", action="append", default=[], metavar="KEY=VALUE")
        child.add_argument("--limit", type=int)
        _common(child)


def _config(args: argparse.Namespace) -> RetrievalConfig:
    raw = args.state_dir or os.environ.get(STATE_DIR_ENV, DEFAULT_STATE_DIR)
    return RetrievalConfig(derived_root=Path(raw))


def _filters(values: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in values:
        if "=" not in item:
            raise FilterConfigurationError("retrieval filter must use KEY=VALUE")
        key, raw = item.split("=", 1)
        if not key:
            raise FilterConfigurationError("retrieval filter key is required")
        try:
            result[key] = json.loads(raw)
        except json.JSONDecodeError:
            result[key] = raw
    return result


def _emit(payload: dict[str, Any], json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    if "results" in payload:
        for item in payload["results"]:
            print(f"concept_id: {item['concept_id']}")
            print(item["text_content"])
    else:
        print(f"state: {payload.get('state', 'ok')}")


def run(args: argparse.Namespace, logger: logging.Logger) -> int:
    bundle_root = Path(args.bundle_root).resolve()
    if not bundle_root.is_dir():
        logger.error("Bundle canônico não encontrado ou inválido: %s", bundle_root)
        return EXIT_INPUT
    try:
        config = _config(args)
        if config.derived_root == bundle_root or config.derived_root.is_relative_to(bundle_root):
            raise ValueError("retrieval derived root must remain outside bundle/")
        if args.command == "retrieval":
            backend = SqliteFts5Index(bundle_root, config)
            concepts = enumerate_concepts(bundle_root)
            result = backend.sync(concepts, config) if args.retrieval_command == "sync" else backend.rebuild(concepts, config)
            _emit({"operation": args.retrieval_command, "state": result.state.status, "operations": list(result.operations)}, args.json)
            return EXIT_OK
        filters = _filters(args.filter)
        if args.command == "search-diagnose":
            diagnosis = search_diagnose(bundle_root, config.derived_root, args.query, filters, args.limit, config=config)
            _emit(
                {
                    "results": list(diagnosis.outcome.results),
                    "candidate_discovery": diagnosis.candidate_discovery,
                    "filter_application": diagnosis.filter_application,
                    "materialization": diagnosis.materialization,
                    "fallback": diagnosis.fallback,
                    "reranking": diagnosis.reranking,
                },
                args.json,
            )
        else:
            outcome = search(bundle_root, config.derived_root, args.query, filters, args.limit, config=config)
            _emit({"results": list(outcome.results), "degraded": outcome.degraded, "reason": outcome.reason, "reranking": outcome.rerank_state}, args.json)
        return EXIT_OK
    except (ValueError, FilterConfigurationError) as exc:
        logger.error("Erro de configuração de retrieval: %s", exc)
        return EXIT_CONFIG
    except OSError as exc:
        logger.error("Falha operacional de retrieval: %s", type(exc).__name__)
        return EXIT_UNEXPECTED
    except Exception as exc:
        logger.error("Falha inesperada de retrieval: %s", type(exc).__name__)
        return EXIT_UNEXPECTED
