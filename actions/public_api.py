"""Public APIs selected from public-apis/public-apis for J.A.R.V.I.S."""

from core.public_api_hub import API_CATALOG, call_api, catalog


def public_api(parameters: dict = None, **_) -> str:
    p = parameters or {}
    service = str(p.get("service") or "list").strip().lower()
    if service in {"list", "catalog"}:
        return catalog()

    return call_api(
        service,
        query=str(p.get("query") or ""),
        action=str(p.get("action") or ""),
        latitude=p.get("latitude"),
        longitude=p.get("longitude"),
        timezone=p.get("timezone"),
        from_currency=p.get("from_currency"),
        to_currency=p.get("to_currency"),
        base=p.get("base"),
        to=p.get("to"),
        icao=p.get("icao"),
        league=p.get("league"),
        season=p.get("season"),
    )


TOOL = {
    "name": "public_api",
    "description": (
        "Access J.A.R.V.I.S.'s selected 20 Public APIs from the public-apis/public-apis "
        "catalog. Use service=list to see the catalog. Useful services include weather, "
        "geocoding, IP location, sun times, currency, timezone, radar, NASA, books, "
        "dictionary, anime, diagrams, API testing, aviation weather, Star Wars, scholarly "
        "metadata, Gutenberg books, Hacker News, music metadata and football data."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "service": {"type": "STRING", "description": "One of the 20 services, or list."},
            "query": {"type": "STRING", "description": "Search term, location, IP, word, date, or service query."},
            "action": {"type": "STRING", "description": "Service-specific action such as reverse, users, new, top."},
            "latitude": {"type": "NUMBER", "description": "Latitude."},
            "longitude": {"type": "NUMBER", "description": "Longitude."},
            "timezone": {"type": "STRING", "description": "IANA timezone."},
            "from_currency": {"type": "STRING", "description": "Source currency."},
            "to_currency": {"type": "STRING", "description": "Target currency."},
            "icao": {"type": "STRING", "description": "Four-letter airport ICAO code."},
            "league": {"type": "STRING", "description": "OpenLigaDB league shortcut, for example bl1."},
            "season": {"type": "STRING", "description": "OpenLigaDB season year."},
        },
        "required": ["service"],
    },
    "handler": public_api,
}
