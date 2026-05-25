---
lang: en
requirements:
  - DOC-17
tags:
  - transformation
  - opensource
  - agentic
  - hitl
  - oepv
---

# Transformation — From the Original Competition Track to the Agentic Platform

## Project Origin

This project is a reworking and expansion of an original competition track,
which described a fictional textile-sector client with digitalisation needs covering
Operations, Maintenance and Training, evaluated under the OEPV 70/30 criterion
(most economically advantageous offer — 70% technical, 30% economic, Base Bid €108,000).

The original competition track was **transformed and expanded** into a self-contained
opensource product, retaining the textile domain as the reference case while redesigning
the architecture, the delivery model and the AI governance approach.

---

## What Changed and Why

### From Proprietary Consulting to Opensource Self-Hosted Platform

**Original competition track:** GenAI solution delivered via a cloud stack with proprietary
services; the client depends on the vendor for updates and data security.

**This platform:** 100% self-hostable stack (Ollama/vLLM + Qdrant + FastAPI + Angular SSR
on an Nx monorepo), with open-weight LLMs (Qwen2.5 family, Apache 2.0 licence). Industrial
data stays on-premise. The code is reusable and modifiable by any organisation.

**Why:** industrial data protection is a non-negotiable requirement for manufacturing SMEs.
Opensource guarantees auditability, long-term economic sustainability and freedom
from vendor lock-in.

### From "AI Decides" to Systematic Human-in-the-Loop

**Original competition track:** AI agents are presented as automation tools; the role
of the human operator is implicit.

**This platform:** every critical action by an AI agent requires explicit approval by an
informed human (HITL — Human-in-the-Loop), with traceable evidence (audit trail,
RAG citations, confidence score) before the action is executed.
The guiding principle: *no human being is ever alone facing an operational problem,
but no critical decision bypasses human accountability.*

**Why:** emerging AI regulations (EU AI Act, ISO/IEC 42001) and the industrial operational
context (safety, MTTR, quality) require explicit governance and auditability. Operational
trust is built through transparency, not blind automation.

### From Three Clusters to Four Clusters Including Supply Chain

**Original competition track:** Operations, Maintenance, Training — three domains.

**This platform:** four agent clusters (16 reference agents):
- **Operations & Production:** OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector
- **Maintenance & Reliability:** PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer
- **Knowledge & Training:** KnowledgeCurator, TrainingCoach, ShiftHandover, DocumentationSynthesizer
- **Supply Chain & Economics:** InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster

**Why:** the textile manufacturing domain has strong dependencies between quality,
production and supply chain. CostAnalyzer and DemandForecaster close the economic
loop with reproducible OEPV models.

### From Generic Datasets to Simulated Textile Data + Public Benchmarks

**Original competition track:** datasets not specified; use of generic LLMs.

**This platform:** custom textile line simulator (looms, spinning frames, warp
preparation) with simulated OPC-UA events + replay of validated public datasets
(NASA C-MAPSS for predictive maintenance, UCI Manufacturing). LLM: Qwen2.5
multilingual (IT/EN) with native manufacturing domain support.

**Why:** technical credibility requires domain-specific data. Public datasets make
benchmarks reproducible by third parties.

### From Narrative 70/30 Evaluation to Reproducible OEPV Model

**Original competition track:** the OEPV evaluation is described as a tender criterion
without a verifiable economic model.

**This platform:** the economic model is a reproducible Python notebook/script
(`docs/economic-analysis/`) that, given configurable parameters (Base Bid €108,000,
GPU amortisation over 3 years, electricity 0.25 EUR/kWh, justified discount 10–15%
with written rationale), generates: 3-year TCO, OEPV 70/30 score, non-linear
sensitivity analysis, cloud stack vs self-hosted comparison.

**Why:** an economically defensible tender proposal must be reproducible and traceable.
The Assumption Register (DOC-12) documents every assumption with its source.

---

## Key Elements Retained from the Original Track

| Element | Description |
|---------|-------------|
| Domain | Textile manufacturing industry (fictional reference client: Mantis Textile Group) |
| Tender criteria | OEPV 70/30, Base Bid €108,000 |
| Primary language | Italian (with EN mirror for the opensource community) |
| Primary audience | Factory operators, maintenance technicians, shift supervisors, CIO |
| Scope | Functional PoC on simulated data, not real hardware integration |

---

## Choices Introduced by the Transformation

| Choice | Rationale |
|--------|-----------|
| 100% self-hostable stack | Industrial data on-premise; no vendor lock-in |
| Open-weight LLM (Qwen2.5) | Apache 2.0; multilingual IT/EN; controlled inference cost |
| Systematic HITL (LangGraph) | Explicit AI governance; audit trail for every critical decision |
| RAG on enterprise knowledge base | Reduces knowledge silos; SOPs searchable by all roles |
| Reproducible economic model | Defensibility in tender evaluation; transparency for assessors |
| Bilingual IT/EN documentation | Italian competition + international opensource community |
| Nx polyglot monorepo | Python (agents/backend) + Angular SSR (UI); unified CI/CD |

---

## Explicitly Excluded Elements

- References, branding or verbatim reproduction of content from the original competition track
- Physical hardware integration (real PLCs, physical sensors) — everything simulated
- LLM fine-tuning from scratch — targeted LoRA is a v2 candidate
- Multi-tenant SaaS — the product is single-tenant on-premise by design
- Custom computer vision for optical quality control — v2 candidate

---

## Requirements Traceability

| Requirement | Transformation element |
|-------------|----------------------|
| DOC-17 | This document |
| SC-4 | No reference to the original brand in public deliverables |
| ECO-01..08 | Reproducible OEPV model in `docs/economic-analysis/` |
| DEL-01..08 | Corresponding docs sections (architecture, workflows, use cases, UI, roadmap, economic) |
| HITL (all clusters) | LangGraph interrupt + `/v1/approvals` + audit trail |
