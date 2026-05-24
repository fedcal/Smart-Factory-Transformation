---
phase: 11
plan: 05
subsystem: security-hardening
tags: [stride, owasp-llm, sec-hardening, env-config, rate-limit, ar-closure]
requires: [11-00, 11-01, 11-02, 11-03, 11-04]
provides: [SEC-01, SEC-02, SEC-05, AR-01-closure, AR-06-closure, AR-07-closure]
affects: [docs/security, infra/compose, .planning/phases/10]
tech-stack:
  added: []
  patterns:
    - STRIDE 6x3 matrix con code-mapped mitigations
    - OWASP LLM Top-10 mapping a codice
    - .env.example placeholder policy (SEC-05)
    - Redis rate-limit scaling path (documentation-only)
key-files:
  created:
    - docs/security/STRIDE-threat-model.md
    - docs/security/owasp-llm-top10.md
    - docs/security/rate-limit-scaling.md
    - docs/security/tests/test_stride_coverage.py
  modified:
    - infra/compose/.env.example
    - .planning/phases/10-backend-api-frontend/10-SECURITY.md
decisions:
  - AR-02/AR-03 (SSE token/localStorage) rimangono dev-mode; HttpOnly cookie deferred post-v1.0
  - LANGFUSE_ENCRYPTION_KEY rimpiazzato con placeholder testuale (prevenzione falsi positivi secret scanner)
  - Redis rate-limit documentato ma non implementato (AR-07 documentation-only)
metrics:
  duration: 25min
  completed: 2026-05-25
  tasks_completed: 3
  tasks_total: 3
  files_created: 4
  files_modified: 2
---

# Phase 11 Plan 05: Security Hardening Consolidation Summary

**One-liner:** STRIDE 6×3 matrix con 18 celle code-mapped (SC-4) + OWASP LLM Top-10 → codice + .env.example Phase 11 senza secrets + chiusura AR-01/06/07 e annotazione AR-02/03.

---

## Tasks Completati

| Task | Nome | Commit | File chiave |
|------|------|--------|-------------|
| 1 | STRIDE threat model 6x3 + test copertura (SEC-01) | e0ce972 | `docs/security/STRIDE-threat-model.md`, `docs/security/tests/test_stride_coverage.py` |
| 2 | OWASP LLM Top-10 + Redis doc + AR-01..07 (SEC-02, AR-06/07) | 9846f18 | `docs/security/owasp-llm-top10.md`, `docs/security/rate-limit-scaling.md`, `10-SECURITY.md` |
| 3 | .env.example Phase 11 senza secret hardcoded (SEC-05) | 1f9ca8b | `infra/compose/.env.example` |

---

## Cosa è Stato Realizzato

### Task 1 — STRIDE Threat Model (SEC-01, SC-4)

Creato `docs/security/STRIDE-threat-model.md`: matrice 6×3 = 18 celle, ognuna con:
- Threat descrittivo
- Mitigazione implementata
- Riferimento a codice reale (`file.py:funzione`)

Superfici analizzate: IT/OT boundary, RAG ingest, Agent orchestration.

Mitigazioni chiave citate: `sanitize_document` (SEC-04), `NatsHeaderCarrier` W3C traceparent (11-01),
`build_acl_filter` Qdrant pre-filter (SEC-07), `recursion_limit=25` (CORE-03),
`test_ot_bridge_guard` AST write-block (SEC-06), `MOTIVATION_MIN_LENGTH` HITL (10-SECURITY).

Consolidato i registri Phase 08/09/10 SECURITY.md nella sezione "Registro per-fase consolidato".

Creato `docs/security/tests/test_stride_coverage.py`: 7 test pytest — tutti 7 passano:
- Documento esiste e non vuoto
- Tutte le 6 categorie STRIDE presenti
- 18 celle totali presenti
- Ogni categoria ha 3 superfici
- Ogni cella cita almeno un file `.py` o `.ts`
- Mitigazioni chiave referenziate (sanitize_document, RESTRICTED_DOC_ACCESS, NatsHeaderCarrier, ecc.)
- Frontmatter dichiara `cells: 18`

### Task 2 — OWASP LLM Top-10 + Rate-limit Doc + AR Closure (SEC-02, AR-06/07)

Creato `docs/security/owasp-llm-top10.md`: LLM01..LLM10 mappati a mitigazioni concrete.
Tutti i 10 item coprono un file sorgente reale o una rationale "non applicabile" documentata.
Chiude AR-06 (OWASP LLM hardening deferred da Phase 10).

Creato `docs/security/rate-limit-scaling.md`: descrive il limiter in-process Phase 10
(`_alert_rate_state`, `_ALERT_RATE_LIMIT=12`, `RuntimeWarning WEB_CONCURRENCY>1`) e il path
evolutivo Redis con variabile `RATE_LIMIT_BACKEND=redis` — DOCUMENTATION-ONLY, non implementato.
Chiude AR-01 e AR-07 come documentati.

Aggiornato `10-SECURITY.md`: aggiunta sezione "Phase 11 Closure" con tabella di stato per
AR-01..AR-07. AR-02/AR-03 annotati come dev-mode con HttpOnly cookie deferred post-v1.0.

### Task 3 — .env.example Phase 11 (SEC-05)

Aggiornato `infra/compose/.env.example` con sezione "Phase 11 — Observability & Eval":
- `OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317` (consumato da `provider.py:setup_tracer_provider`)
- `OTEL_SERVICE_NAME=sft-api-gateway`
- `GRAFANA_PORT=3001` (RESEARCH Pitfall 4 — porta separata da Langfuse)
- `LANGFUSE_PUBLIC_KEY=pk-lf-placeholder-change-me` / `LANGFUSE_SECRET_KEY=sk-lf-placeholder-change-me`
- `EVAL_REAL_LLM=` (vuoto = CI gate deterministico, `MockDeepEvalLLM`)

Sostituito `LANGFUSE_ENCRYPTION_KEY=0000...` preesistente con placeholder testuale
`<CHANGE_ME_IN_PROD_run_openssl_rand_hex_32>` — prevenzione falsi positivi secret scanner regex.

Citato pattern SEC-05: `jwt.py` righe 38-53 `RuntimeError` se `API_SECRET_KEY` assente e non dev.

Verifica automatizzata: regex `(SECRET|KEY)\s*=\s*[A-Za-z0-9]{16,}` non trova match.

---

## Deviazioni dal Piano

### Auto-fixed Issues

**1. [Rule 1 - Bug] Regex secret scanner triggerata da LANGFUSE_ENCRYPTION_KEY preesistente**

- **Trovato durante:** Task 3 (verifica `env-example-ok`)
- **Issue:** Il valore `0000000000000000000000000000000000000000000000000000000000000000` (64 zeri) del campo preesistente matchava il pattern regex `[A-Za-z0-9]{16,}` del verify del piano, causando `AssertionError: possible hardcoded secret` nonostante non sia un vero secret.
- **Fix:** Sostituito il valore con il placeholder testuale `<CHANGE_ME_IN_PROD_run_openssl_rand_hex_32>` che non matcha la regex e comunica chiaramente l'azione richiesta.
- **File modificati:** `infra/compose/.env.example`
- **Commit:** 1f9ca8b

---

## Known Stubs

Nessuno — tutti i documenti di sicurezza citano mitigazioni implementate o documentano
esplicitamente i rischi residui/deferred con rationale. Nessun placeholder senza contenuto.

---

## Threat Flags

| Flag | File | Description |
|------|------|-------------|
| threat_flag: info_disclosure | `infra/compose/.env.example` | Aggiunta sezione con LANGFUSE keys — placeholder only, nessun secret reale; policy SEC-05 citata. |

---

## Requirements Chiusi

- **SEC-01:** STRIDE 6×3 code-mapped (SC-4) — CHIUSO
- **SEC-02:** OWASP LLM Top-10 mapping a codice — CHIUSO (AR-06 closed)
- **SEC-05:** .env.example Phase 11 senza secrets — CHIUSO

---

## Self-Check: PASSED

File verificati:

- `docs/security/STRIDE-threat-model.md` — FOUND
- `docs/security/owasp-llm-top10.md` — FOUND
- `docs/security/rate-limit-scaling.md` — FOUND
- `docs/security/tests/test_stride_coverage.py` — FOUND
- `infra/compose/.env.example` (modificato) — FOUND
- `.planning/phases/10-backend-api-frontend/10-SECURITY.md` (annotato) — FOUND

Commit verificati:

- `e0ce972` — FOUND (STRIDE + test)
- `9846f18` — FOUND (OWASP + rate-limit + AR)
- `1f9ca8b` — FOUND (.env.example)

Test: `pytest docs/security/tests/test_stride_coverage.py` → 7/7 PASSED
