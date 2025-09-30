# 📰 NewsGenie – AI-Powered News & Information Assistant

NewsGenie is an interactive, AI-driven assistant that delivers **real-time, curated news updates** and answers to **general knowledge queries** within a unified interface.  
Built with **Streamlit, LangGraph, OpenAI, and NewsAPI**, the app helps users cut through information overload by presenting timely, credible, and clearly labeled stories.

---

## Features

- **Interactive Chat Assistant**  
  Type natural queries – NewsGenie routes them to either live news feeds or general Q&A via an LLM.

- **Real-Time News Integration**  
  Uses [NewsAPI](https://newsapi.org) with smart fallbacks:  
  - `top-headlines` for broad categories (Technology, Finance, Sports, Top US, Top Global)  
  - `everything` endpoint for entity-specific queries (e.g., “Chicago Bears”, “Nvidia CoWoS”)  

- **Credibility & Bias Tagging**  
  Each story is scored for freshness + domain trust and labeled Left / Center / Right bias.

- **Corroboration Check (optional)**  
  Integration with Bing/SerpAPI for ✅ corroboration tags when multiple trusted sources cover the same story.

- **General Q&A**  
  Routes non-news queries to OpenAI for concise, sourced explanations.

- **Streamlit UI**  
  - Sidebar category filters  
  - Centered logo splash header  
  - Session-managed chat history  
  - Responsive, card-style news display

- **Resilient Workflow**  
  LangGraph pipeline handles routing, retries, caching (15-min TTL), and mock fallback when APIs fail.

---

## 🏗️ Architecture
```
User ──> Streamlit UI
│
▼
LangGraph Workflow
├─ RouterNode
│
├─ News Path ─> NewsAPI client → Credibility/Bias scoring → Formatter
│
└─ General Path ─> OpenAI LLM (concise Q&A)
│
Guardrails → Output to UI
```

- **`app/main.py`** – Streamlit UI glue  
- **`graph/workflow.py`** – LangGraph nodes & pipeline  
- **`services/news_client.py`** – NewsAPI + mock + fallback logic  
- **`services/search_client.py`** – Optional web search corroboration  
- **`logic/credibility.py`** – Credibility scoring + political bias labeling  
- **`requirements.txt`** – Python dependencies  
- **`Dockerfile` / `docker-compose.yaml`** – Containerized deployment  
- **`.env`** – API keys & config (never committed)  

---

## 🚀 Deployment Instructions

### Prerequisites
- Docker & Docker Compose v2  
- API keys:  
  - [NewsAPI](https://newsapi.org/) → `NEWS_API_KEY`  
  - [OpenAI](https://platform.openai.com/) → `OPENAI_API_KEY`  
  - *(Optional)* Bing/SerpAPI → `SEARCH_API_KEY`

### 1. Clone the repo
```bash
git clone https://github.com/l8knightz/newsgenie.git
cd newsgenie
```
### 2. Create environment file
```
cp .env.sample .env
```
Edit .env and fill in your API keys. Example:
```
NEWS_API_KEY=your_newsapi_key
OPENAI_API_KEY=your_openai_key
MOCK_MODE=false
REGION=us
CACHE_TTL_SEC=900
TOP_K=4
```
### 3. Build and run
```
docker compose build
docker compose up
```
### 4. Open in browser
Visit: http://localhost:8501

## Repo Layout:
```
newsgenie/
├─ app/
│  └─ main.py
├─ graph/
│  └─ workflow.py
├─ logic/
│  └─ credibility.py
├─ services/
│  ├─ news_client.py
│  └─ search_client.py
├─ tests/                  # (future unit tests)
├─ config/                 # (future configs)
├─ requirements.txt
├─ docker-compose.yaml
├─ Dockerfile
├─ .env.sample
└─ README.md
```
## 🛡️ Fallback & Reliability

Retries: Tenacity with exponential backoff for NewsAPI calls.

Cache: 15-minute TTL to reduce API hits.

Mock Mode: Demo without keys (MOCK_MODE=true).

Degraded Mode: Banner indicates when fallback to mock/cached results is active.

Everything endpoint: Improves recall for specific queries when top-headlines is sparse.

