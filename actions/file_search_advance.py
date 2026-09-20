from pathlib import Path
import shutil
import os
import string
import threading

HOME = Path.home()

# Search these locations before doing an expensive full-PC scan.
COMMON_ROOTS = [
    HOME / "Desktop",
    HOME / "Documents",
    HOME / "Downloads",
    HOME / "Pictures",
    HOME / "Videos",
    HOME / "Music",
    HOME / "OneDrive",
]

# Development locations are checked next.
PRIORITY_ROOTS = [
    Path("G:/Coding"),
    Path("G:/Projects"),
]

MARKERS = (
    "pyproject.toml", "requirements.txt", "setup.py", "Pipfile",
    "uv.lock", "main.py", "app.py", "run.py", "manage.py"
)

SEARCH_CANCEL_EVENT = threading.Event()
SEARCH_LOGGER = None


def set_search_logger(logger):
    global SEARCH_LOGGER
    SEARCH_LOGGER = logger


def _task_log(message):
    try:
        if SEARCH_LOGGER is not None:
            SEARCH_LOGGER(str(message))
    except Exception:
        pass


def cancel_file_search():
    SEARCH_CANCEL_EVENT.set()


def reset_file_search_cancel():
    SEARCH_CANCEL_EVENT.clear()


SKIP_DIRS = {
    "$recycle.bin", "system volume information", "node_modules",
    ".git", "__pycache__", ".venv", "venv"
}


def _existing(paths):
    result = []
    seen = set()
    for root in paths:
        try:
            root = Path(root).expanduser().resolve()
            key = str(root).lower()
            if root.exists() and key not in seen:
                result.append(root)
                seen.add(key)
        except Exception:
            pass
    return result


def _available_drives():
    if os.name != "nt":
        return []
    drives = []
    for letter in string.ascii_uppercase:
        root = Path(f"{letter}:\\")
        try:
            if root.exists():
                drives.append(root.resolve())
        except Exception:
            pass
    return drives


def _safe(path):
    try:
        p = Path(path).expanduser().resolve()
        roots = _existing(COMMON_ROOTS + PRIORITY_ROOTS + _available_drives() + [HOME])
        return any(p == r or p.is_relative_to(r) for r in roots)
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
            if SEARCH_CANCEL_EVENT.is_set():
                return
            dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS]
            yield Path(current), dirs, files
    except Exception:
        return


def _folder_matches(folder, q):
    name = folder.name.lower()
    path = str(folder).lower()
    return q == name or q in name or q in path


def _direct_match(base, q):
    """Very fast check for folders directly inside a common/dev root."""
    try:
        if _folder_matches(base, q):
            return base
        for child in base.iterdir():
            if child.is_dir() and child.name.lower() not in SKIP_DIRS:
                if _folder_matches(child, q):
                    return child
    except Exception:
        pass
    return None


def _search_roots(roots, q, max_results, recursive=True):
    """Search roots and return the first useful matches."""
    results = []
    seen = set()

    # First check the root itself and its immediate children. This makes
    # G:/Coding/Mark-LIV-Advance nearly instant instead of walking all of G:.
    for base in roots:
        hit = _direct_match(base, q) if q else None
        if hit:
            key = str(hit).lower()
            if key not in seen:
                label = "[PYTHON PROJECT]" if _is_project(hit) else "[FOLDER]"
                results.append(f"{label} {hit}")
                seen.add(key)
                if len(results) >= max_results:
                    return results

    if not recursive:
        return results

    for base in roots:
        if SEARCH_CANCEL_EVENT.is_set():
            return results
        for folder, dirs, files in _walk(base):
            if SEARCH_CANCEL_EVENT.is_set():
                return results
            if q and _folder_matches(folder, q):
                key = str(folder).lower()
                if key not in seen:
                    label = "[PYTHON PROJECT]" if _is_project(folder) else "[FOLDER]"
                    results.append(f"{label} {folder}")
                    seen.add(key)
                    if len(results) >= max_results:
                        return results
            if _is_project(folder) and (
                not q or q in folder.name.lower() or q in str(folder).lower()
            ):
                key = str(folder).lower()
                if key not in seen:
                    results.append(f"[PYTHON PROJECT] {folder}")
                    seen.add(key)
                    if len(results) >= max_results:
                        return results
            for name in files:
                if SEARCH_CANCEL_EVENT.is_set():
                    return results
                if q and q not in name.lower() and q not in str(folder).lower():
                    continue
                full = folder / name
                key = str(full).lower()
                if key not in seen:
                    results.append(str(full))
                    seen.add(key)
                    if len(results) >= max_results:
                        return results
    return results


def file_search_advance(query: str, root: str = "", extension: str = "", limit: int = 30):
    reset_file_search_cancel()
    _task_log(f'SEARCHING: {query}')
    raw_q = (query or "").strip()
    low_q = raw_q.lower()
    exhaustive = any(word in low_q.split() for word in ("every", "all"))
    q = low_q
    for marker in ("every", "all", "files", "file", "named", "called"):
        q = q.replace(marker, " ")
    q = " ".join(q.split()).strip()
    ext = (extension or "").lower().strip()
    max_results = max(1, min(int(limit or (100 if exhaustive else 30)), 500 if exhaustive else 100))

    if root:
        base = Path(root).expanduser()
        if not _safe(base):
            return "Access denied: the requested search root is outside the available local drives."
        roots = [base.resolve()]
        _task_log(f'ROOT: {base.resolve()}')
        results = _search_roots(roots, q, max_results)
        return ("Search cancelled." if SEARCH_CANCEL_EVENT.is_set() else 
                ("\n".join(results) if results else "No matching files or folders found."))

    common = _existing(COMMON_ROOTS)
    dev = _existing(PRIORITY_ROOTS)
    searched = {str(p).lower() for p in common + dev}
    all_drives = [p for p in _available_drives() if str(p).lower() not in searched]

    # Normal searches stop at the first useful root for speed.
    if not exhaustive:
        _task_log('SCANNING: common user folders')
        results = _search_roots(common, q, max_results)
        if results:
            return "\n".join(results)
        _task_log('SCANNING: development folders')
        results = _search_roots(dev, q, max_results)
        if results:
            return "\n".join(results)
        _task_log('SCANNING: available drives')
        results = _search_roots(all_drives, q, max_results)
        if results:
            return "\n".join(results)
    else:
        # "every/all" means aggregate across the PC until the result cap.
        results = []
        seen = set()
        for label, roots in (("common user folders", common), ("development folders", dev), ("available drives", all_drives)):
            _task_log(f'SCANNING: {label}')
            if SEARCH_CANCEL_EVENT.is_set():
                _task_log("CANCELLED: file search")
                return "Search cancelled."
            for item in _search_roots(roots, q, max_results):
                key = item.lower()
                if key not in seen:
                    results.append(item)
                    seen.add(key)
                    if len(results) >= max_results:
                        break
            if len(results) >= max_results:
                break
        if results:
            _task_log(f"FOUND: {len(results)} matching results")
            suffix = f"\n\nShowing up to {max_results} matching results."
            return "\n".join(results) + suffix

    if ext:
        wanted = ext if ext.startswith(".") else "." + ext
        for base in all_drives:
            for folder, dirs, files in _walk(base):
                if SEARCH_CANCEL_EVENT.is_set():
                    return "Search cancelled."
                for name in files:
                    if Path(name).suffix.lower() == wanted and (
                        not q or q in name.lower() or q in str(folder).lower()
                    ):
                        return str(folder / name)

    return "No matching files or folders found on the available drives."


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
            try:
                from core.mode_manager import current_mode
                if current_mode() == "serious":
                    src.unlink()
                    return f"Deleted {src}."
            except Exception as exc:
                return f"File deletion failed: {exc}"
            return "REQUIRES_CONFIRMATION: delete the requested file."
        return "Unknown action. Use open, copy, move, rename, or delete."
    except Exception as e:
        return f"File operation failed: {e}"


TOOL = {
    "name": "file_search_advance",
    "description": (
        "REAL LOCAL FILE/FOLDER SEARCH. MUST be called for 'find my project', "
        "'find a folder', 'search my PC', or 'find files'. Search order is: "
        "Desktop, Documents, Downloads, Pictures, Videos, Music and OneDrive; "
        "then G:/Coding and G:/Projects; ONLY if no result is found, search all "
        "other Windows drives. Direct child folders are checked before expensive "
        "recursive scanning, so common project folders such as G:/Coding/Mark-LIV-Advance "
        "should be found quickly. Never claim a result unless this tool returned it."
    ),
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
