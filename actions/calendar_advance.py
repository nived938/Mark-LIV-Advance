import json
import os
import webbrowser
from datetime import datetime, timedelta
from urllib.parse import quote

import requests

from core.env import load_env


load_env()
_CALDAYS_BASE = os.getenv("CALDAYS_BASE_URL", "https://caldays.com/api").rstrip("/")
_TIMEOUT = 15


def _google_dates(start: str, end: str = "") -> str:
    """Convert common ISO datetimes to Google's YYYYMMDDTHHMMSS form."""
    try:
        s = datetime.fromisoformat(start.replace("Z", "+00:00"))
        e = datetime.fromisoformat(end.replace("Z", "+00:00")) if end else s + timedelta(hours=1)
        return s.strftime("%Y%m%dT%H%M%S") + "/" + e.strftime("%Y%m%dT%H%M%S")
    except Exception:
        return ""


def _caldays_get(path: str, params: dict | None = None):
    url = f"{_CALDAYS_BASE}/{path.lstrip('/')}"
    response = requests.get(url, params=params or {}, timeout=_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _json_result(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def calendar_advance(
    action: str = "",
    title: str = "",
    start: str = "",
    end: str = "",
    details: str = "",
    country_code: str = "",
    cities: str = "",
    tz: str = "",
):
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
            url = "https://calendar.google.com/calendar/r/eventedit?text=" + quote(title + " " + start)
            if details:
                url += "&details=" + quote(details)
        webbrowser.open(url)
        return (
            "Opened a pre-filled Google Calendar event for review. "
            "Nothing was saved automatically."
        )

    if action == "holidays":
        code = (country_code or "IN").strip().lower()
        try:
            data = _caldays_get(f"holidays/{code}")
            return _json_result(data)
        except Exception as exc:
            return f"Caldays holidays request failed: {exc}"

    if action == "long_weekends":
        code = (country_code or "IN").strip().lower()
        try:
            data = _caldays_get(f"long-weekends/{code}")
            return _json_result(data)
        except Exception as exc:
            return f"Caldays long-weekends request failed: {exc}"

    if action == "clock":
        params = {}
        if cities:
            params["cities"] = cities
        if tz:
            params["tz"] = tz
        if not params:
            return "Provide cities and/or an IANA time zone for the world clock."
        try:
            data = _caldays_get("clock", params=params)
            return _json_result(data)
        except Exception as exc:
            return f"Caldays world-clock request failed: {exc}"

    return (
        "Unknown action. Use open, event, holidays, long_weekends, or clock. "
        "For Caldays use country_code for holidays/long_weekends and cities/tz for clock."
    )


TOOL = {
    "name": "calendar_advance",
    "description": (
        "Calendar and date intelligence. Use action='open' to open Google Calendar, "
        "action='event' to prepare a Google Calendar event for review, "
        "action='holidays' for 2026 public holidays from Caldays, "
        "action='long_weekends' for 2026 long-weekend/bridge-day planning from Caldays, "
        "and action='clock' for the Caldays world clock using city codes and/or IANA time zones. "
        "Caldays needs no API key. Do not claim a Google Calendar event was saved; this tool only "
        "opens the pre-filled event page."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "open | event | holidays | long_weekends | clock",
            },
            "title": {"type": "STRING", "description": "Google Calendar event title"},
            "start": {"type": "STRING", "description": "Google Calendar event start datetime"},
            "end": {"type": "STRING", "description": "Google Calendar event end datetime"},
            "details": {"type": "STRING", "description": "Google Calendar event details"},
            "country_code": {"type": "STRING", "description": "Two-letter country code such as IN or US"},
            "cities": {"type": "STRING", "description": "Comma-separated Caldays city codes such as jkt,lon,nyc"},
            "tz": {"type": "STRING", "description": "IANA zone such as Asia/Tokyo"},
        },
        "required": ["action"],
    },
    "handler": calendar_advance,
}
