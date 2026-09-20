import json
import os

import requests

from core.env import load_env


load_env()
_BASE = os.getenv("MASSIVEMUSIC_BASE_URL", "https://api.7digital.com").rstrip("/")
_KEY = os.getenv("MASSIVEMUSIC_CONSUMER_KEY", "").strip()
_COUNTRY = os.getenv("MASSIVEMUSIC_COUNTRY", "IN").strip().upper()
_USAGE = os.getenv(
    "MASSIVEMUSIC_USAGE_TYPES",
    "subscriptionstreaming",
).strip()
_TIMEOUT = 20


def _request(path: str, params: dict) -> str:
    if not _KEY:
        return "MassiveMusic consumer key is missing. Add MASSIVEMUSIC_CONSUMER_KEY to .env."

    query = dict(params)
    query["oauth_consumer_key"] = _KEY
    query.setdefault("country", _COUNTRY)

    try:
        response = requests.get(
            f"{_BASE}/{path.lstrip('/')}",
            params=query,
            headers={"Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        if not response.ok:
            return (
                f"MassiveMusic request failed: HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )
        try:
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception:
            return response.text[:3000]
    except Exception as exc:
        return f"MassiveMusic request failed: {exc}"


def massivemusic_api(
    action: str = "",
    query: str = "",
    artist_id: int = 0,
    release_id: int = 0,
    track_id: int = 0,
    country: str = "",
    page: int = 1,
    page_size: int = 10,
    exclude_explicit: bool = False,
):
    action = (action or "").lower().strip()
    cc = (country or _COUNTRY).strip().upper()

    if action == "track_search":
        if not query:
            return "query is required for track_search."
        return _request(
            "track/search",
            {
                "q": query,
                "usageTypes": _USAGE,
                "country": cc,
                "page": max(1, int(page)),
                "pageSize": max(1, min(int(page_size), 50)),
                "excludeExplicitContent": str(bool(exclude_explicit)).lower(),
            },
        )

    if action == "artist_search":
        if not query:
            return "query is required for artist_search."
        return _request(
            "artist/search",
            {
                "q": query,
                "country": cc,
                "page": max(1, int(page)),
                "pageSize": max(1, min(int(page_size), 50)),
            },
        )

    if action == "artist_details":
        if not artist_id:
            return "artist_id is required."
        return _request(
            "1.2/artist/details",
            {"artistId": int(artist_id), "country": cc},
        )

    if action == "release_details":
        if not release_id:
            return "release_id is required."
        return _request(
            "1.2/release/details",
            {
                "releaseId": int(release_id),
                "country": cc,
                "usageTypes": _USAGE,
            },
        )

    if action == "track_preview_url":
        if not track_id:
            return "track_id is required."
        url = (
            f"https://previews.7digital.com/clip/{int(track_id)}"
            f"?oauth_consumer_key={_KEY}&country={cc}"
        )
        return json.dumps(
            {
                "trackId": int(track_id),
                "previewUrl": url,
                "note": "Preview URLs are temporary and should not be stored for reuse.",
            },
            ensure_ascii=False,
            indent=2,
        )

    return (
        "Unknown action. Use track_search, artist_search, artist_details, "
        "release_details, or track_preview_url."
    )


TOOL = {
    "name": "massivemusic_api",
    "description": (
        "MassiveMusic / 7digital catalogue integration. Search tracks and artists, "
        "retrieve artist/release details, and generate a temporary preview URL for a "
        "track. Configure MASSIVEMUSIC_CONSUMER_KEY, MASSIVEMUSIC_COUNTRY and "
        "MASSIVEMUSIC_USAGE_TYPES in .env. Catalogue endpoints are read-oriented; "
        "streaming/download rights depend on the partner account and country."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "track_search | artist_search | artist_details | release_details | track_preview_url",
            },
            "query": {"type": "STRING", "description": "Track or artist search text"},
            "artist_id": {"type": "INTEGER", "description": "MassiveMusic artist ID"},
            "release_id": {"type": "INTEGER", "description": "MassiveMusic release ID"},
            "track_id": {"type": "INTEGER", "description": "MassiveMusic track ID"},
            "country": {"type": "STRING", "description": "ISO 2-letter country code"},
            "page": {"type": "INTEGER", "description": "Result page"},
            "page_size": {"type": "INTEGER", "description": "Result size; max 50 for track search"},
            "exclude_explicit": {"type": "BOOLEAN", "description": "Exclude explicit track results"},
        },
        "required": ["action"],
    },
    "handler": massivemusic_api,
}
