"""Temporary diagnostic for WhatsApp Desktop incoming-call UI.

Run this while another phone is actively calling the Windows WhatsApp Desktop
app. It prints visible windows, process names, titles and UI Automation controls.
No clicks are performed.
"""
from __future__ import annotations

import sys
import time

try:
    import psutil
    from pywinauto import Desktop
except Exception as exc:
    print("Missing dependency:", exc)
    print("Install with: python -m pip install pywinauto psutil")
    raise SystemExit(1)


def safe(fn, default=""):
    try:
        value = fn()
        return str(value or default)
    except Exception:
        return default


print("WhatsApp incoming-call UI diagnostic")
print("Start the WhatsApp call NOW. This script will scan for 30 seconds.")
print()

end = time.time() + 30
seen = set()

while time.time() < end:
    try:
        windows = Desktop(backend="uia").windows(visible_only=True)
    except Exception as exc:
        print("UIA error:", repr(exc))
        time.sleep(1)
        continue

    for win in windows:
        try:
            pid = win.process_id()
        except Exception:
            pid = 0
        try:
            pname = psutil.Process(pid).name() if pid else ""
        except Exception:
            pname = ""

        title = safe(win.window_text)
        key = (pid, title)
        if key in seen:
            continue

        texts = []
        try:
            for control in win.descendants():
                txt = safe(control.window_text)
                aid = safe(lambda c=control: c.automation_id())
                ctype = safe(lambda c=control: c.element_info.control_type)
                if txt or aid or ctype:
                    texts.append((ctype, txt, aid))
        except Exception as exc:
            texts.append(("ERROR", repr(exc), ""))

        # Print WhatsApp-looking windows, call-related windows, or windows
        # containing Accept/Decline/Answer/Reject text.
        blob = " ".join([title, pname] + [x for row in texts for x in row]).lower()
        interesting = (
            "whatsapp" in blob
            or "accept" in blob
            or "answer" in blob
            or "decline" in blob
            or "reject" in blob
            or "incoming" in blob
            or "calling" in blob
        )
        if not interesting:
            continue

        seen.add(key)
        print("=" * 80)
        print("PID:", pid)
        print("PROCESS:", pname)
        print("WINDOW:", repr(title))
        print("CLASS:", safe(lambda: win.class_name()))
        print("RECT:", safe(lambda: win.rectangle()))
        print("CONTROLS:")
        for ctype, txt, aid in texts:
            print(f"  type={ctype!r} text={txt!r} automation_id={aid!r}")
        print()

    time.sleep(0.5)

print("Diagnostic finished.")
