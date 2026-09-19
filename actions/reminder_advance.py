import json
import threading
import time
from datetime import datetime
from pathlib import Path

FILE = Path(__file__).resolve().parent.parent / "memory" / "reminders.json"

def _load():
    if not FILE.exists():
        return []
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def reminder_advance(action: str, text: str = "", when: str = ""):
    data = _load()
    action = (action or "").lower().strip()
    if action == "add":
        if not text or not when:
            return "Text and an ISO datetime are required, for example 2026-09-20T18:30:00."
        try:
            dt = datetime.fromisoformat(when)
        except ValueError:
            return "Invalid datetime. Use ISO format: YYYY-MM-DDTHH:MM:SS."
        item = {"id": int(time.time() * 1000), "text": text, "when": dt.isoformat(), "done": False}
        data.append(item)
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return f"Reminder created for {dt}."
    if action == "list":
        pending = [x for x in data if not x.get("done")]
        return json.dumps(pending, indent=2) if pending else "No pending reminders."
    if action == "remove":
        try:
            rid = int(text)
            data = [x for x in data if x.get("id") != rid]
            FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return "Reminder removed."
        except ValueError:
            return "Provide the reminder id."
    return "Unknown action. Use add, list, or remove."

TOOL = {
    "name": "reminder_advance",
    "description": "Create, list, and remove local reminders. Use an ISO datetime for scheduling.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "add, list, or remove"},
            "text": {"type": "STRING", "description": "Reminder text, or reminder id when removing"},
            "when": {"type": "STRING", "description": "ISO datetime, for example 2026-09-20T18:30:00"},
        },
        "required": ["action"],
    },
    "handler": reminder_advance,
}
