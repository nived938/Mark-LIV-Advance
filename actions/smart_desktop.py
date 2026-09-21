"""Reversible desktop organizer with preview and rollback."""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

from core.undo import push_undo

_FILE_TYPE_MAP = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".ico", ".heic"},
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".odt", ".ods", ".odp"},
    "Videos": {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v"},
    "Music": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"},
    "Code": {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".cpp", ".java", ".cs", ".go", ".rs", ".sh", ".php"},
    "Executables": {".exe", ".msi", ".bat", ".cmd", ".appimage", ".deb", ".rpm"},
}
_SKIP = {".lnk", ".url", ".webloc", ".desktop"}


def _desktop() -> Path:
    if os.environ.get("XDG_DESKTOP_DIR"):
        p = Path(os.environ["XDG_DESKTOP_DIR"]).expanduser()
        if p.exists():
            return p
    return Path.home() / "Desktop"


def _folder_for(item: Path, mode: str) -> str:
    if mode == "by_date":
        return datetime.fromtimestamp(item.stat().st_mtime).strftime("%Y-%m")
    ext = item.suffix.lower()
    for folder, exts in _FILE_TYPE_MAP.items():
        if ext in exts:
            return folder
    return "Others"


def _plan(mode: str) -> tuple[Path, list[tuple[Path, Path]]]:
    desktop = _desktop()
    if not desktop.exists():
        return desktop, []
    moves = []
    for item in desktop.iterdir():
        if item.is_dir() or item.name.startswith(".") or item.suffix.lower() in _SKIP:
            continue
        target = desktop / _folder_for(item, mode) / item.name
        if target.exists():
            continue
        moves.append((item, target))
    return desktop, moves


def _undo_moves(moves: list[tuple[Path, Path]], created_dirs: list[Path]) -> str:
    restored = 0
    for src, dst in reversed(moves):
        try:
            if dst.exists() and not src.exists():
                src.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(dst), str(src))
                restored += 1
        except Exception:
            pass
    for directory in reversed(created_dirs):
        try:
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
        except Exception:
            pass
    return f"Restored {restored} file(s)."


def organize(mode: str) -> str:
    desktop, moves = _plan(mode)
    if not moves:
        return f"No reversible desktop moves are needed ({mode})."

    created_dirs: list[Path] = []
    completed: list[tuple[Path, Path]] = []
    try:
        for src, dst in moves:
            if not dst.parent.exists():
                dst.parent.mkdir(parents=True, exist_ok=True)
                created_dirs.append(dst.parent)
            shutil.move(str(src), str(dst))
            completed.append((src, dst))
    except Exception as exc:
        _undo_moves(completed, created_dirs)
        return f"Desktop organization failed and was rolled back: {exc}"

    push_undo(
        f"Organize Desktop ({mode}) — {len(completed)} files",
        lambda: _undo_moves(completed, created_dirs),
    )

    lines = [f"Desktop organized ({mode}) — {len(completed)} files moved."]
    lines.extend(f"{src.name} → {dst.parent.name}/" for src, dst in completed[:12])
    if len(completed) > 12:
        lines.append(f"... and {len(completed) - 12} more.")
    lines.append("This batch is registered as one undo operation.")
    return "\n".join(lines)


def preview(mode: str) -> str:
    _, moves = _plan(mode)
    if not moves:
        return f"No desktop files would move ({mode})."
    lines = [f"Preview ({mode}) — {len(moves)} file(s):"]
    lines.extend(f"{src.name} → {dst.parent.name}/" for src, dst in moves[:30])
    if len(moves) > 30:
        lines.append(f"... and {len(moves) - 30} more.")
    return "\n".join(lines)


TOOL = {
    "name": "smart_desktop",
    "description": (
        "Safely organize the Windows desktop with preview and rollback. "
        "Use preview first when the user asks what would move; use organize "
        "for a reversible batch, and use the normal undo tool to restore the "
        "whole batch. Supports by_type and by_date."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "preview | organize"},
            "mode": {"type": "STRING", "description": "by_type | by_date"},
        },
        "required": ["operation"],
    },
}


def smart_desktop(parameters: dict | None = None, **_) -> str:
    p = parameters or {}
    operation = str(p.get("operation") or "preview").strip().lower()
    mode = str(p.get("mode") or "by_type").strip().lower()
    if mode not in {"by_type", "by_date"}:
        return "Mode must be by_type or by_date."
    if operation == "preview":
        return preview(mode)
    if operation == "organize":
        return organize(mode)
    return "Operation must be preview or organize."
