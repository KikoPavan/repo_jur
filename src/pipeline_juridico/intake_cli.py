import argparse
import logging
import os
import shutil
from pathlib import Path
from .config import IntakeConfig, IngressConfig
from .intake_manager import IntakeManager, IntakeState
from .intake_orchestrator import IntakeOrchestrator

def build_intake_parser(subparsers):
    intake = subparsers.add_parser("intake", help="Gerencia a fila de entrada operacional.")
    commands = intake.add_subparsers(dest="intake_command", required=True)

    add = commands.add_parser("add", help="Adiciona um PDF ao diretório de entrada de forma segura.")
    add.add_argument("pdf", help="Caminho do arquivo PDF.")
    add.add_argument("--type", required=True, choices=["legislacao", "jurisprudencia", "temas", "precedentes"], help="Tipo do documento.")

    scan = commands.add_parser("scan", help="Varre o diretório de entrada e processa novos arquivos.")

    status = commands.add_parser("status", help="Exibe o status da fila e do registro.")
    status.add_argument("--sha", help="Filtrar por SHA-256.")

    retry = commands.add_parser("retry", help="Reinicia o processamento de um arquivo que falhou.")
    retry.add_argument("sha", help="SHA-256 do arquivo.")

def run_intake(args, logger):
    intake_config = IntakeConfig.from_env()
    ingress_config = IngressConfig.from_env()

    if args.intake_command == "add":
        pdf_path = Path(args.pdf)
        if not pdf_path.is_file():
            logger.error(f"Arquivo não encontrado: {pdf_path}")
            return 1

        target_dir = intake_config.input_dir / args.type
        target_dir.mkdir(parents=True, exist_ok=True)

        target = target_dir / f"{pdf_path.name}.partial"
        shutil.copy2(pdf_path, target)
        final_target = target_dir / pdf_path.name
        os.replace(target, final_target)
        logger.info(f"Adicionado em {args.type}: {final_target}")
        return 0

    orchestrator = IntakeOrchestrator(intake_config, ingress_config, logger)

    if args.intake_command == "scan":
        orchestrator.scan_and_process()
        return 0

    if args.intake_command == "status":
        manager = IntakeManager(intake_config)
        if args.sha:
            entry = manager.load_entry(args.sha)
            if entry:
                print(entry.to_json())
            else:
                print(f"Registro não encontrado para SHA {args.sha}")
        else:
            for registry_file in sorted(intake_config.registry_dir.glob("*.json")):
                sha = registry_file.stem
                entry = manager.load_entry(sha)
                if entry:
                    print(f"{sha}: {entry.state} (Type: {entry.okf_type})")
        return 0

    if args.intake_command == "retry":
        manager = IntakeManager(intake_config)
        entry = manager.load_entry(args.sha)
        if not entry:
            logger.error(f"Registro não encontrado: {args.sha}")
            return 1

        if entry.state != IntakeState.FAILED:
            logger.error(f"Apenas registros em FAILED podem ser reiniciados. Estado atual: {entry.state}")
            return 1

        failed_pdf = intake_config.failed_dir / f"{args.sha}.pdf"
        if not failed_pdf.exists():
            logger.error(f"Arquivo PDF não encontrado em failed/: {failed_pdf}")
            return 1

        # Move back to input subfolder based on okf_type
        # If okf_type was legislacao, map back to legislacao/
        inv_map = {v.value: k for k, v in manager.TYPE_MAPPING.items()}
        subdir = inv_map.get(entry.okf_type.value) if entry.okf_type else "jurisprudencia"

        target_dir = intake_config.input_dir / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(failed_pdf), str(target_dir / f"{args.sha}.pdf"))

        logger.info(f"Arquivo {args.sha}.pdf movido de volta para entrada/{subdir}.")
        return 0

    return 1
