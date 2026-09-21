"""Inspect/reset the JARVIS two-way call audio bridge."""
from core.call_audio import ROUTER


TOOL = {
    "name": "call_audio",
    "description": (
        "Inspect or reset the Windows two-way call audio bridge. "
        "Use status before trying to speak to a caller if the call bridge is unavailable; "
        "reset restores normal Windows communications audio."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "status | reset"},
        },
        "required": ["action"],
    },
}


def call_audio(parameters=None, **_) -> str:
    action = str((parameters or {}).get("action") or "status").strip().lower()
    if action == "status":
        state = "active" if ROUTER.active else "inactive"
        return ROUTER.status() + f"\nBridge is {state}."
    if action == "reset":
        ROUTER.stop()
        return "Call audio bridge reset; normal Windows communications audio restored."
    return "Use action=status or reset."

# Action handler registration
TOOL["handler"] = call_audio

