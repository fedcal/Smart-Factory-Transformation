---
tags:
  - security
  - owasp
  - llm
---

# OWASP LLM Top 10 — Mapping to Concrete Mitigations

!!! info "Authoritative source (single source of truth)"
    This page faithfully reproduces the OWASP LLM Top 10 mapping consolidated in
    **Phase 11** (`docs/security/owasp-llm-top10.md`, OWASP LLM Top 10 2025 standard,
    2026-05-25). Every change must be made in the source and re-published here to
    avoid divergence (DOC-11, SEC-02).

Systematic mapping of the 10 OWASP LLM risks to the mitigations implemented in the
Smart Factory Transformation v1.0 project. Where a risk is not applicable, the
technical rationale is documented.

---

## LLM01 — Prompt Injection

**OWASP description:** An attacker manipulates the prompt (directly or via indirect
input) to make the LLM perform unauthorized actions or extract confidential information.

**Vectors applicable to SFT:**

- Documents uploaded into RAG ingest may contain injection instructions.
- API users may attempt to manipulate the RAG query text.

**Implemented mitigation (SEC-04, Plan 11-03):**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| Ingest | Regex denylist (7 patterns) + `bleach.clean(tags=[], strip=True)` | `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py:sanitize_document` |
| Runtime | Sanitization applied post-chunking on plain text (Pitfall 6 RESEARCH) | `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:IngestPipeline.ingest` |
| Test | SC-3: crafted-PDF test verifies no imperative instruction survives | `tests/security/test_prompt_injection.py` |

**Status:** MITIGATED — deterministic CI-testable denylist.

---

## LLM02 — Sensitive Information Disclosure

**OWASP description:** The LLM reveals confidential information (personal data, intellectual
property, credentials) in its responses or logs.

**Vectors applicable to SFT:**

- `restricted` document chunks (patents, confidential SOPs) exposed to unauthorized roles.
- Stack traces or internal details in error response bodies.

**Implemented mitigation (SEC-07, Plan 11-03 + Phase 05):**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| ACL pre-filter | `build_acl_filter()` → Qdrant engine-side filter; operator sees only `public` | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` |
| Audit trail | `RESTRICTED_DOC_ACCESS` AuditRecord with SHA-256 query_hash (no plaintext) | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:RetrievalPipeline._write_restricted_audit` |
| Error body | `_handle_agent_error()` → `{"error":"internal_agent_error"}`; str(exc) only in structlog | `apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py:_handle_agent_error` |
| UI | Evidence panel hides `chunk_preview` if `acl_level == 'restricted'` | `apps/factory-ui/src/app/shared/evidence-panel/evidence-panel.component.ts` |

**Status:** MITIGATED — ACL enforced at engine level + generic error body.

---

## LLM03 — Supply Chain

**OWASP description:** Compromised LLM dependencies (pre-trained models, datasets, plugins,
packages) introduce backdoors or vulnerabilities.

**Vectors applicable to SFT:**

- Python/npm packages installed via pip/uv/npm could be slopsquatted or malicious.
- The Qwen2.5 model is downloaded from Ollama; it could be replaced with a corrupted model.

**Implemented mitigation (Plan 10-RESEARCH, Phase 11):**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| Package pin | `uv.lock` with SHA-256 hash per Python dependency; `package-lock.json` for npm | `uv.lock` (root workspace) + `apps/factory-ui/package-lock.json` |
| Legitimacy audit | Package Legitimacy Audit documented in RESEARCH.md for each new package | `.planning/phases/*/RESEARCH.md` (Package Legitimacy Audit section) |
| Checkpoint | Executor blocks installation of unverified packages (gate `blocking-human`) | Executor policy (checkpoint protocol) |
| LLM model | Ollama downloads from the official registry; version tag specified in `.env.example` | `infra/compose/.env.example:OLLAMA_MODEL_DEFAULT` |

**Status:** MITIGATED — pinned versions + legitimacy audit + lock file.

---

## LLM04 — Model Denial of Service

**OWASP description:** Specially crafted inputs (long prompts, recursion, loops) exhaust
the LLM's resources, making the service unavailable.

**Vectors applicable to SFT:**

- RAG queries with very long prompts increase the computational cost of embedding.
- Looping LangGraph agents consume CPU/RAM until terminated.

**Implemented mitigation:**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| Recursion limit | `recursion_limit=25` in every `build_invocation_config()`; `_RECURSION_LIMIT=5` supply cluster | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` |
| Graph recursion | `GraphRecursionError → 503` with `agent_loop_detected` message | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` |
| Alert rate limit | SSE alerts capped at 12/hour per principal (`_ALERT_RATE_LIMIT=12`) | `apps/api-gateway/src/svc_api_gateway/routers/sse.py:_ALERT_RATE_LIMIT` |

**Status:** MITIGATED — recursion guard + SSE rate limit.

---

## LLM05 — Output Handling

**OWASP description:** The LLM output is not validated before being passed to downstream
systems (shell, database, browser), causing XSS, SQL injection, code execution.

**Vectors applicable to SFT:**

- Agent rationale stored in audit JSONB could be interpreted as HTML/JS.
- Citation text from RAG rendered in the evidence panel.

**Implemented mitigation:**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| Angular auto-escape | Angular templates: `{{ expr }}` interpolation auto-escaped; no unsanitized `innerHTML` | `apps/factory-ui/src/app/shared/alert-feed/alert-feed.component.ts` |
| Evidence panel | `isValidUri()` validates `source_uri` (http/https only); chunk_preview not interpreted as HTML | `apps/factory-ui/src/app/shared/evidence-panel/evidence-panel.component.ts:isValidUri` |
| SQL params | All queries use parameterized `$1..$N`; no f-strings in SQL | `apps/api-gateway/src/svc_api_gateway/routers/kpi.py` |

**Status:** MITIGATED — Angular auto-escape + parameterized SQL.

---

## LLM06 — Excessive Agency

**OWASP description:** The LLM has excessive capabilities (functions, permissions, autonomy)
allowing it to perform high-impact actions without supervision.

**Vectors applicable to SFT:**

- Agents (ShiftHandover, InventoryManager, EnergyOptimizer, DemandForecaster) can issue
  recommendations with real operational effects.
- CostAnalyzer and DocumentationSynthesizer operate in autonomous mode (Decision.AUTO).

**Implemented mitigation:**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| HITL mandatory | Mandatory LangGraph `interrupt()` for `Decision.APPROVE` actions — the agent does not proceed without operator OK | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` |
| Recursion limit | `recursion_limit=25` as a guard against unsupervised autonomous loops | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` |
| Limited tool scope | Each agent has an explicitly declared toolspec; no generic shell/file tool | LangGraph agent definitions in `packages/sft-agents/src/sft_agents/` |
| Motivation gate | Frontend requires `MOTIVATION_MIN_LENGTH = 10` characters per approval | `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:MOTIVATION_MIN_LENGTH` |

**Status:** MITIGATED — mandatory HITL + recursion limit + explicit tool scope.

---

## LLM07 — System Prompt Leakage

**OWASP description:** The system prompt containing sensitive instructions, policies or
credentials is extracted from the LLM via prompt injection or direct output.

**Vectors applicable to SFT:**

- Agent system prompts contain operational instructions (not credentials).
- Langfuse records the prompts: unauthorized access to Langfuse exposes the prompts.

**Implemented mitigation:**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| No secrets in prompts | System prompts contain no credentials or API keys; only operational instructions | Documented convention + review |
| Langfuse access | `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` managed via env vars; Langfuse protected by authentication | `infra/compose/.env.example:LANGFUSE_PUBLIC_KEY` |
| Audit role | Only the `auditor` role accesses the audit logs (SEC-03) | `apps/api-gateway/src/svc_api_gateway/security/jwt.py:SEEDED_USERS` |

**Status:** PARTIALLY MITIGATED — prompts contain no secrets; Langfuse access protected.
Note: in production, Langfuse RBAC is recommended to limit trace visibility.

---

## LLM08 — Vector and Embedding Weaknesses

**OWASP description:** Manipulation of the vector database or embeddings to alter RAG
results (poisoning, embedding inversion).

**Vectors applicable to SFT:**

- A malicious ingested document can "poison" the Qdrant collection.
- BGE-M3 embeddings can be inverted to extract the original text.

**Implemented mitigation:**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| Authenticated ingest | Only authenticated operators (ingest role) can upload documents | `apps/api-gateway/src/svc_api_gateway/security/rbac.py:require_roles` |
| Pre-embed sanitization | `sanitize_document()` removes injection before the text reaches the embedder | `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py:sanitize_document` |
| Post-retrieval ACL | Restricted chunks are not exposed to unauthorized roles (double defense) | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` |

**Status:** PARTIALLY MITIGATED — authenticated ingest + pre-embed sanitization.
Note: embedding inversion is not mitigated (academic risk, not operational in v1.0).

---

## LLM09 — Misinformation

**OWASP description:** The LLM generates plausible but factually incorrect output
(hallucinations), accepted as authoritative and leading to wrong decisions.

**Vectors applicable to SFT:**

- Agent recommendations (e.g. InventoryManager reorder point, EnergyOptimizer savings)
  can be based on hallucinations rather than real data.
- RAG can produce answers not faithful to the SOP documents.

**Implemented mitigation:**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| Eval gate CI | `MockDeepEvalLLM` CI gate verifies hallucination rate < 5% and answer relevance ≥ 0.75 | `tests/eval/test_rag_ci_gate.py:test_hallucination_rate_below_threshold` |
| HITL review | Agent recommendations go through HITL before any operational action | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` |
| Evidence panel | The UI shows RAG citations with snippet and source_uri — the operator can verify the source | `apps/factory-ui/src/app/shared/evidence-panel/evidence-panel.component.ts` |

**Status:** MITIGATED — CI eval gate + mandatory HITL + verifiable evidence panel.

---

## LLM10 — Unbounded Consumption

**OWASP description:** The LLM consumes resources (tokens, CPU, API calls) without limits,
causing excessive costs or service degradation.

**Vectors applicable to SFT:**

- Very frequent RAG queries or agent invocations exhaust the token/cost budget.
- Local Ollama has no API cost but has CPU/GPU limits; many parallel requests degrade performance.

**Implemented mitigation:**

| Layer | Mitigation | File:function |
|-------|------------|---------------|
| Budget tracking | `BudgetSnapshot` tracks token_input, token_output, cost_usd_simulated per invocation | `packages/sft-agents/src/sft_agents/models/budget.py:BudgetSnapshot` |
| SSE rate limit | SSE alerts capped at 12/hour per principal; `rate_limit` event emitted on reaching the cap | `apps/api-gateway/src/svc_api_gateway/routers/sse.py:_ALERT_RATE_LIMIT` |
| Recursion guard | `recursion_limit=25` prevents costly loops; `GraphRecursionError → 503` | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` |

**Status:** PARTIALLY MITIGATED — budget tracking + recursion guard.
Note: API-level rate limiting (FastAPI middleware) is documented as AR-01 (deferred);
see the Phase 11 source `docs/security/rate-limit-scaling.md` for the Redis evolution path.

---

## Summary

| ID | Title | SFT Status | Key file |
|----|-------|-----------|----------|
| LLM01 | Prompt Injection | MITIGATED | `sanitizer.py:sanitize_document` |
| LLM02 | Sensitive Info Disclosure | MITIGATED | `pipeline.py:build_acl_filter` |
| LLM03 | Supply Chain | MITIGATED | `uv.lock` + Package Legitimacy Audit |
| LLM04 | Model DoS | MITIGATED | `langfuse_callback.py:build_invocation_config` |
| LLM05 | Output Handling | MITIGATED | Angular auto-escape + SQL params |
| LLM06 | Excessive Agency | MITIGATED | `supervisor.py:safe_invoke` + HITL |
| LLM07 | System Prompt Leakage | PARTIALLY MITIGATED | env var policy + auditor role |
| LLM08 | Vector/Embedding Weaknesses | PARTIALLY MITIGATED | ingest auth + sanitization |
| LLM09 | Misinformation | MITIGATED | CI eval gate + HITL + evidence panel |
| LLM10 | Unbounded Consumption | PARTIALLY MITIGATED | BudgetSnapshot + recursion_limit |

**Legend:**

- **MITIGATED:** mitigation implemented and tested in code
- **PARTIALLY MITIGATED:** primary mitigation implemented; residual gaps documented
- **N/A:** risk not applicable to the SFT v1.0 technical perimeter

For the full STRIDE matrix see [STRIDE Threat Model](stride-threat-model.md).
