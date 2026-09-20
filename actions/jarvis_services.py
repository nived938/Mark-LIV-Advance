"""J.A.R.V.I.S. utility control surface for the new standalone services."""

from __future__ import annotations

import json
import time
from pathlib import Path

from core.device_services import (
    GEOFENCE_MONITOR,
    add_geofence,
    check_geofences,
    data_usage_status,
    device_location,
    find_device_web_url,
    google_maps_url,
    internet_diagnostics,
    ip_location,
    list_devices,
    list_geofences,
    network_devices,
    open_qr_result,
    presentation_control,
    save_device,
    scan_qr_camera,
    scan_qr_screen,
    school_add,
    school_list,
    school_remove,
    school_today,
    screen_time_reset,
    screen_time_status,
    SCREEN_TRACKER,
    remove_geofence,
    wifi_analyzer,
)


def _fmt(obj) -> str:
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, indent=2, ensure_ascii=False)


def jarvis_services(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    service = str(p.get("service", "")).strip().lower()
    action = str(p.get("action", "")).strip().lower()

    if service in {"location", "ip_location"}:
        if action in {"ip", "lookup", "locate"}:
            data = ip_location(str(p.get("ip") or ""))
            if data.get("latitude") is not None and data.get("longitude") is not None and player:
                try:
                    player.show_map(
                        google_maps_url(
                            data["latitude"], data["longitude"],
                            data.get("city") or data.get("ip") or "Location"
                        )
                    )
                except Exception:
                    pass
            return _fmt(data)
        if action in {"devices", "list"}:
            return _fmt(list_devices())
        if action in {"device", "show"}:
            name = str(p.get("name") or "").strip()
            data = device_location(name)
            if data.get("latitude") is not None and data.get("longitude") is not None and player:
                player.show_map(google_maps_url(
                    float(data["latitude"]), float(data["longitude"]), name
                ))
            return _fmt(data)
        if action in {"save", "remember"}:
            return save_device(
                str(p.get("name") or ""),
                p.get("latitude"),
                p.get("longitude"),
                str(p.get("ip") or ""),
                str(p.get("note") or ""),
            )
        if action in {"map", "show_map"}:
            lat = float(p.get("latitude"))
            lon = float(p.get("longitude"))
            if player:
                player.show_map(google_maps_url(lat, lon, str(p.get("label") or "Location")))
            return "Map opened inside J.A.R.V.I.S."
        if action in {"find_device", "find_my_device"}:
            if player:
                player.show_map(find_device_web_url())
            return "Google Find My Device is open inside J.A.R.V.I.S. The page uses the user's own signed-in account if Google permits the embedded session."
        return "Location actions: ip, devices, device, save, map, find_device."

    if service in {"internet", "internet_diagnostics"}:
        return internet_diagnostics(
            host=str(p.get("host") or "1.1.1.1"),
            url=str(p.get("url") or "https://www.google.com"),
        )

    if service in {"network", "network_devices"}:
        rows = network_devices()
        return _fmt(rows)

    if service in {"wifi", "wifi_analyzer"}:
        rows = wifi_analyzer()
        return _fmt(rows)

    if service in {"geofence", "geofencing"}:
        if action == "add":
            return add_geofence(
                str(p.get("name") or ""),
                float(p.get("latitude")),
                float(p.get("longitude")),
                float(p.get("radius_m") or 100),
                str(p.get("instruction") or ""),
            )
        if action == "list":
            return _fmt(list_geofences())
        if action == "remove":
            return remove_geofence(str(p.get("name") or ""))
        if action in {"check", "now"}:
            return _fmt(check_geofences(player))
        if action in {"start", "enable"}:
            GEOFENCE_MONITOR.start(player)
            return "Geofence monitoring started."
        if action in {"stop", "disable"}:
            GEOFENCE_MONITOR.stop()
            return "Geofence monitoring stopped."
        return "Geofence actions: add, list, remove, check, start, stop."

    if service in {"school", "timetable", "school_timetable"}:
        if action == "add":
            return school_add(
                str(p.get("subject") or ""),
                str(p.get("day") or ""),
                str(p.get("start") or ""),
                str(p.get("end") or ""),
                str(p.get("room") or ""),
                str(p.get("teacher") or ""),
            )
        if action == "list":
            return _fmt(school_list(str(p.get("day") or "")))
        if action == "today":
            return _fmt(school_today())
        if action == "remove":
            return school_remove(str(p.get("id") or ""))
        return "School timetable actions: add, list, today, remove."

    if service in {"screen_time", "screentime"}:
        if action in {"start", "enable"}:
            SCREEN_TRACKER.start()
            return "Screen-time tracking started."
        if action in {"stop", "disable"}:
            SCREEN_TRACKER.stop()
            return "Screen-time tracking stopped."
        if action in {"status", "report", "today"}:
            return _fmt(screen_time_status())
        if action == "reset":
            return screen_time_reset()
        return "Screen-time actions: start, stop, status, reset."

    if service in {"presentation", "presentation_remote"}:
        return presentation_control(action)

    if service in {"data_usage", "data"}:
        return _fmt(data_usage_status())

    if service in {"qr", "qrcode", "qr_code"}:
        source = str(p.get("source") or "camera").strip().lower()
        if source == "screen":
            value = scan_qr_screen(int(p.get("monitor") or 0))
        else:
            value = scan_qr_camera(player, timeout=float(p.get("timeout") or 30))
        if not value:
            return "No QR code detected."
        return open_qr_result(value)

    return (
        "Available services: location, internet_diagnostics, network_devices, "
        "wifi_analyzer, geofence, school_timetable, screen_time, "
        "presentation_remote, data_usage, qr_code."
    )


TOOL = {
    "name": "jarvis_services",
    "description": (
        "Standalone J.A.R.V.I.S. services. Use for IP/device location, showing a hidden-URL "
        "Google Maps view, network device discovery, Wi-Fi analysis, internet diagnostics, "
        "geofences, school timetable, screen-time tracking, data-usage reporting, "
        "presentation remote control, and QR scanning from the camera or current screen. "
        "For QR scanning use source=camera when the user says scan the QR code with the camera, "
        "and source=screen when the user says scan the QR code on my screen. "
        "For Google Find My Device, use location/find_device only as an embedded website; "
        "do not claim private device coordinates were retrieved programmatically."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "service": {
                "type": "STRING",
                "description": "location | internet_diagnostics | network_devices | wifi_analyzer | geofence | school_timetable | screen_time | presentation_remote | data_usage | qr_code",
            },
            "action": {
                "type": "STRING",
                "description": "Service-specific action such as ip, device, add, list, start, status, next, previous, screen, camera.",
            },
            "name": {"type": "STRING", "description": "Device, geofence or timetable item name."},
            "ip": {"type": "STRING", "description": "IPv4/IPv6 address for IP geolocation."},
            "latitude": {"type": "NUMBER", "description": "Latitude for a saved device or geofence."},
            "longitude": {"type": "NUMBER", "description": "Longitude for a saved device or geofence."},
            "radius_m": {"type": "NUMBER", "description": "Geofence radius in meters."},
            "instruction": {"type": "STRING", "description": "Optional instruction to run when a geofence changes state."},
            "day": {"type": "STRING", "description": "School timetable weekday."},
            "subject": {"type": "STRING", "description": "School subject."},
            "start": {"type": "STRING", "description": "Start time."},
            "end": {"type": "STRING", "description": "End time."},
            "room": {"type": "STRING", "description": "Room."},
            "teacher": {"type": "STRING", "description": "Teacher."},
            "id": {"type": "STRING", "description": "Saved timetable item ID."},
            "source": {"type": "STRING", "description": "QR source: camera or screen."},
            "timeout": {"type": "NUMBER", "description": "QR camera scan timeout in seconds."},
            "monitor": {"type": "NUMBER", "description": "Monitor number for screen QR scanning: 0=all monitors, 1=first monitor, 2=second monitor."},
            "host": {"type": "STRING", "description": "Host for network diagnostic ping/DNS."},
            "url": {"type": "STRING", "description": "URL for HTTP connectivity testing."},
            "label": {"type": "STRING", "description": "Map label."},
            "note": {"type": "STRING", "description": "Optional saved device note."},
        },
        "required": ["service", "action"],
    },
    "handler": jarvis_services,
}
