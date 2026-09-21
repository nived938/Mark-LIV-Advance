"""Local searchable Knowledge Vault.

This is intentionally separate from normal file search. File search answers
"where is this file?"; the vault builds a persistent text index so J.A.R.V.I.S.
can answer questions across selected documents and return source paths.
"""

from __future__ import annotations

import json
import re
import sqlite3
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
DIR = ROOT / "memory" / "knowledge_vault"
DB = DIR / "vault.db"

TEXT_EXTS = {
    ".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".json", ".yaml", ".yml", ".xml", ".csv", ".sql", ".java", ".cs", ".cpp",
    ".h", ".hpp", ".go", ".rs", ".toml", ".ini", ".cfg", ".log",
}


def _db() -> sqlite3.Connection:
    DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            path TEXT PRIMARY KEY,
            collection TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            content TEXT NOT NULL DEFAULT '',
            modified REAL NOT NULL DEFAULT 0
        )
    """)
    try:
        con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(path, collection, title, content)")
    except sqlite3.OperationalError:
        pass
    con.commit()
    return con


def _extract(path: Path) -> str:
    if path.suffix.lower() in TEXT_EXTS:
        return path.read_text(encoding="utf-8", errors="ignore")

    if path.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(path) as z:
                xml = z.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            return "\n".join(t.text or "" for t in root.iter() if t.tag.endswith("}t"))
        except Exception:
            return ""

    if path.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader
            return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        except Exception:
            return ""

    return ""


def index_path(root: str, collection: str = "") -> dict:
    target = Path(root).expanduser()
    if not target.exists():
        return {"ok": False, "message": f"Path not found: {target}"}

    files = [target] if target.is_file() else [
        p for p in target.rglob("*") if p.is_file()
    ]
    indexed = 0
    skipped = 0

    with _db() as con:
        for path in files:
            if path.name.startswith("~$") or path.suffix.lower() not in TEXT_EXTS | {".docx", ".pdf"}:
                skipped += 1
                continue
            try:
                text = _extract(path)
                if not text.strip():
                    skipped += 1
                    continue
                resolved = str(path.resolve())
                col = str(collection or "").strip()[:80]
                con.execute(
                    "INSERT INTO documents(path,collection,title,content,modified) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(path) DO UPDATE SET collection=excluded.collection,title=excluded.title,"
                    "content=excluded.content,modified=excluded.modified",
                    (resolved, col, path.name, text[:500000], path.stat().st_mtime),
                )
                indexed += 1
            except (OSError, UnicodeError):
                skipped += 1

        try:
            con.execute("DELETE FROM documents_fts")
            con.execute(
                "INSERT INTO documents_fts(path,collection,title,content) "
                "SELECT path,collection,title,content FROM documents"
            )
        except sqlite3.OperationalError:
            pass
        con.commit()

    return {"ok": True, "indexed": indexed, "skipped": skipped, "root": str(target)}


def search_vault(query: str, collection: str = "", limit: int = 8) -> list[dict]:
    q = str(query or "").strip()
    if not q:
        return []

    limit = max(1, min(int(limit), 20))
    with _db() as con:
        try:
            terms = " ".join(re.findall(r"[A-Za-z0-9_]+", q))
            if not terms:
                terms = q.replace('"', " ")
            rows = con.execute(
                "SELECT path,collection,title,"
                "snippet(documents_fts,3,'[',']','…',24) AS snippet, "
                "bm25(documents_fts) AS rank "
                "FROM documents_fts WHERE documents_fts MATCH ? "
                "AND (?='' OR collection=?) "
                "ORDER BY rank LIMIT ?",
                (terms, collection, collection, limit),
            ).fetchall()
            return [dict(x) for x in rows]
        except sqlite3.OperationalError:
            like = f"%{q}%"
            rows = con.execute(
                "SELECT path,collection,title,substr(content,1,500) AS snippet,0 AS rank "
                "FROM documents WHERE (title LIKE ? OR content LIKE ?) "
                "AND (?='' OR collection=?) LIMIT ?",
                (like, like, collection, collection, limit),
            ).fetchall()
            return [dict(x) for x in rows]


def vault_status() -> dict:
    with _db() as con:
        count = con.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        collections = con.execute(
            "SELECT collection,COUNT(*) AS count FROM documents GROUP BY collection ORDER BY collection"
        ).fetchall()
    return {"documents": int(count), "collections": [dict(x) for x in collections]}


def remove_collection(collection: str) -> int:
    with _db() as con:
        cur = con.execute("DELETE FROM documents WHERE collection=?", (str(collection or "").strip(),))
        try:
            con.execute("DELETE FROM documents_fts")
            con.execute(
                "INSERT INTO documents_fts(path,collection,title,content) "
                "SELECT path,collection,title,content FROM documents"
            )
        except sqlite3.OperationalError:
            pass
        return int(cur.rowcount)
