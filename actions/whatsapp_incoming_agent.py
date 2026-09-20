"""WhatsApp Windows desktop incoming-call agent.

WhatsApp Desktop can expose an incoming call in two stages on some Windows
builds: the chat first shows a "Calling..." / "Calling" call item, and clicking
that item opens the native call controls. This agent handles both stages.
It deliberately does not use WhatsApp Web.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

try:
    from pywinauto import Desktop
except Exception:
    Desktop = None

try:
    import psutil
except Exception:
    psutil = None


_GENERIC = {
    "whatsapp", "accept", "answer", "decline", "reject", "ignore",
    "cancel", "more", "device settings", "settings", "video call",
    "voice call", "audio call", "start video call", "start voice call",
    "calling", "calling...", "incoming call", "incoming call...",
}


@dataclass
class IncomingCall:
    caller: str
    window: object
    accept_control: object
    decline_control: object
    detected_at: float


class WhatsAppIncomingAgent:
    """Background detector/controller for WhatsApp Desktop incoming calls."""

    def __init__(
        self,
        on_incoming: Optional[Callable[[IncomingCall], None]] = None,
        poll_seconds: float = 0.5,
    ):
        self.on_incoming = on_incoming
        self.poll_seconds = max(0.25, float(poll_seconds))
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._pending: Optional[IncomingCall] = None
        self._last_signature = ""
        self._last_seen_at = 0.0
        self._last_bridge_click = 0.0

    @property
    def pending(self) -> Optional[IncomingCall]:
        with self._lock:
            return self._pending

    def start(self) -> None:
        if Desktop is None:
            print("[WhatsAppAgent] pywinauto is unavailable; incoming calls disabled.")
            return
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="WhatsAppIncomingAgent",
            daemon=True,
        )
        self._thread.start()
        print("[WhatsAppAgent] Incoming-call monitor started.")

    def stop(self) -> None:
        self._stop.set()

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    @staticmethod
    def _safe_text(control) -> str:
        try:
            return str(control.window_text() or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _safe_id(control) -> str:
        try:
            return str(getattr(control, "automation_id", lambda: "")() or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _safe_class(control) -> str:
        try:
            return str(getattr(control, "class_name", lambda: "")() or "").strip()
        except Exception:
            return ""

    def _is_whatsapp_process(self, control) -> bool:
        if psutil is None:
            return False
        try:
            pid = control.process_id()
            p = psutil.Process(pid)
            blob = " ".join([
                p.name(),
                p.exe() or "",
                " ".join(p.cmdline()),
            ]).lower()
            return "whatsapp" in blob
        except Exception:
            return False

    def _find_buttons(self, window):
        accept = decline = None
        try:
            controls = window.descendants(control_type="Button")
        except Exception:
            controls = []
        for control in controls:
            name = self._norm(self._safe_text(control))
            aid = self._norm(self._safe_id(control))
            if accept is None and (
                name in {"accept", "answer"}
                or "accept" in name
                or "answer" in name
                or "accept" in aid
                or "answer" in aid
            ):
                accept = control
            if decline is None and (
                name in {"decline", "reject", "ignore"}
                or "decline" in name
                or "reject" in name
                or "ignore" in name
                or any(x in aid for x in ("decline", "reject", "ignore"))
            ):
                decline = control
        return accept, decline

    def _extract_caller(self, window) -> str:
        texts = []
        try:
            title = self._safe_text(window)
            if title:
                texts.append(title)
        except Exception:
            pass

        try:
            for control in window.descendants():
                text = self._safe_text(control)
                if text:
                    texts.append(text)
        except Exception:
            pass

        for raw in texts:
            clean = re.sub(r"\s+", " ", raw).strip()
            for pattern in (
                r"(?:incoming\s+call\s+from|call\s+from|incoming\s+call|calling)\s*[:\-]?\s*(.+)$",
                r"^(.+?)\s+(?:is\s+)?calling$",
            ):
                m = re.search(pattern, clean, flags=re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip(" -:|.")
                    if candidate and self._norm(candidate) not in _GENERIC:
                        return candidate

        for raw in texts:
            clean = re.sub(r"\s+", " ", raw).strip(" -:|.")
            low = self._norm(clean)
            if not clean or low in _GENERIC:
                continue
            if len(clean) > 80 or clean.isdigit():
                continue
            if any(word in low for word in (
                "incoming", "call", "device", "microphone", "camera",
                "settings", "whatsapp", "calling",
            )):
                continue
            return clean
        return "someone"

    def _find_whatsapp_windows(self):
        if Desktop is None:
            return []
        try:
            return Desktop(backend="uia").windows(visible_only=False)
        except Exception:
            return []

    def _looks_like_whatsapp(self, window) -> bool:
        title = self._norm(self._safe_text(window))
        aid = self._norm(self._safe_id(window))
        if "whatsapp" in title or "whatsapp" in aid:
            return True
        return self._is_whatsapp_process(window)

    def _click_calling_bridge(self) -> bool:
        """Find the visible 'Calling...' call item in the WhatsApp chat and click it.

        Some WhatsApp Desktop builds do not expose the incoming call controls
        until the current chat's 'Calling...' item is activated. We therefore
        treat that item as a bridge into the real call dialog.
        """
        now = time.time()
        if now - self._last_bridge_click < 2.0:
            return False

        for window in self._find_whatsapp_windows():
            if not self._looks_like_whatsapp(window):
                continue

            candidates = [window]
            try:
                candidates.extend(window.descendants())
            except Exception:
                pass

            for control in candidates:
                text = self._norm(self._safe_text(control))
                if text not in {"calling", "calling...", "calling…"}:
                    continue

                # Do not click the entire application window. Prefer the
                # actual text control, then its clickable parent.
                click_targets = [control]
                try:
                    parent = control.parent()
                    if parent is not None:
                        click_targets.append(parent)
                except Exception:
                    pass

                for target in click_targets:
                    try:
                        target.click_input()
                        self._last_bridge_click = now
                        print("[WhatsAppAgent] Found WhatsApp 'Calling...' item; clicked it to open call controls.")
                        time.sleep(0.35)
                        return True
                    except Exception:
                        try:
                            target.invoke()
                            self._last_bridge_click = now
                            print("[WhatsAppAgent] Invoked WhatsApp 'Calling...' item to open call controls.")
                            time.sleep(0.35)
                            return True
                        except Exception:
                            pass
        return False

    def _find_incoming(self):
        if Desktop is None:
            return None

        windows = self._find_whatsapp_windows()

        # Stage 1: the chat contains a "Calling..." item. Clicking it should
        # reveal the native call controls on affected WhatsApp builds.
        self._click_calling_bridge()

        # Stage 2: after the bridge click, look again for Accept/Decline.
        # Search all UIA windows, because the native call surface can have a
        # caller-only title and no "WhatsApp" title.
        for window in windows:
            accept, decline = self._find_buttons(window)
            if accept is None or decline is None:
                continue

            whatsapp = self._looks_like_whatsapp(window)
            if not whatsapp:
                try:
                    sample = " ".join(
                        self._safe_text(x).lower()
                        for x in window.descendants()
                        if self._safe_text(x)
                    )
                    whatsapp = "whatsapp" in sample
                except Exception:
                    whatsapp = False
            if not whatsapp:
                # Native call windows may have a caller-only title. The
                # presence of both native call controls is strong evidence, but
                # still require a WhatsApp process somewhere in the ancestry.
                try:
                    whatsapp = self._is_whatsapp_process(window)
                except Exception:
                    whatsapp = False
            if not whatsapp:
                continue

            caller = self._extract_caller(window)
            return IncomingCall(
                caller=caller,
                window=window,
                accept_control=accept,
                decline_control=decline,
                detected_at=time.time(),
            )

        return None

    @staticmethod
    def _click(control) -> tuple[bool, str]:
        try:
            control.invoke()
            return True, ""
        except Exception:
            try:
                control.click_input()
                return True, ""
            except Exception as exc:
                return False, str(exc)

    def accept(self) -> tuple[bool, str]:
        with self._lock:
            call = self._pending
        if not call:
            return False, "There is no pending WhatsApp incoming call."
        fresh = self._find_incoming()
        control = fresh.accept_control if fresh else call.accept_control
        ok, error = self._click(control)
        if ok:
            with self._lock:
                self._pending = None
                self._last_signature = ""
        return ok, error

    def decline(self) -> tuple[bool, str]:
        with self._lock:
            call = self._pending
        if not call:
            return False, "There is no pending WhatsApp incoming call."
        fresh = self._find_incoming()
        control = fresh.decline_control if fresh else call.decline_control
        ok, error = self._click(control)
        if ok:
            with self._lock:
                self._pending = None
                self._last_signature = ""
        return ok, error

    def _run(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                call = self._find_incoming()
                if call is None:
                    with self._lock:
                        if self._pending and time.time() - self._last_seen_at > 120:
                            self._pending = None
                            self._last_signature = ""
                    continue

                signature = self._norm(call.caller)
                with self._lock:
                    already_pending = self._pending is not None
                    same_recent = (
                        signature == self._last_signature
                        and time.time() - self._last_seen_at < 5
                    )
                    if already_pending or same_recent:
                        continue
                    self._pending = call
                    self._last_signature = signature
                    self._last_seen_at = time.time()

                print(f"[WhatsAppAgent] Incoming call detected from {call.caller}.")
                if self.on_incoming:
                    try:
                        self.on_incoming(call)
                    except Exception as exc:
                        print(f"[WhatsAppAgent] Event callback failed: {exc}")
            except Exception as exc:
                print(f"[WhatsAppAgent] Detection error: {exc}")


_AGENT: Optional[WhatsAppIncomingAgent] = None


def get_incoming_agent() -> WhatsAppIncomingAgent:
    global _AGENT
    if _AGENT is None:
        _AGENT = WhatsAppIncomingAgent()
    return _AGENT


def start_incoming_call_agent(on_incoming: Callable[[IncomingCall], None]) -> WhatsAppIncomingAgent:
    agent = get_incoming_agent()
    agent.on_incoming = on_incoming
    agent.start()
    return agent
