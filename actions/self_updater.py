from core.self_updater import apply_update, check_update


def self_updater(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "check")).strip().lower()

    if action == "check":
        s = check_update()
        if not s.get("ok"):
            return s["message"]
        state = "update available" if s["update_available"] else "up to date"
        dirty = " Local changes are present, so apply will wait until they are preserved." if s["dirty"] else ""
        return (
            f"Repository: {s['repo']} | branch: {s['branch']} | {state}.{dirty} "
            f"Latest: {s['latest_message']}"
        )

    if action in {"update", "apply"}:
        return apply_update()

    return "Use action=check or action=update."


TOOL = {
    "name": "self_updater",
    "description": (
        "Check this J.A.R.V.I.S. installation for updates from its GitHub origin and "
        "safely apply a fast-forward update. Never hard-resets or silently destroys local changes."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "check | update"}
        },
        "required": ["action"]
    },
    "handler": self_updater,
}
