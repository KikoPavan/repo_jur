"""Operational route command for the Stage 6 Domain Router."""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
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
from .report import ReportContractError, validate_report_contract
from .validator import write_atomic

DEFAULT_STATE_DIR = "var/routing/state"
STATE_DIR_ENV = "ROUTING_STATE_DIR"

EXIT_OK = 0
EXIT_INPUT = 1
EXIT_UNEXPECTED = 2
EXIT_CONFIG = 3
EXIT_BLOCKED = 5


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="repo-jur",
        description="Comandos operacionais do pipeline jurídico.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    from .legal_producer_cli import build_producer_parser
    build_producer_parser(subparsers)
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
    return parser


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
    logging.basicConfig(level=args.log_level)
    logger = logging.getLogger(__name__)
    if args.command == "route":
        return _run_route(args, logger)
    if args.command == "producer":
        from .legal_producer_cli import run
        return run(args, logger)
    return EXIT_UNEXPECTED


if __name__ == "__main__":
    raise SystemExit(main())
