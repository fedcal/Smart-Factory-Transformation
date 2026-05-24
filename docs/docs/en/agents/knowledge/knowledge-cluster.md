---
lang: en
cluster: knowledge-training
requirements:
  - TRN-02
  - TRN-03
  - TRN-04
  - TRN-05
tags:
  - agents
  - knowledge
  - training
  - TRN-02
  - TRN-03
  - TRN-04
  - TRN-05
---

# Knowledge & Training Cluster

## Overview

The **Knowledge & Training** cluster groups the four agents responsible for
managing operational knowledge and workforce training in the factory:

| Agent | Primary Responsibility | HITL |
|-------|------------------------|------|
| **ShiftHandover** | Shift-change report compilation with dual supervisor sign-off | Dual-supervisor sign-off (D-SH-03) |
| **TrainingCoach** | Role-adaptive MCQ quiz + supervisor competency sign-off | Supervisor sign-off on pass (D-TC-03) |
| **KnowledgeCurator** | Autonomous document deduplication + staleness flagging | No HITL (D-KC-04) |
| **DocumentationSynthesizer** | Bilingual IT/EN SOP synthesis from historical RCA/downtime events + pre-index HITL | Supervisor pre-index (D-DS-03) |

All cluster outputs carry **`source_uri` + `timestamp`** on every citation
(TRN-05 — provenance guarantee). An output without citations is rejected by the
`SOPCitationValidator` before it can be indexed or delivered to the operator
(SC-5).

---

## ShiftHandover

### Overview

`ShiftHandover` compiles the end-of-shift report by aggregating
operational/maintenance events from the current shift (from `audit.actions`),
summarises them into a structured document, and submits it for sequential
dual sign-off by the outgoing and incoming shift supervisors (D-SH-03).
The trigger is automatic (NATS consumer on `shift.boundary.>`) or on-demand
by the supervisor.

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `query_audit_actions` | Phase 4 (`sft_agents.tools.audit`) | Retrieves shift events from `audit.actions` filtered by time window and `action_type` (D-SH-02). |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Sends the approval request to the outgoing supervisor (first sign-off) and then to the incoming supervisor (second sign-off). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes `HANDOVER_DRAFT` and `HANDOVER_SIGNOFF` rows to `audit.actions`. |

### Data Sources

- **TimescaleDB `audit.actions`** — cross-cluster audit backbone (ops/maintenance);
  the `ShiftAggregator` reads exclusively from this table (D-SH-02 — no
  `ops.alerts` or `ops.work_orders` tables).
- **TimescaleDB `maintenance.downtime_events`** — machine downtime events in the shift.
- **sft-knowledge Qdrant** — RAG citations for the handover narrative summary.

### HITL Tier

| Decision | Tier | Approver |
|----------|------|---------|
| Outgoing shift sign-off | supervisor (Decision.HITL_SUPERVISOR) | Outgoing shift supervisor |
| Incoming shift sign-off | supervisor (Decision.HITL_SUPERVISOR) | Incoming shift supervisor |

Two `HANDOVER_SIGNOFF` rows per handover — sequential sign-off (D-SH-03).

### KPIs Impacted

- **handover_completion_rate** — percentage of shifts with handover completed within the 3-minute deadline.
- **handover_dual_signoff_p95** — p95 latency of the dual-signoff flow.

### Invocation

- **API endpoint**: `POST /v1/agents/shift-handover/compile`
  with body `{"shift_start": "<ISO-UTC>", "shift_end": "<ISO-UTC>", "user_roles": ["shift_supervisor"]}`
- **NATS trigger**: consumer on `shift.boundary.>` (configurable boundaries, e.g. 06:00/14:00/22:00).
- **Thread ID**: convention `knowledge.shift-handover.<uuid4>`.
- **Response**: `202 Accepted` (async HITL).

### Audit Footprint

- `HANDOVER_DRAFT` — one row on draft completion.
- `HANDOVER_SIGNOFF` — two rows per handover (outgoing + incoming, D-SH-03).
- Every row carries `source_uri` + `retrieved_at` on RAG citations (TRN-05).

---

## TrainingCoach

### Overview

`TrainingCoach` delivers adaptive MCQ quiz sessions for different operator
roles/personas (tessitore, tintore, manutentore — from the Mantis synthetic
registry, D-X-03). Questions are generated deterministically from SOPs via RAG.
The competency score is computed without an LLM judge (D-TC-01). Above the
threshold (default 0.80), the competency sign-off is sent to the supervisor for
HITL approval (D-TC-03).

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `rag_retrieve` | Phase 5 (`sft_knowledge.retrieval.pipeline`) | Retrieves role-relevant SOP chunks for question generation. |
| `score_quiz` | trn-training-coach | Computes the deterministic score against known answer keys. |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Sends the competency sign-off request to the supervisor when `score >= threshold`. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes `TRAINING_SESSION` and `TRAINING_SIGNOFF` to `audit.actions`. |

### Data Sources

- **sft-knowledge Qdrant** — SOP index by role; provides RAG citations with
  `source_uri` + `retrieved_at` for each generated question (TRN-05).
- **Mantis personas registry** — maps `persona_role` to the SOP profile (D-X-03).

### HITL Tier

| Decision | Tier | Approver |
|----------|------|---------|
| Score below threshold (0.80) — fail | none (Decision.AUTO) | n/a |
| Score >= threshold — competency acquired | supervisor (Decision.HITL_SUPERVISOR) | Shift supervisor |

### KPIs Impacted

- **training_pass_rate** — percentage of sessions with score >= threshold by role.
- **competency_signoff_latency** — latency between supervisor notification and sign-off.
- **rag_citation_coverage** — percentage of questions with at least one `source_uri` citation (TRN-05).

### Invocation

- **Session** `POST /v1/agents/training-coach/session`
  with body `{"persona_role": "tessitore", "user_roles": ["operator"]}`
- **Resume** `POST /v1/agents/training-coach/resume`
  with body `{"thread_id": "<id>", "decision": "approved"}`
- **Thread ID**: convention `knowledge.training-coach.<uuid4>`.
- **Session response**: `200 OK` with `competency_result` + `training_session`.
- **Resume response**: `200 OK` with competency sign-off.

### Audit Footprint

- `TRAINING_SESSION` — one row per session (pass or fail).
- `TRAINING_SIGNOFF` — one row per session with score >= threshold (post-HITL).
- Every session carries RAG citations with `source_uri` + `retrieved_at` (TRN-05).

---

## KnowledgeCurator

### Overview

`KnowledgeCurator` autonomously manages knowledge base quality: detects
duplicates (exact via SHA-256 + near-dup via BGE-M3 cosine, D-KC-01), flags
stale documents by type (D-KC-02), and computes the document reuse rate
(D-KC-03). It is a **fully autonomous** agent — no HITL (D-KC-04): dedup and
staleness operations are read-only/flag-only, with no irreversible action.

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `sha256_hash` | trn-knowledge-curator.dedup | Exact hash of normalised text for exact duplicate detection (D-KC-01). |
| `embed_bge_m3` | Phase 5 (`sft_knowledge.embedding.bge_m3`) | BGE-M3 embedding for near-duplicate detection via cosine similarity (D-KC-01). |
| `check_staleness` | trn-knowledge-curator.staleness | Compares `last_updated` against the per-type threshold (D-KC-02). |
| `compute_reuse_rate` | trn-knowledge-curator.reuse_rate | Computes `distinct cited / total indexed` over a rolling window (D-KC-03). |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes `KNOWLEDGE_DEDUP` and `STALE_FLAG` to `audit.actions`. |

### Data Sources

- **sft-knowledge Qdrant** — document index; target for near-dup search and
  reuse-rate computation.
- **TimescaleDB `audit.actions`** — `source_uri` citations emitted by TRN/MNT/OPS
  agents; basis for the reuse-rate calculation (D-KC-03).

### HITL Tier

`KnowledgeCurator` is fully autonomous (Decision.AUTO on all operations).
No HITL is defined (D-KC-04).

### KPIs Impacted

- **knowledge_dedup_rate** — percentage of ingests blocked as duplicates.
- **stale_doc_fraction** — percentage of documents flagged as stale.
- **knowledge_reuse_rate** — `distinct cited / total indexed` (D-KC-03).

### Invocation

- **API endpoint**: `POST /v1/agents/knowledge-curator/ingest`
  with body `{"document_text": "...", "doc_type": "sop", "last_updated": "<ISO-UTC>"}`
- **Thread ID**: convention `knowledge.knowledge-curator.<uuid4>`.
- **Response**: `200 OK` (synchronous, autonomous — never 202).

### Audit Footprint

- `KNOWLEDGE_DEDUP` — one row per ingest with verdict (unique/near_duplicate/exact_duplicate).
- `STALE_FLAG` — one row per document flagged as stale.
- Both rows carry `source_uri` + timestamp (TRN-05).

---

## DocumentationSynthesizer

### Overview

`DocumentationSynthesizer` generates bilingual SOPs (IT primary + EN translation)
from historical RCA/downtime/coach events aggregated by failure mode and asset
(D-DS-02). The output follows a fixed-section template (Scopo/Purpose,
Prerequisiti/Prerequisites, Passi/Steps, Sicurezza/Safety, Riferimenti/References)
with every claim anchored to `[SRC:N]` citations traceable to a `source_uri`
(D-DS-03, TRN-05). Supervisor approval is required **before** Qdrant indexing
(D-DS-03).

The IT → EN translation re-anchors `[SRC:N]` citations to prevent citation drift
(D-DS-01 Pitfall §1). The `SOPCitationValidator` verifies anchor parity between
IT and EN before committing.

### Tools Used

| Tool | Source | Purpose |
|------|--------|---------|
| `aggregate_events` | trn-documentation-synthesizer.event_aggregator | Aggregates RCA/downtime/coach events from `audit.actions` by `failure_mode` + `asset_id` + `window_days` (D-DS-02). |
| `build_sop` | trn-documentation-synthesizer.sop_builder | Generates the IT SOP with fixed sections and `[SRC:N]` anchors (D-DS-03). |
| `translate_sop` | trn-documentation-synthesizer.translator | Translates IT SOP → EN preserving all `[SRC:N]` anchors (D-DS-01). |
| `validate_citations` | trn-documentation-synthesizer.validators | `SOPCitationValidator`: verifies provenance + IT/EN anchor parity (TRN-05). |
| `escalate_to_supervisor` | Phase 6 (`sft_agents.tools.hitl`) | Sends the SOP draft to the supervisor for pre-index approval (D-DS-03). |
| `upsert_qdrant` | Phase 5 (`sft_knowledge`) | Indexes the approved SOP in Qdrant only after HITL approval. |
| `log_event` | Phase 4 (`sft_agents.tools.audit`) | Writes `SOP_DRAFT` to `audit.actions` after approval. |

### Data Sources

- **TimescaleDB `audit.actions`** — historical RCA/downtime/coach events
  aggregated by failure mode and asset (D-DS-02).
- **sft-knowledge Qdrant** — indexing target for the approved SOP.
- **BGE-M3 embedder** (Phase 5) — generates embeddings for post-HITL indexing.

### HITL Tier

| Decision | Tier | Approver |
|----------|------|---------|
| SOP draft generated — pre-indexing | supervisor (Decision.HITL_SUPERVISOR) | Shift supervisor |

Qdrant indexing happens **only after** HITL approval (D-DS-03).

### KPIs Impacted

- **sop_generation_rate** — new bilingual SOPs approved per week.
- **citation_coverage** — percentage of SOP sections with at least one `[SRC:N]` anchor.
- **hitl_approval_latency** — p50/p95 latency from supervisor notification to approval.

### Invocation

- **Draft** `POST /v1/agents/documentation-synthesizer/draft`
  with body `{"failure_mode": "...", "asset_id": "LOOM-01", "window_days": 30}`
- **Thread ID**: convention `knowledge.documentation-synthesizer.<uuid4>`.
- **Draft response**: `202 Accepted` with `hitl_status: supervisor_pending`.
- **Resume** via `/approvals` endpoint (Phase 6 HITL workflow).

### Audit Footprint

- `SOP_DRAFT` — one row **after** supervisor approval (not before).
- Every citation in the SOP carries `source_uri` + `retrieved_at` (TRN-05).
- `SOPCitationValidator` runs before commit — outputs without citations or with
  anchor drift are rejected (SC-5).

---

## Provenance Guarantee (TRN-05 / SC-5)

All four Knowledge & Training cluster agents satisfy **TRN-05**: every output
that reaches an operator or is indexed in Qdrant must carry at least one
citation with a non-null `source_uri` + `retrieved_at`. The `SOPCitationValidator`
is the final gate for the DocumentationSynthesizer cluster; explicit negative
tests in the E2E suite (Plan 08-09) ensure opaque outputs are rejected during
testing.

```
SC-5: "Citation provenance enforced; no opaque outputs accepted"
     — verified by test_knowledge_cluster_e2e.py::test_trn05_opaque_output_rejected_by_sop_citation_validator
```
