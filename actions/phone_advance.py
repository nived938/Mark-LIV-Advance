from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import urllib.parse
from pathlib import Path


def _adb_path() -> str | None:
    candidates = [
        shutil.which("adb"),
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
        os.path.expandvars(r"%USERPROFILE%\AppData\Local\Android\Sdk\platform-tools\adb.exe"),
        r"C:\platform-tools\adb.exe",
    ]
    for p in candidates:
        if p and Path(p).exists():
            return str(p)
    return None


def _run_adb(args: list[str], timeout: float = 15.0):
    adb = _adb_path()
    if not adb:
        return False, "", "ADB was not found. Install Android SDK Platform-Tools and add adb.exe to PATH."
    try:
        p = subprocess.run(
            [adb, *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return p.returncode == 0, p.stdout.strip(), p.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "", "ADB command timed out."
    except Exception as e:
        return False, "", str(e)


def _devices() -> list[str]:
    ok, out, _ = _run_adb(["devices"])
    if not ok:
        return []
    result = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            result.append(parts[0])
    return result


def _device() -> str | None:
    devs = _devices()
    return devs[0] if devs else None


def _d(args: list[str], timeout: float = 15.0):
    dev = _device()
    if not dev:
        return False, "", "No Android phone is connected. Enable Wireless debugging and connect the phone first."
    return _run_adb(["-s", dev, *args], timeout)


def _connect(address: str) -> str:
    address = address.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", address):
        return "Invalid ADB address."
    ok, out, err = _run_adb(["connect", address], timeout=15)
    msg = out or err or "No response from adb."
    return f"ADB connection: {msg}" if ok else f"ADB connection failed: {msg}"


def _pair(address: str, code: str) -> str:
    address = address.strip()
    code = code.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", address) or not re.fullmatch(r"\d{4,8}", code):
        return "Invalid wireless pairing address or pairing code."
    ok, out, err = _run_adb(["pair", address, code], timeout=20)
    msg = out or err or "No response from adb."
    return f"ADB pairing: {msg}" if ok else f"ADB pairing failed: {msg}"


def _resolve_contact(name: str) -> str | None:
    name = name.strip()
    if not name:
        return None

    # Android's ContactsProvider is readable by adb's shell user on common
    # Android builds. Query both display name and phone number, then choose
    # the closest case-insensitive match.
    uri = "content://com.android.contacts/data/phones"
    ok, out, _ = _d([
        "shell", "content", "query", "--uri", uri,
        "--projection", "display_name:number",
    ], timeout=20)
    if not ok:
        return None

    wanted = re.sub(r"\s+", " ", name).strip().lower()
    exact = None
    partial = None

    for line in out.splitlines():
        low = line.lower()
        m_name = re.search(r"display_name=([^,]+)", line, re.I)
        m_num = re.search(r"number=([^,]+)", line, re.I)
        if not m_name or not m_num:
            continue
        display = m_name.group(1).strip()
        number = m_num.group(1).strip()
        if not number:
            continue
        dn = re.sub(r"\s+", " ", display).lower()
        if dn == wanted:
            exact = number
            break
        if wanted in dn or dn in wanted:
            partial = partial or number

    return exact or partial


def _normalize_number(number: str) -> str:
    number = number.strip()
    if number.startswith("00"):
        number = "+" + number[2:]
    return re.sub(r"[^0-9+]", "", number)


def _phone_call(target: str) -> str:
    number = target if re.search(r"\d", target) else _resolve_contact(target)
    if not number:
        return f"I could not find a phone contact named {target}."
    number = _normalize_number(number)
    ok, _, err = _d([
        "shell", "am", "start", "-a", "android.intent.action.CALL",
        "-d", f"tel:{number}",
    ], timeout=15)
    return f"Calling {target}." if ok else f"Could not start the phone call: {err}"


def _launch_whatsapp() -> bool:
    ok, _, _ = _d([
        "shell", "monkey", "-p", "com.whatsapp", "1",
    ], timeout=15)
    return ok


def _whatsapp_message(target: str, message: str) -> str:
    number = target if re.search(r"\d", target) else _resolve_contact(target)
    if not number:
        return f"I could not find a phone contact named {target}."
    number = _normalize_number(number)
    if not number.startswith("+"):
        # WhatsApp deep links require an international number. If the contact
        # provider returned a local number, keep it usable through the normal
        # WhatsApp UI instead of inventing a country code.
        return "The contact has no international-format number. Save it with country code first."

    encoded = urllib.parse.quote(message, safe="")
    uri = f"https://wa.me/{number.lstrip('+')}?text={encoded}"
    ok, _, err = _d([
        "shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", uri, "-p", "com.whatsapp",
    ], timeout=20)
    if not ok:
        return f"Could not open WhatsApp chat: {err}"

    # The deep link opens the chat with the text filled in. Click the Send
    # button through Android UI Automator so the message is actually sent.
    time.sleep(1.2)
    ok, out, _ = _d(["shell", "uiautomator", "dump", "/sdcard/window.xml"], timeout=15)
    if ok:
        ok2, xml, _ = _d(["shell", "cat", "/sdcard/window.xml"], timeout=10)
        if ok2:
            send_re = re.compile(r'text="([^"]*send[^"]*)"[^>]*resource-id="([^"]*)"', re.I)
            m = send_re.search(xml)
            if m:
                rid = m.group(2)
                if rid:
                    ok3, _, _ = _d(["shell", "input", "tap", "0", "0"], timeout=5)
                    # Prefer coordinate extracted from the node bounds.
                    node = re.search(
                        r'<node[^>]*resource-id="' + re.escape(rid) +
                        r'"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                        xml,
                    )
                    if node:
                        x = (int(node.group(1)) + int(node.group(3))) // 2
                        y = (int(node.group(2)) + int(node.group(4))) // 2
                        _d(["shell", "input", "tap", str(x), str(y)], timeout=5)
                        return f"WhatsApp message sent to {target}."
            # Generic content-description fallback.
            node = re.search(
                r'<node[^>]*(?:content-desc="([^"]*send[^"]*)"|text="([^"]*send[^"]*)")[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
                xml, re.I,
            )
            if node:
                x = (int(node.group(3)) + int(node.group(5))) // 2
                y = (int(node.group(4)) + int(node.group(6))) // 2
                _d(["shell", "input", "tap", str(x), str(y)], timeout=5)
                return f"WhatsApp message sent to {target}."

    return f"WhatsApp opened the chat with {target}, but the Send button could not be located automatically."


def _whatsapp_call(target: str, video: bool = False) -> str:
    number = target if re.search(r"\d", target) else _resolve_contact(target)
    if not number:
        return f"I could not find a phone contact named {target}."
    number = _normalize_number(number)
    if not number.startswith("+"):
        return "Save the WhatsApp contact with the international country code first."

    if not _launch_whatsapp():
        return "Could not open WhatsApp on the phone."
    time.sleep(1.5)

    # Open the chat/contact by deep link first.
    uri = f"https://wa.me/{number.lstrip('+')}"
    ok, _, err = _d([
        "shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", uri, "-p", "com.whatsapp",
    ], timeout=20)
    if not ok:
        return f"Could not open the WhatsApp contact: {err}"
    time.sleep(1.5)

    ok, _, _ = _d(["shell", "uiautomator", "dump", "/sdcard/window.xml"], timeout=15)
    ok2, xml, _ = _d(["shell", "cat", "/sdcard/window.xml"], timeout=10)
    if not (ok and ok2):
        return "WhatsApp opened, but its controls could not be inspected."

    patterns = (
        ("video", r'content-desc="([^"]*video call[^"]*)"',),
        ("audio", r'content-desc="([^"]*(?:voice call|call)[^"]*)"',),
    )
    wanted = "video" if video else "audio"
    candidates = []
    for kind, pat in patterns:
        if kind != wanted:
            continue
        candidates.extend(re.finditer(
            pat + r'[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            xml, re.I
        ))
    if not candidates:
        # Some WhatsApp builds expose the button through text instead.
        label = "video call" if video else "call"
        candidates = list(re.finditer(
            r'text="([^"]*' + re.escape(label) +
            r'[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            xml, re.I
        ))

    if candidates:
        m = candidates[0]
        nums = [int(x) for x in m.groups() if x.isdigit()]
        if len(nums) >= 4:
            x = (nums[-4] + nums[-2]) // 2
            y = (nums[-3] + nums[-1]) // 2
            ok, _, err = _d(["shell", "input", "tap", str(x), str(y)], timeout=8)
            if ok:
                return f"WhatsApp {'video ' if video else ''}call started with {target}."

    return f"WhatsApp opened {target}'s chat, but the {'video' if video else 'voice'} call control could not be located."


def _send_sms(target: str, message: str) -> str:
    number = target if re.search(r"\d", target) else _resolve_contact(target)
    if not number:
        return f"I could not find a phone contact named {target}."
    number = _normalize_number(number)
    encoded = urllib.parse.quote(message, safe="")
    ok, _, err = _d([
        "shell", "am", "start", "-a", "android.intent.action.SENDTO",
        "-d", f"sms:{number}", "--es", "sms_body", message,
    ], timeout=15)
    if not ok:
        return f"Could not open the SMS composer: {err}"

    time.sleep(1.0)
    ok, _, _ = _d(["shell", "uiautomator", "dump", "/sdcard/window.xml"], timeout=15)
    ok2, xml, _ = _d(["shell", "cat", "/sdcard/window.xml"], timeout=10)
    if ok and ok2:
        m = re.search(
            r'(?:content-desc|text)="([^"]*send[^"]*)"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"',
            xml, re.I
        )
        if m:
            x = (int(m.group(2)) + int(m.group(4))) // 2
            y = (int(m.group(3)) + int(m.group(5))) // 2
            _d(["shell", "input", "tap", str(x), str(y)], timeout=8)
            return f"Message sent to {target}."

    return f"SMS composer opened for {target}, but the Send control could not be located."


def _pull_file(phone_path: str, pc_path: str = "") -> str:
    phone_path = phone_path.strip()
    if not phone_path:
        return "No phone file path was provided."

    if phone_path.lower() in ("latest photo", "latest picture", "latest image"):
        ok, out, err = _d([
            "shell", "sh", "-c",
            "ls -t /sdcard/DCIM/Camera/* 2>/dev/null | head -n 1",
        ], timeout=15)
        if not ok or not out:
            return f"Could not find the latest camera photo: {err}"
        phone_path = out.splitlines()[-1].strip()

    destination = Path(pc_path).expanduser() if pc_path else (Path.home() / "Downloads" / Path(phone_path).name)
    destination.parent.mkdir(parents=True, exist_ok=True)

    ok, _, err = _d(["pull", phone_path, str(destination)], timeout=120)
    return f"Copied {phone_path} to {destination}" if ok else f"Phone-to-PC transfer failed: {err}"


def _push_file(pc_path: str, phone_path: str = "") -> str:
    source = Path(pc_path).expanduser()
    if not source.exists() or not source.is_file():
        return f"PC file not found: {source}"

    destination = phone_path.strip() or f"/sdcard/Download/{source.name}"
    ok, _, err = _d(["push", str(source), destination], timeout=120)
    return f"Copied {source} to {destination}" if ok else f"PC-to-phone transfer failed: {err}"


def phone_advance(
    action: str,
    target: str = "",
    message: str = "",
    path: str = "",
    destination: str = "",
    address: str = "",
    code: str = "",
) -> str:
    action = (action or "").lower().strip()

    if action == "status":
        devs = _devices()
        return f"Connected Android devices: {', '.join(devs)}" if devs else "No Android device is connected."

    if action == "connect":
        return _connect(address)

    if action == "pair":
        return _pair(address, code)

    if action in ("call", "phone_call"):
        return _phone_call(target)

    if action in ("message", "sms", "send_sms"):
        return _send_sms(target, message)

    if action in ("whatsapp_message", "wa_message"):
        return _whatsapp_message(target, message)

    if action in ("whatsapp_call", "wa_call"):
        return _whatsapp_call(target, video=False)

    if action in ("whatsapp_video_call", "wa_video_call", "video_call"):
        return _whatsapp_call(target, video=True)

    if action in ("pull", "from_phone", "phone_to_pc", "get_file"):
        return _pull_file(path, destination)

    if action in ("push", "to_phone", "pc_to_phone", "send_file"):
        return _push_file(path, destination)

    return "Unknown phone action."


TOOL = {
    "name": "phone_advance",
    "description": (
        "Control the user's Android phone from this Windows PC through ADB wireless debugging. "
        "Use ONLY when the user explicitly uses @phone or asks to control the connected phone. "
        "Actions: status, pair, connect, call a normal phone contact, send an SMS, "
        "whatsapp_message, whatsapp_call, whatsapp_video_call, pull a photo/file from phone "
        "to PC, and push a photo/file from PC to phone. Resolve contact names from the phone's "
        "Contacts provider. For '@phone call amma' use action=call. For '@phone call amma in "
        "whatsapp' use action=whatsapp_call. For '@phone video call amma in whatsapp' use "
        "action=whatsapp_video_call. Never open WhatsApp Web; use the Android WhatsApp app. "
        "For 'send latest photo from phone to PC', use pull with path='latest photo'. "
        "For PC-to-phone transfer, use push with the PC path and destination such as "
        "/sdcard/Download/file.jpg. ADB must already be paired/connected unless the user "
        "asks for pair/connect."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "status, pair, connect, call, message, whatsapp_message, whatsapp_call, whatsapp_video_call, pull, or push",
            },
            "target": {"type": "STRING", "description": "Phone contact name or phone number"},
            "message": {"type": "STRING", "description": "SMS or WhatsApp message text"},
            "path": {"type": "STRING", "description": "PC path or phone path; use 'latest photo' for newest phone camera photo"},
            "destination": {"type": "STRING", "description": "Destination path on PC or phone"},
            "address": {"type": "STRING", "description": "ADB wireless address such as 192.168.1.20:5555 or pairing address"},
            "code": {"type": "STRING", "description": "ADB wireless pairing code"},
        },
        "required": ["action"],
    },
    "handler": phone_advance,
}
