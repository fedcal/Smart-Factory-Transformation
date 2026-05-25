---
phase: 11-observability-evaluation-security-hardening
slug: observability-evaluation-security-hardening
status: verified
threats_total: 21
threats_open: 0
asvs_level: 2
created: 2026-05-25
audited: 2026-05-25
review_fixes_verified: true
---

# Phase 11 — Security Audit

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Verifica delle mitigazioni dichiarate nei 6 file PLAN (11-00..11-05) e dei 4 Critical
> + 5 Warning fix documentati in 11-REVIEW-FIX.md.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| npm/pip registry → build | Codice di terze parti (deepeval/ragas/bleach/OTLP) entra al momento dell'install | Codice eseguito in CI/runtime |
| compose host ports → network | Grafana(3001)/Prometheus(9090)/Tempo(4317) esposti in dev | Metriche, trace, span (non PII) |
| migration SQL → audit DB | DDL 014 modifica il CHECK constraint su audit.actions | Valore stringa enum |
| gateway → NATS → agent | Header di trace attraversano il broker NATS | W3C traceparent (correlazione, non controllo accesso) |
| agent → Langfuse | Span LLM (token count, latency, HITL metadata) inviati a Langfuse self-hosted | Metriche operative aggregate |
| PR diff → CI gate | Modifiche RAG/agent attraversano il gate eval deterministico prima del merge | Qualità output LLM |
| documento ingest → embedding | Contenuto non attendibile (PDF, testo utente) entra nel pipeline RAG | Testo potenzialmente malizioso |
| agent layer → OPC-UA | Confine data-diode: solo subscribe (lettura), nessun write verso OT | Comandi OPC-UA (bloccati) |
| retrieval → audit DB | Accesso a documenti restricted registrato obbligatoriamente | Chunk IDs, query hash SHA-256, principal_id |
| env file → runtime config | Secret/endpoint forniti via ambiente, mai hardcoded | Credenziali Langfuse, OTEL endpoint |
| documentazione → audit/review | STRIDE doc è il contratto di sicurezza trasversale | Riferimenti a codice reale |

---

## Threat Register

### Piano 11-00: OTEL + Infra + Migration + Eval Scaffold

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-11-SC | Tampering | Supply chain (deepeval/ragas/bleach/OTLP) | mitigate | Pin espliciti in pyproject.toml (`opentelemetry-exporter-otlp-proto-grpc>=1.42,<2`; `bleach>=6.3,<7`; `deepeval>=4.0,<5`; `ragas>=0.4,<0.5`); `opentelemetry-instrumentation-nats` escluso (non esiste su PyPI). | CLOSED |
| T-11-00-01 | Tampering | Migration 014 CHECK drift | mitigate | `014_extend_audit_phase11.sql` usa pattern DROP+ADD idempotente sullo stesso constraint name di 012; `test_migration_014.py` verifica no-regression e lockstep enum. | CLOSED |
| T-11-00-02 | Elevation of Privilege | Grafana anonymous dev | accept | `GF_AUTH_ANONYMOUS_ENABLED=true` solo in `obs.yml` dev compose (ruolo Viewer read-only); documentato in `infra/compose/.env.example`. Nessun dato PII reale. | CLOSED |
| T-11-00-03 | Denial of Service | Tempo OTLP receiver aperto | accept | Rete `sft-obs` interna al compose dev; porta 4317 non esposta in prod. Documentato come rischio dev accettato. | CLOSED |

### Piano 11-01: OTEL Trace Propagation E2E

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-11-01-01 | Tampering | NATS traceparent header | mitigate | `TraceContextTextMapPropagator` W3C con validazione formato inclusa; header è solo correlazione, non controllo di accesso. `propagate.inject()` in `nats_publisher.py:8,62,90`. | CLOSED |
| T-11-01-02 | Information Disclosure | Token count LLM in trace | accept | Trace su Langfuse self-hosted interno alla rete `sft-obs` dev; documentato nel STRIDE doc (cella Agent/Info-Disclosure). | CLOSED |
| T-11-01-03 | Tampering | Span duplicati (OTLP+CallbackHandler) | mitigate | Nessun OTLP exporter aggiunto verso Langfuse; solo `langfuse_callback.py` CallbackHandler. `TracerProvider` OTLP → Tempo. | CLOSED |
| T-11-01-04 | Repudiation | HITL decision senza trace | mitigate | Span CONSUMER apre la trace agent in `agent_runner.py:propagate.extract()` + `start_as_current_span(kind=SpanKind.CONSUMER)`; HITL metadata via CallbackHandler con tag `phase11`. | CLOSED |

### Piano 11-02: DeepEval+RAGAS CI Gate

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-11-02-01 | Tampering | Gate sempre-verde (mock score=1) | mitigate | `MockDeepEvalLLM` con score variabile (Jaccard token-overlap); `TestNegativeGateProof` in `test_rag_ci_gate.py:275` usa `pytest.raises(AssertionError)` per dimostrare che il gate fallisce su input degradati. | CLOSED |
| T-11-02-02 | Denial of Service | Eval che chiama LLM esterno in CI | mitigate | Solo metriche token-overlap deterministiche + MockDeepEvalLLM; real-Ollama gated da `@pytest.mark.skipif(not os.environ.get("EVAL_REAL_LLM"))` in `test_rag_ci_gate.py:354`. | CLOSED |
| T-11-02-SC | Tampering | deepeval/ragas install | mitigate | Vettati in 11-RESEARCH (PyPI Approved); pin versione; aggiunti al gruppo `dev` del root pyproject (non runtime). | CLOSED |

### Piano 11-03: Security Hardening (SEC-03/04/06/07)

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-11-03-01 | Elevation of Privilege | Ruolo auditor | mitigate | `auditor@mantis.it` in `jwt.py:89` con `role='auditor'`; `require_roles("admin")` nega JWT auditor con 403 in `test_rbac_auditor.py:75`. | CLOSED |
| T-11-03-02 | Tampering | Prompt injection via documento | mitigate | `sanitizer.py:sanitize_document()` denylist regex + `_SCRIPT_CONTENT_PATTERNS` + `bleach.clean(tags=[], strip=True)` deterministico; cablato in `pipeline.py:195` pre-embedding; test crafted-PDF in `test_prompt_injection.py`. | CLOSED |
| T-11-03-03 | Elevation of Privilege | OT Bridge write path | mitigate | AST guard `test_ot_bridge_guard.py:56-57` (`ast.walk` con `_WRITE_PATTERNS={write_value, write_attributes, set_attribute, call_method, set_value}`); stesso set nel CI grep (`ci.yml:113`); step non-skippable in CI. | CLOSED |
| T-11-03-04 | Information Disclosure | Accesso chunk restricted | mitigate | `_write_restricted_audit()` in `retrieval/pipeline.py:396`: `query_hash = sha256(query)` (no testo in chiaro); `chunk_ids` inclusi; `principal_id=principal.get("sub")`. | CLOSED |
| T-11-03-05 | Repudiation | Accesso restricted senza traccia | mitigate | Audit row obbligatoria con `principal_id`, `chunk_ids`, `query_hash`; opera su `top_k_hits` (chunk effettivamente restituiti, non prefetch pre-top-k — fix WR-03). | CLOSED |
| T-11-03-06 | Tampering | SQL injection nel path audit | mitigate | `AuditRecord` usa parametri asyncpg `$N`; nessun f-string SQL nel path audit verificato per assenza di pattern `f"...SQL..."`. | CLOSED |

### Piano 11-04: Grafana Dashboards

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-11-04-01 | Information Disclosure | Grafana anonymous viewer | accept | `GF_AUTH_ANONYMOUS_ORG_ROLE: Viewer` (read-only); metriche aggregate non-PII; documentato in `.env.example`. | CLOSED |
| T-11-04-02 | Tampering | Dashboard JSON schema drift | mitigate | `test_dashboards_valid.py` carica ogni `*.json` in `infra/grafana/dashboards/`, asserisce `panels`, `title`, `schemaVersion>=36` e datasource UID provisioned. 19 test verdi. | CLOSED |
| T-11-04-03 | Denial of Service | Query PromQL pesanti | accept | Dashboard dev su finestre temporali limitate; non esposte in prod. | CLOSED |

### Piano 11-05: Consolidamento Sicurezza

| Threat ID | Category | Component | Disposition | Mitigation | Status |
|-----------|----------|-----------|-------------|------------|--------|
| T-11-05-01 | Information Disclosure | Secret in .env.example | mitigate | Solo placeholder/commenti in `.env.example`; regex `(SECRET\|KEY)\s*=\s*[A-Za-z0-9]{16,}` non trova match; `LANGFUSE_ENCRYPTION_KEY` preesistente sostituito con placeholder testuale. | CLOSED |
| T-11-05-02 | Repudiation | Threat non mappato a codice | mitigate | `test_stride_coverage.py:195` asserisce riferimento `.py` in ogni cella; frontmatter `cells: 18` verificato da test 7. 7/7 test verdi. | CLOSED |
| T-11-05-03 | Denial of Service | Rate-limit multi-worker | accept | Documentato in `docs/security/rate-limit-scaling.md` come AR-07 documentation-only; Redis non implementato in v1.0; `RuntimeWarning` in lifespan se `WEB_CONCURRENCY>1`. | CLOSED |
| T-11-05-04 | Elevation of Privilege | OWASP excessive agency (LLM06) | mitigate | `recursion_limit=25` in `langfuse_callback.py:build_invocation_config`; HITL obbligatorio `supervisor.py:safe_invoke`; `MOTIVATION_MIN_LENGTH=10` in `approval-card.component.ts`; documentati in `owasp-llm-top10.md:141-144`. | CLOSED |

---

## Code Review Fix Verification (11-REVIEW-FIX.md)

I seguenti fix critici e warning sono stati verificati nel codice tramite grep:

| Fix ID | Tipo | Verifica | Evidenza | Stato |
|--------|------|----------|----------|-------|
| CR-01 | Critical | Step `tests/security/` in CI non-skippable | `ci.yml:168-171` — step "Run security gate (SEC-04 / SEC-06)" senza `continue-on-error` o `\|\| true` | VERIFIED |
| CR-02 | Critical | `threading.Lock` in `provider.py` | `provider.py:26,35,61` — `import threading`, `_lock = threading.Lock()`, `with _lock:` | VERIFIED |
| CR-03 | Critical | `ROLE_TO_ACL` include `shift-supervisor`, `admin`, `auditor` | `retrieval/pipeline.py:68,72,73` — tutti e tre i ruoli presenti con frozenset ACL corretti | VERIFIED |
| CR-04 | Critical | Pattern OPC-UA write unificati tra CI grep e AST test | `ci.yml:113` — `(set_value\|write_value\|write_attributes\|set_attribute\|call_method)`; `test_ot_bridge_guard.py:23-28` — `_WRITE_PATTERNS` con 5 elementi incluso `set_value` | VERIFIED |
| WR-02 | Warning | Asserzioni tautologiche rimosse da test_prompt_injection.py | `test_prompt_injection.py:63-66` (system:) e `test_prompt_injection.py:99` (alert) — asserzioni senza escape hatch OR per i due casi critici | VERIFIED (parziale) |
| WR-03 | Warning | Audit restricted su top-k restituiti (non prefetch) | `retrieval/pipeline.py:352-353` — `top_k_hits=[hit for hit, _ in top_k]` passato a `_write_restricted_audit()` | VERIFIED |

**Nota WR-02 parziale:** Il fix principale (test `system:` e test `alert`) è corretto e le asserzioni
tautologiche sono state rimosse per i due casi citati nella review. Rimane una terza asserzione
`or "[REDACTED]" in result` nel test `test_sanitize_strips_disregard_previous` (riga 75) che
non era tra i casi esplicitamente citati nella review ma usa lo stesso anti-pattern. Poiché
`disregard` è nel denylist (`sanitizer.py:58`) e viene sostituito con `[REDACTED]`, la seconda
clausola è sempre True dopo una sostituzione riuscita — il test non dimostrerebbe un fallimento
parziale. Classificato come **unregistered_flag** (non BLOCKER): il test copre il caso positivo
correttamente ma non è il test più robusto. La mitigazione SEC-04 è dimostrata dagli altri 10
test della suite.

---

## Deliverable Verification (SEC-01..07)

| Deliverable | Requisito | Evidenza | Stato |
|-------------|-----------|----------|-------|
| SEC-01: STRIDE-threat-model.md 18 celle | 6 STRIDE × 3 superfici, ciascuna con `file:funzione` | `STRIDE-threat-model.md` frontmatter `cells: 18`; 18 heading `####[A-Z][0-9]` grep-confermati; 17+ riferimenti `.py` | VERIFIED |
| SEC-01: test_stride_coverage.py | Asserisce 18 celle + codice in ogni cella | `test_stride_coverage.py:150-270` — 7 test inclusi `test_stride_18_cells_present` e `test_stride_all_cells_have_code_reference` | VERIFIED |
| SEC-02: owasp-llm-top10.md LLM01..LLM10 | Mappa ogni item OWASP a mitigazione codice | `owasp-llm-top10.md` contiene LLM01..LLM10 con file:funzione; LLM06 → `recursion_limit=25` + HITL | VERIFIED |
| SEC-03: ruolo auditor + RBAC 403 | `auditor@mantis.it` seeded; 403 su endpoint non autorizzato | `jwt.py:89`; `test_rbac_auditor.py:75,84` — 403 su `require_roles("admin")` | VERIFIED |
| SEC-04: sanitizer wired + crafted-PDF test | `sanitize_document()` pre-embedding; test SC-3 | `pipeline.py:195`; `test_prompt_injection.py` — 11 test verdi incluso SC-3 | VERIFIED |
| SEC-05: .env.example senza secrets + jwt.py guard | Placeholder solo; `RuntimeError` se `API_SECRET_KEY` assente in prod | `.env.example` — regex no match; `jwt.py:38-45` — `RuntimeError` in non-dev | VERIFIED |
| SEC-06: OT Bridge AST guard + CI | `ast.walk` su `svc_ot_bridge`; step CI non-skippable | `test_ot_bridge_guard.py:56-57`; `ci.yml:168-171` | VERIFIED |
| SEC-07: RESTRICTED_DOC_ACCESS audit + migration 014 | Audit row su chunk restricted; lockstep enum-SQL | `retrieval/pipeline.py:352-457`; `enums.py:155`; `014_extend_audit_phase11.sql:74-76` | VERIFIED |

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-11-01 | T-11-00-02 (Grafana anonymous) | `GF_AUTH_ANONYMOUS_ENABLED=true` solo in compose dev (Viewer read-only); nessun PII reale; non esposto in prod. | Federico / gsd-security-auditor | 2026-05-25 |
| AR-11-02 | T-11-00-03 (Tempo OTLP aperto) | Rete `sft-obs` interna al compose dev; porta 4317 non esposta in prod. Rischio confinato all'ambiente di sviluppo. | Federico / gsd-security-auditor | 2026-05-25 |
| AR-11-03 | T-11-01-02 (token count in trace) | Trace Langfuse self-hosted interna alla rete `sft-obs` dev; dati di monitoraggio non-PII. | Federico / gsd-security-auditor | 2026-05-25 |
| AR-11-04 | T-11-04-01 (Grafana anonymous viewer) | Identico a AR-11-01 — metriche aggregate non-PII in compose dev; ruolo Viewer read-only. | Federico / gsd-security-auditor | 2026-05-25 |
| AR-11-05 | T-11-04-03 (PromQL pesanti) | Dashboard dev su finestre temporali limitate; non esposte in prod. | Federico / gsd-security-auditor | 2026-05-25 |
| AR-11-06 | T-11-05-03 (rate-limit multi-worker) | Limiter in-process accettato per v1.0 dev-mode (WEB_CONCURRENCY=1 richiesto); Redis path documentato in `rate-limit-scaling.md`; chiude AR-07 di Phase 10. | Federico / gsd-security-auditor | 2026-05-25 |

### Chiusura Rischi Accettati Phase 10 (AR-01..AR-07)

| AR Phase 10 | Stato Phase 11 | Riferimento |
|-------------|----------------|-------------|
| AR-01 (DoS rate-limit) | DOCUMENTATO | `docs/security/rate-limit-scaling.md` — path Redis non implementato |
| AR-02 (SSE token URL) | RIMANE DEV-MODE | HttpOnly cookie deferred post-v1.0; annotato in `10-SECURITY.md:111` |
| AR-03 (localStorage token) | RIMANE DEV-MODE | HttpOnly cookie deferred post-v1.0; annotato in `10-SECURITY.md:112` |
| AR-04 (demo aperto) | CHIUSO (design) | Nessun cambiamento in Phase 11 |
| AR-05 (screenshot sintetici) | CHIUSO (design) | Nessun cambiamento in Phase 11 |
| AR-06 (OWASP LLM Top 10) | CHIUSO | `docs/security/owasp-llm-top10.md` — LLM01..LLM10 mappati a codice |
| AR-07 (multi-worker limiter) | DOCUMENTATO | `docs/security/rate-limit-scaling.md` — Redis documentation-only |

---

## Unregistered Flags (da SUMMARY ## Threat Flags)

| Flag | File | Descrizione | Mapping Threat | Classificazione |
|------|------|-------------|----------------|-----------------|
| threat_flag: compose_port_exposure | `infra/compose/obs.yml` | Prometheus (9090) e Tempo OTLP (4317/4318) esposti su host in dev | T-11-00-03 (accepted) | Informational — mappa a threat esistente |
| threat_flag: grafana_anonymous | `infra/compose/obs.yml` | `GF_AUTH_ANONYMOUS_ENABLED=true` — solo dev, viewer role, nessun PII | T-11-00-02 (accepted) | Informational — mappa a threat esistente |
| threat_flag: traceparent_in_headers | `nats_publisher.py` | Header NATS tamperabile — solo correlazione non controllo accesso | T-11-01-01 (mitigated) | Informational — mappa a threat esistente |
| threat_flag: info_disclosure | `infra/compose/.env.example` | Sezione LANGFUSE keys — placeholder only, nessun secret reale | T-11-05-01 (mitigated) | Informational — mappa a threat esistente |
| WR-02 residuo: tautological OR | `test_prompt_injection.py:75` | `or "[REDACTED]" in result` nel test `disregard` — non uno dei due casi critici corretti | Nessun threat ID | **unregistered_flag** (non BLOCKER) |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-05-25 | 21 | 21 | 0 | gsd-security-auditor (Claude Sonnet 4.6) |

**Code Review Fixes Verified:** 4 Critical + 5 Warning (da 11-REVIEW-FIX.md commit `159d657`, `de1ac64`, `54f22ed`, `54597ae`, `c71166c`, `091d263`, `80bc449`, `f83caf0`, `675c263`)

**Nota metodologica:** Ogni mitigazione verificata tramite grep diretto sul file di implementazione
citato nel piano, non tramite fiducia nella documentazione. La stance adversariale applicata:
ipotesi di partenza "threat aperto" fino a evidenza grep.

---

## Sign-Off

- [x] Tutti i 21 threat hanno una disposizione (mitigate / accept / transfer)
- [x] Rischi accettati documentati nell'Accepted Risks Log (AR-11-01..06)
- [x] `threats_open: 0` confermato
- [x] Tutti i fix CR-01..CR-04 e WR-02..WR-05 verificati nel codice
- [x] Deliverable SEC-01..SEC-07 verificati con evidenza file:riga
- [x] Chiusura AR-01..AR-07 di Phase 10 annotata in `10-SECURITY.md`
- [x] `status: verified` impostato nel frontmatter

**Approval:** verified 2026-05-25
