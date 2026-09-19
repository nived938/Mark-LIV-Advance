import webbrowser
from urllib.parse import quote


def email_advance(action: str, to: str = "", subject: str = "", body: str = ""):
    action = (action or "").lower().strip()
    if action == "open":
        webbrowser.open("https://mail.google.com/")
        return "Opened Gmail in the browser."
    if action in ("compose", "draft"):
        if not to and not subject and not body:
            return "Provide at least a recipient, subject, or body."
        url = "https://mail.google.com/mail/?view=cm"
        params = []
        if to:
            params.append("to=" + quote(to))
        if subject:
            params.append("su=" + quote(subject))
        if body:
            params.append("body=" + quote(body))
        if params:
            url += "&" + "&".join(params)
        webbrowser.open(url)
        return "Opened a pre-filled Gmail compose window for review. Nothing was sent automatically."
    return "Unknown action. Use open or compose."


TOOL = {
    "name": "email_advance",
    "description": "REAL GMAIL ACTION. MUST be called when the user asks to open Gmail, compose, draft, or prepare an email. For 'draft an email', call action='compose' with the supplied recipient, subject, and body. Open the pre-filled Gmail compose UI; NEVER claim an email was sent. Do not merely describe a draft without calling this tool.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open or compose/draft"},
            "to": {"type": "STRING", "description": "Recipient email"},
            "subject": {"type": "STRING", "description": "Email subject"},
            "body": {"type": "STRING", "description": "Email body"},
        },
        "required": ["action"],
    },
    "handler": email_advance,
}
