"""Operating modes for J.A.R.V.I.S.

Normal:
    Existing behavior. No gaming optimization and normal Mark32 permission policy.

Gaming:
    Opens Steam and stops a conservative list of optional user background apps.
    It never targets Windows/system processes and never stops the J.A.R.V.I.S.
    process. Switching back to normal does not guess at relaunching applications.

Serious:
    Enables autonomous Mark32 permissions for user-requested operations. The OS
    still enforces its own ACL/UAC rules. The universal J.A.R.V.I.S. interrupt
    remains available.
"""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path

import psutil


MODES = ("normal", "gaming", "serious")

# Deliberately narrow: these are optional desktop/background apps commonly
# unrelated to an active game. Steam itself is not in this set.
DEFAULT_GAMING_PROCESSES = (
    "onedrive.exe",
    "google-drive.exe",
    "googledrivesync.exe",
    "dropbox.exe",
    "discord.exe",
    "spotify.exe",
    "slack.exe",
    "teams.exe",
    "ms-teams.exe",
    "zoom.exe",
)

# J.A.R.V.I.S. never terminates these even if a user customization accidentally
# puts a system process name into the stop list.
HARD_PROTECTED_PROCESSES = {
    "system",
    "system idle process",
    "registry",
    "smss.exe",
    "csrss.exe",
    "wininit.exe",
    "services.exe",
    "lsass.exe",
    "svchost.exe",
    "winlogon.exe",
    "explorer.exe",
    "dwm.exe",
    "audiodg.exe",
    "python.exe",
    "pythonw.exe",
}

ALIASES = {
    "default": "normal",
    "standard": "normal",
    "normal mode": "normal",
    "gaming mode": "gaming",
    "game mode": "gaming",
    "serious mode": "serious",
    "focus mode": "serious",
}


def _config_file() -> Path:
    return Path(__file__).resolve().parent.parent / "config" / "api_keys.json"


def _load() -> dict:
    path = _config_file()
    try:
        return __import__("json").loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: dict) -> None:
    path = _config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(__import__("json").dumps(data, indent=4), encoding="utf-8")


def normalize_mode(mode: str) -> str:
    value = str(mode or "").strip().lower()
    value = ALIASES.get(value, value)
    return value if value in MODES else ""


def current_mode() -> str:
    value = normalize_mode(_load().get("operating_mode", "normal"))
    return value or "normal"


def set_mode(mode: str) -> str:
    value = normalize_mode(mode)
    if not value:
        return f"Unknown operating mode: {mode}. Available: {', '.join(MODES)}"
    data = _load()
    data["operating_mode"] = value
    _save(data)
    return value


def mode_description(mode: str | None = None) -> str:
    value = normalize_mode(mode or current_mode()) or "normal"
    if value == "gaming":
        return (
            "Gaming mode: Steam is opened and a conservative set of optional "
            "background desktop apps can be stopped. Normal J.A.R.V.I.S. "
            "conversation remains available."
        )
    if value == "serious":
        return (
            "Serious mode: autonomous Mark32 permission checks are relaxed for "
            "user-requested operations. The operating system still enforces "
            "real permissions/UAC, and the universal interrupt remains available. "
            "Use a serious, concise, professional tone. Do not use friendly small "
            "talk, playful phrasing, emojis, casual filler, or unnecessary praise. "
            "State actions and results directly. Do not be rude or insulting."
        )
    return (
        "Normal mode: standard J.A.R.V.I.S. behavior. Gaming optimization and "
        "Serious-mode autonomous permissions are inactive. Use the normal "
        "friendly, helpful conversational tone."
    )


def prompt_context() -> str:
    mode = current_mode()
    return (
        "[OPERATING MODE]\n"
        f"Current mode: {mode.upper()}\n"
        f"{mode_description(mode)}\n"
        "The user can switch modes with mode_control. "
        "When Gaming mode is requested, use mode_control instead of manually "
        "launching Steam or killing arbitrary processes. "
        "When Serious mode is requested, you may carry out Mark32 operations "
        "without routine confirmation prompts. In Serious mode, keep responses "
        "concise, direct and professional rather than friendly or playful; do "
        "not use emojis or casual filler. Never claim success before the "
        "operation actually returns success.\n"
    )


def gaming_processes() -> list[str]:
    cfg = _load().get("gaming_mode", {})
    names = cfg.get("stop_processes") if isinstance(cfg, dict) else None
    if not isinstance(names, list):
        names = list(DEFAULT_GAMING_PROCESSES)
    out = []
    for value in names:
        name = str(value).strip().lower()
        if not name or name in HARD_PROTECTED_PROCESSES:
            continue
        out.append(name if name.endswith(".exe") else name + ".exe")
    return list(dict.fromkeys(out))


def stop_optional_background_apps() -> list[str]:
    if platform.system() != "Windows":
        return []
    current_pid = os.getpid()
    wanted = set(gaming_processes())
    stopped: list[str] = []

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            pid = int(proc.info.get("pid") or 0)
            name = str(proc.info.get("name") or "").strip().lower()
            if not pid or pid == current_pid or not name:
                continue
            if name in HARD_PROTECTED_PROCESSES or name not in wanted:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=1.5)
            except psutil.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
            stopped.append(f"{name} (PID {pid})")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
        except Exception:
            continue
    return stopped


def launch_steam() -> bool:
    try:
        if platform.system() == "Windows":
            os.startfile("steam://open/main")  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["steam"])
        return True
    except Exception:
        try:
            subprocess.Popen(["steam"])
            return True
        except Exception:
            return False


def activate_mode(mode: str) -> dict:
    value = normalize_mode(mode)
    if not value:
        return {
            "ok": False,
            "mode": current_mode(),
            "message": f"Unknown mode '{mode}'. Available: {', '.join(MODES)}",
        }

    before = current_mode()
    data = _load()
    data["operating_mode"] = value
    _save(data)

    result = {"ok": True, "mode": value, "previous": before, "stopped": [], "steam_opened": False}

    if value == "gaming":
        result["steam_opened"] = launch_steam()
        result["stopped"] = stop_optional_background_apps()

    return result
