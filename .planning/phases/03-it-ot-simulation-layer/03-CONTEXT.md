---
phase: 3
phase_name: IT/OT Simulation Layer
phase_slug: it-ot-simulation-layer
discussed_at: "2026-05-18"
requirements: [IOT-01, IOT-02, IOT-03, IOT-04, IOT-05, IOT-06, IOT-07, IOT-08, IOT-09, IOT-10]
depends_on_phases: [1]
---

# Phase 3 Context — IT/OT Simulation Layer

<domain>
**What this phase delivers:** the live event-stream substrate that all downstream agentic phases (Phase 4 runtime, Phase 6 anomaly detection, Phase 7 predictive maintenance) will subscribe to or query.

Concretely:
- A **Python textile factory simulator** (`simulators/sim-textile/`) that emits realistic adversarial sensor streams for 5 asset families (loom, spinning, warping, dyeing, finishing) over `asyncua` OPC-UA. Configurable fault injection per asset (NaN, drift, jitter, burst noise, alarm storm) via YAML profiles.
- A **data-diode OT Bridge** (`services/ot-bridge/`) that subscribes to OPC-UA and republishes normalized `SensorEvent` to NATS JetStream subjects `sensor.events.<asset_family>.<asset_id>.<tag>`. Demonstrably incapable of receiving write commands from the IT side (Docker network ACL + pytest enforcement test).
- A **TimescaleDB ingest pipeline** with hypertables for time-series sensor events, hitting sustained 5,000 msg/s with p99 latency < 200 ms under a 60-second steady-state load test with realistic asset mix.
- A **dataset replay loader pair** (NASA C-MAPSS turbofan + UCI Manufacturing) exposed as LangChain Tools from a new `packages/sft-tools/` package, ready for Phase 4 agents to consume.
- An **asset registry + tag dictionary** in a new `packages/sft-assets/` package (Pydantic models + YAML) documenting asset_id / asset_family / opcua_namespace / tag definitions / units of measure.

This phase does NOT build agents, retrieval, or LLM wiring. It produces the **live and historical telemetry substrate** that Phase 4 (Core Agentic Runtime) and Phase 6-7 (QualityInspector, AnomalyDetector, PredictiveMaintenance) will react to or query.
</domain>

<canonical_refs>
Files downstream agents (researcher, planner) MUST consult:

- `.planning/ROADMAP.md` — Phase 3 goal, 10 requirements (IOT-01..10), 5 success criteria
- `.planning/REQUIREMENTS.md` lines 57-66 — full text of IOT-01..10
- `.planning/PROJECT.md` — core value, OT/IT separation principle
- `.planning/research/STACK.md` — asyncua 1.0+, NATS JetStream 2.10+, TimescaleDB 2.x (PG extension), asyncpg client. NATS preferred over Redis Streams for OT→IT pipeline. asyncua scelto su node-opcua per Python-native stack.
- `.planning/research/ARCHITECTURE.md` — C4 diagram con OT Bridge data-diode pattern; "No agent holds OPC-UA client session reference"
- `.planning/phases/01-foundation-monorepo/01-CONTEXT.md` — D-02 sft-domain layout; D-09 docker-compose dev stack (NATS+TimescaleDB+Postgres già scaffoldati); D-15 MkDocs i18n
- `.planning/phases/01-foundation-monorepo/01-02-compose-SUMMARY.md` — docker-compose services scaffolded (Phase 1)
- `.planning/phases/01-foundation-monorepo/01-06-helm-SUMMARY.md` — Helm chart skeleton (NetworkPolicy estendibile in Phase 3 prod-extension)
- `.planning/phases/02-domain-modeling-synthetic-corpus/02-CONTEXT.md` — D-21 5 process families (allineamento naming asset_family); D-30 textile-asset glossary category
- `packages/sft-domain/` — già published v0.2.0; sft-assets sarà sibling, NON nested
- `simulators/sim-textile/` — Phase 1 scaffold (empty dependencies); Phase 3 lo riempie
- `services/ot-bridge/` — Phase 1 scaffold (empty dependencies); Phase 3 lo riempie
- `docs/assumptions/register.yaml` — A-001..A-018 (Phase 2 seed) coprono già: sample rate stability, NaN semantics, asset_id non-null, UTC timestamps + skew < 500ms, units of measure as OPC-UA engineering unit, buffer 3x burst tolerance, dataset replay coverage ≥ 90 days, OPC-UA schema forward-compat, time skew tra PLC, alarm storm threshold

No external SPEC.md or ADR exists for Phase 3 — this CONTEXT.md is the source of truth for downstream agents until ROADMAP.md is updated.
</canonical_refs>

<code_context>
**Already exists from Phase 1 — reuse, do NOT duplicate:**

- `simulators/sim-textile/{pyproject.toml,project.json,src/sim_textile/,README.md}` — empty scaffold, ready for Pydantic models + asyncua server + fault injection engine + asyncio main loop
- `services/ot-bridge/{pyproject.toml,project.json,src/svc_ot_bridge/,README.md}` — empty scaffold, ready for asyncua client + NATS publisher + Pydantic event normalization
- `docker-compose.yml` (Phase 1) — già contiene service entries placeholder per `nats`, `timescaledb`, `postgres`. Phase 3 estende con `sim-textile` + `ot-bridge` services + dual-network ACL config
- `helm/sft/templates/` (Phase 1) — Helm chart skeleton; Phase 3 può estendere con NetworkPolicy YAML (deferred, primary focus docker-compose enforcement)
- `.github/workflows/ci.yml` — Phase 2 ha aggiunto step "Validate content"; Phase 3 aggiungerà step "Run IT/OT load test (smoke)" (1k msg/s × 10s, full 5k×60s opzionale via `--full-load-test` PR label)
- `scripts/sync-python-versions.py` (Phase 1) + `scripts/validate-*.py` (Phase 2) — pattern template per qualsiasi nuovo script Phase 3 (argparse + --dry-run + exit codes documentati)
- `packages/sft-domain/src/sft_domain/glossary/` — terms `loom`, `spindle`, `warping`, `dyeing_bath`, `picks_per_cm`, `warp_tension`, ecc. (Phase 2 bootstrap + expansion). Phase 3 può FAR REFERENCE ai termini ma NON modifica sft-domain.

**Naming conventions to honor:**
- Conventional Commits con scope `feat(03-NN-slug):` per atomic commit (matches Phase 1+2 pattern)
- Pydantic v2 frozen models con `extra = "forbid"` (allineato a D-44 Phase 1 + Phase 2 schema enforcement)
- YAML: ALWAYS `yaml.safe_load` (mai `yaml.load`) — pattern Phase 2
- snake_case per Python field names + YAML keys
- asyncio-first: `asyncpg` per Postgres/Timescale, `nats-py` async API, `asyncua` (già async-native)
</code_context>

<decisions>

## D-44 — Fault injection: per-asset YAML profiles + 5 calibrated defaults

**Decision:** sim-textile carica fault injection profiles via YAML files in `simulators/sim-textile/profiles/`:
- `loom.yaml` — focus jitter warp_tension (10Hz × 100 telai), alarm storm broken_pick, drift creel_speed
- `spinning.yaml` — jitter spindle imbalance, alarm broken_end, drift drafting_roller_wear
- `warping.yaml` — drift tension_imbalance, burst creel_feed_jam
- `dyeing.yaml` — drift bath_temperature, NaN pH_sensor_disconnect, alarm recipe_deviation
- `finishing.yaml` — drift humidity_temp, burst fabric_tension

Schema per profile:
```yaml
asset_family: loom
sample_rate_hz: 10
fault_injection:
  nan_probability: 0.001       # 0.1% — disconnessione sensore
  drift:
    enabled: true
    rate_per_hour: 0.005       # 0.5%/h drift incrementale
    affected_tags: [creel_speed]
  jitter:
    enabled: true
    band_pct: 5                # ±5% del valore nominale
    affected_tags: [warp_tension]
  burst_noise:
    enabled: false
  alarm_storm:
    enabled: true
    threshold_events: 50       # se >50 eventi/30s scatena storm
    affected_tags: [broken_pick]
default_baseline:
  # tag baseline values for "normal operations"
  warp_tension: { value: 25, unit: N }
  pick_density: { value: 24, unit: picks_per_cm }
```

Loadable via CLI `uv run sim-textile --profile loom` o env `SIM_PROFILES=loom,dyeing` (multi-asset).

**Why:** Realismo industriale richiesto da Phase 7 (PredictiveMaintenance) training; YAML-driven permette estensione senza code change. La calibrazione iniziale è "range tipici industria" (allineato D-28 Phase 2 SOP boundary).

**Rejected alternatives:**
- Homogeneous baseline: troppo poco realistico per training PredictiveMaintenance.
- Runtime config via OPC-UA write: viola data-diode (un percorso write esiste, anche se "interno").
- Hybrid sim.control.* nodes: aggiunge complessità OPC-UA non-data per Phase 3 PoC.

## D-45 — Asset registry: nuovo package `packages/sft-assets/` (platform metadata)

**Decision:** Nuovo Nx project `packages/sft-assets/` con:
- `src/sft_assets/registry.yaml` — asset registry con shape:
  ```yaml
  - asset_id: LOOM-01
    asset_family: loom
    line_id: weaving-line-1
    opcua_namespace: "urn:mantis:weaving:loom:LOOM-01"
    tags:
      - tag_id: warp_tension
        unit: N
        sample_rate_hz: 10
        semantic_type: tension
      - tag_id: pick_density
        unit: picks_per_cm
        sample_rate_hz: 1
        semantic_type: density
    status: active
  ```
- `src/sft_assets/models.py` — Pydantic `Asset`, `Tag`, frozen + extra=forbid
- `src/sft_assets/loader.py` — `load_assets() -> list[Asset]` + `load_assets_dict() -> dict[str, Asset]` + `load_tag_dict() -> dict[str, Tag]` con lru_cache
- `src/sft_assets/schemas/asset.schema.json` — JSON Schema Draft 2020-12 per CI validation

Phase 3 seeds **~30 asset reali** (mix Mantis-realistic): 12 looms + 8 ring frames + 4 warpers + 4 jet dyeing vasche + 2 stenter. Tag dictionary ~50 tag (≥10 per family).

**Why:** SSOT per platform metadata, riusabile da sim-textile (generate OPC-UA nodes), ot-bridge (resolve asset_id → routing key), Phase 4+ agents (filter eventi per asset). Distinto da sft-domain (textile **concepts** like "warping is a process"), sft-assets contiene **runtime metadata** (LOOM-01 has IP 192.168.x.x).

**Rejected alternatives:**
- In sft-domain submodule: mescola domain knowledge con platform metadata; sft-domain published v0.2.0 = breaking change.
- In sim-textile YAML + Pydantic in sft-domain: anti-pattern services → simulators dependency.
- ot-bridge config + DB registry: over-engineered per Phase 3; DB-backed registry può essere Phase 11 (governance audit).

## D-46 — Replay loaders: LangChain Tool registry

**Decision:** Phase 3 esporta 2 LangChain Tools:
- `replay_cmapss(unit_id: int, time_range: tuple[datetime, datetime] | None = None, sensor_subset: list[str] | None = None) -> pd.DataFrame` — NASA C-MAPSS turbofan, mappa unit_id concettualmente a un nostro LOOM-XX (M:1 mapping registry-driven)
- `replay_uci(dataset: Literal["air_quality", "energy", "production"], asset_id: str, time_range: tuple[datetime, datetime] | None = None) -> pd.DataFrame` — UCI Manufacturing variants

Output schema unificato:
```python
class ReplayRecord(BaseModel):
    asset_id: str
    timestamp: datetime  # UTC
    sensor_id: str
    value: float
    unit: str
    source_dataset: Literal["cmapss", "uci"]
    source_unit: str  # original dataset identifier
```

Tools usano `BaseTool` da `langchain-core` con `args_schema` Pydantic. async-first (`_arun` priorizzato).

**Why:** Phase 4 agents consumeranno via LangChain ToolNode standard (`langgraph.prebuilt.ToolNode`). Schema unificato (asset_id + timestamp + sensor_id + value + unit) permette agli stessi agents di gestire live (NATS) e replay (Tool) con la stessa pipeline.

**Rejected alternatives:**
- CLI scripts + JSON stdout: overhead serialize per ogni agent call.
- MCP wrapper: Phase 3 over-engineering; MCP è Phase 7+ priority (PROJECT.md menziona AAS+MCP industrial future).
- Pubblicazione su NATS replay subjects: confonde live vs replay nelle metriche Langfuse Phase 4.

## D-47 — Tool registry location: nuovo `packages/sft-tools/`

**Decision:** Nuovo Nx project `packages/sft-tools/` dedicato a LangChain Tools cross-cutting:
- Phase 3 ships: `replay_cmapss`, `replay_uci` + `query_timescale(asset_id, time_range, tags)` (Tool che proxy queries hypertable per agent ergonomia)
- Phase 5+ extension: retrieval tools (`retrieve_sop`, `retrieve_glossary`, `retrieve_assumption`)
- Phase 6+ extension: action tools (`raise_alert`, `request_human_approval`)

Layout:
```
packages/sft-tools/
├── pyproject.toml          # depends on langchain-core, sft-assets, sft-domain
├── project.json            # Nx with test target
├── src/sft_tools/
│   ├── __init__.py         # exports REPLAY_TOOLS, TIMESCALE_TOOLS
│   ├── replay/
│   │   ├── cmapss.py
│   │   ├── uci.py
│   │   └── models.py
│   └── timescale/
│       └── query.py
└── tests/
```

**Why:** Centralizza i Tool LangChain in un solo posto, evita scattered tools in sim-textile/ot-bridge/agents. Agent packages Phase 4+ importano `from sft_tools.replay import REPLAY_TOOLS`.

**Rejected alternatives:**
- In sim-textile (`sim_textile.tools`): anti-pattern (simulator as dependency).
- Defer a Phase 4: Phase 4 dovrebbe focalizzarsi sull'orchestrator, non sui tool wrappers.

## D-48 — Load test scenario: steady-state 60s + realistic asset mix

**Decision:** `tests/load/test_ingestion_throughput.py` (custom asyncio harness):
- **Mix asset (totale ~5,000 msg/s):**
  - 60% loom: 100 telai × 10Hz = 1,000 msg/s warp_tension + 100×0.5Hz = 50 msg/s pick_density + altri tag = ~3,000 msg/s
  - 20% spinning: 50 spindles × 5Hz × ~4 tag = 1,000 msg/s
  - 10% dyeing/finishing: 30 vasche+tunnel × ~1Hz × ~6 tag = ~180 msg/s + dyeing storm test = ~500 msg/s
  - 10% warping: 20 orditi × 2Hz × ~5 tag = ~200 msg/s
- **Payload:** 256-512 byte JSON `{"asset_id","tag_id","timestamp_utc","value","unit","quality_code"}`
- **Durata:** 60s steady-state (NO ramp-up — il sistema deve essere stabile dal secondo zero)
- **Misura:** p99 ingest latency via `pg_stat_statements` su `INSERT INTO sensor_events` + custom Python histogram lato publisher (start_ts → ack_ts). Target: p99 < 200ms (IOT-10).
- **Tool:** custom asyncio harness in `tests/load/harness.py` con `asyncio.gather` + `asyncpg.Pool(min_size=10, max_size=20)`. NO Locust/k6 (overhead HTTP layer non-realistic vs NATS native).

**Implementazione:** harness pubblica direttamente su NATS (bypassando sim-textile per isolare il bottleneck I/O Timescale, NON la generazione fault). Smoke test in CI (`tests/load/test_ingestion_smoke.py`) 1k msg/s × 10s; full test gated da PR label `load-test`.

**Why:** Steady-state misura capacity production-realistic. Mix asset documenta IOT-01..03 coverage end-to-end. Custom harness asyncio = stesso stack del prodotto = misura realistica.

**Rejected alternatives:**
- Burst test 10k × 5s: stressante ma non riflette steady-state production.
- Ramp-up 1k→10k: utile capacity planning ma over-spec per IOT-10 (target è 5k, non 10k).
- Locust: aggiunge HTTP overhead che non riflette OPC-UA → NATS native path.

## D-49 — TimescaleDB retention: chunk=1d / compress=7d / drop=90d

**Decision:** Hypertable `sensor_events`:
```sql
CREATE TABLE sensor_events (
  asset_id      TEXT NOT NULL,
  tag_id        TEXT NOT NULL,
  timestamp_utc TIMESTAMPTZ NOT NULL,
  value         DOUBLE PRECISION,
  unit          TEXT,
  quality_code  SMALLINT,
  source        TEXT  -- 'live' | 'replay_cmapss' | 'replay_uci'
);
SELECT create_hypertable('sensor_events', 'timestamp_utc',
                          chunk_time_interval => INTERVAL '1 day');

ALTER TABLE sensor_events SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'asset_id, tag_id',
  timescaledb.compress_orderby = 'timestamp_utc DESC'
);
SELECT add_compression_policy('sensor_events', INTERVAL '7 days');
SELECT add_retention_policy('sensor_events', INTERVAL '90 days');
```

**Tabelle separate per audit:** Phase 11 (governance) gestirà retention diversa (es. 7 anni) su tabelle audit/agent.actions separate. `sensor_events` è platform telemetry, NON audit data.

**Continuous aggregates DEFERRED a Phase 4-5:** quando OEE/MTBF dashboards saranno definiti, aggregates 1min/1hour saranno creati con retention separate. Phase 3 ships solo l'hypertable raw.

**Why:** Default Timescale benchmark, allineato A-007 (dataset ≥90d) ma con compress dopo 7d (hot/warm tier). 30d minimum hot = quasi tutti agenti Phase 4 query (anomaly detection live windowing).

**Rejected alternatives:**
- chunk=1h / drop=30d aggressive: storage minimo ma chunk overhead alto su 30+ asset.
- No retention/compression: data bloat dopo 60 giorni.
- Continuous aggregates day-one: Phase 3 PoC over-engineering; aggregates richiedono query patterns chiari (Phase 4-5).

## D-50 — Simulator orchestration: docker-compose service + YAML profile

**Decision:** `sim-textile` come singolo container long-running:
```yaml
# docker-compose.yml extension
sim-textile:
  build:
    context: simulators/sim-textile
  container_name: sft-sim-textile
  environment:
    - SIM_PROFILES=loom,spinning,warping,dyeing,finishing  # default: all 5
    - SIM_TIME_SCALE=1.0  # 1.0 = realtime; >1.0 = accelerated
    - OPCUA_BIND=0.0.0.0:4840
    - METRICS_PORT=8080
  networks:
    - ot-network                      # SOLO ot-network (no it-network access)
  ports:
    - "4840:4840"                     # OPC-UA discoverable from ot-bridge only
    - "8080:8080"                     # Prometheus metrics (development scrape ok)
```

Process design:
- Singolo processo asyncio in `sim_textile.main:run()`
- Per ogni profile abilitato: spawna task `asyncio.create_task(asset_emitter(profile))`
- Centralized OPC-UA server `asyncua.Server` con namespace `urn:mantis:<asset_family>:<asset_id>`
- Endpoint Prometheus `/metrics` su porta 8080: `sim_events_emitted_total{asset_family,asset_id,tag_id}`, `sim_fault_injected_total{type,asset_family}`, `sim_message_rate_per_second`

Modalità CLI: `uv run --project simulators/sim-textile sim-textile --profile loom --time-scale 2.0` per dev locale senza docker.

**Why:** Dev-friendly (1 docker compose up lancia tutto), low ops overhead, singolo log stream. Metrics endpoint subito utile per debug load test (D-48).

**Rejected alternatives:**
- Per-asset container: 5x overhead docker, complessità debug cross-container.
- Headless CLI no container: non testa docker-compose data-diode (D-51).
- Single container senza metrics: cieca durante load test debug.

## D-51 — OT Bridge data-diode enforcement: docker network ACL + pytest

**Decision:** Belt-and-suspenders pattern:

**Layer 1 (network ACL):**
```yaml
# docker-compose.yml extension
networks:
  ot-network:
    driver: bridge
    internal: false  # OPC-UA può exit; sim-textile pubblica solo (no inbound da it)
  it-network:
    driver: bridge

services:
  sim-textile:
    networks: [ot-network]              # ONLY ot
  ot-bridge:
    networks: [ot-network, it-network]  # bridge — solo container che vede entrambe
  nats:
    networks: [it-network]              # ONLY it
  timescaledb:
    networks: [it-network]
```

ot-bridge è l'unico container con interfacce su entrambe le reti; configurato a livello applicativo per non aprire mai socket ascolto verso ot-network (only outbound subscribe via asyncua client).

**Layer 2 (pytest enforcement):**
```python
# tests/integration/test_data_diode.py
async def test_agent_cannot_reach_sim_textile():
    """Un container 'fake-agent' su it-network NON deve poter aprire socket OPC-UA verso sim-textile."""
    # spawn container temporaneo su it-network
    # tentativo asyncua.Client("opc.tcp://sim-textile:4840") DEVE failure entro 5s
    # asserzione: ConnectionRefusedError | asyncio.TimeoutError | OSError "Network is unreachable"
    with pytest.raises((ConnectionRefusedError, asyncio.TimeoutError, OSError)):
        async with asyncio.timeout(5):
            async with asyncua.Client("opc.tcp://sim-textile:4840") as client:
                await client.get_root_node()
```

Test eseguito in CI come step "Verify OT data-diode" (richiede docker-in-docker o `gh-actions` services context).

**Layer 3 (application-level refuse):**
```python
# services/ot-bridge/src/svc_ot_bridge/main.py
# Bridge espone SOLO subscribe API verso OPC-UA; nessun write endpoint.
# Asserzione static-analysis in CI: grep -E 'set_value|write_attribute' src/svc_ot_bridge/ → exit 0 expected (zero match)
```

**Why:** Network ACL = primary defense (hardware-style). pytest test = audit trail (Phase 11 governance riferimento). App-level refuse = defense-in-depth contro regression.

**Rejected alternatives:**
- K8s NetworkPolicy only: dev workflow non testa (docker-compose unset).
- Application-level only: nessuna garanzia hardware se bug codice rompe pattern.
- Combinazione 3-tier con K8s + helm: aggiunge complessità Phase 11; differito a Phase 11 deployment hardening.

## D-52 — NATS subject hierarchy (Claude's discretion + locked here)

**Decision:** Subject schema:
- `sensor.events.<asset_family>.<asset_id>.<tag_id>` — esempio: `sensor.events.loom.LOOM-01.warp_tension`
- `sensor.alarms.<asset_family>.<asset_id>` — alarm storm aggregate
- `audit.ot.<service>` — log strutturato (Phase 11 governance)

ot-bridge crea JetStream stream `SENSOR_EVENTS` con retention `WorkQueuePolicy` + maxAge `7d` (allineato D-49 compression). Consumer durability per agent: `agent.<agent_name>.consumer` (Phase 4 deciderà nomi consumer).

**Why:** Granularità per tag permette agent subscribers selettivi (PredictiveMaintenance solo su `warp_tension`, AnomalyDetector su `>`). Allineato a STACK.md recommendation NATS JetStream subjects `sensor.events.*`, `agent.actions.*`, `audit.*` (IOT-04).

**Rejected alternatives:**
- `sensor.events.<asset_id>.<tag_id>` (no family): perde drill-down by family.
- `sensor.events.<line_id>.<asset_id>.<tag_id>` (with line): più granulare ma line_id già dentro asset registry; routing via wildcard subject inutile per Phase 4.

</decisions>

<scope_boundaries>

**In scope (Phase 3):**
- sim-textile riempimento (Pydantic models + asyncua server + 5 YAML profiles + Prometheus metrics + asyncio main)
- ot-bridge riempimento (asyncua client + NATS publisher + Pydantic event normalization + asyncpg writer)
- packages/sft-assets/ nuovo package (registry YAML + Pydantic loader + JSON Schema + 30 asset seed + 50 tag seed)
- packages/sft-tools/ nuovo package (replay_cmapss + replay_uci + query_timescale LangChain Tools)
- TimescaleDB hypertable + compression + retention policy + asyncpg migration
- NATS JetStream stream `SENSOR_EVENTS` setup script
- Docker-compose extension (sim-textile + ot-bridge services + dual-network ACL)
- pytest data-diode enforcement test (Layer 2 of D-51)
- Load test custom asyncio harness (D-48) + smoke test in CI
- IOT-09 ingest schema docs (MkDocs sezione "Ingest schema": asset registry layout + tag dictionary + UoM table + sample event JSON)

**Explicitly NOT in scope (deferred):**
- **K8s NetworkPolicy + Helm extension** per data-diode prod-grade → Phase 11 (security hardening)
- **Continuous aggregates TimescaleDB** (OEE/MTBF rollups) → Phase 4-5 (agents definiscono query patterns)
- **Audit trail tables** (agent.actions, hitl.decisions) → Phase 11
- **OPC-UA write commands path** (HITL_REQUIRED) → never in PoC scope; menzionato in ARCHITECTURE.md ma commented out
- **vLLM/LLM serving** → Phase 4 (Core Agentic Runtime)
- **OEE / MTBF computation** → Phase 5-6 (knowledge layer + quality agents)
- **MCP server wrapping** dei tools → Phase 7+ (PROJECT.md AAS+MCP industrial future)
- **Real PLC integration** (vs mock simulator) → out of MVP scope (A-013 scope-limit)
- **Asset registry DB-backed** (vs YAML) → Phase 11 (governance audit needs)

**Out-of-bounds entirely:**
- Multi-tenant simulator (multiple factories): A-012 scope-limit assumption
- Real-time fault injection via web UI: dev tool, non production feature
- ERP integration: A-014 scope-limit

</scope_boundaries>

<deferred_ideas>

**Recorded during this discussion but out of Phase 3 scope:**

- **OPC-UA tag naming standard (ISA-95 / AAS):** Phase 3 usa `urn:mantis:<asset_family>:<asset_id>` browseable namespace. ISA-95 hierarchy formale (Enterprise/Site/Area/Cell) + AAS mapping è Phase 7+ (industrial integration push).
- **Continuous aggregates** OEE/MTBF/throughput: Phase 4-5 quando query patterns degli agent saranno definiti.
- **K8s NetworkPolicy + Helm chart extension** per data-diode prod: Phase 11.
- **MCP wrapping di sft-tools**: Phase 7+ (cross-IDE / cross-AI tool sharing).
- **Simulator burst test 10k msg/s** (capacity headroom): Phase 11 (production load profile).
- **Hot/warm/cold tier storage** (S3 archive after 90d): Phase 11.
- **Asset registry DB-backed** (versioning + audit): Phase 11.
- **PredictiveMaintenance training pipeline su replay data**: Phase 7 (cluster maintenance agents).

</deferred_ideas>

<claudes_discretion>

Areas where the user did not request explicit discussion — Claude's PLAN will follow these sensible defaults and document them:

- **OPC-UA namespace pattern:** `urn:mantis:<asset_family>:<asset_id>` (freeform but documented in `docs/docs/it-ot/opcua-schema.md`). NodeId BrowseName matches asset_id; BrowsePath includes asset_family for grouping. NO ISA-95 hierarchy formale (deferred).
- **OPC-UA server endpoint:** `opc.tcp://sim-textile:4840` (sim-textile service hostname inside ot-network). Anonymous policy (no auth in PoC; A-018 / Phase 11 will harden).
- **NATS subject hierarchy:** D-52 already locked. `sensor.events.<family>.<asset_id>.<tag>` + `sensor.alarms.<family>.<asset_id>` + `audit.ot.<service>`.
- **asyncpg connection pool:** `min_size=10, max_size=20`, statement_cache_size=0 (TimescaleDB has dynamic plan optimization that benefits from cache misses). Connection string from env `TIMESCALE_DSN`.
- **Pydantic models:** v2 frozen + extra=forbid (matches sft-domain pattern). Models in `sft_assets.models`, `sim_textile.models`, `svc_ot_bridge.models`, `sft_tools.replay.models`.
- **Logging:** structlog JSON con fields `service`, `asset_id`, `tag_id`, `event_type`. Output stderr. CI parses for assertion in pytest integration tests.
- **Metrics:** Prometheus client_python in sim-textile + ot-bridge. Endpoint `/metrics` standard. NO Grafana dashboards in Phase 3 (Phase 11 observability hardening).
- **Replay loader dataset paths:** dataset files in `simulators/sim-textile/replay-data/` (gitignored). Download script `scripts/download-replay-datasets.py` (NASA C-MAPSS via direct PHM challenge URL; UCI via uci-ml repo URL). Verify via SHA256 in `replay-data/CHECKSUMS.txt`.
- **CI strategy:** estende `.github/workflows/ci.yml` con step "Run IT/OT integration tests" (docker-compose up + pytest tests/integration/) + step "Run IT/OT load test (smoke)" (1k×10s gate, full PR-labeled). NO separate workflow file.
- **Time skew handling:** simulator emits con `datetime.now(UTC)` come timestamp_utc; ot-bridge ri-stampa server_received_ts ma NON modifica timestamp_utc (preserve source-of-truth). A-004 invariante (skew < 500ms) testato in pytest fixture.
- **Quality codes:** OPC-UA standard StatusCode integer (Good=0, BadOutOfService=0x80AF0000, ecc.) preservato pass-through.
- **Asset registry seed (30 asset):** 12 LOOM-01..12, 8 SPIN-01..08, 4 WARP-01..04, 4 DYE-01..04, 2 STEN-01..02. Tag dictionary ~50 tag distribuiti per family.

</claudes_discretion>

<downstream_guidance>

**For gsd-phase-researcher (Phase 3):**

Research focus areas (high → low priority):
1. **asyncua best practices** per server multi-namespace + subscription management (D-50 single process)
2. **NATS JetStream Python (nats-py)** consumer durability + ack policy + JetStream stream setup script (idempotent)
3. **TimescaleDB hypertable + compression + retention policy** SQL idiomatic (D-49 exact policy SQL); migration management con Alembic vs raw SQL
4. **asyncpg connection pool tuning** per write-heavy workload (sensor events ingestion); `INSERT ... VALUES` vs `COPY` batch performance comparison
5. **NASA C-MAPSS schema** (4 datasets FD001-FD004, 21 sensori, run-to-failure cycles) + UCI Manufacturing dataset variants (air quality, energy, production) — mapping concettuale a asset Mantis (M:1)
6. **LangChain `BaseTool` async pattern** + `args_schema` Pydantic v2 best practice
7. **Docker network ACL pattern** per data-diode (è realmente enforced da Docker bridge driver? L4 sufficient? compose `internal: true` semantica)
8. **pytest integration test** docker-in-docker pattern per data-diode enforcement (D-51 Layer 2) — github-actions services context vs testcontainers-python

NOT research (already decided in this CONTEXT):
- Fault injection mix (D-44)
- Asset registry location (D-45)
- Tool registry location (D-47)
- Load test scenario (D-48)
- Retention policy (D-49)
- Simulator runtime mode (D-50)
- Data-diode enforcement (D-51)

**Output a Validation Architecture section** in RESEARCH.md (Nyquist applies — load test gate, data-diode test, schema validation gates).

**For gsd-planner (Phase 3):**

Expected plan count: **5-7 plans** with clear wave structure:

- **Wave 1 (foundation parallelizable):** packages/sft-assets/ (registry + loader + ~30 asset seed) || packages/sft-tools/ (replay LangChain tools scaffold)
- **Wave 2 (parallel):** sim-textile riempimento (asyncua server + 5 YAML profiles + Prometheus metrics) || ot-bridge riempimento (asyncua client + NATS publisher + asyncpg writer) || TimescaleDB migration (hypertable + policies)
- **Wave 3 (integration):** docker-compose extension (sim-textile+ot-bridge services + dual-network ACL) + pytest data-diode test (D-51 Layer 2) + smoke load test in CI
- **Wave 4 (load + docs):** full load test 5k×60s (D-48) + IOT-09 ingest schema docs (MkDocs section "Ingest schema") + asset registry validate CI integration

Each plan must have:
- Atomic commit boundaries (preserve Phase 1+2 convention scope `feat(03-NN-slug):`)
- Frontmatter schema validation step before content (asset registry, fault profiles)
- `depends_on` in canonical short-form (`["01"]` for foundation packages, `["01","03-01-assets","03-02-tools"]` for sim-textile/ot-bridge that consume sft-assets)

**Sizing constraint:**
- 1 plan = sft-assets (registry + loader + 30 seed) — do NOT split per-asset
- 1 plan = sft-tools (replay_cmapss + replay_uci + query_timescale scaffold) — do NOT split per-tool
- 1 plan = sim-textile (all 5 family emitters + OPC-UA server) — single asyncio process design (D-50)
- 1 plan = ot-bridge (NATS publisher + TimescaleDB writer + data-diode enforcement)
- Performance smoke (1k×10s) in CI Phase 3; full 5k×60s test gated da PR label

</downstream_guidance>

<next_steps>

Run `/clear` to free context, then:

```
/gsd-plan-phase 3
```

This will:
1. Spawn `gsd-phase-researcher` (reads this CONTEXT + ROADMAP + research areas above) → produces `03-RESEARCH.md`
2. Spawn `gsd-pattern-mapper` → produces `03-PATTERNS.md` (maps new files to closest Phase 1+2 analogs)
3. Spawn `gsd-planner` → produces 5-7 `03-NN-slug-PLAN.md` files
4. Spawn `gsd-plan-checker` → verification iteration loop

Only after planning is approved: `/gsd-execute-phase 3`.

</next_steps>
