from __future__ import annotations

import time
from pathlib import Path

try:
    from PyQt6.QtWidgets import QApplication
except Exception:
    QApplication = None


def _jarvis_window():
    """Return JARVIS's real MainWindow so camera stays inside the app."""
    if QApplication is None:
        return None
    try:
        app = QApplication.instance()
        if app is None:
            return None
        for widget in app.topLevelWidgets():
            if hasattr(widget, "start_camera_stream") and hasattr(widget, "capture_camera_photo"):
                return widget
    except Exception as e:
        print(f"[Camera] Could not find JARVIS window: {e}")
    return None


def _open_camera():
    win = _jarvis_window()
    if win is None:
        return False, "JARVIS UI is not available."
    try:
        win.start_camera_stream()
        return True, "Embedded camera feed opened inside JARVIS."
    except Exception as e:
        return False, str(e)


def _take_picture():
    win = _jarvis_window()
    if win is None:
        return False, "JARVIS UI is not available."

    try:
        # Make sure the embedded stream is running.
        win.start_camera_stream()
    except Exception:
        pass

    # Give the stream a moment to deliver a fresh frame.
    deadline = time.monotonic() + 3.0
    path = None
    while time.monotonic() < deadline:
        try:
            path = win.capture_camera_photo()
        except Exception as e:
            print(f"[Camera] Capture error: {e}")
            path = None
        if path:
            return True, f"Picture saved as {path}"
        time.sleep(0.10)

    return False, "The embedded camera is open, but no camera frame was available."


def _close_camera():
    win = _jarvis_window()
    if win is None:
        return "JARVIS UI is not available."
    try:
        win.stop_camera_stream()
        return "Closed the embedded camera feed in JARVIS."
    except Exception as e:
        return f"Could not close the embedded camera: {e}"


def camera_advance(action: str):
    action = (action or "").lower().strip()

    if action in ("open", "open_camera", "start"):
        ok, result = _open_camera()
        return result if ok else f"Could not open camera: {result}"

    if action in ("take_picture", "take_photo", "capture", "photo"):
        ok, result = _take_picture()
        return result if ok else f"Could not take a picture: {result}"

    if action in ("close", "close_camera", "stop", "turn_off"):
        return _close_camera()

    return "Unknown camera action. Use open_camera, take_picture, or close_camera."


TOOL = {
    "name": "camera_advance",
    "description": (
        "Control JARVIS'S EMBEDDED CAMERA, NOT Windows Camera. "
        "For open_camera, show the live physical webcam feed INSIDE the JARVIS application "
        "and keep it open until explicitly closed. For take_picture, save the current embedded "
        "camera frame as a real JPEG photo in Pictures/Camera Roll. Do not launch any external "
        "Camera application and do not use screen_process or file_controller for the photo. "
        "For close_camera, stop and hide the embedded JARVIS camera feed."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "open_camera, take_picture, or close_camera",
            }
        },
        "required": ["action"],
    },
    "handler": camera_advance,
}
