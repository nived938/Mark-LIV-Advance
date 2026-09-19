import webbrowser
from urllib.parse import quote
from datetime import datetime


def _google_dates(start: str, end: str = "") -> str:
    """Convert common ISO datetimes to Google's YYYYMMDDTHHMMSS form."""
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if end:
            e = datetime.fromisoformat(end.replace("Z", "+00:00"))
        else:
            from datetime import timedelta
            e = s + timedelta(hours=1)
        return s.strftime("%Y%m%dT%H%M%S") + "/" + e.strftime("%Y%m%dT%H%M%S")
    except Exception:
        return ""


def calendar_advance(action: str, title: str = "", start: str = "", end: str = "", details: str = ""):
    action = (action or "").lower().strip()
    if action == "open":
        webbrowser.open("https://calendar.google.com/")
        return "Opened Google Calendar in the browser."
    if action == "event":
        if not title or not start:
            return "Title and start datetime are required."
        dates = _google_dates(start, end)
        if dates:
            url = "https://calendar.google.com/calendar/render?action=TEMPLATE"
            url += "&text=" + quote(title)
            url += "&dates=" + quote(dates)
            if details:
                url += "&details=" + quote(details)
        else:
            # Still provide a review page if the model supplied natural language.
            url = "https://calendar.google.com/calendar/r/eventedit?text=" + quote(title + " " + start)
            if details:
                url += "&details=" + quote(details)
        webbrowser.open(url)
        return "Opened a pre-filled Google Calendar event for review. Nothing was saved automatically."
    return "Unknown action. Use open or event."


TOOL = {
    "name": "calendar_advance",
    "description": "REAL CALENDAR ACTION. MUST be called when the user asks to open Google Calendar or create/prepare a calendar event. For 'create a calendar event', call action='event' with title and start (and end/details when known). Open the pre-filled event in the user's browser for review; NEVER claim the event was created/saved unless the tool result says it was opened for review. Do not merely describe what you could do.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open or event"},
            "title": {"type": "STRING", "description": "Event title"},
            "start": {"type": "STRING", "description": "Start date/time; ISO datetime or natural language if needed"},
            "end": {"type": "STRING", "description": "End date/time"},
            "details": {"type": "STRING", "description": "Event details"},
        },
        "required": ["action"],
    },
    "handler": calendar_advance,
}
