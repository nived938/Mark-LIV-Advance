import pyautogui

pyautogui.PAUSE = 0.05

def mouse_keyboard(action: str, x: int = 0, y: int = 0, text: str = "", key: str = ""):
    action = (action or "").lower().strip()
    try:
        if action == "move":
            pyautogui.moveTo(x, y, duration=0.15)
            return f"Moved mouse to ({x}, {y})."
        if action == "click":
            pyautogui.click(x=x, y=y)
            return f"Clicked ({x}, {y})."
        if action == "double_click":
            pyautogui.doubleClick(x=x, y=y, interval=0.08)
            return f"Double-clicked ({x}, {y})."
        if action == "right_click":
            pyautogui.rightClick(x=x, y=y)
            return f"Right-clicked ({x}, {y})."
        if action == "type":
            pyautogui.write(text, interval=0.01)
            return "Typed the requested text."
        if action == "hotkey":
            keys = [k.strip() for k in key.split("+") if k.strip()]
            pyautogui.hotkey(*keys)
            return f"Pressed {key}."
        if action == "press":
            pyautogui.press(key)
            return f"Pressed {key}."
        if action == "scroll":
            pyautogui.scroll(int(y))
            return "Scrolled."
        return "Unknown action. Use move, click, double_click, right_click, type, hotkey, press, or scroll."
    except Exception as e:
        return f"Mouse/keyboard action failed: {e}"

TOOL = {
    "name": "mouse_keyboard_advance",
    "description": "Control the mouse and keyboard. Use screen capture first when coordinates are not known.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "move, click, double_click, right_click, type, hotkey, press, or scroll"},
            "x": {"type": "INTEGER", "description": "Screen X coordinate"},
            "y": {"type": "INTEGER", "description": "Screen Y coordinate or scroll amount"},
            "text": {"type": "STRING", "description": "Text to type"},
            "key": {"type": "STRING", "description": "Key name or + separated hotkey, such as ctrl+s"},
        },
        "required": ["action"],
    },
    "handler": mouse_keyboard,
}
