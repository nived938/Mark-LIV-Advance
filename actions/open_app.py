import time
import subprocess
import platform
import shutil

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

_SYSTEM = platform.system()

_APP_ALIASES: dict[str, dict[str, str]] = {
    "chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "google chrome": {"Windows": "chrome", "Darwin": "Google Chrome", "Linux": "google-chrome"},
    "firefox": {"Windows": "firefox", "Darwin": "Firefox", "Linux": "firefox"},
    "edge": {"Windows": "msedge", "Darwin": "Microsoft Edge", "Linux": "microsoft-edge"},
    "brave": {"Windows": "brave", "Darwin": "Brave Browser", "Linux": "brave-browser"},
    "safari": {"Windows": "msedge", "Darwin": "Safari", "Linux": "firefox"},
    "opera": {"Windows": "opera", "Darwin": "Opera", "Linux": "opera"},
    "whatsapp": {"Windows": "WhatsApp", "Darwin": "WhatsApp", "Linux": "whatsapp"},
    "telegram": {"Windows": "Telegram", "Darwin": "Telegram", "Linux": "telegram"},
    "discord": {"Windows": "Discord", "Darwin": "Discord", "Linux": "discord"},
    "slack": {"Windows": "Slack", "Darwin": "Slack", "Linux": "slack"},
    "zoom": {"Windows": "Zoom", "Darwin": "zoom.us", "Linux": "zoom"},
    "teams": {"Windows": "msteams", "Darwin": "Microsoft Teams", "Linux": "teams"},
    "skype": {"Windows": "skype", "Darwin": "Skype", "Linux": "skype"},
    "signal": {"Windows": "signal", "Darwin": "Signal", "Linux": "signal"},
    "spotify": {"Windows": "Spotify", "Darwin": "Spotify", "Linux": "spotify"},
    "vlc": {"Windows": "vlc", "Darwin": "VLC", "Linux": "vlc"},
    "vscode": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "visual studio code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "code": {"Windows": "code", "Darwin": "Visual Studio Code", "Linux": "code"},
    "terminal": {"Windows": "wt", "Darwin": "Terminal", "Linux": "x-terminal-emulator"},
    "windows terminal": {"Windows": "wt", "Darwin": "Terminal", "Linux": "x-terminal-emulator"},
    "cmd": {"Windows": "cmd.exe", "Darwin": "Terminal", "Linux": "bash"},
    "command prompt": {"Windows": "cmd.exe", "Darwin": "Terminal", "Linux": "bash"},
    "powershell": {"Windows": "powershell.exe", "Darwin": "Terminal", "Linux": "bash"},
    "windows powershell": {"Windows": "powershell.exe", "Darwin": "Terminal", "Linux": "bash"},
    "postman": {"Windows": "Postman", "Darwin": "Postman", "Linux": "postman"},
    "figma": {"Windows": "Figma", "Darwin": "Figma", "Linux": "figma"},
    "blender": {"Windows": "blender", "Darwin": "Blender", "Linux": "blender"},
    "word": {"Windows": "winword", "Darwin": "Microsoft Word", "Linux": "libreoffice --writer"},
    "excel": {"Windows": "excel", "Darwin": "Microsoft Excel", "Linux": "libreoffice --calc"},
    "powerpoint": {"Windows": "powerpnt", "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "notepad": {"Windows": "notepad.exe", "Darwin": "TextEdit", "Linux": "gedit"},
    "explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "file explorer": {"Windows": "explorer.exe", "Darwin": "Finder", "Linux": "nautilus"},
    "task manager": {"Windows": "taskmgr.exe", "Darwin": "Activity Monitor", "Linux": "gnome-system-monitor"},
    "settings": {"Windows": "ms-settings:", "Darwin": "System Preferences", "Linux": "gnome-control-center"},
    "calculator": {"Windows": "calc.exe", "Darwin": "Calculator", "Linux": "gnome-calculator"},
    "paint": {"Windows": "mspaint.exe", "Darwin": "Preview", "Linux": "gimp"},
    "steam": {"Windows": "steam", "Darwin": "Steam", "Linux": "steam"},
}

def _normalize(raw: str) -> str:
    key = raw.lower().strip()
    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(_SYSTEM, raw)
    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(_SYSTEM, raw)
    return raw

def _focus_window(title_parts: tuple[str, ...], timeout: float = 5.0) -> bool:
    if not Desktop or _SYSTEM != "Windows":
        return False
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            for win in Desktop(backend="uia").windows():
                title = (win.window_text() or "").lower()
                if any(part.lower() in title for part in title_parts):
                    try:
                        win.restore()
                    except Exception:
                        pass
                    try:
                        win.set_focus()
                    except Exception:
                        pass
                    return True
        except Exception:
            pass
        time.sleep(0.25)
    return False

def _launch_windows(app_name: str) -> bool:
    low = app_name.lower().strip()

    # PowerShell needs special handling: launch a real console and then
    # explicitly focus its window before returning. Otherwise the next
    # computer/type tool can type into the JARVIS UI instead.
    if low in ("powershell.exe", "powershell", "pwsh", "pwsh.exe"):
        try:
            subprocess.Popen(
                ["powershell.exe", "-NoLogo"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return _focus_window(("windows powershell", "powershell"), timeout=7.0)
        except Exception as e:
            print(f"[open_app] PowerShell launch failed: {e}")

    # Command Prompt gets the same focus guarantee.
    if low in ("cmd.exe", "cmd", "command prompt"):
        try:
            subprocess.Popen(
                ["cmd.exe"],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return _focus_window(("command prompt", "cmd"), timeout=7.0)

        except Exception as e:
            print(f"[open_app] CMD launch failed: {e}")

    if shutil.which(app_name) or shutil.which(app_name.split(".")[0]):
        try:
            subprocess.Popen(
                app_name,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.5)
            # Focus common desktop apps when possible.
            _focus_window((app_name.replace(".exe", ""),), timeout=2.0)
            return True
        except Exception as e:
            print(f"[open_app] subprocess failed: {e}")

    if ":" in app_name:
        try:
            subprocess.Popen(f"start {app_name}", shell=True)
            time.sleep(1.5)
            return True
        except Exception:
            pass

    try:
        import pyautogui
        pyautogui.PAUSE = 0.1
        pyautogui.press("win")
        time.sleep(0.7)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.9)
        pyautogui.press("enter")
        time.sleep(2.5)
        _focus_window((app_name,), timeout=2.0)
        return True
    except Exception as e:
        print(f"[open_app] Start Menu search failed: {e}")

    return False

def _launch_macos(app_name: str) -> bool:
    try:
        result = subprocess.run(["open", "-a", app_name], capture_output=True, timeout=8)
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass
    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass
    return False

def _launch_linux(app_name: str) -> bool:
    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen([binary], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.0)
            return True
        except Exception:
            pass
    try:
        subprocess.run(["xdg-open", app_name], capture_output=True, timeout=5)
        return True
    except Exception:
        return False

_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin": _launch_macos,
    "Linux": _launch_linux,
}

def open_app(parameters=None, response=None, player=None, session_memory=None) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()
    if not app_name:
        return "No application name provided."

    launcher = _OS_LAUNCHERS.get(_SYSTEM)
    if launcher is None:
        return f"Unsupported operating system: {_SYSTEM}"

    normalized = _normalize(app_name)
    print(f"[open_app] Launching: '{app_name}' → '{normalized}' ({_SYSTEM})")
    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        if launcher(normalized):
            return f"Opened {app_name} and focused its window."
        if normalized.lower() != app_name.lower() and launcher(app_name):
            return f"Opened {app_name} and focused its window."
        return f"Could not confirm that {app_name} launched."
    except Exception as e:
        print(f"[open_app] Error: {e}")
        return f"Failed to open {app_name}: {e}"

TOOL = {
    "name": "open_app",
    "description": (
        "Opens and focuses an application on the computer. "
        "Use this whenever the user asks to open, launch, or start an app. "
        "On Windows, PowerShell and CMD are launched as real console windows "
        "and explicitly focused before returning, so a following keyboard "
        "type/press action goes into that terminal rather than the JARVIS chat. "
        "For a command such as 'cd G:/Coding/project', use terminal_advance "
        "when the user wants the command executed rather than merely typed."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "app_name": {"type": "STRING", "description": "Application name, e.g. PowerShell, Chrome, WhatsApp"},
        },
        "required": ["app_name"],
    },
    "handler": open_app,
}
