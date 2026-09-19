import pyperclip
from pathlib import Path

def clipboard_advance(action: str, text: str = "", file_path: str = ""):
    action = (action or "").lower().strip()
    try:
        if action == "read" or action == "paste":
            return pyperclip.paste()
        if action == "set":
            pyperclip.copy(text)
            return "Clipboard updated."
        if action == "clipboard_to_file":
            if not file_path:
                return "A destination file path is required."
            path = Path(file_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(pyperclip.paste(), encoding="utf-8")
            return f"Clipboard saved to {path}."
        if action == "clear":
            pyperclip.copy("")
            return "Clipboard cleared."
        return "Unknown action. Use read, paste, set, clipboard_to_file, or clear."
    except Exception as e:
        return f"Clipboard error: {e}"

TOOL = {
    "name": "clipboard_advance",
    "description": "Read, set, clear, paste, or save the Windows clipboard to a file.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "read, paste, set, clipboard_to_file, or clear"},
            "text": {"type": "STRING", "description": "Text for set"},
            "file_path": {"type": "STRING", "description": "Destination path for clipboard_to_file"},
        },
        "required": ["action"],
    },
    "handler": clipboard_advance,
}
