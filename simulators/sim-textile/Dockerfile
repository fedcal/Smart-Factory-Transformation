# Build context: monorepo root (set in docker-compose `context: ../../`).
# Plan 03-06 configura compose con context: . (monorepo root) e dockerfile: simulators/sim-textile/Dockerfile.
#
# Multi-stage build: builder installa dipendenze, runtime copia artifacts.
# python:3.12-slim — allineato a requires-python = ">=3.12,<3.13" (pyproject.toml).
# Sicurezza: USER 1000:1000 (non-root), nessuna credenziale hardcoded.

# --- Stage builder ---
FROM python:3.12-slim AS builder

# Installa ca-certificates per uv HTTPS
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Installa uv per dependency management
RUN pip install --no-cache-dir uv==0.5.0

WORKDIR /build

# Copia workspace sft-assets (workspace dep) + sim-textile
COPY packages/sft-assets /build/packages/sft-assets
COPY simulators/sim-textile /build/simulators/sim-textile

# Installa sft-assets prima (workspace dep). Senza il root pyproject.toml workspace
# nel container uv non risolve `{ workspace = true }`, quindi patch in-place del
# pyproject.toml per usare path source (preserva workspace mode per dev locale).
RUN sed -i 's|sft-assets = { workspace = true }|sft-assets = { path = "../../packages/sft-assets" }|' \
    /build/simulators/sim-textile/pyproject.toml
RUN uv pip install --system --no-cache-dir /build/packages/sft-assets
WORKDIR /build/simulators/sim-textile
RUN uv pip install --system --no-cache-dir .

# --- Stage runtime ---
FROM python:3.12-slim

WORKDIR /app

# Copia site-packages dal builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# Copia entrypoint CLI
COPY --from=builder /usr/local/bin/sim-textile /usr/local/bin/sim-textile

# Copia profiles per il runtime (required da profile_loader.py)
COPY simulators/sim-textile/profiles /app/profiles

# Espone porta OPC-UA (4840) e Prometheus metrics (8080)
EXPOSE 4840 8080

# Env configurabili (D-50 — sovrascrivibili da docker-compose o k8s)
ENV SIM_PROFILES=loom,spinning,warping,dyeing,finishing \
    SIM_TIME_SCALE=1.0 \
    OPCUA_BIND=0.0.0.0:4840 \
    METRICS_PORT=8080

# Non-root user (sicurezza baseline)
USER 1000:1000

CMD ["sim-textile"]
