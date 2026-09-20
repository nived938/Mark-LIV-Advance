"""Public API hub for J.A.R.V.I.S.

The catalog is based on the current public-apis/public-apis repository.
The integrations below intentionally favor keyless, HTTPS services that are
useful for a personal assistant. All requests are read-only and have short
timeouts.
"""

from __future__ import annotations

import json
import base64
import zlib
from urllib.parse import quote

import requests


UA = "JARVIS-Mark-LIV/1.0"
TIMEOUT = 12
_MUSICBRAINZ_LOCK = __import__("threading").Lock()
_MUSICBRAINZ_LAST = 0.0


API_CATALOG = [
    {"name": "open_meteo", "title": "Open-Meteo", "purpose": "global weather forecasts", "auth": "none", "https": True},
    {"name": "nominatim", "title": "Nominatim", "purpose": "forward/reverse geocoding", "auth": "none", "https": True},
    {"name": "ipinfo", "title": "IPinfo", "purpose": "IP address and approximate geolocation", "auth": "none", "https": True},
    {"name": "sunrise_sunset", "title": "Sunrise and Sunset", "purpose": "sunrise and sunset times", "auth": "none", "https": True},
    {"name": "frankfurter", "title": "Frankfurter", "purpose": "currency conversion and exchange rates", "auth": "none", "https": True},
    {"name": "world_time_weather", "title": "World Time & Weather", "purpose": "time, timezone and weather data", "auth": "none", "https": True},
    {"name": "rainviewer", "title": "RainViewer", "purpose": "weather radar map data", "auth": "none", "https": True},
    {"name": "nasa", "title": "NASA", "purpose": "NASA science and imagery", "auth": "none/DEMO_KEY", "https": True},
    {"name": "open_library", "title": "Open Library", "purpose": "books and book metadata", "auth": "none", "https": True},
    {"name": "free_dictionary", "title": "Free Dictionary", "purpose": "definitions and pronunciations", "auth": "none", "https": True},
    {"name": "jikan", "title": "Jikan", "purpose": "MyAnimeList anime data", "auth": "none", "https": True},
    {"name": "kroki", "title": "Kroki", "purpose": "diagram rendering", "auth": "none", "https": True},
    {"name": "jsonplaceholder", "title": "JSONPlaceholder", "purpose": "safe API testing", "auth": "none", "https": True},
    {"name": "aviation_weather", "title": "AviationWeather", "purpose": "aviation METAR/TAF weather", "auth": "none", "https": True},
    {"name": "swapi", "title": "SWAPI", "purpose": "Star Wars data", "auth": "none", "https": True},
    {"name": "crossref", "title": "Crossref Metadata Search", "purpose": "scholarly article and book metadata", "auth": "none", "https": True},
    {"name": "gutendex", "title": "Gutendex", "purpose": "Project Gutenberg books", "auth": "none", "https": True},
    {"name": "hacker_news", "title": "HackerNews", "purpose": "technology and startup news", "auth": "none", "https": True},
    {"name": "musicbrainz", "title": "MusicBrainz", "purpose": "music artist/release metadata", "auth": "none", "https": True},
    {"name": "openligadb", "title": "OpenLigaDB", "purpose": "football league and match data", "auth": "none", "https": True},
]


def _get(url: str, params: dict | None = None):
    r = requests.get(
        url,
        params=params or {},
        timeout=TIMEOUT,
        headers={"User-Agent": UA, "Accept": "application/json"},
    )
    r.raise_for_status()
    return r


def catalog() -> str:
    return json.dumps(API_CATALOG, indent=2, ensure_ascii=False)


def call_api(service: str, query: str = "", **kwargs) -> str:
    s = str(service or "").strip().lower().replace("-", "_").replace(" ", "_")
    q = str(query or "").strip()

    if s in {"list", "catalog"}:
        return catalog()

    if s == "open_meteo":
        lat = kwargs.get("latitude")
        lon = kwargs.get("longitude")
        if lat is None or lon is None:
            geo = _get(
                "https://geocoding-api.open-meteo.com/v1/search",
                {"name": q or "London", "count": 1, "language": "en", "format": "json"},
            ).json()
            rows = geo.get("results") or []
            if not rows:
                return "Open-Meteo could not geocode that location."
            lat, lon = rows[0]["latitude"], rows[0]["longitude"]
            place = rows[0].get("name", q)
        else:
            place = q or f"{lat},{lon}"
        data = _get(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": lat, "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
                "timezone": "auto", "forecast_days": 3,
            },
        ).json()
        return json.dumps({"place": place, "data": data}, indent=2, ensure_ascii=False)

    if s == "nominatim":
        if str(kwargs.get("action") or "").lower() == "reverse":
            lat, lon = kwargs.get("latitude"), kwargs.get("longitude")
            return json.dumps(_get(
                "https://nominatim.openstreetmap.org/reverse",
                {"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 18, "addressdetails": 1},
            ).json(), indent=2, ensure_ascii=False)
        return json.dumps(_get(
            "https://nominatim.openstreetmap.org/search",
            {"q": q, "format": "jsonv2", "limit": 5, "addressdetails": 1},
        ).json(), indent=2, ensure_ascii=False)

    if s == "ipinfo":
        ip = q.strip()
        url = f"https://ipinfo.io/{quote(ip)}/json" if ip else "https://ipinfo.io/json"
        return json.dumps(_get(url).json(), indent=2, ensure_ascii=False)

    if s == "sunrise_sunset":
        return json.dumps(_get(
            "https://api.sunrise-sunset.org/json",
            {"lat": kwargs.get("latitude"), "lng": kwargs.get("longitude"), "formatted": 0},
        ).json(), indent=2, ensure_ascii=False)

    if s == "frankfurter":
        base = str(kwargs.get("from_currency") or kwargs.get("base") or "USD").upper()
        target = str(kwargs.get("to_currency") or kwargs.get("to") or "EUR").upper()
        return json.dumps(_get(
            f"https://api.frankfurter.dev/v2/rate/{quote(base)}/{quote(target)}"
        ).json(), indent=2, ensure_ascii=False)

    if s == "world_time_weather":
        zone = q or str(kwargs.get("timezone") or "Asia/Kolkata")
        return json.dumps(_get(
            "https://worldtimeweather.com/api/time",
            {"zone": zone},
        ).json(), indent=2, ensure_ascii=False)

    if s == "rainviewer":
        return json.dumps(_get(
            "https://api.rainviewer.com/public/weather-maps.json"
        ).json(), indent=2, ensure_ascii=False)

    if s == "nasa":
        return json.dumps(_get(
            "https://api.nasa.gov/planetary/apod",
            {"api_key": "DEMO_KEY", "date": q} if q else {"api_key": "DEMO_KEY"},
        ).json(), indent=2, ensure_ascii=False)

    if s == "open_library":
        return json.dumps(_get(
            "https://openlibrary.org/search.json",
            {"q": q or "python programming", "limit": 10},
        ).json(), indent=2, ensure_ascii=False)

    if s == "free_dictionary":
        word = q or "computer"
        return json.dumps(_get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word)}"
        ).json(), indent=2, ensure_ascii=False)

    if s == "jikan":
        return json.dumps(_get(
            "https://api.jikan.moe/v4/anime",
            {"q": q or "One Piece", "limit": 10},
        ).json(), indent=2, ensure_ascii=False)

    if s == "kroki":
        # Kroki's GET path format uses zlib-compressed, URL-safe base64 data.
        diagram = q or "graph TD; A[Start] --> B[Jarvis]"
        compressed = zlib.compress(diagram.encode("utf-8"), 9)
        encoded = base64.urlsafe_b64encode(compressed).decode("ascii").rstrip("=")
        return f"https://kroki.io/mermaid/svg/{encoded}"

    if s == "jsonplaceholder":
        if str(kwargs.get("action") or "posts").lower() == "users":
            path = "users"
        else:
            path = "posts"
        return json.dumps(_get(
            f"https://jsonplaceholder.typicode.com/{path}",
            {"_limit": 10},
        ).json(), indent=2, ensure_ascii=False)

    if s == "aviation_weather":
        icao = (q or str(kwargs.get("icao") or "")).upper()
        params = {"format": "json"}
        if icao:
            params["ids"] = icao
        return json.dumps(_get(
            "https://aviationweather.gov/api/data/metar", params
        ).json(), indent=2, ensure_ascii=False)

    if s == "swapi":
        term = q or "people"
        if term.isdigit():
            url = f"https://swapi.dev/api/people/{term}/"
            return json.dumps(_get(url).json(), indent=2, ensure_ascii=False)
        return json.dumps(_get(
            f"https://swapi.dev/api/{term}/", {}
        ).json(), indent=2, ensure_ascii=False)

    if s == "crossref":
        return json.dumps(_get(
            "https://api.crossref.org/works",
            {"query": q or "artificial intelligence", "rows": 10},
        ).json(), indent=2, ensure_ascii=False)

    if s == "gutendex":
        return json.dumps(_get(
            "https://gutendex.com/books/",
            {"search": q} if q else {"page": 1},
        ).json(), indent=2, ensure_ascii=False)

    if s == "hacker_news":
        base = "https://hacker-news.firebaseio.com/v0/"
        if str(kwargs.get("action") or "top").lower() == "new":
            ids = _get(base + "newstories.json").json()[:10]
        else:
            ids = _get(base + "topstories.json").json()[:10]
        stories = []
        for item_id in ids:
            try:
                stories.append(_get(base + f"item/{item_id}.json").json())
            except Exception:
                continue
        return json.dumps(stories, indent=2, ensure_ascii=False)

    if s == "musicbrainz":
        global _MUSICBRAINZ_LAST
        with _MUSICBRAINZ_LOCK:
            now = __import__("time").monotonic()
            wait = 1.05 - (now - _MUSICBRAINZ_LAST)
            if wait > 0:
                __import__("time").sleep(wait)
            result = _get(
                "https://musicbrainz.org/ws/2/artist",
                {"query": q or "Daft Punk", "fmt": "json", "limit": 10},
            ).json()
            _MUSICBRAINZ_LAST = __import__("time").monotonic()
        return json.dumps(result, indent=2, ensure_ascii=False)

    if s == "openligadb":
        shortcut = str(kwargs.get("league") or "bl1").lower()
        season = str(kwargs.get("season") or "2026")
        return json.dumps(_get(
            f"https://api.openligadb.de/getmatchdata/{shortcut}/{season}"
        ).json(), indent=2, ensure_ascii=False)

    return f"Unknown Public API service '{service}'. Use service=list to see the 20 integrated APIs."
