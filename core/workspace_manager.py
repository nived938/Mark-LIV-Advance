"""Persistent personal workspace profiles.

Workspace modes are separate from operating modes:
- operating mode controls autonomy/system behavior (normal/gaming/serious)
- workspace controls preferred apps, context and notes (coding/study/work/presentation/travel...)
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "memory" / "workspaces.json"

DEFAULTS = {
    "coding": {
        "description": "Development and coding context.",
        "apps": ["code"],
        "context": "Focus on programming, repositories, terminals, tests and developer work.",
    },
    "study": {
        "description": "Study and school context.",
        "apps": [],
        "context": "Focus on learning, explanations, revision and school work.",
    },
    "work": {
        "description": "General work context.",
        "apps": [],
        "context": "Focus on work documents, communication and productive tasks.",
    },
    "presentation": {
        "description": "Presentation context.",
        "apps": [],
        "context": "Keep responses concise and presentation-friendly.",
    },
    "travel": {
        "description": "Travel planning context.",
        "apps": [],
        "context": "Focus on routes, bookings, schedules and travel information.",
    },
}


def _load() -> dict:
    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"active": "", "profiles": dict(DEFAULTS)}


def _save(data: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def list_workspaces() -> dict:
    data = _load()
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        profiles = {}
    return profiles


def current_workspace() -> str:
    return str(_load().get("active") or "").strip().lower()


def workspace_context() -> str:
    data = _load()
    name = current_workspace()
    if not name:
        return "[WORKSPACE]\nNo personal workspace is active.\n"
    profile = (data.get("profiles") or {}).get(name) or {}
    return (
        "[WORKSPACE]\n"
        f"Active workspace: {name}\n"
        f"Description: {profile.get('description', '')}\n"
        f"Context: {profile.get('context', '')}\n"
    )


def set_workspace(name: str, launch_apps: bool = False) -> dict:
    key = str(name or "").strip().lower()
    data = _load()
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        profiles = dict(DEFAULTS)
        data["profiles"] = profiles

    if key not in profiles:
        return {"ok": False, "message": f"Unknown workspace '{name}'."}

    data["active"] = key
    _save(data)

    opened = []
    if launch_apps:
        for app in profiles[key].get("apps") or []:
            if _launch(app):
                opened.append(app)

    return {"ok": True, "workspace": key, "opened": opened, "profile": profiles[key]}


def define_workspace(name: str, description: str = "", context: str = "", apps=None) -> str:
    key = str(name or "").strip().lower()
    if not key or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_- " for ch in key):
        return "Workspace name must contain letters, numbers, spaces, '_' or '-'."
    data = _load()
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        profiles = dict(DEFAULTS)
    profiles[key] = {
        "description": str(description or "").strip()[:300],
        "context": str(context or "").strip()[:1000],
        "apps": [str(x).strip() for x in (apps or []) if str(x).strip()][:12],
    }
    data["profiles"] = profiles
    _save(data)
    return f"Workspace '{key}' saved."


def delete_workspace(name: str) -> str:
    key = str(name or "").strip().lower()
    if key in DEFAULTS:
        return "Built-in workspaces cannot be deleted."
    data = _load()
    profiles = data.get("profiles")
    if key not in profiles:
        return f"Workspace '{key}' does not exist."
    del profiles[key]
    if data.get("active") == key:
        data["active"] = ""
    _save(data)
    return f"Workspace '{key}' deleted."


def _launch(app: str) -> bool:
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["cmd", "/c", "start", "", app])
        else:
            subprocess.Popen([app])
        return True
    except Exception:
        try:
            if platform.system() == "Windows":
                os.startfile(app)  # type: ignore[attr-defined]
                return True
        except Exception:
            pass
    return False
