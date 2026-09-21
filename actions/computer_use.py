"""Autonomous whole-PC computer-use agent for JARVIS."""
from __future__ import annotations
import io, json, re, time
from typing import Any
from pathlib import Path
from core import gemini
from actions.computer_control import computer_control
from actions.open_app import open_app
try:
    import pyautogui
except Exception:
    pyautogui = None
try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

def _screen():
    if pyautogui is None: raise RuntimeError("PyAutoGUI is not installed.")
    img = pyautogui.screenshot(); buf = io.BytesIO(); img.save(buf, format="PNG")
    return buf.getvalue(), img.size[0], img.size[1]

def _window():
    if Desktop is None: return {"title":"", "class_name":""}
    try:
        w = Desktop(backend="uia").get_active()
        return {"title": (w.window_text() or "")[:300], "class_name": (w.class_name() or "")[:200]}
    except Exception: return {"title":"", "class_name":""}

def _json(text: str):
    raw = re.sub(r"^```(?:json)?\s*", "", (text or "").strip(), flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    try: return json.loads(raw)
    except Exception: pass
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if not m: return None
    try: return json.loads(m.group(0))
    except Exception: return None

def _app_title_matches(app_name: str, title: str) -> bool:
    low = app_name.lower().strip()
    title_low = (title or "").lower().strip()
    if not low or not title_low:
        return False

    vscode_names = {"vs code", "vscode", "visual studio code", "code"}
    if low in vscode_names:
        return "visual studio code" in title_low or title_low.endswith(" - code")
    return low in title_low


def _looks_like_system_dialog(window: dict) -> bool:
    """Keep a visible modal/system dialog in front instead of stealing focus back."""
    title = (window.get("title") or "").strip().lower()
    class_name = (window.get("class_name") or "").strip().lower()

    if class_name == "#32770":
        return True

    dialog_titles = (
        "open", "save as", "select folder", "choose", "browse for folder",
        "confirm", "security warning", "rename", "file upload", "file download",
    )
    return any(title == item or title.startswith(item + " ") for item in dialog_titles)


def _focus_app_window(app_name: str):
    """Find, restore, and focus an existing app window. Return its title or None."""
    if Desktop is None:
        return None

    try:
        for win in Desktop(backend="uia").windows():
            title = (win.window_text() or "").strip()
            if not _app_title_matches(app_name, title):
                continue

            try:
                win.restore()
            except Exception:
                pass

            try:
                win.set_focus()
            except Exception:
                pass

            time.sleep(0.25)
            print(f"[ComputerUse] Focused {app_name}: {title}")
            return title
    except Exception as exc:
        print(f"[ComputerUse] focus scan failed for {app_name}: {exc}")

    return None


def _existing_app_window(app_name: str):
    """Return and focus an already-open matching desktop window, if present."""
    return bool(_focus_app_window(app_name))


def _infer_target_app(goal: str) -> str:
    """Infer an explicitly named target app from natural-language GUI goals."""
    patterns = (
        r"\b(?:open|launch|start|use|using|in|inside)\s+(?:the\s+)?([A-Za-z0-9][A-Za-z0-9 ._&'()+-]{0,60}?)(?=\s+(?:and|then|to|for|where|with|on)\b|[,.;]|$)",
        r"\b(?:app|application)\s*[:=-]\s*([A-Za-z0-9][A-Za-z0-9 ._&'()+-]{0,60}?)(?=\s+(?:and|then|to|for)\b|[,.;]|$)",
    )

    for pattern in patterns:
        match = re.search(pattern, goal, flags=re.I)
        if match:
            name = match.group(1).strip(" .,-")
            if name:
                return name

    return ""


def _ensure_target_focus(target_app: str, active_window: dict) -> str:
    """Keep the requested app focused unless a visible modal dialog needs the foreground."""
    if not target_app:
        return ""

    if _app_title_matches(target_app, active_window.get("title", "")):
        return active_window.get("title", "")

    if _looks_like_system_dialog(active_window):
        # The dialog is part of the current GUI flow. Let Gemini inspect it first.
        return active_window.get("title", "")

    focused_title = _focus_app_window(target_app)
    if focused_title:
        return focused_title

    print(f"[ComputerUse] Target app not found/focusable: {target_app}")
    return active_window.get("title", "")

_ALLOWED = {"click","double_click","right_click","type","smart_type","hotkey","press","key","scroll","wait","screen_click","focus_window"}

def _hotkey_parts(spec):
    """Normalize Gemini shortcut output into safe PyAutoGUI operations.

    Accepts:
      - ["ctrl", "n"]
      - "ctrl+n"
      - "ctrl+k ctrl+o"  (two chords)
      - "ctrl+k o"       (chord followed by a single key)
    """
    if isinstance(spec, (list, tuple)):
        raw = [str(x).strip() for x in spec if str(x).strip()]
        if len(raw) > 1 and all("+" not in x for x in raw):
            return [("hotkey", raw)]
        spec = " ".join(raw)

    text = str(spec or "").strip()
    if not text:
        return []

    ops = []
    # Spaces separate sequential key operations. '+' joins a chord.
    for token in text.split():
        token = token.strip()
        if not token:
            continue
        if "+" in token:
            keys = [k.strip() for k in token.split("+") if k.strip()]
            if keys:
                ops.append(("hotkey", keys))
        else:
            ops.append(("press", token))
    return ops

def _execute_hotkey(spec):
    ops = _hotkey_parts(spec)
    if not ops:
        return "Rejected hotkey: empty shortcut."

    results = []
    for kind, value in ops:
        if kind == "hotkey":
            result = computer_control({"action": "hotkey", "keys": value})
        else:
            result = computer_control({"action": "press", "key": value})
        results.append(result)

    return " → ".join(results)

def _decide(goal, history, image, width, height, window, target_app=""):
    title = window.get("title", "")
    recent = json.dumps(history[-6:], ensure_ascii=False)
    prompt = f"""You are JARVIS Computer Use controlling a real Windows desktop.
USER GOAL:
{goal}
TARGET APP: {target_app or "not explicitly identified"}
ACTIVE WINDOW: {title}
SCREEN: {width}x{height}
RECENT ACTIONS: {recent}

The attached screenshot is the current desktop. It is the source of truth.
Inspect the screenshot before deciding. For every mouse click, use the visible screen image
to identify the exact UI control and return its center pixel coordinates x,y from this screenshot.
NEVER guess a button location from memory, a typical layout, or an app description.
Only click a control that is actually visible in the screenshot.
Choose exactly ONE next UI action.

When the target app is visible but not focused, choose focus_window with its visible title.
If the target app is already focused, do not focus it again.
If a Windows/app dialog is visibly in front of the target app, operate the dialog because it is
part of the current GUI flow.
After any action that changes the UI, expect the next step to use a fresh screenshot.

Prefer normal click/double_click/right_click with screenshot-derived x,y coordinates.
Use screen_click only when a natural-language element description is safer than coordinates.
Prefer keyboard shortcuts only when the shortcut is clearly appropriate to the visible app state.
Do not use terminal commands, filesystem APIs, or guessed UI coordinates as a substitute for GUI interaction.
Do not claim success without visual verification.
Do not repeat the exact same action and parameters when the screenshot did not visibly change.
For hotkeys, put the shortcut in parameters.keys as a single chord like "ctrl+n".
For sequential shortcuts, use one chord per action; never write "ctrl+k ctrl+o" as one chord.
For VS Code folder/file creation, prefer the visible File menu, Open Folder flow, New File flow,
or reliable individual keyboard actions. Do not press Save on an unsaved empty editor before creating the requested file.
If the goal is visibly complete, return done.

Return ONLY JSON:
{{"action":"click|double_click|right_click|type|smart_type|hotkey|press|scroll|wait|screen_click|focus_window|done",
"parameters":{{"x":0,"y":0}},"reason":"short reason based on what is visible"}}"""
    try:
        from google.genai import types as gtypes
        r = gemini.call([gtypes.Part.from_bytes(data=image, mime_type="image/png"), prompt], tier=gemini.FAST, timeout_ms=20000)
        return _json(r.text if r else "")
    except Exception as exc:
        print(f"[ComputerUse] decision failed: {exc}"); return None

def _verify(goal, history, image, width, height, window):
    title = window.get("title", "")
    recent = json.dumps(history[-10:], ensure_ascii=False)
    prompt = f"""Verify whether the Windows desktop actually completed this goal.
GOAL: {goal}
ACTIVE WINDOW: {title}
ACTIONS: {recent}
Use the screenshot as the source of truth.
For this task, completion requires every requested visible result to exist, not merely that an app was opened.
Do not infer completion from the action history alone.
Return ONLY JSON:
{{"verified":true|false,"evidence":"short concrete evidence"}}"""
    try:
        from google.genai import types as gtypes
        r = gemini.call([gtypes.Part.from_bytes(data=image, mime_type="image/png"), prompt], tier=gemini.FAST, timeout_ms=20000)
        data = _json(r.text if r else "")
        return bool(data and data.get("verified")), str(data.get("evidence","")) if data else "No verification response."
    except Exception as exc: return False, f"verification failed: {exc}"

def _execute(step):
    action = str(step.get("action","")).lower().strip()
    if action == "key":
        action = "press"
    if action not in _ALLOWED:
        return f"Rejected action: {action}"

    # Gemini may serialize parameters at the top level or under parameters.
    p = dict(step.get("parameters") or {})
    for key in (
        "x", "y", "text", "keys", "key", "hotkey", "direction", "amount",
        "seconds", "title", "description", "clear_first"
    ):
        if key not in p and key in step:
            p[key] = step[key]

    if action == "hotkey":
        # The model historically returned "hotkey" instead of the declared
        # "keys" field. Accept both, and correctly execute sequential chords.
        spec = p.get("keys") or p.get("hotkey")
        return _execute_hotkey(spec)

    p["action"] = action

    if action in {"click","double_click","right_click"} and pyautogui is not None:
        w, h = pyautogui.size()
        p["x"] = max(0, min(int(p.get("x", 0)), w - 1))
        p["y"] = max(0, min(int(p.get("y", 0)), h - 1))

    return computer_control(p)

def computer_use(parameters=None, response=None, player=None, session_memory=None):
    params = parameters or {}; goal = str(params.get("goal","")).strip()
    if not goal: return "computer_use requires a goal."
    max_steps = max(1,min(int(params.get("max_steps",12)),30)); verify_every = max(1,min(int(params.get("verify_every",2)),5))
    history=[]; print(f"[ComputerUse] ▶ {goal}")
    if player: player.write_log(f"[ComputerUse] {goal}")

    # Always keep track of the app the user asked JARVIS to operate.
    # The visual loop will refocus it automatically whenever JARVIS or another
    # unrelated window becomes active.
    target_app = str(params.get("target_app") or "").strip() or _infer_target_app(goal)

    # If the goal explicitly names an app to open, open and focus it before
    # the first screenshot. Never launch a duplicate if an existing window is available.
    m = re.search(r"open\s+([A-Za-z0-9][A-Za-z0-9 ._&'()+-]{0,60}?)(?=\s*(?:,|\band\b|\bthen\b|$))", goal, flags=re.I)
    if m:
        app_name = m.group(1).strip().strip(" .,")
        if app_name:
            target_app = app_name
            active_window = _window()
            if _app_title_matches(app_name, active_window.get("title", "")):
                history.append({
                    "step":"0",
                    "action":"open_app",
                    "result":f"{app_name} is already focused; launch skipped",
                })
                print(f"[ComputerUse] {app_name} already focused; skipping launch.")
            else:
                existing_window = _existing_app_window(app_name)
                if existing_window:
                    history.append({
                        "step":"0",
                        "action":"open_app",
                        "result":f"{app_name} already open; focused existing window",
                    })
                    print(f"[ComputerUse] Reusing existing {app_name}; skipping duplicate launch.")
                else:
                    launch_result = open_app({"app_name": app_name})
                    history.append({"step":"0","action":"open_app","result":launch_result[:500]})
                    if "Could not confirm" in launch_result or "Failed to open" in launch_result:
                        print(f"[ComputerUse] App launch was not confirmed: {launch_result}")
                    time.sleep(1.0)

            # Opening an app may produce a splash/startup window first. Focus it
            # again before the first screenshot so Gemini sees the real target app.
            current = _window()
            _ensure_target_focus(target_app, current)
            time.sleep(0.35)

    previous_signature = None
    repeated_count = 0

    for n in range(1,max_steps+1):
        # Before EVERY screenshot, make sure the target app is in the foreground.
        # If a modal Open/Save/etc. dialog is currently visible, keep the dialog in front
        # so Gemini can operate it as part of the same app flow.
        window=_window()
        if target_app:
            focused_title = _ensure_target_focus(target_app, window)
            if focused_title and focused_title != window.get("title", ""):
                time.sleep(0.25)
            window=_window()

        try:
            image,width,height=_screen()
        except Exception as exc:
            return f"Computer-use failed to capture desktop: {exc}"

        # The screenshot is deliberately captured AFTER focus correction, so Gemini
        # never plans from a screenshot of the wrong application.
        window=_window()
        decision=_decide(goal,history,image,width,height,window,target_app)
        if not decision:
            history.append({"step":str(n),"result":"No valid vision decision"})
            time.sleep(.5)
            continue

        action=str(decision.get("action","")).lower().strip()
        params=dict(decision.get("parameters") or {})
        if action == "hotkey":
            params.setdefault("keys", decision.get("hotkey") or decision.get("keys") or "")
        signature=json.dumps(
            {"action":action, "parameters":params},
            sort_keys=True, ensure_ascii=False
        )

        if signature == previous_signature:
            repeated_count += 1
        else:
            repeated_count = 0
        previous_signature = signature

        if repeated_count >= 1 and action != "done":
            # One repeated decision with no intervening screen change is enough
            # to force a new visual decision rather than clicking/typing twice.
            history.append({
                "step":str(n),
                "action":action,
                "result":"Blocked repeated action: choose a different action from the current screenshot.",
                "reason":str(decision.get("reason",""))[:200],
            })
            print(f"[ComputerUse] step {n}: blocked repeated {action}")
            time.sleep(.2)
            continue

        if action=="done":
            ok,evidence=_verify(goal,history,image,width,height,window)
            if ok:
                return f"Computer-use completed and verified: {evidence}"
            history.append({
                "step":str(n),
                "result":f"Done claim rejected: {evidence}",
            })
            continue

        result=_execute(decision)
        history.append({
            "step":str(n),
            "action":action,
            "result":result[:500],
            "reason":str(decision.get("reason",""))[:200],
        })
        print(f"[ComputerUse] step {n}: {action} -> {result[:200]}")
        time.sleep(.4)
        if any(x in result.lower() for x in ("failed","error:","rejected action")): continue
        if n % verify_every == 0:
            try:
                im,w,h=_screen(); win=_window(); ok,evidence=_verify(goal,history,im,w,h,win)
                if ok: return f"Computer-use completed and verified: {evidence}"
                history.append({"step":str(n),"result":f"Checkpoint not complete: {evidence}"})
            except Exception as exc: history.append({"step":str(n),"result":f"Checkpoint error: {exc}"})
    try:
        image,width,height=_screen(); window=_window(); ok,evidence=_verify(goal,history,image,width,height,window)
        if ok: return f"Computer-use completed and verified: {evidence}"
    except Exception: pass
    return "Computer-use stopped before verification confirmed completion."

TOOL = {
    "name":"computer_use",
    "description":"PRIMARY TOOL FOR MULTI-STEP DESKTOP TASKS. Use this tool whenever the user asks JARVIS to operate an application or the Windows GUI across multiple steps: open/launch an app AND then click, type, create, edit, navigate, save, configure, or verify something in it. Examples: 'Open VS Code and create main.py', 'open Blender and make...', 'open WhatsApp and send...', 'open Settings and change...'. Pass the COMPLETE user goal unchanged in goal. The agent MUST capture the real screen and send that screenshot to Gemini before each decision. Gemini must choose UI actions from visible controls and derive click coordinates from the current screenshot, not guessed button positions. The agent automatically brings the target app to the foreground before each screenshot and re-observes after actions; visible modal dialogs are allowed to remain in front. Do NOT split such tasks between open_app, file_controller, terminal_advance, or computer_control. Do not substitute terminal commands, filesystem APIs, or guessed coordinates for GUI interaction.",
    "parameters":{"type":"OBJECT","properties":{"goal":{"type":"STRING","description":"Complete user goal to accomplish through the desktop UI."},"target_app":{"type":"STRING","description":"Optional exact app name to keep focused during the GUI task. If omitted, JARVIS infers it from the goal."},"max_steps":{"type":"INTEGER","description":"Maximum UI actions, default 12, maximum 30."},"verify_every":{"type":"INTEGER","description":"Verify progress every N actions, default 2."}},"required":["goal"]},
    "handler":computer_use,
}
