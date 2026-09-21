"""Voice controls for the JARVIS Android companion."""
from __future__ import annotations

import asyncio
from core.mobile_gateway import GATEWAY


TOOL = {
    "name": "android_connect",
    "description": (
        "Pair with and control the JARVIS Android companion. Use pair to create "
        "a six-digit pairing code for the phone app, list to show paired/connected "
        "phones, and command to send a device action such as open_app, open_url, "
        "tap, swipe, type, back, home, volume, flashlight, or screenshot."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "pair | list | command | revoke"},
            "device_id": {"type": "STRING", "description": "Paired Android device id."},
            "command": {"type": "STRING", "description": "Device command."},
            "payload": {"type": "STRING", "description": "JSON payload for the device command."},
        },
        "required": ["action"],
    },
}


def android_connect(parameters=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action") or "").strip().lower()

    if action == "pair":
        code = GATEWAY.new_pairing_code()
        return (
            f"Android pairing code: {code}. "
            "Open JARVIS Connect on the phone, select this JARVIS gateway, "
            "or enter the PC host manually, then enter this code."
        )

    if action == "list":
        devices = GATEWAY.list_devices()
        if not devices:
            return "No Android companion devices are paired."
        return "Android devices:\n" + "\n".join(
            f"- {d['device_id']} | {d['name']} | {d['model']} | "
            f"{'connected' if d['connected'] else 'offline'}"
            for d in devices
        )

    if action == "revoke":
        device_id = str(p.get("device_id") or "").strip()
        if device_id and device_id in GATEWAY._devices:
            GATEWAY._devices.pop(device_id, None)
            GATEWAY._save()
            return f"Revoked Android device {device_id}."
        return "Android device id not found."

    if action == "command":
        device_id = str(p.get("device_id") or "").strip()
        command = str(p.get("command") or "").strip()
        if not device_id or not command:
            return "device_id and command are required."
        payload = p.get("payload") or {}
        if isinstance(payload, str):
            try:
                import json
                payload = json.loads(payload)
            except Exception:
                return "payload must be valid JSON."
        try:
            result = asyncio.run(GATEWAY.command(device_id, command, payload))
        except RuntimeError:
            # The action normally runs in JARVIS's executor thread, but keep
            # this branch safe if a caller invokes it from a worker with a loop.
            loop = asyncio.new_event_loop()
            try:
                result = loop.run_until_complete(GATEWAY.command(device_id, command, payload))
            finally:
                loop.close()
        if isinstance(result, dict):
            return str(result.get("result") or result)
        return str(result)

    return "Use action=pair, list, command, or revoke."
