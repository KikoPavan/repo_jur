import json
from dataclasses import asdict

from .models import Relatorio


def build_report_json(relatorio: Relatorio) -> str:
    return json.dumps(asdict(relatorio), ensure_ascii=False, indent=2)
