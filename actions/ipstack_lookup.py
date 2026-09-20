import json
import os

import requests

from core.env import load_env


load_env()
_BASE = os.getenv("IPSTACK_BASE_URL", "http://api.ipstack.com").rstrip("/")
_TIMEOUT = 15


def _key():
    return os.getenv("IPSTACK_API_KEY", "").strip()


def _request(path: str, params: dict) -> str:
    key = _key()
    if not key:
        return "IPstack API key is missing. Add IPSTACK_API_KEY to .env."

    params = dict(params)
    params["access_key"] = key

    try:
        response = requests.get(
            f"{_BASE}/{path.lstrip('/')}",
            params=params,
            timeout=_TIMEOUT,
        )
        if not response.ok:
            return f"IPstack request failed: HTTP {response.status_code}: {response.text[:1000]}"

        data = response.json()
        if isinstance(data, dict) and data.get("success") is False:
            return json.dumps(data, ensure_ascii=False, indent=2)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception as exc:
        return f"IPstack request failed: {exc}"


def ipstack_lookup(
    action: str = "",
    ip: str = "",
    fields: str = "",
    language: str = "",
    hostname: bool = False,
):
    action = (action or "").lower().strip()

    if action == "check":
        params = {}
        if fields:
            params["fields"] = fields
        if language:
            params["language"] = language
        if hostname:
            params["hostname"] = 1
        return _request("check", params)

    if action == "lookup":
        if not ip:
            return "ip is required for lookup."
        params = {}
        if fields:
            params["fields"] = fields
        if language:
            params["language"] = language
        if hostname:
            params["hostname"] = 1
        return _request(ip.strip(), params)

    return "Unknown action. Use check or lookup."


TOOL = {
    "name": "ipstack_lookup",
    "description": (
        "IPstack geolocation lookup. Use action='check' to resolve the public IP address "
        "of the current requester, or action='lookup' with a supplied IPv4/IPv6 address. "
        "Returns location/network fields provided by the configured IPstack plan. The API "
        "key comes from IPSTACK_API_KEY in .env."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "check | lookup"},
            "ip": {"type": "STRING", "description": "IPv4 or IPv6 address for lookup"},
            "fields": {"type": "STRING", "description": "Comma-separated IPstack response fields"},
            "language": {"type": "STRING", "description": "Language for localized fields"},
            "hostname": {"type": "BOOLEAN", "description": "Include reverse DNS hostname when supported"},
        },
        "required": ["action"],
    },
    "handler": ipstack_lookup,
}
