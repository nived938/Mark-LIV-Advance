"""Conservative self-healing for JARVIS Python action/core modules."""
from __future__ import annotations

import ast
import json
import shutil
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "memory" / "self_heal_state.json"
BACKUPS = ROOT / "memory" / "self_heal_backups"
_LOCK = threading.RLock()

class SelfHealEngine:
    def __init__(self):
        self._failures = {}
        self._repairing = set()
        self._load()

    def _load(self):
        try:
            data = json.loads(STATE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._failures = data.get("failures", {})
        except Exception:
            self._failures = {}

    def _save(self):
        try:
            STATE.parent.mkdir(parents=True, exist_ok=True)
            STATE.write_text(json.dumps({"failures": self._failures, "updated_at": time.time()}, indent=2), encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _target_for(name):
        clean = str(name or "").strip().replace("\\", "/")
        if clean.endswith(".py"):
            path = (ROOT / clean).resolve()
        elif clean.startswith("core/"):
            path = (ROOT / (clean + ".py")).resolve()
        else:
            path = (ROOT / "actions" / (clean + ".py")).resolve()
        allowed = [(ROOT / "actions").resolve(), (ROOT / "core").resolve()]
        if not any(path.is_relative_to(base) for base in allowed):
            return None
        if path.name in {"main.py", "ui.py"}:
            return None
        return path

    @staticmethod
    def _compile(path):
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source, filename=str(path))
            compile(source, str(path), "exec")
            return True, ""
        except Exception as exc:
            return False, str(exc)

    @staticmethod
    def _json_object(text):
        text = str(text or "").strip()
        a, b = text.find("{"), text.rfind("}")
        if a < 0 or b <= a:
            return None
        try:
            value = json.loads(text[a:b + 1])
            return value if isinstance(value, dict) else None
        except Exception:
            return None

    def observe_failure(self, name, error):
        key = str(name or "unknown")
        now = time.time()
        with _LOCK:
            rec = self._failures.setdefault(key, {"count": 0, "last_at": now, "last_error": ""})
            if now - float(rec.get("last_at", 0)) > 900:
                rec["count"] = 0
            rec["count"] = int(rec.get("count", 0)) + 1
            rec["last_at"] = now
            rec["last_error"] = str(error)[:1200]
            self._save()
            should_repair = rec["count"] >= 2 and key not in self._repairing
        if should_repair:
            threading.Thread(target=self._repair_worker, args=(key, str(error)), daemon=True, name="JARVIS-SelfHeal").start()

    def _repair_worker(self, name, error):
        with _LOCK:
            if name in self._repairing:
                return
            self._repairing.add(name)
        try:
            print(f"[SelfHeal] {name}: {self.repair(name, error, automatic=True)}")
        except Exception as exc:
            print(f"[SelfHeal] {name}: repair failed: {exc}")
        finally:
            with _LOCK:
                self._repairing.discard(name)

    def repair(self, name, error="", automatic=False):
        path = self._target_for(name)
        if path is None or not path.exists():
            return "Self-heal target is not an allowed existing Python module."
        source = path.read_text(encoding="utf-8")
        try:
            from core import gemini
            prompt = ("Repair this one Python module. Return ONLY JSON with keys "
                      "search and replace. search must be an exact substring from "
                      "the source and occur once. replace is corrected code. Make "
                      "the smallest possible change and add no dependencies.\n\n"
                      f"File: {path.relative_to(ROOT)}\n"
                      f"Runtime error: {str(error)[:1600]}\n\nSource:\n{source[-24000:]}")
            reply = gemini.call(prompt, tier=gemini.SMART, timeout_ms=30000)
            if reply is None:
                return "Gemini did not return a repair patch."
            patch = self._json_object(getattr(reply, "text", ""))
            if not patch:
                return "Repair response was not valid JSON."
            search = str(patch.get("search") or "")
            replace = str(patch.get("replace") or "")
            if not search or source.count(search) != 1:
                return "Repair rejected because the search text was not unique."
            candidate = source.replace(search, replace, 1)
            try:
                ast.parse(candidate, filename=str(path))
                compile(candidate, str(path), "exec")
            except Exception as exc:
                return f"Repair rejected by compile validation: {exc}"
            BACKUPS.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y%m%d-%H%M%S")
            backup = BACKUPS / f"{path.stem}-{stamp}-{path.stat().st_mtime_ns}.py"
            shutil.copy2(path, backup)
            path.write_text(candidate, encoding="utf-8")
            ok, err = self._compile(path)
            if not ok:
                shutil.copy2(backup, path)
                return f"Repair rolled back: {err}"
            mode = "automatic" if automatic else "manual"
            return f"Applied {mode} repair to {path.relative_to(ROOT)}; backup={backup.name}"
        except Exception as exc:
            return f"Repair error: {exc}"

    def restore_last(self, name):
        path = self._target_for(name)
        if path is None:
            return "Restore target is not allowed."
        backups = sorted(BACKUPS.glob(f"{path.stem}-*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            return "No self-heal backup exists for that module."
        try:
            shutil.copy2(backups[0], path)
            ok, err = self._compile(path)
            return f"Restored {path.relative_to(ROOT)} from {backups[0].name}." if ok else f"Restore compile check failed: {err}"
        except Exception as exc:
            return f"Restore failed: {exc}"

    def status(self):
        with _LOCK:
            if not self._failures:
                return "Self-healing is active; no repeated module failures are recorded."
            return "Self-healing status:\n" + "\n".join(
                f"{name}: {rec.get('count', 0)} failures — {rec.get('last_error', '')[:180]}"
                for name, rec in sorted(self._failures.items())
            )

ENGINE = SelfHealEngine()