"""Small, real smart-home service for JARVIS.

Integrations:
- TinyTuya local LAN devices.
- Android TV Remote v2 devices, including Panasonic models that run Google TV.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from core.google_tv import GOOGLE_TV

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "memory" / "smart_home_devices.json"


def _load() -> dict:
    try:
        data = json.loads(STATE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("tuya", [])
            data.setdefault("google_tv", [])
            return data
    except Exception:
        pass
    return {"tuya": [], "google_tv": []}


def _save(data: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(STATE)


def _safe(value: str, default: str) -> str:
    value = re.sub(r"\s+", " ", str(value or "").strip())
    return value[:100] if value else default


class SmartHomeService:
    def list_devices(self) -> list[dict]:
        data = _load()
        out = []
        for item in data.get("google_tv", []):
            out.append({
                "type": "google_tv",
                "name": item.get("name", "Google TV"),
                "brand": item.get("brand", ""),
                "host": item.get("host", ""),
            })
        for item in data.get("tuya", []):
            out.append({
                "type": "tuya",
                "name": item.get("name", "Tuya device"),
                "brand": "Tuya / Smart Life",
                "host": item.get("ip", ""),
            })
        return out

    def add_google_tv(self, name: str, host: str, brand: str = "Panasonic") -> str:
        data = _load()
        name = _safe(name, "Panasonic Google TV")
        host = _safe(host, "")
        if not host:
            return "Google TV IP address is required."
        items = data["google_tv"]
        found = next((x for x in items if x.get("host") == host), None)
        if found:
            found.update({"name": name, "brand": _safe(brand, "Panasonic")})
        else:
            items.append({"name": name, "brand": _safe(brand, "Panasonic"), "host": host})
        _save(data)
        return f"Saved {name} at {host}."

    def add_tuya(self, name: str, device_id: str, ip: str, local_key: str, version: str = "3.3") -> str:
        data = _load()
        item = {
            "name": _safe(name, "Tuya device"),
            "device_id": str(device_id or "").strip(),
            "ip": str(ip or "").strip(),
            "local_key": str(local_key or "").strip(),
            "version": str(version or "3.3").strip(),
        }
        if not all((item["device_id"], item["ip"], item["local_key"])):
            return "Tuya device id, IP, and local key are required."
        items = data["tuya"]
        existing = next((x for x in items if x.get("name", "").casefold() == item["name"].casefold()), None)
        if existing:
            existing.update(item)
        else:
            items.append(item)
        _save(data)
        return f"Saved Tuya device {item['name']}."

    def _find(self, name: str, kind: str) -> dict | None:
        needle = str(name or "").strip().casefold()
        data = _load()
        for item in data.get(kind, []):
            if str(item.get("name", "")).casefold() == needle:
                return item
        for item in data.get(kind, []):
            if needle and needle in str(item.get("name", "")).casefold():
                return item
        return None

    def tv_command(self, name: str, action: str, value: str = "") -> str:
        item = self._find(name, "google_tv")
        if not item:
            return f"Google TV '{name}' is not configured."
        host = str(item["host"])
        return GOOGLE_TV.command(host, action, value)

    def tv_discover(self) -> str:
        return GOOGLE_TV.discover()

    def tv_pair_start(self, host: str, name: str = "", brand: str = "Panasonic") -> str:
        result = GOOGLE_TV.pair_start(host)
        if result.startswith("Pairing started"):
            self.add_google_tv(name or "Panasonic Google TV", host, brand)
        return result

    def tv_pair_finish(self, host: str, pin: str) -> str:
        return GOOGLE_TV.pair_finish(host, pin)

    def tv_status(self, name: str) -> str:
        item = self._find(name, "google_tv")
        if not item:
            return f"Google TV '{name}' is not configured."
        return GOOGLE_TV.status(item["host"])

    def tuya_command(self, name: str, action: str, value: str = "") -> str:
        item = self._find(name, "tuya")
        if not item:
            return f"Tuya device '{name}' is not configured."
        try:
            import tinytuya
            device = tinytuya.Device(
                item["device_id"],
                item["ip"],
                item["local_key"],
                version=float(item.get("version", "3.3")),
            )
            if action in {"on", "turn_on"}:
                result = device.turn_on()
            elif action in {"off", "turn_off"}:
                result = device.turn_off()
            elif action == "status":
                result = device.status()
            elif action == "set":
                if ":" not in value:
                    return "For Tuya set, value must be DPS:value, for example 2:50."
                dps, raw = value.split(":", 1)
                try:
                    parsed = int(raw)
                except ValueError:
                    parsed = raw
                result = device.set_value(int(dps), parsed)
            else:
                return "Tuya action must be on, off, status, or set."
            return f"{item['name']}: {result}"
        except ImportError:
            return "TinyTuya is not installed. Run pip install tinytuya."
        except Exception as exc:
            return f"Tuya control failed: {exc}"


SMART_HOME = SmartHomeService()
