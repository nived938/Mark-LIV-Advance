"""Android TV / Google TV Remote v2 client used by smart-home controls."""
from __future__ import annotations

import asyncio
import re
import threading
import time
from pathlib import Path


class GoogleTVManager:
    def __init__(self):
        self._lock = threading.RLock()
        self._loop = None
        self._thread = None
        self._remotes = {}
        self._pairing = {}

    def _ensure_loop(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            ready = threading.Event()

            def runner():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                self._loop = loop
                ready.set()
                loop.run_forever()
                loop.close()

            self._thread = threading.Thread(
                target=runner,
                daemon=True,
                name="JARVIS-GoogleTV",
            )
            self._thread.start()

        ready.wait(5)

    def _run(self, coro, timeout=20):
        self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    @staticmethod
    def _safe_host(host):
        value = str(host or "").strip()
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", value):
            return ""
        return value.split(":", 1)[0]

    def _paths(self, host):
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", self._safe_host(host))
        base = Path(__file__).resolve().parent.parent / "memory" / "google_tv"
        base.mkdir(parents=True, exist_ok=True)
        return base / f"{safe}.cert.pem", base / f"{safe}.key.pem"

    async def _make_remote(self, host):
        from androidtvremote2 import AndroidTVRemote

        cert, key = self._paths(host)
        remote = AndroidTVRemote(
            "JARVIS Remote",
            str(cert),
            str(key),
            self._safe_host(host),
            enable_ime=True,
            enable_voice=False,
            loop=self._loop,
        )
        await remote.async_generate_cert_if_missing()
        return remote

    def discover(self, timeout: float = 3.0) -> str:
        """Discover Android TV/Google TV endpoints using mDNS."""
        try:
            from zeroconf import Zeroconf, ServiceBrowser, ServiceStateChange, ServiceInfo
        except Exception:
            return "zeroconf is not installed."

        found = []
        zc = Zeroconf()

        class Listener:
            def add_service(self, zc_obj, service_type, name):
                try:
                    info = ServiceInfo(service_type, name)
                    if info.request(zc_obj, 1500):
                        for addr in info.parsed_addresses():
                            found.append((name, addr, info.port))
                            break
                except Exception:
                    pass

            def remove_service(self, zc_obj, service_type, name):
                pass

            def update_service(self, zc_obj, service_type, name):
                pass

        listener = Listener()
        browser = ServiceBrowser(zc, "_androidtvremote2._tcp.local.", listener)
        time.sleep(max(1.0, min(10.0, float(timeout))))
        try:
            browser.cancel()
        except Exception:
            pass
        zc.close()

        unique = []
        seen = set()
        for name, host, port in found:
            key = (host, port)
            if key in seen:
                continue
            seen.add(key)
            unique.append(f"{name} — {host}:{port}")
        return (
            "Google TV devices discovered:\n" + "\n".join(unique[:20])
            if unique else
            "No Android TV/Google TV Remote Service was discovered."
        )

    def pair_start(self, host):
        host = self._safe_host(host)
        if not host:
            return "A valid Google TV IP address is required."
        try:
            remote = self._run(self._make_remote(host))
            self._run(remote.async_start_pairing(), timeout=12)
            with self._lock:
                self._pairing[host] = remote
            return (
                f"Pairing started for Google TV at {host}. "
                "Look at the TV for the pairing PIN, then call tv_pair_finish with that PIN."
            )
        except Exception as exc:
            return f"Google TV pairing could not start: {exc}"

    def pair_finish(self, host, pin):
        host = self._safe_host(host)
        code = str(pin or "").strip()
        with self._lock:
            remote = self._pairing.get(host)
        if not remote:
            return "No active Google TV pairing session exists for that IP. Start pairing first."
        try:
            self._run(remote.async_finish_pairing(code), timeout=15)
            with self._lock:
                self._pairing.pop(host, None)
                self._remotes[host] = remote
            self._run(remote.async_connect(), timeout=20)
            remote.keep_reconnecting()
            return f"Google TV at {host} is paired and connected."
        except Exception as exc:
            return f"Google TV pairing failed: {exc}"

    def connect(self, host):
        host = self._safe_host(host)
        if not host:
            return False, "A valid Google TV IP address is required."
        with self._lock:
            remote = self._remotes.get(host)
        try:
            if remote is None:
                remote = self._run(self._make_remote(host))
                with self._lock:
                    self._remotes[host] = remote
            self._run(remote.async_connect(), timeout=20)
            remote.keep_reconnecting()
            return True, ""
        except Exception as exc:
            return False, str(exc)

    def status(self, host):
        host = self._safe_host(host)
        with self._lock:
            remote = self._remotes.get(host)
        if remote is None:
            ok, error = self.connect(host)
            if not ok:
                return f"Google TV connection failed: {error}"
            with self._lock:
                remote = self._remotes.get(host)
        info = getattr(remote, "device_info", None)
        volume = getattr(remote, "volume_info", None)
        return (
            f"Google TV {host}: on={getattr(remote, 'is_on', None)}, "
            f"app={getattr(remote, 'current_app', None)}, "
            f"device={info}, volume={volume}"
        )

    def command(self, host, action, value=""):
        host = self._safe_host(host)
        action = str(action or "").strip().lower()

        with self._lock:
            remote = self._remotes.get(host)

        if remote is None:
            ok, error = self.connect(host)
            if not ok:
                return f"Google TV connection failed: {error}"
            with self._lock:
                remote = self._remotes.get(host)

        keys = {
            "power": "POWER",
            "home": "HOME",
            "back": "BACK",
            "up": "DPAD_UP",
            "down": "DPAD_DOWN",
            "left": "DPAD_LEFT",
            "right": "DPAD_RIGHT",
            "enter": "DPAD_CENTER",
            "volume_up": "VOLUME_UP",
            "volume_down": "VOLUME_DOWN",
            "mute": "VOLUME_MUTE",
            "play_pause": "MEDIA_PLAY_PAUSE",
            "channel_up": "CHANNEL_UP",
            "channel_down": "CHANNEL_DOWN",
        }

        try:
            if action == "status":
                return self.status(host)
            if action in keys:
                remote.send_key_command(keys[action])
                return f"Google TV {action.replace('_', ' ')} complete."
            if action == "text":
                if not value:
                    return "Text is required."
                remote.send_text(str(value))
                return "Text sent to Google TV."
            if action == "app":
                if not value:
                    return "An app deep link or app id is required."
                remote.send_launch_app_command(str(value))
                return f"Opened {value} on Google TV."
            return "TV action must be power, home, back, up, down, left, right, enter, volume_up, volume_down, mute, play_pause, channel_up, channel_down, text, app, or status."
        except Exception as exc:
            return f"Google TV command failed: {exc}"

    def stop(self):
        with self._lock:
            remotes = list(self._remotes.values())
            self._remotes.clear()
            self._pairing.clear()
        for remote in remotes:
            try:
                remote.disconnect()
            except Exception:
                pass
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass


GOOGLE_TV = GoogleTVManager()
