"""ADB + UIAutomator Android remote autopilot."""
from __future__ import annotations

import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "screenshots" / "android"


def _adb() -> str:
    return shutil.which("adb") or "adb"


def _run(args: list[str], timeout: float = 15.0) -> tuple[bool, str, str]:
    try:
        p = subprocess.run(
            [_adb(), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return False, "", "adb was not found on PATH."
    except subprocess.TimeoutExpired:
        return False, "", "adb command timed out."
    except Exception as exc:
        return False, "", str(exc)


def _devices() -> list[str]:
    ok, out, _ = _run(["devices"])
    if not ok:
        return []
    result = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            result.append(parts[0])
    return result


def _serial(value: str = "") -> tuple[bool, str]:
    serial = str(value or "").strip()
    found = _devices()
    if serial:
        return (
            (True, serial) if serial in found
            else (False, f"Android device '{serial}' is not connected.")
        )
    if not found:
        return False, "No Android ADB device is connected."
    if len(found) > 1:
        return False, "Multiple Android devices are connected; provide serial."
    return True, found[0]


def _device(serial: str, args: list[str], timeout: float = 15.0):
    return _run(["-s", serial, *args], timeout)


def _bounds(value: str):
    m = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", value.strip())
    return tuple(int(x) for x in m.groups()) if m else None


def _dump(serial: str) -> tuple[bool, str]:
    remote = "/sdcard/jarvis-ui.xml"
    ok, _, err = _device(serial, ["shell", "uiautomator", "dump", remote], 15)
    if not ok:
        return False, err
    ok, out, err = _device(serial, ["exec-out", "cat", remote], 15)
    return (ok, out if ok else err)


def _tap_text(serial: str, text: str) -> str:
    ok, xml_text = _dump(serial)
    if not ok:
        return xml_text
    try:
        root = ET.fromstring(xml_text)
    except Exception as exc:
        return f"Could not parse accessibility tree: {exc}"

    needle = str(text or "").strip().casefold()
    best = None
    for node in root.iter("node"):
        label = " ".join(
            x for x in (
                node.attrib.get("text", ""),
                node.attrib.get("content-desc", ""),
                node.attrib.get("resource-id", ""),
            ) if x
        ).strip()
        if not label:
            continue
        low = label.casefold()
        if low == needle or (needle and needle in low and best is None):
            best = node
            if low == needle:
                break

    if best is None:
        return f"No accessibility node matched '{text}'."
    bounds = _bounds(best.attrib.get("bounds", ""))
    if not bounds:
        return f"Matched '{text}' but its bounds were unavailable."

    x1, y1, x2, y2 = bounds
    x, y = (x1 + x2) // 2, (y1 + y2) // 2
    ok, _, err = _device(serial, ["shell", "input", "tap", str(x), str(y)], 10)
    return f"Tapped '{text}' at ({x}, {y})." if ok else f"Tap failed: {err}"


TOOL = {
    "name": "android_autopilot",
    "description": (
        "Control a connected Android phone over ADB. Supports status, screenshot, "
        "tap, tap_text, swipe, type, back, home, open_app, keyevent, and ui_dump. "
        "For app controls, prefer tap_text because it uses UIAutomator accessibility."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "status | screenshot | tap | tap_text | swipe | type | back | home | open_app | keyevent | ui_dump"},
            "serial": {"type": "STRING", "description": "Optional adb serial or IP."},
            "x": {"type": "INTEGER", "description": "Tap/swipe start X."},
            "y": {"type": "INTEGER", "description": "Tap/swipe start Y."},
            "x2": {"type": "INTEGER", "description": "Swipe end X."},
            "y2": {"type": "INTEGER", "description": "Swipe end Y."},
            "duration_ms": {"type": "INTEGER", "description": "Swipe duration."},
            "text": {"type": "STRING", "description": "Text for type/tap_text."},
            "package": {"type": "STRING", "description": "Android package name."},
            "keycode": {"type": "STRING", "description": "ADB keyevent code."},
            "path": {"type": "STRING", "description": "Screenshot output path."},
        },
        "required": ["operation"],
    },
}


def android_autopilot(parameters: dict | None = None, **_) -> str:
    p = parameters or {}
    operation = str(p.get("operation") or "").strip().lower()
    ok, serial = _serial(p.get("serial", ""))
    if not ok:
        return serial

    if operation == "status":
        ok2, out, err = _device(serial, ["get-state"])
        return f"Android {serial}: {out if ok2 else err}"

    if operation == "screenshot":
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        path = Path(p.get("path") or (OUT_DIR / f"android-{int(time.time())}.png")).expanduser()
        if not path.is_absolute():
            path = OUT_DIR / path
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            proc = subprocess.run(
                [_adb(), "-s", serial, "exec-out", "screencap", "-p"],
                capture_output=True,
                timeout=20,
            )
            if proc.returncode != 0:
                return f"Android screenshot failed: {proc.stderr.decode(errors='replace')}"
            path.write_bytes(proc.stdout)
            return f"Android screenshot saved: {path}"
        except Exception as exc:
            return f"Android screenshot failed: {exc}"

    if operation == "ui_dump":
        ok2, xml_text = _dump(serial)
        if not ok2:
            return xml_text
        try:
            root = ET.fromstring(xml_text)
            nodes = []
            for node in root.iter("node"):
                label = node.attrib.get("text") or node.attrib.get("content-desc") or ""
                if label:
                    nodes.append(
                        f"{label} | {node.attrib.get('resource-id', '')} | {node.attrib.get('bounds', '')}"
                    )
            return "Android UI:\n" + "\n".join(nodes[:80])
        except Exception as exc:
            return f"UI dump parse failed: {exc}"

    if operation == "tap_text":
        return _tap_text(serial, p.get("text", ""))

    if operation == "tap":
        ok2, _, err = _device(
            serial, ["shell", "input", "tap", str(int(p.get("x", 0))), str(int(p.get("y", 0)))], 10
        )
        return "Android tap complete." if ok2 else f"Tap failed: {err}"

    if operation == "swipe":
        duration = max(80, int(p.get("duration_ms", 350)))
        ok2, _, err = _device(
            serial,
            ["shell", "input", "swipe", str(int(p.get("x", 0))), str(int(p.get("y", 0))),
             str(int(p.get("x2", 0))), str(int(p.get("y2", 0))), str(duration)],
            15,
        )
        return "Android swipe complete." if ok2 else f"Swipe failed: {err}"

    if operation == "type":
        value = str(p.get("text") or "")
        if not value:
            return "Provide text to type."
        escaped = value.replace(" ", "%s").replace("'", "\\'")
        ok2, _, err = _device(serial, ["shell", "input", "text", escaped], 15)
        return "Android typing complete." if ok2 else f"Typing failed: {err}"

    if operation == "back":
        ok2, _, err = _device(serial, ["shell", "input", "keyevent", "KEYCODE_BACK"], 10)
        return "Android back complete." if ok2 else f"Back failed: {err}"

    if operation == "home":
        ok2, _, err = _device(serial, ["shell", "input", "keyevent", "KEYCODE_HOME"], 10)
        return "Android home complete." if ok2 else f"Home failed: {err}"

    if operation == "keyevent":
        keycode = str(p.get("keycode") or "").strip()
        if not keycode:
            return "Provide a keycode."
        ok2, _, err = _device(serial, ["shell", "input", "keyevent", keycode], 10)
        return "Android keyevent complete." if ok2 else f"Keyevent failed: {err}"

    if operation == "open_app":
        package = str(p.get("package") or "").strip()
        if not package:
            return "Provide an Android package name."
        ok2, _, err = _device(serial, ["shell", "monkey", "-p", package, "1"], 15)
        return f"Opened {package}." if ok2 else f"Open app failed: {err}"

    return "Unknown Android autopilot operation."
