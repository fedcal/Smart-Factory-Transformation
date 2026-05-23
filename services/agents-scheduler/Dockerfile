# Build context: monorepo root (compose builds with `context: ../..`)
# Usage: docker build -f services/agents-scheduler/Dockerfile -t sft-agents-scheduler .
#
# Multi-stage build — python:3.12-slim
# Stage 1 (builder): install uv + svc-agents-scheduler from local source
# Stage 2 (runtime): copy site-packages + entrypoint, USER 1000:1000
# No workspace cross-package deps (scheduler is intentionally self-contained).

# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# CA certs required for httpx TLS towards the api-gateway in prod.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# uv pin for reproducible builds (matches ot-bridge Dockerfile baseline).
RUN pip install --no-cache-dir uv==0.5.0

WORKDIR /build

# Copy source — scheduler depends only on PyPI packages so no other workspace
# members need to land in the image.
COPY services/agents-scheduler /build/services/agents-scheduler

WORKDIR /build/services/agents-scheduler
RUN uv pip install --system --no-cache-dir .

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.12/site-packages \
                    /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin/agents-scheduler /usr/local/bin/agents-scheduler

# Env defaults — override via compose env or Helm values.
ENV API_GATEWAY_URL="http://api-gateway:8081" \
    ANOMALY_WINDOW_MINUTES="15" \
    ANOMALY_CRON="*/5 * * * *" \
    LOG_LEVEL="INFO"

# Non-root user (security: T-1-04 EoP prevention, D-17).
USER 1000:1000

CMD ["python", "-m", "svc_agents_scheduler"]
