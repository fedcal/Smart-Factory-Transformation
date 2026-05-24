# LGTM Stack — Observability for Smart Factory Transformation

**Status: OPTIONAL** — Required only for local dev observability. Not required for CI or production.

**Requirement:** OBS-03 — Stack LGTM (Loki + Grafana + Tempo + Mimir/Prometheus) documentato come opzionale.

---

## Overview

The Smart Factory Transformation observability stack is based on the **LGTM** pattern:

| Component | Role | Image | Port |
|-----------|------|-------|------|
| **L**oki | Log aggregation (optional, not yet wired) | `grafana/loki` | 3100 |
| **G**rafana | Dashboard & visualization | `grafana/grafana:11.3.1` | **3001** (host) |
| **T**empo | Distributed trace backend (OTLP receiver) | `grafana/tempo:2.6.1` | 4317 (gRPC), 3200 (HTTP) |
| **M**imir / Prometheus | Metrics storage & query | `prom/prometheus:v2.53.3` | 9090 |

> **Why port 3001 for Grafana?** Langfuse self-hosted already occupies port 3000. Grafana is mapped to host port 3001 to avoid conflict (see `GRAFANA_PORT` in `.env.example`).

---

## Starting the Stack

```bash
# Start the full observability stack (Langfuse + Prometheus + Tempo + Grafana)
docker compose -f infra/compose/obs.yml up -d

# Start only Prometheus + Tempo + Grafana (without Langfuse)
docker compose -f infra/compose/obs.yml up -d prometheus tempo grafana

# Check status
docker compose -f infra/compose/obs.yml ps
```

### Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3001 | admin / admin (dev) or anonymous Viewer |
| Prometheus | http://localhost:9090 | none (dev) |
| Tempo HTTP | http://localhost:3200 | none (dev) |
| Langfuse | http://localhost:3000 | see Langfuse project settings |

---

## Grafana Provisioning (Automatic)

Grafana auto-loads **datasources** and **dashboards** at startup via provisioning volumes:

### Datasources (auto-provisioned)

File: `infra/grafana/provisioning/datasources/datasources.yaml`

| Name | Type | UID | URL | Default |
|------|------|-----|-----|---------|
| Prometheus | `prometheus` | `prometheus` | `http://prometheus:9090` | **yes** |
| Tempo | `tempo` | `tempo` | `http://tempo:3200` | no |

The Prometheus datasource is configured with exemplar links to Tempo for drill-down from metrics to traces.

### Dashboards (auto-provisioned)

File: `infra/grafana/provisioning/dashboards/dashboards.yaml`

Provider type `file`, path `/var/lib/grafana/dashboards` (mapped from `./infra/grafana/dashboards`). Update interval: 30 seconds.

| Dashboard | File | Covers |
|-----------|------|--------|
| Agent KPIs | `infra/grafana/dashboards/agent-kpis.json` | Latency p50/p95/p99 + token proxy (OBS-04/07) |
| Factory KPIs | `infra/grafana/dashboards/factory-kpis.json` | OEE / MTTR / MTBF / Scrap (OBS-04) |
| Cost Dashboard | `infra/grafana/dashboards/cost-dashboard.json` | Simulated cost + token consumption + latency (OBS-07) |

To add a new dashboard: place a valid Grafana JSON (schemaVersion >= 39) in `infra/grafana/dashboards/`. Grafana picks it up within 30 seconds without restart.

---

## Trace Flow: Agents → Tempo → Grafana

```
Angular UI
  │  X-Trace-ID (W3C traceparent header)
  ▼
FastAPI API Gateway  ──[OTLPExporter gRPC]──► Tempo:4317
  │  W3C traceparent injected in NATS Msg.Headers
  │  (via NatsHeaderCarrier in sft_agents.otel)
  ▼
NATS JetStream
  │  NatsHeaderCarrier.extract() on subscribe
  ▼
LangGraph Agent (sft_agents)
  │  CallbackHandler → Langfuse (HTTP SDK)
  │  OTLPExporter → Tempo (gRPC, OTEL_EXPORTER_OTLP_ENDPOINT)
  ▼
Tempo (trace backend)
  │
  ▼
Grafana (Explore → Tempo datasource → search by service / trace ID)
```

**Key env vars for OTEL (agents and gateway):**

```bash
OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317   # gRPC, inside compose network
OTEL_SERVICE_NAME=sft-api-gateway               # or sft-{agent-name}
```

These are configured in `infra/compose/.env.example` (Phase 11-05).

---

## Prometheus Scrape Targets

File: `infra/grafana/prometheus.yml`

| Job | Target | Metrics Source |
|-----|--------|----------------|
| `prometheus` | `localhost:9090` | Self-monitoring |
| `api-gateway` | `api-gateway:8000/metrics` | FastAPI + prometheus-client |
| `ot-bridge` | `ot-bridge:8001/metrics` | `svc_ot_bridge/metrics.py` (ingest latency, events, NATS acks, pool) |

**OT Bridge metrics exposed (from `svc_ot_bridge/metrics.py`):**

| Metric | Type | Description |
|--------|------|-------------|
| `ingest_latency_seconds` | Histogram | Event→DB ingest latency (D-48 target: p99 < 200ms) |
| `events_published_total` | Counter | NATS events per subject |
| `nats_pending_acks` | Gauge | JetStream pending acks (publisher lag) |
| `asyncpg_pool_size_used` | Gauge | asyncpg connection pool usage |

**Agent budget metrics** (`BudgetSnapshot` from `sft_agents/models/budget.py`) are emitted via Pushgateway (to be wired in a future plan). The cost dashboard panels include fallback PromQL for when Pushgateway metrics are absent.

---

## Tempo Configuration

File: `infra/grafana/tempo.yaml`

Tempo is configured to receive OTLP spans via gRPC (port 4317) and expose a query HTTP API (port 3200). The Grafana Tempo datasource queries the HTTP API for trace search and waterfall view.

---

## Adding Loki (Log Aggregation — Optional Extension)

Loki is not currently included in `obs.yml`. To add it:

1. Add Loki service to `infra/compose/obs.yml`:
   ```yaml
   loki:
     image: grafana/loki:3.0.0
     ports:
       - "3100:3100"
     volumes:
       - loki-data:/loki
     networks:
       - sft-obs
   ```

2. Add a `loki` datasource to `infra/grafana/provisioning/datasources/datasources.yaml`:
   ```yaml
   - name: Loki
     type: loki
     uid: loki
     access: proxy
     url: http://loki:3100
   ```

3. Configure Tempo `tracesToLogsV2` with `datasourceUid: loki` in `datasources.yaml`.

4. Ship logs via Promtail or the OpenTelemetry Collector log pipeline.

---

## Security Notes

- **GF_AUTH_ANONYMOUS_ENABLED=true** is set for dev only. Anonymous users have Viewer role (read-only).
  For production: disable anonymous access and configure a real identity provider (Keycloak, LDAP).
- Prometheus and Tempo are accessible on host ports without authentication in dev.
  In production: use Grafana Cloud or place behind a reverse proxy with mTLS.
- See threat model: `docs/security/STRIDE-threat-model.md` (T-11-04-01 — anonymous viewer accepted risk).

---

## Stopping the Stack

```bash
# Stop all services (preserves volumes)
docker compose -f infra/compose/obs.yml down

# Stop and remove volumes (destructive — loses all metrics/traces)
docker compose -f infra/compose/obs.yml down -v
```

---

*This document covers OBS-03. Stack is optional for development and not required for CI runs.*
*For production observability, use Grafana Cloud or a managed LGTM stack.*
