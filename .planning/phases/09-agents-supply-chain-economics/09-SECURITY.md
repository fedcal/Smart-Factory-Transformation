---
phase: 9
slug: agents-supply-chain-economics
status: verified
threats_total: 29
threats_open: 0
asvs_level: standard
created: 2026-05-24
audited_by: gsd-security-auditor (claude-sonnet-4-6)
---

# Phase 9 — Security Audit

> Contratto di sicurezza per la fase 9 (Supply Chain & Economics).
> Registro minacce, rischi accettati e trail di audit.
> Nota: SEC-02 (OWASP LLM hardening completo) è deferred by design alla Phase 11;
> qui viene verificata solo la mitigazione scoped per la fase 9 (logica LLM-free).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| HTTP client → API Gateway | Request bodies POST su 7 endpoint supply | sku_ids, datetime tz-aware, ribasso_pct, user_roles |
| Gateway → LangGraph supply subgraph | state dict con target_agent | AgentState con parametri SCM |
| Supply agents → asyncpg pool | Query SQL parametrizzate su scm.* | datetime, text[], numeric — mai f-string |
| Interrupt boundary | LangGraph checkpoint + resume payload | recommendation/proposal/plan_id |
| Audit trail | AuditRecord scritto DOPO interrupt() | ActionType, Decision, approval_id |

---

## Threat Register

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-09-01 | Tampering | migration 012 CHECK — regressione legacy | mitigate | 22 test parametrizzati in test_migration_012.py ammettono tutti i valori Phase 1-8 | CLOSED |
| T-09-02 | Tampering | enum/SQL lockstep drift | mitigate | 012_extend_audit_scm.sql + enums.py: 8 valori byte-identici verificati | CLOSED |
| T-09-03 | Tampering | scm.* category/process CHECK | mitigate | DDL CHECK IN ('raw_yarn','accessory','spare_part','fabric') e IN ('dyeing','finishing','spinning','weaving','other') in 011_create_scm_schema.sql | CLOSED |
| T-09-04 | Tampering | test scaffold completeness | mitigate | 9 file di test presenti (2×inventory, 2×energy, 2×cost, 3×demand); nessun module-level skip | CLOSED |
| T-09-05 | Tampering | HITL replay correctness | mitigate | test_inventory_hitl.py: stable-id + interrupt-then-audit + single-write encoding CR-02/CR-04 | CLOSED |
| T-09-06 | Tampering | unknown target routing | mitigate | _route() fallback a cost-analyzer (read-only) con structlog warning in clusters.py:408-413 | CLOSED |
| T-09-07 | Denial of Service | missing fallback agent | mitigate | build_supply_subgraph() raise ValueError se cost-analyzer absent (clusters.py:388-392) | CLOSED |
| T-09-08 | Information Disclosure | synthetic data mislabeled | mitigate | Header bilancio IT+EN in scm_mantis_seed.sql riga 2-9 + SCM-05 docs espliciti | CLOSED |
| T-09-09 | Tampering | reorder SQL sku_id params | mitigate | _SQL_CURRENT_LEVELS usa ANY($1::text[]) senza interpolazione (repository.py:35-48) | CLOSED |
| T-09-10 | Repudiation | HITL audit correlation InventoryManager | mitigate | sha256(AGENT_ID.thread_id)[:32] → recommendation_id stabile; AuditRecord posizionale (agent.py:132-149) | CLOSED |
| T-09-11 | Tampering | double-write on replay | mitigate | interrupt-then-audit ordering: 0 write pre-interrupt; test asserts 1 DRAFT + 1 SIGNOFF (agent.py:351-401) | CLOSED |
| T-09-12 | Tampering | energy-readings window SQL | mitigate | _SQL_READINGS usa $1/$2/$3 parametrizzati; datetime passati come oggetti (non .isoformat()) a asyncpg riga 106 | CLOSED |
| T-09-13 | Repudiation | HITL audit correlation EnergyOptimizer | mitigate | sha256(AGENT_ID.thread_id)[:32] → proposal_id stabile; AuditRecord posizionale (agent.py:141-158) | CLOSED |
| T-09-14 | Tampering | EnPI overflow frozen model | mitigate | compute_enpi() guard kg>0 + ValueError su no-valid-slot (enpi.py:82-88); EnpiReport frozen dataclass | CLOSED |
| T-09-15 | Tampering | OEPV input ranges | mitigate | compute_oepv() ValueError su ribasso_pct∉[0,100] e pt∉[0,pt_max] (oepv.py:121-129) | CLOSED |
| T-09-16 | Repudiation | autonomous cost row | mitigate | Singola riga Decision.AUTO COST_REPORT posizionale; no interrupt; no replay double-write (agent.py:155-240) | CLOSED |
| T-09-17 | Elevation of Privilege | OEPV anomaly threshold misread | accept | Documentato come warning configurabile, non regola Codice Appalti; docstring esplicita in oepv.py:1-18 | CLOSED |
| T-09-18 | Tampering | monthly-orders SQL | mitigate | _SQL_MONTHLY_ORDERS usa $1/$2 parametrizzati; DATE_TRUNC aggregation (repository.py:35-43) | CLOSED |
| T-09-19 | Repudiation | HITL audit correlation DemandForecaster | mitigate | sha256(AGENT_ID.thread_id)[:32] → plan_id stabile; AuditRecord posizionale (agent.py:160-178) | CLOSED |
| T-09-20 | Tampering | MAPE overflow frozen model | mitigate | Per-point clamp a 1.0 + clamp finale ≤100.0 in compute_mape() (mape.py:46-48); MapeReport CR-05 | CLOSED |
| T-09-21 | Tampering | cross-cluster plan injection | accept | demand_plan pubblicato via state solo dopo supervisor sign-off; ProductionPlanner re-validates in Phase 10 | CLOSED |
| T-09-22 | Tampering | request payloads | mitigate | ConfigDict(frozen=True, extra="forbid") + @field_validator tz-aware su tutti i 7 modelli (supply_agents.py:96-298) | CLOSED |
| T-09-23 | Information Disclosure | 500 error body | mitigate | _handle_agent_error restituisce {"error":"internal_agent_error"}; str(exc) solo nel logger (supply_agents.py:320-334) | CLOSED |
| T-09-24 | Denial of Service | unbounded recursion | mitigate | _RECURSION_LIMIT=5 in tutti i 7 build_invocation_config; _handle_recursion_error→503 (supply_agents.py:64-317) | CLOSED |
| T-09-25 | Spoofing/EoP | endpoint auth + ACL | accept | Dev-mode user_roles in body propagato nello state; JWT/RBAC deferred Phase 11 (WR-03 mantiene il campo) | CLOSED |
| T-09-26 | Repudiation | per-agent audit completeness | mitigate | E2E asserts conteggi esatti DRAFT/SIGNOFF/AUTO e correlation id stabili per agent (test_supply_cluster_e2e.py:190-665) | CLOSED |
| T-09-27 | Tampering | replay double-write | mitigate | E2E simula replay idempotency; assert len(audit_events) invariato dopo secondo resume (test_supply_cluster_e2e.py:327-341) | CLOSED |
| T-09-28 | Information Disclosure | synthetic data mislabeled | mitigate | Banner bilingue prominente in mantis-synthetic-dataset.md (IT) riga 16 e (EN) riga 16; grep zero occorrenze "real" senza disclaimer | CLOSED |
| T-09-29 | Repudiation | brand reference leak | mitigate | grep zero occorrenze "accenture" (case-insensitive) in docs/docs/agents/supply/ IT+EN verificato | CLOSED |
| T-09-SC (×9) | Tampering/Supply-Chain | npm/pip/cargo installs + OWASP LLM | accept/mitigate | Nessun nuovo pacchetto installato in Phase 9; numpy pre-approvato in sft-ml; logica supply LLM-free (Inventory/Cost/Demand) o LLM-rationale-only (Energy) — nessuna dipendenza da modello esterno | CLOSED |

*Status: open · closed*
*Disposition: mitigate (implementazione richiesta) · accept (rischio documentato) · transfer (terza parte)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-09-01 | T-09-17 | La soglia anomalia OEPV è un WARNING configurabile (OepvConfig.anomaly_threshold_pct), non la regola definitiva del Codice Appalti 2023. La precisione legale è demandata a Phase 12 (F12). La docstring in oepv.py righe 1-18 documenta esplicitamente questo confine. | Phase 9 executor + auditor | 2026-05-24 |
| AR-09-02 | T-09-21 | Cross-cluster plan injection: il demand_plan viene pubblicato via state['demand_plan'] solo dopo supervisor sign-off (HITL interrupt pattern). La validazione lato ProductionPlanner è prevista in Phase 10. Il confine è la re-entry a un agente ops di sola lettura via state, non una chiamata diretta. | Phase 9 executor + auditor | 2026-05-24 |
| AR-09-03 | T-09-25 | Auth endpoint (JWT/RBAC): in Phase 9 i user_roles sono trasmessi nel body della richiesta in modalità dev (WR-03 garantisce che il campo sia presente per la retrocompatibilità). Il rafforzamento JWT/RBAC è deferred by design a Phase 11. | Phase 9 executor + auditor | 2026-05-24 |
| AR-09-04 | T-09-SC (accept plans) | Nessun nuovo pacchetto installato in Phase 9. numpy è già pre-approvato nel workspace sft-ml. statsmodels considerato e deciso di non usare. L'audit di legittimità è documentato nel RESEARCH.md Package Legitimacy Audit. | Phase 9 executor + auditor | 2026-05-24 |
| AR-09-05 | T-09-SC (09-06 SEC-02) | SEC-02 (OWASP LLM Top-10 hardening completo) è un milestone-level requirement deferred a Phase 11 per design (REQUIREMENTS.md). La mitigazione scoped in Phase 9 è sufficiente: logica core supply è LLM-free (Inventory/Cost/Demand) o LLM-rationale-only (Energy), con parametri OEPV da config e nessuna dipendenza da modello esterno. | Phase 9 executor + auditor | 2026-05-24 |

*I rischi accettati non riemergono nelle esecuzioni di audit future.*

---

## Unregistered Threat Flags

Nessuna flag non mappata. Tutti i Threat Flags nei SUMMARY.md di questa fase sono mappati a threat ID registrati nel threat register sopra, o dichiarati esplicitamente come "None" dall'executor.

---

## Notes on Deferred Items

**SEC-02 → Phase 11 (transfer per milestone design)**
Il requisito REQUIREMENTS.md SEC-02 (OWASP LLM Top-10 supply-chain hardening completo) è progettato per essere implementato in Phase 11. In Phase 9 la mitigazione è sufficiente per il perimetro dichiarato: nessun agente supply ha dipendenze da modelli LLM esterni (tutti LLM-free o LLM-rationale-only con LLM locale). Questo non costituisce un gap aperto — è una scelta architetturale documentata e accettata (AR-09-05).

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-24 | 29 | 29 | 0 | gsd-security-auditor / claude-sonnet-4-6 |

---

## Evidence Summary per Threat

### Mitigazioni verificate via grep / lettura codice

| Threat ID | File verificato | Riga chiave |
|-----------|----------------|-------------|
| T-09-01 | infra/migrations/timescale/tests/test_migration_012.py | 22 test legacy parametrizzati |
| T-09-02 | infra/migrations/timescale/012_extend_audit_scm.sql + packages/sft-agents/src/sft_agents/models/enums.py | 8 valori byte-identici |
| T-09-03 | infra/migrations/timescale/011_create_scm_schema.sql | righe 40, 77 CHECK IN |
| T-09-04 | apps/agents/supply/*/tests/ | 9 file test presenti, nessun module-skip |
| T-09-05 | apps/agents/supply/inventory-manager/tests/test_inventory_hitl.py | righe 1-18 (contratti CR-02/CR-04) |
| T-09-06 | packages/sft-agents/src/sft_agents/runtime/clusters.py | righe 404-413 _route() fallback |
| T-09-07 | packages/sft-agents/src/sft_agents/runtime/clusters.py | righe 388-392 ValueError |
| T-09-08 | infra/migrations/timescale/seed/scm_mantis_seed.sql | righe 2-9 header bilingue |
| T-09-09 | apps/agents/supply/inventory-manager/src/scm_inventory_manager/repository.py | righe 35-48 ANY($1::text[]) |
| T-09-10 | apps/agents/supply/inventory-manager/src/scm_inventory_manager/agent.py | righe 132-149 sha256 + riga 225 posizionale |
| T-09-11 | apps/agents/supply/inventory-manager/src/scm_inventory_manager/agent.py | righe 351-401 post-interrupt |
| T-09-12 | apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/repository.py | righe 39-51 $1/$2/$3; riga 106 oggetti datetime diretti ad asyncpg |
| T-09-13 | apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/agent.py | righe 141-158 sha256 stabile |
| T-09-14 | apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/enpi.py | righe 82-88 guard kg>0 + ValueError |
| T-09-15 | apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/oepv.py | righe 121-129 ValueError range |
| T-09-16 | apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/agent.py | righe 155-240 Decision.AUTO posizionale |
| T-09-18 | apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/repository.py | righe 35-43 $1/$2 parametrizzati |
| T-09-19 | apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/agent.py | righe 160-178 sha256 stabile |
| T-09-20 | apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/mape.py | righe 43-48 clamp per-point + finale |
| T-09-22 | apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py | righe 96,114,139,174,199,251,282 frozen+extra=forbid |
| T-09-23 | apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py | righe 320-334 corpo generico |
| T-09-24 | apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py | riga 64 _RECURSION_LIMIT=5; 7 endpoint con recursion_limit |
| T-09-26 | apps/api-gateway/tests/test_supply_cluster_e2e.py | righe 190-665 conteggi per-agent |
| T-09-27 | apps/api-gateway/tests/test_supply_cluster_e2e.py | righe 327-341 replay no-double-write |
| T-09-28 | docs/docs/agents/supply/mantis-synthetic-dataset.md + docs/docs/en/agents/supply/mantis-synthetic-dataset.md | riga 16 banner SYNTHETIC |
| T-09-29 | docs/docs/agents/supply/ (IT+EN) | grep zero "accenture" verificato |
| T-09-SC (09-06) | apps/agents/supply/*/src/ | nessun import openai/anthropic/httpx; llm=None su tutti gli agenti |

---

## Sign-Off

- [x] Tutte le minacce hanno una disposition (mitigate / accept / transfer)
- [x] Rischi accettati documentati nell'Accepted Risks Log (AR-09-01..AR-09-05)
- [x] `threats_open: 0` confermato
- [x] `status: verified` impostato nel frontmatter
- [x] Elementi deferred a Phase 11 (SEC-02, JWT/RBAC) documentati come accepted risk, non come gap aperti

**Approval:** verified 2026-05-24
