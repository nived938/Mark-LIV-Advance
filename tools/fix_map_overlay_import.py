from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "ui.py"
IMPORT = "from core.map_overlay import MapOverlay"
MARKER = "try:\n    from core.avatar import HoloAvatar"


def main() -> int:
    text = UI.read_text(encoding="utf-8")
    if IMPORT in text:
        print("MapOverlay import already present.")
        return 0

    if MARKER not in text:
        raise SystemExit("Could not find the core.avatar import block in ui.py")

    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith("try:") and i + 1 < len(lines) and "from core.avatar import HoloAvatar" in lines[i + 1]:
            insert_at = i
            while insert_at < len(lines) and lines[insert_at].strip() != "":
                insert_at += 1
            lines.insert(insert_at + 1, IMPORT + "\n")
            UI.write_text("".join(lines), encoding="utf-8", newline="")
            print(f"Patched {UI}: imported MapOverlay from core.map_overlay")
            return 0

    raise SystemExit("Could not locate the HoloAvatar import block in ui.py")


if __name__ == "__main__":
    raise SystemExit(main())
