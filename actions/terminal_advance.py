import os
import subprocess
import platform


def terminal_advance(
    command: str,
    shell: str = "powershell",
    timeout: int = 30,
    visible: bool = False,
):
    command = (command or "").strip()
    if not command:
        return "No command supplied."

    shell_name = (shell or "powershell").lower().strip()
    visible = bool(visible)

    # Interactive commands such as "open PowerShell and run cd ..." need a
    # visible persistent console. A normal captured subprocess cannot show the
    # user a PowerShell window and its working directory would disappear when
    # the process exits.
    if visible:
        if shell_name in ("powershell", "pwsh"):
            try:
                subprocess.Popen(
                    [
                        "powershell.exe",
                        "-NoLogo",
                        "-NoExit",
                        "-Command",
                        command,
                    ],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                return f"Opened a visible PowerShell window and ran: {command}"
            except Exception as e:
                return f"Could not open visible PowerShell: {e}"

        try:
            subprocess.Popen(
                ["cmd.exe", "/k", command],
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
            return f"Opened a visible Command Prompt window and ran: {command}"
        except Exception as e:
            return f"Could not open visible Command Prompt: {e}"

    # Non-visible mode is for diagnostics/background developer commands where
    # JARVIS needs the output back in the conversation.
    if shell_name in ("powershell", "pwsh"):
        args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command]
    else:
        args = ["cmd.exe", "/d", "/s", "/c", command]

    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        result = subprocess.run(
            args,
            cwd=os.path.expanduser("~"),
            capture_output=True,
            text=True,
            timeout=max(1, min(int(timeout), 120)),
            creationflags=flags,
        )
        output = (result.stdout + ("\n" + result.stderr if result.stderr else "")).strip()
        return f"Exit code: {result.returncode}\n{output[-12000:]}"
    except subprocess.TimeoutExpired:
        return "Command timed out."
    except Exception as e:
        return f"Terminal error: {e}"


TOOL = {
    "name": "terminal_advance",
    "description": (
        "Run PowerShell or CMD commands. For a user request that explicitly says "
        "open PowerShell/CMD, show the terminal, or keep the terminal open after "
        "running a command, set visible=true. This creates a real visible console "
        "window and keeps it open. For diagnostics where JARVIS needs command output, "
        "leave visible=false so the output is returned to JARVIS. "
        "Example: user says 'open PowerShell and run cd G:/Coding/Mark-LIV-Advance' -> "
        "use shell='powershell', command='cd G:/Coding/Mark-LIV-Advance', visible=true."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {"type": "STRING", "description": "PowerShell or CMD command to execute"},
            "shell": {"type": "STRING", "description": "powershell or cmd"},
            "timeout": {"type": "INTEGER", "description": "Timeout in seconds, maximum 120"},
            "visible": {"type": "BOOLEAN", "description": "Set true for a visible persistent terminal window when explicitly requested by the user"},
        },
        "required": ["command"],
    },
    "handler": terminal_advance,
}
