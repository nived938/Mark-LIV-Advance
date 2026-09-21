"""Generic Windows desktop-call attention monitor.

Uses the Windows notification database and visible application windows for
supported desktop calling apps. WhatsApp is intentionally excluded.
"""
from __future__ import annotations

import ctypes
import os
import re
import sqlite3
import threading
import time
import xml.etree.ElementTree as ET
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    import psutil
except Exception:
    psutil = None


_APP_ALIASES = {
    "Microsoft Teams": ("teams", "msteams"),
    "Zoom": ("zoom",),
    "Discord": ("discord",),
    "Skype": ("skype",),
    "Telegram": ("telegram",),
    "Signal": ("signal",),
    "Webex": ("webex", "cisco webex"),
    "Google Meet": ("google meet", "meet.google.com"),
    "Messenger": ("messenger",),
    "Slack": ("slack",),
}

_CALL_HINTS = (
    "incoming call", "call from", "voice call", "video call", "incoming video",
    "incoming voice", "ringing", "is calling", "calling you", "join call",
    "answer call", "accept call", "decline call", "hang up", "end call",
)

_WINDOW_HINTS = (
    "incoming", "ringing", "calling", "voice call", "video call", "join call",
    "in a call", "on a call", "call",
)

_GENERIC = {
    "incoming call", "voice call", "video call", "calling", "ringing",
    "accept", "answer", "decline", "reject", "ignore", "join call",
}


@dataclass
class CallEvent:
    app: str
    title: str
    preview: str
    caller: str
    source: str
    notification_id: str = ""
    window_handle: int | None = None
    detected_at: float = 0.0

    @property
    def signature(self) -> str:
        raw = " | ".join((self.app, self.title, self.preview, self.caller))
        return re.sub(r"\s+", " ", raw).strip().casefold()[:600]


class CallAttentionMonitor:
    def __init__(
        self,
        on_call: Callable[[CallEvent], None] | None = None,
        interval: float = 1.0,
        ignored_apps: set[str] | None = None,
    ):
        self.on_call = on_call
        self.interval = max(0.5, float(interval))
        self.ignored_apps = {str(x).casefold() for x in (ignored_apps or set())}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._seen_notifications: set[str] = set()
        self._recent_events: dict[str, float] = {}
        self._logged_db_error = False

    @staticmethod
    def _db_path() -> Path | None:
        if os.name != "nt":
            return None
        base = os.environ.get("LOCALAPPDATA", "")
        if not base:
            return None
        path = Path(base) / "Microsoft" / "Windows" / "Notifications" / "wpndatabase.db"
        return path if path.exists() else None

    @staticmethod
    def _app_from_text(text: str, primary_id: str = "") -> str:
        blob = f"{text} {primary_id}".casefold()
        for app, aliases in _APP_ALIASES.items():
            if any(alias.casefold() in blob for alias in aliases):
                return app
        return ""

    @staticmethod
    def _caller(text: str) -> str:
        clean = " ".join(re.sub(r"\s+", " ", str(text or "")).split()).strip(" -:|.")
        patterns = (
            r"(?:incoming\s+(?:voice|video\s+)?call|call|voice\s+call|video\s+call)\s*(?:from|by)?\s*[:\-]?\s*(.+)$",
            r"^(.+?)\s+(?:is\s+)?calling(?:\s+you)?$",
            r"calling\s*[:\-]?\s*(.+)$",
        )
        for pattern in patterns:
            match = re.search(pattern, clean, flags=re.IGNORECASE)
            if match:
                candidate = match.group(1).strip(" -:|.")
                if candidate and candidate.casefold() not in _GENERIC and len(candidate) < 100:
                    return candidate
        for piece in re.split(r"[|\n]", clean):
            piece = piece.strip()
            low = piece.casefold()
            if not piece or low in _GENERIC or len(piece) > 80:
                continue
            if any(h in low for h in _CALL_HINTS):
                continue
            if any(alias in low for vals in _APP_ALIASES.values() for alias in vals):
                continue
            return piece
        return ""

    @staticmethod
    def _toast_text(payload: str) -> str:
        try:
            root = ET.fromstring(payload)
        except Exception:
            return ""
        out = []
        for element in root.iter():
            if element.tag.split("}")[-1] == "text" and element.text:
                value = str(element.text).strip()
                if value:
                    out.append(value)
        return " | ".join(out)

    def _poll_wpndb(self) -> list[CallEvent]:
        path = self._db_path()
        if path is None:
            return []
        events = []
        try:
            conn = sqlite3.connect(
                f"file:{path}?mode=ro",
                uri=True,
                timeout=1.5,
            )
            try:
                rows = conn.execute(
                    "SELECT n.Id, n.Payload, n.ArrivalTime, h.PrimaryId "
                    "FROM Notification n "
                    "LEFT JOIN NotificationHandler h ON n.HandlerId=h.Id "
                    "WHERE n.Type='toast' "
                    "ORDER BY n.ArrivalTime DESC LIMIT 80"
                ).fetchall()
            finally:
                conn.close()

            for notification_id, payload, arrival, primary_id in rows:
                key = str(notification_id)
                if key in self._seen_notifications:
                    continue
                self._seen_notifications.add(key)

                text = self._toast_text(str(payload or ""))
                blob = f"{primary_id or ''} {text}".strip()
                low = blob.casefold()
                if not any(hint in low for hint in _CALL_HINTS):
                    continue

                app = self._app_from_text(text, str(primary_id or ""))
                if not app or app.casefold() in self.ignored_apps:
                    continue

                events.append(
                    CallEvent(
                        app=app,
                        title=text[:180],
                        preview=text[:500],
                        caller=self._caller(text or blob),
                        source="wpndb",
                        notification_id=key,
                        detected_at=time.time(),
                    )
                )

            if len(self._seen_notifications) > 1000:
                self._seen_notifications = set(list(self._seen_notifications)[-500:])
        except sqlite3.Error as exc:
            if not self._logged_db_error:
                print(f"[CallAttention] WPN database unavailable: {exc}")
                self._logged_db_error = True
        except Exception as exc:
            if not self._logged_db_error:
                print(f"[CallAttention] WPN detector error: {exc}")
                self._logged_db_error = True
        return events

    def _poll_windows(self) -> list[CallEvent]:
        if os.name != "nt" or psutil is None:
            return []

        user32 = ctypes.windll.user32
        events = []
        enum_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        @enum_type
        def callback(hwnd, _):
            try:
                if not user32.IsWindowVisible(hwnd):
                    return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length <= 0:
                    return True

                title_buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, title_buf, length + 1)
                title = title_buf.value.strip()
                if not title:
                    return True

                pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                pid_value = int(pid.value)

                proc_name = ""
                try:
                    proc_name = psutil.Process(pid_value).name()
                except Exception:
                    pass

                blob = f"{proc_name} | {title}"
                app = self._app_from_text(blob)
                if not app or app.casefold() in self.ignored_apps:
                    return True

                low = blob.casefold()
                if not any(hint in low for hint in _WINDOW_HINTS):
                    return True
                if "call" not in low and not any(x in low for x in ("ringing", "incoming", "calling", "join")):
                    return True

                now = time.time()
                sig = f"{app}|{title}".casefold()
                if now - self._recent_events.get(f"window:{sig}", 0) < 8:
                    return True
                self._recent_events[f"window:{sig}"] = now

                events.append(
                    CallEvent(
                        app=app,
                        title=title[:180],
                        preview=title[:500],
                        caller=self._caller(title),
                        source="window",
                        window_handle=hwnd,
                        detected_at=now,
                    )
                )
            except Exception:
                pass
            return True

        try:
            user32.EnumWindows(callback, 0)
        except Exception:
            return []
        return events

    def _emit(self, event: CallEvent) -> None:
        now = time.time()
        previous = self._recent_events.get(f"event:{event.signature}", 0)
        if now - previous < 8:
            return
        self._recent_events[f"event:{event.signature}"] = now
        if self.on_call:
            try:
                self.on_call(event)
            except Exception as exc:
                print(f"[CallAttention] Callback failed: {exc}")

    def _run(self) -> None:
        while not self._stop.wait(self.interval):
            for event in self._poll_wpndb():
                self._emit(event)
            for event in self._poll_windows():
                self._emit(event)

    def start(self) -> None:
        if os.name != "nt":
            print("[CallAttention] Generic call monitor disabled on non-Windows.")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="CallAttentionMonitor",
        )
        self._thread.start()
        print("[CallAttention] Generic desktop-call detection started.")

    def stop(self) -> None:
        self._stop.set()


LAST_CALL: CallEvent | None = None
