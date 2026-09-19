import os
import subprocess

def terminal_advance(command: str, shell: str = "powershell", timeout: int = 30):
    command = (command or "").strip()
    if not command:
        return "No command supplied."

    # Keep interactive/shell persistence out of the voice tool. Every command gets
    # a bounded process and a captured result.
    if shell.lower() in ("powershell", "pwsh"):
        args = ["powershell", "-NoProfile", "-NonInteractive", "-Command", command]
    else:
        args = ["cmd", "/d", "/s", "/c", command]

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
    "description": "Run a bounded PowerShell or CMD command and return its output. Use it for diagnostics and developer tasks.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "command": {"type": "STRING", "description": "Command to execute"},
            "shell": {"type": "STRING", "description": "powershell or cmd"},
            "timeout": {"type": "INTEGER", "description": "Timeout in seconds, maximum 120"},
        },
        "required": ["command"],
    },
    "handler": terminal_advance,
}
