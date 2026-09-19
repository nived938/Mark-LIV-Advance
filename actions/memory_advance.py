import json
from pathlib import Path
from datetime import datetime

MEMORY_FILE = Path(__file__).resolve().parent.parent / "memory" / "advance_memory.json"

def _load():
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not MEMORY_FILE.exists():
        return []
    try:
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def memory_advance(action: str, key: str = "", value: str = ""):
    data = _load()
    action = (action or "").lower().strip()

    if action == "remember":
        if not key or not value:
            return "Both key and value are required."
        data = [m for m in data if m.get("key") != key]
        data.append({"key": key, "value": value, "updated": datetime.now().isoformat(timespec="seconds")})
        MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return f"Remembered {key}."
    if action == "recall":
        matches = [m for m in data if key.lower() in m.get("key", "").lower() or key.lower() in m.get("value", "").lower()]
        return json.dumps(matches, ensure_ascii=False, indent=2) if matches else "No matching memory."
    if action == "forget":
        old = len(data)
        data = [m for m in data if m.get("key") != key]
        MEMORY_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return "Memory removed." if len(data) != old else "No memory with that key."
    if action == "list":
        return json.dumps(data, ensure_ascii=False, indent=2) if data else "Memory is empty."
    return "Unknown action. Use remember, recall, forget, or list."

TOOL = {
    "name": "memory_advance",
    "description": "Store, recall, list, and forget local long-term assistant memories.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "remember, recall, forget, or list"},
            "key": {"type": "STRING", "description": "Memory key or search text"},
            "value": {"type": "STRING", "description": "Value to remember"},
        },
        "required": ["action"],
    },
    "handler": memory_advance,
}
