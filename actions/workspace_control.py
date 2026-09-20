from core.workspace_manager import (
    current_workspace, define_workspace, delete_workspace,
    list_workspaces, set_workspace,
)


def workspace_control(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "get")).strip().lower()

    if action in {"get", "status"}:
        name = current_workspace()
        return f"Active workspace: {name or 'none'}."

    if action == "list":
        profiles = list_workspaces()
        return "Workspaces: " + ", ".join(sorted(profiles)) if profiles else "No workspaces."

    if action == "set":
        result = set_workspace(
            p.get("workspace", ""),
            bool(p.get("launch_apps", False)),
        )
        if not result["ok"]:
            return result["message"]
        msg = f"Workspace activated: {result['workspace']}."
        if result.get("opened"):
            msg += " Opened: " + ", ".join(result["opened"]) + "."
        if player:
            try:
                player.write_log("[WORKSPACE] " + msg)
            except Exception:
                pass
        return msg

    if action == "define":
        apps = p.get("apps") or []
        if isinstance(apps, str):
            apps = [x.strip() for x in apps.split(",") if x.strip()]
        return define_workspace(
            p.get("workspace", ""),
            p.get("description", ""),
            p.get("context", ""),
            apps,
        )

    if action == "delete":
        return delete_workspace(p.get("workspace", ""))

    return "Use action=set/get/list/define/delete."


TOOL = {
    "name": "workspace_control",
    "description": (
        "Manage persistent personal workspace profiles such as coding, study, work, "
        "presentation, and travel. A workspace stores context, description, and optional "
        "apps. Use this for workspace context, not normal/gaming/serious operating modes."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "set | get | list | define | delete"},
            "workspace": {"type": "STRING", "description": "Workspace name"},
            "description": {"type": "STRING", "description": "Short workspace description"},
            "context": {"type": "STRING", "description": "Instructions/context for this workspace"},
            "apps": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Optional app commands"},
            "launch_apps": {"type": "BOOLEAN", "description": "Launch this workspace's configured apps"}
        },
        "required": ["action"]
    },
    "handler": workspace_control,
}
