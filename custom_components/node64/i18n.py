import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl

_TRANSLATIONS: dict[str, str] = json.loads((Path(__file__).parent / "monitor64_de.json").read_text(encoding="utf-8"))

_PREFIX = "monitor64."
_TOKEN = re.compile(r"i18n:([a-z0-9_]+(?:\.[a-z0-9_]+)*)(?:\?([A-Za-z0-9%+=&_.~-]*))?")
_DECIMAL = re.compile(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])")
_MAX_DEPTH = 4


def _number(value: str) -> str:
    return _DECIMAL.sub(r"\1,\2", value)


def translate(text: str, depth: int = 0) -> str:
    if "i18n:" not in text:
        return text

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        params = {
            name: translate(value, depth + 1) if depth < _MAX_DEPTH else value
            for name, value in parse_qsl(match.group(2) or "", keep_blank_values=True)
        }
        short = key.removeprefix(_PREFIX)
        template = _TRANSLATIONS.get(short)
        if template is None:
            if not params:
                return short
            return f"{short} ({', '.join(f'{k}={_number(v)}' for k, v in params.items())})"
        for name, value in params.items():
            template = template.replace("{" + name + "}", _number(value))
        return template

    return _TOKEN.sub(replace, text)


def parse_detail(text: str | None) -> dict[str, Any]:
    if not text:
        return {}
    match = _TOKEN.search(text)
    if match is None or match.group(0) != text:
        return {}
    return {"detail_key": match.group(1), "params": dict(parse_qsl(match.group(2) or "", keep_blank_values=True))}
