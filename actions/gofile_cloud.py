import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import urlparse

import requests

from core.env import load_env


load_env()
_API = os.getenv("GOFILE_API_BASE_URL", "https://api.gofile.io").rstrip("/")
_UPLOAD = os.getenv("GOFILE_UPLOAD_URL", "https://upload.gofile.io/uploadfile").strip()
_DEFAULT_DOWNLOAD_DIR = Path(os.getenv("GOFILE_DOWNLOAD_DIR", "downloads"))
_TIMEOUT = 30


def _token() -> str:
    return os.getenv("GOFILE_API_TOKEN", "").strip()


def _headers() -> dict:
    token = _token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _error(response: requests.Response) -> str:
    try:
        data = response.json()
        return json.dumps(data, ensure_ascii=False)
    except Exception:
        return response.text[:1000]


def _find_link(value):
    if isinstance(value, dict):
        link = value.get("link")
        if isinstance(link, str) and link.startswith(("http://", "https://")):
            return link
        for child in value.values():
            found = _find_link(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_link(child)
            if found:
                return found
    return None


def _content(content_id: str, params: dict | None = None):
    response = requests.get(
        f"{_API}/contents/{content_id}",
        headers=_headers(),
        params=params or {},
        timeout=_TIMEOUT,
    )
    if not response.ok:
        return None, _error(response)
    try:
        return response.json(), ""
    except Exception:
        return None, response.text[:1000]


def _download(url: str, destination: str) -> str:
    path = Path(destination).expanduser()
    if not path.suffix and urlparse(url).path:
        name = Path(urlparse(url).path).name
        if name:
            path = path / name

    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(url, headers=_headers(), stream=True, timeout=_TIMEOUT) as response:
            if not response.ok:
                return f"Download failed: HTTP {response.status_code}: {_error(response)}"

            if path.is_dir():
                name = Path(urlparse(url).path).name or "gofile-download"
                disposition = response.headers.get("content-disposition", "")
                if "filename=" in disposition:
                    name = disposition.split("filename=", 1)[1].strip().strip('"')
                path = path / name

            with path.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        handle.write(chunk)

        return f"Downloaded to {path.resolve()}"
    except Exception as exc:
        return f"Download failed: {exc}"


def gofile_cloud(
    action: str = "",
    file_path: str = "",
    folder_id: str = "",
    parent_folder_id: str = "",
    folder_name: str = "",
    content_id: str = "",
    contents_id: str = "",
    attribute: str = "",
    attribute_value: str = "",
    searched_string: str = "",
    url: str = "",
    destination: str = "",
    page: int = 1,
    page_size: int = 100,
):
    action = (action or "").lower().strip()
    token = _token()

    if action in {"upload", "create_folder", "get_content", "update", "delete", "search"} and not token:
        return "Gofile API token is missing. Add GOFILE_API_TOKEN to .env."

    if action == "upload":
        path = Path(file_path).expanduser()
        if not path.is_file():
            return f"File not found: {path}"

        data = {}
        if folder_id:
            data["folderId"] = folder_id

        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        try:
            with path.open("rb") as handle:
                response = requests.post(
                    _UPLOAD,
                    headers=_headers(),
                    data=data,
                    files={"file": (path.name, handle, mime)},
                    timeout=120,
                )
            if not response.ok:
                return f"Gofile upload failed: HTTP {response.status_code}: {_error(response)}"
            payload = response.json()
            if payload.get("status") != "ok":
                return json.dumps(payload, ensure_ascii=False)
            result = payload.get("data", {})
            return json.dumps({
                "status": "ok",
                "id": result.get("id"),
                "name": result.get("name"),
                "downloadPage": result.get("downloadPage"),
                "code": result.get("code"),
                "parentFolderCode": result.get("parentFolderCode"),
            }, ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"Gofile upload failed: {exc}"

    if action == "create_folder":
        if not parent_folder_id or not folder_name:
            return "parent_folder_id and folder_name are required."
        body = {
            "parentFolderId": parent_folder_id,
            "folderName": folder_name,
        }
        try:
            response = requests.post(
                f"{_API}/contents/createFolder",
                headers={**_headers(), "Content-Type": "application/json"},
                json=body,
                timeout=_TIMEOUT,
            )
            if not response.ok:
                return f"Gofile create-folder failed: HTTP {response.status_code}: {_error(response)}"
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"Gofile create-folder failed: {exc}"

    if action == "get_content":
        if not content_id:
            return "content_id is required."
        data, err = _content(content_id, {
            "page": max(1, int(page)),
            "pageSize": max(1, min(int(page_size), 100)),
        })
        return err or json.dumps(data, ensure_ascii=False, indent=2)

    if action == "update":
        if not content_id or not attribute:
            return "content_id and attribute are required."
        body = {
            "attribute": attribute,
            "attributeValue": attribute_value,
        }
        try:
            response = requests.put(
                f"{_API}/contents/{content_id}/update",
                headers={**_headers(), "Content-Type": "application/json"},
                json=body,
                timeout=_TIMEOUT,
            )
            if not response.ok:
                return f"Gofile update failed: HTTP {response.status_code}: {_error(response)}"
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"Gofile update failed: {exc}"

    if action == "delete":
        ids = contents_id or content_id
        if not ids:
            return "contents_id is required."
        try:
            response = requests.delete(
                f"{_API}/contents",
                headers={**_headers(), "Content-Type": "application/json"},
                json={"contentsId": ids},
                timeout=_TIMEOUT,
            )
            if not response.ok:
                return f"Gofile delete failed: HTTP {response.status_code}: {_error(response)}"
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"Gofile delete failed: {exc}"

    if action == "search":
        if not content_id or not searched_string:
            return "content_id and searched_string are required."
        try:
            response = requests.get(
                f"{_API}/contents/search",
                headers=_headers(),
                params={
                    "contentId": content_id,
                    "searchedString": searched_string,
                },
                timeout=_TIMEOUT,
            )
            if not response.ok:
                return f"Gofile search failed: HTTP {response.status_code}: {_error(response)}"
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"Gofile search failed: {exc}"

    if action == "download":
        if url:
            target = destination or str(_DEFAULT_DOWNLOAD_DIR)
            return _download(url, target)

        if not content_id:
            return "Provide either url or content_id for download."

        data, err = _content(content_id)
        if err:
            return (
                f"Could not resolve {content_id}: {err}. "
                "Some Gofile content-listing/download management endpoints require Premium."
            )

        link = _find_link(data)
        if not link:
            return (
                "Gofile returned content metadata but no downloadable link. "
                "Provide a direct file URL or use a Gofile endpoint/plan that exposes download links."
            )

        target = destination or str(_DEFAULT_DOWNLOAD_DIR)
        return _download(link, target)

    return (
        "Unknown action. Use upload, download, create_folder, get_content, update, "
        "delete, or search."
    )


TOOL = {
    "name": "gofile_cloud",
    "description": (
        "Gofile personal cloud storage. Upload a local PC file to Gofile, download a file "
        "from a direct Gofile URL to the PC, create folders, inspect content, update metadata, "
        "delete content, and search a folder. Authentication uses GOFILE_API_TOKEN from .env. "
        "Do not claim an upload/download succeeded unless this tool returns success."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "upload | download | create_folder | get_content | update | delete | search",
            },
            "file_path": {"type": "STRING", "description": "Local file path for upload"},
            "folder_id": {"type": "STRING", "description": "Destination Gofile folder UUID for upload"},
            "parent_folder_id": {"type": "STRING", "description": "Parent Gofile folder UUID"},
            "folder_name": {"type": "STRING", "description": "New folder display name"},
            "content_id": {"type": "STRING", "description": "Gofile content UUID/share code where supported"},
            "contents_id": {"type": "STRING", "description": "Comma-separated Gofile content UUIDs for delete"},
            "attribute": {"type": "STRING", "description": "name | description | tags | public | expiry | password | modTime"},
            "attribute_value": {"type": "STRING", "description": "Value for the selected attribute"},
            "searched_string": {"type": "STRING", "description": "Text to search for in Gofile content names/tags"},
            "url": {"type": "STRING", "description": "Direct file URL to download"},
            "destination": {"type": "STRING", "description": "Local output filename or directory"},
            "page": {"type": "INTEGER", "description": "Content page number"},
            "page_size": {"type": "INTEGER", "description": "Number of children to return"},
        },
        "required": ["action"],
    },
    "handler": gofile_cloud,
}
