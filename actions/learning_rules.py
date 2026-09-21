"""JARVIS behavioral learning controls."""

from core.learned_rules import add_rule, list_rules, remove_rule, set_enabled

TOOL = {
    "name": "learning_rules",
    "description": (
        "Manage explicit user behavior rules that JARVIS should remember. "
        "Use learn when the user says things like 'remember that I always...', "
        "'next time I say X, do Y', or 'from now on'. Use forget with a rule id "
        "or use list to show learned behaviors. These are behavior preferences, "
        "not personal facts."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "learn | forget | list | enable | disable"},
            "trigger": {"type": "STRING", "description": "Situation or phrase that should activate the behavior."},
            "instruction": {"type": "STRING", "description": "What JARVIS should do in that situation."},
            "name": {"type": "STRING", "description": "Optional short human-friendly rule name."},
            "rule_id": {"type": "STRING", "description": "Rule id for forget/enable/disable."},
        },
        "required": ["action"],
    },
}


def learning_rules(parameters: dict | None = None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action") or "").strip().lower()

    if action == "learn":
        result = add_rule(p.get("trigger", ""), p.get("instruction", ""), p.get("name", ""))
        if not result.get("ok"):
            return result.get("message", "Could not learn that behavior.")
        return f"Learned behavior rule '{result['rule']['name']}'."

    if action == "forget":
        ok = remove_rule(p.get("rule_id", ""))
        return "Behavior rule forgotten." if ok else "Rule id not found."

    if action in {"enable", "disable"}:
        ok = set_enabled(p.get("rule_id", ""), action == "enable")
        state = "enabled" if action == "enable" else "disabled"
        return f"Behavior rule {state}." if ok else "Rule id not found."

    if action == "list":
        rules = list_rules()
        if not rules:
            return "No learned behavior rules."
        lines = []
        for r in rules:
            state = "enabled" if r.get("enabled", True) else "disabled"
            lines.append(
                f"{r.get('id')}: {r.get('name')} [{state}] — "
                f"When: {r.get('trigger')} → Then: {r.get('instruction')}"
            )
        return "\n".join(lines)

    return "Use action=learn, forget, list, enable, or disable."

# Action handler registration
TOOL["handler"] = learning_rules
