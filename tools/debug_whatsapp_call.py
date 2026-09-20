"""Deep diagnostic for WhatsApp Desktop incoming-call detection.

Run this while another phone calls the Windows WhatsApp Desktop app.
This version checks UI Automation, Win32 top-level windows, and WhatsApp/WebView
processes. It never clicks anything.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import time

import psutil
from pywinauto import Desktop


CALL_WORDS = (
    "whatsapp", "accept", "answer", "decline", "reject", "ignore",
    "incoming", "calling", "call", "ringing",
)
PROC_WORDS = ("whatsapp", "webview", "msedgewebview", "teams")


def safe(fn, default=""):
    try:
        value = fn()
        return str(value or default)
    except Exception:
        return default


def enum_win32_windows():
    user32 = ctypes.windll.user32
    rows = []

    @wintypes.BOOL
    def callback(hwnd, _lparam):
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(max(length + 1, 256))
        user32.GetWindowTextW(hwnd, buf, len(buf))
        title = buf.value

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, len(class_buf))

        visible = bool(user32.IsWindowVisible(hwnd))
        if title or visible:
            rows.append((int(hwnd), int(pid.value), title, class_buf.value, visible))
        return True

    user32.EnumWindows(callback, 0)
    return rows


print("=" * 80)
print("WhatsApp incoming-call DEEP diagnostic")
print("1. Keep WhatsApp Desktop open.")
print("2. Start the WhatsApp call from another phone NOW.")
print("3. Let it ring for at least 8 seconds.")
print("4. This script scans for 30 seconds and DOES NOT click anything.")
print("=" * 80)
print()

printed = set()
end = time.time() + 30

# Print WhatsApp-related processes immediately and again during the call.
def print_processes():
    for p in psutil.process_iter(["pid", "name", "exe", "cmdline"]):
        try:
            name = str(p.info.get("name") or "")
            exe = str(p.info.get("exe") or "")
            cmd = " ".join(p.info.get("cmdline") or [])
            blob = f"{name} {exe} {cmd}".lower()
            if any(word in blob for word in PROC_WORDS):
                key = ("proc", p.pid)
                if key in printed:
                    continue
                printed.add(key)
                print("-" * 80)
                print("PROCESS MATCH")
                print("PID:", p.pid)
                print("NAME:", name)
                print("EXE:", exe)
                print("CMD:", cmd)
                print()
        except Exception:
            pass


print_processes()

while time.time() < end:
    print_processes()

    # ---------------- UI Automation ----------------
    try:
        windows = Desktop(backend="uia").windows(visible_only=False)
    except Exception as exc:
        print("UIA error:", repr(exc))
        windows = []

    for win in windows:
        pid = 0
        try:
            pid = win.process_id()
        except Exception:
            pass

        pname = ""
        try:
            pname = psutil.Process(pid).name()
        except Exception:
            pass

        title = safe(win.window_text)
        aid = safe(lambda: win.element_info.automation_id)
        ctype = safe(lambda: win.element_info.control_type)

        # Do not dump every normal application. Only dump candidates.
        head_blob = f"{title} {aid} {ctype} {pname}".lower()
        candidate = any(word in head_blob for word in CALL_WORDS)

        texts = []
        if candidate or "whatsapp" in pname.lower():
            try:
                for control in win.descendants():
                    txt = safe(control.window_text)
                    caid = safe(lambda c=control: c.automation_id())
                    ctype2 = safe(lambda c=control: c.element_info.control_type)
                    if txt or caid or ctype2:
                        texts.append((ctype2, txt, caid))
            except Exception:
                pass

            blob = " ".join(
                [title, aid, ctype, pname] +
                [x for row in texts for x in row]
            ).lower()
            if any(word in blob for word in CALL_WORDS):
                key = ("uia", pid, title, aid)
                if key not in printed:
                    printed.add(key)
                    print("=" * 80)
                    print("UIA CANDIDATE")
                    print("PID:", pid)
                    print("PROCESS:", pname)
                    print("WINDOW:", repr(title))
                    print("AUTOMATION_ID:", repr(aid))
                    print("CONTROL_TYPE:", repr(ctype))
                    print("CLASS:", safe(lambda: win.class_name()))
                    print("RECT:", safe(lambda: win.rectangle()))
                    print("CONTROLS:")
                    for ctype2, txt, caid in texts:
                        print(
                            f"  type={ctype2!r} text={txt!r} "
                            f"automation_id={caid!r}"
                        )
                    print()

    # ---------------- Win32 top-level windows ----------------
    for hwnd, pid, title, cls, visible in enum_win32_windows():
        try:
            pname = psutil.Process(pid).name()
        except Exception:
            pname = ""

        blob = f"{title} {cls} {pname}".lower()
        if not any(word in blob for word in CALL_WORDS):
            continue

        key = ("win32", hwnd)
        if key in printed:
            continue
        printed.add(key)

        print("=" * 80)
        print("WIN32 CANDIDATE")
        print("HWND:", hwnd)
        print("PID:", pid)
        print("PROCESS:", pname)
        print("VISIBLE:", visible)
        print("TITLE:", repr(title))
        print("CLASS:", repr(cls))
        print()

    time.sleep(0.5)

print("=" * 80)
print("Diagnostic finished.")
print("If you see PROCESS MATCH / UIA CANDIDATE / WIN32 CANDIDATE entries")
print("during the ringing period, paste those sections back to me.")
print("If there are NO WhatsApp process/window entries at all, the next")
print("step is Windows notification/toast detection rather than UIA.")
