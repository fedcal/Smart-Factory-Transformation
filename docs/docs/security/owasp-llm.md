---
tags:
  - security
  - owasp
  - llm
---

# OWASP LLM Top 10 — Mapping a Mitigazioni Concrete

!!! info "Fonte autoritativa (single source of truth)"
    Questa pagina riporta fedelmente il mapping OWASP LLM Top 10 consolidato in
    **Phase 11** (`docs/security/owasp-llm-top10.md`, standard OWASP LLM Top 10 2025,
    2026-05-25). Ogni modifica va effettuata nella fonte e ripubblicata qui per
    evitare divergenze (DOC-11, SEC-02).

Mappatura sistematica dei 10 rischi OWASP LLM alle mitigazioni implementate nel progetto
Smart Factory Transformation v1.0. Dove un rischio non è applicabile, è documentata la
rationale tecnica.

---

## LLM01 — Prompt Injection

**Descrizione OWASP:** Un attaccante manipola il prompt (direttamente o tramite input
indiretto) per far eseguire all'LLM azioni non autorizzate o estrarre informazioni riservate.

**Vettori applicabili a SFT:**

- Documenti caricati nel RAG ingest possono contenere istruzioni injection.
- Utenti API possono tentare di manipolare il query text del RAG.

**Mitigazione implementata (SEC-04, Plan 11-03):**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| Ingest | Denylist regex (7 pattern) + `bleach.clean(tags=[], strip=True)` | `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py:sanitize_document` |
| Runtime | Sanitizzazione applicata post-chunking sul testo plain (Pitfall 6 RESEARCH) | `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py:IngestPipeline.ingest` |
| Test | SC-3: test crafted-PDF verifica che nessuna istruzione imperativa sopravviva | `tests/security/test_prompt_injection.py` |

**Stato:** MITIGATO — denylist deterministica CI-testabile.

---

## LLM02 — Sensitive Information Disclosure

**Descrizione OWASP:** L'LLM rivela informazioni riservate (dati personali, proprietà
intellettuale, credenziali) nelle risposte o nei log.

**Vettori applicabili a SFT:**

- Chunk di documenti `restricted` (brevetti, SOP confidenziali) esposti a ruoli non autorizzati.
- Stack trace o dettagli interni nel corpo delle risposte di errore.

**Mitigazione implementata (SEC-07, Plan 11-03 + Phase 05):**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| ACL pre-filter | `build_acl_filter()` → Qdrant engine-side filter; operator vede solo `public` | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` |
| Audit trail | `RESTRICTED_DOC_ACCESS` AuditRecord con query_hash SHA-256 (non testo in chiaro) | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:RetrievalPipeline._write_restricted_audit` |
| Error body | `_handle_agent_error()` → `{"error":"internal_agent_error"}`; str(exc) solo in structlog | `apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py:_handle_agent_error` |
| UI | Evidence panel nasconde `chunk_preview` se `acl_level == 'restricted'` | `apps/factory-ui/src/app/shared/evidence-panel/evidence-panel.component.ts` |

**Stato:** MITIGATO — ACL enforced a livello engine + error body generico.

---

## LLM03 — Supply Chain

**Descrizione OWASP:** Dipendenze LLM compromesse (modelli pre-trainati, dataset, plugin,
pacchetti) introducono backdoor o vulnerabilità.

**Vettori applicabili a SFT:**

- Pacchetti Python/npm installati via pip/uv/npm potrebbero essere slopsquatted o malevoli.
- Il modello Qwen2.5 è scaricato da Ollama; potrebbe essere sostituito con un modello corrotto.

**Mitigazione implementata (Plan 10-RESEARCH, Phase 11):**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| Package pin | `uv.lock` con hash SHA-256 per ogni dipendenza Python; `package-lock.json` per npm | `uv.lock` (root workspace) + `apps/factory-ui/package-lock.json` |
| Legitimacy audit | Package Legitimacy Audit documentato in RESEARCH.md per ogni nuovo pacchetto | `.planning/phases/*/RESEARCH.md` (sezione Package Legitimacy Audit) |
| Checkpoint | Executor blocca install di pacchetti non verificati (gate `blocking-human`) | Policy executor (checkpoint protocol) |
| LLM model | Ollama scarica da registry ufficiale; tag versione specificato in `.env.example` | `infra/compose/.env.example:OLLAMA_MODEL_DEFAULT` |

**Stato:** MITIGATO — versioni pin + audit di legittimità + lock file.

---

## LLM04 — Model Denial of Service

**Descrizione OWASP:** Input appositamente costruiti (prompt lunghi, recursione, loop)
esauriscono le risorse del modello LLM, rendendo il servizio non disponibile.

**Vettori applicabili a SFT:**

- Query RAG con prompt molto lunghi aumentano il costo computazionale dell'embedding.
- Agenti LangGraph in loop consumano CPU/RAM finché non vengono terminati.

**Mitigazione implementata:**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| Recursion limit | `recursion_limit=25` in ogni `build_invocation_config()`; `_RECURSION_LIMIT=5` supply cluster | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` |
| Graph recursion | `GraphRecursionError → 503` con messaggio `agent_loop_detected` | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` |
| Alert rate limit | SSE alert capped a 12/ora per principal (`_ALERT_RATE_LIMIT=12`) | `apps/api-gateway/src/svc_api_gateway/routers/sse.py:_ALERT_RATE_LIMIT` |

**Stato:** MITIGATO — recursion guard + rate limit SSE.

---

## LLM05 — Output Handling

**Descrizione OWASP:** L'output LLM non è validato prima di essere passato a sistemi
downstream (shell, database, browser), causando XSS, SQL injection, code execution.

**Vettori applicabili a SFT:**

- Rationale agente inserita in audit JSONB potrebbe essere interpretata come HTML/JS.
- Citation text dal RAG renderizzato nell'evidence panel.

**Mitigazione implementata:**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| Angular auto-escape | Template Angular: interpolazione `{{ expr }}` auto-escaped; nessun `innerHTML` non sanitizzato | `apps/factory-ui/src/app/shared/alert-feed/alert-feed.component.ts` |
| Evidence panel | `isValidUri()` valida `source_uri` (solo http/https); chunk_preview non interpretato come HTML | `apps/factory-ui/src/app/shared/evidence-panel/evidence-panel.component.ts:isValidUri` |
| SQL params | Tutte le query usano `$1..$N` parametrizzati; nessun f-string in SQL | `apps/api-gateway/src/svc_api_gateway/routers/kpi.py` |

**Stato:** MITIGATO — auto-escape Angular + SQL parametrizzato.

---

## LLM06 — Excessive Agency

**Descrizione OWASP:** L'LLM ha capacità eccessive (funzioni, permessi, autonomia) che
gli permettono di eseguire azioni con impatto significativo senza supervisione.

**Vettori applicabili a SFT:**

- Gli agenti (ShiftHandover, InventoryManager, EnergyOptimizer, DemandForecaster) possono
  emettere raccomandazioni con effetti operativi reali.
- CostAnalyzer e DocumentationSynthesizer operano in modalità autonoma (Decision.AUTO).

**Mitigazione implementata:**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| HITL mandatory | `interrupt()` LangGraph obbligatorio per azioni `Decision.APPROVE` — l'agente non procede senza OK operatore | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` |
| Recursion limit | `recursion_limit=25` come guard contro loop autonomi non supervisionati | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` |
| Tool scope limitato | Ogni agente ha toolspec dichiarata esplicitamente; nessun tool generico shell/file | LangGraph agent definitions in `packages/sft-agents/src/sft_agents/` |
| Motivation gate | Frontend richiede `MOTIVATION_MIN_LENGTH = 10` caratteri per ogni approvazione | `apps/factory-ui/src/app/shared/approval-card/approval-card.component.ts:MOTIVATION_MIN_LENGTH` |

**Stato:** MITIGATO — HITL obbligatorio + recursion limit + tool scope esplicito.

---

## LLM07 — System Prompt Leakage

**Descrizione OWASP:** Il system prompt contenente istruzioni sensibili, policy o credenziali
viene estratto dall'LLM tramite attacchi di prompt injection o output diretto.

**Vettori applicabili a SFT:**

- I prompt di sistema degli agenti contengono istruzioni operative (non credenziali).
- Langfuse registra i prompt: un accesso non autorizzato a Langfuse espone i prompt.

**Mitigazione implementata:**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| No secrets in prompts | I prompt di sistema non contengono credenziali o chiavi API; solo istruzioni operative | Convention documentata + review |
| Langfuse access | `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` gestiti via env var; Langfuse protetto da autenticazione | `infra/compose/.env.example:LANGFUSE_PUBLIC_KEY` |
| Audit role | Solo il ruolo `auditor` accede ai log di audit (SEC-03) | `apps/api-gateway/src/svc_api_gateway/security/jwt.py:SEEDED_USERS` |

**Stato:** MITIGATO PARZIALMENTE — prompts non contengono secrets; accesso Langfuse protetto.
Nota: in produzione si raccomanda RBAC Langfuse per limitare la visibilità dei trace.

---

## LLM08 — Vector and Embedding Weaknesses

**Descrizione OWASP:** Manipolazione del database vettoriale o degli embedding per
alterare i risultati RAG (poisoning, inversion degli embedding).

**Vettori applicabili a SFT:**

- Un documento malevolo ingerito può "inquinare" la collection Qdrant.
- Gli embedding BGE-M3 possono essere invertiti per estrarre testo originale.

**Mitigazione implementata:**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| Ingest autenticato | Solo operatori autenticati (ruolo ingest) possono caricare documenti | `apps/api-gateway/src/svc_api_gateway/security/rbac.py:require_roles` |
| Sanitizzazione pre-embed | `sanitize_document()` rimuove injection prima che il testo raggiunga l'embedder | `services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py:sanitize_document` |
| ACL post-retrieval | I chunk restricted non sono esposti a ruoli non autorizzati (double defense) | `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py:build_acl_filter` |

**Stato:** MITIGATO PARZIALMENTE — ingest autenticato + sanitizzazione pre-embed.
Nota: l'inversione degli embedding non è mitigata (rischio accademico, non operativo in v1.0).

---

## LLM09 — Misinformation

**Descrizione OWASP:** L'LLM genera output plausibili ma fattuamente incorretti (allucinazioni),
che vengono accettati come autorevoli e portano a decisioni errate.

**Vettori applicabili a SFT:**

- Le raccomandazioni degli agenti (es. reorder point InventoryManager, savings EnergyOptimizer)
  possono essere basate su allucinazioni invece che su dati reali.
- Il RAG può produrre risposte non fedeli ai documenti SOPs.

**Mitigazione implementata:**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| Eval gate CI | `MockDeepEvalLLM` gate CI verifica hallucination rate < 5% e answer relevance ≥ 0.75 | `tests/eval/test_rag_ci_gate.py:test_hallucination_rate_below_threshold` |
| HITL review | Le raccomandazioni degli agenti passano per HITL prima di qualsiasi azione operativa | `packages/sft-agents/src/sft_agents/runtime/supervisor.py:safe_invoke` |
| Evidence panel | L'UI mostra le citazioni RAG con snippet e source_uri — l'operatore può verificare la fonte | `apps/factory-ui/src/app/shared/evidence-panel/evidence-panel.component.ts` |

**Stato:** MITIGATO — eval gate CI + HITL obbligatorio + evidence panel verificabile.

---

## LLM10 — Unbounded Consumption

**Descrizione OWASP:** L'LLM consuma risorse (token, CPU, API calls) senza limiti,
causando costi eccessivi o degradazione del servizio.

**Vettori applicabili a SFT:**

- Query RAG o invocazioni agente molto frequenti esauriscono il budget token/costo.
- Ollama locale non ha costo API ma ha limiti di CPU/GPU; molte richieste parallele
  degradano le performance.

**Mitigazione implementata:**

| Layer | Mitigazione | File:funzione |
|-------|------------|---------------|
| Budget tracking | `BudgetSnapshot` traccia token_input, token_output, cost_usd_simulated per invocazione | `packages/sft-agents/src/sft_agents/models/budget.py:BudgetSnapshot` |
| SSE rate limit | Alert SSE capped a 12/ora per principal; `rate_limit` event emesso al raggiungimento | `apps/api-gateway/src/svc_api_gateway/routers/sse.py:_ALERT_RATE_LIMIT` |
| Recursion guard | `recursion_limit=25` impedisce loop costosi; `GraphRecursionError → 503` | `packages/sft-agents/src/sft_agents/llm/langfuse_callback.py:build_invocation_config` |

**Stato:** MITIGATO PARZIALMENTE — budget tracking + recursion guard.
Nota: rate limiting API-level (middleware FastAPI) è documentato come AR-01 (deferred);
vedere la fonte Phase 11 `docs/security/rate-limit-scaling.md` per il path evolutivo Redis.

---

## Riepilogo

| ID | Titolo | Stato SFT | File chiave |
|----|--------|-----------|-------------|
| LLM01 | Prompt Injection | MITIGATO | `sanitizer.py:sanitize_document` |
| LLM02 | Sensitive Info Disclosure | MITIGATO | `pipeline.py:build_acl_filter` |
| LLM03 | Supply Chain | MITIGATO | `uv.lock` + Package Legitimacy Audit |
| LLM04 | Model DoS | MITIGATO | `langfuse_callback.py:build_invocation_config` |
| LLM05 | Output Handling | MITIGATO | Angular auto-escape + SQL params |
| LLM06 | Excessive Agency | MITIGATO | `supervisor.py:safe_invoke` + HITL |
| LLM07 | System Prompt Leakage | MITIGATO PARZIALMENTE | env var policy + auditor role |
| LLM08 | Vector/Embedding Weaknesses | MITIGATO PARZIALMENTE | ingest auth + sanitizzazione |
| LLM09 | Misinformation | MITIGATO | eval gate CI + HITL + evidence panel |
| LLM10 | Unbounded Consumption | MITIGATO PARZIALMENTE | BudgetSnapshot + recursion_limit |

**Legenda:**

- **MITIGATO:** mitigazione implementata e testata in codice
- **MITIGATO PARZIALMENTE:** mitigazione primaria implementata; gap residui documentati
- **N/A:** rischio non applicabile al perimetro tecnico SFT v1.0

Per la matrice STRIDE completa vedere [STRIDE Threat Model](stride-threat-model.md).
