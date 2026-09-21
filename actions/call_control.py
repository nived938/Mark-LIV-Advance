"""Accept/decline controls for currently ringing supported desktop calls."""
from __future__ import annotations

import re
import time

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

try:
    import psutil
except Exception:
    psutil = None

_ACCEPT = ("accept", "answer", "pick up", "join", "allow")
_DECLINE = ("decline", "reject", "ignore", "hang up", "end call", "cut", "dismiss")
_HANGUP = ("hang up", "end call", "disconnect", "leave", "end")
_CALL_WORDS = ("incoming", "ringing", "calling", "call", "voice call", "video call")


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _app_match(window, app: str) -> bool:
    want = _norm(app)
    if not want:
        return True
    title = ""
    try:
        title = _norm(window.window_text())
    except Exception:
        pass

    proc = ""
    if psutil is not None:
        try:
            proc = _norm(psutil.Process(int(window.process_id())).name())
        except Exception:
            pass

    return (
        want in title
        or want in proc
        or (want == "microsoft teams" and "teams" in proc)
        or (want == "google meet" and "meet" in title)
    )


def _call_window(window) -> bool:
    try:
        blob = _norm(window.window_text())
    except Exception:
        return False
    return bool(blob) and any(word in blob for word in _CALL_WORDS)


def _button(window, hints):
    try:
        controls = window.descendants(control_type="Button")
    except Exception:
        return None

    for control in controls:
        try:
            text = _norm(control.window_text())
            aid = _norm(getattr(control, "automation_id", lambda: "")())
            blob = f"{text} {aid}"
            if any(hint in blob for hint in hints):
                return control
        except Exception:
            continue
    return None


def _click(control):
    try:
        control.invoke()
        return True, ""
    except Exception:
        try:
            control.click_input()
            return True, ""
        except Exception as exc:
            return False, str(exc)


TOOL = {
    "name": "call_control",
    "description": (
        "Accept, decline, or inspect a currently ringing desktop call in "
        "supported apps such as Microsoft Teams, Zoom, Discord, Skype, Telegram, "
        "Signal, Webex, or Google Meet. Uses UI Automation and never guesses a "
        "coordinate."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "accept | decline | hangup | status"},
            "app": {"type": "STRING", "description": "Optional app name to target."},
        },
        "required": ["action"],
    },
}


def call_control(parameters: dict | None = None, **_) -> str:
    p = parameters or {}
    action = _norm(p.get("action"))
    app = str(p.get("app") or "").strip()

    if Desktop is None:
        return "UI Automation is unavailable on this Windows installation."

    try:
        windows = Desktop(backend="uia").windows(visible_only=True)
    except Exception as exc:
        return f"Could not inspect desktop windows: {exc}"

    if action == "status":
        matches = []
        for window in windows:
            try:
                if _app_match(window, app) and _call_window(window):
                    matches.append(window.window_text())
            except Exception:
                pass
        return (
            "Pending call windows: " + " | ".join(matches[:8])
            if matches else "No supported ringing call window is visible."
        )

    hints = _ACCEPT if action == "accept" else _DECLINE if action == "decline" else _HANGUP if action == "hangup" else ()
    if not hints:
        return "Action must be accept, decline, hangup, or status."

    for window in windows:
        try:
            if not _app_match(window, app) or not _call_window(window):
                continue
            control = _button(window, hints)
            if control is not None:
                ok, error = _click(control)
                if ok:
                    return f"{action.title()}ed the {window.window_text()} call."
                return f"Could not activate the call control: {error}"
        except Exception:
            continue

    for window in windows:
        try:
            if not _app_match(window, app) or not _call_window(window):
                continue
            try:
                window.set_focus()
            except Exception:
                pass
            if pyautogui:
                key = "enter" if action == "accept" else "esc"
                pyautogui.press(key)
                time.sleep(0.4)
                return f"Sent the {action} key to {window.window_text()}."
        except Exception:
            continue

    return "No matching ringing call control was found."
