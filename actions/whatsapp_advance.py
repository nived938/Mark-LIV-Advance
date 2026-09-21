import os
import time
from pathlib import Path
from urllib.parse import quote
from difflib import SequenceMatcher

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    import pyperclip
except Exception:
    pyperclip = None

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

try:
    import psutil
except Exception:
    psutil = None


def _clean_phone(phone):
    return "".join(c for c in (phone or "") if c.isdigit())


def _open_desktop():
    try:
        os.startfile("whatsapp:")
        return True
    except Exception:
        return False


def _is_native_whatsapp_window(win) -> bool:
    """Only allow automation against the installed WhatsApp Windows process.

    A browser window can have 'WhatsApp' in its title when WhatsApp Web is open.
    Never type into or click a browser during a native WhatsApp automation task.
    """
    if not psutil:
        return False
    try:
        pid = int(win.process_id())
        proc = psutil.Process(pid)
        name = str(proc.name() or "").casefold()
        exe = str(proc.exe() or "").casefold()
        return "whatsapp" in name or "whatsapp" in Path(exe).name.casefold()
    except Exception:
        return False


def _find_whatsapp_window(timeout=12.0):
    if not Desktop:
        return None
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            for win in Desktop(backend="uia").windows():
                try:
                    if not _is_native_whatsapp_window(win):
                        continue
                    title = (win.window_text() or "").strip().lower()
                    cls = (getattr(win, "class_name", lambda: "")() or "").lower()
                    if "whatsapp" in title or "whatsapp" in cls:
                        return win

                    # After a call ends, the native WhatsApp window can change
                    # its title/class and expose neither the app name nor the
                    # chat name through UIA. The process check above is still
                    # authoritative, so a visible top-level WhatsApp process
                    # window is also a valid target.
                    if _is_native_whatsapp_window(win):
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
    time.sleep(0.3)
    return win


def _get_edits(win):
    try:
        return win.descendants(control_type="Edit")
    except Exception:
        return []


def _set_edit_text(control, text):
    try:
        control.click_input()
        time.sleep(0.15)
        control.set_edit_text(text)
        return True
    except Exception:
        return False


def _norm_contact(value):
    return " ".join(str(value or "").casefold().split()).strip()


def _contact_match_score(candidate: str, target: str) -> int:
    candidate_n = _norm_contact(candidate)
    target_n = _norm_contact(target)
    if not candidate_n or not target_n:
        return -1
    if candidate_n == target_n:
        return 100
    if candidate_n.startswith(target_n + " "):
        return 92
    if target_n.startswith(candidate_n + " "):
        return 88
    target_tokens = set(target_n.split())
    candidate_tokens = set(candidate_n.split())
    overlap = len(target_tokens & candidate_tokens)
    ratio = SequenceMatcher(None, candidate_n, target_n).ratio()
    if overlap:
        return 70 + min(15, overlap * 5) + int(ratio * 10)
    if ratio >= 0.72:
        return 60 + int(ratio * 20)
    return -1


def _click_search_and_find(contact):
    """Open a contact in the native WhatsApp app without browser/global-keyboard fallback."""
    win = _focus_whatsapp(8)
    if not win or not _is_native_whatsapp_window(win):
        return False, "The native WhatsApp desktop window was not found."

    target = str(contact or "").strip()
    if not target:
        return False, "No WhatsApp contact was provided."

    search = None
    try:
        for edit in _get_edits(win):
            text_value = (edit.window_text() or "").casefold()
            aid = (getattr(edit, "automation_id", lambda: "")() or "").casefold()
            if "search" in text_value or "search" in aid:
                search = edit
                break
    except Exception:
        search = None

    if search is None:
        return False, "WhatsApp's native search box was not exposed to Windows UI Automation."

    if not _set_edit_text(search, target):
        return False, "Could not enter the contact into WhatsApp's native search box."

    time.sleep(1.2)

    candidates = []
    try:
        controls = win.descendants()
    except Exception:
        controls = []

    for control in controls:
        try:
            control_type = str(control.element_info.control_type or "").casefold()
            if control_type not in {"listitem", "treeitem", "dataitem", "text", "button"}:
                continue
            text_value = (control.window_text() or "").strip()
            if not text_value:
                continue
            score = _contact_match_score(text_value, target)
            if score >= 70:
                candidates.append((score, text_value, control))
        except Exception:
            continue

    # Prefer actual row/item controls over a Text/Button child inside some
    # unrelated part of the chat. A clicked list item is our native proof that
    # the WhatsApp search result matched the requested contact.
    type_bonus = {
        "listitem": 30,
        "treeitem": 28,
        "dataitem": 26,
        "button": 8,
        "text": 0,
    }
    candidates.sort(
        key=lambda item: (
            -(item[0] + type_bonus.get(
                str(item[2].element_info.control_type or "").casefold(),
                0,
            )),
            -item[0],
            len(item[1]),
        )
    )

    for _, selected_name, control in candidates:
        control_type = str(
            control.element_info.control_type or ""
        ).casefold()
        try:
            try:
                control.invoke()
            except Exception:
                control.click_input()

            # On some WhatsApp builds invoke() only highlights the result.
            # If the native search box still contains the query, press Enter
            # through that same UIA control rather than sending a global key to
            # whatever window happens to be active.
            time.sleep(0.45)
            try:
                search_text = (search.window_text() or "").strip()
            except Exception:
                search_text = ""
            if _norm_contact(search_text) == _norm_contact(target):
                try:
                    search.set_focus()
                    search.type_keys("{ENTER}")
                except Exception:
                    pass

            time.sleep(1.2)
            return True, selected_name
        except Exception:
            continue

    return False, f"No native WhatsApp search result matched '{target}'."


def _focus_message_box(win):
    """Focus the actual chat composer, not the search field."""
    if not pyautogui:
        return False

    # First try UI Automation controls whose accessible name identifies the composer.
    try:
        edits = _get_edits(win)
        for edit in reversed(edits):
            try:
                text = (edit.window_text() or "").lower()
                aid = (getattr(edit, "automation_id", lambda: "")() or "").lower()
                combined = text + " " + aid
                if any(x in combined for x in ("type a message", "message", "compose", "write a message")):
                    edit.click_input()
                    time.sleep(0.2)
                    return True
            except Exception:
                continue
    except Exception:
        pass

    # The current chat composer is at the bottom of the WhatsApp window.
    # Clicking its center avoids accidentally typing into the contact search box.
    try:
        rect = win.rectangle()
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width > 500 and height > 400:
            x = rect.left + int(width * 0.70)
            y = rect.bottom - max(65, int(height * 0.075))
            pyautogui.click(x, y)
            time.sleep(0.3)
            return True
    except Exception:
        pass

    return False


def _type_and_send_message(win, message):
    """Use clipboard paste because it works reliably with WhatsApp's contenteditable composer."""
    if not pyautogui:
        return False, "pyautogui is not installed."

    if not _focus_message_box(win):
        return False, "Could not focus the WhatsApp message box."

    try:
        if pyperclip:
            old_clipboard = None
            try:
                old_clipboard = pyperclip.paste()
            except Exception:
                pass
            pyperclip.copy(message)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.25)
            pyautogui.press("enter")
            time.sleep(1.2)
            if old_clipboard is not None:
                try:
                    pyperclip.copy(old_clipboard)
                except Exception:
                    pass
            return True, ""

        pyautogui.write(message, interval=0.03)
        pyautogui.press("enter")
        time.sleep(1.2)
        return True, ""
    except Exception as e:
        return False, str(e)


def _verify_native_chat_target(win, contact: str) -> bool:
    """Verify the native WhatsApp chat actually shows the requested contact."""
    target = " ".join(str(contact or "").casefold().split()).strip()
    if not target:
        return False

    try:
        controls = win.descendants()
    except Exception:
        controls = []

    candidates = []
    try:
        title = (win.window_text() or "").strip()
        if title:
            candidates.append(title)
    except Exception:
        pass

    for control in controls:
        try:
            control_type = str(
                control.element_info.control_type or ""
            ).casefold()
            if control_type not in {"text", "button", "listitem"}:
                continue
            text = (control.window_text() or "").strip()
            if text:
                candidates.append(text)
        except Exception:
            continue

    best_score = -1
    for value in candidates:
        score = _contact_match_score(value, contact)
        if score > best_score:
            best_score = score

    # A short caller name such as "Malu" is allowed to match the actual
    # WhatsApp display name "Malu Chechi", but an unrelated chat is not.
    return best_score >= 70


def _send_message_desktop(contact, message):
    if not pyautogui:
        return False, "pyautogui is not installed."
    if not _open_desktop():
        return False, "Could not launch the installed WhatsApp desktop app."

    win = _focus_whatsapp(12)
    if not win:
        return False, "WhatsApp opened, but its desktop window was not detected."

    # Use the active native chat when it already matches the requested contact;
    # otherwise search for the contact before typing anything.
    if _verify_native_chat_target(win, contact):
        ok, error = _type_and_send_message(win, message)
        if not ok:
            return False, error
        return True, ""

    ok, selected_name_or_error = _click_search_and_find(contact)
    if not ok:
        return False, selected_name_or_error

    selected_name = str(selected_name_or_error or "").strip()

    win = _focus_whatsapp(5)
    if not win:
        return False, "WhatsApp chat opened, but its window disappeared."

    # Some current WhatsApp builds do not expose the selected chat header to
    # UI Automation, so a second UIA scan can falsely report failure even though
    # the native search row that was just clicked matched the contact. Only skip
    # the second verification when the clicked native result itself is a strong
    # contact match; never bypass the process/native-window check.
    selected_score = _contact_match_score(selected_name, contact)
    if selected_score < 70:
        return (
            False,
            f"WhatsApp selected '{selected_name or 'an unknown result'}', "
            f"which does not match '{contact}'. No message was typed or sent."
        )

    if not _verify_native_chat_target(win, contact) and selected_score < 88:
        return (
            False,
            f"Could not verify the native WhatsApp chat for '{contact}'. "
            "No message was typed or sent."
        )

    ok, error = _type_and_send_message(win, message)
    if not ok:
        return False, error
    return True, ""


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


def whatsapp_advance(
    action,
    contact="",
    phone="",
    message="",
):
    """Open WhatsApp or send a message through the native Windows app."""
    action = (action or "").lower().strip()

    if action in ("open", "open_whatsapp"):
        return (
            "Opened the WhatsApp desktop app."
            if _open_desktop()
            else "Could not open the WhatsApp desktop app."
        )

    if action in (
        "prepare_message",
        "message",
        "send",
        "send_message",
        "send_confirmed",
        "confirm_and_send",
    ):
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

    return (
        "Unknown WhatsApp action. Use open_whatsapp or message/send "
        "to work with WhatsApp chats."
    )


TOOL = {
    "name": "whatsapp_advance",
    "description": (
        "WINDOWS WHATSAPP DESKTOP ONLY. Use this tool to open the native "
        "WhatsApp desktop app and send WhatsApp messages."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "open_whatsapp | message | send",
            },
            "contact": {
                "type": "STRING",
                "description": "WhatsApp contact name",
            },
            "phone": {
                "type": "STRING",
                "description": "International phone number",
            },
            "message": {
                "type": "STRING",
                "description": "Message text",
            },
        },
        "required": ["action"],
    },
    "handler": whatsapp_advance,
}
