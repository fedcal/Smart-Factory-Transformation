---
tags:
  - security
  - stride
  - threat-model
---

# STRIDE Threat Model

!!! info "Authoritative source (single source of truth)"
    This page faithfully reproduces the STRIDE model consolidated in **Phase 11**
    (`docs/security/STRIDE-threat-model.md`, v1.0, 2026-05-25). The source is the
    project's cross-cutting security contract: every change must be made there and
    re-published here to avoid divergence (DOC-11, SC-4).

Cross-cutting STRIDE model: 6 categories × 3 surfaces = **18 cells**.
Each cell states the threat, the implemented mitigation and the source-code reference.

Consolidates the per-phase registers:

- **Phase 08:** ShiftHandover, TrainingCoach, KnowledgeCurator, DocumentationSynthesizer
- **Phase 09:** InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster (Phase 09 security register)
- **Phase 10:** API Gateway, SSE, Angular UI, HITL approvals (Phase 10 security register)

---

## Analyzed Surfaces

| ID | Surface | Description |
|----|---------|-------------|
| S1 | **IT/OT boundary** | Boundary between the IT network (NATS, API Gateway, AI) and the OT network (OPC-UA / PLC). Data-diode via Docker network. |
| S2 | **RAG ingest** | Document ingestion pipeline: parse → sanitization → chunking → embedding → Qdrant. |
| S3 | **Agent orchestration** | LangGraph supervisor + agent cluster: routing, HITL interrupt, audit, budget control. |

---

## STRIDE Matrix 6×3

### S — Spoofing

#### S1: IT/OT boundary — Spoofing

| Field | Value |
|-------|-------|
| **Threat** | An IT attacker sends fake OPC-UA data on the NATS network impersonating the OT Bridge, poisoning the TimescaleDB time-series. |
| **Mitigation** | The OT Bridge is the only authorized publisher on `sensor.*`. The Docker network boundary isolates the OT segment (D-51). The NATS subject is derived from the normalized asset ID, not mutable at runtime. |
| **Mapped code** | `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:NatsPublisher.publish` — subject derived from `normalizer.derive_subject(asset_id, metric)`, not user input. |
| **Register provenance** | Phase 10 security register (Tampering supply-chain, adapted) |

#### S2: RAG ingest — Spoofing

| Field | Value |
|-------|-------|
| **Threat** | A malicious document impersonates an authoritative source (e.g. an official SOP) to manipulate RAG answers. |
| **Mitigation** | The parser binds each chunk to `source_uri` and `acl_level` at ingest time. `source_uri` is not writable by the end user — it is set by the authenticated ingest operator. |
| **Mapped code** | `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:IngestPipeline.ingest` — `source_uri` derived from the document path, not from document metadata. |
| **Register provenance** | New (Phase 11, SEC-01) |

#### S3: Agent orchestration — Spoofing

| Field | Value |
|-------|-------|
| **Threat** | An unauthenticated client invokes agent endpoints (`/v1/approvals`, `/agents/*`) spoofing an elevated role in the request body. |
| **Mitigation** | `require_roles()` decodes the HS256-signed JWT and extracts the `role` claim. The body is ignored for authorization. A secret guard in `jwt.py` (lines 38-53) ensures `API_SECRET_KEY` is present in production. |
| **Mapped code** | `apps/api-gateway/src/svc_api_gateway/security/jwt.py:decode_token` + `apps/api-gateway/src/svc_api_gateway/security/rbac.py:require_roles` |
| **Register provenance** | Phase 10 security register (JWT HS256, require_roles) |

---

### T — Tampering

#### T1: IT/OT boundary — Tampering

| Field | Value |
|-------|-------|
| **Threat** | An IT component attempts to write OPC-UA values to the PLC (write-back command), bypassing the data-diode. |
| **Mitigation** | The OT Bridge uses asyncua in subscriber-only mode (D-51). The SC-5 AST test verifies at every CI run that no ot-bridge module calls `write_value`, `call_method`, `set_attribute`, or `write_attributes`. |
| **Mapped code** | `tests/security/test_ot_bridge_guard.py:test_ot_bridge_has_no_write_api_calls` — AST walk over `services/ot-bridge/src/svc_ot_bridge/*.py`. |
| **Register provenance** | Phase 08 (D-51 data-diode, 11-03 SEC-06) |

#### T2: RAG ingest — Tampering

| Field | Value |
|-------|-------|
| **Threat** | A malicious document contains prompt-injection instructions (e.g. "Ignore previous instructions") that survive parsing and reach the embedder or the LLM. |
| **Mitigation** | `sanitize_document()` applies a deterministic regex denylist (7 patterns) + `bleach.clean(tags=[], strip=True)` on the post-parse plain text. No imperative instruction survives (SC-3). |
| **Mapped code** | `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py:sanitize_document` |
| **Register provenance** | Phase 10 security register (adapted); Phase 11 SEC-04 |

#### T3: Agent orchestration — Tampering

| Field | Value |
|-------|-------|
| **Threat** | An agent mutates its own LangGraph state to bypass the HITL checkpoint and self-approve. |
| **Mitigation** | The HITL flow uses native LangGraph `interrupt()`: the agent cannot resume without the API resume-payload. An `AuditRecord` is written post-interrupt with `Decision.SIGNOFF` signed by the JWT principal. |
| **Mapped code** | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` — mandatory `recursion_limit` + interrupt semantics. |
| **Register provenance** | Phase 09 security register (HITL audit) |

---

### R — Repudiation

#### R1: IT/OT boundary — Repudiation

| Field | Value |
|-------|-------|
| **Threat** | An operator denies having read OT-derived restricted data sent on the IT network without leaving an audit trace. |
| **Mitigation** | W3C traceparent propagated via `NatsHeaderCarrier` (OTEL). Every NATS span is traced in Langfuse and Tempo. Trace-to-audit correlation allows reconstructing the full flow. |
| **Mapped code** | `packages/sft-agents/src/sft_agents/otel/nats_carrier.py:NatsHeaderCarrier` — inject/extract W3C traceparent on NATS headers. |
| **Register provenance** | Phase 11 11-01 (NatsHeaderCarrier OTEL propagation) |

#### R2: RAG ingest — Repudiation

| Field | Value |
|-------|-------|
| **Threat** | An ingest operator uploads a document and later denies having ingested it or having modified the metadata. |
| **Mitigation** | The ingest pipeline writes an `AuditRecord` with `ActionType.RESTRICTED_DOC_ACCESS` and a SHA-256 `query_hash` for every restricted-chunk access. `source_uri` and `acl_level` are immutable post-ingest (Qdrant payload). |
| **Mapped code** | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:RetrievalPipeline._write_restricted_audit` — RESTRICTED_DOC_ACCESS audit row with query_hash. |
| **Register provenance** | Phase 11 SEC-07, T-11-03-04 |

#### R3: Agent orchestration — Repudiation

| Field | Value |
|-------|-------|
| **Threat** | An operator approves or rejects a HITL action and denies having done so, or denies the motivation provided. |
| **Mitigation** | `MOTIVATION_MIN_LENGTH = 10` (frontend enforcement). The backend writes an `AuditRecord` with `decision`, `motivation`, `decision_actor` = JWT sub. An E2E test asserts the audit record exists post-approval. |
| **Mapped code** | `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:MOTIVATION_MIN_LENGTH` + Phase 10 security register |
| **Register provenance** | Phase 10 security register (MOTIVATION_MIN, audit) |

---

### I — Information Disclosure

#### I1: IT/OT boundary — Information Disclosure

| Field | Value |
|-------|-------|
| **Threat** | Sensitive OT data (setpoints, confidential machine states) leaks from the OT network to unauthorized IT clients via NATS. |
| **Mitigation** | The NATS subject `sensor.*` is consumed only by the API Gateway with an authenticated role. The OT Bridge exposes no HTTP endpoint; only the gateway publishes to clients. The Docker network separates the segments. |
| **Mapped code** | `services/ot-bridge/src/svc_ot_bridge/nats_publisher.py:NatsPublisher` — publishes only on `sensor.{asset_id}.{metric}` with no HTTP endpoint. |
| **Register provenance** | Phase 11 (D-51 data-diode boundary) |

#### I2: RAG ingest — Information Disclosure

| Field | Value |
|-------|-------|
| **Threat** | `restricted` document chunks (e.g. patents, confidential SOPs) are returned to users with the `operator` role that lacks ACL access. |
| **Mitigation** | `build_acl_filter()` applies an in-engine Qdrant pre-filter based on `ROLE_TO_ACL` (operator → `public` only). The filter is engine-side, not a Python post-filter — not bypassable. Fail-closed if no role maps. |
| **Mapped code** | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` — `Filter(must=[FieldCondition(key="acl_level", match=MatchAny(any=sorted(allowed)))])` |
| **Register provenance** | Phase 05 T-05-09-01; Phase 11 SEC-07 |

#### I3: Agent orchestration — Information Disclosure

| Field | Value |
|-------|-------|
| **Threat** | An agent error exposes a stack trace, LLM model details or internal state data in the API response body. |
| **Mitigation** | `_handle_agent_error()` returns `{"error":"internal_agent_error"}` — no `str(exc)` in the body. Details are logged server-side via structlog only. The same pattern applies in auth, kpi, sse. |
| **Mapped code** | `apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py:_handle_agent_error` (lines 320-334) + Phase 10 security register |
| **Register provenance** | Phase 09 security register; Phase 10 security register |

---

### D — Denial of Service

#### D1: IT/OT boundary — Denial of Service

| Field | Value |
|-------|-------|
| **Threat** | An attacker floods the NATS bridge with fake high-frequency messages, saturating the queue and blocking legitimate OT data. |
| **Mitigation** | The NATS bridge uses a bounded internal queue. Excess messages are dropped with a `opcua_queue_full_drop` log. The OPC-UA subscription is read-only — no feedback to the PLC. |
| **Mapped code** | `services/ot-bridge/src/svc_ot_bridge/opcua_client.py:OpcUaClient` — bounded queue with `opcua_queue_full_drop` log. |
| **Register provenance** | Phase 08 (D-51, bounded OT bridge queue) |

#### D2: RAG ingest — Denial of Service

| Field | Value |
|-------|-------|
| **Threat** | A massive document upload (huge files or ingest loop) blocks the ingest worker by exhausting CPU/memory, making the service unavailable. |
| **Mitigation** | The knowledge-ingest service has an in-process rate limit and processes one document at a time in the lifespan. File size can be limited by the reverse proxy (Nginx max_body_size). |
| **Mapped code** | `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:IngestPipeline.ingest` — sequential processing; the FastAPI gateway limits body size via `max_request_body_size`. |
| **Register provenance** | Phase 11 (new, SEC-01) |

#### D3: Agent orchestration — Denial of Service

| Field | Value |
|-------|-------|
| **Threat** | A LangGraph agent enters an infinite loop (recursion), exhausts CPU and blocks other supervisor threads. |
| **Mitigation** | `recursion_limit=25` is mandatory in every `build_invocation_config()`. The supervisor raises `GraphRecursionError → 503` if the limit is exceeded. `_RECURSION_LIMIT=5` in supply clusters (more conservative). |
| **Mapped code** | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` — `"recursion_limit": 25` hardcoded as default. |
| **Register provenance** | Phase 09 security register; Phase 11 CORE-03 |

---

### E — Elevation of Privilege

#### E1: IT/OT boundary — Elevation of Privilege

| Field | Value |
|-------|-------|
| **Threat** | An IT process gains write access to the OT network (e.g. sending commands to a PLC via OPC-UA) bypassing the data-diode. |
| **Mitigation** | The SC-5 AST guard (CI test) verifies that no ot-bridge module calls the OPC-UA write APIs. The `ot-net` Docker network is separate from `it-net`; only the OT Bridge can access both (D-51). |
| **Mapped code** | `tests/security/test_ot_bridge_guard.py:test_ot_bridge_has_no_write_api_calls` — AST walk + frozenset WRITE_PATTERNS. |
| **Register provenance** | Phase 11 SEC-06, SC-5 |

#### E2: RAG ingest — Elevation of Privilege

| Field | Value |
|-------|-------|
| **Threat** | A user with the `operator` role accesses `restricted` chunks by manipulating query parameters (e.g. passing `acl_level=restricted` in the request). |
| **Mitigation** | The ACL filter is applied by the Qdrant engine (pre-filter), not by Python code. `build_acl_filter()` builds the filter exclusively from `ROLE_TO_ACL[user_roles]` — the caller cannot specify the allowed ACL levels. |
| **Mapped code** | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` — `ROLE_TO_ACL` is a module-level immutable dict. |
| **Register provenance** | Phase 05 T-05-09-01; Phase 10 security register |

#### E3: Agent orchestration — Elevation of Privilege

| Field | Value |
|-------|-------|
| **Threat** | An agent with excessive agency performs actions beyond the authorized perimeter (e.g. writing to the production DB, sending commands to external systems) without HITL approval. |
| **Mitigation** | Every agent has a `recursion_limit=25` + mandatory HITL for `Decision.APPROVE` actions. Available tools are explicitly declared in the LangGraph toolspec — no generic shell/file tool. |
| **Mapped code** | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` — mandatory HITL interrupt for relevant actions + `recursion_limit` as a guard. |
| **Register provenance** | Phase 09 security register; OWASP LLM06 (excessive agency) |

---

## Mitigation Summary by Category

| Category | S1 IT/OT | S2 RAG ingest | S3 Agent orch. |
|----------|----------|---------------|----------------|
| **Spoofing** | Docker network + derived NATS subject | source_uri set by operator | JWT HS256 + require_roles |
| **Tampering** | AST guard D-51 (no OPC-UA write) | sanitize_document() denylist+bleach | LangGraph interrupt + post-HITL audit |
| **Repudiation** | NatsHeaderCarrier W3C traceparent | RESTRICTED_DOC_ACCESS audit + query_hash | MOTIVATION_MIN_LENGTH + AuditRecord |
| **Info Disclosure** | Docker network segmentation | build_acl_filter Qdrant pre-filter | _handle_agent_error generic body |
| **Denial of Service** | OpcUaClient bounded queue | IngestPipeline sequential + proxy limit | recursion_limit=25 + GraphRecursionError→503 |
| **EoP** | AST guard CI (test_ot_bridge_guard) | build_acl_filter immutable | safe_invoke HITL + limited tool scope |

---

## Closing Notes

This document realizes **SC-4** (STRIDE ≥1 threat per category × 3 surfaces with code-mapped mitigation) and is the project's v1.0 cross-cutting security contract.

For the OWASP LLM Top-10 mapping see [OWASP LLM](owasp-llm.md); for the governance and AI explainability overview see [Security & Governance](index.md).
