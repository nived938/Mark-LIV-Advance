import json
from pathlib import Path
from datetime import datetime

# Store memory in the user's profile, not inside the repository. This makes
# memory survive git pulls, repository replacement, and running from another cwd.
MEMORY_FILE = Path.home() / ".mark_liv_advance_memory.json"


def _load():
    try:
        if not MEMORY_FILE.exists():
            return []
        data = json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save(data):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = MEMORY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(MEMORY_FILE)


def memory_advance(action: str, key: str = "", value: str = ""):
    data = _load()
    action = (action or "").lower().strip()
    key = (key or "").strip()

    if action in ("remember", "save", "store"):
        if not key or not value:
            return "Both key and value are required."
        # Replace an existing exact key instead of creating duplicates.
        data = [m for m in data if str(m.get("key", "")).lower() != key.lower()]
        data.append({"key": key, "value": str(value), "updated": datetime.now().isoformat(timespec="seconds")})
        _save(data)
        return f"Remembered: {key} = {value}"

    if action in ("recall", "get", "search"):
        if not key:
            return "A memory key or search text is required."
        needle = key.lower()
        matches = [m for m in data if needle in str(m.get("key", "")).lower() or needle in str(m.get("value", "")).lower()]
        return json.dumps(matches, ensure_ascii=False, indent=2) if matches else "No matching memory."

    if action == "forget":
        if not key:
            return "A memory key is required."
        old = len(data)
        data = [m for m in data if str(m.get("key", "")).lower() != key.lower()]
        _save(data)
        return "Memory removed." if len(data) != old else "No memory with that key."

    if action == "list":
        return json.dumps(data, ensure_ascii=False, indent=2) if data else "Memory is empty."

    return "Unknown action. Use remember, recall, forget, or list."


TOOL = {
    "name": "memory_advance",
    "description": "REAL LONG-TERM LOCAL MEMORY. MUST be called when the user says remember, save this, don't forget, recall, what did you remember, or asks where a remembered item is. Memory is stored persistently in the user's profile at ~/.mark_liv_advance_memory.json. For 'Remember that my project is at G:/Coding/Mark-LIV-Advance', call action='remember', key='Mark-LIV-Advance project', value='G:/Coding/Mark-LIV-Advance'. For 'Where is my Mark LIV Advance project?', call action='recall' with key='Mark-LIV-Advance project'. NEVER claim something was remembered or recalled without calling this tool.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "remember, recall, forget, or list"},
            "key": {"type": "STRING", "description": "Stable memory key or search text"},
            "value": {"type": "STRING", "description": "Value to remember"},
        },
        "required": ["action"],
    },
    "handler": memory_advance,
}
