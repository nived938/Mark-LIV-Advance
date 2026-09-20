"""Persistent workflow recorder/replayer for J.A.R.V.I.S."""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "memory" / "workflows"
STATE = DIR / "recorder.json"


def _load_state() -> dict:
    try:
        d = json.loads(STATE.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return {"recording": False, "name": "", "steps": [], "replaying": False}


def _save_state(d: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


def start(name: str) -> str:
    key = re.sub(r"[^A-Za-z0-9 _-]+", "", str(name or "").strip())[:80]
    if not key:
        return "Provide a workflow name."
    d = _load_state()
    d.update({"recording": True, "name": key, "steps": [], "started_at": time.time()})
    _save_state(d)
    return f"Recording workflow '{key}'."


def record(tool: str, args: dict) -> None:
    d = _load_state()
    if not d.get("recording") or d.get("replaying"):
        return
    if str(tool) == "workflow_recorder":
        return
    steps = d.setdefault("steps", [])
    steps.append({"tool": str(tool), "args": dict(args or {})})
    _save_state(d)


def stop() -> dict:
    d = _load_state()
    if not d.get("recording"):
        return {"ok": False, "message": "No workflow is being recorded."}
    name = str(d.get("name") or "workflow")
    out = DIR / f"{re.sub(r'[^A-Za-z0-9_-]+', '_', name)}.json"
    payload = {
        "name": name,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "steps": d.get("steps") or [],
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    d = {"recording": False, "name": "", "steps": [], "replaying": False}
    _save_state(d)
    return {"ok": True, "name": name, "path": str(out), "steps": len(payload["steps"])}


def list_workflows() -> list[dict]:
    DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in sorted(DIR.glob("*.json")):
        if p.name == STATE.name:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            out.append({"name": d.get("name", p.stem), "path": str(p), "steps": len(d.get("steps") or [])})
        except Exception:
            continue
    return out


def load(name: str) -> dict | None:
    target = str(name or "").strip().lower()
    for p in DIR.glob("*.json"):
        if p.name == STATE.name:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if str(d.get("name", "")).strip().lower() == target or p.stem.lower() == target:
            return d
    return None


def delete(name: str) -> str:
    d = load(name)
    if not d:
        return f"Workflow '{name}' not found."
    target = Path(d.get("path", "")) if d.get("path") else None
    # Resolve from the matching workflow name instead of trusting arbitrary input.
    for p in DIR.glob("*.json"):
        if p.name == STATE.name:
            continue
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            if str(payload.get("name", "")).strip().lower() == str(name).strip().lower():
                p.unlink(missing_ok=True)
                return f"Workflow '{name}' deleted."
        except Exception:
            pass
    if target and target.exists():
        target.unlink(missing_ok=True)
    return f"Workflow '{name}' deleted."


def set_replaying(value: bool) -> None:
    d = _load_state()
    d["replaying"] = bool(value)
    _save_state(d)
