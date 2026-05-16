---
phase: 1
plan: 2
slug: compose
subsystem: foundation/infra
status: awaiting-human-verify
tags: [docker, compose, langfuse, qdrant, nats, ollama, timescaledb, makefile, infra]
dependency_graph:
  requires:
    - nx-workspace-polyglot  # da plan 01-01
  provides:
    - docker-compose-dev-stack
    - makefile-entry-points
    - langfuse-v3-self-hosted
    - healthchecked-services
    - named-volumes-persistence
  affects:
    - phase-03-simulator  # usa NATS in sim.yml
    - phase-04-agentic    # usa postgres, qdrant, ollama
    - phase-05-rag        # usa qdrant, ollama
    - phase-10-backend-ui # usa postgres, redis
    - phase-11-obs        # usa langfuse stack
tech_stack:
  added:
    - timescale/timescaledb:2.18.0-pg16
    - qdrant/qdrant:v1.16.1
    - redis:7-alpine
    - nats:2.10-alpine
    - ollama/ollama:0.6.0 (CPU + GPU overlay)
    - postgres:17-alpine (Langfuse dedicated)
    - clickhouse/clickhouse-server:24.3-alpine
    - cgr.dev/chainguard/minio:latest (AGPL-3.0 exception documented)
    - langfuse/langfuse:3
    - langfuse/langfuse-worker:3
  patterns:
    - Docker Compose multi-file stack con overlay LLM CPU/GPU (D-07, D-08)
    - Named volumes per persistenza portabile (D-09)
    - Healthchecks nativi + depends_on condition service_healthy (D-10)
    - Network isolation: sft-core, sft-sim, sft-obs bridge networks
    - Makefile entry points con --wait per exit-healthy (PLAT-09)
key_files:
  created:
    - infra/compose/core.yml
    - infra/compose/obs.yml
    - infra/compose/sim.yml
    - infra/compose/llm-cpu.yml
    - infra/compose/llm-gpu.yml
    - infra/compose/.env.example
    - Makefile
    - docs/contributing/compose-dev-stack.md
  modified: []
decisions:
  - "clickhouse/clickhouse-server:24.3-alpine tag verificato disponibile (2026-05-16) — usato senza fallback su 24.3 senza alpine"
  - "MinIO healthcheck via curl /minio/health/ready (Pitfall 6): chainguard/minio non include mc client"
  - "ClickHouse healthcheck start_period 30s + retries 20 (Pitfall 1): boot lento confermato da RESEARCH"
  - "make up-core aggiunto come target extra per debug rapido senza obs/LLM"
  - "cgr.dev/chainguard/minio:latest mantiene :latest — tag immutabile per SHA in chainguard registry"
metrics:
  duration_minutes: 8
  completed_date: "2026-05-16T19:31:03Z"
  tasks_completed: 3
  tasks_total: 4
  files_created: 8
  commits: 3
---

# Phase 1 Plan 2: compose Summary

**One-liner:** Dev stack Docker Compose a 5 file (core/obs/sim/llm-cpu/llm-gpu) con Langfuse v3 self-hosted, healthchecks nativi, named volumes e Makefile `make up` exit-healthy.

---

## What Was Built

Un dev environment completo orchestrato via Docker Compose e Makefile:

- **`infra/compose/core.yml`** — Postgres+TimescaleDB 2.18.0-pg16, Redis 7-alpine, Qdrant v1.16.1; tutti con healthcheck e named volumes; network `sft-core`
- **`infra/compose/obs.yml`** — Langfuse v3 stack completo: langfuse-pg (postgres:17-alpine), ClickHouse 24.3-alpine (Pitfall 1 fix: start_period 30s, retries 20), MinIO chainguard (Pitfall 6 fix: curl healthcheck), langfuse-redis, langfuse-web, langfuse-worker; boot order corretto tramite depends_on condition service_healthy su 4 upstream; network `sft-obs`
- **`infra/compose/sim.yml`** — NATS 2.10-alpine JetStream con healthcheck `/healthz`; placeholder commentato per sim-textile (Fase 3); network `sft-sim` (anticipa data-diode D-18)
- **`infra/compose/llm-cpu.yml`** — Ollama 0.6.0 CPU-only con healthcheck `/api/tags`; named volume `ollama-models`
- **`infra/compose/llm-gpu.yml`** — Ollama 0.6.0 identico ma con `deploy.resources.reservations.devices` NVIDIA (D-08 overlay mutex)
- **`infra/compose/.env.example`** — tutte le variabili documentate con commenti, valori `_dev_pass` riconoscibili da scanner, header sicurezza con istruzioni `openssl rand -hex 32` per LANGFUSE_ENCRYPTION_KEY (T-1-03)
- **`Makefile`** — target: up, up-gpu, up-core, down, reset, ps, logs, test, lint, format, docs, demo, sbom, helm-test; `make up` usa `--wait` per exit solo quando stack healthy; `make logs SVC=` per log selettivi
- **`docs/contributing/compose-dev-stack.md`** — guida IT con sezione EN summary: pre-requisiti, port matrix 10 servizi, comandi, GPU setup, troubleshooting Pitfall 1+6

---

## Verification Results

```
docker compose -f core.yml -f sim.yml -f obs.yml -f llm-cpu.yml config   → exit 0
make -n up → docker compose -f core.yml -f sim.yml -f obs.yml -f llm-cpu.yml up -d --wait
grep -E 'image:.*:latest' core.yml sim.yml llm-cpu.yml llm-gpu.yml       → 0 match (OK)
grep -E '(password|secret|key).*=.*[a-zA-Z0-9]{8,}' infra/compose/*.yml → 0 match (OK)
.PHONY check: up up-gpu up-core down reset test lint format docs demo sbom helm-test ps logs
dry-run count matching (docker compose|nx|mkdocs|@echo): 9 (>= 9 richiesto)
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing functionality] Aggiunto target `up-core` non presente nel piano**
- **Found during:** Task 3 (Makefile)
- **Issue:** Il piano specificava `up-core` come extra opzionale nel task description; aggiunto esplicitamente
- **Fix:** Target `up-core` aggiunto a Makefile e .PHONY — avvia solo core.yml + sim.yml per debug rapido
- **Files modified:** `Makefile`
- **Commit:** 7eef480

**2. [Rule 2 - Security] LANGFUSE_NEXTAUTH_SECRET default esplicito `<CHANGE_ME_IN_PROD>`**
- **Found during:** Task 1 (creazione .env.example)
- **Issue:** Piano richiedeva marcatura `<CHANGE_ME_IN_PROD>` per variabili critiche
- **Fix:** Aggiunti commenti espliciti per LANGFUSE_NEXTAUTH_SECRET (32+ char), LANGFUSE_SALT, LANGFUSE_ENCRYPTION_KEY con istruzioni di generazione
- **Files modified:** `infra/compose/.env.example`
- **Commit:** c0152a4

### Notes

- `clickhouse/clickhouse-server:24.3-alpine` verificato disponibile in Docker Hub (2026-05-16) — nessun fallback necessario
- `cgr.dev/chainguard/minio:latest` mantiene `:latest` per policy chainguard (tag SHA-immutabile); documentato come eccezione
- Langfuse MINIO_ROOT_PASSWORD rinominata (in env var obs.yml si usa `MINIO_ROOT_PASSWORD` al posto di `MINIO_ROOT_PASSWORD` di research) per consistenza con .env.example

---

## Known Stubs

| Componente | File | Placeholder | Phase Planned |
|-----------|------|-------------|---------------|
| sim-textile | `infra/compose/sim.yml` | Container commentato, solo placeholder comment | Phase 3 |
| helm-test | `Makefile` | `@echo "helm-test definito in plan 06"` | Phase 6 (plan 06) |
| sbom | `Makefile` | Richiede syft+trivy installati (plan 03/license-scanner) | Phase 1 Plan 3 |

Questi sono stub intenzionali — non bloccano l'obiettivo di Piano 02 (`make up` healthy).

---

## Threat Surface Scan

Nessuna nuova superficie oltre quanto documentato in `<threat_model>` del piano:

- Tutti i secret nei file `.yml` usano interpolazione `${VAR}` — nessun valore in plaintext
- `.env` reale protetto da `.gitignore` (creato in plan 01); solo `.env.example` versionato
- MinIO AGPL-3.0 documentato in piano — vedere `LICENSE-EXCEPTIONS.md` (da creare in plan license-scanner)
- Image tag pinati: nessun `:latest` nei file core/sim/llm (T-1-SC); chainguard/minio:latest è eccezione documentata

---

## Task 4: Human Verify (Checkpoint)

**Stato:** In attesa di verifica funzionale su macchina reale con Docker Engine.

**Cosa verificare:**
1. `cp infra/compose/.env.example .env` + generazione LANGFUSE_ENCRYPTION_KEY
2. `make up` → tutti i container healthy entro 180s
3. `curl -sf http://localhost:6333/healthz` (Qdrant), `:8222/healthz` (NATS), `:11434/api/tags` (Ollama), `:3000/api/public/health` (Langfuse)
4. `pg_isready -h localhost -p 5432 -U sft`
5. `make down` + `make reset`

**Resume signal:** "approved" se tutti i 6 step passano; altrimenti descrivere l'errore.

---

## Commit History

| Task | Descrizione | Commit |
|------|-------------|--------|
| 1 | core.yml, sim.yml, LLM overlays, .env.example | c0152a4 |
| 2 | obs.yml — Langfuse v3 stack con boot order corretto | 27d7f19 |
| 3 | Makefile entry points + docs/contributing/compose-dev-stack.md | 7eef480 |
| 4 | SUMMARY.md (questo file) | — |

---

## Self-Check: PASSED

```
[x] infra/compose/core.yml exists — contains timescale/timescaledb:2.18.0-pg16 and qdrant/qdrant:v1.16.1
[x] infra/compose/obs.yml exists — contains langfuse/langfuse:3 and langfuse-worker:3
[x] infra/compose/sim.yml exists — contains nats:2.10-alpine
[x] infra/compose/llm-cpu.yml exists — contains ollama/ollama:0.6.0
[x] infra/compose/llm-gpu.yml exists — contains driver: nvidia
[x] infra/compose/.env.example exists — contains OLLAMA_MODEL_DEFAULT=qwen2.5:7b-instruct-q4_K_M
[x] Makefile exists — contains all 13 required targets + .PHONY
[x] docs/contributing/compose-dev-stack.md exists — contains make up and port matrix
[x] docker compose config exits 0 for full stack
[x] make -n up shows correct docker compose command
[x] No plaintext secrets in compose files (all use ${VAR})
[x] No :latest tags in core/sim/llm files
[x] clickhouse has start_period: 30s + retries: 20 (Pitfall 1)
[x] minio healthcheck uses curl (Pitfall 6)
[x] langfuse-web has 4 depends_on with condition service_healthy
[x] Commits c0152a4, 27d7f19, 7eef480 verified in git log
```
