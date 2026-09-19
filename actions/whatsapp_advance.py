import os
import time
import webbrowser
from urllib.parse import quote

try:
    import pyautogui
except Exception:
    pyautogui = None

_pending = {}

def _open_desktop():
    try:
        os.startfile("whatsapp:")
        return True
    except Exception:
        try:
            os.startfile("shell:AppsFolder")
            return True
        except Exception:
            return False

def _clean_phone(phone):
    return "".join(c for c in (phone or "") if c.isdigit())

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

    if action in ("prepare_message", "message"):
        if not contact and not phone:
            return "A WhatsApp contact name or international phone number is required."
        if not message:
            return "The message text is required."

        key = contact.strip().lower() if contact else _clean_phone(phone)
        _pending[key] = {
            "contact": contact.strip(),
            "phone": _clean_phone(phone),
            "message": message,
        }
        return (
            f"READY_FOR_CONFIRMATION: Send this WhatsApp message to "
            f"{contact or phone}: {message!r}. "
            f"Ask the user to confirm before calling whatsapp_advance again "
            f"with action=send_confirmed and the same contact/phone."
        )

    if action == "send_confirmed":
        if (confirmation or "").lower().strip() not in ("yes", "confirm", "confirmed", "true"):
            return "REQUIRES_CONFIRMATION: The user must explicitly confirm before sending."
        key = contact.strip().lower() if contact else _clean_phone(phone)
        pending = _pending.get(key)
        if not pending:
            return "No prepared WhatsApp message was found. Prepare the message first."

        if not pyautogui:
            return "pyautogui is not installed, so WhatsApp desktop automation is unavailable."

        try:
            if pending["phone"]:
                # Use the Windows WhatsApp URI when a phone number is known.
                uri = (
                    "whatsapp://send?phone="
                    + pending["phone"]
                    + "&text="
                    + quote(pending["message"])
                )
                os.startfile(uri)
                time.sleep(2)
                pyautogui.press("enter")
            else:
                # Contact-name workflow for the installed Windows WhatsApp app.
                _open_desktop()
                time.sleep(3)
                pyautogui.hotkey("ctrl", "f")
                time.sleep(0.5)
                pyautogui.write(pending["contact"], interval=0.03)
                time.sleep(1)
                pyautogui.press("enter")
                time.sleep(1.5)
                pyautogui.write(pending["message"], interval=0.02)
                pyautogui.press("enter")

            del _pending[key]
            return f"Sent the WhatsApp message to {pending['contact'] or pending['phone']}."
        except Exception as e:
            return f"WhatsApp send failed: {e}"

    if action in ("call", "voice_call", "video_call"):
        target = contact or phone
        if not target:
            return "A WhatsApp contact name or phone number is required."
        if (confirmation or "").lower().strip() not in ("yes", "confirm", "confirmed", "true"):
            return (
                f"REQUIRES_CONFIRMATION: Start a WhatsApp "
                f"{'video' if action == 'video_call' else 'voice'} call with {target}."
            )
        # There is no stable documented Windows WhatsApp URI for starting calls.
        # Open the desktop app and the requested contact; the user starts the call.
        _open_desktop()
        if pyautogui and contact:
            time.sleep(3)
            pyautogui.hotkey("ctrl", "f")
            time.sleep(0.5)
            pyautogui.write(contact, interval=0.03)
            pyautogui.press("enter")
        return (
            f"Opened WhatsApp to {target}. "
            f"Windows WhatsApp does not expose a stable public call URI, "
            f"so the { 'video' if action == 'video_call' else 'voice'} call button must be pressed in the app."
        )

    return "Unknown action. Use open_whatsapp, prepare_message, send_confirmed, call, or video_call."

TOOL = {
    "name": "whatsapp_advance",
    "description": (
        "Control the installed Windows WhatsApp desktop app. "
        "Use prepare_message first, then require explicit user confirmation, "
        "then use send_confirmed to send. Do not use WhatsApp Web. "
        "A contact name can be used; a phone number can be used for a direct chat. "
        "Voice/video calls require confirmation and open the contact; the final call button "
        "is manual because Windows WhatsApp has no stable public call URI."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open_whatsapp, prepare_message, send_confirmed, call, or video_call"},
            "contact": {"type": "STRING", "description": "WhatsApp contact name, for example Nived"},
            "phone": {"type": "STRING", "description": "International phone number, for example 919876543210"},
            "message": {"type": "STRING", "description": "Message text"},
            "confirmation": {"type": "STRING", "description": "Use yes/confirm only after the user explicitly confirms."},
        },
        "required": ["action"],
    },
    "handler": whatsapp_advance,
}
