import webbrowser
from urllib.parse import quote

def whatsapp_advance(action: str, phone: str = "", message: str = ""):
    action = (action or "").lower().strip()
    if action in ("open", "open_whatsapp"):
        webbrowser.open("https://web.whatsapp.com/")
        return "Opened WhatsApp Web."
    if action in ("message", "prepare_message"):
        if not phone:
            return "A phone number in international format is required."
        url = "https://wa.me/" + "".join(c for c in phone if c.isdigit())
        if message:
            url += "?text=" + quote(message)
        webbrowser.open(url)
        return "WhatsApp chat opened. No message was sent automatically."
    if action in ("call", "video_call"):
        return "WhatsApp Web does not expose a reliable public automation API for starting calls. Open the chat and start the call manually."
    return "Unknown action. Use open_whatsapp or prepare_message."

TOOL = {
    "name": "whatsapp_advance",
    "description": "Open WhatsApp Web or prepare a WhatsApp chat/message. It does not silently send messages or initiate calls.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "open_whatsapp or prepare_message"},
            "phone": {"type": "STRING", "description": "Phone number in international format"},
            "message": {"type": "STRING", "description": "Message text"},
        },
        "required": ["action"],
    },
    "handler": whatsapp_advance,
}
