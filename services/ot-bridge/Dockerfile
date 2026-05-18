# Build context: monorepo root (configurato in docker-compose Plan 03-06)
# Usage: docker build -f services/ot-bridge/Dockerfile -t sft-ot-bridge .
#
# Multi-stage build — python:3.12-slim
# Stage 1 (builder): installa uv + deps + sft-assets + svc-ot-bridge
# Stage 2 (runtime): copia solo site-packages + entrypoint, USER 1000:1000

# ── Stage 1: builder ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# Installa CA certs per connessioni TLS OPC-UA + NATS
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Installa uv (versione pin per build riproducibile)
RUN pip install --no-cache-dir uv==0.5.0

WORKDIR /build

# Copia workspace deps — sft-assets prima (layer cache ottimizzato)
COPY packages/sft-assets /build/packages/sft-assets
COPY services/ot-bridge /build/services/ot-bridge

# Installa deps nel sistema (no venv — container isolato)
WORKDIR /build/services/ot-bridge
RUN uv pip install --system --no-cache-dir .

# ── Stage 2: runtime ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

# Installa CA certs (necessari per connessioni TLS runtime)
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copia site-packages dal builder (senza uv né build tools)
COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages

# Copia entrypoint script
COPY --from=builder /usr/local/bin/ot-bridge /usr/local/bin/ot-bridge

# Prometheus metrics port
EXPOSE 8080

# Env defaults (override via docker-compose env o Kubernetes ConfigMap)
ENV OPCUA_URL=opc.tcp://sim-textile:4840 \
    NATS_URL=nats://nats:4222 \
    METRICS_PORT=8080 \
    LOG_LEVEL=INFO \
    WORKER_COUNT=4

# Non-root user (security: no privilege escalation)
USER 1000:1000

CMD ["ot-bridge"]
