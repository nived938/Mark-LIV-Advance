"""Persistent call automation rules and recent call history.

The rule engine is deterministic and runs locally, so time-window call actions
do not depend on Gemini being available.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "memory" / "call_rules.json"
HISTORY = ROOT / "memory" / "call_history.json"
_LOCK = threading.RLock()


def _read(path: Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except Exception:
        return default


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(value, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    tmp.replace(path)


def set_rule(action: str, seconds: int, message: str = "") -> dict:
    action = str(action or "").strip().lower()
    if action not in {"busy", "accept"}:
        raise ValueError("Call rule action must be busy or accept.")
    seconds = max(1, min(int(seconds), 24 * 60 * 60))
    now = time.time()
    rule = {
        "action": action,
        "created_at": now,
        "expires_at": now + seconds,
        "message": str(message or "").strip()
        or "Hello {caller} unfortunately Nived is busy, Call him again later, Bye",
    }
    with _LOCK:
        _write(STATE, rule)
    return rule


def clear_rule() -> None:
    with _LOCK:
        try:
            STATE.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            _write(STATE, {})


def active_rule() -> dict | None:
    with _LOCK:
        rule = _read(STATE, {})
        if not isinstance(rule, dict):
            return None
        expires = float(rule.get("expires_at", 0) or 0)
        if expires <= time.time():
            try:
                STATE.unlink()
            except Exception:
                pass
            return None
        return dict(rule)


def rule_status() -> str:
    rule = active_rule()
    if not rule:
        return "No automatic incoming-call rule is active."
    remaining = max(0, int(float(rule.get("expires_at", 0)) - time.time()))
    mins, secs = divmod(remaining, 60)
    action = "busy reply" if rule.get("action") == "busy" else "automatic acceptance"
    return f"Automatic {action} is active for {mins}m {secs}s."


def record_call(
    app: str,
    caller: str,
    action: str,
    *,
    source: str = "",
    message: str = "",
) -> None:
    entry = {
        "timestamp": time.time(),
        "app": str(app or "Unknown app"),
        "caller": str(caller or "").strip() or "Unknown caller",
        "action": str(action or "detected"),
        "source": str(source or ""),
        "message": str(message or ""),
    }
    with _LOCK:
        history = _read(HISTORY, [])
        if not isinstance(history, list):
            history = []
        history.append(entry)
        _write(HISTORY, history[-100:])


def recent_calls(limit: int = 10) -> list[dict]:
    with _LOCK:
        history = _read(HISTORY, [])
        if not isinstance(history, list):
            return []
        return list(reversed(history[-max(1, int(limit)):]))


def history_text(limit: int = 10) -> str:
    calls = recent_calls(limit)
    if not calls:
        return "No recent calls are recorded."
    lines = ["Recent calls:"]
    for item in calls:
        when = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(item.get("timestamp", time.time())))
        lines.append(
            f"- {when} | {item.get('app')} | {item.get('caller')} | "
            f"{item.get('action')}"
        )
    return "\n".join(lines)
