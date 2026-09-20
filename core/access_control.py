"""Local access control for the J.A.R.V.I.S. desktop.

Password authentication is local and stored as a salted PBKDF2 hash.
Voice unlock is a convenience feature based on a spoken passphrase recognized
by the optional SpeechRecognition package; it is not biometric speaker
identification and should not be treated as high-assurance authentication.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "memory" / "access_control.json"
ITERATIONS = 240_000


def _load() -> dict:
    try:
        value = json.loads(FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _save(value: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2), encoding="utf-8")
    tmp.replace(FILE)


def normalize_phrase(value: str) -> str:
    value = str(value or "").strip().lower()
    value = re.sub(r"[^a-z0-9\s]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _hash(value: str, salt: bytes | None = None) -> tuple[str, str]:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", value.encode("utf-8"), salt, ITERATIONS
    )
    return (
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def _verify(value: str, salt_b64: str, digest_b64: str) -> bool:
    try:
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256", value.encode("utf-8"), salt, ITERATIONS
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def is_configured() -> bool:
    data = _load()
    return bool(data.get("password_hash") and data.get("password_salt"))


def has_voice_phrase() -> bool:
    data = _load()
    return bool(data.get("voice_hash") and data.get("voice_salt"))


def setup(password: str, voice_phrase: str = "") -> str:
    password = str(password or "")
    if len(password) < 6:
        return "Password must be at least 6 characters."
    salt, digest = _hash(password)
    data = _load()
    data["password_salt"] = salt
    data["password_hash"] = digest
    phrase = normalize_phrase(voice_phrase)
    if phrase:
        vsalt, vhash = _hash(phrase)
        data["voice_salt"] = vsalt
        data["voice_hash"] = vhash
    else:
        data.pop("voice_salt", None)
        data.pop("voice_hash", None)
    data["version"] = 1
    _save(data)
    return "J.A.R.V.I.S. access protection configured."


def verify_password(password: str) -> bool:
    data = _load()
    return _verify(
        str(password or ""),
        str(data.get("password_salt") or ""),
        str(data.get("password_hash") or ""),
    )


def verify_voice_phrase(phrase: str) -> bool:
    data = _load()
    normalized = normalize_phrase(phrase)
    if not normalized:
        return False
    return _verify(
        normalized,
        str(data.get("voice_salt") or ""),
        str(data.get("voice_hash") or ""),
    )


def access_summary() -> dict:
    return {
        "configured": is_configured(),
        "voice_unlock": has_voice_phrase(),
        "password_unlock": is_configured(),
    }
