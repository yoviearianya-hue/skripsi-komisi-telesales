FROM python:3.11-slim

LABEL maintainer="Yovie - Skripsi Sistem Komisi Telesales ISP"
LABEL description="Container Terisolasi: Dashboard Streamlit + Bot Telegram ALPHA WOLF SQUAD + Cloudflare Go-Live Tunnel + Seluruh Data Excel/Prospect"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Jakarta \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install utilitas sistem & binary resmi Cloudflare Tunnel versi Linux (tanpa mengganggu sistem lain)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    tzdata \
    && curl -fsSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared \
    && chmod +x /usr/local/bin/cloudflared \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install seluruh library Python sesuai requirements.txt
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

# Masukkan SELURUH file codingan (.py, .md, .toml) beserta SELURUH file data (.xlsx, .xls) ke dalam image Docker
COPY . /app

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8501/_stcore/health || exit 1

CMD ["python", "-u", "golive_server.py"]
