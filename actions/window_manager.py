"""Deterministic Windows window placement controls."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import re

try:
    import psutil
except Exception:
    psutil = None


SW_RESTORE = 9
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010


def _monitors():
    user32 = ctypes.windll.user32
    result = []

    monitor_enum = ctypes.WINFUNCTYPE(
        wintypes.BOOL,
        wintypes.HMONITOR,
        wintypes.HDC,
        ctypes.POINTER(wintypes.RECT),
        wintypes.LPARAM,
    )

    @monitor_enum
    def callback(handle, _hdc, _rect, _lparam):
        info = wintypes.MONITORINFO()
        info.cbSize = ctypes.sizeof(info)
        if user32.GetMonitorInfoW(handle, ctypes.byref(info)):
            result.append({
                "handle": handle,
                "left": info.rcWork.left,
                "top": info.rcWork.top,
                "right": info.rcWork.right,
                "bottom": info.rcWork.bottom,
            })
        return True

    user32.EnumDisplayMonitors(0, 0, callback, 0)
    return result


def _windows():
    user32 = ctypes.windll.user32
    result = []
    enum_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @enum_type
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return True
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value.strip()
        if not title:
            return True

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process = ""
        try:
            if psutil is not None:
                process = psutil.Process(int(pid.value)).name()
        except Exception:
            pass

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True

        result.append({
            "hwnd": hwnd,
            "pid": int(pid.value),
            "title": title,
            "process": process,
            "rect": rect,
        })
        return True

    user32.EnumWindows(callback, 0)
    return result


def _match(window, app: str):
    needle = str(app or "").strip().casefold()
    if not needle:
        return False
    title = window["title"].casefold()
    process = window["process"].casefold()
    return needle in title or needle in process or (
        needle in {"chrome", "google chrome"} and "chrome" in process
    )


def move_to_monitor(app: str, target: int = 0, direction: str = "next") -> str:
    if not app:
        return "An app name is required."

    monitors = _monitors()
    if len(monitors) < 2:
        return "Only one display is currently detected."

    windows = [w for w in _windows() if _match(w, app)]
    if not windows:
        return f"No visible window matched '{app}'."

    user32 = ctypes.windll.user32
    hwnd = windows[0]["hwnd"]
    rect = windows[0]["rect"]
    width = max(200, rect.right - rect.left)
    height = max(120, rect.bottom - rect.top)
    cx = (rect.left + rect.right) // 2
    cy = (rect.top + rect.bottom) // 2

    current_idx = min(
        range(len(monitors)),
        key=lambda i: (
            max(monitors[i]["left"] - cx, 0, cx - monitors[i]["right"])
            + max(monitors[i]["top"] - cy, 0, cy - monitors[i]["bottom"])
        ),
    )

    if direction == "next":
        target_idx = (current_idx + 1) % len(monitors)
    else:
        try:
            target_idx = max(0, min(len(monitors) - 1, int(target) - 1))
        except Exception:
            return "Target monitor must be a number."

    dest = monitors[target_idx]
    x = dest["left"] + max(0, (dest["right"] - dest["left"] - width) // 2)
    y = dest["top"] + max(0, (dest["bottom"] - dest["top"] - height) // 2)

    user32.ShowWindow(hwnd, SW_RESTORE)
    ok = user32.SetWindowPos(
        hwnd, 0, x, y, width, height, SWP_NOZORDER | SWP_NOACTIVATE
    )
    if not ok:
        return f"Could not move '{windows[0]['title']}' to display {target_idx + 1}."

    return f"Moved {windows[0]['title']} to display {target_idx + 1}."


TOOL = {
    "name": "window_manager",
    "description": (
        "Move a visible Windows app window to another physical monitor. "
        "Use this for requests like 'put Chrome on the other screen'. "
        "This is deterministic Win32 control, not Gemini vision."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "move_to_monitor"},
            "app": {"type": "STRING", "description": "Application name such as Chrome, Edge, VS Code, or Teams."},
            "target": {"type": "INTEGER", "description": "Optional 1-based monitor number."},
            "direction": {"type": "STRING", "description": "next to move to the next monitor; target is used otherwise."},
        },
        "required": ["action", "app"],
    },
}


def window_manager(parameters=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action") or "move_to_monitor").strip().lower()
    if action != "move_to_monitor":
        return "Use action=move_to_monitor."
    return move_to_monitor(
        str(p.get("app") or ""),
        int(p.get("target") or 0),
        str(p.get("direction") or "next").strip().lower(),
    )
