import subprocess
import sys


def notifications_advance(title: str = "JARVIS", message: str = ""):
    """Show a Windows desktop notification using available local backends."""
    if not message:
        return "Notification message is required."

    errors = []

    # Preferred modern Windows notification backend when installed.
    try:
        from winotify import Notification, audio
        toast = Notification(app_id="JARVIS", title=title or "JARVIS", msg=message)
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return "Notification displayed using winotify."
    except Exception as e:
        errors.append(f"winotify: {e}")

    # Existing dependency kept as a fallback.
    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title or "JARVIS", message, duration=5, threaded=True)
        return "Notification displayed using win10toast."
    except Exception as e:
        errors.append(f"win10toast: {e}")

    return "Notification failed: " + " | ".join(errors)


TOOL = {
    "name": "notifications_advance",
    "description": "REAL WINDOWS DESKTOP NOTIFICATION TOOL. MUST be called when the user asks to show/send/display a desktop notification. Do not merely say a notification was shown; call this tool and report its actual result. This tool is for local Windows notifications, not chat responses.",
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
