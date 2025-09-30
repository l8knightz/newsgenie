import os
from dotenv import load_dotenv
import streamlit as st
from graph.workflow import build_graph

# ---------- Setup ----------
load_dotenv()
st.set_page_config(page_title="NewsGenie", layout="wide")

if "history" not in st.session_state:
    st.session_state.history = []
if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("### Filters")
    cats = st.multiselect(
        "Categories",
    ["Top US", "Top Global", "Technology", "Finance", "Sports"],
    ["Top US", "Technology", "Finance", "Sports"]
    )
    query_hint = st.text_input(
        "Optional topic filter (e.g., 'Nvidia', 'GDP', 'Cowboys')", ""
    )
    st.caption("General Q&A Using OpenAI)")
    st.markdown("---")
    st.markdown("**Legend**")
    st.caption("🟥 Left · 🟦 Center · 🟧 Right · ⬜️ Unknown · ✅ corroborated")

# ---------- Title ----------
#st.title("📰 NewsGenie — AI News & Info Assistant")  Old title, replacing with logo/headline
# streamlit making this difficult, so using base64 inline image
import base64
from pathlib import Path

def _img_b64(path: str) -> str:
    p = Path(path)
    return base64.b64encode(p.read_bytes()).decode()

# File is at project root inside the container (/app/NewsGenie-sm.png)
logo_b64 = _img_b64("NewsGenie-sm.png")

st.markdown(
    f"""
    <div style="
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        margin: 10px 0 18px;
    ">
      <img src="data:image/png;base64,{logo_b64}" width="100" alt="NewsGenie Logo"
           style="border-radius:12px; display:block;"/>
      <h1 style="margin:10px 0 4px; line-height:1.1;">NewsGenie</h1>
      <p style="margin:0; color:#94a3b8; font-size:16px;">AI News &amp; Info Assistant</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------- Graph runner ----------
def run_graph(text: str, category: str | None, qhint: str | None) -> str:
    g = st.session_state.graph
    out = g.invoke({
        "user_text": text,
        "category": category,
        "query_hint": qhint
    })
    return out.get("answer", "(no answer)")

# ---------- Chat loop ----------
user_text = st.chat_input("Ask for headlines or any quick answer…")
if user_text:
    st.session_state.history.append(("user", user_text))
    lower = user_text.lower()

    sports_terms = [
        "nfl","nba","mlb","nhl","soccer","premier","la liga","bundesliga",
        "bears","cowboys","packers","chiefs","eagles","vikings","patriots"  # add more as desired
    ]
    is_sports_query = any(t in lower for t in sports_terms)

    is_news = any(tok in lower for tok in [
        "news","latest","headlines","today","breaking"
    ]) or is_sports_query or any(tok in lower for tok in ["market","stock","ai","chip","tesla","cloud"])

    # Always pass the chat text as the search hint for newsy asks
    if is_news:
        # If it's clearly sports, force categories to ["Sports"] for this turn
        run_cats = ["Sports"] if is_sports_query else (cats or ["Technology","Finance","Sports"])
        for c in run_cats:
            ans = run_graph(user_text, c, user_text)  # <- user_text as query_hint
            st.session_state.history.append(("assistant", ans))
    else:
        ans = run_graph(user_text, None, None)
        st.session_state.history.append(("assistant", ans))

# Render chat history - added html because output wasn't easily readable
for role, msg in st.session_state.history:
    with st.chat_message(role):
        st.markdown(msg, unsafe_allow_html=True)

st.markdown("---")
st.caption("Degraded mode auto-falls back to mock news if live fetch fails. "
           "General Q&A uses OpenAI with concise responses.")
