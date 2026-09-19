from pathlib import Path
import shutil
import os
import string

HOME = Path.home()
# Put common development locations first. This prevents C:\Users\...\Recent
# shortcuts from filling the result limit before a real project on G: is found.
PRIORITY_ROOTS = [Path("G:/Coding"), Path("G:/Projects"), HOME]
MARKERS = ("pyproject.toml", "requirements.txt", "setup.py", "Pipfile", "uv.lock", "main.py", "app.py", "run.py", "manage.py")
SKIP_DIRS = {"$recycle.bin", "system volume information", "node_modules", ".git", "__pycache__", ".venv", "venv"}


def _available_roots():
    roots, seen = [], set()
    candidates = list(PRIORITY_ROOTS)
    if os.name == "nt":
        candidates += [Path(f"{letter}:\\") for letter in string.ascii_uppercase]
    for root in candidates:
        try:
            root = root.resolve()
            key = str(root).lower()
            if root.exists() and key not in seen:
                roots.append(root)
                seen.add(key)
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


def _walk(base):
    try:
        for current, dirs, files in os.walk(base, topdown=True, onerror=lambda e: None):
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
            yield Path(current), dirs, files
    except Exception:
        return


def _folder_matches(folder, q):
    name = folder.name.lower()
    path = str(folder).lower()
    return q == name or q in name or q in path


def file_search_advance(query: str, root: str = "", extension: str = "", limit: int = 30):
    q = (query or "").lower().strip()
    ext = (extension or "").lower().strip()
    max_results = max(1, min(int(limit or 30), 100))

    if root:
        base = Path(root).expanduser()
        if not _safe(base):
            return "Access denied: the requested search root is outside the available local drives."
        roots = [base.resolve()]
    else:
        roots = _available_roots()

    # Phase 1: exact/near-exact folder matches FIRST. This is important for
    # commands such as 'Find my Mark-LIV-Advance project'.
    folder_results = []
    seen = set()
    for base in roots:
        for folder, dirs, files in _walk(base):
            if _folder_matches(folder, q) if q else False:
                key = str(folder).lower()
                if key not in seen:
                    folder_results.append(f"[FOLDER] {folder}")
                    if _is_project(folder):
                        folder_results[-1] = f"[PYTHON PROJECT] {folder}"
                    seen.add(key)
                    if len(folder_results) >= max_results:
                        return "\\n".join(folder_results)
    if folder_results:
        return "\\n".join(folder_results)

    # Phase 2: project markers / matching files.
    results = []
    for base in roots:
        for folder, dirs, files in _walk(base):
            if _is_project(folder) and (not q or q in folder.name.lower() or q in str(folder).lower() or q == "python project"):
                key = str(folder).lower()
                if key not in seen:
                    results.append(f"[PYTHON PROJECT] {folder}")
                    seen.add(key)
                    if len(results) >= max_results:
                        return "\\n".join(results)
            for name in files:
                if ext and Path(name).suffix.lower() != (ext if ext.startswith(".") else "." + ext):
                    continue
                if q and q not in name.lower() and q not in str(folder).lower():
                    continue
                full = folder / name
                key = str(full).lower()
                if key not in seen:
                    results.append(str(full))
                    seen.add(key)
                    if len(results) >= max_results:
                        return "\\n".join(results)
    return "\\n".join(results) if results else "No matching files or folders found on the available drives."


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
    "description": "REAL LOCAL FILE/FOLDER SEARCH. MUST be called for 'find my project', 'find a folder', 'search my PC', or 'find files'. Searches G:/Coding and G:/Projects first, then the home folder and other available Windows drives. It prioritizes exact folder-name matches before files/shortcuts, so 'Find my Mark-LIV-Advance project' should return the real project folder, not a Recent .lnk shortcut. Never claim a search result unless this tool returned it.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "File, folder, project, or text to find"},
            "root": {"type": "STRING", "description": "Optional drive/folder root"},
            "extension": {"type": "STRING", "description": "Optional extension such as py or pdf"},
            "limit": {"type": "INTEGER", "description": "Maximum results"},
        },
        "required": ["query"],
    },
    "handler": file_search_advance,
}
