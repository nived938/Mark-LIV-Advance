from pathlib import Path
import time

def screen_control(action: str, path: str = ""):
    action = (action or "").lower().strip()
    try:
        import mss
        from PIL import Image
        if action == "screenshot":
            destination = Path(path) if path else Path.home() / "Pictures" / f"jarvis-screen-{int(time.time())}.png"
            destination.parent.mkdir(parents=True, exist_ok=True)
            with mss.mss() as sct:
                shot = sct.grab(sct.monitors[1])
                Image.frombytes("RGB", shot.size, shot.rgb).save(destination)
            return f"Screenshot saved to {destination}."
        if action == "size":
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                return f"Primary screen size: {monitor['width']}x{monitor['height']}."
        return "Unknown action. Use screenshot or size."
    except Exception as e:
        return f"Screen action failed: {e}"

TOOL = {
    "name": "screen_control_advance",
    "description": "Capture the Windows primary screen to an image file or report its size.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "screenshot or size"},
            "path": {"type": "STRING", "description": "Optional screenshot destination path"},
        },
        "required": ["action"],
    },
    "handler": screen_control,
}
