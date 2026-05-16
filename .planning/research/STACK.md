# Stack Research

**Domain:** Agentic Smart Factory Platform — Textile Manufacturing (GenAI + HITL + IT/OT)
**Researched:** 2026-05-16
**Confidence:** HIGH (Core), MEDIUM (LLM serving tradeoffs), HIGH (Observability)

---

## Validated Locked Choices

The following decisions are confirmed and validated by research. Rationale below.

| Decision | Validation |
|----------|------------|
| Nx monorepo (polyglot) | CONFIRMED — @nxlv/python plugin provides first-class uv + Poetry support; affected commands work for both Python and Angular |
| LangGraph as orchestrator | CONFIRMED — HITL nativo con `interrupt()`, state machine ispezionabili, checkpointing pluggabile |
| Qwen2.5 family via Ollama/vLLM | CONFIRMED — Apache 2.0, ottimo function calling, multilingua IT/EN; tradeoff Ollama/vLLM chiarito sotto |
| Qdrant self-hosted | CONFIRMED — v1.16+, BM42 hybrid search (dense+sparse), on-prem first, MIT license |
| Angular 18+ SSR | CONFIRMED — @nx/angular ha supporto setup-ssr generator e esbuild integrato |
| FastAPI backend | CONFIRMED — standard de facto per backend Python asincrono; httpx + pytest-asyncio per testing |
| MkDocs Material i18n | CONFIRMED — plugin i18n built-in, GitHub Pages deploy via mkdocs gh-deploy |

---

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Nx | 20.x | Monorepo orchestrator, affected commands, remote cache | First-class Python (@nxlv/python) + Angular support; dep-graph cruciale per CI selettiva in repo polyglot |
| @nxlv/python | 21.x | Plugin Nx per Python (uv workspace) | Unico plugin maturo che integra uv workspaces con Nx affected + dependency graph; alternativa Pants è overhead per team piccoli |
| uv | 0.6+ | Python package manager e virtual env | 10-100x più veloce di pip/poetry per lock e install; supporta workspace mode (monorepo); usarlo come "pip sostituto" dentro ogni Python project Nx |
| LangGraph | 0.4+ | Orchestrazione agentica HITL | HITL nativo con `interrupt()` + `Command(resume=)`, state machine ispezionabili, streaming built-in; versione 0.4+ ha PostgreSQL checkpointer v3.1.0 |
| FastAPI | 0.115+ | API backend per servizi agentici | Async-first, OpenAPI auto-generated, dependency injection; standard per Python AI backends |
| Angular | 18+ (v19 target) | Frontend SSR factory floor + admin UI | SSR con hydration incrementale da v17+; `@nx/angular:setup-ssr` generator; touch-friendly con Angular Material |

### LLM Serving

**REGOLA GENERALE:** Usa Ollama per dev/testing, vLLM per produzione multi-utente.

| Technology | Version | Purpose | When to Use |
|------------|---------|---------|-------------|
| Ollama | 0.6+ | LLM serving locale, dev + single-user | Dev environment, CI smoke test, singolo operatore; concorrenza max ~4-8 req/s; VRAM auto-managed |
| vLLM | 0.8+ | LLM serving produzione GPU | Produzione multi-utente: 793 tok/s vs Ollama 41 tok/s; PagedAttention, disaggregated prefill/decode; OpenAI-compatible API |

**Quantizzazione Qwen2.5 — Scelte Prescrittive:**

| Modello | Formato | VRAM | Throughput | Quando |
|---------|---------|------|-----------|--------|
| Qwen2.5-7B | GGUF Q4_K_M via Ollama | ~6 GB | 84 tok/s (vLLM BF16) | Dev locale, agent bassa latenza, hardware consumer |
| Qwen2.5-7B | AWQ via vLLM | ~5 GB | ~100 tok/s | Produzione GPU, massima velocità su 8GB VRAM |
| Qwen2.5-14B | AWQ via vLLM | ~10 GB | 46 tok/s (BF16 ref) | Bilanciamento qualità/velocità; target produzione PoC |
| Qwen2.5-32B | GGUF Q4_K_M via Ollama | ~22-24 GB | Lento, single-user | Demo/eval qualità su RTX 4090 single-GPU |
| Qwen2.5-32B | AWQ via vLLM multi-GPU | ~2×24 GB | Ottimale multi-user | Produzione con 2×A5000 o 2×RTX 4090 |

**Scelta raccomandata per PoC:** Qwen2.5-14B AWQ su vLLM con singola GPU 16-24 GB. Fallback Ollama Qwen2.5-7B Q4_K_M per dev senza GPU dedicata.

**GGUF vs AWQ — Regola:**
- GGUF Q4_K_M = flessibile (CPU+GPU offload, Ollama, llama.cpp), leggermente più lento
- AWQ = solo GPU NVIDIA, CUDA kernels ottimizzati, 15-30% più veloce, usare con vLLM

### Vector Store e Embedding

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Qdrant | 1.16+ | Vector store self-hosted, dense+sparse+BM42 | Hybrid search (BM42 da v1.10, ACORN da v1.14), MIT license, on-prem first, GPU-accelerated indexing da 2025 |
| **BGE-M3** | latest (BAAI) | **Embedding primario — RACCOMANDATO** | MIT license, 100+ lingue, modalità triple (dense+sparse+multi-vector), 8192-token context, MTEB score ~63.0; self-hostabile via FastEmbed o sentence-transformers |
| multilingual-e5-large-instruct | latest (intfloat) | Embedding alternativo | XLM-R Large, superiore su lingue mid-resource (IT), migliore per retrieval multilingua puro; usare come fallback/confronto A/B |

**Embedding consigliato: BGE-M3** perché:
1. Triple-output nativo (dense vectors per semantica + sparse BM42 per keyword exact match + multi-vector ColBERT) in un solo modello
2. MIT license — Jina v3 è CC BY-NC, incompatibile con produzione self-hosted commerciale
3. Context window 8192 token — coprire SOP lunghi senza chunking aggressivo
4. Integrazione nativa con Qdrant FastEmbed: `BAAI/bge-m3` è il modello default per sparse

**Chunk strategy:** 512 token con overlap 64, usando RecursiveCharacterTextSplitter con separatori IT+EN per MkDocs + PDF tecnici.

### Data Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| PostgreSQL | 16+ | Database relazionale principale (LangGraph checkpoints, user data, audit trail) | Standard de facto; LangGraph checkpoint postgres v3.1.0 richiede PG; TimescaleDB è estensione compatibile |
| TimescaleDB | 2.x | Estensione PG per dati time-series sensori | JOIN con dati relazionali (asset metadata, maintenance schedule) senza ETL aggiuntivo; 90% compressione columnar; SQL standard — operatori e manutentori già conoscono SQL |
| Redis | 7.x | Cache, LangGraph short-term memory store, code asincrona | `langgraph-redis` checkpointer + `RedisStore` per long-term memory; alternativa Postgres per checkpointing ad alta frequenza |

**TimescaleDB vince su InfluxDB perché:** InfluxDB v3 è ottimo per pure time-series monitoring ma richiede Flux/InfluxQL separato; per una factory con JOINs tra sensori e ordini produzione, SQL puro di TimescaleDB è decisivo. ClickHouse è overkill per PoC (dimensionamento TB+).

### Agente e Orchestrazione

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| LangGraph | 0.4+ | Runtime agentico HITL | `interrupt()` + `Command(resume=)` per HITL nativo; `StateGraph` + `MessagesState`; parallel subgraph execution |
| langgraph-checkpoint-postgres | 3.1.0 | Persistenza stato agenti (produzione) | Raccomandato ufficialmente per produzione; thread_id per isolamento sessioni operatore |
| langgraph-checkpoint-sqlite | 3.1.0 | Persistenza stato (dev locale) | Solo per dev/testing locale; non usare in produzione (write bottleneck) |
| langgraph-redis | 0.3.2 | Checkpointer Redis + Vector Store Redis | Alternativa Postgres per alta frequenza di checkpoint; include Redis vector search |
| LangChain | 0.3+ | Tool abstractions, LLM adapters | Provider-agnostic LLM adapter (Ollama → vLLM → cloud opzionale); tool calling standard |
| langchain-ollama | 0.3+ | Adapter Ollama | Dev locale |
| langchain-openai | 0.3+ | Adapter vLLM (compatibile OpenAI API) | Produzione; vLLM espone endpoint OpenAI-compatible |

**HITL Pattern con LangGraph:**
```python
# Nodo di approvazione umana
def human_approval_node(state: AgentState) -> Command:
    action = state["proposed_action"]
    result = interrupt({"action": action, "requires_approval": True})
    return Command(resume=result["approved"])
```

### Event Bus

**RACCOMANDAZIONE: NATS JetStream**

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| NATS JetStream | 2.10+ | Event bus principale OT→IT | 820K msg/s throughput; single binary (zero deps); MQTT 3.1.1 bridge nativo per PLC/sensori IoT; at-least-once delivery persistente; ideale per Kubernetes edge/factory |

**Perché NATS su Redis Streams:**
- Redis Streams richiede Redis già in stack (ok, ce l'abbiamo), ma la persistenza dei messaggi degrada performance Redis principale
- NATS JetStream è pensato specificamente per IoT/edge, include MQTT bridge per OPC-UA → NATS pipeline
- Operativamente più leggero di Kafka; single binary senza Zookeeper
- Redis Streams rimane valido se il volume è <10K msg/s e si vuole ridurre componenti

**Fallback:** Se si preferisce ridurre componenti infrastrutturali, Redis Streams su Redis 7.x va bene per il PoC (sensori simulati non superano 1K msg/s).

### OPC-UA (Simulazione IT/OT)

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| asyncua (opcua-asyncio) | 1.0+ | Client/Server OPC-UA per simulatori | Async nativo (asyncio), maintainer attivo (35K+ downloads/week), LGPL license, Python >= 3.10; `python-opcua` sincrono è deprecato |

```bash
pip install asyncua  # pacchetto PyPI è 'asyncua', namespace FreeOpcUa
```

**node-opcua** (Node.js) scartato: inutile aggiungere runtime Node.js solo per OPC-UA quando asyncua è maturo.

### Osservabilità e Tracing

**ARCHITETTURA DUALE:** Langfuse per LLM tracing + stack LGTM per infra.

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Langfuse | v3 (self-hosted) | LLM observability: tracing, eval, prompt management | MIT license, self-hosted first-class (Docker Compose o Helm), 1000+ deployment self-hosted in produzione; integrazione LangGraph via callback nativo; data sovereignty totale |
| OpenTelemetry (otel-sdk) | 1.x | Instrumentazione distributa FastAPI + agenti | Standard CNCF; Langfuse supporta OTEL natively come ingestion point alternativo |
| Prometheus | 2.x | Metriche infra (CPU, GPU, VRAM, latenza) | Scraping pull model; Grafana datasource standard |
| Grafana | 11+ | Visualizzazione unificata metriche + log + trace | Dashboards LGTM stack; node-exporter per GPU metrics NVIDIA |
| Loki | 3.x | Log aggregation | Labels-only indexing, lightweight; Grafana native datasource |
| Tempo | 2.x | Distributed traces (infra layer) | Complementare a Langfuse (che traca LLM calls); Langfuse → OTEL → Tempo per trace end-to-end |

**Langfuse v3 self-hosted richiede:** PostgreSQL (metadata) + ClickHouse (traces/observations) + Redis + MinIO/S3. Docker Compose ufficiale disponibile su github.com/langfuse/langfuse.

**Perché non LangSmith:** Closed-source, SaaS-first, self-hosting richiede Enterprise license. Incompatibile con requisito open-source e data sovereignty industriale.

### Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| pytest | 8.x | Test runner principale | Standard Python; integrazione Nx via @nxlv/python test executor |
| pytest-asyncio | 0.24+ | Test asincroni FastAPI + LangGraph agents | Mandatory per async endpoints; modalità `asyncio_mode = "auto"` in pyproject.toml |
| httpx | 0.28+ | HTTP client per test FastAPI (AsyncClient + ASGITransport) | Async-native, evita avvio server reale in test; zero overhead rispetto a TestClient sync |
| DeepEval | 1.x | RAG evaluation CI/CD gate (PR blocker) | pytest plugin nativo; LLM-as-judge per hallucination rate, answer relevance, bias; un solo LLM call/sample → più economico |
| RAGAS | 0.2+ | RAG evaluation monitoring produzione (campionamento) | Metrics faithfulness + context precision senza ground truth; runner periodico su 5% trace produzione da Langfuse |
| factory-boy | 3.x | Fixture factories per entità dominio | Riduce boilerplate test data; compatibile pytest |

**Pattern dual-framework:**
- DeepEval in CI: blocca PR se hallucination rate > 5% o answer_relevance < 0.75
- RAGAS come Kubernetes CronJob settimanale: campiona trace Langfuse, scrive score back

### Frontend

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Angular | 18+ (target 19) | Framework UI | Locked; SSR con incremental hydration; @nx/angular supporto first-class |
| Angular SSR (@angular/ssr) | 18+ | Server-Side Rendering | `nx generate @nx/angular:setup-ssr`; esbuild integrato; SEO + First Paint per factory floor |
| Angular Material | 18+ | Design system componenti | Componenti accessibili touch-friendly; theme customizzabile con Design Token |
| Tailwind CSS | 3.4+ | Utility CSS per layout custom | Complementare ad Angular Material; più veloce per dashboard KPI custom |
| @ngrx/store | 18+ | State management frontend | Per stato agenti HITL (pending approvals queue); RxJS-native; evita prop drilling in dashboard complessa |
| @angular/pwa | 18+ | Progressive Web App (opzionale v2) | Offline capability per operatori in zona factory con connectivity intermittente |

### Documentazione

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| MkDocs Material | 9.5+ | Documentazione bilingue IT/EN | Plugin i18n integrato; GitHub Pages deploy via `mkdocs gh-deploy`; supporto Mermaid nativo |
| mkdocs-i18n plugin | latest | Internazionalizzazione IT/EN | Separazione contenuti per lingua con fallback EN |
| Mermaid | latest | Diagrammi as-code nei doc | Supported natively in Material theme; sequence diagrams per workflow HITL |
| D2 (opzionale) | latest | Diagrammi architettura avanzati | Alternativa a Mermaid per architettura complessa; non integrato nativamente, richiede pre-render |

### IaC e Deploy

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Docker Compose | v2.x (plugin) | Dev environment completo | Single `docker compose up` avvia: FastAPI, Angular, Qdrant, PostgreSQL+TimescaleDB, Redis, NATS, Langfuse, Ollama |
| Helm | 3.x | Deploy Kubernetes produzione | Helm charts esistenti per: Qdrant, Langfuse, NATS, Prometheus/Grafana stack; riuso chart ufficiali |
| Kustomize | 5.x | Overlay per ambienti (staging/prod) | Alternativa/complemento a Helm per configurazioni environment-specific senza templating |
| Terraform | 1.9+ | Cloud-optional IaC (GPU VMs) | Solo se deploy su cloud; moduli per Azure/AWS GPU instance (per vLLM); on-prem deploy non richiede Terraform |

### CI/CD

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| GitHub Actions | latest | Pipeline CI/CD | Native per GitHub; Nx Cloud integration opzionale |
| nrwl/nx-set-shas | v4 | Calcola base SHA per affected commands | Essenziale per `nx affected --base=$NX_BASE --head=$NX_HEAD` su PR |
| Docker buildx + GHCR | latest | Build e push immagini | GitHub Container Registry gratuito per OSS |

**Workflow pattern raccomandato:**

```yaml
# .github/workflows/ci.yml
on: [push, pull_request]
jobs:
  ci:
    steps:
      - uses: nrwl/nx-set-shas@v4        # calcola base/head SHA
      - run: npx nx affected --target=lint  --base=$NX_BASE --head=$NX_HEAD
      - run: npx nx affected --target=test  --base=$NX_BASE --head=$NX_HEAD
      - run: npx nx affected --target=build --base=$NX_BASE --head=$NX_HEAD
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Agent orchestration | LangGraph | CrewAI | CrewAI è high-level e opininionated; meno controllo su state machine; HITL meno granulare; non adequato per audit trail industriale |
| Agent orchestration | LangGraph | AutoGen (Microsoft) | Conversational agent model; più verboso; HITL non nativo; community più piccola |
| LLM serving | Ollama (dev) + vLLM (prod) | OpenAI API cloud | Cloud lock-in; dati industriali sensibili non devono uscire da factory; costo per-token non sostenibile a lungo termine |
| Vector store | Qdrant | Pinecone | SaaS-only; incompatibile con requisito self-hosted; vendor lock-in |
| Vector store | Qdrant | Chroma | Meno maturo per produzione; no hybrid search; persistenza meno robusta |
| Vector store | Qdrant | pgvector | Valido ma manca hybrid search avanzato (BM42/ACORN); preferire per scenari semplici dove PG già c'è |
| Embedding | BGE-M3 | Jina Embeddings v3 | CC BY-NC license — incompatibile con produzione open-source self-hosted; API richiesta per uso commerciale |
| Embedding | BGE-M3 | OpenAI text-embedding-3 | Cloud API; data sovereignty violata; costo per chiamata |
| LLM observability | Langfuse self-hosted | LangSmith | LangSmith è closed-source; self-hosting richiede Enterprise license; incompatibile con OS + data sovereignty |
| LLM observability | Langfuse self-hosted | Phoenix (Arize) | Meno maturo per self-hosting; minore community |
| Event bus | NATS JetStream | Apache Kafka | Overkill per PoC (Zookeeper/KRaft overhead); stesso ordine di grandezza per throughput ma 10x più complesso da operare |
| Event bus | NATS JetStream | Redis Streams | Redis Streams degrada la performance Redis principale quando usato per event sourcing; NATS JetStream è dedicato e include MQTT bridge nativo |
| Time-series DB | TimescaleDB | InfluxDB v3 | InfluxDB v3 richiede Flux/InfluxQL separato; nessun JOIN nativo con dati relazionali; costo licenza v3 enterprise |
| Time-series DB | TimescaleDB | ClickHouse | Overkill per PoC (dimensionato per TB+); no estensione PG nativa; separazione dati relazionali/time-series |
| Python tooling | uv + @nxlv/python | Pants | Pants ha curva di apprendimento ripida; overkill per team piccolo; @nxlv/python + uv copre il 90% dei casi |
| Python tooling | uv + @nxlv/python | Poetry | Poetry è più lento di uv; nessun workspace mode nativo; uv è il successore de facto in 2025 |
| OPC-UA | asyncua (FreeOpcUa) | node-opcua | Evitare runtime Node.js aggiuntivo; asyncua è maturo e async-native Python |
| RAG eval | DeepEval (CI) + RAGAS (monitoring) | Solo RAGAS | RAGAS non ha pytest integration nativa per CI gate; DeepEval come PR blocker + RAGAS come monitoring periodico è il pattern 2025 de facto |
| Frontend | Angular 18+ | React/Next.js | Locked dall'utente; Nx ha supporto Angular first-class; Module Federation SSR supportato |
| Monorepo | Nx | Turborepo | Turborepo è JS-only; nessun supporto Python nativo; Nx è poliglotta |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| OpenAI API as primary LLM | Dati industriali sensibili; costo per-token non sostenibile; vendor lock-in; GDPR risk per dati factory | Qwen2.5 via Ollama/vLLM self-hosted |
| Pinecone / Weaviate Cloud | SaaS-only; dati vettoriali escono dall'on-premise; incompatibile con security industriale | Qdrant self-hosted |
| LangSmith cloud | Closed-source SaaS; dati trace inviati a LangChain servers; self-hosting richiede Enterprise license | Langfuse self-hosted (MIT) |
| InfluxDB v3 Enterprise | Licenza costosa; query language Flux separato; nessun JOIN SQL | TimescaleDB (PG extension) |
| GPTQ quantization per vLLM | AWQ è superiore per qualità-velocità su NVIDIA; GPTQ kernels più lenti; AWQ preserva pesi critici basandosi su attivazioni | AWQ per vLLM GPU |
| python-opcua (sincrono) | Deprecato; non manutenuto; API bloccante incompatibile con asyncio | asyncua (opcua-asyncio) |
| SQLite checkpointer in produzione | Write bottleneck critico; non adatto a multi-agent concurrent state; documentazione LangGraph sconsiglia esplicitamente | langgraph-checkpoint-postgres |
| AsyncSqliteSaver in produzione | Stesso bottleneck SQLite; usare solo per dev locale o test | PostgresSaver o RedisSaver |
| CrewAI come orchestratore | HITL limitato; black-box interno; difficile auditing; non adeguato per governance AI industriale | LangGraph |
| Jina Embeddings v3 | CC BY-NC: incompatibile con progetto opensource self-hosted in contesti produzione | BGE-M3 (MIT) |
| Kafka per event bus PoC | Complessità operativa (KRaft/Zookeeper, topic management, consumer groups) sproporzionata per <10K msg/s | NATS JetStream |
| Multi-tenant SaaS deploy | Anti-feature esplicita; dati di fabbriche diverse non devono mescolarsi; security industriale richiede isolamento | Single-tenant self-hosted on-premise |
| Fine-tuning LLM da zero | Fuori scope; costoso in compute e dati; LoRA su Qwen2.5 solo se necessario per dominio specializzato | RAG su Qdrant per knowledge base tessile |

---

## Stack Patterns by Variant

**Se hardware è CPU-only (no GPU):**
- Usa Ollama con Qwen2.5-7B Q4_K_M
- BGE-M3 in modalità CPU per embedding (lento ma funzionale)
- Riduci concorrenza agenti a 2 paralleli max
- TimescaleDB rimane identico

**Se GPU è singola 16GB (es. RTX 4080):**
- Qwen2.5-14B AWQ via vLLM — target primario PoC
- BGE-M3 su GPU condivisa (batch embedding asincrono)
- Concorrenza 4-8 utenti simultanei comfortably

**Se GPU è singola 24GB (RTX 4090 / A5000):**
- Qwen2.5-32B GGUF Q4_K_M via Ollama per demo qualità
- Oppure Qwen2.5-14B AWQ via vLLM per produzione concorrente

**Se infra è Kubernetes (produzione):**
- Helm chart per ogni servizio (Qdrant, NATS, Langfuse, Prometheus stack)
- Kustomize overlay per staging vs prod namespaces
- Sostituire Docker Compose con Helm durante deploy

**Se si vuole cloud-optional (AWS/Azure):**
- Terraform modulo per GPU VM (AWS p3.2xlarge o Azure NC6s_v3)
- vLLM container su GPU VM
- Tutto il resto rimane identico (Qdrant, Langfuse, NATS self-hosted su VM)

**Se LLM fallback cloud è necessario (SLA critico):**
- Implementare adapter LangChain: `ChatOllama` (local) → `ChatOpenAI` (cloud fallback)
- Configurare via env var `LLM_PROVIDER=ollama|vllm|openai`
- OpenAI/Azure OpenAI come ultima istanza, non primario

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| LangGraph 0.4+ | LangChain 0.3+ | Disaccoppiati da 0.2; importare da `langgraph` non da `langchain` |
| langgraph-checkpoint-postgres 3.1.0 | PostgreSQL 12+ | `checkpointer.setup()` obbligatorio al primo avvio |
| langgraph-redis 0.3.2 | Redis 7.x | `RedisSaver.from_conn_string()` + `store.setup()` |
| asyncua 1.x | Python 3.10+ | Python 3.12 raccomandato per performance |
| Qdrant 1.16 | qdrant-client 1.9+ | BM42 richiede FastEmbed installato: `pip install qdrant-client[fastembed]` |
| Angular 18/19 | @nx/angular 20.x | `nx generate @nx/angular:setup-ssr` per SSR; esbuild richiesto |
| DeepEval 1.x | pytest 8.x | `deepeval test run test_rag.py` wrappa pytest |
| RAGAS 0.2+ | LangChain 0.3+ | Supporta custom LLM judge (usare Qwen2.5-14B per eval senza cloud) |
| uv 0.6+ | @nxlv/python 21.x | `packageManager: "uv"` in nx.json |
| Langfuse v3 | PostgreSQL 12+, ClickHouse 24.3+ | Timezone UTC obbligatoria su tutti i DB |

---

## Installation — Bootstrap Commands

```bash
# Nx workspace creation (polyglot)
npx create-nx-workspace@latest smart-factory --preset=empty --packageManager=npm

# Nx plugins
npm install -D @nx/angular @nxlv/python @nx/docker

# Python projects (es. agente)
npx nx generate @nxlv/python:uv-project --name=agent-core --projectType=library

# Angular SSR app
npx nx generate @nx/angular:application --name=factory-ui --routing --ssr

# Infra Python deps per agente
uv add langgraph langchain langchain-ollama langchain-openai \
       qdrant-client[fastembed] asyncua fastapi uvicorn \
       nats-py langfuse opentelemetry-sdk

# Testing
uv add --dev pytest pytest-asyncio httpx deepeval ragas factory-boy

# Frontend (in apps/factory-ui)
npm install @angular/material @ngrx/store tailwindcss

# MkDocs
pip install mkdocs-material mkdocs-i18n
```

---

## Sources

- Context7 `/websites/langchain_oss_python_langgraph` — HITL patterns, checkpointing backends, Redis/Postgres savers (HIGH confidence)
- [LangGraph checkpoint-postgres PyPI 3.1.0](https://pypi.org/project/langgraph-checkpoint-postgres/) — version confirmed (HIGH)
- [Qwen2.5 Speed Benchmark — official docs](https://qwen.readthedocs.io/en/v2.5/benchmark/speed_benchmark.html) — throughput 7B/14B/32B (HIGH)
- [Qwen2.5-32B VRAM requirements](https://apxml.com/models/qwen2-5-32b) — ~80GB FP16, ~24GB Q4_K_M (MEDIUM)
- [vLLM vs Ollama production benchmark 2026](https://codersera.com/blog/vllm-vs-ollama-vs-lm-studio-production-2026/) — 793 tok/s vs 41 tok/s (MEDIUM)
- [LLM Quantization: Q4_K_M vs AWQ vs FP16](https://www.sitepoint.com/quantization-explained-q4km-vs-awq-vs-fp16-for-local-llms/) — quantization tradeoffs (MEDIUM)
- [BGE-M3 vs Jina comparison — VIPS](https://learn.engineering.vips.edu/compare/bge-m3-vs-jina-embeddings-v3) — embedding model comparison (MEDIUM)
- [Best embedding models for multilingual RAG](https://www.knightli.com/en/2026/04/23/compare-openai-bge-e5-gte-jina-embedding-models/) — multilingual-e5 recommendation (MEDIUM)
- [MMTEB benchmark 2025](https://arxiv.org/abs/2502.13595) — multilingual embedding benchmarks (HIGH)
- [Qdrant BM42 article](https://qdrant.tech/articles/bm42/) — BM42 da v1.10, FastEmbed integration (HIGH)
- [Qdrant 1.16 release](https://qdrant.tech/blog/qdrant-1.16.x/) — tiered multitenancy, ACORN (HIGH)
- [asyncua GitHub — FreeOpcUa](https://github.com/FreeOpcUa/opcua-asyncio) — OPC-UA async, 35K downloads/week (HIGH)
- [Langfuse vs LangSmith comparison](https://langfuse.com/faq/all/langsmith-alternative) — MIT license, self-hosting (HIGH)
- [Langfuse v3 Docker Compose](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml) — PostgreSQL + ClickHouse + Redis + MinIO (HIGH)
- [NATS JetStream vs Redis Streams 2026](https://www.javacodegeeks.com/2026/03/nats-vs-kafka-vs-redis-streams-for-java-microservices-when-simpler-actually-wins.html) — throughput comparison, IoT suitability (MEDIUM)
- [TimescaleDB review 2026](https://www.modern-datatools.com/tools/timescaledb) — JOIN capability, sensor data (MEDIUM)
- [ClickHouse vs TimescaleDB vs InfluxDB 2026](https://sanj.dev/post/clickhouse-timescaledb-influxdb-time-series-comparison) — benchmark comparison (MEDIUM)
- [DeepEval vs RAGAS 2026](https://genai.qa/blog/deepeval-vs-ragas/) — dual-framework pattern, CI vs monitoring (MEDIUM)
- [@nxlv/python npm](https://www.npmjs.com/package/@nxlv/python) — uv workspace support confirmed (HIGH)
- [Nx Angular setup-ssr generator](https://nx.dev/nx-api/angular/generators/setup-ssr) — SSR generator docs (HIGH)
- [Ollama FAQ concurrency](https://docs.ollama.com/faq) — OLLAMA_NUM_PARALLEL, VRAM limits (HIGH)

---

*Stack research for: Agentic Smart Factory Transformation (Textile) — opensource self-hosted*
*Researched: 2026-05-16*
