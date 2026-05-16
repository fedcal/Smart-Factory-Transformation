# Dev Stack Docker Compose

Guida al dev environment locale basato su Docker Compose.
Lo stack copre tutti i servizi necessari per sviluppare SFT senza infrastruttura esterna.

---

## Pre-requisiti

| Tool | Versione minima | Installazione |
|------|----------------|--------------|
| Docker Engine | 29+ | [docs.docker.com/engine/install](https://docs.docker.com/engine/install/) |
| Docker Compose | v2.20+ | incluso in Docker Desktop / Engine 23+ |
| `make` | 3.81+ | `sudo apt install make` / Homebrew `make` |
| `curl` | qualsiasi | pre-installato su macOS/Linux |
| `openssl` | qualsiasi | pre-installato su macOS/Linux |

---

## Primo avvio

```bash
# 1. Copiare il file di esempio
cp infra/compose/.env.example .env

# 2. Generare l'encryption key obbligatoria per Langfuse
export LANGFUSE_ENCRYPTION_KEY=$(openssl rand -hex 32)
sed -i "s|LANGFUSE_ENCRYPTION_KEY=.*|LANGFUSE_ENCRYPTION_KEY=$LANGFUSE_ENCRYPTION_KEY|" .env

# 3. (Opzionale) Personalizzare le password in .env — le default vanno bene per dev locale

# 4. Avviare lo stack
make up
```

Prima esecuzione: ~60-180 secondi (pull immagini ~2-3 GB).
Esecuzioni successive con volumi caldi: ~30 secondi.

---

## Comandi principali

| Comando | Descrizione |
|---------|-------------|
| `make up` | Avvia tutto lo stack (CPU mode, default) |
| `make up-gpu` | Avvia lo stack con Ollama su GPU NVIDIA |
| `make up-core` | Avvia solo core + NATS (senza obs/LLM, per debug rapido) |
| `make down` | Ferma lo stack (mantiene i volumi dati) |
| `make reset` | Cancella volumi e ricrea stack pulito |
| `make ps` | Stato containers |
| `make logs` | Log di tutti i servizi (Ctrl+C per uscire) |
| `make logs SVC=langfuse-web` | Log di un servizio specifico |

---

## Port matrix

| Servizio | Porta host | Protocollo | Note |
|----------|-----------|------------|------|
| Postgres + TimescaleDB | **5432** | TCP | `POSTGRES_USER=sft`, `POSTGRES_DB=sft` |
| Redis (core) | **6379** | TCP | Cache applicativa |
| Qdrant (vector store) | **6333** | HTTP | REST API; **6334** gRPC |
| Qdrant gRPC | 6334 | gRPC | — |
| Langfuse Web | **3000** | HTTP | Dashboard + API pubblica |
| ClickHouse | **8123** | HTTP | HTTP interface per query; usato da Langfuse |
| MinIO | **9090** | HTTP | Object storage (API S3-compatible su porta 9000 interna) |
| NATS | **4222** | TCP | Client protocol JetStream |
| NATS Monitoring | **8222** | HTTP | Dashboard + `/healthz` |
| Ollama | **11434** | HTTP | REST API modelli LLM |

---

## Quando usare `make up-gpu`

Usare `make up-gpu` quando si vuole che Ollama sfrutti la GPU NVIDIA per inferenza più veloce.

**Requisiti:**
1. GPU NVIDIA con driver installati sull'host
2. NVIDIA Container Toolkit installato:
   ```bash
   # Verifica toolkit
   nvidia-smi
   docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi
   ```
3. Docker configurato per usare nvidia runtime:
   ```bash
   # Verifica in daemon.json
   docker info | grep -i runtime
   ```

`make up` di default usa `llm-cpu.yml` (CPU-only) che funziona su qualsiasi macchina.
`make up-gpu` usa `llm-gpu.yml` che ha `deploy.resources.reservations.devices` con NVIDIA.
I due overlay sono **mutualmente esclusivi** — non avviare entrambi nello stesso momento.

---

## Troubleshooting

### ClickHouse impiega troppo tempo ad avviarsi (Pitfall 1)

ClickHouse può richiedere 30-60 secondi per inizializzare lo storage engine.
Il healthcheck è configurato con `start_period: 30s` e `retries: 20` per gestirlo.

Se `make up` fallisce su ClickHouse con timeout:
```bash
# Attendere ulteriormente e verificare lo stato
docker compose -f infra/compose/obs.yml logs clickhouse --tail=50
# Ritentare
make up
```

### MinIO healthcheck fallisce (Pitfall 6)

L'immagine `cgr.dev/chainguard/minio` (variante hardened) non include `mc` (MinIO client).
Il healthcheck usa `curl http://localhost:9000/minio/health/ready` — non richiedere `mc`.

Se il healthcheck fallisce:
```bash
docker compose -f infra/compose/obs.yml logs minio --tail=30
# Verificare che la porta 9000 interna sia accessibile
docker exec <minio_container> curl -sf http://localhost:9000/minio/health/ready
```

### Una porta e' gia' occupata

```bash
# Identificare il processo che usa la porta (es. 3000)
lsof -i :3000
# Terminare il processo o modificare la porta in .env
# Esempio: LANGFUSE_PORT=3001
```

### Reset completo (dati corrotti o volume inconsistente)

```bash
# Cancella tutti i volumi e ricrea lo stack da zero
make reset
# Equivalente a: docker compose ... down -v && make up
```

### Stack non si avvia (`make up` esce con errore)

```bash
# Verificare lo stato di ogni servizio
make ps
# Vedere i log di un servizio specifico
make logs SVC=<nome_servizio>
# Esempi:
make logs SVC=clickhouse
make logs SVC=langfuse-web
make logs SVC=minio
```

---

## Variabili d'ambiente configurabili

Tutte le variabili sono in `infra/compose/.env.example`.
Copiare in `.env` e personalizzare:

```bash
cp infra/compose/.env.example .env
# Editare .env con i valori desiderati
```

File `.env` NON e' versionato (protetto da `.gitignore`) — solo `.env.example` e' nel repo.

---

## EN Summary

**Quick start:** `cp infra/compose/.env.example .env && make up`

The dev stack consists of 4 compose files merged at startup:
- `core.yml` — Postgres+TimescaleDB, Redis, Qdrant
- `sim.yml` — NATS JetStream
- `obs.yml` — Langfuse v3 (Postgres, ClickHouse, MinIO, Redis, langfuse-web, langfuse-worker)
- `llm-cpu.yml` — Ollama (CPU) or `llm-gpu.yml` (GPU variant)

All services have Docker healthchecks. `make up` uses `--wait` and exits only when all services are healthy. Named volumes provide data persistence across restarts. `make reset` wipes volumes and recreates the stack cleanly.
