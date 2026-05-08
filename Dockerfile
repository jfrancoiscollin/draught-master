# ── Stage 1: Build React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Fetch Scan engine + eval weights ────────────────────────────
# raw.githubusercontent.com serves Git LFS pointer files, not the real blobs.
# git clone + git lfs pull downloads the actual binaries.
FROM ubuntu:22.04 AS scan-fetcher
RUN apt-get update && apt-get install -y --no-install-recommends \
        git git-lfs ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git lfs install --skip-repo \
    && git clone --depth=1 https://github.com/rhalbersma/scan.git /tmp/scan \
    && cd /tmp/scan && git lfs pull

# Verify the files are real (not LFS pointer stubs)
RUN test -f /tmp/scan/scan_linux \
    && test $(stat -c%s /tmp/scan/scan_linux) -gt 100000 \
    && echo "scan_linux OK: $(stat -c%s /tmp/scan/scan_linux) bytes"

RUN test -f /tmp/scan/data/eval \
    && test $(stat -c%s /tmp/scan/data/eval) -gt 1000000 \
    && echo "data/eval OK: $(stat -c%s /tmp/scan/data/eval) bytes"

RUN cp /tmp/scan/scan_linux /scan && chmod +x /scan
RUN mkdir -p /scan-data && cp -r /tmp/scan/data/. /scan-data/ && echo "Scan data files:" && ls -la /scan-data/

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
