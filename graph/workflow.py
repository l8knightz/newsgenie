import os
import orjson, sys, time
from typing import TypedDict, Literal, List, Dict, Optional
from datetime import datetime
from langgraph.graph import StateGraph, END
from openai import OpenAI
from services.search_client import web_search_domains
from logic.credibility import DOMAIN_TRUST
from services.news_client import fetch_rank_ready, REGION
from logic.credibility import domain_from_url, combined_score, bias_label

OPENAI_MODEL = os.getenv("OPENAI_MODEL","gpt-4o-mini")

class State(TypedDict, total=False):
    user_text: str
    intent: Literal["News.Fetch","General.Fact"]
    category: Optional[str]
    query_hint: Optional[str]
    articles: List[Dict]
    answer: str
    ts: str

def route_intent(text: str) -> str:
    t = text.lower()
    news_tokens = ["news","latest","today","headlines","breaking","earnings","market","stock","fed","gdp",
                   "nfl","nba","mlb","soccer","premier","game","score","ai","chip","iphone","tesla",
                   "cloud","kubernetes","microsoft","google"]
    return "News.Fetch" if any(tok in t for tok in news_tokens) else "General.Fact"

def router_node(state: State) -> State:
    intent = route_intent(state["user_text"])
    return {**state, "intent": intent}

def news_node(state: State) -> State:
    cat = state.get("category") or "Technology"
    # NEW: prefer sidebar query_hint; else fall back to user's message
    q = state.get("query_hint") or state.get("user_text")  # <<< add this line / replace old q

    raw, source_label = fetch_rank_ready(cat, REGION, q)

    ranked = []
    for a in raw:
        d = domain_from_url(a.get("url",""))
        score = combined_score(d, a["dt"])

        # (…leave the corroboration code as you have it…)
        ranked.append({
            **a,
            "__score": round(score,3),
            "domain": d,
            "bias": bias_label(d),
            "corroborated": a.get("corroborated", False),
        })

    ranked.sort(key=lambda x: x["__score"], reverse=True)
    return {**state, "articles": ranked[:4], "degraded": (source_label == "mock")}


## Structured logging helper (using orjson for speed)
def log_event(event: str, **kwargs):
    payload = {"ts": time.time(), "event": event, **kwargs}
    sys.stdout.write(orjson.dumps(payload).decode() + "\n")
    sys.stdout.flush()

## updated this to use html to hopefully make it more readable
def format_news(state: State) -> State:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")

    def pill(text: str, bg: str, fg: str = "#fff"):
        return f"<span style='display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;background:{bg};color:{fg};margin-left:6px'>{text}</span>"

    def bias_badge(label: str) -> str:
        colors = {
            "Left": ("#ef4444", "#fff"),
            "Right": ("#f59e0b", "#111"),
            "Center": ("#3b82f6", "#fff"),
            "Center (est.)": ("#60a5fa", "#fff"),
            "Unknown": ("#e5e7eb", "#111"),
        }
        bg, fg = colors.get(label, ("#e5e7eb", "#111"))
        return pill(f"Bias: {label}", bg, fg)

    def cred_badge(score: float) -> str:
        # green if >=0.85, amber 0.75–0.85, grey else
        if score >= 0.85: bg, fg = "#10b981", "#111"
        elif score >= 0.75: bg, fg = "#f59e0b", "#111"
        else: bg, fg = "#9ca3af", "#111"
        return pill(f"Cred {score:.2f}", bg, fg)

    def corr_badge(ok: bool) -> str:
        return pill("✅ corroborated" if ok else "—", "#e5e7eb", "#111")

    header = (
        f"<div style='margin-bottom:8px'><strong>{state.get('category','Technology')} — Updated:</strong> {ts}"
        f" &nbsp; <strong>Region:</strong> {REGION.upper()}</div>"
    )
    if state.get("degraded"):
        header += "<div style='color:#b45309'>⚠️ Degraded mode: cached/mock results while live feed recovers.</div>"

    qshow = state.get("query_hint") or state.get("user_text") or ""
    if qshow:
        header += f"<div style='opacity:.8;margin-bottom:8px'>Query used: <strong>{qshow}</strong></div>"

    parts = [header]
    arts = state.get("articles", [])
    if not arts:
        parts.append("<em>No credible updates right now.</em>")
    else:
        for i, a in enumerate(arts, 1):
            when = a["dt"].astimezone().strftime("%b %d, %H:%M")
            title = a.get("title","(untitled)")
            desc = a.get("description","")
            url = a.get("url","")
            src = a.get("source") or a.get("domain") or "Unknown"
            score = float(a.get("__score", 0.0))
            bias = a.get("bias","Unknown")
            corr = bool(a.get("corroborated", False))

            parts.append(
                "<div style='padding:12px 14px;margin:10px 0;border:1px solid #e5e7eb;"
                "border-radius:12px;background:#0b0f19;'>"  # nice dark card
                f"<div style='font-weight:600;font-size:16px;margin-bottom:4px;'>"
                f"{i}) <a href='{url}' target='_blank' style='text-decoration:none;color:#60a5fa'>{title}</a></div>"
                f"<div style='opacity:.9;margin-bottom:6px'>{desc}</div>"
                f"<div style='opacity:.85'>Source: <strong>{src}</strong> · "
                f"Published: {when} {cred_badge(score)} {bias_badge(bias)} {corr_badge(corr)}</div>"
                "</div>"
            )

    return {**state, "answer": "\n".join(parts), "ts": ts}


def general_node(state: State) -> State:
    client = OpenAI()
    prompt = (
        "Answer concisely (≤120 words). If a claim is uncertain, say so briefly.\n\n"
        f"Question: {state['user_text']}"
    )
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
    )
    txt = resp.choices[0].message.content.strip()
    return {**state, "answer": txt, "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}

def build_graph():
    g = StateGraph(State)
    g.add_node("router", router_node)
    g.add_node("news", news_node)
    g.add_node("format_news", format_news)
    g.add_node("general", general_node)

    g.set_entry_point("router")
    # edges
    g.add_conditional_edges(
        "router",
        lambda s: s["intent"],
        {
            "News.Fetch": "news",
            "General.Fact": "general",
        }
    )
    g.add_edge("news","format_news")
    g.add_edge("format_news", END)
    g.add_edge("general", END)
    return g.compile()
