import json
import os
import time
from pathlib import Path
from urllib.parse import quote

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

_PENDING_FILE = Path.home() / ".mark_liv_advance_whatsapp_pending.json"


def _clean_phone(phone):
    return "".join(c for c in (phone or "") if c.isdigit())


def _load_pending():
    try:
        if _PENDING_FILE.exists():
            data = json.loads(_PENDING_FILE.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        pass
    return {}


def _save_pending(data):
    try:
        _PENDING_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _open_desktop():
    try:
        os.startfile("whatsapp:")
        return True
    except Exception:
        return False


def _find_whatsapp_window():
    if not Desktop:
        return None
    try:
        windows = Desktop(backend="uia").windows()
        candidates = []
        for win in windows:
            try:
                title = (win.window_text() or "").lower()
                if "whatsapp" in title:
                    candidates.append(win)
            except Exception:
                continue
        return candidates[0] if candidates else None
    except Exception:
        return None


def _focus_whatsapp():
    win = _find_whatsapp_window()
    if not win:
        return None
    try:
        win.restore()
    except Exception:
        pass
    try:
        win.set_focus()
    except Exception:
        pass
    return win


def _click_search_and_find(contact):
    win = _focus_whatsapp()
    if not win:
        return False, "WhatsApp window was not found."

    # The Windows app's search box is exposed through UI Automation.
    try:
        edits = win.descendants(control_type="Edit")
        search = None
        for edit in edits:
            try:
                name = (edit.window_text() or "").lower()
                if "search" in name:
                    search = edit
                    break
            except Exception:
                pass
        if search is None and edits:
            search = edits[0]

        if search is not None:
            search.click_input()
            search.set_edit_text(contact)
            time.sleep(1.5)
            pyautogui.press("down")
            pyautogui.press("enter")
            time.sleep(1.5)
            return True, ""
    except Exception:
        pass

    # Fallback: use the app's normal search shortcut, but do NOT use a browser.
    if pyautogui:
        try:
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.write(contact, interval=0.04)
            time.sleep(1.5)
            pyautogui.press("enter")
            time.sleep(1.5)
            return True, ""
        except Exception as e:
            return False, str(e)

    return False, "pyautogui is not installed."


def _send_message_desktop(contact, message):
    if not pyautogui:
        return False, "pyautogui is not installed."

    _open_desktop()
    time.sleep(2.5)

    ok, error = _click_search_and_find(contact)
    if not ok:
        return False, error

    # Click the actual message compose box exposed by Windows UI Automation.
    win = _focus_whatsapp()
    if win:
        try:
            edits = win.descendants(control_type="Edit")
            for edit in reversed(edits):
                try:
                    name = (edit.window_text() or "").lower()
                    if "message" in name or "type a message" in name:
                        edit.click_input()
                        edit.set_edit_text(message)
                        pyautogui.press("enter")
                        time.sleep(1)
                        return True, ""
                except Exception:
                    continue
        except Exception:
            pass

    # Keyboard fallback after the chat is selected.
    try:
        pyautogui.write(message, interval=0.03)
        pyautogui.press("enter")
        time.sleep(1)
        return True, ""
    except Exception as e:
        return False, str(e)


def _send_by_phone(phone, message):
    if not pyautogui:
        return False, "pyautogui is not installed."
    number = _clean_phone(phone)
    if not number:
        return False, "Invalid phone number."

    try:
        uri = "whatsapp://send?phone=" + number + "&text=" + quote(message)
        os.startfile(uri)
        time.sleep(3)
        # URI opens the chat; press Enter only if the app leaves a confirmation/open state.
        pyautogui.press("enter")
        time.sleep(0.7)
        return True, ""
    except Exception as e:
        return False, str(e)


def _click_call_button(kind: str):
    """Try to click the active WhatsApp desktop call button using UI Automation."""
    win = _focus_whatsapp()
    if not win:
        return False, "WhatsApp window was not found."

    wanted = (
        ["video", "video call", "videocall"]
        if kind == "video"
        else ["voice call", "audio call", "call"]
    )

    try:
        buttons = win.descendants(control_type="Button")
        # Prefer exact/strong matches first.
        for button in buttons:
            try:
                name = (button.window_text() or "").strip().lower()
                if any(name == x or x in name for x in wanted):
                    button.click_input()
                    time.sleep(1)
                    return True, ""
            except Exception:
                continue
    except Exception:
        pass

    return False, "The WhatsApp call button was not exposed through Windows UI Automation."


def whatsapp_advance(
    action: str,
    contact: str = "",
    phone: str = "",
    message: str = "",
    confirmation: str = ""
):
    action = (action or "").lower().strip()

    if action in ("open", "open_whatsapp"):
        ok = _open_desktop()
        return "Opened the WhatsApp desktop app." if ok else "Could not open the WhatsApp desktop app."

    if action in ("prepare_message", "message", "send", "send_message"):
        if not contact and not phone:
            return "A WhatsApp contact name or international phone number is required."
        if not message:
            return "The message text is required."

        if phone:
            ok, error = _send_by_phone(phone, message)
        else:
            ok, error = _send_message_desktop(contact, message)

        if not ok:
            return f"WhatsApp send failed: {error}"
        return f"Sent the WhatsApp message to {contact or phone}."

    if action in ("send_confirmed", "confirm_and_send"):
        # Kept as a backwards-compatible alias. Confirmation is no longer required.
        if not contact and not phone:
            return "A WhatsApp contact name or international phone number is required."
        if not message:
            return "The message text is required."

        if phone:
            ok, error = _send_by_phone(phone, message)
        else:
            ok, error = _send_message_desktop(contact, message)

        if not ok:
            return f"WhatsApp send failed: {error}"
        return f"Sent the WhatsApp message to {contact or phone}."

    if action in ("call", "voice_call", "video_call"):
        target = contact or phone
        if not target:
            return "A WhatsApp contact name or phone number is required."

        _open_desktop()
        time.sleep(2.5)

        if contact:
            ok, error = _click_search_and_find(contact)
            if not ok:
                return f"Could not open the WhatsApp chat for {target}: {error}"
        else:
            try:
                os.startfile("whatsapp://send?phone=" + _clean_phone(phone))
                time.sleep(3)
            except Exception as e:
                return f"Could not open the WhatsApp contact: {e}"

        kind = "video" if action == "video_call" else "voice"
        ok, error = _click_call_button(kind)

        if ok:
            return f"Started a WhatsApp {kind} call with {target}."

        return (
            f"Opened WhatsApp to {target}, but Windows UI Automation could not find "
            f"the {kind} call button. {error}"
        )

    return (
        "Unknown action. Use open_whatsapp, message, send, call, or video_call."
    )


TOOL = {
    "name": "whatsapp_advance",
    "description": (
        "Control the INSTALLED WINDOWS WHATSAPP DESKTOP APP ONLY. Never use WhatsApp Web. "
        "When the user explicitly asks to message, call, or video call a WhatsApp contact, "
        "perform the action directly without asking for a confirmation step. For messages, "
        "find the contact, open the chat, type the message, and press Enter. For voice/video "
        "calls, find the contact and use Windows UI Automation to click the matching call "
        "button automatically. Do not tell the user to press the call button manually unless "
        "UI Automation genuinely cannot find the button. send_confirmed remains as a backwards-"
        "compatible alias but does not require confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "open_whatsapp, prepare_message, send_confirmed, call, or video_call",
            },
            "contact": {
                "type": "STRING",
                "description": "WhatsApp contact name, for example Nived",
            },
            "phone": {
                "type": "STRING",
                "description": "International phone number, for example 919876543210",
            },
            "message": {
                "type": "STRING",
                "description": "Message text",
            },
            "confirmation": {
                "type": "STRING",
                "description": "Use yes/confirm only after explicit user confirmation.",
            },
        },
        "required": ["action"],
    },
    "handler": whatsapp_advance,
}
