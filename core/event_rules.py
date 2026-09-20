"""Persistent event-rule engine using lightweight polling.

Rules are stored locally. Supported events:
- file_created
- file_changed
- process_started

When a rule fires, the instruction is sent back to the normal J.A.R.V.I.S.
conversation path so the existing model/tool system decides what to do next.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "memory" / "event_rules.json"


def _load() -> dict:
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return {"rules": [], "enabled": False}


def _save(d: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")


class EventRuleEngine:
    def __init__(self):
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._player = None
        self._seen: dict[str, dict] = {}

    def configure_player(self, player) -> None:
        self._player = player

    def start(self, player=None) -> None:
        if player is not None:
            self._player = player
        d = _load()
        d["enabled"] = True
        _save(d)
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="jarvis-event-rules")
        self._thread.start()

    def stop(self) -> None:
        d = _load()
        d["enabled"] = False
        _save(d)
        self._stop.set()

    def add(self, event: str, path: str = "", pattern: str = "", instruction: str = "", name: str = "") -> dict:
        event = str(event or "").strip().lower()
        if event not in {"file_created", "file_changed", "process_started"}:
            return {"ok": False, "message": "Event must be file_created, file_changed, or process_started."}
        instruction = str(instruction or "").strip()
        if not instruction:
            return {"ok": False, "message": "A THEN instruction is required."}

        d = _load()
        rule = {
            "id": uuid.uuid4().hex[:10],
            "name": str(name or f"{event} rule").strip()[:80],
            "event": event,
            "path": str(path or "").strip(),
            "pattern": str(pattern or "").strip().lower(),
            "instruction": instruction[:1000],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        d.setdefault("rules", []).append(rule)
        _save(d)
        return {"ok": True, "rule": rule}

    def remove(self, rule_id: str) -> bool:
        d = _load()
        before = len(d.get("rules") or [])
        d["rules"] = [r for r in d.get("rules") or [] if str(r.get("id")) != str(rule_id)]
        _save(d)
        return len(d["rules"]) != before

    def list(self) -> list[dict]:
        return list(_load().get("rules") or [])

    def _emit(self, rule: dict, detail: str) -> None:
        player = self._player
        if player is None:
            return
        msg = (
            f"[EVENT RULE FIRED] {rule.get('name','rule')}: {detail}. "
            f"Execute this instruction if appropriate: {rule.get('instruction','')}"
        )
        try:
            cb = getattr(player, "on_text_command", None)
            if callable(cb):
                threading.Thread(target=cb, args=(msg,), daemon=True).start()
            else:
                player.write_log(msg)
        except Exception:
            pass

    def _file_state(self, root: Path, pattern: str) -> dict[str, float]:
        state = {}
        if root.is_file():
            files = [root]
        elif root.is_dir():
            files = list(root.glob(pattern or "*"))
        else:
            return state
        for p in files:
            try:
                if p.is_file():
                    state[str(p.resolve())] = p.stat().st_mtime
            except OSError:
                pass
        return state

    def _loop(self) -> None:
        while not self._stop.wait(3):
            rules = self.list()
            for rule in rules:
                try:
                    event = rule.get("event")
                    if event in {"file_created", "file_changed"}:
                        root = Path(str(rule.get("path") or "")).expanduser()
                        current = self._file_state(root, str(rule.get("pattern") or "*").strip())
                        key = f"file:{rule.get('id')}"
                        old = self._seen.get(key, {})
                        self._seen[key] = current
                        if not old:
                            continue
                        created = set(current) - set(old)
                        changed = {
                            p for p in set(current) & set(old)
                            if current[p] > old[p] + 0.5
                        }
                        candidates = created if event == "file_created" else changed
                        if candidates:
                            detail = ", ".join(sorted(candidates)[:4])
                            self._emit(rule, detail)
                    elif event == "process_started":
                        wanted = str(rule.get("pattern") or "").strip().lower()
                        if not wanted:
                            continue
                        try:
                            import psutil
                            now = {
                                str(p.pid): str(p.info.get("name") or "").lower()
                                for p in psutil.process_iter(["pid", "name"])
                            }
                        except Exception:
                            continue
                        key = f"proc:{rule.get('id')}"
                        old = self._seen.get(key, {})
                        self._seen[key] = now
                        if not old:
                            continue
                        for pid, name in now.items():
                            if pid not in old and (name == wanted or wanted in name):
                                self._emit(rule, f"process {name} started (PID {pid})")
                                break
                except Exception:
                    continue


ENGINE = EventRuleEngine()
