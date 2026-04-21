# ── Stage 1: Build React frontend ────────────────────────────────────────
FROM node:20-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Compile Scan draughts engine ────────────────────────────────
FROM ubuntu:22.04 AS scan-builder
RUN apt-get update && apt-get install -y --no-install-recommends \
        git g++ cmake make ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth=1 https://github.com/rhalbersma/scan.git /scan
WORKDIR /scan
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-O3 -DNDEBUG" \
    && cmake --build build --parallel $(nproc)
# Find the compiled binary wherever CMake placed it
RUN find /scan/build -maxdepth 5 -name "scan" -type f -perm /111 \
        | head -1 \
        | xargs -I{} cp {} /usr/local/bin/scan \
    && chmod +x /usr/local/bin/scan \
    && echo "Scan built: $(/usr/local/bin/scan --version 2>&1 || echo 'ok')"

# ── Stage 3: Python backend ───────────────────────────────────────────────
FROM python:3.12-slim
WORKDIR /app/backend

# Copy Scan binary (falls back gracefully if missing — minimax takes over)
COPY --from=scan-builder /usr/local/bin/scan /usr/local/bin/scan

# Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend source + built frontend
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist

ENV PORT=8080
EXPOSE 8080

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}
