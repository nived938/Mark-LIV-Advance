"""New standalone JARVIS utility services.

This module contains lightweight desktop capabilities that are intentionally
separate from the Mark32 task engine: location/geofencing, network inspection,
Wi-Fi analysis, school timetable, screen time, presentation control, data usage,
and QR scanning.
"""

from __future__ import annotations

import ipaddress
import json
import os
import platform
import re
import socket
import subprocess
import threading
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

try:
    import psutil
except Exception:
    psutil = None

try:
    import pyautogui
except Exception:
    pyautogui = None


ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = ROOT / "memory"
LOCATION_FILE = MEMORY_DIR / "devices.json"
GEOFENCE_FILE = MEMORY_DIR / "geofences.json"
SCHOOL_FILE = MEMORY_DIR / "school_timetable.json"
SCREEN_FILE = MEMORY_DIR / "screen_time.json"
DATA_FILE = MEMORY_DIR / "data_usage.json"

_LOCK = threading.RLock()


def _load(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _save(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _http_get(url: str, timeout: int = 10, **kwargs):
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", "JARVIS-Mark-LIV/1.0")
    r = requests.get(url, timeout=timeout, headers=headers, **kwargs)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------

def ip_location(ip: str = "") -> dict:
    target = str(ip or "").strip()
    url = f"https://ipinfo.io/{quote(target)}/json" if target else "https://ipinfo.io/json"
    data = _http_get(url, timeout=8).json()
    loc = str(data.get("loc") or "")
    lat = lon = None
    if "," in loc:
        try:
            lat, lon = [float(x) for x in loc.split(",", 1)]
        except Exception:
            pass
    data["latitude"] = lat
    data["longitude"] = lon
    return data


def save_device(name: str, latitude: float | None = None, longitude: float | None = None,
                ip: str = "", note: str = "") -> str:
    name = str(name or "").strip()
    if not name:
        return "Device name is required."
    devices = _load(LOCATION_FILE, {})
    if not isinstance(devices, dict):
        devices = {}
    entry = dict(devices.get(name, {}))
    entry.update({
        "name": name,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "ip": str(ip or "").strip(),
        "note": str(note or "").strip(),
    })
    if latitude is not None and longitude is not None:
        entry["latitude"] = float(latitude)
        entry["longitude"] = float(longitude)
    devices[name] = entry
    _save(LOCATION_FILE, devices)
    return f"Saved location record for {name}."


def list_devices() -> list[dict]:
    data = _load(LOCATION_FILE, {})
    return list(data.values()) if isinstance(data, dict) else []


def device_location(name: str) -> dict:
    devices = _load(LOCATION_FILE, {})
    entry = devices.get(name)
    if not isinstance(entry, dict):
        raise ValueError(f"No saved device named '{name}'.")
    if entry.get("latitude") is not None and entry.get("longitude") is not None:
        return entry
    if entry.get("ip"):
        geo = ip_location(entry["ip"])
        entry.update({
            "latitude": geo.get("latitude"),
            "longitude": geo.get("longitude"),
            "city": geo.get("city"),
            "region": geo.get("region"),
            "country": geo.get("country"),
            "org": geo.get("org"),
        })
        devices[name] = entry
        _save(LOCATION_FILE, devices)
        return entry
    return entry


def google_maps_url(latitude: float, longitude: float, label: str = "") -> str:
    q = quote(f"{latitude},{longitude}" + (f" ({label})" if label else ""))
    return f"https://www.google.com/maps/search/?api=1&query={q}"


def find_device_web_url() -> str:
    # Kept as a website view instead of attempting to scrape Google's private
    # Find My Device account data. The user can use their own signed-in session.
    return "https://www.google.com/android/find/"


# ---------------------------------------------------------------------------
# Geofencing
# ---------------------------------------------------------------------------

def _distance_km(lat1, lon1, lat2, lon2) -> float:
    from math import asin, cos, radians, sin, sqrt
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(min(1.0, sqrt(a)))


def add_geofence(name: str, latitude: float, longitude: float, radius_m: float,
                 instruction: str = "") -> str:
    name = str(name or "").strip()
    if not name:
        return "Geofence name is required."
    data = _load(GEOFENCE_FILE, {})
    if not isinstance(data, dict):
        data = {}
    data[name] = {
        "name": name,
        "latitude": float(latitude),
        "longitude": float(longitude),
        "radius_m": max(25.0, float(radius_m)),
        "instruction": str(instruction or "").strip(),
        "inside": None,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    _save(GEOFENCE_FILE, data)
    return f"Geofence '{name}' saved."


def list_geofences() -> list[dict]:
    data = _load(GEOFENCE_FILE, {})
    return list(data.values()) if isinstance(data, dict) else []


def remove_geofence(name: str) -> str:
    data = _load(GEOFENCE_FILE, {})
    if name not in data:
        return f"Geofence '{name}' was not found."
    del data[name]
    _save(GEOFENCE_FILE, data)
    return f"Geofence '{name}' removed."


def check_geofences(player=None) -> list[str]:
    fences = _load(GEOFENCE_FILE, {})
    if not isinstance(fences, dict) or not fences:
        return []
    try:
        geo = ip_location()
        lat, lon = geo.get("latitude"), geo.get("longitude")
        if lat is None or lon is None:
            return []
    except Exception:
        return []

    events = []
    changed = False
    for name, fence in list(fences.items()):
        try:
            km = _distance_km(
                float(lat), float(lon),
                float(fence["latitude"]), float(fence["longitude"])
            )
            inside = km * 1000 <= float(fence["radius_m"])
            previous = fence.get("inside")
            fence["distance_m"] = round(km * 1000)
            fence["checked_at"] = datetime.now().isoformat(timespec="seconds")
            if previous is not None and bool(previous) != inside:
                state = "entered" if inside else "left"
                events.append(f"{name}: {state}")
                instruction = str(fence.get("instruction") or "").strip()
                if instruction and player is not None:
                    try:
                        player.on_text_command(
                            f"[GEOFENCE EVENT] {name} {state}. Execute this instruction if appropriate: {instruction}"
                        )
                    except Exception:
                        pass
            fence["inside"] = inside
            changed = True
        except Exception:
            continue
    if changed:
        _save(GEOFENCE_FILE, fences)
    return events


class GeofenceMonitor:
    def __init__(self, interval: float = 90.0):
        self.interval = max(30.0, float(interval))
        self._stop = threading.Event()
        self._thread = None
        self.player = None

    def start(self, player=None):
        self.player = player
        if self._thread and self._thread.is_alive():
            return
        if not _load(GEOFENCE_FILE, {}):
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="JARVIS-Geofence")
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.wait(self.interval):
            check_geofences(self.player)


GEOFENCE_MONITOR = GeofenceMonitor()


# ---------------------------------------------------------------------------
# Internet/network diagnostics
# ---------------------------------------------------------------------------

def internet_diagnostics(host: str = "1.1.1.1", url: str = "https://www.google.com") -> str:
    parts = []
    try:
        started = time.perf_counter()
        socket.gethostbyname(host)
        parts.append(f"DNS {host}: {((time.perf_counter() - started) * 1000):.0f} ms")
    except Exception as exc:
        parts.append(f"DNS {host}: FAILED ({exc})")

    try:
        started = time.perf_counter()
        r = _http_get(url, timeout=8)
        ms = (time.perf_counter() - started) * 1000
        parts.append(f"HTTP {url}: {r.status_code} in {ms:.0f} ms")
    except Exception as exc:
        parts.append(f"HTTP {url}: FAILED ({exc})")

    if platform.system() == "Windows":
        try:
            out = subprocess.run(
                ["ping", "-n", "2", host],
                capture_output=True, text=True, timeout=8,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            times = re.findall(r"time[=<]\s*(\d+)ms", out.stdout or "", re.I)
            parts.append(
                f"Ping {host}: {', '.join(times)} ms"
                if times else f"Ping {host}: {'OK' if out.returncode == 0 else 'FAILED'}"
            )
        except Exception as exc:
            parts.append(f"Ping: FAILED ({exc})")

    try:
        geo = ip_location()
        public_ip = geo.get("ip", "unknown")
        parts.append(
            f"Public IP: {public_ip} | {geo.get('city','?')}, {geo.get('country','?')}"
        )
    except Exception:
        pass
    return "JARVIS INTERNET DIAGNOSTICS\n" + "\n".join(parts)


def network_devices() -> list[dict]:
    if platform.system() != "Windows":
        return []
    rows = []
    seen = set()
    commands = [
        ["arp", "-a"],
        ["netsh", "interface", "ip", "show", "neighbors"],
    ]
    for cmd in commands:
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=8,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).stdout
        except Exception:
            continue
        for line in out.splitlines():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+).*?([0-9a-f]{2}(?:[-:][0-9a-f]{2}){5})", line, re.I)
            if m:
                ip, mac = m.group(1), m.group(2).replace("-", ":").lower()
                if (ip, mac) in seen:
                    continue
                seen.add((ip, mac))
                rows.append({"ip": ip, "mac": mac, "source": cmd[0]})
    return rows


def wifi_analyzer() -> list[dict]:
    if platform.system() != "Windows":
        return []
    try:
        out = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
    except Exception:
        return []

    current = None
    result = []
    for raw in out.splitlines():
        line = raw.strip()
        if re.match(r"^SSID\s+\d+\s*:", line, re.I):
            ssid = line.split(":", 1)[1].strip()
            current = {"ssid": ssid, "signal": None, "channel": None, "authentication": None}
            result.append(current)
        elif current and re.match(r"^Signal\s*:", line, re.I):
            current["signal"] = line.split(":", 1)[1].strip()
        elif current and re.match(r"^Channel\s*:", line, re.I):
            current["channel"] = line.split(":", 1)[1].strip()
        elif current and re.match(r"^Authentication\s*:", line, re.I):
            current["authentication"] = line.split(":", 1)[1].strip()
    return result


# ---------------------------------------------------------------------------
# School timetable
# ---------------------------------------------------------------------------

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def school_add(subject: str, day: str, start: str, end: str = "", room: str = "", teacher: str = "") -> str:
    day = str(day or "").strip().lower()
    if day not in WEEKDAYS:
        return "Day must be Monday through Sunday."
    subject = str(subject or "").strip()
    if not subject:
        return "Subject is required."
    data = _load(SCHOOL_FILE, [])
    if not isinstance(data, list):
        data = []
    row = {
        "id": f"{int(time.time() * 1000)}",
        "subject": subject,
        "day": day,
        "start": str(start or "").strip(),
        "end": str(end or "").strip(),
        "room": str(room or "").strip(),
        "teacher": str(teacher or "").strip(),
    }
    data.append(row)
    _save(SCHOOL_FILE, data)
    return f"Added {subject} on {day.title()} at {row['start']}."


def school_list(day: str = "") -> list[dict]:
    data = _load(SCHOOL_FILE, [])
    if not isinstance(data, list):
        return []
    day = str(day or "").strip().lower()
    if day:
        data = [x for x in data if str(x.get("day", "")).lower() == day]
    return sorted(data, key=lambda x: (x.get("day", ""), x.get("start", "")))


def school_remove(item_id: str) -> str:
    data = _load(SCHOOL_FILE, [])
    before = len(data) if isinstance(data, list) else 0
    data = [x for x in data if str(x.get("id")) != str(item_id)]
    _save(SCHOOL_FILE, data)
    return "Timetable item removed." if len(data) != before else "Timetable item not found."


def school_today() -> list[dict]:
    return school_list(WEEKDAYS[datetime.now().weekday()])


# ---------------------------------------------------------------------------
# Screen time
# ---------------------------------------------------------------------------

class ScreenTimeTracker:
    def __init__(self, interval: float = 15.0):
        self.interval = max(5.0, float(interval))
        self._stop = threading.Event()
        self._thread = None
        self.enabled = False

    def start(self):
        if self._thread and self._thread.is_alive():
            self.enabled = True
            return
        self.enabled = True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="JARVIS-ScreenTime")
        self._thread.start()

    def stop(self):
        self.enabled = False
        self._stop.set()

    @staticmethod
    def _active_app() -> str:
        if platform.system() != "Windows":
            return "desktop"
        try:
            import pygetwindow
            win = pygetwindow.getActiveWindow()
            title = str(win.title if win else "").strip()
            return title[:100] if title else "Windows Desktop"
        except Exception:
            return "Windows Desktop"

    def _run(self):
        while not self._stop.wait(self.interval):
            app = self._active_app()
            data = _load(SCREEN_FILE, {"date": datetime.now().date().isoformat(), "apps": {}})
            today = datetime.now().date().isoformat()
            if data.get("date") != today:
                data = {"date": today, "apps": {}}
            data["apps"][app] = float(data["apps"].get(app, 0.0)) + self.interval
            _save(SCREEN_FILE, data)


SCREEN_TRACKER = ScreenTimeTracker()


def screen_time_status() -> dict:
    data = _load(SCREEN_FILE, {"date": datetime.now().date().isoformat(), "apps": {}})
    if data.get("date") != datetime.now().date().isoformat():
        return {"date": datetime.now().date().isoformat(), "apps": {}, "tracking": SCREEN_TRACKER.enabled}
    apps = sorted(
        [{"app": k, "seconds": round(float(v))} for k, v in data.get("apps", {}).items()],
        key=lambda x: x["seconds"],
        reverse=True,
    )
    return {"date": data.get("date"), "apps": apps, "tracking": SCREEN_TRACKER.enabled}


def screen_time_reset() -> str:
    _save(SCREEN_FILE, {"date": datetime.now().date().isoformat(), "apps": {}})
    return "Today's screen-time data was reset."


# ---------------------------------------------------------------------------
# Presentation remote
# ---------------------------------------------------------------------------

PRESENTATION_KEYS = {
    "next": "right",
    "previous": "left",
    "prev": "left",
    "start": "f5",
    "escape": "esc",
    "end": "esc",
    "black": "b",
    "white": "w",
}


def presentation_control(action: str) -> str:
    action = str(action or "").strip().lower()
    if not pyautogui:
        return "pyautogui is not available."
    key = PRESENTATION_KEYS.get(action)
    if key is None:
        return "Use next, previous, start, escape/end, black, or white."
    try:
        pyautogui.press(key)
        return f"Presentation command sent: {action}."
    except Exception as exc:
        return f"Presentation control failed: {exc}"


# ---------------------------------------------------------------------------
# Data usage
# ---------------------------------------------------------------------------

def data_usage_status() -> dict:
    if psutil is None:
        return {"error": "psutil is unavailable."}
    stats = psutil.net_io_counters()
    data = _load(DATA_FILE, {})
    if not isinstance(data, dict):
        data = {}
    today = datetime.now().date().isoformat()
    baseline = data.get("baseline")
    if data.get("date") != today or not isinstance(baseline, dict):
        baseline = {"sent": int(stats.bytes_sent), "recv": int(stats.bytes_recv)}
        data = {"date": today, "baseline": baseline}
        _save(DATA_FILE, data)
    sent = max(0, int(stats.bytes_sent) - int(baseline.get("sent", stats.bytes_sent)))
    recv = max(0, int(stats.bytes_recv) - int(baseline.get("recv", stats.bytes_recv)))
    active = []
    try:
        by_pid = {}
        for conn in psutil.net_connections(kind="inet"):
            pid = conn.pid
            if pid:
                by_pid[pid] = by_pid.get(pid, 0) + 1
        for pid, count in sorted(by_pid.items(), key=lambda x: x[1], reverse=True)[:15]:
            try:
                name = psutil.Process(pid).name()
            except Exception:
                name = str(pid)
            active.append({"process": name, "pid": pid, "connections": count})
    except Exception:
        pass
    return {
        "date": today,
        "sent_bytes": sent,
        "received_bytes": recv,
        "total_bytes": sent + recv,
        "top_active_processes": active,
        "note": "Windows exposes reliable system totals here; the process list is active-connection based, not per-process byte accounting.",
    }


# ---------------------------------------------------------------------------
# QR scanning
# ---------------------------------------------------------------------------

def scan_qr_screen(monitor_index: int = 0) -> str:
    """Scan a QR code from the full desktop or a specific monitor.

    monitor_index=0 captures the full virtual desktop; 1, 2, ... target an
    individual physical monitor in MSS order.
    """
    import cv2
    import mss
    import numpy as np
    with mss.mss() as sct:
        try:
            idx = int(monitor_index)
        except Exception:
            idx = 0
        if idx < 0 or idx >= len(sct.monitors):
            idx = 0
        monitor = sct.monitors[idx]
        frame = np.array(sct.grab(monitor))
    bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
    detector = cv2.QRCodeDetector()
    value, points, _ = detector.detectAndDecode(bgr)
    return str(value or "").strip()


def scan_qr_camera(player=None, timeout: float = 30.0) -> str:
    """Scan QR codes using JARVIS's single embedded camera stream.

    Reusing the existing stream avoids opening two VideoCapture handles on the
    same webcam, which can fail on Windows with many camera drivers.
    """
    import cv2
    import numpy as np

    started_here = False
    if player is not None:
        try:
            active = bool(player.camera_stream_active())
        except Exception:
            active = False
        if not active:
            player.start_camera_stream()
            started_here = True

    deadline = time.monotonic() + max(5.0, float(timeout))
    try:
        while time.monotonic() < deadline:
            frame_bytes = None
            if player is not None:
                try:
                    frame_bytes = player.get_latest_camera_frame()
                except Exception:
                    frame_bytes = None
            if not frame_bytes:
                time.sleep(0.05)
                continue

            frame = cv2.imdecode(
                np.frombuffer(frame_bytes, dtype=np.uint8),
                cv2.IMREAD_COLOR,
            )
            if frame is None:
                time.sleep(0.03)
                continue

            value, points, _ = cv2.QRCodeDetector().detectAndDecode(frame)
            value = str(value or "").strip()
            if value:
                return value
            time.sleep(0.03)
    finally:
        if started_here and player is not None:
            player.stop_camera_stream()
    return ""


def open_qr_result(value: str) -> str:
    value = str(value or "").strip()
    if not value:
        return "No QR code was detected."
    if not re.match(r"^https?://", value, re.I):
        return f"QR detected: {value}"
    webbrowser.open(value, new=2)
    return f"QR detected and opened: {value}"


def format_rows(title: str, rows) -> str:
    if not rows:
        return title + "\nNo results."
    return title + "\n" + "\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
