---
tags:
  - adr
  - architecture
  - llm
---

# ADR-003 — Self-hosted LLM via Ollama

- **Status:** Accepted
- **Phase:** Phase 1 (infra) / Phase 4 (runtime)
- **Date:** 2026

## Context

The platform processes potentially sensitive operational data and technical
documentation (process parameters, anomalies, proprietary knowledge).
Constraints:

- **data residency / privacy**: data must not leave the on-premise perimeter;
- predictable costs, independent of token volume;
- ability to run in air-gapped environments (shop floor / IT-OT);
- portability between CPU and NVIDIA GPU.

A dependency on a cloud LLM API would violate residency requirements and
introduce variable costs and an external network dependency.

## Decision

We adopt **self-hosted LLM inference via Ollama**, run inside the project's
containerized stack. The development stack starts Ollama with CPU and GPU
profiles; no calls to external inference services.

Reference:

- `make up` / `make up-gpu` — stack startup with Ollama (CPU/GPU).
- [LLM Serving](../architecture/llm-serving.md).
- runtime integration in `packages/sft-agents` (LLM client targeting the local
  Ollama endpoint).

## Consequences

**Positive**

- no data leaves the on-premise perimeter (privacy/residency);
- fixed, predictable inference costs;
- works in air-gapped environments; CPU and GPU profiles.

**Negative / trade-off**

- quality/latency bound by local hardware compared to frontier cloud models;
- operational burden of managing and updating local models.

Decision implemented in the infra (Phase 1) and consumed by the runtime
(Phase 4).
