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

_ALLOWED = {"click","double_click","right_click","type","smart_type","hotkey","press","key","scroll","wait","screen_click","focus_window"}

def _decide(goal, history, image, width, height, window):
    prompt = """You are JARVIS Computer Use controlling a real Windows desktop.
USER GOAL:
{goal}
ACTIVE WINDOW: {title}
SCREEN: {width}x{height}
RECENT ACTIONS: {history}
Inspect the screenshot and choose exactly ONE next UI action.
Use visible UI coordinates, not guessed coordinates. Prefer keyboard shortcuts when reliable.
Do not use terminal commands as a substitute for GUI interaction. Do not claim success without verification.
If the goal is visibly complete, return done.
Return ONLY JSON: {"action":"click|double_click|right_click|type|smart_type|hotkey|press|scroll|wait|screen_click|focus_window|done","parameters":{},"reason":"short reason"}""".format(goal=goal,title=window.get("title",""),width=width,height=height,history=json.dumps(history[-6:]))
    try:
        from google.genai import types as gtypes
        r = gemini.call([gtypes.Part.from_bytes(data=image, mime_type="image/png"), prompt], tier=gemini.FAST, timeout_ms=20000)
        return _json(r.text if r else "")
    except Exception as exc:
        print(f"[ComputerUse] decision failed: {exc}"); return None

def _verify(goal, history, image, width, height, window):
    prompt = """Verify whether the Windows desktop actually completed this goal.
GOAL: {goal}
ACTIVE WINDOW: {title}
ACTIONS: {history}
Return ONLY JSON: {"verified":true|false,"evidence":"short concrete evidence"}""".format(goal=goal,title=window.get("title",""),history=json.dumps(history[-10:]))
    try:
        from google.genai import types as gtypes
        r = gemini.call([gtypes.Part.from_bytes(data=image, mime_type="image/png"), prompt], tier=gemini.FAST, timeout_ms=20000)
        data = _json(r.text if r else "")
        return bool(data and data.get("verified")), str(data.get("evidence","")) if data else "No verification response."
    except Exception as exc: return False, f"verification failed: {exc}"

def _execute(step):
    action = str(step.get("action","")).lower().strip()
    if action == "key": action = "press"
    if action not in _ALLOWED: return f"Rejected action: {action}"
    p = dict(step.get("parameters") or {}); p["action"] = action
    if action in {"click","double_click","right_click"} and pyautogui is not None:
        w,h = pyautogui.size(); p["x"] = max(0,min(int(p.get("x",0)),w-1)); p["y"] = max(0,min(int(p.get("y",0)),h-1))
    return computer_control(p)

def computer_use(parameters=None, response=None, player=None, session_memory=None):
    params = parameters or {}; goal = str(params.get("goal","")).strip()
    if not goal: return "computer_use requires a goal."
    max_steps = max(1,min(int(params.get("max_steps",12)),30)); verify_every = max(1,min(int(params.get("verify_every",2)),5))
    history=[]; print(f"[ComputerUse] ▶ {goal}")
    if player: player.write_log(f"[ComputerUse] {goal}")

    # If the goal explicitly names an app to open, open and focus it before
    # the visual loop. This prevents the first UI action from landing in JARVIS.
    m = re.search(r"open\s+([A-Za-z0-9 ._-]+?)(?=\s*(?:,|\band\b|\bthen\b|$))", goal, flags=re.I)
    if m:
        app_name = m.group(1).strip().strip(" .")
        if app_name:
            launch_result = open_app({"app_name": app_name})
            history.append({"step":"0","action":"open_app","result":launch_result[:500]})
            if "Could not confirm" in launch_result or "Failed to open" in launch_result:
                print(f"[ComputerUse] App launch was not confirmed: {launch_result}")
            time.sleep(1.0)
    for n in range(1,max_steps+1):
        try: image,width,height=_screen()
        except Exception as exc: return f"Computer-use failed to capture desktop: {exc}"
        window=_window(); decision=_decide(goal,history,image,width,height,window)
        if not decision: history.append({"step":str(n),"result":"No valid vision decision"}); time.sleep(.5); continue
        action=str(decision.get("action","")).lower().strip()
        if action=="done":
            ok,evidence=_verify(goal,history,image,width,height,window)
            if ok: return f"Computer-use completed and verified: {evidence}"
            history.append({"step":str(n),"result":f"Done claim rejected: {evidence}"}); continue
        result=_execute(decision); history.append({"step":str(n),"action":action,"result":result[:500]})
        print(f"[ComputerUse] step {n}: {action} -> {result[:200]}"); time.sleep(.4)
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
    "description":"PRIMARY TOOL FOR MULTI-STEP DESKTOP TASKS. Use this tool whenever the user asks JARVIS to operate an application or the Windows GUI across multiple steps: open/launch an app AND then click, type, create, edit, navigate, save, configure, or verify something in it. Examples: 'Open VS Code and create main.py', 'open Blender and make...', 'open WhatsApp and send...', 'open Settings and change...'. Pass the COMPLETE user goal unchanged in goal. Do NOT split such tasks between open_app, file_controller, terminal_advance, or computer_control. Observe the real screen, operate visible UI, re-observe, recover, and verify. Do not substitute terminal commands for GUI actions.",
    "parameters":{"type":"OBJECT","properties":{"goal":{"type":"STRING","description":"Complete user goal to accomplish through the desktop UI."},"max_steps":{"type":"INTEGER","description":"Maximum UI actions, default 12, maximum 30."},"verify_every":{"type":"INTEGER","description":"Verify progress every N actions, default 2."}},"required":["goal"]},
    "handler":computer_use,
}
