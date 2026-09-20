"""Voice/tool control for J.A.R.V.I.S. operating modes."""

from core.mode_manager import activate_mode, current_mode, gaming_processes, MODES


def mode_control(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "get")).strip().lower()
    if action in {"get", "status"}:
        return f"Operating mode: {current_mode()}."
    if action == "list":
        return "Operating modes: " + ", ".join(MODES) + "."
    if action in {"set", "activate", "switch"}:
        result = activate_mode(str(p.get("mode", "normal")))
        if not result["ok"]:
            return result["message"]

        mode = result["mode"]
        lines = [f"Operating mode changed: {result['previous']} -> {mode}."]

        if mode == "gaming":
            lines.append(
                "Steam launch: " + ("requested." if result["steam_opened"] else "could not be started.")
            )
            stopped = result.get("stopped") or []
            lines.append(
                f"Stopped {len(stopped)} optional background app(s)."
                if stopped else
                "No configured optional background apps were running."
            )
        elif mode == "serious":
            lines.append(
                "Serious autonomy is active for Mark32 operations. "
                "From this point, use a serious, concise, professional tone: "
                "no friendly small talk, playful phrasing, emojis, or unnecessary praise."
            )
        else:
            lines.append(
                "Standard operating behavior restored. "
                "Return to the normal friendly and helpful conversational tone."
            )

        msg = " ".join(lines)
        if player:
            try:
                player.write_log("[MODE] " + msg)
                setter = getattr(player, "set_mode_display", None)
                if setter:
                    setter(mode)
            except Exception:
                pass
        return msg

    if action == "gaming_processes":
        return "Gaming cleanup list: " + ", ".join(gaming_processes())

    return "Use action=set/get/list/gaming_processes."


TOOL = {
    "name": "mode_control",
    "description": (
        "Switch J.A.R.V.I.S. operating modes. "
        "gaming opens Steam and stops a conservative list of optional background apps; "
        "normal restores standard behavior; serious enables autonomous Mark32 permissions "
        "for user-requested operations. Use this tool for mode changes instead of manually "
        "changing processes."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "set | get | list | gaming_processes"
            },
            "mode": {
                "type": "STRING",
                "description": "normal | gaming | serious"
            }
        },
        "required": ["action"]
    },
    "handler": mode_control,
}
