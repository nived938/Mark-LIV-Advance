from core.hardware_diagnostics import diagnostic_report


def hardware_diagnostics(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "diagnose")).strip().lower()
    if action in {"diagnose", "report", "check"}:
        return diagnostic_report(bool(p.get("deep", False)))
    return "Use action=diagnose with deep=true for optional SMART discovery."


TOOL = {
    "name": "hardware_diagnostics",
    "description": (
        "Run a hardware health diagnostic report covering CPU, RAM, temperatures, "
        "battery, disks and Windows physical-disk status. Optional deep mode checks "
        "for smartctl SMART devices. This is diagnostics, not continuous telemetry "
        "and does not automatically perform stress tests."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "diagnose | report | check"},
            "deep": {"type": "BOOLEAN", "description": "Also attempt SMART device discovery when smartctl is installed"}
        },
        "required": ["action"]
    },
    "handler": hardware_diagnostics,
}
