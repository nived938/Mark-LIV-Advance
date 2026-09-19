import webbrowser
from urllib.parse import quote

def email_advance(action: str, to: str = "", subject: str = "", body: str = ""):
    action = (action or "").lower().strip()
    if action == "open":
        webbrowser.open("https://mail.google.com/")
        return "Opened Gmail."
    if action in ("compose", "draft"):
        if not to and not subject and not body:
            return "Provide at least a recipient, subject, or body."
        url = "https://mail.google.com/mail/?view=cm"
        params = []
        if to: params.append("to=" + quote(to))
        if subject: params.append("su=" + quote(subject))
        if body: params.append("body=" + quote(body))
        if params: url += "&" + "&".join(params)
        webbrowser.open(url)
        return "Opened a pre-filled email draft. Nothing was sent automatically."
    return "Unknown action. Use open or compose."

TOOL = {
    "name": "email_advance",
    "description": "Open Gmail or prepare an email draft for user review. Never silently sends email.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open, compose, or draft"},
            "to": {"type": "STRING", "description": "Recipient email"},
            "subject": {"type": "STRING", "description": "Email subject"},
            "body": {"type": "STRING", "description": "Email body"},
        },
        "required": ["action"],
    },
    "handler": email_advance,
}
