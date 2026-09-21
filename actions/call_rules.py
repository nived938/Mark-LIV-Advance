"""Voice-controlled time-window rules for incoming desktop calls."""
from __future__ import annotations

import re

from core.call_manager import active_rule, clear_rule, history_text, rule_status, set_rule


def _seconds(value: str, default: int = 300) -> int:
    text = str(value or "").lower()
    match = re.search(r"(\d+)", text)
    if not match:
        return default
    return max(1, int(match.group(1)) * (60 if "minute" in text or "min" in text else 1))


TOOL = {
    "name": "call_rules",
    "description": (
        "Create temporary automatic incoming-call rules. Use busy for commands "
        "such as 'if anyone calls me for the next 5 minutes tell them I am busy', "
        "accept for commands such as 'for the next 1 minute accept calls', "
        "clear to disable the current rule, status to inspect it, and history to "
        "show recent calls received while the user was away."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "busy | accept | clear | status | history"},
            "minutes": {"type": "INTEGER", "description": "How many minutes the rule should stay active."},
            "message": {"type": "STRING", "description": "Optional exact message for busy mode; {caller} is replaced with caller name."},
        },
        "required": ["action"],
    },
}


def call_rules(parameters: dict | None = None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action") or "").strip().lower()
    if action == "busy":
        minutes = max(1, min(1440, int(p.get("minutes") or 5)))
        message = str(p.get("message") or "").strip()
        set_rule("busy", minutes * 60, message)
        return f"Automatic busy-call mode enabled for {minutes} minute(s)."
    if action == "accept":
        minutes = max(1, min(1440, int(p.get("minutes") or 1)))
        set_rule("accept", minutes * 60)
        return f"Automatic call acceptance enabled for {minutes} minute(s)."
    if action == "clear":
        clear_rule()
        return "Automatic incoming-call rule cleared."
    if action == "status":
        return rule_status()
    if action == "history":
        return history_text(12)
    return "Use action=busy, accept, clear, status, or history."
