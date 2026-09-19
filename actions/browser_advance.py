import webbrowser

def browser_advance(action: str, url: str = ""):
    action = (action or "").lower().strip()
    if action in ("open", "navigate"):
        if not url:
            return "A URL is required."
        webbrowser.open(url)
        return f"Opened {url}."
    if action == "home":
        webbrowser.open("https://www.google.com/")
        return "Opened the browser home page."
    return "Unknown action. Use open, navigate, or home."

TOOL = {
    "name": "browser_advance",
    "description": "Open and navigate the user's default web browser.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open, navigate, or home"},
            "url": {"type": "STRING", "description": "HTTPS URL"},
        },
        "required": ["action"],
    },
    "handler": browser_advance,
}
