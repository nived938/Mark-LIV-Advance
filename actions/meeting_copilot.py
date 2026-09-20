from core.meeting_manager import append_line, is_active, start_meeting, status, stop_meeting


def meeting_copilot(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "status")).strip().lower()

    if action == "start":
        result = start_meeting(p.get("name", ""))
        if not result.get("ok", True):
            return result.get("message", "Could not start meeting.")
        msg = f"Meeting capture started: {result['title']}."
        if player:
            try:
                player.write_log("[MEETING] " + msg)
            except Exception:
                pass
        return msg + " Microphone input transcription will be recorded until you stop it."

    if action == "status":
        s = status()
        return (
            f"Meeting active: {s.get('active')}. "
            + (f"Title: {s.get('title')}; captured lines: {s.get('line_count')}."
               if s.get("active") else "No meeting is active.")
        )

    if action == "add":
        if not is_active():
            return "No active meeting."
        append_line(p.get("speaker", "User"), p.get("text", ""))
        return "Meeting line added."

    if action == "stop":
        result = stop_meeting()
        if not result.get("ok"):
            return result.get("message", "No active meeting.")
        return (
            f"Meeting stopped: {result['title']}. Transcript saved to "
            f"{result['transcript_path']}.\n\n{result['transcript']}\n\n"
            "Summarize this meeting now. Extract decisions, action items with "
            "owners when stated, unresolved questions, and a short follow-up."
        )

    return "Use action=start/status/add/stop."


TOOL = {
    "name": "meeting_copilot",
    "description": (
        "Meeting and call copilot workspace. Start a meeting to capture Gemini "
        "microphone input transcription, stop it to save a transcript, then summarize "
        "decisions, action items, unresolved questions and follow-up. Do not claim "
        "speaker identity unless the transcript provides it."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "start | status | add | stop"},
            "name": {"type": "STRING", "description": "Meeting title"},
            "speaker": {"type": "STRING", "description": "Speaker label for manual transcript line"},
            "text": {"type": "STRING", "description": "Manual transcript line"}
        },
        "required": ["action"]
    },
    "handler": meeting_copilot,
}
