"""Local meeting capture state.

The live Gemini session provides input transcription. When a meeting is active,
main.py appends those transcribed microphone turns here. Stopping the meeting
returns a transcript that Gemini can summarize naturally in the user's language.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "memory" / "meetings"
ACTIVE = DIR / "active.json"


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._ -]+", "", str(value or "").strip())
    return (value or "meeting")[:80]


def _load_active() -> dict | None:
    try:
        data = json.loads(ACTIVE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("active") else None
    except Exception:
        return None


def is_active() -> bool:
    return _load_active() is not None


def start_meeting(name: str = "") -> dict:
    if is_active():
        return {"ok": False, "message": "A meeting is already active."}
    DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    title = _safe_name(name) or "meeting"
    data = {
        "active": True,
        "id": f"{stamp}_{title.replace(' ', '_')}",
        "title": title,
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "lines": [],
    }
    ACTIVE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def append_line(speaker: str, text: str) -> None:
    data = _load_active()
    if not data or not str(text or "").strip():
        return
    data.setdefault("lines", []).append({
        "time": time.strftime("%H:%M:%S"),
        "speaker": str(speaker or "User")[:40],
        "text": str(text).strip()[:4000],
    })
    ACTIVE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def status() -> dict:
    data = _load_active()
    if not data:
        return {"active": False}
    return {
        "active": True,
        "id": data.get("id", ""),
        "title": data.get("title", ""),
        "started_at": data.get("started_at", ""),
        "line_count": len(data.get("lines") or []),
    }


def stop_meeting() -> dict:
    data = _load_active()
    if not data:
        return {"ok": False, "message": "No active meeting."}
    data["active"] = False
    data["ended_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    transcript = "
".join(
        f"[{line.get('time','')}] {line.get('speaker','User')}: {line.get('text','')}"
        for line in data.get("lines") or []
    )
    out = DIR / f"{data.get('id','meeting')}.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    ACTIVE.unlink(missing_ok=True)
    txt_path = out.with_suffix(".txt")
    txt_path.write_text(transcript, encoding="utf-8")
    return {
        "ok": True,
        "title": data.get("title", "meeting"),
        "transcript_path": str(txt_path),
        "transcript": transcript[:30000],
        "line_count": len(data.get("lines") or []),
    }
