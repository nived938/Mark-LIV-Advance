"""WhatsApp Windows desktop incoming-call agent.

Uses Windows UI Automation through pywinauto to watch for WhatsApp's native
incoming-call dialog. It deliberately does not use WhatsApp Web.
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
        poll_seconds: float = 0.7,
    ):
        self.on_incoming = on_incoming
        self.poll_seconds = max(0.3, float(poll_seconds))
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._pending: Optional[IncomingCall] = None
        self._last_signature = ""
        self._last_seen_at = 0.0

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

    def _find_buttons(self, window):
        accept = decline = None
        try:
            controls = window.descendants(control_type="Button")
        except Exception:
            controls = []
        for control in controls:
            name = self._norm(self._safe_text(control))
            aid = self._norm(self._safe_id(control))
            combined = f"{name} {aid}"
            if accept is None and (
                name in {"accept", "answer"}
                or "accept" in aid
                or "answer" in aid
            ):
                accept = control
            if decline is None and (
                name in {"decline", "reject", "ignore"}
                or any(x in aid for x in ("decline", "reject", "ignore"))
            ):
                decline = control
        return accept, decline

    def _extract_caller(self, window) -> str:
        """Extract the caller from fresh UIA text on every poll.

        WhatsApp can rebuild its call window while ringing, so cached controls
        are intentionally never reused for detection.
        """
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

        # Prefer explicit phrases exposed by the native call dialog.
        for raw in texts:
            clean = re.sub(r"\s+", " ", raw).strip()
            low = clean.lower()
            for pattern in (
                r"(?:incoming\s+call\s+from|call\s+from|incoming\s+call|calling)\s*[:\\-]?\s*(.+)$",
                r"^(.+?)\s+(?:is\s+)?calling$",
            ):
                m = re.search(pattern, clean, flags=re.IGNORECASE)
                if m:
                    candidate = m.group(1).strip(" -:|")
                    if candidate and self._norm(candidate) not in _GENERIC:
                        return candidate

        # Otherwise use a short non-generic text element. The native dialog
        # normally exposes the caller name separately from its buttons.
        for raw in texts:
            clean = re.sub(r"\s+", " ", raw).strip(" -:|")
            low = self._norm(clean)
            if not clean or low in _GENERIC:
                continue
            if len(clean) > 80:
                continue
            if any(word in low for word in (
                "incoming", "call", "device", "microphone", "camera",
                "settings", "whatsapp",
            )):
                continue
            if clean.isdigit():
                continue
            return clean
        return "someone"

    def _find_incoming(self):
        if Desktop is None:
            return None
        try:
            windows = Desktop(backend="uia").windows(visible_only=True)
        except Exception:
            return None

        for window in windows:
            title = self._safe_text(window)
            low_title = self._norm(title)
            # WhatsApp's incoming-call UI is a native dialog and exposes
            # Accept/Decline controls. Checking the controls prevents the main
            # WhatsApp window from being mistaken for a call.
            whatsapp_window = "whatsapp" in low_title or "whatsapp" in self._norm(self._safe_id(window))
            if not whatsapp_window and psutil is not None:
                try:
                    process_name = psutil.Process(window.process_id()).name().lower()
                    whatsapp_window = "whatsapp" in process_name
                except Exception:
                    pass
            if not whatsapp_window:
                # Some builds title the native call dialog with the caller name.
                # In that case require WhatsApp text somewhere in the fresh UIA
                # tree before accepting the window as a call.
                try:
                    sample = " ".join(
                        self._safe_text(x).lower()
                        for x in window.descendants()
                        if self._safe_text(x)
                    )
                    whatsapp_window = "whatsapp" in sample
                except Exception:
                    whatsapp_window = False
            if not whatsapp_window:
                continue
            accept, decline = self._find_buttons(window)
            if accept is None or decline is None:
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
        # Re-find the control before acting because WhatsApp can rebuild the
        # dialog between detection and the user's spoken response.
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
                    # If the ringing dialog disappeared without JARVIS receiving
                    # a response (for example the caller hung up), release the
                    # pending state so the next call can be announced.
                    with self._lock:
                        if self._pending and time.time() - self._last_seen_at > 120:
                            self._pending = None
                            self._last_signature = ""
                    continue
                signature = f"{self._norm(call.caller)}:{round(call.detected_at, 1)}"
                with self._lock:
                    already_pending = self._pending is not None
                    same_recent = (
                        signature.split(":")[0] == self._last_signature.split(":")[0]
                        and time.time() - self._last_seen_at < 5
                    )
                    if already_pending or same_recent:
                        continue
                    self._pending = call
                    self._last_signature = self._norm(call.caller)
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
