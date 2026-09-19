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


def whatsapp_advance(
    action: str,
    contact: str = "",
    phone: str = "",
    message: str = "",
    confirmation: str = ""
):
    action = (action or "").lower().strip()
    pending = _load_pending()

    if action in ("open", "open_whatsapp"):
        ok = _open_desktop()
        return "Opened the WhatsApp desktop app." if ok else "Could not open the WhatsApp desktop app."

    if action in ("prepare_message", "message"):
        if not contact and not phone:
            return "A WhatsApp contact name or international phone number is required."
        if not message:
            return "The message text is required."

        key = (contact.strip().lower() if contact else _clean_phone(phone))
        pending[key] = {
            "contact": contact.strip(),
            "phone": _clean_phone(phone),
            "message": message,
        }
        _save_pending(pending)

        return (
            f"READY_FOR_CONFIRMATION: WhatsApp message prepared for "
            f"{contact or phone}: {message!r}. "
            f"STOP and ask the user for explicit confirmation. "
            f"After the user says yes/confirm/send it, call whatsapp_advance "
            f"with action=send_confirmed and contact={contact!r} or phone={phone!r}, "
            f"confirmation='yes'. Do not prepare the message again."
        )

    if action in ("send_confirmed", "confirm_and_send"):
        accepted = {"yes", "y", "yeah", "yep", "sure", "confirm", "confirmed", "true", "send", "send it", "do it"}
        if (confirmation or "").lower().strip() not in accepted:
            return "REQUIRES_CONFIRMATION: Explicit user confirmation is required before sending."

        key = contact.strip().lower() if contact else _clean_phone(phone)
        if not key and len(pending) == 1:
            key = next(iter(pending))

        item = pending.get(key)
        if not item:
            return (
                "No prepared WhatsApp message was found for this confirmation. "
                "Use the saved pending message instead of asking the user to repeat it."
            )

        if item["phone"]:
            ok, error = _send_by_phone(item["phone"], item["message"])
        else:
            ok, error = _send_message_desktop(item["contact"], item["message"])

        if not ok:
            return f"WhatsApp send failed: {error}"

        pending.pop(key, None)
        _save_pending(pending)
        return f"Sent the WhatsApp message to {item['contact'] or item['phone']}."

    if action in ("call", "voice_call", "video_call"):
        target = contact or phone
        if not target:
            return "A WhatsApp contact name or phone number is required."

        if (confirmation or "").lower().strip() not in {
            "yes", "y", "yeah", "yep", "sure", "confirm", "confirmed", "true", "do it"
        }:
            return (
                f"REQUIRES_CONFIRMATION: Start a WhatsApp "
                f"{'video' if action == 'video_call' else 'voice'} call with {target}. "
                f"Wait for explicit confirmation."
            )

        _open_desktop()
        time.sleep(2.5)
        if contact:
            _click_search_and_find(contact)

        return (
            f"Opened WhatsApp to {target}. "
            f"The final {'video' if action == 'video_call' else 'voice'} call button "
            f"must be pressed manually because the Windows WhatsApp app does not provide "
            f"a stable public call URI."
        )

    return (
        "Unknown action. Use open_whatsapp, prepare_message, send_confirmed, "
        "call, or video_call."
    )


TOOL = {
    "name": "whatsapp_advance",
    "description": (
        "Control the INSTALLED WINDOWS WHATSAPP DESKTOP APP ONLY. Never use WhatsApp Web. "
        "For messages: call prepare_message once, STOP and ask the user for confirmation. "
        "When the user confirms, call send_confirmed using the SAME contact/phone and "
        "confirmation='yes'. The prepared message is persisted to disk, so it remains "
        "available across separate tool calls. Never ask the user to repeat the message. "
        "The send_confirmed action searches for the contact in the desktop WhatsApp app, "
        "selects the chat, types into the message compose box, and presses Enter. "
        "Voice/video calls require confirmation and open the contact; the final call button "
        "is manual because Windows WhatsApp has no stable public call URI."
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
