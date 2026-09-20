"""Reliable local wait action for multi-step desktop tasks."""

import time


def wait_advance(parameters: dict = None, **_) -> str:
    params = parameters or {}
    raw = params.get("seconds", params.get("duration", 1))
    try:
        seconds = float(raw)
    except (TypeError, ValueError):
        return "Invalid wait duration."

    seconds = max(0.0, min(seconds, 300.0))
    time.sleep(seconds)
    if seconds.is_integer():
        shown = str(int(seconds))
    else:
        shown = f"{seconds:.1f}".rstrip("0").rstrip(".")
    return f"Waited {shown} second(s)."


TOOL = {
    "name": "wait_advance",
    "description": (
        "Waits for an exact number of seconds during a multi-step task. "
        "Use this instead of inventing a tool name such as wcm_control. "
        "For requests like 'wait 5 seconds', call exactly once with seconds=5. "
        "After the wait returns, continue the requested sequence. Do not call "
        "wait_advance unless the user explicitly asked for a delay or the next "
        "step genuinely depends on a timed wait."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "seconds": {
                "type": "NUMBER",
                "description": "Number of seconds to wait, normally 0-300."
            }
        },
        "required": ["seconds"],
    },
    "handler": wait_advance,
}
