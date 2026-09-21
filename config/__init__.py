# config/__init__.py
import json, os, platform
from pathlib import Path

from core.env import load_env

load_env()

_CONFIG_PATH = Path(__file__).parent / "api_keys.json"

def _platform_os() -> str:
    """Auto-detect OS when config file is absent."""
    return {"Windows": "windows", "Darwin": "mac", "Linux": "linux"}.get(
        platform.system(), "linux"
    )

def get_config() -> dict:
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    # Environment variables override legacy JSON for local secrets/settings.
    env_map = {
        "GEMINI_API_KEY": "gemini_api_key",
        "JARVIS_OS": "os_system",
    }
    for env_name, config_name in env_map.items():
        value = os.getenv(env_name, "").strip()
        if value:
            data[config_name] = value

    return data

def get_os() -> str:
    """Returns: 'windows' | 'mac' | 'linux'"""
    return get_config().get("os_system", _platform_os()).lower()

def is_windows() -> bool: return get_os() == "windows"
def is_mac()     -> bool: return get_os() == "mac"
def is_linux()   -> bool: return get_os() == "linux"
