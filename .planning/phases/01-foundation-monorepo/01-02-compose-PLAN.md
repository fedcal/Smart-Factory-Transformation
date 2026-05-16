---
phase: 1
plan: 2
slug: compose
type: execute
wave: 2
depends_on: ["01"]
files_modified:
  - infra/compose/core.yml
  - infra/compose/obs.yml
  - infra/compose/sim.yml
  - infra/compose/llm-cpu.yml
  - infra/compose/llm-gpu.yml
  - infra/compose/.env.example
  - Makefile
  - docs/contributing/compose-dev-stack.md
autonomous: true
requirements: [PLAT-07, PLAT-09, OBS-01]
tags: [foundation, infra, docker, compose, langfuse]

must_haves:
  truths:
    - "`make up` esegue `docker compose -f core.yml -f sim.yml -f obs.yml -f llm-cpu.yml up -d --wait` e tutti i container raggiungono stato healthy"
    - "Postgres+TimescaleDB risponde a `pg_isready` su porta 5432"
    - "Qdrant 1.16 risponde con `ok` su /healthz porta 6333"
    - "NATS JetStream risponde con `ok` su /healthz porta 8222"
    - "Langfuse v3 web risponde 200 su /api/public/health porta 3000 dopo boot order rispettato"
    - "Ollama CPU risponde con lista modelli su /api/tags porta 11434"
    - "`make reset` (down -v + up) ricrea lo stack senza dati residui"
    - "`make up-gpu` sostituisce llm-cpu con llm-gpu (Ollama con device NVIDIA dichiarati)"
    - "Nessun secret in plaintext nei file `.yml`: tutte le password leggono `${VAR}` da `.env`"
  artifacts:
    - path: "infra/compose/core.yml"
      provides: "Stack core: postgres+timescaledb, redis, qdrant con healthchecks"
      contains: "timescale/timescaledb"
    - path: "infra/compose/obs.yml"
      provides: "Langfuse v3 stack: langfuse-pg, clickhouse, minio, langfuse-redis, langfuse-web, langfuse-worker"
      contains: "langfuse/langfuse:3"
    - path: "infra/compose/sim.yml"
      provides: "NATS JetStream con healthcheck"
      contains: "nats:2.10"
    - path: "infra/compose/llm-cpu.yml"
      provides: "Ollama CPU-only variant"
    - path: "infra/compose/llm-gpu.yml"
      provides: "Ollama con NVIDIA devices reservation"
    - path: "infra/compose/.env.example"
      provides: "Documentazione tutte le env vars con valori dev default"
      contains: "OLLAMA_MODEL_DEFAULT=qwen2.5:7b-instruct-q4_K_M"
    - path: "Makefile"
      provides: "Entry points: up, up-gpu, down, reset, test, lint, format, docs, demo, sbom, helm-test"
      contains: "BASE_STACK"
  key_links:
    - from: "infra/compose/obs.yml langfuse-web"
      to: "clickhouse, langfuse-pg, minio, langfuse-redis"
      via: "depends_on condition service_healthy"
      pattern: "service_healthy"
    - from: "Makefile target up"
      to: "all four compose files"
      via: "docker compose -f ... up -d --wait"
      pattern: "docker compose.*--wait"
---

<objective>
Creare l'intero dev stack Docker Compose orchestrato da Makefile, separato in 4 file per area (core, obs, sim, LLM-cpu/gpu), con healthchecks nativi, depends_on condition service_healthy, named volumes per persistenza portabile e .env.example documentato. Soddisfa Phase Success Criterion #1: `make up` avvia TUTTI i servizi dev healthy con un solo comando.

Purpose: senza questo stack non esiste un dev environment riproducibile. Le altre fasi (3 simulator, 4 agentic runtime, 5 RAG, 10 backend/UI, 11 obs) consumano questi servizi. Langfuse v3 self-hosted soddisfa OBS-01.

Output: stack healthy in ~60-90 secondi su prima esecuzione, `~30s` su esecuzioni successive (volumi caldi).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-foundation-monorepo/01-CONTEXT.md
@.planning/phases/01-foundation-monorepo/01-RESEARCH.md
@CLAUDE.md
@.planning/phases/01-foundation-monorepo/01-01-SUMMARY.md
</context>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| developer machine -> compose stack | container con porte mappate localhost; credenziali dev devono essere chiaramente identificate come non-prod |
| .env / .env.example -> git | rischio T-1-03: leak password se `.env` reale viene committato |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-1-03 | Information Disclosure | `.env` con credenziali dev | mitigate | `.env` listato in `.gitignore` (creato in plan 01); solo `.env.example` committato; valori in `.env.example` esplicitamente marcati `<CHANGE_ME>` e seguiti da `_dev_pass` suffix; gitleaks hook (plan 04) catturerà secret pattern; valori default sono intenzionalmente weak `<service>_dev_pass` per essere riconoscibili da scanner |
| T-1-SC | Tampering | Container images | mitigate | Tag pinati a versioni esatte (NO `latest`): `timescale/timescaledb:2.18.0-pg16`, `qdrant/qdrant:v1.16.1`, `clickhouse/clickhouse-server:24.3-alpine`, `langfuse/langfuse:3`, `langfuse/langfuse-worker:3`, `nats:2.10-alpine`, `redis:7-alpine`, `postgres:17-alpine` |
</threat_model>

<tasks>

<task id="1-02-01" wave="2" type="auto">
  <name>Task 1: infra/compose/core.yml + sim.yml + LLM overlays + .env.example</name>
  <files>infra/compose/core.yml, infra/compose/sim.yml, infra/compose/llm-cpu.yml, infra/compose/llm-gpu.yml, infra/compose/.env.example</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 3: Docker Compose Multi-Stack con Healthchecks, righe ~418-674; Pitfall 1 ClickHouse boot order; Pitfall 6 MinIO chainguard)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-07 split per area, D-08 GPU/CPU overlay, D-09 named volumes, D-10 healthchecks, D-11 .env.example)
    - CLAUDE.md (Recommended Stack: Qdrant 1.16+, PostgreSQL 16+, TimescaleDB, NATS 2.10+, Ollama)
  </read_first>
  <action>
    Creare `infra/compose/core.yml` con servizi `postgres` (image `timescale/timescaledb:2.18.0-pg16`, healthcheck `pg_isready -U ${POSTGRES_USER:-sft}` interval 5s retries 10, volume `pg-data:/var/lib/postgresql/data`, port `${POSTGRES_PORT:-5432}:5432`, env `POSTGRES_USER/POSTGRES_PASSWORD/POSTGRES_DB`), `redis` (image `redis:7-alpine`, healthcheck `redis-cli ping`, volume `redis-data:/data`, port `${REDIS_PORT:-6379}:6379`), `qdrant` (image `qdrant/qdrant:v1.16.1`, healthcheck `wget -qO- http://localhost:6333/healthz | grep -q ok` interval 5s retries 10, volumes `qdrant-data:/qdrant/storage`, ports `${QDRANT_PORT:-6333}:6333` e `6334:6334`). Sezione `volumes:` dichiara `pg-data:`, `redis-data:`, `qdrant-data:` come named (D-09). Aggiungere `networks: { sft-core: { driver: bridge } }` e annotare tutti i servizi `networks: [sft-core]`. NON usare bind mounts.

    Creare `infra/compose/sim.yml` con servizio `nats` (image `nats:2.10-alpine`, command `["-js", "-m", "8222"]`, ports `${NATS_PORT:-4222}:4222` e `${NATS_MONITORING_PORT:-8222}:8222`, volume `nats-data:/data`, healthcheck `wget -qO- http://localhost:8222/healthz | grep -q ok`). Includere commento `# sim-textile placeholder - popolato in Fase 3` ma NON il servizio vero. `networks: [sft-sim]` con bridge dedicato (D-18 anticipa data-diode).

    Creare `infra/compose/llm-cpu.yml` con servizio `ollama` (image `ollama/ollama:0.6.0`, port `${OLLAMA_PORT:-11434}:11434`, volume `ollama-models:/root/.ollama`, env `OLLAMA_NUM_PARALLEL=2`, healthcheck `curl -sf http://localhost:11434/api/tags`).

    Creare `infra/compose/llm-gpu.yml` identico a llm-cpu.yml MA con `deploy: resources: reservations: devices: [{driver: nvidia, count: all, capabilities: [gpu]}]`. Aggiungere commento header `# Use: make up-gpu — richiede NVIDIA Container Toolkit installato`.

    Creare `infra/compose/.env.example` ESATTO come da RESEARCH righe 637-673 ma con valori chiaramente marcati `<CHANGE_ME_IN_PROD>` e con header documentation che dice "Questo file è solo per dev locale; secrets prod gestiti via SealedSecrets (plan 06)". Includere TUTTE le variabili: POSTGRES_USER/PASSWORD/DB/PORT, REDIS_PORT, QDRANT_PORT, LANGFUSE_PG_USER/PASSWORD/DB, LANGFUSE_NEXTAUTH_SECRET (commento esplicito "deve essere 32+ char in prod"), LANGFUSE_SALT, LANGFUSE_ENCRYPTION_KEY (64 hex chars, generabile con `openssl rand -hex 32`), CLICKHOUSE_DB/USER/PASSWORD/PORT, MINIO_ROOT_USER/PASSWORD/PORT, NATS_PORT/MONITORING_PORT, OLLAMA_PORT, OLLAMA_MODEL_DEFAULT=qwen2.5:7b-instruct-q4_K_M.

    NON committare `.env` (deve essere in `.gitignore` da plan 01).
  </action>
  <acceptance_criteria>
    - `infra/compose/core.yml` contiene la riga `timescale/timescaledb:2.18.0-pg16` e la riga `qdrant/qdrant:v1.16.1`
    - `infra/compose/core.yml` contiene `pg_isready` come comando healthcheck
    - `infra/compose/sim.yml` contiene `nats:2.10-alpine` e `wget -qO- http://localhost:8222/healthz`
    - `infra/compose/llm-cpu.yml` contiene `ollama/ollama` e healthcheck su `/api/tags`
    - `infra/compose/llm-gpu.yml` contiene `driver: nvidia` e `capabilities: [gpu]`
    - `infra/compose/.env.example` contiene `OLLAMA_MODEL_DEFAULT=qwen2.5:7b-instruct-q4_K_M`
    - `grep -E '^\s*image:.*latest' infra/compose/*.yml` ritorna ZERO match (tutti i tag sono pinati)
    - `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml -f infra/compose/llm-cpu.yml config` exits 0 (parsing valido)
  </acceptance_criteria>
</task>

<task id="1-02-02" wave="2" type="auto">
  <name>Task 2: infra/compose/obs.yml — Langfuse v3 full stack con boot order corretto</name>
  <files>infra/compose/obs.yml</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Pattern 3 obs.yml righe ~469-569; Pitfall 1 ClickHouse boot order; Pitfall 6 MinIO chainguard; Open Question 1 ClickHouse tag)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (D-07 obs.yml separato, OBS-01 Langfuse self-hosted v3)
  </read_first>
  <action>
    Creare `infra/compose/obs.yml` con 6 servizi nell'ordine boot corretto (Pitfall 1):
    1. `langfuse-pg` (image `postgres:17-alpine`, env LANGFUSE_PG_USER/PASSWORD/DB, healthcheck `pg_isready -U ${LANGFUSE_PG_USER:-langfuse}` interval 3s retries 10, volume `langfuse-pg-data:/var/lib/postgresql/data`)
    2. `clickhouse` (image `clickhouse/clickhouse-server:24.3-alpine`, env CLICKHOUSE_DB/USER/PASSWORD, healthcheck `wget --no-verbose --tries=1 --spider http://localhost:8123/ping` interval 5s retries 20 start_period 30s — Pitfall 1 fix, port `${CLICKHOUSE_PORT:-8123}:8123`, volumes `langfuse-clickhouse-data:/var/lib/clickhouse` e `langfuse-clickhouse-logs:/var/log/clickhouse-server`). NOTA: Open Question 1 — se il tag `24.3-alpine` non esiste, fallback su `clickhouse/clickhouse-server:24.3` (no alpine) e documentare in SUMMARY.
    3. `minio` (image `cgr.dev/chainguard/minio:latest`, env MINIO_ROOT_USER/PASSWORD, port `${MINIO_PORT:-9090}:9000`, volume `langfuse-minio-data:/data`, healthcheck `curl -sf http://localhost:9000/minio/health/ready` interval 5s retries 10 — Pitfall 6 fix usando curl invece di `mc ready local`).
    4. `langfuse-redis` (image `redis:7-alpine`, volume `langfuse-redis-data:/data`, healthcheck `redis-cli ping`).
    5. `langfuse-web` (image `langfuse/langfuse:3`, env: DATABASE_URL con riferimento `langfuse-pg`, NEXTAUTH_SECRET/SALT/ENCRYPTION_KEY da `.env`, CLICKHOUSE_URL=http://clickhouse:8123, CLICKHOUSE_USER/PASSWORD, REDIS_HOST=langfuse-redis, LANGFUSE_S3_MEDIA_UPLOAD_BUCKET=langfuse, LANGFUSE_S3_EVENT_UPLOAD_BUCKET=langfuse, LANGFUSE_S3_MEDIA_UPLOAD_ENDPOINT=http://minio:9000, LANGFUSE_S3_MEDIA_UPLOAD_ACCESS_KEY_ID=${MINIO_ROOT_USER}, LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}, LANGFUSE_S3_MEDIA_UPLOAD_FORCE_PATH_STYLE=true), port `${LANGFUSE_PORT:-3000}:3000`, depends_on con condition service_healthy su langfuse-pg/clickhouse/minio/langfuse-redis, healthcheck `wget -qO- http://localhost:3000/api/public/health | grep -q "OK\\|ok\\|status"` interval 10s retries 12 start_period 60s).
    6. `langfuse-worker` (image `langfuse/langfuse-worker:3`, stesse env minus NEXTAUTH_SECRET e port, stesse depends_on).

    Sezione volumes dichiara: `langfuse-pg-data`, `langfuse-clickhouse-data`, `langfuse-clickhouse-logs`, `langfuse-minio-data`, `langfuse-redis-data` (D-09).
    Sezione networks: `sft-obs: { driver: bridge }`. Tutti i servizi sopra `networks: [sft-obs]`.

    Validare YAML parsing con `docker compose -f infra/compose/core.yml -f infra/compose/obs.yml config > /dev/null`.
  </action>
  <acceptance_criteria>
    - `infra/compose/obs.yml` contiene `langfuse/langfuse:3` e `langfuse/langfuse-worker:3`
    - `infra/compose/obs.yml` contiene `clickhouse/clickhouse-server:24.3` (con o senza `-alpine`)
    - `infra/compose/obs.yml` contiene `cgr.dev/chainguard/minio`
    - Healthcheck ClickHouse contiene `start_period: 30s` e `retries: 20` (Pitfall 1)
    - Healthcheck MinIO usa `curl` (NOT `mc ready local`) (Pitfall 6)
    - `langfuse-web` ha `depends_on` con `condition: service_healthy` su 4 servizi (langfuse-pg, clickhouse, minio, langfuse-redis)
    - `docker compose -f infra/compose/core.yml -f infra/compose/obs.yml -f infra/compose/sim.yml -f infra/compose/llm-cpu.yml config` exits 0
    - `grep -E "image:.*:latest" infra/compose/obs.yml` ritorna SOLO la riga MinIO chainguard (eccezione documentata)
  </acceptance_criteria>
</task>

<task id="1-02-03" wave="2" type="auto">
  <name>Task 3: Makefile entry points + docs/contributing/compose-dev-stack.md</name>
  <files>Makefile, docs/contributing/compose-dev-stack.md</files>
  <read_first>
    - .planning/phases/01-foundation-monorepo/01-RESEARCH.md (Code Examples sezione "Makefile completo per Fase 1" righe ~1493-1547; Pattern 3 Makefile righe ~616-635)
    - .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Claude's Discretion: Makefile entrypoints; D-09 reset semantics)
  </read_first>
  <action>
    Creare `Makefile` esatto come da RESEARCH Code Examples (righe 1495-1547) con le seguenti correzioni:
    - Aggiungere target `up-core` (solo core+sim, senza obs/llm) per debug rapido
    - Aggiungere target `ps` che lancia `docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) ps`
    - Aggiungere target `logs` con argomento opzionale `SVC=` (`make logs SVC=langfuse-web`)
    - Target `helm-test` e `sbom` sono placeholder che falliscono con messaggio `"@echo 'helm-test definito in plan 06'"` finché plans 03/06 non li implementano (fail-fast esplicito, niente exit 1 silenzioso)
    - `.PHONY:` includere tutti i target
    - Aggiungere `MAKEFLAGS += --no-print-directory` in cima per output pulito
    - Variabili COMPOSE_CORE/COMPOSE_OBS/COMPOSE_SIM/COMPOSE_LLM_CPU/COMPOSE_LLM_GPU come da RESEARCH
    - BASE_STACK := -f $(COMPOSE_CORE) -f $(COMPOSE_SIM) -f $(COMPOSE_OBS)
    - Target `up`: `docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) up -d --wait`
    - Target `up-gpu`: stesso con `$(COMPOSE_LLM_GPU)`
    - Target `down`: stesso pattern con `down`
    - Target `reset`: `down -v && $(MAKE) up`
    - Target `test`: `npx nx run-many --target=test --all --parallel=4` (placeholder se nessun test ancora; non fallire se nessuno)
    - Target `lint`: `npx nx run-many --target=lint --all --parallel=4 && pre-commit run --all-files`
    - Target `format`: `npx nx format:write && pre-commit run ruff-format --all-files || true && pre-commit run prettier --all-files || true`
    - Target `docs`: `cd docs && mkdocs build`
    - Target `demo`: `@echo "Demo non implementata in Fase 1 (Fase 5+)"`

    Creare `docs/contributing/compose-dev-stack.md` (file IT, con sezione "EN summary" in fondo) che documenta:
    - Pre-requisiti (`cp infra/compose/.env.example .env`, generazione `LANGFUSE_ENCRYPTION_KEY` con `openssl rand -hex 32`)
    - Comandi base: `make up`, `make up-gpu`, `make down`, `make reset`, `make ps`, `make logs SVC=<name>`
    - Port matrix tabellare (PG 5432, Redis 6379, Qdrant 6333+6334, Langfuse Web 3000, ClickHouse 8123, MinIO 9090, NATS 4222+8222, Ollama 11434)
    - Sezione "Troubleshooting" con voci per Pitfall 1 (ClickHouse boot timeout), Pitfall 6 (MinIO healthcheck), porte già occupate (`lsof -i :3000`), `docker compose down -v` per reset completo.
    - Sezione "Quando usare make up-gpu": richiede NVIDIA Container Toolkit; verificare con `nvidia-smi` su host.
  </action>
  <acceptance_criteria>
    - `Makefile` esiste e contiene target `up`, `up-gpu`, `down`, `reset`, `test`, `lint`, `format`, `docs`, `demo`, `sbom`, `helm-test`, `ps`, `logs`
    - `make -n up` (dry-run) mostra `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml -f infra/compose/obs.yml -f infra/compose/llm-cpu.yml up -d --wait`
    - `make --dry-run up up-gpu down reset test lint format docs demo sbom helm-test 2>&1 | grep -c "docker compose\|nx\|mkdocs\|@echo"` ritorna >= 9
    - `docs/contributing/compose-dev-stack.md` esiste e contiene la stringa "make up"
    - `docs/contributing/compose-dev-stack.md` contiene una tabella port matrix con `3000` (Langfuse) e `5432` (Postgres)
    - `grep -E "^\.PHONY:" Makefile` exits 0
  </acceptance_criteria>
</task>

<task id="1-02-04" wave="2" type="checkpoint:human-verify" gate="blocking">
  <name>Task 4: Verifica funzionale `make up` su macchina reale</name>
  <what-built>Stack dev completo (Postgres+TimescaleDB, Redis, Qdrant, NATS, Langfuse v3 full stack, Ollama CPU) orchestrato via Docker Compose con healthchecks. Comandi `make up`, `make down`, `make reset` operativi.</what-built>
  <how-to-verify>
    1. Su una macchina con Docker engine 29+ installato:
       ```bash
       cp infra/compose/.env.example .env
       # Generare encryption key:
       export LANGFUSE_ENCRYPTION_KEY=$(openssl rand -hex 32)
       sed -i "s|LANGFUSE_ENCRYPTION_KEY=.*|LANGFUSE_ENCRYPTION_KEY=$LANGFUSE_ENCRYPTION_KEY|" .env
       make up
       ```
    2. Attendere completamento (atteso: 60-180s su prima esecuzione, pull immagini incluso).
    3. Verificare: `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml -f infra/compose/obs.yml -f infra/compose/llm-cpu.yml ps --format json | jq -r '.[] | select(.Health != "healthy" and .Health != "") | .Name'` deve ritornare EMPTY string.
    4. Test funzionali singoli:
       - `curl -sf http://localhost:6333/healthz` ritorna `healthz check passed`
       - `curl -sf http://localhost:8222/healthz` ritorna `{"status":"ok"}`
       - `curl -sf http://localhost:11434/api/tags` ritorna `{"models":[]}` o lista
       - `curl -sf http://localhost:3000/api/public/health` ritorna 200
       - `pg_isready -h localhost -p 5432 -U sft` ritorna `accepting connections`
    5. `make down` ferma lo stack senza errori; `docker ps | grep -E "(postgres|qdrant|langfuse|nats|ollama|clickhouse|minio)" | wc -l` ritorna 0.
    6. `make reset` cancella i volumi e ricrea lo stack pulito.
  </how-to-verify>
  <resume-signal>Type "approved" se tutti i 6 step passano; altrimenti descrivere quale step fallisce e con quale errore.</resume-signal>
</task>

</tasks>

<verification>
1. `docker compose -f infra/compose/core.yml -f infra/compose/sim.yml -f infra/compose/obs.yml -f infra/compose/llm-cpu.yml config` exits 0
2. `make --dry-run up` mostra il comando docker compose composto correttamente
3. `make up` (run manuale) -> tutti i container healthy in <= 3 minuti, exit 0
4. `docker compose ps --format json | jq '[.[] | select(.Health == "healthy")] | length' ` ritorna >= 9 servizi healthy
5. `make down && make reset` exit 0 senza errori
6. `grep -E "(password|secret|key|salt).*=.*[a-zA-Z0-9]{8,}" infra/compose/*.yml` ritorna ZERO match (tutti i secret sono `${VAR}` interpolation)
</verification>

<success_criteria>
- `make up` avvia stack healthy senza intervento manuale (Phase Success Criterion #1)
- Langfuse v3 raggiungibile su :3000 e ClickHouse:8123 con boot order rispettato (OBS-01)
- 5 file compose isolati per area (core/obs/sim/llm-cpu/llm-gpu) — D-07
- GPU overlay mutex con CPU — D-08
- Named volumes per persistenza — D-09
- Healthchecks su ogni servizio — D-10
- `.env.example` documenta tutte le env vars — D-11
- Makefile copre tutti i target richiesti — PLAT-09
</success_criteria>

<output>
Create `.planning/phases/01-foundation-monorepo/01-02-SUMMARY.md` quando done.
</output>
