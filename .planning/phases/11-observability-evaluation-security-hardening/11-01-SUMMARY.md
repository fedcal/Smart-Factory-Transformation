---
phase: 11-observability-evaluation-security-hardening
plan: "01"
subsystem: otel-trace-propagation
tags:
  - otel
  - nats-propagation
  - traceparent
  - langfuse
  - consumer-span
  - phase11-tag
dependency_graph:
  requires:
    - "11-00: sft_agents.otel (NatsHeaderCarrier + setup_tracer_provider)"
  provides:
    - "svc_api_gateway.nats_publisher (publish_agent_command con inject traceparent)"
    - "sft_agents.runtime.agent_runner (handle_agent_command con extract + CONSUMER span)"
    - "langfuse_callback con tag phase11 additivo"
    - "lifespan con setup_tracer_provider('sft-api-gateway')"
  affects:
    - "11-02: eval gate (usa langfuse con tag phase11 per filtraggio traces)"
    - "11-03: security (agent_runner è punto di aggancio per audit CONSUMER)"
tech_stack:
  added: []
  patterns:
    - "publish_agent_command(publish_fn, subject, payload) — inject W3C traceparent via NatsHeaderCarrier prima del publish NATS"
    - "handle_agent_command(msg, tracer, process_fn) — extract traceparent, attach context, CONSUMER span, detach in finally"
    - "build_invocation_metadata con tag 'phase11' additivo (non rimuove 'phase4')"
    - "setup_tracer_provider best-effort in lifespan (singleton-guarded, OBS-02)"
key_files:
  created:
    - apps/api-gateway/src/svc_api_gateway/nats_publisher.py
    - packages/sft-agents/src/sft_agents/runtime/agent_runner.py
    - apps/api-gateway/tests/test_otel_propagation_e2e.py
  modified:
    - apps/api-gateway/src/svc_api_gateway/lifespan.py (setup_tracer_provider nel lifespan)
    - packages/sft-agents/src/sft_agents/llm/langfuse_callback.py (tag phase11)
    - packages/sft-agents/tests/test_langfuse_callback.py (test_phase11_tag_always_present)
decisions:
  - "publish_agent_command è sync (non async) per facilitare il testing con fake callables; publish_agent_command_async è la variante per nats-py reale"
  - "handle_agent_command è sync con process_fn callable — la caller responsabile dell'await per codice async; pattern più testabile"
  - "setup_tracer_provider nel lifespan è best-effort (try/except) — OTEL failure non deve impedire al gateway di avviarsi (Phase 10 pattern)"
  - "tag 'phase11' aggiunto in build_invocation_metadata (non in build_invocation_config) — unico punto canonico di modifica"
  - "nessun OTLP exporter verso Langfuse — solo CallbackHandler (RESEARCH Pitfall 3: evita trace duplicate)"
  - "nats_publisher.py nel gateway, non in sft_agents — dependency direction corretta (gateway conosce sft_agents, non viceversa)"
metrics:
  duration: "6 minuti"
  completed_date: "2026-05-25"
  tasks_completed: 2
  files_created: 3
  files_modified: 3
---

# Phase 11 Plan 01: OTEL Trace Propagation E2E (Gateway → NATS → Agent → Langfuse) Summary

**One-liner:** Propagazione W3C traceparent gateway→NATS→agent via NatsHeaderCarrier con CONSUMER span e tag phase11 su Langfuse CallbackHandler; test e2e asserta trace_id identico publisher/consumer.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 RED | TDD RED — test e2e inject + provider | ee95e79 | tests/test_otel_propagation_e2e.py |
| 1 GREEN | Init TracerProvider lifespan + inject traceparent publish NATS | 122f672 | lifespan.py, nats_publisher.py |
| 2 RED | TDD RED — test phase11 tag Langfuse | c19a6d6 | test_langfuse_callback.py |
| 2 GREEN | Extract + CONSUMER span agent_runner + tag phase11 | ac1c788 | agent_runner.py, langfuse_callback.py |

## Acceptance Verifications

### Verifica e2e traceparent propagation

```
uv run pytest apps/api-gateway/tests/test_otel_propagation_e2e.py -x -q
3 passed in 0.28s
```

Test verificati:
- `test_tracer_provider_service_name` — service.name="sft-api-gateway" PASSED
- `test_publish_agent_command_injects_traceparent` — header W3C valido PASSED
- `test_consumer_extract_same_trace_id` — trace_id publisher == consumer PASSED

### Verifica tag phase11 Langfuse

```
uv run pytest packages/sft-agents/tests/test_langfuse_callback.py -x -q
12 passed in 2.49s
```

Test aggiunto:
- `test_phase11_tag_always_present` — "phase11" in tags, "phase4" preservato PASSED

## Deviations from Plan

### Auto-fixed Issues

Nessuna auto-fix necessaria.

### Nota su architettura publisher

Il piano fa riferimento a un `nats_publisher.py` come modulo separato. Nel gateway esistente il publish NATS è via `AuditNatsPublisher.publish_raw()` (per eventi di dominio come QualityEvent) e il `supervisor_graph.ainvoke()` (per i comandi agent, direttamente in-process senza NATS). 

Il modulo `nats_publisher.py` creato fornisce `publish_agent_command(publish_fn, subject, payload)` — un wrapper generico che inietta il traceparent in qualsiasi publish NATS. La `publish_agent_command_async(nats_js, subject, payload)` è la variante per il publish diretto su JetStream. Questo copre sia i publish di comandi agent futuri che i publish di eventi di dominio che richiedono traceparent.

### Nota su agent_runner.py

Il piano indica `packages/sft-agents/src/sft_agents/runtime/agent_runner.py` come modulo che estrae il traceparent. Il modulo creato fornisce `handle_agent_command(msg, tracer, process_fn)` — callback adattabile a qualsiasi consumer NATS (QualityInspector, shift-handover consumer, downtime-analyzer consumer). La firma è generica e compatibile con tutti i pattern consumer esistenti (`_process_one` in `nats_consumer.py`).

## TDD Gate Compliance

- RED gate Task 1: commit `ee95e79` (test fallente ModuleNotFoundError su nats_publisher)
- GREEN gate Task 1: commit `122f672` (3 test verdi)
- RED gate Task 2: commit `c19a6d6` (test fallente AssertionError su phase11 tag)
- GREEN gate Task 2: commit `ac1c788` (tutti 15 test verdi)
- REFACTOR: non necessario (codice conforme alle coding-style rules, funzioni < 50 righe)

## Known Stubs

Nessuno — il publish_agent_command e handle_agent_command sono implementazioni complete. Il wiring reale con i consumer NATS esistenti (quality-inspector, shift-handover) avverrà nei piani futuri che estenderanno i consumer con handle_agent_command.

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: traceparent_in_headers | apps/api-gateway/src/svc_api_gateway/nats_publisher.py | Header NATS traversano il broker — tamperabile (T-11-01-01: mitigato da TraceContextTextMapPropagator W3C con validazione formato inclusa; header è solo correlazione non controllo accesso) |

## Self-Check

File creati esistenti: 3/3 FOUND
Commit esistenti: 4/4 FOUND (ee95e79, 122f672, c19a6d6, ac1c788)
package.json/package-lock.json UNCHANGED: verificato (piano tocca solo Python)
.claude/ non staged: verificato

## Self-Check: PASSED
