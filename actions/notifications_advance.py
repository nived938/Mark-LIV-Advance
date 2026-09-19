import os
import subprocess


def notifications_advance(title: str = "JARVIS", message: str = ""):
    """Show a visible Windows notification with several local fallbacks."""
    if not message:
        return "Notification message is required."

    errors = []

    try:
        from winotify import Notification, audio
        toast = Notification(app_id="JARVIS", title=title or "JARVIS", msg=message)
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        return "Notification displayed using Windows toast notifications."
    except Exception as e:
        errors.append(f"winotify: {e}")

    try:
        from win10toast import ToastNotifier
        ToastNotifier().show_toast(title or "JARVIS", message, duration=5, threaded=True)
        return "Notification displayed using Windows toast notifications."
    except Exception as e:
        errors.append(f"win10toast: {e}")

    # Guaranteed visible fallback on Windows: a small native-style dialog.
    # This is intentionally only a notification fallback; it does not send data anywhere.
    if os.name == "nt":
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo(title or "JARVIS", message, parent=root)
            root.destroy()
            return "Notification displayed using the Windows desktop popup fallback."
        except Exception as e:
            errors.append(f"tkinter popup: {e}")

    return "Notification failed: " + " | ".join(errors)


TOOL = {
    "name": "notifications_advance",
    "description": "REAL WINDOWS DESKTOP NOTIFICATION. MUST be called for requests to show/send/display a notification. Call it with the user's requested message and report the actual tool result. Never merely say a notification was shown without calling this tool.",
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
