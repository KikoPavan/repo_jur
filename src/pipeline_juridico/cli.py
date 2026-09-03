import argparse
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .cleaner import UnauthorizedIllegibleMarkerError
from .config import RoutingConfig
from .contracts import Phase1Artifacts
from .converter import convert_document
from .engines import OcrConfigurationError
from .inspector import PdfInspectionError
from .quality_gate import evaluate
from .report import (
    ReportContractError,
    attach_gate_result,
    build_candidate_report_json,
    build_report_json,
    strip_technical_routing_metadata,
    validate_report_contract,
)
from .validator import (
    MarkdownValidationError,
    OutputAlreadyExistsError,
    write_atomic,
)

GEMINI_OPENAI_BASE_URL = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
)


def _sanitize_log_message(
    message: str,
    secrets: list[str],
    max_length: int = 500,
) -> str:
    for secret in secrets:
        if secret:
            message = message.replace(secret, "***REDACTED***")

    if len(message) > max_length:
        message = (
            message[:max_length]
            + " ... [mensagem truncada por segurança]"
        )

    return message


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Converte um PDF jurídico em Markdown e gera seu relatório."
    )
    parser.add_argument(
        "pdf_path",
        help="Caminho do PDF a converter.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Permite substituir arquivos de saída existentes.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="Permite publicar páginas com texto ilegível.",
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Desabilita chamadas de OCR.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Preserva arquivos temporários para diagnóstico.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Nível do log técnico.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level)
    logger = logging.getLogger(__name__)
    known_secrets: list[str] = []

    try:
        output_dir = os.environ.get("OUTPUT_DIR", "output")
        logs_dir = os.environ.get("LOGS_DIR", "logs")
        temp_root = os.environ.get("TEMP_DIR", "var/tmp")
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        known_secrets = [gemini_api_key] if gemini_api_key else []
        gemini_model = os.environ.get("GEMINI_MODEL")
        gemini_base_url = os.environ.get(
            "GEMINI_BASE_URL",
            GEMINI_OPENAI_BASE_URL,
        )
        ocr_prompt_file = os.environ.get(
            "OCR_PROMPT_FILE",
            "prompts/ocr_literal_ptbr.txt",
        )
        ocr_enabled_from_env = (
            os.environ.get("OCR_ENABLED", "true").lower() == "true"
        )

        pdf_path = Path(args.pdf_path)
        output_path = Path(output_dir) / f"{pdf_path.stem}.md"
        report_path = Path(logs_dir) / f"{pdf_path.stem}.report.json"
        routing_config = RoutingConfig.from_env()
        use_ocr_final = (not args.no_ocr) and ocr_enabled_from_env

        markdown, relatorio = convert_document(
            pdf_path=pdf_path,
            output_path=output_path,
            temp_root=temp_root,
            allow_partial=args.allow_partial,
            use_ocr=use_ocr_final,
            ocr_api_key=gemini_api_key,
            ocr_model=gemini_model,
            ocr_base_url=gemini_base_url,
            ocr_prompt_path=ocr_prompt_file,
            routing_config=routing_config,
            keep_temp=args.keep_temp,
        )
        literal = strip_technical_routing_metadata(markdown)
        candidate_json = build_candidate_report_json(relatorio)
        gate_result = evaluate(
            Phase1Artifacts(markdown=literal, report_json=candidate_json)
        )
        final = attach_gate_result(
            relatorio,
            quality_gate=gate_result.state.value,
            warnings=gate_result.warnings,
            errors=gate_result.errors,
        )
        report_json = build_report_json(final)
        validate_report_contract(json.loads(report_json))

        write_atomic(
            literal,
            output_path,
            temp_root,
            overwrite=args.overwrite,
        )
        write_atomic(
            report_json,
            report_path,
            temp_root,
            overwrite=args.overwrite,
        )
    except (PdfInspectionError, OcrConfigurationError) as exc:
        logger.error(
            "Falha de entrada ou configuração: %s",
            _sanitize_log_message(str(exc), known_secrets),
        )
        return 1
    except OutputAlreadyExistsError as exc:
        logger.error(
            "Conflito de saída existente: %s",
            _sanitize_log_message(str(exc), known_secrets),
        )
        return 4
    except (
        MarkdownValidationError,
        UnauthorizedIllegibleMarkerError,
        ReportContractError,
    ) as exc:
        logger.error(
            "Falha de validação: %s",
            _sanitize_log_message(str(exc), known_secrets),
        )
        return 3
    except Exception as exc:
        logger.error(
            "Falha de conversão ou OCR: %s",
            _sanitize_log_message(str(exc), known_secrets),
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
