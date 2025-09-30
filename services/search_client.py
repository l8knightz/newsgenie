# services/search_client.py
import os
import httpx
from typing import List, Tuple
import tldextract

SEARCH_API_KEY = os.getenv("SEARCH_API_KEY", "").strip()
SEARCH_PROVIDER = os.getenv("SEARCH_PROVIDER", "bing").lower()  # 'bing' or 'serpapi'

def _domain(url: str) -> str:
    try:
        ext = tldextract.extract(url)
        return ".".join([p for p in [ext.domain, ext.suffix] if p])
    except Exception:
        return ""

def web_search_domains(query: str, top_k: int = 5) -> List[str]:
    """
    Returns a list of result domains for simple corroboration.
    Gracefully degrades to [] if no key/provider.
    """
    if not SEARCH_API_KEY:
        return []

    try:
        if SEARCH_PROVIDER == "bing":
            # Bing Web Search v7
            url = "https://api.bing.microsoft.com/v7.0/search"
            headers = {"Ocp-Apim-Subscription-Key": SEARCH_API_KEY}
            params = {"q": query, "count": top_k, "responseFilter": "Webpages", "textDecorations": "false"}
            with httpx.Client(timeout=8) as client:
                r = client.get(url, headers=headers, params=params)
                r.raise_for_status()
                data = r.json()
                items = (data.get("webPages", {}) or {}).get("value", []) or []
                urls = [it.get("url","") for it in items if it.get("url")]
                return [_domain(u) for u in urls if u]
        # add other providers here (SerpAPI, etc.)
        return []
    except Exception:
        return []
