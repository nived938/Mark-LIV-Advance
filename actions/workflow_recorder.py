from core.workflow_manager import delete, list_workflows, load, set_replaying, start, stop


def workflow_recorder(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "list")).strip().lower()

    if action == "start":
        return start(p.get("name", ""))

    if action == "stop":
        result = stop()
        if not result.get("ok"):
            return result["message"]
        return f"Workflow '{result['name']}' saved with {result['steps']} step(s) at {result['path']}."

    if action == "list":
        rows = list_workflows()
        if not rows:
            return "No saved workflows."
        return "Workflows: " + ", ".join(f"{r['name']} ({r['steps']} steps)" for r in rows)

    if action == "delete":
        return delete(p.get("name", ""))

    if action == "run":
        name = str(p.get("name", "")).strip()
        workflow = load(name)
        if not workflow:
            return f"Workflow '{name}' not found."
        runner = getattr(player, "execute_workflow", None) if player else None
        if not callable(runner):
            return "Workflow runner is unavailable in this session."
        set_replaying(True)
        try:
            result = runner(workflow)
        finally:
            set_replaying(False)
        return result

    return "Use action=start/stop/list/run/delete."


TOOL = {
    "name": "workflow_recorder",
    "description": (
        "Record and replay reusable user workflows. Start recording, perform normal "
        "JARVIS tool actions, stop to save the sequence, then run it later by name. "
        "Use this for repeatable multi-step routines, not one-off autonomous planning."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start | stop | list | run | delete"},
            "name": {"type": "STRING", "description": "Workflow name"}
        },
        "required": ["action"]
    },
    "handler": workflow_recorder,
}
