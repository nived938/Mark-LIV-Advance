import pyperclip
from pathlib import Path


def clipboard_advance(action: str, text: str = "", file_path: str = ""):
    """Control the real Windows clipboard.

    This action only reads/writes the OS clipboard. It does not use the chat
    transcript as clipboard content.
    """
    action = (action or "").lower().strip()
    try:
        if action in ("read", "paste", "get"):
            value = pyperclip.paste()
            return value if value else "Clipboard is empty."
        if action in ("set", "copy"):
            if not text:
                return "Text is required to set the clipboard."
            pyperclip.copy(text)
            return f"Clipboard updated with: {text}"
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
        return "Unknown action. Use read, get, set, copy, clipboard_to_file, or clear."
    except Exception as e:
        return f"Clipboard error: {e}"


TOOL = {
    "name": "clipboard_advance",
    "description": "REAL WINDOWS CLIPBOARD TOOL. MUST be called when the user asks to read/get/check/show their clipboard, set/copy text to the clipboard, paste clipboard content, save clipboard to a file, or clear it. For 'read my clipboard', call action='read' and return the tool result; NEVER guess clipboard contents from the conversation or repeat the user's latest message.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "read/get/paste, set/copy, clipboard_to_file, or clear"},
            "text": {"type": "STRING", "description": "Text for set/copy"},
            "file_path": {"type": "STRING", "description": "Destination path for clipboard_to_file"},
        },
        "required": ["action"],
    },
    "handler": clipboard_advance,
}
