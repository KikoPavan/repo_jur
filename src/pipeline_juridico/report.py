import json
from dataclasses import asdict
from pathlib import Path

from .hashing import get_runtime_info, sha256_file
from .models import OcrInfo, Relatorio, RuntimeInfo


def build_runtime_info() -> RuntimeInfo:
    return get_runtime_info()


def build_ocr_info(
    enabled: bool,
    provider: str,
    model: str,
    prompt_path: str | Path,
) -> OcrInfo:
    return OcrInfo(
        enabled=enabled,
        provider=provider,
        model=model,
        prompt_sha256=sha256_file(prompt_path),
    )


def build_report_json(relatorio: Relatorio) -> str:
    return json.dumps(asdict(relatorio), ensure_ascii=False, indent=2)
