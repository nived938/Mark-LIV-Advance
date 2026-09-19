import webbrowser
from urllib.parse import quote

def calendar_advance(action: str, title: str = "", start: str = "", end: str = "", details: str = ""):
    action = (action or "").lower().strip()
    if action == "open":
        webbrowser.open("https://calendar.google.com/")
        return "Opened Google Calendar."
    if action == "event":
        if not title or not start:
            return "Title and start datetime are required."
        # Google Calendar quick-add accepts natural-language text and lets the
        # user review the event before saving.
        text = title
        if start:
            text += " " + start
        if end:
            text += " to " + end
        if details:
            text += " " + details
        webbrowser.open("https://calendar.google.com/calendar/r/eventedit?text=" + quote(text))
        return "Opened a pre-filled calendar event for review. Nothing was saved automatically."
    return "Unknown action. Use open or event."

TOOL = {
    "name": "calendar_advance",
    "description": "Open Google Calendar or prepare a calendar event for user review without silently saving it.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open or event"},
            "title": {"type": "STRING", "description": "Event title"},
            "start": {"type": "STRING", "description": "Start date/time"},
            "end": {"type": "STRING", "description": "End date/time"},
            "details": {"type": "STRING", "description": "Event details"},
        },
        "required": ["action"],
    },
    "handler": calendar_advance,
}
