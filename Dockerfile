FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# OS deps for tldextract (needs publicsuffix list), certs, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gcc build-essential \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app 

# Streamlit defaults
ENV PYTHONPATH=/app \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_HEADLESS=true

EXPOSE 8501
CMD ["streamlit", "run", "app/main.py"]
