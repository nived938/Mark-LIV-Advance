"""Self-update helper for the source checkout.

The updater is intentionally conservative:
- check compares local HEAD with origin/main;
- apply uses git pull --ff-only and refuses a dirty working tree;
- no hard reset is performed, so local changes cannot be destroyed silently.
"""

from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str, timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        return p.returncode, (p.stdout or p.stderr or "").strip()
    except Exception as exc:
        return 1, str(exc)


def _repo_slug() -> str:
    rc, remote = _git("config", "--get", "remote.origin.url")
    if rc != 0:
        return ""
    remote = remote.strip()
    m = re.search(r"github\.com[:/]+([^/]+)/([^/#]+?)(?:\.git)?$", remote)
    return f"{m.group(1)}/{m.group(2)}" if m else ""


def check_update() -> dict:
    rc1, head = _git("rev-parse", "HEAD")
    rc2, branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    rc3, dirty = _git("status", "--porcelain")
    if rc1 or rc2:
        return {"ok": False, "message": "This installation is not a valid Git checkout."}

    slug = _repo_slug()
    if not slug:
        return {"ok": False, "message": "Could not determine the GitHub repository from origin."}

    req = urllib.request.Request(
        f"https://api.github.com/repos/{slug}/commits/main",
        headers={"User-Agent": "JARVIS-self-updater"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            latest = json.loads(resp.read().decode("utf-8"))
        remote_sha = str(latest.get("sha") or "")
        message = str((latest.get("commit") or {}).get("message") or "").splitlines()[0]
    except Exception as exc:
        return {"ok": False, "message": f"Could not query GitHub: {exc}"}

    return {
        "ok": True,
        "repo": slug,
        "branch": branch,
        "local": head,
        "remote": remote_sha,
        "update_available": bool(remote_sha and remote_sha != head),
        "dirty": bool(dirty.strip()),
        "latest_message": message,
    }


def apply_update() -> str:
    state = check_update()
    if not state.get("ok"):
        return state["message"]
    if state.get("dirty"):
        return (
            "Update not applied: the working tree has local changes. "
            "Commit or stash them first; the updater never performs a destructive reset."
        )
    if not state.get("update_available"):
        return "J.A.R.V.I.S. is already up to date."

    rc, out = _git("fetch", "origin", timeout=30)
    if rc != 0:
        return f"Git fetch failed: {out[:1000]}"

    rc, out = _git("pull", "--ff-only", "origin", "main", timeout=60)
    if rc != 0:
        return f"Safe update failed: {out[:1500]}"

    return (
        "J.A.R.V.I.S. updated successfully. Restart the application to load the new code."
    )
