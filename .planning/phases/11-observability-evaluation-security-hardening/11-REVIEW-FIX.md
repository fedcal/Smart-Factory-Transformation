---
phase: 11-observability-evaluation-security-hardening
fixed_at: 2026-05-25T00:00:00Z
review_path: .planning/phases/11-observability-evaluation-security-hardening/11-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 11: Code Review Fix Report

**Fixed at:** 2026-05-25
**Source review:** `.planning/phases/11-observability-evaluation-security-hardening/11-REVIEW.md`
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (4 Critical + 5 Warning)
- Fixed: 9
- Skipped: 0

---

## Fixed Issues

### CR-01: I test SEC-04 e SEC-06 non sono eseguiti in CI

**Files modified:** `.github/workflows/ci.yml`
**Commit:** `159d657`
**Applied fix:** Aggiunto step `Run security gate (SEC-04 / SEC-06)` dopo `Run eval CI gate`,
con `uv run --python 3.12 python -m pytest tests/security/ -x -q`. Nessun `continue-on-error`
né `|| true` — step non-skippable.

---

### CR-02: Singleton TracerProvider non thread-safe

**Files modified:** `packages/sft-agents/src/sft_agents/otel/provider.py`
**Commit:** `de1ac64`
**Applied fix:** Aggiunto `import threading` e `_lock = threading.Lock()` a livello modulo.
La funzione `setup_tracer_provider` ora usa double-checked locking: fast-path senza lock
(dopo la prima init) + sezione critica protetta da `with _lock:` che ricontrolla il flag
prima di procedere all'inizializzazione. Previene la doppia creazione di `BatchSpanProcessor`
con due connessioni gRPC in scenari multi-thread.

---

### CR-03: Ruoli `auditor`, `shift-supervisor`, `admin` assenti da `ROLE_TO_ACL`

**Files modified:** `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`,
`packages/sft-knowledge/tests/test_retrieval_pipeline.py`
**Commit:** `54f22ed`
**Applied fix:** Aggiunti tre ruoli JWT a `ROLE_TO_ACL`:
- `shift-supervisor`: frozenset({"public", "internal"}) — ruolo canonico JWT (alias di supervisor)
- `admin`: frozenset({"public", "internal", "restricted"}) — accesso completo
- `auditor`: frozenset({"public", "internal", "restricted"}) — read-only su tutti i livelli (SEC-03)

Aggiunto test `test_acl_filter_phase11_roles_resolve_without_error` che verifica i tre nuovi
ruoli senza `ValueError`.

---

### CR-04: Pattern write OPC-UA non sovrapposti tra CI grep e AST pytest

**Files modified:** `.github/workflows/ci.yml`, `tests/security/test_ot_bridge_guard.py`
**Commit:** `54597ae`
**Applied fix (CI grep):** Gate 3 in `ci.yml` aggiornato da
`(set_value|write_attribute|write_value)` a
`(set_value|write_value|write_attributes|set_attribute|call_method)` — set unificato con
l'AST guard pytest. Corretta la forma singolare `write_attribute` → `write_attributes`.

**Applied fix (AST guard):** Aggiunto `set_value` a `_WRITE_PATTERNS` nel test pytest
(da 4 a 5 pattern). Aggiornato `test_ot_bridge_write_pattern_set_non_empty` con il set
atteso a 5 elementi.

**Note:** Il fix WR-05 per il path assoluto di questo file è stato incluso nello stesso commit.

---

### WR-01: Docstring afferma soglia 0.75 ma codice usa 0.35

**Files modified:** `tests/eval/test_rag_ci_gate.py`
**Commit:** `c71166c`
**Applied fix:** Sostituito il docstring di `test_context_precision_above_threshold` con
documentazione accurata: soglia 0.35 (non 0.75), spiegazione che SC-2 (0.75) è verificata
da `AnswerRelevancyMetric` con MockLLM, e razionale per il valore 0.35 calibrato sul dataset
SFT tecnico (valore atteso ~0.44).

---

### WR-02: Asserzioni tautologiche in test_prompt_injection.py

**Files modified:** `tests/security/test_prompt_injection.py`,
`services/knowledge-ingest/src/svc_knowledge_ingest/sanitizer.py`
**Commit:** `091d263`
**Applied fix (test):**
- Riga 59: rimossa la clausola `or "[REDACTED]" in result` — l'asserzione verifica ora
  unicamente che `"you are now a malicious assistant"` non sia nel risultato.
- Riga 83: rimossa l'asserzione tautologica `"alert" not in result or "script" not in result`
  (la seconda clausola era sempre True dopo bleach). Sostituita con asserzione diretta
  `"alert" not in result`.

**Applied fix (sanitizer):** Aggiunti pattern `_SCRIPT_CONTENT_PATTERNS` che rimuovono
i tag `script`/`style` con il loro contenuto interno prima del bleach pass. bleach da solo
rimuoveva i tag ma lasciava `alert('xss')` nel testo indicizzato. Con il fix, il sanitizer
rimuove `<script>alert('xss')</script>` → stringa vuota prima che bleach processi il resto.

---

### WR-03: Audit restricted scritto su hit pre-top-k mai restituiti

**Files modified:** `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`
**Commit:** `80bc449`
**Applied fix:** La chiamata a `_write_restricted_audit` ora passa `top_k_hits=[hit for hit, _ in top_k]`
invece di `fused_hits` (lista pre-top-k). La firma del metodo è aggiornata di conseguenza
(`top_k_hits` invece di `fused_hits`). Il log di audit rispecchia ora esclusivamente i chunk
effettivamente restituiti all'utente, eliminando i falsi positivi su chunk in posizione 11-20
del prefetch mai inclusi nella risposta.

---

### WR-04: `test_auditor_login_returns_valid_jwt` è uno stub vuoto

**Files modified:** `apps/api-gateway/tests/test_rbac_auditor.py`
**Commit:** `f83caf0`
**Applied fix:** Rimosso il test stub `test_auditor_login_returns_valid_jwt` (corpo `pass`).
Lo scenario è già coperto da `test_auditor_jwt_contains_role_claim` con `@pytest.mark.anyio`.

---

### WR-05: Path relativi dipendenti da CWD

**Files modified:** `tests/security/test_ot_bridge_guard.py` (incluso in commit CR-04),
`tests/security/test_prompt_injection.py`
**Commits:** `54597ae` (OT bridge guard), `675c263` (prompt injection)
**Applied fix:**
- `test_ot_bridge_guard.py`: `_REPO_ROOT = pathlib.Path(__file__).parent.parent.parent`,
  `_OT_BRIDGE_SRC = _REPO_ROOT / "services" / "ot-bridge" / "src" / "svc_ot_bridge"`.
- `test_prompt_injection.py`: `_repo_root = pathlib.Path(__file__).parent.parent.parent`,
  `pipeline_path = _repo_root / "services" / "knowledge-ingest" / "src" / ...`.

---

## Risultati test

Tutti i test eseguiti con `uv run --python 3.12 python -m pytest`:

| Suite | Risultato |
|-------|-----------|
| `tests/security/` | **14 passed** in 0.12s |
| `tests/eval/` | **35 passed, 1 skipped** in 2.29s (Ollama real-LLM skippato — corretto) |
| `packages/sft-knowledge/tests/` (no integration) | **7 passed** in 1.07s |
| `apps/api-gateway/tests/test_rbac_auditor.py` | **5 passed** in 3.88s |
| `packages/sft-agents/` | **441 passed, 2 skipped** in 17.45s |

Il fixture negativo `TestNegativeGateProof` in `test_rag_ci_gate.py` continua a dimostrare
che il gate fallisce su dataset degradati (anti-tautologia T-11-02-01 confermata).

---

_Fixed: 2026-05-25_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
