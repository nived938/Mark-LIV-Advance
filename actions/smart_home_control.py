"""Voice control surface for JARVIS smart-home devices."""
from smart_home.service import SMART_HOME


TOOL = {
    "name": "smart_home_control",
    "description": (
        "Control configured smart-home devices. Supports Panasonic Google TVs "
        "running Google TV/Android TV Remote Service and Tuya/Smart Life LAN devices. "
        "Use tv_pair_start then tv_pair_finish for first-time Panasonic Google TV pairing. "
        "Use tv_control for power, volume, navigation, play/pause, text, or app links. "
        "Use tuya_control for on/off/status/DPS control. Use list to see configured devices."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "description": "list | tv_pair_start | tv_pair_finish | tv_status | tv_control | tuya_add | tuya_control"},
            "name": {"type": "STRING", "description": "Friendly device name."},
            "host": {"type": "STRING", "description": "TV IP address for pairing."},
            "brand": {"type": "STRING", "description": "TV brand, default Panasonic."},
            "pin": {"type": "STRING", "description": "PIN displayed by the TV during pairing."},
            "action": {"type": "STRING", "description": "TV: power, home, back, up, down, left, right, enter, volume_up, volume_down, mute, play_pause, status, app, text. Tuya: on, off, status, set."},
            "value": {"type": "STRING", "description": "App deep link, text, or Tuya DPS:value."},
            "device_id": {"type": "STRING", "description": "Tuya device id."},
            "ip": {"type": "STRING", "description": "Tuya device IP."},
            "local_key": {"type": "STRING", "description": "Tuya local key."},
            "version": {"type": "STRING", "description": "Tuya protocol version, e.g. 3.3."},
        },
        "required": ["operation"],
    },
}


def smart_home_control(parameters=None, **_) -> str:
    p = parameters or {}
    op = str(p.get("operation") or "").strip().lower()
    if op == "list":
        items = SMART_HOME.list_devices()
        if not items:
            return "No smart-home devices are configured."
        return "Smart-home devices:\n" + "\n".join(
            f"- {x['name']} ({x['type']}) {x.get('brand','')}"
            for x in items
        )
    if op == "tv_pair_start":
        return SMART_HOME.tv_pair_start(p.get("host", ""), p.get("name", ""), p.get("brand", "Panasonic"))
    if op == "tv_pair_finish":
        return SMART_HOME.tv_pair_finish(p.get("host", ""), p.get("pin", ""))
    if op == "tv_status":
        return SMART_HOME.tv_status(p.get("name", ""))
    if op == "tv_control":
        return SMART_HOME.tv_command(p.get("name", ""), p.get("action", ""), p.get("value", ""))
    if op == "tuya_add":
        return SMART_HOME.add_tuya(
            p.get("name", ""), p.get("device_id", ""), p.get("ip", ""),
            p.get("local_key", ""), p.get("version", "3.3")
        )
    if op == "tuya_control":
        return SMART_HOME.tuya_command(p.get("name", ""), p.get("action", ""), p.get("value", ""))
    return "Use operation=list, tv_pair_start, tv_pair_finish, tv_status, tv_control, tuya_add, or tuya_control."
