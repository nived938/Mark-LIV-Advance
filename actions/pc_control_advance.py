import os
import platform
import subprocess
from pathlib import Path

def _run(cmd):
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=20, creationflags=flags)

def pc_control(action: str, target: str = ""):
    action = (action or "").lower().strip()
    target = (target or "").strip()

    if action == "open":
        if not target:
            return "No application or path was supplied."
        try:
            os.startfile(target)
            return f"Opened {target}."
        except Exception as e:
            return f"Could not open {target}: {e}"

    if action == "close":
        if not target:
            return "Provide a process name, for example chrome.exe."
        name = target if target.lower().endswith(".exe") else target + ".exe"
        r = _run(["taskkill", "/IM", name, "/T"])
        return r.stdout.strip() or r.stderr.strip() or f"Close command completed for {name}."

    if action == "lock":
        if platform.system() == "Windows":
            _run(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Windows is locked."
        return "Lock is currently implemented for Windows."

    if action == "restart":
        return "REQUIRES_CONFIRMATION: restart the computer with 'shutdown /r /t 0'."

    if action == "shutdown":
        return "REQUIRES_CONFIRMATION: shut down the computer with 'shutdown /s /t 0'."

    if action == "sleep":
        if platform.system() == "Windows":
            _run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
            return "Sleep requested."
        return "Sleep is currently implemented for Windows."

    if action == "info":
        return f"System: {platform.system()} {platform.release()} | Machine: {platform.machine()} | Python: {platform.python_version()}"

    return "Unknown action. Use open, close, lock, restart, shutdown, sleep, or info."

TOOL = {
    "name": "pc_control_advance",
    "description": "Control safe Windows PC actions: open/close applications, lock, sleep, system information, and confirmation-required shutdown/restart.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open, close, lock, restart, shutdown, sleep, or info"},
            "target": {"type": "STRING", "description": "Application, path, or process name when needed"},
        },
        "required": ["action"],
    },
    "handler": pc_control,
}
