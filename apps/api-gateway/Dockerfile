# Build context: monorepo root (configurato in docker-compose Plan 04-07)
# Usage: docker build -f apps/api-gateway/Dockerfile -t sft-api-gateway .
#
# Multi-stage build — python:3.12-slim
# Stage 1 (builder): installa uv + sft-agents workspace deps + svc-api-gateway
# Stage 2 (runtime): copia solo site-packages + entrypoint, USER 1000:1000
#
# Mirror service: services/ot-bridge/Dockerfile (Phase 3 pattern)

# ── Stage 1: builder ────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# CA certs per connessioni TLS NATS + PG; build deps for psycopg/asyncpg wheels
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.5.0

WORKDIR /build

# Copia workspace deps (ordine: leaves prima, app-target ultimo)
COPY packages/sft-domain      /build/packages/sft-domain
COPY packages/sft-contracts   /build/packages/sft-contracts
COPY packages/sft-assets      /build/packages/sft-assets
COPY packages/sft-tools       /build/packages/sft-tools
COPY packages/sft-agents      /build/packages/sft-agents
COPY apps/api-gateway         /build/apps/api-gateway

# Patch workspace deps to file paths (no workspace root inside container)
RUN sed -i 's|sft-tools = { workspace = true }|sft-tools = { path = "../../packages/sft-tools" }|; s|sft-assets = { workspace = true }|sft-assets = { path = "../../packages/sft-assets" }|; s|sft-domain = { workspace = true }|sft-domain = { path = "../../packages/sft-domain" }|; s|sft-contracts = { workspace = true }|sft-contracts = { path = "../../packages/sft-contracts" }|' \
    /build/packages/sft-agents/pyproject.toml
RUN sed -i 's|sft-agents = { workspace = true }|sft-agents = { path = "../../packages/sft-agents" }|' \
    /build/apps/api-gateway/pyproject.toml

# Install leaves first, then sft-agents (depends on leaves), then api-gateway.
RUN uv pip install --system --no-cache-dir \
    /build/packages/sft-domain \
    /build/packages/sft-contracts \
    /build/packages/sft-assets \
    /build/packages/sft-tools
RUN uv pip install --system --no-cache-dir /build/packages/sft-agents
RUN uv pip install --system --no-cache-dir /build/apps/api-gateway

# ── Stage 2: runtime ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/api-gateway /usr/local/bin/api-gateway

EXPOSE 8081

ENV API_GATEWAY_PORT=8081 \
    NATS_URL=nats://nats:4222 \
    POOL_MIN_SIZE=5 \
    POOL_MAX_SIZE=20 \
    LOG_LEVEL=INFO

USER 1000:1000

CMD ["api-gateway"]
