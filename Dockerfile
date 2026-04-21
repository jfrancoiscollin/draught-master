# ── Stage 1: Build React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Fetch Scan engine + eval weights ────────────────────────────
# Using the pre-compiled Linux binary from rhalbersma/scan (mirror of
# Fabien Letouzey's Scan 3.1 — the engine behind lidraughts).
# No C++ compilation needed.
FROM ubuntu:22.04 AS scan-fetcher
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL \
    "https://raw.githubusercontent.com/rhalbersma/scan/master/scan_linux" \
    -o /scan && chmod +x /scan

# Evaluation weights (~8.5 MB) — required for strong play
RUN mkdir -p /scan-data && \
    curl -fsSL \
    "https://raw.githubusercontent.com/rhalbersma/scan/master/data/eval" \
    -o /scan-data/eval

# ── Stage 3: Python runtime ───────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app/backend

# Runtime libs the Scan binary may need
RUN apt-get update && apt-get install -y --no-install-recommends \
        libstdc++6 libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Scan binary + data directory (scan looks for data/ relative to its CWD)
COPY --from=scan-fetcher /scan /usr/local/bin/scan
COPY --from=scan-fetcher /scan-data /app/backend/data

# Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source + built frontend
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist

ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
