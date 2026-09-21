"""Deterministic Windows system-setting controls."""
from __future__ import annotations

import asyncio
import os
import time


def _bluetooth_state(desired: str):
    if os.name != "nt":
        return False, "Bluetooth radio control is Windows-only."

    async def run():
        from winrt.windows.devices.radios import Radio, RadioAccessStatus, RadioKind, RadioState

        radios = await Radio.get_radios_async()
        bluetooth = [r for r in radios if r.kind == RadioKind.BLUETOOTH]
        if not bluetooth:
            return False, "No Bluetooth radio was found."

        access = await Radio.request_access_async()
        if access != RadioAccessStatus.ALLOWED:
            return False, f"Windows denied Bluetooth radio control: {access}"

        target = RadioState.ON if desired == "on" else RadioState.OFF
        changed = 0
        for radio in bluetooth:
            if radio.state != target:
                await radio.set_state_async(target)
                changed += 1
        return True, f"Bluetooth {'turned on' if desired == 'on' else 'turned off'} ({changed} radio(s) changed)."

    try:
        return asyncio.run(run())
    except Exception as exc:
        return False, str(exc)


TOOL = {
    "name": "system_settings",
    "description": (
        "Deterministic Windows settings controls. Use bluetooth_on, bluetooth_off, "
        "bluetooth_cycle, or open_bluetooth_settings for Bluetooth. Do not use "
        "computer_use or open_app to perform Bluetooth changes."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "bluetooth_on | bluetooth_off | bluetooth_cycle | open_bluetooth_settings",
            },
            "cycle_seconds": {
                "type": "INTEGER",
                "description": "Seconds to leave Bluetooth off during bluetooth_cycle; default 2.",
            },
        },
        "required": ["action"],
    },
}


def system_settings(parameters=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action") or "").strip().lower()

    if action == "open_bluetooth_settings":
        if os.name != "nt":
            return "Windows Bluetooth settings are only available on Windows."
        try:
            os.startfile("ms-settings:bluetooth")
            return "Opened Windows Bluetooth settings."
        except Exception as exc:
            return f"Could not open Bluetooth settings: {exc}"

    if action in {"bluetooth_on", "bluetooth_off"}:
        desired = "on" if action.endswith("_on") else "off"
        ok, detail = _bluetooth_state(desired)
        return detail if ok else f"Bluetooth control failed: {detail}"

    if action == "bluetooth_cycle":
        ok, detail = _bluetooth_state("off")
        if not ok:
            return f"Bluetooth could not be turned off: {detail}"
        time.sleep(max(1, min(10, int(p.get("cycle_seconds") or 2))))
        ok, detail = _bluetooth_state("on")
        return "Bluetooth cycle complete." if ok else f"Bluetooth was turned off but could not be turned back on: {detail}"

    return "Use action=bluetooth_on, bluetooth_off, bluetooth_cycle, or open_bluetooth_settings."
