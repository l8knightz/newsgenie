import os, time
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional, List, Dict
import httpx

class NewsAPIError(Exception): pass

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "").strip()
REGION = os.getenv("REGION", "us")
CACHE_TTL_SEC = int(os.getenv("CACHE_TTL_SEC", "900"))
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"
TOP_GLOBAL_SOURCES = "reuters,associated-press,bbc-news,al-jazeera-english" ## added to be able to use World and US news

def _now_utc():
    return datetime.now(timezone.utc)

def _parse_dt(iso_str: str | None) -> datetime:
    if not iso_str: return _now_utc() - timedelta(days=365)
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z","+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return _now_utc() - timedelta(days=365)

def mock_articles(category: str) -> List[Dict]:
    now = _now_utc()
    demo = [
        {"title":"Nvidia unveils energy-efficient inference GPU",
         "description":"Lower cost per token for LLM serving.",
         "url":"https://www.reuters.com/technology/ai-nvidia-inference-gpu",
         "source":"Reuters","publishedAt":(now - timedelta(hours=2)).isoformat()},
        {"title":"TSMC expands advanced packaging","description":"CoWoS easing GPU bottlenecks.",
         "url":"https://www.bloomberg.com/tsmc-packaging","source":"Bloomberg",
         "publishedAt":(now - timedelta(hours=5)).isoformat()},
        {"title":"Markets slip as yields rise","description":"Energy up on crude strength.",
         "url":"https://www.wsj.com/markets/daily-recap","source":"WSJ",
         "publishedAt":(now - timedelta(hours=3)).isoformat()},
        {"title":"Injury watch reshapes NFL outlook","description":"Star WR questionable.",
         "url":"https://www.espn.com/nfl/story","source":"ESPN",
         "publishedAt":(now - timedelta(hours=7)).isoformat()},
    ]
    if category.lower()=="technology": return demo[:2]
    if category.lower()=="finance": return [demo[2]]
    if category.lower()=="sports": return [demo[3]]
    return demo

def _clean_query(q: str) -> str:
    # Strip fluff like "latest", "headlines" to improve recall
    drop = {"latest", "headlines", "news", "today"}
    tokens = [t for t in q.split() if t.lower() not in drop]
    return " ".join(tokens) or q

def newsapi_top_headlines(category: str, region: str, q: Optional[str]) -> List[Dict]:
    if not NEWS_API_KEY:
        raise NewsAPIError("NEWS_API_KEY missing")
    url = "https://newsapi.org/v2/top-headlines"
    params = {"apiKey": NEWS_API_KEY, "pageSize": 20}

    c = category.lower()
    if c == "top us":
        params["country"] = "us"
    elif c == "top global":
        # rely on trusted global sources; no country
        params["sources"] = TOP_GLOBAL_SOURCES
    else:
        params["country"] = region
        if c in ["technology","business","sports","finance"]:
            params["category"] = "business" if c == "finance" else c

    if q:
        params["q"] = q

    with httpx.Client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "ok":
            raise NewsAPIError("NewsAPI failure")
        arts = data.get("articles", [])
        return [{
            "title": a.get("title"),
            "description": a.get("description"),
            "url": a.get("url"),
            "source": a.get("source", {}).get("name"),
            "publishedAt": a.get("publishedAt"),
        } for a in arts if a.get("url")]


def newsapi_everything(query: str, page_size: int = 20) -> List[Dict]:
    if not NEWS_API_KEY:
        raise NewsAPIError("NEWS_API_KEY missing")
    url = "https://newsapi.org/v2/everything"
    params = {
        "apiKey": NEWS_API_KEY,
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
    }
    with httpx.Client(timeout=10) as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "ok":
            raise NewsAPIError("NewsAPI everything failure")
        arts = data.get("articles", [])
        return [{
            "title": a.get("title"),
            "description": a.get("description"),
            "url": a.get("url"),
            "source": a.get("source", {}).get("name"),
            "publishedAt": a.get("publishedAt"),
        } for a in arts if a.get("url")]


@lru_cache(maxsize=128)
def get_news(category: str, region: str, q: Optional[str], bucket: str) -> List[Dict]:
    if MOCK_MODE or not NEWS_API_KEY:
        return mock_articles(category)
    # Prefer top-headlines for broad category browsing; fallback to everything for specific queries
    try:
        if q:
            cleaned = _clean_query(q)
            # try top-headlines first within category
            primary = newsapi_top_headlines(category, region, cleaned)
            if primary:
                return primary
            # fallback to everything (wider net)
            return newsapi_everything(cleaned)
        else:
            return newsapi_top_headlines(category, region, None)
    except Exception:
        return mock_articles(category)

def fetch_rank_ready(category: str, region: str, q: Optional[str]) -> tuple[list[Dict], str]:
    bucket = str(int(time.time() // CACHE_TTL_SEC))
    using_live = (not MOCK_MODE) and bool(NEWS_API_KEY)
    try:
        items = get_news(category, region, q, bucket)
        source_label = "mock" if (MOCK_MODE or not NEWS_API_KEY) else "live"
    except Exception:
        items = mock_articles(category)
        source_label = "mock"
    for a in items:
        a["dt"] = _parse_dt(a.get("publishedAt"))
    return items, source_label
