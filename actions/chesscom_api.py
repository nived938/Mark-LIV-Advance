import json
import os

import requests

from core.env import load_env


load_env()
_BASE = os.getenv("CHESS_BASE_URL", "https://api.chess.com/pub").rstrip("/")
_USER_AGENT = os.getenv(
    "CHESS_USER_AGENT",
    "JARVIS/1.0 (contact: configure CHESS_USER_AGENT in .env)",
)
_TIMEOUT = 20


def _get(path: str):
    url = f"{_BASE}/{path.lstrip('/')}"
    response = requests.get(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        },
        timeout=_TIMEOUT,
    )
    if not response.ok:
        return f"Chess.com request failed: HTTP {response.status_code}: {response.text[:1000]}"
    try:
        return json.dumps(response.json(), ensure_ascii=False, indent=2)
    except Exception:
        return response.text[:1000]


def chesscom_api(
    action: str = "",
    username: str = "",
    year: int = 0,
    month: int = 0,
    title: str = "",
    country_code: str = "",
):
    action = (action or "").lower().strip()

    if action in {"profile", "stats", "online", "games", "to_move", "archives", "monthly", "clubs", "matches"}:
        if not username:
            return "username is required."
        username = username.strip()

    if action == "profile":
        return _get(f"player/{username}")

    if action == "stats":
        return _get(f"player/{username}/stats")

    if action == "online":
        return _get(f"player/{username}/is-online")

    if action == "games":
        return _get(f"player/{username}/games")

    if action == "to_move":
        return _get(f"player/{username}/games/to-move")

    if action == "archives":
        return _get(f"player/{username}/games/archives")

    if action == "monthly":
        if not year or not month:
            return "year and month are required for a monthly archive."
        if not 1 <= int(month) <= 12:
            return "month must be between 1 and 12."
        return _get(f"player/{username}/games/{int(year):04d}/{int(month):02d}")

    if action == "clubs":
        return _get(f"player/{username}/clubs")

    if action == "matches":
        return _get(f"player/{username}/matches")

    if action == "daily_puzzle":
        return _get("puzzle")

    if action == "random_puzzle":
        return _get("puzzle/random")

    if action == "streamers":
        return _get("streamers")

    if action == "leaderboards":
        return _get("leaderboards")

    if action == "titled":
        if not title:
            return "title is required, for example GM, IM, FM, WGM, or WIM."
        return _get(f"titled/{title.upper()}")

    if action == "country_players":
        if not country_code:
            return "country_code is required, for example IN or US."
        return _get(f"country/{country_code.upper()}/players")

    if action == "country_clubs":
        if not country_code:
            return "country_code is required, for example IN or US."
        return _get(f"country/{country_code.upper()}/clubs")

    if action == "pgn":
        if not username or not year or not month:
            return "username, year and month are required for a PGN download."
        if not 1 <= int(month) <= 12:
            return "month must be between 1 and 12."

        url = f"{_BASE}/player/{username}/games/{int(year):04d}/{int(month):02d}/pgn"
        try:
            response = requests.get(
                url,
                headers={"User-Agent": _USER_AGENT},
                timeout=_TIMEOUT,
            )
            if not response.ok:
                return f"Chess.com PGN download failed: HTTP {response.status_code}: {response.text[:1000]}"

            safe_username = "".join(ch for ch in username if ch.isalnum() or ch in "-_")
            filename = f"ChessCom_{safe_username}_{int(year):04d}{int(month):02d}.pgn"
            destination = os.path.join("downloads", filename)
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            with open(destination, "wb") as handle:
                handle.write(response.content)
            return f"Downloaded Chess.com PGN to {os.path.abspath(destination)}"
        except Exception as exc:
            return f"Chess.com PGN download failed: {exc}"

    return (
        "Unknown action. Use profile, stats, online, games, to_move, archives, "
        "monthly, clubs, matches, daily_puzzle, random_puzzle, streamers, "
        "leaderboards, titled, country_players, country_clubs, or pgn."
    )


TOOL = {
    "name": "chesscom_api",
    "description": (
        "Chess.com Published Data API integration. Read public player profiles, stats, "
        "online status, current Daily games, to-move games, monthly archives, clubs, "
        "matches, daily/random puzzles, streamers, leaderboards, titled-player lists, "
        "country player/club lists, and download monthly PGN archives. This is read-only "
        "public data; it cannot make moves or control a Chess.com game. A recognizable "
        "User-Agent with contact information is configured by CHESS_USER_AGENT in .env."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": (
                    "profile | stats | online | games | to_move | archives | monthly | "
                    "clubs | matches | daily_puzzle | random_puzzle | streamers | "
                    "leaderboards | titled | country_players | country_clubs | pgn"
                ),
            },
            "username": {"type": "STRING", "description": "Chess.com username"},
            "year": {"type": "INTEGER", "description": "Four-digit archive year"},
            "month": {"type": "INTEGER", "description": "Archive month 1-12"},
            "title": {"type": "STRING", "description": "Chess title abbreviation, for titled action"},
            "country_code": {"type": "STRING", "description": "ISO country code, for example IN"},
        },
        "required": ["action"],
    },
    "handler": chesscom_api,
}
