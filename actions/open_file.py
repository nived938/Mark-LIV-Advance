"""
open_file.py

Open files and folders using the operating system's
default application.
"""

import os
import platform
import subprocess
from pathlib import Path


_SYSTEM = platform.system()


def _find_path(path_string: str) -> Path | None:

    if not path_string:
        return None

    path_string = str(path_string).strip()

    # Remove quotes
    path_string = path_string.strip('"').strip("'")

    # Expand environment variables
    path_string = os.path.expandvars(path_string)

    # Expand ~
    path_string = os.path.expanduser(path_string)

    path = Path(path_string)

    # Direct path
    if path.exists():
        return path.resolve()

    # Relative to current directory
    current = Path.cwd() / path_string

    if current.exists():
        return current.resolve()

    # Common Windows directories
    if _SYSTEM == "Windows":

        home = Path.home()

        locations = [
            home / "Desktop",
            home / "Documents",
            home / "Downloads",
            home / "Pictures",
            home / "Videos",
            home / "Music",
        ]

        for location in locations:

            # Exact relative path
            candidate = location / path_string

            if candidate.exists():
                return candidate.resolve()

            # Search by filename
            candidate = location / Path(
                path_string
            ).name

            if candidate.exists():
                return candidate.resolve()

    return None


def _open_windows(path: Path) -> bool:

    try:

        os.startfile(str(path))

        return True

    except Exception as e:

        print(f"[open_file] Windows open failed: {e}")

    # Fallback
    try:

        subprocess.Popen(
            [
                "explorer.exe",
                str(path)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        return True

    except Exception as e:

        print(
            f"[open_file] Explorer fallback failed: {e}"
        )

    return False


def _open_macos(path: Path) -> bool:

    try:

        result = subprocess.run(
            [
                "open",
                str(path)
            ],
            capture_output=True,
            timeout=10,
        )

        return result.returncode == 0

    except Exception as e:

        print(f"[open_file] macOS open failed: {e}")

        return False


def _open_linux(path: Path) -> bool:

    try:

        result = subprocess.run(
            [
                "xdg-open",
                str(path)
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )

        return result.returncode == 0

    except Exception as e:

        print(f"[open_file] Linux open failed: {e}")

        return False


def open_file(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:

    parameters = parameters or {}

    path_string = (
        parameters.get("file_path")
        or parameters.get("path")
        or parameters.get("file")
        or parameters.get("filename")
        or ""
    )

    path_string = str(path_string).strip()

    if not path_string:

        return (
            "Please provide the file or folder you want me to open."
        )

    path = _find_path(path_string)

    if path is None:

        return (
            f"I could not find '{path_string}'. "
            "Please provide the full path or filename."
        )

    if _SYSTEM == "Windows":

        success = _open_windows(path)

    elif _SYSTEM == "Darwin":

        success = _open_macos(path)

    elif _SYSTEM == "Linux":

        success = _open_linux(path)

    else:

        return (
            f"Opening files is not supported on "
            f"{_SYSTEM}."
        )

    if success:

        if path.is_dir():

            return f"Opened folder: {path}"

        return f"Opened file: {path.name}"

    return (
        f"I could not open '{path}'. "
        "The operating system failed to launch it."
    )


TOOL = {
    "name": "open_file",
    "description": (
        "Opens a file or folder using the operating system's "
        "default application. Use this whenever the user asks "
        "to open a file, document, image, PDF, folder, project, "
        "or other filesystem item. Examples: 'open report.pdf', "
        "'open my Downloads folder', 'open test.py'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": (
                    "Path or filename of the file or folder to open. "
                    "Example: C:\\Users\\USER\\Downloads\\report.pdf"
                )
            }
        },
        "required": [
            "file_path"
        ]
    },
    "handler": open_file,
}