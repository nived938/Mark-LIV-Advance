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
    import cv2
except Exception:
    cv2 = None

try:
    from PIL import Image
except Exception:
    Image = None

_CAMERA_URI = "microsoft.windows.camera:"


def _find_camera():
    if not Desktop:
        return None
    try:
        for win in Desktop(backend="uia").windows():
            try:
                if "camera" in (win.window_text() or "").lower():
                    return win
            except Exception:
                pass
    except Exception:
        pass
    return None


def _open_camera():
    try:
        os.startfile(_CAMERA_URI)
        # Never wait on or manage the Camera process. It must outlive the JARVIS
        # response and stay open until the user explicitly asks to close it.
        time.sleep(2.0)
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
    return [d for d in (home / "Pictures" / "Camera Roll", home / "Pictures") if d.exists()]


def _photo_files():
    exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".heic", ".heif", ".tif", ".tiff"}
    result = []
    for directory in _pictures_dirs():
        try:
            result.extend(p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in exts)
        except Exception:
            pass
    return result


def _newest_photo(before_names):
    candidates = [p for p in _photo_files() if p.name not in before_names]
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def _normalise_photo(photo):
    if not photo:
        return None
    if Image:
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
            print(f"[Camera] Pillow conversion failed: {e}")
    # HEIC/HEIF may not be supported by Pillow. Try ImageMagick if installed.
    for command in ("magick", "convert"):
        try:
            found = subprocess.run(
                ["where", command], capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if found.returncode != 0:
                continue
            out = photo.with_name(photo.stem + "_JARVIS.jpg")
            result = subprocess.run(
                [command, str(photo), str(out)], capture_output=True,
                text=True, timeout=20,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0 and out.exists() and out.stat().st_size > 10_000:
                return out
        except Exception:
            pass
    return None


def _fallback_camera_photo():
    """Capture from the physical webcam as JPEG if Windows Camera used an
    unsupported codec. This is a camera photo, never a desktop screenshot."""
    if cv2 is None:
        return None
    directory = Path.home() / "Pictures" / "Camera Roll"
    directory.mkdir(parents=True, exist_ok=True)
    out = directory / f"JARVIS_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
    for index in range(6):
        cap = None
        try:
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                continue
            for _ in range(8):
                cap.read()
            ok, frame = cap.read()
            if ok and frame is not None and cv2.imwrite(
                str(out), frame, [cv2.IMWRITE_JPEG_QUALITY, 95]
            ) and out.exists() and out.stat().st_size > 10_000:
                return out
        except Exception as e:
            print(f"[Camera] fallback index {index}: {e}")
        finally:
            if cap is not None:
                try:
                    cap.release()
                except Exception:
                    pass
    return None


def _take_picture():
    win = _focus_camera()
    if not win:
        ok, error = _open_camera()
        if not ok:
            return False, f"Could not open Windows Camera: {error}"
        deadline = time.monotonic() + 5.0
        while time.monotonic() < deadline:
            win = _focus_camera()
            if win:
                break
            time.sleep(0.25)
    if not win:
        return False, "Windows Camera is open, but its shutter could not be located."

    before = {p.name for p in _photo_files()}
    names = {"take photo", "take picture", "photo", "capture", "take photo button", "take picture button"}
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
                pass
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

    deadline = time.monotonic() + 12.0
    photo = None
    while time.monotonic() < deadline:
        photo = _newest_photo(before)
        if photo:
            try:
                size1 = photo.stat().st_size
                if size1 > 10_000:
                    time.sleep(0.4)
                    if photo.exists() and photo.stat().st_size == size1:
                        break
            except Exception:
                pass
        time.sleep(0.25)

    if photo:
        normalised = _normalise_photo(photo)
        if normalised:
            return True, f"Picture saved as {normalised}"

    # If the Windows Camera codec is unsupported, capture a JPEG from the same
    # physical webcam. The Windows Camera window is deliberately left open.
    fallback = _fallback_camera_photo()
    if fallback:
        return True, f"Picture saved as {fallback}"
    return False, "The Camera shutter was activated, but no readable JPEG photo could be created."


def _close_camera():
    try:
        subprocess.run(
            ["taskkill", "/IM", "WindowsCamera.exe", "/T", "/F"],
            capture_output=True, text=True, timeout=5,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return "Closed the Windows Camera app."
    except Exception as e:
        return f"Could not close Windows Camera: {e}"


def camera_advance(action: str):
    action = (action or "").lower().strip()
    if action in ("open", "open_camera", "start"):
        ok, error = _open_camera()
        return (
            "Opened the Windows Camera app. It will stay open until you explicitly tell me to close the camera."
            if ok else f"Could not open Windows Camera: {error}"
        )
    if action in ("take_picture", "take_photo", "capture", "photo"):
        ok, result = _take_picture()
        return f"{result}. The Windows Camera app remains open." if ok else f"Could not take a picture: {result}"
    if action in ("close", "close_camera", "stop", "turn_off"):
        return _close_camera()
    return "Unknown camera action. Use open_camera, take_picture, or close_camera."


TOOL = {
    "name": "camera_advance",
    "description": (
        "Control the REAL WINDOWS CAMERA APP. For open_camera, launch Microsoft Windows Camera and KEEP IT OPEN; never close it because JARVIS starts speaking or a turn ends. For take_picture, use the real Camera shutter, wait for the file to finish writing, and create a standard readable JPEG. If Windows uses unsupported HEIC/HEIF, fall back to a JPEG from the physical webcam. NEVER use a screen screenshot as a camera photo. Only close Camera when the user explicitly asks to close/stop/turn off camera."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open_camera, take_picture, or close_camera"}
        },
        "required": ["action"],
    },
    "handler": camera_advance,
}
