"""Operational route command for the Stage 6 Domain Router."""

from __future__ import annotations

import argparse
import ast
import datetime
import importlib.util
import json
import logging
import os
import subprocess
import sys
from importlib.metadata import distributions
from pathlib import Path

from .config import ensure_outside_canonical_bundle
from .contracts import CriticalValidationStatus, Phase1Artifacts, RouteTarget
from .domain_router import (
    RoutingBlockedError,
    RoutingConfigurationError,
    RoutingContext,
    RoutingDecision,
    build_routing_record,
    route,
    routing_state_filename,
    validate_routing_context,
)
from .config import ensure_outside_canonical_bundle
from .report import ReportContractError, validate_report_contract
from .validator import write_atomic

DEFAULT_STATE_DIR = "var/routing/state"
STATE_DIR_ENV = "ROUTING_STATE_DIR"

EXIT_OK = 0
EXIT_INPUT = 1
EXIT_UNEXPECTED = 2
EXIT_CONFIG = 3
EXIT_BLOCKED = 5

CONFORMANCE_REPORT_DEFAULT = "var/conformance/report.json"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_SOURCE = PROJECT_ROOT / "src/pipeline_juridico/contracts.py"
REAL_CORPUS_FILENAMES = (
    "AINTARESP_1462304-PA.pdf",
    "REsp_1704551-SP.pdf",
    "Inf0024E.pdf",
    "L10.406_CC_2002.pdf",
)
PROHIBITED_CONTRACT_IMPORTS = (
    "pipeline_juridico.retrieval",
)
PROHIBITED_VECTOR_PACKAGES = (
    "faiss",
    "faiss-cpu",
    "faiss-gpu",
    "chromadb",
    "sentence-transformers",
    "sentence_transformers",
    "qdrant-client",
    "qdrant_client",
    "pinecone",
    "pinecone-client",
    "weaviate",
    "weaviate-client",
    "milvus",
    "milvus-lite",
    "pymilvus",
    "lancedb",
    "pgvector",
    "annoy",
    "hnswlib",
    "flagembedding",
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-jur",
        description="Comandos operacionais do pipeline jurídico.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    from .legal_producer_cli import build_producer_parser
    build_producer_parser(subparsers)
    from .process_producer_cli import build_process_parser
    build_process_parser(subparsers)
    from .retrieval_cli import build_retrieval_parsers
    build_retrieval_parsers(subparsers)
    test_parser = subparsers.add_parser(
        "test",
        help="Executa verificações operacionais locais.",
    )
    test_actions = test_parser.add_subparsers(
        dest="test_action", required=True
    )
    conformance_parser = test_actions.add_parser(
        "conformance",
        help="Executa as suítes de conformidade e regressão.",
    )
    conformance_parser.add_argument(
        "--json-report",
        default=CONFORMANCE_REPORT_DEFAULT,
        metavar="PATH",
        help=f"Relatório JSON derivado (padrão: {CONFORMANCE_REPORT_DEFAULT}).",
    )
    conformance_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Exibe a saída dos processos pytest durante a execução.",
    )
    route_parser = subparsers.add_parser(
        "route",
        help="Roteia artefatos da Fase 1 para o domínio de destino.",
    )
    route_parser.add_argument(
        "markdown",
        help="Caminho do Markdown literal da Fase 1.",
    )
    route_parser.add_argument(
        "report",
        help="Caminho do relatório técnico da Fase 1.",
    )
    route_parser.add_argument(
        "--domain",
        metavar="legal_knowledge|judicial_process",
        help=(
            "Domínio solicitado explicitamente pelo operador; mapeado para o "
            "sinal aprovado requested_domain."
        ),
    )
    route_parser.add_argument(
        "--context",
        metavar="CONTEXT_JSON",
        help="Arquivo JSON com o contexto de roteamento validado.",
    )
    route_parser.add_argument(
        "--state-dir",
        metavar="DIR",
        help=(
            f"Diretório operacional do registro (padrão: {DEFAULT_STATE_DIR}; "
            f"variável de ambiente: {STATE_DIR_ENV})."
        ),
    )
    route_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nível do log técnico.",
    )
    route_parser.add_argument(
        "--json",
        action="store_true",
        help="Emite a saída do comando em JSON legível por máquina.",
    )
    ingress_parser = subparsers.add_parser(
        "ingress",
        help="Executa o preflight e preservação de um envelope ITP.",
    )
    ingress_parser.add_argument(
        "envelope",
        help="Caminho do envelope ITP (ZIP) a ser processado.",
    )
    ingress_parser.add_argument(
        "--json",
        action="store_true",
        help="Emite a saída do preflight em JSON operacional.",
    )
    ingress_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nível do log técnico.",
    )
    return parser


def validate_contract_imports(source_path: Path | None = None) -> list[str]:
    """Return prohibited domain-specific imports found in the common contracts."""
    path = source_path or CONTRACTS_SOURCE
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        return [f"could not inspect {path}: {exc}"]

    imported_modules: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = f"pipeline_juridico.{base}".rstrip(".")
            if base == "pipeline_juridico":
                imported_modules.extend(
                    (node.lineno, f"{base}.{alias.name}") for alias in node.names
                )
            elif base:
                imported_modules.append((node.lineno, base))

    def prohibited_import(module: str) -> bool:
        if any(
            module == prohibited or module.startswith(f"{prohibited}.")
            for prohibited in PROHIBITED_CONTRACT_IMPORTS
        ):
            return True
        relative_name = module.removeprefix("pipeline_juridico.")
        return relative_name.startswith(("legal_", "process_"))

    return [
        f"{path}:{line}: prohibited import {module}"
        for line, module in imported_modules
        if prohibited_import(module)
    ]


def _normalized_package_name(name: str) -> str:
    return name.strip().lower().replace("_", "-").replace(".", "-")


def validate_no_vector_infrastructure(
    *,
    installed_distributions: set[str] | None = None,
    loaded_modules: set[str] | None = None,
) -> list[str]:
    """Return installed or loaded vector/embedding infrastructure violations."""
    if installed_distributions is None:
        installed_distributions = {
            distribution.metadata.get("Name", "") for distribution in distributions()
        }
    if loaded_modules is None:
        loaded_modules = set(sys.modules)

    prohibited = {_normalized_package_name(name) for name in PROHIBITED_VECTOR_PACKAGES}
    violations: list[str] = []
    for name in sorted(installed_distributions):
        if _normalized_package_name(name) in prohibited:
            violations.append(f"prohibited distribution installed: {name}")
    for name in sorted(loaded_modules):
        root_name = name.split(".", 1)[0]
        if _normalized_package_name(root_name) in prohibited:
            violations.append(f"prohibited module loaded: {name}")
    return violations


def _configuration_errors() -> list[str]:
    errors: list[str] = []
    if importlib.util.find_spec("pytest") is None:
        errors.append("pytest is not installed in the active Python environment")
    input_root = PROJECT_ROOT / "input"
    missing = [name for name in REAL_CORPUS_FILENAMES if not (input_root / name).is_file()]
    if missing:
        errors.append(
            f"missing PDF fixtures under {input_root}: {', '.join(missing)}"
        )
    return errors


def _write_conformance_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _run_conformance(args: argparse.Namespace, logger: logging.Logger) -> int:
    failures: list[dict[str, str]] = []
    runs: list[dict[str, object]] = []

    for detail in _configuration_errors():
        failures.append(
            {"category": "ENVIRONMENT_CONFIGURATION_ERROR", "detail": detail}
        )

    if not failures:
        for detail in validate_contract_imports():
            failures.append({"category": "CONFORMANCE_FAILURE", "detail": detail})
        for detail in validate_no_vector_infrastructure():
            failures.append({"category": "CONFORMANCE_FAILURE", "detail": detail})

    if not any(
        failure["category"] == "ENVIRONMENT_CONFIGURATION_ERROR"
        for failure in failures
    ):
        for marker, failure_category in (
            ("conformance", "CONFORMANCE_FAILURE"),
            ("regression", "REGRESSION_FAILURE"),
        ):
            command = [
                sys.executable,
                "-m",
                "pytest",
                "-m",
                marker,
                "tests/test_conformance/",
            ]
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    text=True,
                    capture_output=not args.verbose,
                )
            except OSError as exc:
                failures.append(
                    {
                        "category": "ENVIRONMENT_CONFIGURATION_ERROR",
                        "detail": f"could not execute {marker} pytest run: {exc}",
                    }
                )
                break
            runs.append(
                {
                    "marker": marker,
                    "command": command,
                    "return_code": completed.returncode,
                    "stdout": completed.stdout,
                    "stderr": completed.stderr,
                }
            )
            if completed.returncode == 1:
                failures.append(
                    {
                        "category": failure_category,
                        "detail": f"{marker} pytest run failed",
                    }
                )
            elif completed.returncode != 0:
                failures.append(
                    {
                        "category": "ENVIRONMENT_CONFIGURATION_ERROR",
                        "detail": (
                            f"{marker} pytest run exited with configuration/operational "
                            f"code {completed.returncode}"
                        ),
                    }
                )

    if any(
        failure["category"] == "ENVIRONMENT_CONFIGURATION_ERROR"
        for failure in failures
    ):
        exit_code = 2
    elif failures:
        exit_code = 1
    else:
        exit_code = 0

    report: dict[str, object] = {
        "schema_version": "1.0",
        "status": "PASS" if exit_code == 0 else "FAIL",
        "exit_code": exit_code,
        "runs": runs,
        "failures": failures,
    }
    try:
        _write_conformance_report(Path(args.json_report), report)
    except (OSError, UnicodeError) as exc:
        logger.error("Falha ao escrever relatório de conformidade: %s", exc)
        return 2
    return exit_code


def _resolve_state_dir(override: str | None) -> Path:
    raw = override or os.environ.get(STATE_DIR_ENV, DEFAULT_STATE_DIR)
    return ensure_outside_canonical_bundle(raw)


def _effective_routing_context(
    args: argparse.Namespace,
) -> RoutingContext:
    context = RoutingContext()
    if args.context is not None:
        try:
            loaded: object = json.loads(
                Path(args.context).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise RoutingConfigurationError(
                f"contexto de roteamento ilegível: {exc}"
            ) from exc
        if not isinstance(loaded, dict):
            raise RoutingConfigurationError(
                "o contexto de roteamento deve ser um objeto JSON"
            )
        context = validate_routing_context(loaded)
    if args.domain is not None:
        if args.domain not in (
            RouteTarget.LEGAL_KNOWLEDGE.value,
            RouteTarget.JUDICIAL_PROCESS.value,
        ):
            raise RoutingConfigurationError(
                "valor inválido para --domain"
            )
        if (
            context.requested_domain is not None
            and context.requested_domain.value != args.domain
        ):
            raise RoutingConfigurationError(
                "--domain e --context discordam sobre requested_domain"
            )
        return RoutingContext(requested_domain=RouteTarget(args.domain))
    return context


def _print_decision(
    decision: RoutingDecision,
    record_path: Path,
    json_output: bool,
) -> None:
    if json_output:
        print(
            json.dumps(
                {
                    "decision": decision.target.value,
                    "reason": decision.reason.value,
                    "record_path": str(record_path),
                },
                ensure_ascii=False,
            )
        )
        return
    print(f"decision: {decision.target.value}")
    print(f"reason: {decision.reason.value}")
    print(f"record: {record_path}")


def _print_blocked(error: RoutingBlockedError, json_output: bool) -> None:
    if json_output:
        print(json.dumps({"blocked_reason": str(error)}, ensure_ascii=False))
        return
    print(f"blocked: {error}")


def _run_route(args: argparse.Namespace, logger: logging.Logger) -> int:
    try:
        state_dir = _resolve_state_dir(args.state_dir)
    except ValueError as exc:
        logger.error("Diretório de estado inválido: %s", exc)
        return EXIT_CONFIG

    markdown_path = Path(args.markdown)
    report_path = Path(args.report)
    if not markdown_path.is_file():
        logger.error(
            "Arquivo de Markdown da Fase 1 não encontrado: %s",
            markdown_path,
        )
        return EXIT_INPUT
    if not report_path.is_file():
        logger.error(
            "Relatório técnico da Fase 1 não encontrado: %s",
            report_path,
        )
        return EXIT_INPUT
    try:
        markdown = markdown_path.read_text(encoding="utf-8")
        report_json = report_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        logger.error("Falha de entrada ao ler os artefatos: %s", exc)
        return EXIT_INPUT

    try:
        parsed_report: object = json.loads(report_json)
        if not isinstance(parsed_report, dict):
            raise ReportContractError("O relatório técnico deve ser um objeto JSON")
        validate_report_contract(parsed_report)
    except (json.JSONDecodeError, ReportContractError) as exc:
        logger.error("Superfície do relatório técnico inválida: %s", exc)
        return EXIT_CONFIG

    try:
        routing_context = _effective_routing_context(args)
    except RoutingConfigurationError as exc:
        logger.error("Erro de configuração de roteamento: %s", exc)
        return EXIT_CONFIG

    phase1 = Phase1Artifacts(markdown=markdown, report_json=report_json)
    try:
        decision = route(
            phase1,
            critical_status=CriticalValidationStatus.OK,
            routing_context=routing_context,
        )
    except RoutingBlockedError as exc:
        if exc.reason == "fail_gate":
            logger.error("Roteamento bloqueado: %s", exc)
            _print_blocked(exc, args.json)
            return EXIT_BLOCKED
        logger.error("Superfície do relatório técnico inválida: %s", exc)
        return EXIT_CONFIG
    except RoutingConfigurationError as exc:
        logger.error("Erro de configuração de roteamento: %s", exc)
        return EXIT_CONFIG
    except Exception as exc:
        logger.error("Falha inesperada ao rotear: %s", exc)
        return EXIT_UNEXPECTED

    try:
        record = build_routing_record(
            phase1_artifacts=phase1,
            critical_status=CriticalValidationStatus.OK,
            routing_context=routing_context,
            decision=decision,
            recorded_at=datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        )
        record_json = json.dumps(record, ensure_ascii=False, indent=2)
        destination = state_dir / routing_state_filename(phase1)
        artifact_paths = {markdown_path.resolve(), report_path.resolve()}
        if destination.resolve() in artifact_paths:
            raise RoutingConfigurationError(
                "o registro de roteamento não pode substituir um artefato da Fase 1"
            )
        write_atomic(record_json, destination, state_dir, overwrite=True)
    except (RoutingBlockedError, RoutingConfigurationError) as exc:
        logger.error("Registro de roteamento não pode ser escrito: %s", exc)
        return EXIT_CONFIG
    except OSError as exc:
        logger.error("Falha operacional ao persistir o registro: %s", exc)
        return EXIT_UNEXPECTED
    except Exception as exc:
        logger.error("Falha inesperada ao persistir o registro: %s", exc)
        return EXIT_UNEXPECTED

    _print_decision(decision, destination, args.json)
    return EXIT_OK


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=getattr(args, "log_level", "INFO"))
    logger = logging.getLogger(__name__)
    if args.command == "test" and args.test_action == "conformance":
        return _run_conformance(args, logger)
    if args.command == "ingress":
        from .ingress_cli import run_ingress
        return run_ingress(args, logger)
    if args.command == "route":
        return _run_route(args, logger)
    if args.command == "producer":
        from .legal_producer_cli import run
        return run(args, logger)
    if args.command == "process":
        from .process_producer_cli import run
        return run(args, logger)
    if args.command in {"retrieval", "search", "search-diagnose"}:
        from .retrieval_cli import run
        return run(args, logger)
    return EXIT_UNEXPECTED


if __name__ == "__main__":
    raise SystemExit(main())
