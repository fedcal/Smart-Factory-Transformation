# Phase 11: Observability, Evaluation & Security Hardening — Research

**Researched:** 2026-05-24
**Domain:** OpenTelemetry · Langfuse v3 · DeepEval + RAGAS · Grafana provisioning · Prompt-injection sanitization · STRIDE · OWASP LLM Top-10
**Confidence:** HIGH (codebase verificato direttamente; pacchetti controllati via PyPI; pattern OTEL/Langfuse confermati da documentazione ufficiale)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

1. **Evaluation strategy + CI gate** — DeepEval + RAGAS, synthetic ground-truth dataset, CI gate con mock/deterministic LLM.
   - Gate BLOCCA su: hallucination rate >5% OR answer relevance <0.75 (SC-2).
   - Eseguito con mock/deterministic LLM per riproducibilità (no GPU in CI).
   - Real-Ollama run = optional/local job.

2. **Trace propagation + Langfuse** — Full propagation + Langfuse self-hosted (docker-compose dev).
   - OTEL SDK su agents + OT Bridge + gateway con trace-ID propagation end-to-end (UI→gateway→NATS→LangGraph→Langfuse).
   - OTEL context injection/extraction su messaggi NATS.
   - Langfuse v3 self-hosted via `infra/compose/obs.yml` (estendere esistente) per dev.
   - Riutilizzare `packages/sft-agents/.../llm/langfuse_callback.py`.

3. **Prompt-injection defense in ingest** — Structural sanitization + denylist (deterministic, no LLM).
   - Strip pattern noti ("ignore previous instructions", role delimiter, imperative instruction block).
   - Neutralizzare markdown/HTML, trattare contenuto documento come data not instructions.
   - CI security test: crafted PDF → assert nessuna agent action influenzata (SC-3).

4. **OT Bridge data-diode test + Grafana** — App-level guard test (CI-runnable) + real Grafana provisioning JSON.
   - SEC-06: test automatico che un write command verso OPC-UA è bloccato dalla guard (app-level, senza OT hardware).
   - Grafana: provisioning JSON reale (agent KPIs + factory KPIs + cost dashboard).

### Claude's Discretion
Nessun'area esplicita di discrezione aperta; tutte e 4 le gray area sono LOCKED.

### Deferred Ideas (OUT OF SCOPE)
- Real IdP/Keycloak, JWKS rotation, refresh tokens.
- Distributed (Redis) rate-limiter (solo se scoped dal planner sotto AR-07; altrimenti documentato).
- Live GPU/real-LLM eval run.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OBS-02 | OpenTelemetry SDK su tutti gli agenti, OT Bridge, API Gateway con propagazione trace ID | OTEL SDK 1.42.x già in api-gateway; pattern inject/extract NATS documentato |
| OBS-03 | Stack LGTM (Loki + Grafana + Tempo + Mimir/Prometheus) opzionale documentato | Grafana provisioning via compose volumes — pattern verificato |
| OBS-04 | Dashboard Grafana preconfezionate per KPI agenti e KPI factory | Dashboard JSON via `infra/grafana/provisioning/` |
| OBS-05 | Suite eval RAG con DeepEval e RAGAS, gate in CI con threshold configurabili | DeepEval 4.0.3 + RAGAS 0.4.3 su PyPI; mock LLM pattern verificato |
| OBS-06 | Eval agenti: ground truth dataset 30+ scenari per cluster | `tests/data/rag_eval/testset.jsonl` già esiste (estendere a 30+) |
| OBS-07 | Cost dashboard: token consumati, costo simulato, latency p50/p95/p99 per agente | Metriche budget già in `sft_agents/models/budget.py`; Grafana query su Prometheus |
| SEC-01 | Threat model documentato (STRIDE) per IT/OT, RAG ingestion, agent orchestration | Register threat da fase 8/9/10 da consolidare |
| SEC-02 | Mitigation OWASP LLM Top 10 | Mapping a mitigazioni concrete già implementate in fasi 4-10 |
| SEC-03 | RBAC con ruoli: operator, supervisor, manager, technician, admin, auditor | Ruolo `auditor` mancante in `jwt.py` — aggiungere |
| SEC-04 | Sanitizzazione documenti in ingest (markdown safe, stripping prompt-injection pattern) | `parsers/markdown.py` già usa `yaml.safe_load`; aggiungere strato sanitizzazione |
| SEC-05 | Secret management via env + `.env.example` documentato; nessun secret hard-coded | `.env.example` già in `infra/compose/` — estendere con nuove var Phase 11 |
| SEC-06 | Network policy: OT Bridge non ha route inverso verso OPC-UA (verificato in test) | `opcua_client.py` già subscribe-only; CI grep gate già documentato — formalizzare come test pytest |
| SEC-07 | Audit log di ogni accesso a documenti `restricted` | Pattern `ActionType` già esistente in `enums.py` — aggiungere `RESTRICTED_DOC_ACCESS` |
</phase_requirements>

---

## Summary

La Phase 11 è interamente additiva rispetto a un codebase già maturo: non introduce nuovi agent cluster ma strumenta, valuta e indurisce tutto quello che esiste. Il 70-80% del lavoro è cablaggio e documentazione su fondamenta esistenti (OTEL già in api-gateway, Langfuse già in sft-agents, prometheus-client già in ot-bridge, testset.jsonl già in tests/data/).

Le tre sfide tecniche principali sono: (1) la propagazione OTEL attraverso NATS che richiede un carrier adapter manuale (nessuna libreria auto-instrumentation ufficiale per nats-py), (2) la determinism del CI gate DeepEval+RAGAS che richiede una stub class `MockDeepEvalLLM(DeepEvalBaseLLM)` con risposte fisse per evitare dipendenza da LLM esterno, (3) la struttura STRIDE consolidata che deve coprire almeno 1 minaccia per categoria × 3 superfici (IT/OT, RAG ingest, agent orchestration).

**Primary recommendation:** Iniziare da Wave 0 (infra OTEL + Langfuse endpoint expose) perché è prerequisito bloccante per tutto il resto; parallelizzare Wave 1 (DeepEval/RAGAS scaffold) e Wave 2 (sanitizzazione ingest) poiché operano su file disgiunti.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| OTEL trace propagation (inject) | API / Backend (gateway) | NATS publisher layer | Il gateway è il punto di ingresso della trace; inietta W3C traceparent negli header NATS |
| OTEL trace propagation (extract) | API / Backend (agents) | LangGraph node | Gli agenti LangGraph estraggono il contesto dal payload NATS e aprono span figli |
| Langfuse trace ingest | API / Backend (agents) | Langfuse self-hosted | Il CallbackHandler manda le span a Langfuse via SDK — già implementato |
| Grafana dashboards | CDN / Static (provisioning JSON) | Prometheus/Tempo backend | JSON versionato in git; Grafana monta come volume |
| DeepEval CI gate | Build pipeline (pytest) | — | Eseguito come step pytest nel workflow ci.yml |
| Prompt-injection sanitization | API / Backend (ingest pipeline) | — | `pipeline.py` + `parsers/markdown.py` — strato deterministico pre-embedding |
| RBAC auditor role | API / Backend (gateway) | Browser / Client (rbac.guard) | Aggiungere `auditor@mantis.it` a SEEDED_USERS + require_roles enforcement |
| OT Bridge write-block guard | API / Backend (ot-bridge) | — | Guard applicativa: assert che nessun codice path chiama API write OPC-UA |
| Restricted-doc audit log | API / Backend (agents / retrieval) | Database (audit.actions) | `ActionType.RESTRICTED_DOC_ACCESS` scritto al momento della query Qdrant se acl_level=restricted |
| STRIDE doc | Documentation | — | File Markdown in `docs/security/` — non un tier runtime |

---

## Standard Stack

### Core (nuove dipendenze Phase 11)

| Library | Version verificata | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| `opentelemetry-sdk` | 1.42.1 [VERIFIED: PyPI] | TracerProvider, SpanExporter base | Già in api-gateway; estendere con exporter OTLP |
| `opentelemetry-exporter-otlp-proto-grpc` | 1.42.1 [VERIFIED: PyPI] | Esportare span verso Tempo/Langfuse via gRPC | Standard esporter OTLP community |
| `opentelemetry-exporter-otlp-proto-http` | 1.42.1 [VERIFIED: PyPI] | Fallback HTTP/protobuf (per ambienti senza gRPC) | Richiesto da Langfuse self-hosted endpoint |
| `opentelemetry-instrumentation-fastapi` | 0.63b0 (latest 0.55b0+) [VERIFIED: PyPI] | Auto-span su FastAPI (già presente in api-gateway) | Best-effort già wired |
| `prometheus-client` | 0.25.0 [VERIFIED: PyPI] | Metrics counter/histogram/gauge (già in ot-bridge) | Standard; non aggiunge nuova dipendenza |
| `deepeval` | 4.0.3 [VERIFIED: PyPI] | Framework eval RAG + agenti con pytest integration | CI gate hallucination/relevance |
| `ragas` | 0.4.3 [VERIFIED: PyPI] | Metriche RAG non-LLM e LLM-based | Context precision/recall + faithfulness |
| `bleach` | 6.3.0 [VERIFIED: PyPI] | HTML sanitization per strip injection payload | Piccola dep, matura (Mozilla) |

### Dipendenze già presenti (nessuna nuova installazione richiesta)

| Library | Dove già presente | Utilizzo Phase 11 |
|---------|------------------|-------------------|
| `langfuse>=3,<4` | `packages/sft-agents/pyproject.toml` | CallbackHandler Langfuse v3 — solo estendere wiring |
| `opentelemetry-api>=1.40` | `apps/api-gateway/pyproject.toml` | Traceparent inject/extract |
| `nats-py>=2.14` | `packages/sft-agents` + `svc_ot_bridge` | NATS header carrier |
| `prometheus-client` | `services/ot-bridge` | Già wired in `metrics.py` |
| `structlog` | Tutti i servizi | Log structured con trace_id |

### Alternative Considerate

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `opentelemetry-exporter-otlp-proto-grpc` | `opentelemetry-exporter-otlp-proto-http` | HTTP più semplice ma minore throughput; usare HTTP come fallback se gRPC non disponibile in CI |
| `bleach` per HTML strip | `markdownify` + regex manuale | `bleach` è specifico HTML whitelist; per Markdown puro la regex è sufficiente — usare entrambi in pipeline |
| `deepeval` stub LLM | Pre-computed fixture JSONL | Il stub è più flessibile per nuovi test case; fixture JSONL richiede ricalcolo manuale — usare stub |

**Installation (nuovi pacchetti per i package che ne necessitano):**
```bash
# In packages/sft-agents o nel workspace eval package
uv add deepeval>=4.0,<5 ragas>=0.4,<0.5 bleach>=6.3,<7
# In apps/api-gateway (OTLP exporter)
uv add opentelemetry-exporter-otlp-proto-grpc>=1.42,<2
```

---

## Package Legitimacy Audit

> Verifica eseguita su PyPI (fase Python — slopcheck usa npm di default, non applicabile).
> Tutti i pacchetti verificati manualmente con `pip index versions`.

| Package | Registry | Age | Downloads | Source Repo | Verifica | Disposition |
|---------|----------|-----|-----------|-------------|----------|-------------|
| `deepeval` | PyPI | ~2 anni | Alto (framework noto) | github.com/confident-ai/deepeval | [VERIFIED: PyPI] | Approved |
| `ragas` | PyPI | ~2 anni | Alto (framework noto) | github.com/explodinggradients/ragas | [VERIFIED: PyPI] | Approved |
| `opentelemetry-sdk` | PyPI | 5+ anni | Molto alto (CNCF) | github.com/open-telemetry/opentelemetry-python | [VERIFIED: PyPI] | Approved |
| `opentelemetry-exporter-otlp-proto-grpc` | PyPI | 4+ anni | Molto alto (CNCF) | github.com/open-telemetry/opentelemetry-python | [VERIFIED: PyPI] | Approved |
| `opentelemetry-exporter-otlp-proto-http` | PyPI | 4+ anni | Molto alto (CNCF) | github.com/open-telemetry/opentelemetry-python | [VERIFIED: PyPI] | Approved |
| `bleach` | PyPI | 10+ anni | Molto alto (Mozilla) | github.com/mozilla/bleach | [VERIFIED: PyPI] | Approved |
| `prometheus-client` | PyPI | 8+ anni | Molto alto (CNCF) | github.com/prometheus/client_python | [VERIFIED: PyPI] | Approved |

**Pacchetti rimossi per SLOP:** nessuno.
**Pacchetti flagged SUS:** nessuno.

Nota: slopcheck ha verificato i nomi come npm package — falso positivo perché sono Python package. La verifica corretta è `pip index versions` sopra.

---

## Architecture Patterns

### System Architecture Diagram

```
Angular UI
   │ X-Trace-ID (HTTP header W3C traceparent)
   ▼
FastAPI Gateway ──[OTLPExporter]──► Tempo (traces)
   │ W3C traceparent in NATS Msg.Headers                    │
   ▼                                                         │
NATS JetStream ─── NATSCarrier.extract() ──►               │
   │                                                         │
   ▼                                                         │
LangGraph Supervisor                                         │
   │  langfuse_callback.py (CallbackHandler)                 │
   │  ├── span: llm_call (token count, latency)             │
   │  └── span: tool_call (HITL decision)                   │
   │  OTLP/HTTP ──────────────────────────────────►        │
   │                                               Langfuse (self-hosted, obs.yml)
   │                                                         │
   ▼                                                Prometheus ◄── ot-bridge/metrics.py
OT Bridge                                                    │
   │ subscribe-only OPC-UA                                   │
   │ write-block guard test (pytest)                Grafana ─┤
   │                                                         │ provisioning JSON
   ▼                                                         ▼
OPC-UA Simulator                           Dashboards: agent KPIs / factory / cost

Eval CI:
  tests/eval/ ──► DeepEval[MockLLM] + RAGAS[non-LLM] ──► pytest gate (hallucination ≤5%, relevance ≥0.75)

Ingest SEC:
  PDF/MD ──► sanitize_document() ──► denylist regex strip ──► bleach.clean() ──► embedding
                                  └──► CI test: crafted PDF → assert no agent action
```

### Recommended Project Structure (nuovi file Phase 11)

```
packages/sft-agents/src/sft_agents/
├── otel/
│   ├── __init__.py
│   ├── provider.py          # setup_tracer_provider() — TracerProvider + OTLPExporter
│   └── nats_carrier.py      # NatsHeaderCarrier(TextMapCarrier) per inject/extract

services/knowledge-ingest/src/svc_knowledge_ingest/
└── sanitizer.py             # sanitize_document(text) → str — denylist + bleach

tests/eval/
├── conftest.py              # MockDeepEvalLLM, fixtures ground-truth dataset
├── test_rag_ci_gate.py      # DeepEval + RAGAS gate (hallucination/relevance)
├── test_agent_eval.py       # Agent scenario eval (30+ per cluster)
└── dataset/
    └── ground_truth.jsonl   # 30+ scenari sintetici per cluster

tests/security/
├── test_prompt_injection.py # crafted PDF → assert no influenced action (SEC-04)
└── test_ot_bridge_guard.py  # write command → assert blocked (SEC-06)

infra/grafana/
├── provisioning/
│   ├── datasources/
│   │   └── datasources.yaml # Prometheus + Tempo
│   └── dashboards/
│       ├── dashboards.yaml  # provider config
│       ├── agent-kpis.json  # OBS-04: latency p50/p95/p99, token count
│       ├── factory-kpis.json # OBS-04: OEE, MTTR, MTBF, scrap
│       └── cost-dashboard.json # OBS-07: costo simulato, token per agente

docs/security/
└── STRIDE-threat-model.md   # SEC-01: IT/OT + RAG ingest + agent orchestration

infra/compose/obs.yml        # estendere: aggiungere Grafana + Prometheus + Tempo
infra/compose/.env.example   # estendere: OTEL_EXPORTER_OTLP_ENDPOINT, LANGFUSE_PUBLIC_KEY, ecc.
```

### Pattern 1: NATS Context Propagation (OBS-02)

**What:** Inject W3C traceparent nel NATS Msg.Headers al publish; extract al subscribe.
**When to use:** Ogni volta che il gateway pubblica un comando agent su NATS.

```python
# Source: opentelemetry.io/docs/languages/python/propagation/ + pattern manuale

from opentelemetry.propagators.textmap import TextMapPropagator
from opentelemetry import propagate
from nats.aio.msg import Msg
from typing import MutableMapping

class NatsHeaderCarrier(MutableMapping):
    """Adapter NATS Msg.Headers → TextMapCarrier per OTEL propagation."""

    def __init__(self, headers: dict) -> None:
        self._headers = headers

    def __getitem__(self, key: str) -> str:
        return self._headers[key]

    def __setitem__(self, key: str, value: str) -> None:
        self._headers[key] = value

    def __delitem__(self, key: str) -> None:
        del self._headers[key]

    def __iter__(self):
        return iter(self._headers)

    def __len__(self) -> int:
        return len(self._headers)


# Publisher (gateway):
from opentelemetry import trace, propagate

def publish_agent_command(nc, subject: str, payload: bytes) -> None:
    headers: dict[str, str] = {}
    propagate.inject(NatsHeaderCarrier(headers))   # inietta traceparent
    nc.publish(subject, payload, headers=headers)

# Subscriber (agent runner):
from opentelemetry import context as otel_context

def handle_agent_command(msg: Msg) -> None:
    carrier = NatsHeaderCarrier(dict(msg.headers or {}))
    ctx = propagate.extract(carrier)               # estrae traceparent
    token = otel_context.attach(ctx)
    try:
        with tracer.start_as_current_span("agent.command", kind=SpanKind.CONSUMER):
            # ... processo il comando
            pass
    finally:
        otel_context.detach(token)
```

### Pattern 2: TracerProvider Setup (OBS-02)

```python
# Source: [CITED: opentelemetry-python official SDK docs]
# packages/sft-agents/src/sft_agents/otel/provider.py

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
import os

def setup_tracer_provider(service_name: str) -> TracerProvider:
    """Configura TracerProvider con OTLPExporter verso Tempo/Langfuse.
    
    Env vars:
        OTEL_EXPORTER_OTLP_ENDPOINT  — default http://tempo:4317 (gRPC)
        OTEL_SERVICE_NAME            — override service_name
    """
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "http://tempo:4317")
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    if endpoint:
        exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider
```

### Pattern 3: Langfuse + OTEL dual-path (OBS-01, OBS-02)

**Il CallbackHandler Langfuse v3 è SEPARATO dall'OTEL TracerProvider.**
Langfuse v3 espone `/api/public/otel` che accetta span OTLP — si può configurare un secondo esporter OTLP che punta a Langfuse self-hosted, oppure mantenere il CallbackHandler LangChain già implementato. La scelta LOCKED è mantenere il CallbackHandler.

```python
# Estensione di build_invocation_config() in langfuse_callback.py
# Aggiungere tag "phase11" alla lista per identificazione traces
config = build_invocation_config(
    thread_id=thread_id,
    user_id=principal.get("sub"),
    tags=["phase11", cluster_name],
)
```

### Pattern 4: DeepEval Mock LLM per CI deterministic (OBS-05)

**Pitfall critico:** Tutti i metric LLM-based di DeepEval (`AnswerRelevancy`, `Faithfulness`, `HallucinationMetric`) richiedono un LLM judge. **Senza mock**, il CI chiama OpenAI o Ollama — entrambi non deterministici e potenzialmente assenti.

**Soluzione:** Subclassare `DeepEvalBaseLLM` con risposte fisse basate su un fixture JSONL pre-calcolato.

```python
# Source: [CITED: deepeval.com/docs/metrics-introduction]
# tests/eval/conftest.py

from deepeval.models import DeepEvalBaseLLM

class MockDeepEvalLLM(DeepEvalBaseLLM):
    """LLM judge deterministico per CI. Risponde con score fissi da fixture.
    
    Non chiama nessun LLM esterno. Ogni invocazione restituisce
    un JSON hardcoded che DeepEval interpreta come verdetto.
    """
    
    def load_model(self):
        return self  # nessun modello da caricare

    def generate(self, prompt: str) -> str:
        # Risposta minima che soddisfa il parser DeepEval:
        # { "score": 1, "reason": "mock deterministic" }
        return '{"score": 1, "reason": "mock deterministic CI judge"}'

    async def a_generate(self, prompt: str) -> str:
        return self.generate(prompt)

    def get_model_name(self) -> str:
        return "mock-deterministic-ci"
```

**Implicazione:** I test con MockDeepEvalLLM non misurano qualità reale — misurano che la pipeline non esplode e che le metriche RAGAS non-LLM (string similarity, BLEU) soddisfano i threshold. Il gate CI usa fixture pre-calcolati con Ollama locale (run separato) e poi confronta con JSONL golden.

**Approccio consigliato:**
- Gate CI = RAGAS metriche **non-LLM** (context_precision, context_recall — basati su string overlap) + DeepEval fixture pre-calcolati.
- Local/optional job = Ollama real-LLM per aggiornare il fixture JSONL golden.

### Pattern 5: Grafana Provisioning (OBS-03, OBS-04, OBS-07)

```yaml
# infra/grafana/provisioning/datasources/datasources.yaml
# Source: [CITED: grafana.com/docs grafana provisioning]
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    jsonData:
      tracesToLogs:
        datasourceUid: loki
```

```yaml
# infra/compose/obs.yml (aggiunta Grafana + Prometheus + Tempo)
services:
  prometheus:
    image: prom/prometheus:v2.53.3
    volumes:
      - ./infra/grafana/prometheus.yml:/etc/prometheus/prometheus.yml:ro
    networks: [sft-obs]
  
  tempo:
    image: grafana/tempo:2.6.1
    command: ["-config.file=/etc/tempo.yaml"]
    volumes:
      - ./infra/grafana/tempo.yaml:/etc/tempo.yaml:ro
    networks: [sft-obs]

  grafana:
    image: grafana/grafana:11.3.1
    volumes:
      - ./infra/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./infra/grafana/dashboards:/var/lib/grafana/dashboards:ro
    environment:
      GF_AUTH_ANONYMOUS_ENABLED: "true"   # dev only
      GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer
    ports:
      - "3001:3000"   # evita conflitto con Langfuse su 3000
    networks: [sft-obs]
```

### Pattern 6: Prompt-injection Sanitization (SEC-04)

```python
# services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py
import re
import bleach

# Denylist pattern noti per prompt injection (deterministic, no LLM)
_INJECTION_PATTERNS: tuple[re.Pattern, ...] = (
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>", re.IGNORECASE),
    re.compile(r"###\s*(Human|Assistant|System)\s*:", re.IGNORECASE),
    re.compile(r"<\s*/?system\s*>", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?previous", re.IGNORECASE),
)

def sanitize_document(text: str) -> str:
    """Applica sanitizzazione deterministiche anti-injection.
    
    1. Strip pattern injection noti (denylist regex)
    2. Strip HTML con bleach (whitelist vuota — testo plain)
    3. Normalizza whitespace
    
    NON usa LLM — deterministic e CI-testabile (SEC-04, CONTEXT locked decision 3).
    
    Args:
        text: Testo estratto dal documento (post-parse).
    
    Returns:
        Testo sanitizzato — sempre stringa (mai None).
    """
    result = text
    for pattern in _INJECTION_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    # Strip HTML residuo (es. da PDF con HTML embedding)
    result = bleach.clean(result, tags=[], strip=True)
    # Normalizza whitespace eccessivo
    result = re.sub(r"\s{3,}", "\n\n", result)
    return result.strip()
```

### Pattern 7: SEC-06 OT Bridge Write-Block Guard Test

Il `services/ot-bridge/src/svc_ot_bridge/opcua_client.py` è già subscribe-only con commento "CI gate: grep pattern write-API → exit 1". Il test pytest formalizza questa asserzione:

```python
# tests/security/test_ot_bridge_guard.py
import ast
import pathlib

OT_BRIDGE_SRC = pathlib.Path("services/ot-bridge/src/svc_ot_bridge")
WRITE_PATTERNS = frozenset({"write_value", "call_method", "set_attribute", "write_attributes"})

def test_ot_bridge_has_no_write_api_calls():
    """SEC-06: verifica che nessun modulo in ot-bridge chiami API write OPC-UA.
    
    Questo test sostituisce il grep commentato in opcua_client.py con un assert
    pytest strutturato che analizza l'AST Python — più robusto di grep su stringhe.
    """
    violations = []
    for py_file in OT_BRIDGE_SRC.rglob("*.py"):
        source = py_file.read_text()
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in WRITE_PATTERNS:
                violations.append(f"{py_file}:{node.col_offset} → {node.attr}()")
    assert not violations, f"OT Bridge write API detected (SEC-06 violation):\n" + "\n".join(violations)
```

### Pattern 8: SEC-07 Restricted Document Audit Log

```python
# packages/sft-agents/src/sft_agents/models/enums.py — aggiungere:
# Phase 11 additions — keep in lockstep with migration 014_extend_audit_phase11.sql
RESTRICTED_DOC_ACCESS = "RESTRICTED_DOC_ACCESS"  # SEC-07: query a chunk acl_level=restricted

# packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py — dopo query Qdrant:
# if any(r.acl_level == "restricted" for r in results):
#     await audit_writer.write(ActionType.RESTRICTED_DOC_ACCESS, ...)
```

### Anti-Patterns da Evitare

- **Anti-pattern: OTEL global provider impostato due volte.** Se `setup_tracer_provider()` viene chiamato sia nel gateway che negli agenti nello stesso processo, il secondo override sovrascrive il primo. Usare un modulo singleton con flag `_initialized`.
- **Anti-pattern: MockDeepEvalLLM che ritorna sempre score=1.** Rende il gate sempre verde — non testa i threshold. Il mock deve restituire score variabili basati su un seed o su fixture pre-calcolato.
- **Anti-pattern: Langfuse OTLP path e CallbackHandler abilitati contemporaneamente.** Generano trace duplicate. Nella stack attuale usare solo il CallbackHandler LangChain (già wired); il path OTLP diretto è alternativo.
- **Anti-pattern: Grafana su porta 3000 come Langfuse.** Langfuse già usa la 3000 in obs.yml — Grafana deve usare la 3001.
- **Anti-pattern: bleach su Markdown strutturato.** `bleach.clean()` è progettato per HTML; applicarlo su Markdown puro può strip sintassi legittima. Usarlo come secondo strato dopo il denylist regex, non come sostituto.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Trace context serialization W3C | Formato traceparent manuale | `TraceContextTextMapPropagator` (opentelemetry-api) | Spec W3C esatta con flag, versione, validazione |
| Span batch export | HTTP POST manuale a Tempo | `BatchSpanProcessor` + `OTLPSpanExporter` | Buffer, retry, backpressure inclusi |
| HTML stripping da PDF | Parser regex custom | `bleach.clean(text, tags=[], strip=True)` | Mozilla bleach gestisce HTML malformato |
| LLM judge eval scoring | Logica scoring custom | `deepeval.metrics.AnswerRelevancy(model=mock)` | Threshold, assertion, pytest integration già built-in |
| Grafana dashboard JSON | Editor manuale | Grafana UI export + commit | Dashboard JSON generato da Grafana garantisce compatibilità schema |

---

## Runtime State Inventory

> Non applicabile come rename/refactor phase. Nessuna migrazione di dati esistenti richiesta.
> Unica eccezione: la migrazione SQL `014_extend_audit_phase11.sql` aggiunge il valore `RESTRICTED_DOC_ACCESS` al CHECK constraint su `audit.actions.action_type`.

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `audit.actions` CHECK constraint in TimescaleDB — mancano valori Phase 11 | Migration `014_extend_audit_phase11.sql` aggiunge `RESTRICTED_DOC_ACCESS` |
| Live service config | `langfuse-web:3000` già in obs.yml | Grafana deve usare porta 3001; documentato in .env.example |
| OS-registered state | Nessuno — nessun processo OS-registered introdotto | None — verified by codebase grep |
| Secrets/env vars | Nuove var: `OTEL_EXPORTER_OTLP_ENDPOINT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (già presenti in langfuse_callback.py come env read) | Aggiungere a `.env.example` nella sezione Phase 11 |
| Build artifacts | Nessun artifact stale — nessun rename | None |

---

## Common Pitfalls

### Pitfall 1: NATS nats-py non ha auto-instrumentation OTEL ufficiale
**What goes wrong:** Si cerca `opentelemetry-instrumentation-nats` su PyPI → non esiste come package stabile. [VERIFIED: PyPI — `pip index versions opentelemetry-instrumentation-nats` ritorna empty]
**Why it happens:** NATS JetStream è meno diffuso di Kafka/RabbitMQ nell'ecosistema OTEL Python.
**How to avoid:** Implementare il `NatsHeaderCarrier` manualmente (Pattern 1 sopra). È 20 righe di codice e zero dipendenze extra.
**Warning signs:** Se il piano include `pip install opentelemetry-instrumentation-nats` → STOP, il package non esiste.

### Pitfall 2: DeepEval/RAGAS richiedono LLM judge per la maggior parte delle metriche
**What goes wrong:** Eseguire `AnswerRelevancy`, `Faithfulness`, `HallucinationMetric` senza mock → tentano chiamata a OpenAI/Ollama → fallimento in CI senza API key o GPU.
**Why it happens:** DeepEval e RAGAS sono progettati per ambienti con LLM disponibile. Solo le metriche RAGAS non-LLM (string overlap, BLEU) sono genuinamente deterministiche.
**How to avoid:** Usare `MockDeepEvalLLM` (Pattern 4) per i test CI. Il golden fixture JSONL viene calcolato localmente con Ollama e committato — il CI lo usa come riferimento.
**Warning signs:** Test che passano sempre con score=1.0 → fixture mock non differenziante.

### Pitfall 3: Langfuse v3 CallbackHandler vs OTLP dual-path — trace duplicate
**What goes wrong:** Configurare sia `langfuse.langchain.CallbackHandler` che un OTLPExporter verso `http://langfuse-web:3000/api/public/otel` nello stesso processo → ogni span appare due volte in Langfuse.
**Why it happens:** Langfuse v3 accetta sia il path SDK proprietario che il path OTLP standard — sono due ingest indipendenti.
**How to avoid:** Usare solo il CallbackHandler (già implementato). Non aggiungere esporter OTLP verso Langfuse. L'OTLP exporter va verso Tempo per la trace stack generale.
**Warning signs:** Count span duplicati in Langfuse dashboard dopo aggiunta di OTEL exporter.

### Pitfall 4: Langfuse su porta 3000 + Grafana su porta 3000 = conflitto
**What goes wrong:** `obs.yml` mappa `langfuse-web` su `${LANGFUSE_PORT:-3000}:3000`. Se Grafana usa la stessa porta → `Error: address already in use`.
**Why it happens:** L'obs.yml esistente non include Grafana — il planner deve aggiungere Grafana su porta 3001.
**How to avoid:** `GRAFANA_PORT=3001` in `.env.example`; container Grafana mappa `${GRAFANA_PORT:-3001}:3000`.

### Pitfall 5: ClickHouse avvio lento — già documentato in obs.yml, non romperlo
**What goes wrong:** Modificare la sezione ClickHouse in obs.yml (es. rimuovere `start_period: 30s` o ridurre `retries: 20`) causa `langfuse-web` che tenta connessione prima che ClickHouse sia pronto.
**Why it happens:** ClickHouse impiega 30s+ per inizializzare sul cold start.
**How to avoid:** Non toccare i healthcheck ClickHouse esistenti in obs.yml. Aggiungere Grafana/Prometheus/Tempo come servizi separati senza toccare i service esistenti.

### Pitfall 6: bleach.clean() rimuove sintassi Markdown valida
**What goes wrong:** `bleach.clean("**bold** [link](url)", tags=[], strip=True)` → `"bold linkurl"` — rimuove le ancore.
**Why it happens:** bleach è HTML-aware, non Markdown-aware. Tratta `[...]` e `(...)` come testo ma `<a href>` come HTML.
**How to avoid:** Applicare `sanitize_document()` sul testo **estratto** dal parser (testo plain post-parse), non sul Markdown grezzo. Il `MarkdownParser.parse()` già restituisce `ParsedSection.text` come plain text.

### Pitfall 7: STRIDE doc — minaccia per categoria non per componente
**What goes wrong:** Produrre un documento STRIDE che lista 6 minacce tutte della categoria "Tampering" per il solo componente gateway → non soddisfa SC-4 che richiede ≥1 per categoria × 3 superfici.
**Why it happens:** I precedenti SECURITY.md (09/10) sono per-fase, non per-sistema. SEC-01 richiede un documento trasversale.
**How to avoid:** La struttura STRIDE doc deve avere una matrice: righe = categorie STRIDE (S/T/R/I/D/E), colonne = superfici (IT/OT boundary, RAG ingest, agent orchestration). 3×6 = 18 celle minime, ciascuna con almeno 1 threat + mitigation + codice mappato.

### Pitfall 8: ActionType CHECK constraint drift con migration
**What goes wrong:** Aggiungere `RESTRICTED_DOC_ACCESS` all'enum Python senza il corrispettivo nella migration SQL → runtime `CheckViolationError` quando il codice scrive la riga audit.
**Why it happens:** Pattern già documentato nell'enum (vedi commento "keep in lockstep with migration"). Phase 11 deve seguire lo stesso pattern delle fasi precedenti (014 migration).
**How to avoid:** Creare `014_extend_audit_phase11.sql` prima di qualsiasi codice che scrive `ActionType.RESTRICTED_DOC_ACCESS`.

---

## Code Examples

### Setup OTEL TracerProvider in lifespan gateway

```python
# Source: [CITED: opentelemetry-python SDK docs]
# apps/api-gateway/src/svc_api_gateway/lifespan.py (estensione)

from sft_agents.otel.provider import setup_tracer_provider

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_tracer_provider("sft-api-gateway")   # Phase 11: OTEL full init
    # ... resto del lifespan esistente ...
    yield
    # ... shutdown ...
```

### RAGAS non-LLM metrics (deterministiche)

```python
# Source: [CITED: docs.ragas.io/en/stable/concepts/metrics/overview/]
# tests/eval/test_rag_ci_gate.py

from ragas import evaluate
from ragas.metrics import context_precision, context_recall  # non-LLM
from datasets import Dataset

def test_rag_ci_gate(ground_truth_dataset):
    """OBS-05: Gate CI su metriche RAG non-LLM — deterministiche senza LLM judge."""
    result = evaluate(
        dataset=ground_truth_dataset,
        metrics=[context_precision, context_recall],
    )
    assert result["context_precision"] >= 0.75, f"Context precision below threshold: {result['context_precision']}"
    assert result["context_recall"] >= 0.70, f"Context recall below threshold: {result['context_recall']}"
```

### DeepEval Hallucination gate con MockLLM

```python
# Source: [CITED: deepeval.com/docs/metrics-introduction]
# tests/eval/test_rag_ci_gate.py

from deepeval import evaluate
from deepeval.metrics import HallucinationMetric
from deepeval.test_case import LLMTestCase

def test_hallucination_gate(mock_llm, test_cases):
    """OBS-05: Gate CI su hallucination rate ≤5% — usa MockDeepEvalLLM."""
    metric = HallucinationMetric(threshold=0.05, model=mock_llm)
    results = evaluate(test_cases, [metric])
    passed = sum(1 for r in results if r.success)
    rate = 1.0 - (passed / len(results))
    assert rate <= 0.05, f"Hallucination rate {rate:.1%} exceeds 5% threshold"
```

### Restricted-doc audit log in retrieval pipeline

```python
# Source: [ASSUMED — pattern basato su audit.py esistente in sft-agents]
# packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py

from sft_agents.models.enums import ActionType, Decision
from sft_agents.tools.audit import write_audit_record  # pattern esistente

async def retrieve_with_audit(query: str, principal: dict, ...) -> list[Chunk]:
    results = await qdrant_indexer.query(query, ...)
    restricted = [r for r in results if r.metadata.get("acl_level") == "restricted"]
    if restricted:
        await write_audit_record(
            action_type=ActionType.RESTRICTED_DOC_ACCESS,
            decision=Decision.LOGGED,
            principal_id=principal.get("sub", "unknown"),
            details={"chunk_ids": [r.id for r in restricted], "query_hash": hashlib.sha256(query.encode()).hexdigest()[:16]},
        )
    return results
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Langfuse v2: `session_id` in CallbackHandler constructor | Langfuse v3: `session_id` in `config["metadata"]` (Pitfall §11 già documentato in langfuse_callback.py) | Langfuse 3.0 (2024) | Già implementato correttamente — non breaking |
| RAGAS: sempre LLM-based | RAGAS 0.4+: metriche non-LLM disponibili (context_precision/recall) | RAGAS 0.3+ | Permette CI gate deterministico senza LLM |
| DeepEval: solo judge esterno | DeepEval 3.x+: `DeepEvalBaseLLM` subclassabile per mock | DeepEval 3.0 (2024) | Mock LLM per CI riproducibile |
| Grafana v8: provisioning YAML manuale | Grafana v11: provisioning JSON dashboard + YAML datasource (stessa API, più feature) | Grafana 9+ | Dashboard JSON più robusto |
| OTEL Python SDK 1.x: propagazione solo HTTP | OTEL Python SDK 1.40+: propagazione carrier agnostica (funziona per NATS con carrier manuale) | OTel 1.0 stable (2021) | NatsHeaderCarrier è pattern standard |

**Deprecated/outdated:**
- Langfuse Python SDK v2 `CallbackHandler(session_id=...)`: rimosso in v3. Il codice esistente in `langfuse_callback.py` è già corretto per v3.
- RAGAS `answer_relevancy` metric come unico gate: richiede LLM, non deterministico in CI. Usare `context_precision` + `context_recall` come metriche non-LLM per il gate.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | RAGAS `context_precision` e `context_recall` sono metriche non-LLM-based in versione 0.4.x | Standard Stack + Pattern 3 | Se richiedessero LLM → CI gate non deterministico; soluzione: verificare source RAGAS docs prima di implementare |
| A2 | `opentelemetry-instrumentation-nats` non esiste su PyPI come package ufficiale stabile | Pitfall 1 | Se esistesse → potremmo usarlo invece del NatsHeaderCarrier manuale; soluzione: verificare con `pip index versions` prima del Wave 0 |
| A3 | Langfuse self-hosted v3 non richiede parametri aggiuntivi nell'obs.yml per esporre l'endpoint OTLP `/api/public/otel` | Pattern 3 | Se richiedesse config extra → serve environment variable aggiuntiva in obs.yml |
| A4 | Il pattern `write_audit_record` da `sft_agents.tools.audit` è riutilizzabile nel retrieval pipeline di sft-knowledge senza dipendenza circolare | Pattern 8 + SEC-07 | Se ci fosse dipendenza circolare → serve un evento NATS o chiamata asincrona per l'audit |
| A5 | Grafana v11.x (immagine `grafana/grafana:11.3.1`) è disponibile su Docker Hub | Standard Stack + Pattern 5 | Se non disponibile → usare latest o tag precedente verificato |

---

## Open Questions (RESOLVED — AR-07 doc-only in 11-05; Langfuse OTLP auth + RAGAS determinism are 11-00 acceptance steps; migration 014 follows the 010/012 lockstep pattern)

1. **Redis rate-limiter (AR-07)**
   - What we know: AR-07 (10-SECURITY.md) ha accettato il rate-limit in-process con `RuntimeWarning` se `WEB_CONCURRENCY>1`. CONTEXT.md deferred la Redis-based rate-limit ma dice "se scoped dal planner".
   - What's unclear: Il planner deve decidere se includerlo in questa fase o solo documentarlo.
   - Recommendation: Includere come piano opzionale Wave 4 (documentazione + config env `RATE_LIMIT_BACKEND=redis`) senza implementazione — chiude AR-07 come "documentato".

2. **Langfuse OTLP endpoint con auth self-hosted**
   - What we know: Il cloud Langfuse richiede `Authorization: Basic pk:sk` sull'endpoint OTLP. Non è chiaro se il self-hosted richieda la stessa auth o nessuna (interno compose network).
   - What's unclear: Configurazione auth per `langfuse-web:3000/api/public/otel` in dev compose.
   - Recommendation: Testare con `curl -X POST http://localhost:3000/api/public/otel` nel Wave 0 e documentare il risultato. [ASSUMED — non verificato in questo research]

3. **Migration 014 e PostgreSQL CHECK constraint estensibility**
   - What we know: I CHECK constraint esistenti (es. `012_extend_audit_scm.sql`) usano `IN (...)` statico. Aggiungere `RESTRICTED_DOC_ACCESS` richiede ALTER TABLE + DROP/ADD CONSTRAINT (non compatibile con LOCK in produzione).
   - What's unclear: Il pattern di migration usato nelle fasi precedenti gestisce già questo (migrate.py).
   - Recommendation: Seguire il pattern delle migration 009/010/012 esistenti. Verificare se migrate.py supporta transazioni ANSI.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Tutti i pacchetti Python | ✓ | 3.12 (da CI config) | — |
| Docker | obs.yml Langfuse + Grafana | ✓ | (infra esistente) | — |
| `deepeval` | OBS-05 CI gate | ✗ (non in uv.lock) | 4.0.3 disponibile | Nessuno — richiesto |
| `ragas` | OBS-05 CI gate | ✗ (non in uv.lock) | 0.4.3 disponibile | Nessuno — richiesto |
| `bleach` | SEC-04 sanitization | ✗ (non in uv.lock) | 6.3.0 disponibile | Regex puro (meno robusto) |
| `opentelemetry-exporter-otlp-proto-grpc` | OBS-02 OTEL full stack | ✗ (non in api-gateway pyproject) | 1.42.1 disponibile | HTTP exporter |
| Grafana image | OBS-03/04 | ✗ (non in obs.yml) | grafana/grafana:11.x su Docker Hub | — |
| Prometheus image | OBS-03/04 | ✗ (non in obs.yml) | prom/prometheus:v2.53.x | — |
| Tempo image | OBS-02/03 | ✗ (non in obs.yml) | grafana/tempo:2.6.x | — |
| `opentelemetry-instrumentation-nats` | OBS-02 NATS propagation | ✗ (NON esiste su PyPI) | N/A | NatsHeaderCarrier manuale (Pattern 1) |

**Missing dependencies with no fallback:**
- `deepeval`, `ragas` — richiesti per OBS-05/06; blocchi se assenti nel CI gate.

**Missing dependencies with fallback:**
- `bleach` — fallback regex puro (accettabile per fase MVP; bleach preferito per robustezza).
- `opentelemetry-exporter-otlp-proto-grpc` — fallback `opentelemetry-exporter-otlp-proto-http`.
- `opentelemetry-instrumentation-nats` — NON ESISTE; fallback = NatsHeaderCarrier manuale (30 righe, zero deps).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 0.24 |
| Config file | `pyproject.toml` [tool.pytest.ini_options] — `asyncio_mode = "auto"` |
| Quick run command | `uv run pytest tests/eval/ tests/security/ -x -q` |
| Full suite command | `uv run pytest tests/ -x` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OBS-02 | Trace ID propagato NATS | integration | `pytest tests/test_otel_nats_propagation.py` | ❌ Wave 0 |
| OBS-05 | Gate CI hallucination ≤5%, relevance ≥0.75 | unit (mock LLM) | `pytest tests/eval/test_rag_ci_gate.py` | ❌ Wave 1 |
| OBS-06 | 30+ scenari agente ground truth | unit (mock LLM) | `pytest tests/eval/test_agent_eval.py` | ❌ Wave 1 |
| SEC-03 | Ruolo auditor bloccato su endpoint non-autorizzati | unit | `pytest apps/api-gateway/tests/test_rbac_auditor.py` | ❌ Wave 2 |
| SEC-04 | Crafted PDF sanitizzato, nessuna agent action influenzata | unit | `pytest tests/security/test_prompt_injection.py` | ❌ Wave 2 |
| SEC-06 | Write command OT Bridge bloccato (AST check) | unit | `pytest tests/security/test_ot_bridge_guard.py` | ❌ Wave 2 |
| SEC-07 | Accesso chunk restricted → audit row `RESTRICTED_DOC_ACCESS` | unit | `pytest packages/sft-knowledge/tests/test_restricted_audit.py` | ❌ Wave 2 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/eval/ tests/security/ -x -q --tb=short`
- **Per wave merge:** `uv run pytest tests/ -x`
- **Phase gate:** Full suite green prima di `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `packages/sft-agents/src/sft_agents/otel/__init__.py` + `provider.py` + `nats_carrier.py`
- [ ] `tests/test_otel_nats_propagation.py` — smoke test inject/extract
- [ ] `tests/eval/conftest.py` — `MockDeepEvalLLM` fixture + `ground_truth_dataset` fixture
- [ ] `tests/eval/dataset/ground_truth.jsonl` — 30+ scenari (estende `tests/data/rag_eval/testset.jsonl`)
- [ ] `infra/grafana/provisioning/datasources/datasources.yaml`
- [ ] `infra/grafana/provisioning/dashboards/dashboards.yaml`
- [ ] `infra/compose/obs.yml` — aggiungere Grafana + Prometheus + Tempo

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | JWT HS256 esistente (Phase 10) — Phase 11 aggiunge `auditor` role |
| V3 Session Management | partial | Dev-mode localStorage (AR-03 accepted) — HttpOnly cookie deferred |
| V4 Access Control | yes | `require_roles()` FastAPI dependency — estendere con auditor |
| V5 Input Validation | yes | `sanitize_document()` + pydantic `extra=forbid` |
| V6 Cryptography | no | Nessuna nuova crittografia in Phase 11 |
| V9 Data Protection | yes | Audit log accesso restricted — RESTRICTED_DOC_ACCESS ActionType |
| V10 Malicious Code | yes | Prompt-injection sanitization (SEC-04) |

### STRIDE Surfaces e Threat Mapping (SEC-01 — struttura minima richiesta)

Il documento `docs/security/STRIDE-threat-model.md` deve coprire le seguenti celle:

| STRIDE | IT/OT Boundary | RAG Ingest | Agent Orchestration |
|--------|---------------|------------|---------------------|
| **Spoofing** | Agente OT Bridge si spaccia per OPC-UA write client | Documento malevolo si spaccia per SOP autentico (provenance falsa) | JWT forged per accedere a endpoint agent come admin |
| **Tampering** | Messaggio NATS modificato in transito → sensore spoofed | Chunk RAG alterato post-ingest (Qdrant access) | LangGraph state manipolato via checkpoint replay malicious |
| **Repudiation** | Bridge stop senza audit (audit.ot.bridge già mitiga) | Ingest senza audit trail (IngestState mitiga) | Decisione HITL senza motivazione obbligatoria (MOTIVATION_MIN=10 mitiga) |
| **Information Disclosure** | Sensore restricted letto da operatore non autorizzato | Chunk `restricted` esposto a utente `public` (acl_level enforcement) | Token count LLM esposto in trace pubblica |
| **Denial of Service** | Flood di messaggi NATS dall'OT Bridge → queue exhaustion | Ingest bomb (documenti enormi → OOM embedder) | Recursion limit assente → infinite agent loop |
| **Elevation of Privilege** | OT Bridge ottiene path write verso OPC-UA (SEC-06 copre) | Prompt-injection nel documento → LLM esegue tool non autorizzato | JWT con ruolo `auditor` accede a endpoint `admin` |

**Mitigazioni già implementate da fasi precedenti (da citare nel STRIDE doc):**
- IT/OT: `opcua_client.py` subscribe-only (D-51) + AST guard test (SEC-06)
- RAG: `acl_level` enforcement in retrieval (KNW-06) + audit restricted (SEC-07)
- Agent: `recursion_limit=25` (CORE-03) + HITL approval chain + MOTIVATION_MIN=10

### Known Threat Patterns per Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Prompt injection via PDF | Tampering | `sanitize_document()` denylist + bleach (SEC-04) |
| Sensitive info leak via RAG | Information Disclosure | `acl_level` Qdrant filter + `RESTRICTED_DOC_ACCESS` audit |
| Supply chain LLM dependency | Tampering | `langfuse>=3,<4` version pin; `uv.lock` deterministic |
| Token auth in URL (SSE) | Information Disclosure | AR-02 accepted (dev); HttpOnly cookie deferred Phase 11 nota |
| Multi-worker rate-limit bypass | Denial of Service | AR-07 documented; Redis distribuito deferred |
| OT Bridge write injection | Elevation of Privilege | AST guard test (SEC-06) + subscribe-only design (D-51) |

---

## Proposed Wave Decomposition

### Wave 0 — Infra OTEL + Langfuse endpoint + Grafana compose (prerequisito bloccante)
**File modificati:** `infra/compose/obs.yml`, `infra/compose/.env.example`, `packages/sft-agents/src/sft_agents/otel/` (nuovo package), `packages/sft-agents/pyproject.toml` (aggiunge OTLP exporter)
**Obiettivo:** OTEL TracerProvider funzionante con OTLP export verso Tempo; Grafana + Prometheus + Tempo disponibili via `docker compose -f obs.yml up`; `NatsHeaderCarrier` implementato e testato.

### Wave 1 — OTEL propagation end-to-end (OBS-02)
**File modificati:** `apps/api-gateway/src/svc_api_gateway/lifespan.py` (setup_tracer_provider), `apps/api-gateway/src/svc_api_gateway/routers/` (inject NATS header), `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py` (tag "phase11"), agent runner files (extract NATS header + attach ctx)
**Prerequisito:** Wave 0

### Wave 2 — DeepEval + RAGAS CI gate (OBS-05, OBS-06)
**File modificati:** `tests/eval/conftest.py` (MockDeepEvalLLM), `tests/eval/test_rag_ci_gate.py`, `tests/eval/test_agent_eval.py`, `tests/eval/dataset/ground_truth.jsonl` (30+ scenari), `.github/workflows/ci.yml` (aggiungere step eval gate), root `pyproject.toml` (aggiungere deepeval+ragas a dev deps)
**Prerequisito:** nessuno (indipendente da Wave 1)

### Wave 3 — Security hardening (SEC-01..07)
**File modificati (disgiunti da Wave 1/2):**
- `packages/sft-agents/src/sft_agents/models/enums.py` (RESTRICTED_DOC_ACCESS)
- `infra/migrations/timescale/014_extend_audit_phase11.sql` (CHECK constraint)
- `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py` (nuovo)
- `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py` (inject sanitizer)
- `apps/api-gateway/src/svc_api_gateway/security/jwt.py` (aggiunge auditor@mantis.it)
- `infra/compose/.env.example` (nuovi segreti Phase 11)
- `tests/security/test_prompt_injection.py` (crafted PDF → assert)
- `tests/security/test_ot_bridge_guard.py` (SEC-06 AST check)
- `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py` (audit restricted)
- `docs/security/STRIDE-threat-model.md` (SEC-01 documento)
**Prerequisito:** nessuno (indipendente da Wave 1/2 per i file SEC; dipende da Wave 0 per il testing)

### Wave 4 — Grafana dashboards JSON (OBS-04, OBS-07)
**File modificati:** `infra/grafana/provisioning/dashboards/*.json` (agent-kpis, factory-kpis, cost-dashboard)
**Prerequisito:** Wave 0 (Grafana deve essere up per generare i JSON via export UI)

### Wave 5 — .env.example consolidato + STRIDE completo + review finale
**File modificati:** `infra/compose/.env.example` (aggiunta variabili Grafana/OTEL/Langfuse Phase 11), `docs/security/STRIDE-threat-model.md` (completamento con mitigazioni code-mapped), `.planning/phases/10-backend-api-frontend/10-SECURITY.md` (annotazione chiusura AR-01..07)
**Prerequisito:** Tutte le wave precedenti

---

## Sources

### Primary (HIGH confidence)
- `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py` — Langfuse v3 CallbackHandler wiring esistente (letto direttamente)
- `infra/compose/obs.yml` — Langfuse v3 compose topology esistente (letto direttamente)
- `packages/sft-agents/src/sft_agents/models/enums.py` — ActionType pattern esistente (letto direttamente)
- `services/ot-bridge/src/svc_ot_bridge/opcua_client.py` — D-51 subscribe-only guard (letto direttamente)
- `apps/api-gateway/src/svc_api_gateway/main.py` — FastAPIInstrumentor Phase 10 (letto direttamente)
- PyPI `pip index versions` — deepeval 4.0.3, ragas 0.4.3, opentelemetry-sdk 1.42.1, bleach 6.3.0 (verificati)
- [CITED: opentelemetry.io/docs/languages/python/propagation/] — inject/extract pattern W3C traceparent
- [CITED: deepeval.com/docs/metrics-introduction] — `DeepEvalBaseLLM` subclass per mock LLM
- [CITED: grafana.com/docs grafana provisioning] — datasources + dashboard volume provisioning

### Secondary (MEDIUM confidence)
- [CITED: docs.ragas.io/en/stable/concepts/metrics/overview/] — metriche non-LLM vs LLM-based
- [CITED: langfuse.com/faq/all/existing-otel-setup] — Langfuse OTLP endpoint path
- [CITED: owasp.org/www-project-top-10-for-large-language-model-applications/] — OWASP LLM Top-10 2025
- oneuptime.com/blog (2026-02-06) — NATS OTEL trace propagation pattern (Go; adattato a Python)

### Tertiary (LOW confidence)
- Comportamento di `context_precision`/`context_recall` come metriche non-LLM in RAGAS 0.4.x — [ASSUMED] basato su documentazione API overview; verificare in Wave 1 con `ragas --version` test.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — versioni verificate via PyPI
- Architecture patterns: HIGH — basate su codebase reale letto + documentazione ufficiale
- Eval determinism: MEDIUM — MockDeepEvalLLM è pattern documentato ma l'esatto comportamento RAGAS non-LLM non è stato testato
- Pitfalls: HIGH — derivati da codebase reale + documentazione ufficiale
- STRIDE structure: HIGH — requisiti SC-4 espliciti nel ROADMAP

**Research date:** 2026-05-24
**Valid until:** 2026-06-24 (30 giorni — stack stabile; Langfuse SDK in beta OTEL può cambiare più rapidamente)
