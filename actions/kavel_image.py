import json
import os
from pathlib import Path
from urllib.request import urlopen

from core.env import load_env


load_env()


def _save_url(url: str, destination: str) -> str:
    path = Path(destination).expanduser()
    if path.is_dir():
        path = path / "jarvis-generated-image.png"
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with urlopen(url, timeout=60) as response:
            path.write_bytes(response.read())
        return str(path.resolve())
    except Exception as exc:
        return f"Could not save generated image: {exc}"


def kavel_image(
    action: str = "",
    prompt: str = "",
    image_url: str = "",
    model: str = "",
    save_path: str = "",
):
    action = (action or "").lower().strip()

    if action not in {"generate", "edit"}:
        return "Unknown action. Use generate or edit."

    if not prompt:
        return "prompt is required."

    if action == "edit" and not image_url:
        return "image_url is required for edit."

    try:
        from kavel import generate
    except ImportError:
        return (
            "Kavel is not installed. Install it with "
            "'python -m pip install kavel' and try again."
        )

    kwargs = {}
    api_key = os.getenv("KAVEL_API_KEY", "").strip()
    configured_model = model.strip() or os.getenv("KAVEL_MODEL", "").strip()

    if api_key:
        kwargs["api_key"] = api_key
    if configured_model:
        kwargs["model"] = configured_model
    if image_url:
        kwargs["image_url"] = image_url

    try:
        url = generate(prompt, **kwargs)
        result = {
            "status": "ok",
            "action": action,
            "url": url,
        }

        if save_path:
            saved = _save_url(url, save_path)
            if saved.startswith("Could not save"):
                result["save_error"] = saved
            else:
                result["saved_to"] = saved

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as exc:
        name = type(exc).__name__
        return f"Kavel {action} failed ({name}): {exc}"


TOOL = {
    "name": "kavel_image",
    "description": (
        "Generate or edit images with Kavel. Kavel can generate images without an API key; "
        "KAVEL_API_KEY is optional for a user's own account/credits. Use action='generate' "
        "for a new image and action='edit' with image_url for an edit. Optionally save the "
        "returned image URL directly to a local path. Do not claim an image was generated "
        "or saved unless this tool returns status='ok'."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "generate | edit"},
            "prompt": {"type": "STRING", "description": "Image generation or editing instruction"},
            "image_url": {"type": "STRING", "description": "Public image URL for editing"},
            "model": {"type": "STRING", "description": "Optional Kavel model"},
            "save_path": {"type": "STRING", "description": "Optional local output path"},
        },
        "required": ["action", "prompt"],
    },
    "handler": kavel_image,
}
