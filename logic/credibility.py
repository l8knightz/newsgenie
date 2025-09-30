from datetime import datetime, timezone
import tldextract

# Expandable leaning dictionary
POLITICAL_LEANING = {
    # Left
    "nytimes.com":"Left","theguardian.com":"Left","huffpost.com":"Left","vox.com":"Left",
    # Center
    "reuters.com":"Center","apnews.com":"Center","bbc.com":"Center","npr.org":"Center","associatedpress.com":"Center",
    # Right
    "wsj.com":"Right","foxnews.com":"Right","washingtontimes.com":"Right","nationalreview.com":"Right",
    # Tech/finance/sports (usually non-partisan; we’ll infer Center)
    "bloomberg.com":"Center","cnbc.com":"Center","theverge.com":"Center","techcrunch.com":"Center",
    "espn.com":"Center","theathletic.com":"Center","nfl.com":"Center",
}

DOMAIN_TRUST = {
    "reuters.com":0.95,"apnews.com":0.93,"bbc.com":0.90,"bloomberg.com":0.92,"wsj.com":0.88,
    "cnbc.com":0.85,"theguardian.com":0.84,"foxnews.com":0.75,"npr.org":0.90,
    "theverge.com":0.80,"techcrunch.com":0.80,"espn.com":0.88,"theathletic.com":0.90,"nfl.com":0.85,
}

def domain_from_url(url: str) -> str:
    try:
        ext = tldextract.extract(url)
        return ".".join([p for p in [ext.domain, ext.suffix] if p])
    except Exception:
        return ""

def trust_score(domain: str) -> float:
    return DOMAIN_TRUST.get(domain, 0.65)

def freshness_score(published_at: datetime) -> float:
    age_h = max(0.0, (datetime.now(timezone.utc)-published_at).total_seconds()/3600.0)
    if age_h <= 6: return 1.0
    if age_h >= 48: return 0.5
    return 1.0 - (age_h-6.0)*(0.5/42.0)

def combined_score(domain: str, published_at: datetime) -> float:
    return 0.6*trust_score(domain) + 0.4*freshness_score(published_at)

def bias_label(domain: str) -> str:
    # Heuristic: if unknown but trust >=0.9, call it Center; if 0.8–0.9, call it “Center (est.)”
    if domain in POLITICAL_LEANING:
        return POLITICAL_LEANING[domain]
    ts = trust_score(domain)
    if ts >= 0.90: return "Center"
    if ts >= 0.80: return "Center (est.)"
    return "Unknown"
