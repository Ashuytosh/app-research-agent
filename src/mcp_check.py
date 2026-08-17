# Dedicated Firecrawl search for MCP server presence; has_mcp is never inferred from the auth-docs page.
from retriever import _get_client

MCP_HINTS = ("mcp", "model context protocol")


def _looks_like_mcp_result(app_name: str, title: str, description: str, url: str) -> bool:
    app_lower = app_name.lower()
    haystacks = (title.lower(), description.lower(), url.lower())
    mentions_mcp = any(hint in text for hint in MCP_HINTS for text in haystacks)
    mentions_app = any(app_lower in text for text in haystacks)
    return mentions_mcp and mentions_app


def check_mcp(app_name: str) -> dict:
    try:
        results = _get_client().search(f"{app_name} MCP server model context protocol", limit=5)
    except Exception:
        print(f"[mcp_check] {app_name}: has_mcp=False evidence=")
        return {"has_mcp": False, "mcp_evidence_url": ""}

    for result in results.web or []:
        title = result.title or ""
        description = result.description or ""
        if _looks_like_mcp_result(app_name, title, description, result.url):
            print(f"[mcp_check] {app_name}: has_mcp=True evidence={result.url}")
            return {"has_mcp": True, "mcp_evidence_url": result.url}

    print(f"[mcp_check] {app_name}: has_mcp=False evidence=")
    return {"has_mcp": False, "mcp_evidence_url": ""}
