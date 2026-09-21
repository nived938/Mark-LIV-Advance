"""User-facing controls for the JARVIS self-healing engine."""

from core.self_heal import ENGINE

TOOL = {
    "name": "self_heal",
    "description": (
        "Diagnose and safely repair a failing JARVIS Python action/core module. "
        "Use status to inspect repeated failures, diagnose to check whether a "
        "module currently compiles, repair to ask the repair engine for a minimal "
        "validated patch, and restore to roll back the most recent self-heal backup."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "status | diagnose | repair | restore"},
            "module": {"type": "STRING", "description": "Action name such as computer_use, or core/path.py."},
            "error": {"type": "STRING", "description": "Optional runtime error to guide a repair."},
        },
        "required": ["action"],
    },
}


def self_heal(parameters: dict | None = None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action") or "").strip().lower()
    module = str(p.get("module") or "").strip()

    if action == "status":
        return ENGINE.status()

    if action == "diagnose":
        path = ENGINE._target_for(module)
        if path is None or not path.exists():
            return "Module is not an allowed existing JARVIS Python module."
        ok, err = ENGINE._compile(path)
        return f"{path.name} compiles successfully." if ok else f"{path.name} has a compile error: {err}"

    if action == "repair":
        if not module:
            return "Provide a module/action name to repair."
        return ENGINE.repair(module, p.get("error", ""), automatic=False)

    if action == "restore":
        if not module:
            return "Provide a module/action name to restore."
        return ENGINE.restore_last(module)

    return "Use action=status, diagnose, repair, or restore."
