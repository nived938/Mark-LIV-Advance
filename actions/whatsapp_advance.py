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


def _open_desktop():
    try:
        os.startfile("whatsapp:")
        return True
    except Exception:
        return False


def _find_whatsapp_window(timeout=10.0):
    """Wait for the real installed Windows WhatsApp window to appear."""
    if not Desktop:
        return None

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            windows = Desktop(backend="uia").windows()
            for win in windows:
                try:
                    title = (win.window_text() or "").strip().lower()
                    cls = (getattr(win, "class_name", lambda: "")() or "").lower()
                    if "whatsapp" in title or "whatsapp" in cls:
                        return win
                except Exception:
                    continue
        except Exception:
            pass
        time.sleep(0.5)
    return None


def _focus_whatsapp(timeout=10.0):
    win = _find_whatsapp_window(timeout)
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
    time.sleep(0.25)
    return win


def _set_edit_text(control, text):
    try:
        control.click_input()
        time.sleep(0.15)
        control.set_edit_text(text)
        return True
    except Exception:
        return False


def _get_edit_controls(win):
    try:
        return win.descendants(control_type="Edit")
    except Exception:
        return []


def _click_search_and_find(contact):
    win = _focus_whatsapp(timeout=8)
    if not win:
        return False, "WhatsApp desktop window did not appear after opening it."

    # WhatsApp can take several seconds before its accessibility tree is ready.
    for _ in range(6):
        try:
            edits = _get_edit_controls(win)
            search = None
            for edit in edits:
                try:
                    name = (edit.window_text() or "").lower()
                    aid = (getattr(edit, "automation_id", lambda: "")() or "").lower()
                    if "search" in name or "search" in aid:
                        search = edit
                        break
                except Exception:
                    pass

            # If the search box has no accessible name, the first edit is normally it.
            if search is None and edits:
                search = edits[0]

            if search is not None and _set_edit_text(search, contact):
                time.sleep(1.2)
                if pyautogui:
                    pyautogui.press("down")
                    pyautogui.press("enter")
                time.sleep(1.5)
                return True, ""
        except Exception:
            pass
        time.sleep(0.7)

    # Keyboard fallback, still against the installed Windows app.
    if pyautogui:
        try:
            win.set_focus()
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.5)
            pyautogui.hotkey("ctrl", "a")
            pyautogui.write(contact, interval=0.04)
            time.sleep(1.5)
            pyautogui.press("down")
            pyautogui.press("enter")
            time.sleep(1.5)
            return True, ""
        except Exception as e:
            return False, str(e)

    return False, "Could not access the WhatsApp search box."


def _find_message_edit(win):
    for _ in range(5):
        try:
            edits = _get_edit_controls(win)
            for edit in reversed(edits):
                try:
                    name = (edit.window_text() or "").lower()
                    aid = (getattr(edit, "automation_id", lambda: "")() or "").lower()
                    if any(x in (name + " " + aid) for x in ("message", "type a message", "compose")):
                        return edit
                except Exception:
                    continue
            # After a chat is selected, the last Edit is normally the compose box.
            if len(edits) >= 2:
                return edits[-1]
        except Exception:
            pass
        time.sleep(0.6)
    return None


def _send_message_desktop(contact, message):
    if not pyautogui:
        return False, "pyautogui is not installed."

    if not _open_desktop():
        return False, "Could not launch the installed WhatsApp desktop app."

    # Do not declare failure while WhatsApp is still starting.
    win = _focus_whatsapp(timeout=12)
    if not win:
        return False, "WhatsApp opened, but its Windows app window was not detected."

    ok, error = _click_search_and_find(contact)
    if not ok:
        return False, error

    win = _focus_whatsapp(timeout=5)
    if not win:
        return False, "WhatsApp chat opened, but the desktop window disappeared."

    edit = _find_message_edit(win)
    if edit is not None and _set_edit_text(edit, message):
        pyautogui.press("enter")
        time.sleep(0.8)
        return True, ""

    # Final keyboard fallback. The chat is already selected and focused.
    try:
        win.set_focus()
        pyautogui.write(message, interval=0.03)
        pyautogui.press("enter")
        time.sleep(0.8)
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
        pyautogui.press("enter")
        time.sleep(0.7)
        return True, ""
    except Exception as e:
        return False, str(e)


def _click_call_button(kind: str):
    win = _focus_whatsapp(timeout=8)
    if not win:
        return False, "WhatsApp window was not found."

    if kind == "video":
        wanted = {"video", "video call", "videocall", "start video call"}
    else:
        wanted = {"voice call", "audio call", "start voice call", "start audio call"}

    matches = []
    try:
        for control in win.descendants():
            try:
                name = (control.window_text() or "").strip().lower()
                automation_id = (getattr(control, "automation_id", lambda: "")() or "").strip().lower()
                if name in wanted or automation_id in wanted:
                    matches.append(control)
            except Exception:
                continue
    except Exception:
        pass

    for control in matches:
        try:
            control.invoke()
            time.sleep(2)
            return True, ""
        except Exception:
            pass
        try:
            control.click_input()
            time.sleep(2)
            return True, ""
        except Exception:
            pass

    return False, f"WhatsApp exposed no exact {kind} call control to Windows UI Automation."


def whatsapp_advance(action: str, contact: str = "", phone: str = "", message: str = "", confirmation: str = ""):
    action = (action or "").lower().strip()

    if action in ("open", "open_whatsapp"):
        ok = _open_desktop()
        return "Opened the WhatsApp desktop app." if ok else "Could not open the WhatsApp desktop app."

    if action in ("prepare_message", "message", "send", "send_message", "send_confirmed", "confirm_and_send"):
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

        if not _open_desktop():
            return "Could not open the WhatsApp desktop app."
        time.sleep(1.5)
        win = _focus_whatsapp(timeout=10)
        if not win:
            return "WhatsApp opened, but its Windows app window was not detected yet."

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
            return f"Triggered the WhatsApp {kind} call control for {target}."
        return f"Opened WhatsApp to {target}, but I could not trigger the {kind} call control. {error}"

    return "Unknown action. Use open_whatsapp, message, send, call, or video_call."


TOOL = {
    "name": "whatsapp_advance",
    "description": (
        "Control the installed WINDOWS WhatsApp desktop app only. Never use WhatsApp Web. "
        "For a normal WhatsApp message, find the contact, open the chat, type the message, "
        "and press Enter automatically. Do not ask for confirmation. Wait for the WhatsApp "
        "desktop window to finish opening before searching. Calls and video calls should also "
        "be triggered automatically through Windows UI Automation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open_whatsapp, message, send, call, or video_call"},
            "contact": {"type": "STRING", "description": "WhatsApp contact name"},
            "phone": {"type": "STRING", "description": "International phone number"},
            "message": {"type": "STRING", "description": "Message text"},
            "confirmation": {"type": "STRING", "description": "Legacy field, not required"},
        },
        "required": ["action"],
    },
    "handler": whatsapp_advance,
}
