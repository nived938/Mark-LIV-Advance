"""
clipboard.py
Clipboard control for Mark-LIV.

Supports:
- Copy selected text
- Read clipboard
- Set clipboard text
- Paste clipboard into the active application
"""

import time
import platform


_SYSTEM = platform.system()


def _get_clipboard():
    """Return the current clipboard text."""

    try:
        import pyperclip

        text = pyperclip.paste()

        if text is None:
            return ""

        return str(text)

    except ImportError:
        return _get_clipboard_windows()

    except Exception as e:
        return f"Clipboard read failed: {e}"


def _set_clipboard(text: str):
    """Put text into the system clipboard."""

    try:
        import pyperclip

        pyperclip.copy(str(text))
        return True

    except ImportError:
        return _set_clipboard_windows(text)

    except Exception:
        return False


def _get_clipboard_windows():
    """Windows clipboard fallback using PowerShell."""

    if _SYSTEM != "Windows":
        return ""

    try:
        import subprocess

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-Clipboard"
            ],
            capture_output=True,
            text=True,
            timeout=5,
            encoding="utf-8",
            errors="ignore",
        )

        if result.returncode == 0:
            return result.stdout.rstrip("\r\n")

    except Exception:
        pass

    return ""


def _set_clipboard_windows(text: str):
    """Windows clipboard fallback using PowerShell."""

    if _SYSTEM != "Windows":
        return False

    try:
        import subprocess

        process = subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "$input | Set-Clipboard"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
        )

        process.communicate(text, timeout=5)

        return process.returncode == 0

    except Exception:
        return False


def _press_copy():
    """Send Ctrl+C to the active application."""

    try:
        import pyautogui

        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.3)

        return True

    except Exception as e:
        print(f"[clipboard] Copy hotkey failed: {e}")
        return False


def _press_paste():
    """Send Ctrl+V to the active application."""

    try:
        import pyautogui

        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.3)

        return True

    except Exception as e:
        print(f"[clipboard] Paste hotkey failed: {e}")
        return False


def clipboard_action(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:

    parameters = parameters or {}

    action = str(
        parameters.get("action", "read")
    ).strip().lower()

    text = parameters.get("text", "")

    # ---------------------------------------------------------
    # COPY
    # ---------------------------------------------------------

    if action in (
        "copy",
        "copy_selected",
        "copy_selection",
    ):

        if not _press_copy():
            return "I could not send the copy command."

        copied = _get_clipboard()

        if copied:
            preview = copied[:300]

            if len(copied) > 300:
                preview += "..."

            return (
                f"Copied the selected text to the clipboard.\n"
                f"Clipboard content: {preview}"
            )

        return "The copy command was sent, but no text was found in the clipboard."

    # ---------------------------------------------------------
    # PASTE
    # ---------------------------------------------------------

    if action in (
        "paste",
        "paste_clipboard",
    ):

        if not _press_paste():
            return "I could not send the paste command."

        return "Pasted the clipboard content."

    # ---------------------------------------------------------
    # READ CLIPBOARD
    # ---------------------------------------------------------

    if action in (
        "read",
        "get",
        "read_clipboard",
        "clipboard",
    ):

        content = _get_clipboard()

        if not content:
            return "The clipboard is empty."

        return f"Clipboard content:\n{content}"

        # ---------------------------------------------------------
    # CLIPBOARD TO FILE
    # ---------------------------------------------------------

    if action in (
        "clipboard_to_file",
        "save_to_file",
        "write_to_file",
        "save_clipboard",
    ):

        return clipboard_to_file(
            parameters=parameters,
            response=response,
            player=player,
            session_memory=session_memory,
        )

    # ---------------------------------------------------------
    # SET CLIPBOARD
    # ---------------------------------------------------------

    if action in (
        "set",
        "write",
        "copy_text",
    ):

        if not text:
            return "No text was provided to copy."

        if not _set_clipboard(text):
            return "I could not write to the clipboard."

        return "The text has been copied to the clipboard."

    return (
        f"Unknown clipboard action: {action}. "
        "Use copy, paste, read, or set."
    )

def clipboard_to_file(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Write the current clipboard text to a file
    using Mark-LIV's file controller so the operation
    can participate in the existing undo system.
    """

    parameters = parameters or {}

    file_path = (
        parameters.get("file_path")
        or parameters.get("path")
        or parameters.get("destination")
        or ""
    )

    if not file_path:
        return "No destination file was provided."

    file_path = str(file_path).strip().strip('"').strip("'")

    content = _get_clipboard()

    if not content:
        return "The clipboard is empty. Nothing was written."

    try:
        from pathlib import Path

        path = Path(file_path).expanduser()

        import os

        path = Path(
            os.path.expandvars(str(path))
        )

        # Import the existing Mark-LIV file writer.
        from actions.file_controller import write_file

        result = write_file(
            str(path),
            content=content,
            append=False,
        )

        return result

    except PermissionError:
        return (
            f"Access denied when writing to {file_path}. "
            "Check that the folder is writable."
        )

    except Exception as e:
        return (
            f"Could not save clipboard content to "
            f"{file_path}: {e}"
        )


# ── Tool declaration ─────────────────────────────────────────

TOOL = {
    "name": "clipboard",
    "description": (
        "Manage the Windows clipboard. "
        "Copy selected text, paste clipboard contents, read the clipboard, "
        "set clipboard text, or save the current clipboard contents to a file."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "Clipboard operation to perform. "
                    "Use copy, paste, read, set, or clipboard_to_file."
                ),
            },
            "text": {
                "type": "STRING",
                "description": (
                    "Text to place into the clipboard when using the set action."
                ),
            },
            "file_path": {
                "type": "STRING",
                "description": (
                    "Destination file path when using clipboard_to_file. "
                    "Example: G:\\Coding\\Mark-LIV-Copy\\test.txt"
                ),
            },
        },
        "required": ["action"],
    },
    "handler": clipboard_action,
}