from pathlib import Path
import shutil
import os
import string

# Read-only search roots. The user explicitly asked for full-PC search, so
# available Windows drives are included in addition to the common project roots.
HOME = Path.home()
BASE_ROOTS = [HOME, Path("G:/Coding"), Path("G:/Projects")]
MARKERS = ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "uv.lock", "main.py", "app.py", "run.py", "manage.py")
SKIP_DIRS = {"$recycle.bin", "system volume information", "node_modules", ".git", "__pycache__", ".venv", "venv"}


def _available_roots():
    roots = []
    seen = set()
    for root in BASE_ROOTS:
        try:
            root = root.resolve()
            if root.exists() and str(root).lower() not in seen:
                roots.append(root)
                seen.add(str(root).lower())
        except Exception:
            pass
    if os.name == "nt":
        for letter in string.ascii_uppercase:
            root = Path(f"{letter}:\\")
            try:
                if root.exists() and str(root).lower() not in seen:
                    roots.append(root)
                    seen.add(str(root).lower())
            except Exception:
                pass
    return roots


def _safe(path):
    try:
        p = Path(path).expanduser().resolve()
        return any(p == r.resolve() or p.is_relative_to(r.resolve()) for r in _available_roots())
    except Exception:
        return False


def _is_project(folder):
    try:
        return any((folder / marker).exists() for marker in MARKERS)
    except Exception:
        return False


def _iter_paths(base):
    """Walk without crashing on inaccessible Windows directories."""
    try:
        for current, dirs, files in os.walk(base, topdown=True, onerror=lambda e: None):
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
            current_path = Path(current)
            yield current_path, dirs, files
    except Exception:
        return


def file_search_advance(query: str, root: str = "", extension: str = "", limit: int = 30):
    q = (query or "").lower().strip()
    ext = (extension or "").lower().strip()
    max_results = max(1, min(int(limit or 30), 100))

    # If a root is supplied, search it. Otherwise search all available drives.
    if root:
        base = Path(root).expanduser()
        if not _safe(base):
            return "Access denied: the requested search root is outside the available local drives."
        roots = [base.resolve()]
    else:
        roots = _available_roots()

    results = []
    seen = set()
    try:
        for base in roots:
            for folder, dirs, files in _iter_paths(base):
                folder_lower = str(folder).lower()
                # Project-name queries should match the directory itself.
                if _is_project(folder) and (not q or q in folder.name.lower() or q in folder_lower or q in "python project"):
                    key = str(folder).lower()
                    if key not in seen:
                        results.append(f"[PYTHON PROJECT] {folder}")
                        seen.add(key)
                        if len(results) >= max_results:
                            return "\\n".join(results)

                for name in files:
                    if ext and Path(name).suffix.lower() != (ext if ext.startswith(".") else "." + ext):
                        continue
                    full = folder / name
                    if q and q not in name.lower() and q not in folder_lower:
                        continue
                    key = str(full).lower()
                    if key in seen:
                        continue
                    results.append(str(full))
                    seen.add(key)
                    if len(results) >= max_results:
                        return "\\n".join(results)
        return "\\n".join(results) if results else "No matching files or projects found on the available drives."
    except Exception as e:
        return f"File search failed: {e}"


def file_manage_advance(action: str, source: str, destination: str = ""):
    if not _safe(source):
        return "Access denied: source is outside the available local drives."
    try:
        src = Path(source).expanduser()
        if action == "open":
            os.startfile(src)
            return f"Opened {src}."
        if action == "copy":
            if not destination or not _safe(destination):
                return "A safe destination is required."
            shutil.copy2(src, Path(destination).expanduser())
            return f"Copied {src} to {destination}."
        if action == "move":
            if not destination or not _safe(destination):
                return "A safe destination is required."
            shutil.move(str(src), destination)
            return f"Moved {src} to {destination}."
        if action == "rename":
            if not destination or not _safe(destination):
                return "A safe destination is required."
            src.rename(destination)
            return f"Renamed {src} to {destination}."
        if action == "delete":
            return "REQUIRES_CONFIRMATION: delete the requested file."
        return "Unknown action. Use open, copy, move, rename, or delete."
    except Exception as e:
        return f"File operation failed: {e}"


TOOL = {
    "name": "file_search_advance",
    "description": "REAL LOCAL FILE SEARCH. MUST be called for requests such as 'find my project', 'find a folder', 'search my PC', or 'find files'. Searches available Windows drives by default, including G:, and can search a supplied root. For Mark-LIV-Advance, use query='Mark-LIV-Advance' and do not assume it is under the user's home directory. This tool is read-only for searches.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "File, folder, project, or text to find"},
            "root": {"type": "STRING", "description": "Optional drive/folder root; omit to search all available Windows drives"},
            "extension": {"type": "STRING", "description": "Optional extension such as py or pdf"},
            "limit": {"type": "INTEGER", "description": "Maximum results"},
        },
        "required": ["query"],
    },
    "handler": file_search_advance,
}
