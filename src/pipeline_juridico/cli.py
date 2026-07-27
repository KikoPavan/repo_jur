import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

from .config import RoutingConfig
from .converter import convert_document
from .report import build_report_json
from .validator import write_atomic


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

    output_dir = os.environ.get("OUTPUT_DIR", "output")
    logs_dir = os.environ.get("LOGS_DIR", "logs")
    temp_root = os.environ.get("TEMP_DIR", "var/tmp")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    gemini_model = os.environ.get("GEMINI_MODEL")
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
        ocr_prompt_path=ocr_prompt_file,
        routing_config=routing_config,
        keep_temp=args.keep_temp,
    )
    report_json = build_report_json(relatorio)

    write_atomic(
        markdown,
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
