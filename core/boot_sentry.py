"""Boot-time safety guard for self-healed JARVIS modules."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKUPS = ROOT / "memory" / "self_heal_backups"


def _compile(path: Path) -> tuple[bool, str]:
    try:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        return True, ""
    except Exception as exc:
        return False, str(exc)


def _allowed(path: Path) -> bool:
    try:
        return any(
            path.resolve().is_relative_to((ROOT / part).resolve())
            for part in ("actions", "core")
        )
    except Exception:
        return False


def restore_broken_modules(logger=print) -> list[str]:
    """Restore the newest self-heal backup when a module is broken at boot."""
    restored = []
    if not BACKUPS.exists():
        return restored

    backups_by_stem = {}
    for backup in BACKUPS.glob("*.py"):
        backups_by_stem.setdefault(backup.stem.split("-", 1)[0], []).append(backup)

    for base in (ROOT / "actions", ROOT / "core"):
        if not base.exists():
            continue

        for path in base.glob("*.py"):
            if not _allowed(path) or path.name in {"main.py", "ui.py"}:
                continue

            ok, _ = _compile(path)
            if ok:
                continue

            backups = backups_by_stem.get(path.stem, [])
            if not backups:
                continue

            backup = max(backups, key=lambda item: item.stat().st_mtime)
            try:
                shutil.copy2(backup, path)
                good, err = _compile(path)
                if good:
                    name = str(path.relative_to(ROOT))
                    restored.append(name)
                    logger(f"[BootSentry] Restored {name} from {backup.name}")
                else:
                    logger(f"[BootSentry] Restore validation failed for {path}: {err}")
            except Exception as exc:
                logger(f"[BootSentry] Could not restore {path}: {exc}")

    return restored
