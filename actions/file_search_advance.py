from pathlib import Path
import shutil
import os

SAFE_ROOTS = [Path.home(), Path("G:/Coding")]

def _safe(path):
    try:
        p = Path(path).expanduser().resolve()
        return any(p == r.resolve() or p.is_relative_to(r.resolve()) for r in SAFE_ROOTS)
    except Exception:
        return False

def file_search_advance(query: str, root: str = "", extension: str = "", limit: int = 30):
    base = Path(root).expanduser() if root else Path.home()
    if not _safe(base):
        return "Access denied: the requested search root is outside the configured safe roots."
    q = (query or "").lower().strip()
    ext = (extension or "").lower().strip()
    results = []
    try:
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if ext and p.suffix.lower() != (ext if ext.startswith(".") else "." + ext):
                continue
            if q and q not in p.name.lower() and q not in str(p.parent).lower():
                continue
            results.append(str(p))
            if len(results) >= max(1, min(int(limit), 100)):
                break
        return "\n".join(results) if results else "No matching files found."
    except Exception as e:
        return f"File search failed: {e}"

def file_manage_advance(action: str, source: str, destination: str = ""):
    if not _safe(source):
        return "Access denied: source is outside the configured safe roots."
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
    "description": "Search files by name/path/extension and perform safe open, copy, move, rename, or confirmation-required delete operations.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Search text"},
            "root": {"type": "STRING", "description": "Search root"},
            "extension": {"type": "STRING", "description": "Optional extension such as py or pdf"},
            "limit": {"type": "INTEGER", "description": "Maximum results"},
        },
        "required": ["query"],
    },
    "handler": file_search_advance,
}
