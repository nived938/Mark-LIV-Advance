"""Persistent behavioral rules learned from the user's explicit instructions.

A learned rule is different from ordinary long-term memory:
- memory stores facts about the user;
- a learned rule changes how JARVIS should behave next time.

Rules are local JSON and are injected into the system context at connection time.
Nothing is inferred silently: JARVIS only learns a rule when the user explicitly
asks it to remember a behavior.
"""
from __future__ import annotations

import json
import re
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "memory" / "learned_rules.json"
_LOCK = threading.RLock()


def _default() -> dict:
    return {"version": 1, "rules": []}


def _load() -> dict:
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("rules"), list):
            return data
    except Exception:
        pass
    return _default()


def _save(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE)


def _clean(value: str, limit: int) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())[:limit]


def add_rule(trigger: str, instruction: str, name: str = "") -> dict:
    trigger = _clean(trigger, 240)
    instruction = _clean(instruction, 600)
    name = _clean(name, 80)
    if not trigger:
        return {"ok": False, "message": "A trigger or situation is required."}
    if not instruction:
        return {"ok": False, "message": "A behavior instruction is required."}

    with _LOCK:
        data = _load()
        for rule in data["rules"]:
            if (
                rule.get("enabled", True)
                and rule.get("trigger", "").casefold() == trigger.casefold()
            ):
                rule["instruction"] = instruction
                if name:
                    rule["name"] = name
                rule["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                _save(data)
                return {"ok": True, "updated": True, "rule": rule}

        rule = {
            "id": uuid.uuid4().hex[:10],
            "name": name or trigger[:60],
            "trigger": trigger,
            "instruction": instruction,
            "enabled": True,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        data["rules"].append(rule)
        _save(data)
        return {"ok": True, "updated": False, "rule": rule}


def remove_rule(rule_id: str) -> bool:
    with _LOCK:
        data = _load()
        before = len(data["rules"])
        data["rules"] = [
            r for r in data["rules"] if str(r.get("id")) != str(rule_id)
        ]
        changed = len(data["rules"]) != before
        if changed:
            _save(data)
        return changed


def set_enabled(rule_id: str, enabled: bool) -> bool:
    with _LOCK:
        data = _load()
        for rule in data["rules"]:
            if str(rule.get("id")) == str(rule_id):
                rule["enabled"] = bool(enabled)
                _save(data)
                return True
    return False


def list_rules() -> list[dict]:
    with _LOCK:
        return [dict(r) for r in _load()["rules"]]


def prompt_context(max_rules: int = 20) -> str:
    with _LOCK:
        rules = [
            r for r in _load()["rules"]
            if r.get("enabled", True)
        ][:max(1, int(max_rules))]

    if not rules:
        return ""

    lines = [
        "[LEARNED BEHAVIOR RULES]",
        "These are behaviors the user explicitly asked JARVIS to remember.",
        "Follow them when the described situation matches. They do not override "
        "safety, privacy, or a newer explicit instruction.",
    ]
    for rule in rules:
        lines.append(
            f"- Situation: {rule.get('trigger', '')}\n"
            f"  Behavior: {rule.get('instruction', '')}"
        )
    return "\n".join(lines)


def find_matches(text: str) -> list[dict]:
    """Cheap local matcher for integrations that want matching rules."""
    low = str(text or "").casefold()
    if not low:
        return []
    out = []
    for rule in list_rules():
        if not rule.get("enabled", True):
            continue
        trigger = str(rule.get("trigger") or "").casefold()
        if trigger and trigger in low:
            out.append(rule)
    return out
