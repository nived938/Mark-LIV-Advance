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

    # After a WhatsApp call ends, the caller's chat is often already the active
    # native chat. Use it directly before performing another search. On builds
    # that hide the header from UIA, _click_search_and_find below still verifies
    # the selected native result before typing.
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


def _click_call_button(kind):
    win = _focus_whatsapp(8)
    if not win:
        return False, "WhatsApp window was not found."
    wanted = {"video", "video call", "videocall", "start video call"} if kind == "video" else {"voice call", "audio call", "start voice call", "start audio call"}
    try:
        for control in win.descendants():
            try:
                name = (control.window_text() or "").strip().lower()
                aid = (getattr(control, "automation_id", lambda: "")() or "").strip().lower()
                if name in wanted or aid in wanted:
                    try:
                        control.invoke()
                        time.sleep(2)
                        return True, ""
                    except Exception:
                        try:
                            control.click_input()
                            time.sleep(2)
                            return True, ""
                        except Exception:
                            pass
            except Exception:
                continue
    except Exception:
        pass
    return False, f"WhatsApp exposed no exact {kind} call control to Windows UI Automation."


_CALL_SPEAKER = None
_CALL_AUDIO_PREPARE = None

def set_call_speaker(callback) -> None:
    global _CALL_SPEAKER
    _CALL_SPEAKER = callback

def set_call_audio_prepare(callback) -> None:
    global _CALL_AUDIO_PREPARE
    _CALL_AUDIO_PREPARE = callback

def _speak_to_active_call(message: str, caller: str = "", end_after: bool = False):
    callback = _CALL_SPEAKER
    if not callable(callback):
        return False, "JARVIS call-speech bridge is not connected."
    try:
        return callback(str(message or "").strip(), caller, bool(end_after))
    except Exception as exc:
        return False, str(exc)


def whatsapp_advance(action, contact="", phone="", message="", confirmation="", speak=True, end_after=False):
    action = (action or "").lower().strip()

    if action in ("enable_busy_reply", "busy_mode_on", "auto_busy_on"):
        from actions.whatsapp_incoming_agent import set_busy_mode
        return set_busy_mode(True, message)

    if action in ("disable_busy_reply", "busy_mode_off", "auto_busy_off"):
        from actions.whatsapp_incoming_agent import set_busy_mode
        return set_busy_mode(False)

    if action in ("busy_status", "busy_mode_status"):
        from actions.whatsapp_incoming_agent import get_busy_mode
        enabled, busy_message = get_busy_mode()
        return (
            f"Automatic WhatsApp busy reply is {'enabled' if enabled else 'disabled'}. "
            f"Message: {busy_message}"
        )

    # Incoming-call controls are backed by the Windows WhatsApp native call
    # dialog. The detector keeps the pending caller in memory until the user
    # answers JARVIS. Never use WhatsApp Web for these actions.
    if action in ("accept_incoming", "answer_incoming"):
        from actions.whatsapp_incoming_agent import get_incoming_agent
        agent = get_incoming_agent()
        pending = agent.pending
        caller = pending.caller if pending else (contact or "the caller")

        # Prepare one-way Windows speech before accepting the call so WhatsApp
        # can inherit Stereo Mix/loopback as its communications microphone.
        try:
            from core.call_audio import ROUTER
            ROUTER.begin_one_way()
        except Exception:
            pass

        # Accept the real call first. JARVIS call speech is an optional second step.
        ok, error = agent.accept()
        if not ok:
            return f"Could not accept the incoming WhatsApp call from {caller}: {error}"

        if message and bool(speak):
            spoken, speech_error = _speak_to_active_call(
                message,
                caller,
                bool(end_after),
            )
            if spoken:
                return f"Accepted the WhatsApp call from {caller} and spoke the message."

            # Voice injection requires the optional virtual call-audio bridge.
            # Fall back to a normal WhatsApp message so the requested
            # notification is still delivered without pretending speech worked.
            try:
                agent.hang_up()
            except Exception:
                pass

            sent, send_error = False, ""
            try:
                sent, send_error = _send_message_desktop(caller, message)
            except Exception as exc:
                send_error = str(exc)

            if sent:
                return (
                    f"Accepted the WhatsApp call from {caller}, but JARVIS voice "
                    f"audio was unavailable; ended the call and sent the message in WhatsApp."
                )

            return (
                f"Accepted the WhatsApp call from {caller}, but could not speak "
                f"the message ({speech_error}) or send the WhatsApp fallback "
                f"message ({send_error})."
            )
        return f"Accepted the WhatsApp call from {caller}."

    if action in ("hang_up", "end_call", "disconnect_call"):
        from actions.whatsapp_incoming_agent import get_incoming_agent
        agent = get_incoming_agent()
        ok, error = agent.hang_up()
        try:
            from core.call_audio import ROUTER
            ROUTER.stop()
        except Exception:
            pass
        return "Ended the active WhatsApp call." if ok else f"Could not end the WhatsApp call: {error}"

    if action in ("decline_incoming", "reject_incoming"):
        from actions.whatsapp_incoming_agent import get_incoming_agent
        agent = get_incoming_agent()
        caller = agent.pending.caller if agent.pending else (contact or "the caller")
        ok, error = agent.decline()
        if not ok:
            return f"Could not decline the incoming WhatsApp call from {caller}: {error}"
        if message:
            sent, send_error = _send_message_desktop(caller, message)
            if not sent:
                return f"Declined the WhatsApp call from {caller}, but I could not send the follow-up message: {send_error}"
            return f"Declined the WhatsApp call from {caller} and sent the follow-up message."
        return f"Declined the WhatsApp call from {caller}."

    if action in ("call_and_message", "message_then_call"):
        target = contact or phone
        if not target:
            return "A WhatsApp contact name or phone number is required."
        if not message:
            return "The message to send is required."
        # Sending the message before starting the call is the reliable desktop
        # flow: once the native call window takes focus, the chat composer may
        # no longer be reachable. The call still follows immediately.
        if phone:
            sent, send_error = _send_by_phone(phone, message)
        else:
            sent, send_error = _send_message_desktop(contact, message)
        if not sent:
            return f"Could not send the message to {target}: {send_error}"
        if not _open_desktop():
            return f"Sent the message to {target}, but could not open WhatsApp for the call."
        win = _focus_whatsapp(10)
        if not win:
            return f"Sent the message to {target}, but the WhatsApp window was not detected for the call."
        if contact:
            ok, error = _click_search_and_find(contact)
            if not ok:
                return f"Sent the message to {target}, but could not open the chat for the call: {error}"
        kind = "voice"
        ok, error = _click_call_button(kind)
        if not ok:
            return f"Sent the message to {target}, but could not trigger the WhatsApp call: {error}"
        return f"Sent the message to {target} and started the WhatsApp voice call."

    if action in ("open", "open_whatsapp"):
        return "Opened the WhatsApp desktop app." if _open_desktop() else "Could not open the WhatsApp desktop app."

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

        # Plain "Call <person>" gets the requested JARVIS handoff introduction.
        # "and you don't need to speak" is represented by speak=false, which
        # leaves the phone's normal microphone/speaker untouched.
        call_intro = str(message or "").strip()
        if bool(speak) and not call_intro:
            call_intro = "Nived is back. I will transfer the conversation to Nived."

        if not _open_desktop():
            return "Could not open the WhatsApp desktop app."
        win = _focus_whatsapp(10)
        if not win:
            return "WhatsApp opened, but its Windows app window was not detected."
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

        # Start the real WhatsApp call first. JARVIS call speech is optional.
        # Without VB-CABLE/equivalent routing the call still works normally
        # through WhatsApp's own microphone and speakers.
        ok, error = _click_call_button(kind)
        if not ok:
            return f"Opened WhatsApp to {target}, but I could not trigger the {kind} call control. {error}"

        if bool(speak) and call_intro:
            spoken, speech_error = _speak_to_active_call(
                call_intro,
                target,
                False,
            )
            if not spoken:
                return (
                    f"Started the WhatsApp {kind} call to {target}, but JARVIS could not "
                    f"speak the introduction: {speech_error}"
                )
            return f"Started the WhatsApp {kind} call to {target} and spoke the introduction."
        return f"Started the WhatsApp {kind} call to {target}."

    return "Unknown action. Use open_whatsapp, message, send, call, or video_call."


TOOL = {
    "name": "whatsapp_advance",
    "description": (
        "WINDOWS WHATSAPP DESKTOP ONLY. Default tool for WhatsApp on this PC. "
        "Use it for messaging, voice/video calls, incoming-call controls, call introductions, and automatic busy-reply settings. "
        "Never use WhatsApp Web. Incoming calls are detected in the native Windows WhatsApp call dialog. "
        "enable_busy_reply enables persistent automatic handling: decline every incoming WhatsApp call and "
        "send the configured busy message to the caller; optional message sets the message. "
        "disable_busy_reply turns the setting off; busy_status reports it. "
        "For direct call/message actions, do not ask for confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open_whatsapp, message, send, call, video_call, accept_incoming, decline_incoming, hang_up, or call_and_message"},
            "contact": {"type": "STRING", "description": "WhatsApp contact name"},
            "phone": {"type": "STRING", "description": "International phone number"},
            "message": {"type": "STRING", "description": "Message text"},
            "confirmation": {"type": "STRING", "description": "Legacy field, not required"},
            "speak": {"type": "BOOLEAN", "description": "For calls: true to let JARVIS speak to the caller; false to stay silent."},
            "end_after": {"type": "BOOLEAN", "description": "For incoming-call speech: end the call after JARVIS finishes speaking."},
        },
        "required": ["action"],
    },
    "handler": whatsapp_advance,
}
