"""Static check for the public main.py -> ui.py JarvisUI contract.

Run:
    python scripts/check_ui_contract.py

The checker intentionally ignores private ui members such as self.ui._win.
Every public self.ui.<name> used by main.py must be provided by JarvisUI as a
method, property, or property setter.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "main.py"
UI = ROOT / "ui.py"


def _public_ui_refs(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        parent = node.value
        if isinstance(parent, ast.Attribute) and parent.attr == "ui":
            if not node.attr.startswith("_"):
                names.add(node.attr)
    return names


def _jarvis_ui_members(tree: ast.Module) -> set[str]:
    names: set[str] = set()

    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != "JarvisUI":
            continue

        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.add(item.name)

        # A property is still represented by FunctionDef above, so no special
        # AST handling is needed. Keep this loop explicit for readability and
        # future extension.
        break

    return names


def main() -> int:
    main_tree = ast.parse(MAIN.read_text(encoding="utf-8"), filename=str(MAIN))
    ui_tree = ast.parse(UI.read_text(encoding="utf-8"), filename=str(UI))

    refs = _public_ui_refs(main_tree)
    members = _jarvis_ui_members(ui_tree)
    missing = sorted(refs - members)

    if missing:
        print("JARVIS UI CONTRACT FAILED")
        for name in missing:
            print(f"  missing: JarvisUI.{name}")
        return 1

    print(f"JARVIS UI CONTRACT OK — {len(refs)} public bridges checked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
