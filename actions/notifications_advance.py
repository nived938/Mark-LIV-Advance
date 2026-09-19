def notifications_advance(title: str, message: str):
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title or "JARVIS", message or "", duration=5, threaded=True)
        return "Notification displayed."
    except Exception as e:
        return f"Notification failed: {e}"

TOOL = {
    "name": "notifications_advance",
    "description": "Show a Windows desktop notification.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING", "description": "Notification title"},
            "message": {"type": "STRING", "description": "Notification body"},
        },
        "required": ["message"],
    },
    "handler": notifications_advance,
}
