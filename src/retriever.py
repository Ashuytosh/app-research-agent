# Firecrawl search-then-scrape retriever: finds and scrapes real docs pages so evidence_url can never be fabricated.
import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from firecrawl import Firecrawl

load_dotenv()

_client = None
MAX_CHARS = 8000


def _get_client() -> Firecrawl:
    global _client
    if _client is None:
        _client = Firecrawl(api_key=os.environ["FIRECRAWL_API_KEY"])
    return _client


def _domain(url: str) -> str:
    return urlparse(url).netloc.lower().removeprefix("www.")


def _pick_result_url(app_name: str, hint_url: str) -> str | None:
    try:
        results = _get_client().search(f"{app_name} API authentication documentation", limit=5)
    except Exception:
        return None

    web_results = results.web or []
    if not web_results:
        return None

    hint_domain = _domain(hint_url) if hint_url else ""
    if hint_domain:
        for result in web_results:
            if _domain(result.url) == hint_domain:
                return result.url

    return web_results[0].url


def _scrape(url: str) -> str:
    try:
        document = _get_client().scrape(url, formats=["markdown"])
    except Exception:
        return ""
    return (document.markdown or "")[:MAX_CHARS]


def search_and_scrape(app_name: str, hint_url: str) -> dict:
    chosen_url = _pick_result_url(app_name, hint_url) or hint_url
    content = _scrape(chosen_url) if chosen_url else ""

    if not content and chosen_url != hint_url:
        chosen_url = hint_url
        content = _scrape(hint_url) if hint_url else ""

    print(f"[retriever] {app_name}: url={chosen_url} content_len={len(content)}")
    return {"url": chosen_url, "content": content}
