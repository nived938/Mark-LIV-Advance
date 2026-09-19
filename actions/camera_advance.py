import os
import time
from pathlib import Path

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None


def _find_camera():
    if not Desktop:
        return None
    try:
        for win in Desktop(backend="uia").windows():
            try:
                title = (win.window_text() or "").lower()
                if "camera" in title:
                    return win
            except Exception:
                continue
    except Exception:
        pass
    return None


def _open_camera():
    try:
        os.startfile("microsoft.windows.camera:")
        time.sleep(3)
        return True, ""
    except Exception as e:
        return False, str(e)


def _focus_camera():
    win = _find_camera()
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


def _take_picture():
    win = _focus_camera()
    if not win:
        ok, error = _open_camera()
        if not ok:
            return False, f"Could not open Windows Camera: {error}"
        win = _focus_camera()

    if not win:
        return False, "Windows Camera opened, but its window could not be found."

    # Prefer the actual Camera shutter button exposed by Windows UI Automation.
    names = {
        "take photo", "take picture", "photo", "capture",
        "take photo button", "take picture button"
    }

    try:
        controls = win.descendants()
        exact = []
        for control in controls:
            try:
                name = (control.window_text() or "").strip().lower()
                aid = (getattr(control, "automation_id", lambda: "")() or "").strip().lower()
                if name in names or aid in names:
                    exact.append(control)
            except Exception:
                continue

        for control in exact:
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
    except Exception:
        pass

    # Camera's normal keyboard shortcut is Space when the Camera app has focus.
    if pyautogui:
        try:
            pyautogui.press("space")
            time.sleep(2)
            return True, ""
        except Exception as e:
            return False, f"Could not press the Camera shutter: {e}"

    return False, "Camera shutter control was not found."


def camera_advance(action: str):
    action = (action or "").lower().strip()

    if action in ("open", "open_camera", "start"):
        ok, error = _open_camera()
        return "Opened the Windows Camera app. It will stay open until you close it." if ok else f"Could not open Windows Camera: {error}"

    if action in ("take_picture", "take_photo", "capture", "photo"):
        ok, error = _take_picture()
        if ok:
            return "Took a picture with the Windows Camera app. The Camera app remains open."
        return f"Could not take a picture: {error}"

    return "Unknown camera action. Use open_camera or take_picture."


TOOL = {
    "name": "camera_advance",
    "description": (
        "Control the REAL WINDOWS CAMERA APP, not a JARVIS screenshot. "
        "For 'open camera', launch Microsoft Windows Camera and leave it open; never close it automatically. "
        "For 'take a picture' or 'take a photo', use the Camera app's real shutter control or Space key to take an actual camera photo. "
        "Do NOT use screen_control_advance for camera photos because that only captures a screenshot."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "open_camera or take_picture"
            }
        },
        "required": ["action"],
    },
    "handler": camera_advance,
}
