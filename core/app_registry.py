"""
Windows application registry for JARVIS.

Indexes executable applications locally so "open Chrome" resolves to the real
.exe path instead of using Start Menu/search. The index is persisted under
memory/app_registry.json and can be refreshed in the background.
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "memory" / "app_registry.json"
LOCK = threading.RLock()
_REFRESHING = False

_COMMON_ROOTS = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")),
    Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))),
    Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))),
]

_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", "cache", "caches",
    "temp", "tmp", "crashdumps", "packages", "package cache",
}

def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()

def _load() -> list[dict[str, Any]]:
    try:
        data = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []

def _save(apps: list[dict[str, Any]]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = INDEX_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(apps, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(INDEX_PATH)

def _candidate_roots() -> list[Path]:
    roots = []
    seen = set()
    for root in _COMMON_ROOTS:
        try:
            root = root.resolve()
        except Exception:
            continue
        key = str(root).lower()
        if root.exists() and key not in seen:
            seen.add(key)
            roots.append(root)

    win = Path(os.environ.get("WINDIR", r"C:\Windows"))
    for root in (win / "System32",):
        try:
            root = root.resolve()
        except Exception:
            continue
        key = str(root).lower()
        if root.exists() and key not in seen:
            seen.add(key)
            roots.append(root)
    return roots

def _scan() -> list[dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for root in _candidate_roots():
        try:
            for path in root.rglob("*.exe"):
                try:
                    if not path.is_file():
                        continue
                    if any(part.lower() in _SKIP_DIRS for part in path.parts):
                        continue
                    resolved = str(path.resolve())
                    key = resolved.lower()
                    if key not in found:
                        found[key] = {
                            "name": path.stem,
                            "normalized": _norm(path.stem),
                            "path": resolved,
                            "updated_at": int(time.time()),
                        }
                except (OSError, PermissionError):
                    continue
        except (OSError, PermissionError):
            continue
    return sorted(found.values(), key=lambda x: x["normalized"])

def refresh(blocking: bool = False) -> None:
    global _REFRESHING
    with LOCK:
        if _REFRESHING:
            return
        _REFRESHING = True

    def worker():
        global _REFRESHING
        try:
            apps = _scan()
            with LOCK:
                _save(apps)
            print(f"[AppRegistry] Indexed {len(apps)} Windows executables.")
        except Exception as exc:
            print(f"[AppRegistry] Refresh failed: {exc}")
        finally:
            _REFRESHING = False

    if blocking:
        worker()
    else:
        threading.Thread(target=worker, name="JarvisAppIndexer", daemon=True).start()

def status() -> dict[str, Any]:
    with LOCK:
        apps = _load()
    return {"count": len(apps), "refreshing": _REFRESHING, "index": str(INDEX_PATH)}

def find_app(query: str) -> dict[str, Any] | None:
    q = _norm(query)
    if not q:
        return None

    with LOCK:
        apps = _load()

    for app in apps:
        if app.get("normalized") == q:
            return app

    for app in apps:
        if _norm(Path(app.get("path", "")).stem) == q:
            return app

    scored: list[tuple[int, dict[str, Any]]] = []
    q_tokens = set(q.split())
    for app in apps:
        name = app.get("normalized", "")
        tokens = set(name.split())
        score = 0
        if q in name:
            score += 100
        score += len(q_tokens & tokens) * 20
        if score:
            scored.append((score - len(name), app))

    if scored:
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1]
    return None

def list_apps(limit: int = 50) -> list[dict[str, Any]]:
    with LOCK:
        apps = _load()
    return apps[:max(1, min(limit, 500))]

def ensure_index() -> None:
    if not INDEX_PATH.exists():
        print("[AppRegistry] No app index found. Building it in background...")
        refresh(blocking=False)
    elif not _REFRESHING:
        refresh(blocking=False)
