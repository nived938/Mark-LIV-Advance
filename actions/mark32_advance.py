import json

"""Mark 32 master tool.

This is the orchestration surface for the 29 requested Mark 32 capabilities.
Existing specialized actions remain available and should be preferred when the
model can route a request directly to them.
"""
from core.mark32_engine import ENGINE


def mark32_advance(parameters: dict, player=None, speak=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "status")).lower().strip()

    if action == "plan":
        return str(ENGINE.plan(p.get("goal", "")))
    if action == "execute":
        return ENGINE.execute(p.get("goal", ""), bool(p.get("confirmed")))
    if action in {"cancel", "stop", "stop_all"}:
        return ENGINE.cancel_all()
    if action == "reset_cancel":
        return ENGINE.reset_cancel()
    if action == "status":
        return ENGINE.status()
    if action == "parallel":
        return json.dumps(ENGINE.parallel_execute(p.get("goals", [])), indent=2)
    if action == "notify":
        return ENGINE.notifications.notify(p.get("title", "Mark 32"), p.get("message", ""))
    if action == "monitors":
        return str(ENGINE.vision.monitors())
    if action == "screenshot":
        return ENGINE.vision.screenshot(p.get("monitor"), p.get("path", ""))
    if action == "click":
        ok, reason = ENGINE.permissions.check("write_external", bool(p.get("confirmed")))
        if not ok:
            return reason
        return ENGINE.control.click(int(p["x"]), int(p["y"]))
    if action == "move":
        return ENGINE.control.move(int(p["x"]), int(p["y"]))
    if action == "type":
        return ENGINE.control.type(p.get("text", ""))
    if action == "android_status":
        return ENGINE.android.status()
    if action == "android_shell":
        return ENGINE.android.shell(p.get("command", ""))
    if action == "android_tap":
        return ENGINE.android.tap(int(p["x"]), int(p["y"]))
    if action == "android_text":
        return ENGINE.android.text(p.get("text", ""))
    if action == "android_key":
        return ENGINE.android.key(p.get("keycode", "KEYCODE_BACK"))
    if action == "search_files":
        return "\n".join(ENGINE.files.search(p.get("query", ""), p.get("root", ""), int(p.get("limit", 30))))
    if action == "file":
        op = p.get("operation", "open")
        if op == "delete" and not p.get("confirmed"):
            return "CONFIRMATION_REQUIRED:delete"
        return ENGINE.files.manage(op, p.get("source", ""), p.get("destination", ""))
    if action == "terminal":
        ok, reason = ENGINE.permissions.check("write_external", bool(p.get("confirmed")))
        if not ok:
            return reason
        return ENGINE.terminal.run(p.get("command", ""), p.get("cwd", ""), int(p.get("timeout", 60)))
    if action == "test":
        return ENGINE.coding.test(p.get("path", ""), p.get("command", ""))
    if action == "compile":
        return ENGINE.coding.inspect_python(p.get("path", ""))
    if action == "browser_open":
        return ENGINE.browser.open(p.get("url", ""))
    if action == "browser_fetch":
        return ENGINE.browser.fetch(p.get("url", ""))
    if action == "clipboard_read":
        return ENGINE.clipboard.read()
    if action == "clipboard_write":
        return ENGINE.clipboard.write(p.get("text", ""))
    if action == "camera":
        return ENGINE.camera.capture(p.get("path", ""))
    if action == "schedule":
        return ENGINE.scheduler.add(p.get("run_at", ""), p.get("task", ""))
    if action == "schedules":
        return str(ENGINE.scheduler.list())
    if action == "remember":
        return ENGINE.memory.save(p.get("category", "general"), p.get("key", ""), p.get("value", ""))
    if action == "recall":
        return json.dumps(ENGINE.memory.recall(p.get("query", ""), p.get("category", ""), int(p.get("limit", 20))), indent=2)
    if action == "contact_save":
        return ENGINE.contacts.save(p.get("name", ""), p.get("channel", ""), p.get("address", ""), p.get("notes", ""))
    if action == "contact_search":
        return str(ENGINE.contacts.search(p.get("query", "")))
    if action == "email_compose":
        return ENGINE.communication.compose_email(p.get("to", ""), p.get("subject", ""), p.get("body", ""))
    if action == "sms_compose":
        return ENGINE.communication.compose_sms(p.get("number", ""), p.get("body", ""))
    return f"Unknown Mark 32 action: {action}"


TOOL = {
    "name": "mark32_advance",
    "description": (
        "Mark 32 autonomous agent control plane. Use for autonomous task planning, "
        "multi-step execution planning, self-verification/recovery state, intelligent "
        "routing, multi-monitor vision, visual mouse/keyboard control, Android ADB, "
        "natural-language file management/search, terminal, coding/testing, browser, "
        "long-term memory, clipboard, camera, scheduling, contacts, communication "
        "composition, cancellation, parallel-agent infrastructure and live dashboard "
        "status. It never invents success: destructive/external actions can require "
        "confirmation."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "status|plan|execute|parallel|cancel|reset_cancel|monitors|screenshot|click|move|type|android_status|android_shell|android_tap|android_text|android_key|search_files|file|terminal|test|compile|browser_open|browser_fetch|clipboard_read|clipboard_write|camera|notify|schedule|schedules|remember|recall|contact_save|contact_search|email_compose|sms_compose"},
            "goal": {"type": "STRING", "description": "Goal for planning/execution"},
            "goals": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Independent goals for parallel execution"},
            "title": {"type": "STRING", "description": "Notification title"},
            "message": {"type": "STRING", "description": "Notification message"},
            "monitor": {"type": "INTEGER", "description": "Zero-based monitor index"},
            "path": {"type": "STRING", "description": "File path"},
            "url": {"type": "STRING", "description": "Browser URL"},
            "x": {"type": "INTEGER", "description": "Screen/Android X coordinate"},
            "y": {"type": "INTEGER", "description": "Screen/Android Y coordinate"},
            "text": {"type": "STRING", "description": "Text to type/copy/send"},
            "command": {"type": "STRING", "description": "Shell/ADB/test command"},
            "cwd": {"type": "STRING", "description": "Working directory"},
            "timeout": {"type": "INTEGER", "description": "Command timeout seconds"},
            "query": {"type": "STRING", "description": "Search or memory query"},
            "root": {"type": "STRING", "description": "Search root"},
            "limit": {"type": "INTEGER", "description": "Result limit"},
            "operation": {"type": "STRING", "description": "open|copy|move|rename|delete"},
            "source": {"type": "STRING", "description": "Source path"},
            "destination": {"type": "STRING", "description": "Destination path"},
            "run_at": {"type": "STRING", "description": "ISO datetime"},
            "category": {"type": "STRING", "description": "Memory category"},
            "key": {"type": "STRING", "description": "Memory key"},
            "value": {"type": "STRING", "description": "Memory value"},
            "name": {"type": "STRING", "description": "Contact name"},
            "channel": {"type": "STRING", "description": "Contact channel"},
            "address": {"type": "STRING", "description": "Contact address"},
            "notes": {"type": "STRING", "description": "Contact notes"},
            "to": {"type": "STRING", "description": "Email recipient"},
            "subject": {"type": "STRING", "description": "Email subject"},
            "body": {"type": "STRING", "description": "Email body"},
            "keycode": {"type": "STRING", "description": "Android keycode"},
            "confirmed": {"type": "BOOLEAN", "description": "Explicit user confirmation for a protected action"},
        },
        "required": ["action"],
    },
    "handler": mark32_advance,
}
