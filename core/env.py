"""Small .env loader for local JARVIS configuration.

The project intentionally does not require python-dotenv just to read the
assistant's local secrets. Values already present in the process environment
win over .env unless override=True.
"""
from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"


def _clean_value(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""

    if value[0] in {"'", '"'} and value[-1:] == value[0]:
        value = value[1:-1]
    else:
        # Strip an inline comment only when it is separated by whitespace.
        for marker in (" #", "\t#"):
            if marker in value:
                value = value.split(marker, 1)[0].rstrip()
                break
    return value


def load_env(path: Path = ENV_PATH, override: bool = False) -> int:
    """Load KEY=VALUE pairs from .env and return the number loaded."""
    if not path.exists():
        return 0

    loaded = 0
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return 0

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = _clean_value(raw_value)
        if override or key not in os.environ:
            os.environ[key] = value
            loaded += 1

    return loaded


# Load the project's .env as soon as this module is imported.
load_env()
