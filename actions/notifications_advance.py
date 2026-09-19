import os
import subprocess


def _visible_windows_alert(title, message):
    """Guaranteed visible fallback: native Windows message box in its own process."""
    if os.name != "nt":
        return False, "Windows only"
    ps = (
        "Add-Type -AssemblyName PresentationFramework; "
        "$null=[System.Windows.MessageBox]::Show(" 
        + repr(message) + "," + repr(title or "JARVIS") + "," 
        + "[System.Windows.MessageBoxButton]::OK," 
        + "[System.Windows.MessageBoxImage]::Information);"
    )
    try:
        subprocess.Popen(["powershell.exe", "-NoProfile", "-Command", ps], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        return True, ""
    except Exception as e:
        return False, str(e)


def notifications_advance(title: str = "JARVIS", message: str = ""):
    """Show a Windows notification and provide a guaranteed visible fallback."""
    if not message:
        return "Notification message is required."

    errors = []
    toast_shown = False

    try:
        from winotify import Notification, audio
        toast = Notification(app_id="JARVIS", title=title or "JARVIS", msg=message)
        toast.set_audio(audio.Default, loop=False)
        toast.show()
        toast_shown = True
    except Exception as e:
        errors.append(f"winotify: {e}")

    if not toast_shown:
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title or "JARVIS", message, duration=5, threaded=True)
            toast_shown = True
        except Exception as e:
            errors.append(f"win10toast: {e}")

    # Also create a visible native popup. This avoids Windows Focus Assist /
    # notification-center settings making a successful toast invisible.
    ok, error = _visible_windows_alert(title, message)
    if ok:
        return "Windows notification sent and a visible desktop alert was opened."
    if toast_shown:
        return "Windows toast notification sent, but the visible fallback failed: " + error
    return "Notification failed: " + " | ".join(errors) + (" | popup: " + error if error else "")


TOOL = {
    "name": "notifications_advance",
    "description": "REAL WINDOWS DESKTOP NOTIFICATION. MUST be called for requests to show/send/display a notification. It sends a Windows toast and opens a visible native desktop alert so the user can see it even if notification banners are disabled. Never merely say a notification was shown without calling this tool.",
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
