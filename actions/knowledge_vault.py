from core.knowledge_vault import index_path, remove_collection, search_vault, vault_status


def knowledge_vault(parameters: dict = None, player=None, **_) -> str:
    p = parameters or {}
    action = str(p.get("action", "status")).strip().lower()

    if action == "index":
        result = index_path(p.get("path", ""), p.get("collection", ""))
        if not result.get("ok"):
            return result["message"]
        return (
            f"Knowledge Vault indexed {result['indexed']} document(s), skipped "
            f"{result['skipped']}. Root: {result['root']}"
        )

    if action == "search":
        rows = search_vault(
            p.get("query", ""),
            p.get("collection", ""),
            p.get("limit", 8),
        )
        if not rows:
            return "No matching knowledge-vault sources found."
        lines = ["Knowledge Vault sources:"]
        for row in rows:
            lines.append(
                f"- {row['title']} | {row['path']} | "
                f"{row.get('snippet','')[:700]}"
            )
        return "
".join(lines)

    if action == "status":
        s = vault_status()
        cols = ", ".join(
            f"{x['collection'] or 'default'}:{x['count']}" for x in s["collections"]
        ) or "none"
        return f"Knowledge Vault: {s['documents']} documents. Collections: {cols}."

    if action == "remove_collection":
        n = remove_collection(p.get("collection", ""))
        return f"Removed {n} document(s) from collection '{p.get('collection','')}'."

    return "Use action=index/search/status/remove_collection."


TOOL = {
    "name": "knowledge_vault",
    "description": (
        "Persistent local Knowledge Vault for user-selected documents. Index folders/files, "
        "search across their contents, and return source paths/snippets so answers can cite "
        "which local document the information came from. Different from file search: this is "
        "a reusable knowledge index, not filename lookup."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {"type": "STRING", "description": "index | search | status | remove_collection"},
            "path": {"type": "STRING", "description": "File or folder to index"},
            "collection": {"type": "STRING", "description": "Optional collection name such as Coding or School"},
            "query": {"type": "STRING", "description": "Question/keywords to search"},
            "limit": {"type": "INTEGER", "description": "Maximum sources"}
        },
        "required": ["action"]
    },
    "handler": knowledge_vault,
}
