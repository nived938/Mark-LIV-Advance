"""
Mark 32 autonomous-agent foundation.

This module is deliberately dependency-light and Windows-first.  It provides the
state, safety, planning, verification, recovery, routing, vision, Android,
filesystem, terminal, browser, coding/testing, clipboard, camera, scheduling,
communications, cancellation and dashboard primitives used by Mark 32.
Existing Mark LIV actions remain available; this layer adds a single safe
orchestration surface rather than replacing them.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import json
import os
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import webbrowser
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = BASE_DIR / "memory" / "mark32"
STATE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = STATE_DIR / "mark32.db"
DASHBOARD_PATH = STATE_DIR / "dashboard.json"


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def _db():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    return con


def _init_db():
    with _db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(category, key)
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            result TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_at TEXT NOT NULL,
            task TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            channel TEXT NOT NULL DEFAULT '',
            address TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            UNIQUE(name, channel, address)
        );
        """)
_init_db()


class CancelToken:
    def __init__(self):
        self._event = threading.Event()
    def cancel(self):
        self._event.set()
    def reset(self):
        self._event.clear()
    def cancelled(self) -> bool:
        return self._event.is_set()
    def check(self):
        if self.cancelled():
            raise RuntimeError("TASK_CANCELLED")


class PermissionSystem:
    """Default-deny for destructive or external side effects."""

    SAFE = {
        "read", "search", "inspect", "screenshot", "status", "test",
        "plan", "verify", "open", "copy", "clipboard_read", "vision",
    }
    CONFIRM = {
        "delete", "shutdown", "restart", "send_message", "send_email",
        "make_call", "purchase", "install", "move", "rename", "write_external",
    }

    def __init__(self):
        self.enabled = True

    def check(self, operation: str, confirmed: bool = False) -> tuple[bool, str]:
        if not self.enabled:
            return True, "permissions disabled"
        op = operation.lower().strip()
        if op in self.SAFE:
            return True, "safe"
        if op in self.CONFIRM and not confirmed:
            return False, f"CONFIRMATION_REQUIRED:{op}"
        return True, "allowed"


class TaskStore:
    def create(self, goal: str) -> int:
        with _db() as con:
            cur = con.execute(
                "INSERT INTO tasks(goal,status,created_at,updated_at) VALUES(?,?,?,?)",
                (goal, "running", _now(), _now()),
            )
            return int(cur.lastrowid)

    def update(self, task_id: int, status: str, result: str = ""):
        with _db() as con:
            con.execute(
                "UPDATE tasks SET status=?,result=?,updated_at=? WHERE id=?",
                (status, result[:10000], _now(), task_id),
            )

    def recent(self, limit: int = 20):
        with _db() as con:
            return [dict(x) for x in con.execute(
                "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (max(1, min(limit, 100)),)
            ).fetchall()]


class LongTermMemory:
    def save(self, category: str, key: str, value: str) -> str:
        with _db() as con:
            con.execute("""
                INSERT INTO memory(category,key,value,created_at,updated_at)
                VALUES(?,?,?,?,?)
                ON CONFLICT(category,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at
            """, (category, key, value, _now(), _now()))
        return f"Saved memory {category}/{key}."

    def recall(self, query: str = "", category: str = "", limit: int = 20) -> list[dict]:
        q = f"%{query.lower()}%"
        with _db() as con:
            rows = con.execute("""
                SELECT category,key,value,updated_at FROM memory
                WHERE (?='' OR category=?)
                  AND (?='' OR lower(key) LIKE ? OR lower(value) LIKE ?)
                ORDER BY updated_at DESC LIMIT ?
            """, (category, category, query, q, q, max(1, min(limit, 100)))).fetchall()
        return [dict(x) for x in rows]


class TaskPlanner:
    """Deterministic planner. The live model can provide a richer plan; this is
    the reliable fallback that never invents tool calls."""

    def plan(self, goal: str) -> list[dict]:
        g = goal.strip()
        steps = []
        if not g:
            return steps
        low = g.lower()
        if any(x in low for x in ("find", "search", "locate")):
            steps.append({"tool": "deep_search", "description": "Find the requested resource"})
        if any(x in low for x in ("open", "launch", "start")):
            steps.append({"tool": "open", "description": "Open the requested application or URL"})
        if any(x in low for x in ("copy", "move", "rename", "delete", "create", "write")):
            steps.append({"tool": "file", "description": "Perform the requested file operation"})
        if any(x in low for x in ("run", "execute", "terminal", "command", "powershell")):
            steps.append({"tool": "terminal", "description": "Run the requested command"})
        if any(x in low for x in ("test", "pytest", "unittest", "verify")):
            steps.append({"tool": "test", "description": "Run verification tests"})
        if any(x in low for x in ("android", "phone", "adb")):
            steps.append({"tool": "android", "description": "Control the connected Android device"})
        if any(x in low for x in ("screen", "monitor", "look at", "see")):
            steps.append({"tool": "vision", "description": "Inspect the desktop"})
        if any(x in low for x in ("browser", "website", "url", "web page")):
            steps.append({"tool": "browser", "description": "Open or inspect the requested web page"})
        if not steps:
            steps.append({"tool": "route", "description": "Route the goal to the appropriate existing Mark action"})
        return steps


class Verifier:
    def verify(self, expected: str, result: str) -> dict:
        text = str(result or "")
        low = text.lower()
        failed = any(x in low for x in ("failed", "error", "exception", "denied", "not found", "cancelled"))
        return {
            "verified": bool(text.strip()) and not failed,
            "expected": expected,
            "observed": text[:2000],
        }


class ErrorRecovery:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts

    def run(self, operation: Callable[[], str], verify: Callable[[str], bool]) -> str:
        last = ""
        for _ in range(self.max_attempts):
            try:
                last = operation()
                if verify(last):
                    return last
            except Exception as exc:
                last = f"Error: {exc}"
            time.sleep(0.2)
        return last


class ToolRouter:
    """Intent router for Mark 32. Existing Mark actions remain the preferred
    execution path; these names are also useful to the autonomous agent."""

    ROUTES = {
        "file": ("file_search_advance", "file_manage_advance"),
        "terminal": ("terminal_advance", "terminal"),
        "browser": ("browser_advance", "browser_control"),
        "android": ("phone_advance",),
        "vision": ("screen_process",),
        "camera": ("camera_advance",),
        "clipboard": ("clipboard_advance",),
        "calendar": ("calendar_advance",),
        "email": ("email_advance",),
        "whatsapp": ("whatsapp_advance",),
        "coding": ("dev_agent", "code_helper"),
        "scheduler": ("schedule_advance",),
    }

    def route(self, intent: str) -> list[str]:
        low = intent.lower()
        for key, names in self.ROUTES.items():
            if key in low:
                return list(names)
        if any(x in low for x in ("file", "folder")):
            return list(self.ROUTES["file"])
        if any(x in low for x in ("code", "program", "build")):
            return list(self.ROUTES["coding"])
        return []


class VisionAgent:
    def monitors(self) -> list[dict]:
        try:
            import mss
            with mss.mss() as sct:
                return [
                    {"index": i, "left": m["left"], "top": m["top"],
                     "width": m["width"], "height": m["height"]}
                    for i, m in enumerate(sct.monitors[1:])
                ]
        except Exception as exc:
            return [{"error": str(exc)}]

    def screenshot(self, monitor: int | None = None, save: str = "") -> str:
        try:
            import mss
            from PIL import Image
            with mss.mss() as sct:
                mons = sct.monitors[1:]
                if not mons:
                    return "No monitors detected."
                idx = 0 if monitor is None else int(monitor)
                if idx < 0 or idx >= len(mons):
                    return f"Monitor {idx} does not exist."
                shot = sct.grab(mons[idx])
                path = Path(save) if save else STATE_DIR / f"screen-{idx}.png"
                Image.frombytes("RGB", shot.size, shot.rgb).save(path)
                return f"Captured monitor {idx}: {path}"
        except Exception as exc:
            return f"Screen capture failed: {exc}"


class VisualComputerControl:
    def click(self, x: int, y: int) -> str:
        try:
            import pyautogui
            pyautogui.click(int(x), int(y))
            return f"Clicked {x},{y}."
        except Exception as exc:
            return f"Visual click failed: {exc}"

    def move(self, x: int, y: int) -> str:
        try:
            import pyautogui
            pyautogui.moveTo(int(x), int(y), duration=0.15)
            return f"Moved pointer to {x},{y}."
        except Exception as exc:
            return f"Pointer move failed: {exc}"

    def type(self, text: str) -> str:
        try:
            import pyautogui
            pyautogui.write(str(text), interval=0.01)
            return "Typed text."
        except Exception as exc:
            return f"Typing failed: {exc}"


class AndroidAgent:
    def _adb(self, *args: str, timeout: int = 30) -> str:
        try:
            p = subprocess.run(["adb", *map(str, args)], capture_output=True,
                               text=True, timeout=timeout, encoding="utf-8", errors="replace")
            out = (p.stdout + p.stderr).strip()
            return out or ("ADB OK" if p.returncode == 0 else f"ADB exit {p.returncode}")
        except FileNotFoundError:
            return "ADB is not installed or not on PATH."
        except Exception as exc:
            return f"ADB failed: {exc}"

    def parallel_execute(self, goals: list[str]) -> list[str]:
        jobs = [{"goal": g} for g in goals if str(g).strip()]
        return self.parallel.run(jobs, lambda job: self.execute(job["goal"]), self.cancel)

    def status(self) -> str:
        return self._adb("devices")

    def shell(self, command: str) -> str:
        return self._adb("shell", command)

    def tap(self, x: int, y: int) -> str:
        return self._adb("shell", "input", "tap", str(x), str(y))

    def text(self, value: str) -> str:
        return self._adb("shell", "input", "text", value.replace(" ", "%s"))

    def key(self, keycode: str) -> str:
        return self._adb("shell", "input", "keyevent", str(keycode))


class FileAgent:
    def search(self, query: str, root: str = "", limit: int = 30) -> list[str]:
        base = Path(root).expanduser() if root else Path.home()
        if not base.exists():
            return []
        q = query.lower().strip()
        out = []
        skip = {".git", "node_modules", "__pycache__", ".venv", "venv"}
        for current, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d.lower() not in skip]
            for name in files + dirs:
                if not q or q in name.lower():
                    out.append(str(Path(current) / name))
                    if len(out) >= max(1, min(limit, 100)):
                        return out
        return out

    def manage(self, operation: str, source: str, destination: str = "") -> str:
        src = Path(source).expanduser()
        if operation == "open":
            if os.name == "nt":
                os.startfile(src)
            else:
                webbrowser.open(src.as_uri())
            return f"Opened {src}."
        if operation == "copy":
            shutil.copy2(src, Path(destination).expanduser())
            return f"Copied {src} to {destination}."
        if operation == "move":
            shutil.move(str(src), destination)
            return f"Moved {src} to {destination}."
        if operation == "rename":
            src.rename(destination)
            return f"Renamed {src}."
        if operation == "delete":
            if src.is_dir():
                shutil.rmtree(src)
            else:
                src.unlink()
            return f"Deleted {src}."
        return f"Unknown file operation: {operation}"


class TerminalAgent:
    def run(self, command: str, cwd: str = "", timeout: int = 60) -> str:
        if not command.strip():
            return "No command supplied."
        p = subprocess.run(command, shell=True, cwd=(cwd or None),
                           capture_output=True, text=True, timeout=max(1, min(timeout, 600)),
                           encoding="utf-8", errors="replace")
        out = (p.stdout + p.stderr).strip()
        return f"exit={p.returncode}\n{out}"[:12000]


class CodingTestingAgent:
    def test(self, path: str, command: str = "") -> str:
        target = Path(path).expanduser()
        if command:
            return TerminalAgent().run(command, cwd=str(target if target.is_dir() else target.parent), timeout=300)
        if (target / "pytest.ini").exists() or (target / "pyproject.toml").exists():
            return TerminalAgent().run("python -m pytest -q", cwd=str(target), timeout=300)
        if (target / "package.json").exists():
            return TerminalAgent().run("npm test -- --runInBand", cwd=str(target), timeout=300)
        return "No automatic test command was detected."

    def inspect_python(self, path: str) -> str:
        return TerminalAgent().run(f'python -m py_compile "{path}"', timeout=120)


class BrowserAgent:
    def open(self, url: str) -> str:
        webbrowser.open(url)
        return f"Opened {url}."

    def fetch(self, url: str) -> str:
        try:
            import requests
            r = requests.get(url, timeout=20)
            return f"HTTP {r.status_code}\n{r.text[:8000]}"
        except Exception as exc:
            return f"Browser fetch failed: {exc}"


class ClipboardAgent:
    def read(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception as exc:
            return f"Clipboard read failed: {exc}"

    def write(self, text: str) -> str:
        try:
            import pyperclip
            pyperclip.copy(text)
            return "Clipboard updated."
        except Exception as exc:
            return f"Clipboard write failed: {exc}"


class CameraAgent:
    def capture(self, path: str = "") -> str:
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ok, frame = cap.read()
            cap.release()
            if not ok:
                return "Camera capture failed."
            out = Path(path) if path else STATE_DIR / "camera.jpg"
            cv2.imwrite(str(out), frame)
            return f"Saved camera image to {out}."
        except Exception as exc:
            return f"Camera failed: {exc}"


class NotificationAgent:
    def notify(self, title: str, message: str) -> str:
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title or "Mark 32", message, duration=5, threaded=True)
            return "Notification sent."
        except Exception as exc:
            return f"Notification unavailable: {exc}"


class SchedulerAgent:
    def add(self, run_at: str, task: str) -> str:
        try:
            parsed = dt.datetime.fromisoformat(run_at)
        except ValueError:
            return "run_at must be ISO datetime, e.g. 2026-09-20T18:30:00"
        with _db() as con:
            cur = con.execute(
                "INSERT INTO schedules(run_at,task,status,created_at) VALUES(?,?,?,?)",
                (parsed.isoformat(), task, "pending", _now()),
            )
            return f"Scheduled task #{cur.lastrowid} for {parsed.isoformat()}."

    def list(self) -> list[dict]:
        with _db() as con:
            return [dict(x) for x in con.execute(
                "SELECT * FROM schedules WHERE status='pending' ORDER BY run_at"
            ).fetchall()]


class ContactAgent:
    def save(self, name: str, channel: str = "", address: str = "", notes: str = "") -> str:
        with _db() as con:
            con.execute("""
                INSERT INTO contacts(name,channel,address,notes) VALUES(?,?,?,?)
                ON CONFLICT(name,channel,address) DO UPDATE SET notes=excluded.notes
            """, (name, channel, address, notes))
        return f"Saved contact {name}."
    def search(self, query: str) -> list[dict]:
        with _db() as con:
            rows = con.execute(
                "SELECT * FROM contacts WHERE lower(name) LIKE ? OR lower(address) LIKE ?",
                (f"%{query.lower()}%", f"%{query.lower()}%")
            ).fetchall()
        return [dict(x) for x in rows]


class CommunicationAgent:
    """Uses OS/web intents rather than pretending an external message was sent."""

    def compose_email(self, to: str, subject: str = "", body: str = "") -> str:
        from urllib.parse import quote
        url = f"mailto:{quote(to)}?subject={quote(subject)}&body={quote(body)}"
        webbrowser.open(url)
        return f"Opened email composer for {to}."

    def compose_sms(self, number: str, body: str = "") -> str:
        webbrowser.open(f"sms:{number}?body={body}")
        return f"Opened SMS composer for {number}."


class ParallelAgent:
    def run(self, jobs: list[dict], worker: Callable[[dict], str], cancel: CancelToken) -> list[str]:
        cancel.check()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(8, len(jobs)))) as pool:
            futures = [pool.submit(worker, job) for job in jobs]
            out = []
            for future in futures:
                cancel.check()
                out.append(future.result())
            return out


class Mark32Engine:
    def __init__(self):
        self.cancel = CancelToken()
        self.permissions = PermissionSystem()
        self.store = TaskStore()
        self.memory = LongTermMemory()
        self.planner = TaskPlanner()
        self.verifier = Verifier()
        self.recovery = ErrorRecovery()
        self.router = ToolRouter()
        self.vision = VisionAgent()
        self.control = VisualComputerControl()
        self.android = AndroidAgent()
        self.files = FileAgent()
        self.terminal = TerminalAgent()
        self.coding = CodingTestingAgent()
        self.browser = BrowserAgent()
        self.clipboard = ClipboardAgent()
        self.camera = CameraAgent()
        self.scheduler = SchedulerAgent()
        self.contacts = ContactAgent()
        self.communication = CommunicationAgent()
        self.notifications = NotificationAgent()
        self.parallel = ParallelAgent()
        self._lock = threading.RLock()
        self._write_dashboard()

    def _write_dashboard(self):
        payload = {
            "name": "Mark 32",
            "updated_at": _now(),
            "cancelled": self.cancel.cancelled(),
            "monitors": self.vision.monitors(),
            "recent_tasks": self.store.recent(10),
            "schedules": self.scheduler.list(),
        }
        DASHBOARD_PATH.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    def cancel_all(self) -> str:
        self.cancel.cancel()
        self._write_dashboard()
        return "All Mark 32 running tasks have been cancelled."

    def reset_cancel(self) -> str:
        self.cancel.reset()
        return "Cancellation state cleared."

    def plan(self, goal: str) -> list[dict]:
        return self.planner.plan(goal)

    def execute(self, goal: str, confirmed: bool = False) -> str:
        """Execute the safe deterministic part of a multi-step goal."""
        task_id = self.store.create(goal)
        self.cancel.reset()
        steps = self.plan(goal)
        results = []
        try:
            for step in steps:
                self.cancel.check()
                desc = step["description"]
                tool = step["tool"]
                if tool == "deep_search":
                    result = "\n".join(self.files.search(goal, limit=20)) or "No matching files found."
                elif tool == "terminal":
                    ok, reason = self.permissions.check("write_external", confirmed)
                    result = reason if not ok else self.terminal.run(goal, timeout=120)
                elif tool == "test":
                    result = self.coding.test(".", "")
                elif tool == "vision":
                    result = self.vision.screenshot()
                elif tool == "browser":
                    urls = re.findall(r"https?://[^\s]+", goal)
                    result = self.browser.open(urls[0]) if urls else "No URL found; use the browser action directly."
                elif tool == "android":
                    result = self.android.status()
                else:
                    result = f"ROUTE_REQUIRED:{desc}"
                check = self.verifier.verify(desc, result)
                results.append({"step": step, "result": result, "verification": check})
                if not check["verified"] and tool != "route":
                    raise RuntimeError(f"Self-verification failed for: {desc}")
            payload = {"task_id": task_id, "goal": goal, "status": "completed", "steps": results}
            result = json.dumps(payload, indent=2)
            self.store.update(task_id, "completed", result)
            self._write_dashboard()
            return result
        except Exception as exc:
            self.store.update(task_id, "failed", str(exc))
            self._write_dashboard()
            return f"Task failed after verification/recovery: {exc}"

    def status(self) -> str:
        self._write_dashboard()
        return json.dumps({
            "dashboard": str(DASHBOARD_PATH),
            "cancelled": self.cancel.cancelled(),
            "recent_tasks": self.store.recent(10),
            "schedules": self.scheduler.list(),
            "monitors": self.vision.monitors(),
        }, indent=2)


ENGINE = Mark32Engine()
