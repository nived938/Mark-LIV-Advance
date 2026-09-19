def web_search_advance(query: str, max_results: int = 5):
    query = (query or "").strip()
    if not query:
        return "No search query supplied."
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=max(1, min(int(max_results), 10)))
        lines = []
        for r in results:
            lines.append(f"{r.get('title','')}\n{r.get('href','')}\n{r.get('body','')}")
        return "\n\n".join(lines) if lines else "No web results found."
    except Exception as e:
        return f"Web search failed: {e}"

TOOL = {
    "name": "web_search_advance",
    "description": "Search the public web and return concise result titles, URLs, and snippets.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "query": {"type": "STRING", "description": "Search query"},
            "max_results": {"type": "INTEGER", "description": "Maximum results, up to 10"},
        },
        "required": ["query"],
    },
    "handler": web_search_advance,
}
