import os
import time
from pathlib import Path
import subprocess

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

try:
    from PIL import Image
except Exception:
    Image = None


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


def _pictures_dirs():
    home = Path.home()
    dirs = [home / "Pictures" / "Camera Roll", home / "Pictures"]
    return [d for d in dirs if d.exists()]


def _newest_photo(before_names):
    candidates = []
    for directory in _pictures_dirs():
        try:
            for p in directory.iterdir():
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic", ".heif"}:
                    if p.name not in before_names:
                        candidates.append(p)
        except Exception:
            continue
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _normalise_photo(photo):
    """Ensure the newly captured file is a real, readable JPEG.

    Some Windows camera/codec combinations can leave an image with a misleading
    extension or a format that the Photos app cannot decode. Re-encoding the
    completed capture through Pillow gives us a standard JPEG without touching
    the original until the replacement is successfully written.
    """
    if not photo or not Image:
        return photo
    try:
        with Image.open(photo) as img:
            img.load()
            rgb = img.convert("RGB")
        out = photo.with_name(photo.stem + "_JARVIS.jpg")
        rgb.save(out, "JPEG", quality=95, optimize=True)
        with Image.open(out) as check:
            check.verify()
        return out
    except Exception as e:
        print(f"[Camera] Photo normalisation skipped: {e}")
        return photo


def _take_picture():
    win = _focus_camera()
    if not win:
        ok, error = _open_camera()
        if not ok:
            return False, f"Could not open Windows Camera: {error}"
        win = _focus_camera()

    if not win:
        return False, "Windows Camera opened, but its window could not be found."

    before = set()
    for directory in _pictures_dirs():
        try:
            before.update(p.name for p in directory.iterdir() if p.is_file())
        except Exception:
            pass

    names = {
        "take photo", "take picture", "photo", "capture",
        "take photo button", "take picture button"
    }

    clicked = False
    try:
        for control in win.descendants():
            try:
                name = (control.window_text() or "").strip().lower()
                aid = (getattr(control, "automation_id", lambda: "")() or "").strip().lower()
                if name in names or aid in names:
                    try:
                        control.invoke()
                        clicked = True
                        break
                    except Exception:
                        try:
                            control.click_input()
                            clicked = True
                            break
                        except Exception:
                            pass
            except Exception:
                continue
    except Exception:
        pass

    if not clicked and pyautogui:
        try:
            pyautogui.press("space")
            clicked = True
        except Exception as e:
            return False, f"Could not activate the Camera shutter: {e}"

    if not clicked:
        return False, "Camera shutter control was not found. No picture was taken."

    # Give Windows Camera enough time to finish writing the image before we
    # report success or try to normalise the file.
    deadline = time.monotonic() + 8.0
    photo = None
    while time.monotonic() < deadline:
        photo = _newest_photo(before)
        if photo:
            try:
                if photo.stat().st_size > 10_000:
                    break
            except Exception:
                pass
        time.sleep(0.25)

    if not photo:
        return False, "The Camera shutter was activated, but no completed photo file appeared in Pictures."

    normalised = _normalise_photo(photo)
    return True, f"Picture saved as {normalised}"


def _close_camera():
    """Close only the real Windows Camera app, never JARVIS itself."""
    try:
        subprocess.run(
            ["taskkill", "/IM", "WindowsCamera.exe", "/T", "/F"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "Closed the Windows Camera app."
    except Exception as e:
        return f"Could not close Windows Camera: {e}"


def camera_advance(action: str):
    action = (action or "").lower().strip()

    if action in ("open", "open_camera", "start"):
        ok, error = _open_camera()
        return "Opened the Windows Camera app. It will stay open until you tell me to close the camera." if ok else f"Could not open Windows Camera: {error}"

    if action in ("take_picture", "take_photo", "capture", "photo"):
        ok, result = _take_picture()
        if ok:
            return f"{result}. The Windows Camera app remains open."
        return f"Could not take a picture: {result}"

    if action in ("close", "close_camera", "stop", "turn_off"):
        return _close_camera()

    return "Unknown camera action. Use open_camera, take_picture, or close_camera."


TOOL = {
    "name": "camera_advance",
    "description": (
        "Control the REAL WINDOWS CAMERA APP. Use this tool for 'open camera', "
        "'take a picture', 'take a photo', and 'close camera'. "
        "For open_camera, launch Microsoft Windows Camera and KEEP IT OPEN; never "
        "close it merely because JARVIS starts speaking. For take_picture, use "
        "the real Camera shutter, wait for the photo to finish writing, and ensure "
        "the saved result is a standard readable JPEG in Pictures. Do NOT use "
        "screen_process or a screenshot tool for camera photos. Only close the "
        "real Camera app when the user explicitly asks to close/stop/turn off camera."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "open_camera, take_picture, or close_camera"
            }
        },
        "required": ["action"],
    },
    "handler": camera_advance,
}
