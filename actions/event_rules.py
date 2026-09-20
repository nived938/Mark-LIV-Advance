from core.event_rules import ENGINE


def event_rules(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "list")).strip().lower()

    ENGINE.configure_player(player)

    if action == "start":
        ENGINE.start(player)
        return "Event Rules engine started."

    if action == "stop":
        ENGINE.stop()
        return "Event Rules engine stopped."

    if action == "list":
        rows = ENGINE.list()
        if not rows:
            return "No event rules."
        return "\n".join(
            f"- {r.get('id')}: {r.get('name')} | {r.get('event')} | {r.get('path') or r.get('pattern','')} | THEN {r.get('instruction','')}"
            for r in rows
        )

    if action == "create":
        event = p.get("event", "")
        rule = ENGINE.add(
            event=event,
            path=p.get("path", ""),
            pattern=p.get("pattern", ""),
            instruction=p.get("instruction", ""),
            name=p.get("name", ""),
        )
        if not rule.get("ok"):
            return rule["message"]
        ENGINE.start(player)
        return f"Event rule created: {rule['rule']['name']} ({rule['rule']['id']})."

    if action == "remove":
        ok = ENGINE.remove(p.get("rule_id", ""))
        return "Event rule removed." if ok else "Event rule not found."

    return "Use action=create/list/remove/start/stop."


TOOL = {
    "name": "event_rules",
    "description": (
        "Create event-driven WHEN/THEN automations separate from reminders. "
        "Supported triggers: file_created, file_changed, process_started. "
        "When a trigger fires, the THEN instruction is sent into the normal "
        "J.A.R.V.I.S. command path."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "create | list | remove | start | stop"},
            "name": {"type": "STRING", "description": "Rule name"},
            "rule_id": {"type": "STRING", "description": "Rule ID for removal"},
            "event": {"type": "STRING", "description": "file_created | file_changed | process_started"},
            "path": {"type": "STRING", "description": "Directory/file for file events"},
            "pattern": {"type": "STRING", "description": "Filename glob for file events, or process-name fragment for process_started"},
            "instruction": {"type": "STRING", "description": "THEN instruction sent to J.A.R.V.I.S."}
        },
        "required": ["action"]
    },
    "handler": event_rules,
}
