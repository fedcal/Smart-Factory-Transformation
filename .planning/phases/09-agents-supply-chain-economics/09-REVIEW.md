---
phase: 09-agents-supply-chain-economics
reviewed: 2026-05-24T18:00:00Z
depth: standard
files_reviewed: 28
files_reviewed_list:
  - packages/sft-agents/src/sft_agents/runtime/clusters.py
  - infra/migrations/timescale/011_create_scm_schema.sql
  - infra/migrations/timescale/012_extend_audit_scm.sql
  - infra/migrations/timescale/seed/scm_mantis_seed.sql
  - apps/agents/supply/inventory-manager/src/scm_inventory_manager/reorder.py
  - apps/agents/supply/inventory-manager/src/scm_inventory_manager/models.py
  - apps/agents/supply/inventory-manager/src/scm_inventory_manager/repository.py
  - apps/agents/supply/inventory-manager/src/scm_inventory_manager/metadata.py
  - apps/agents/supply/inventory-manager/src/scm_inventory_manager/agent.py
  - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/enpi.py
  - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/models.py
  - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/repository.py
  - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/metadata.py
  - apps/agents/supply/energy-optimizer/src/scm_energy_optimizer/agent.py
  - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/oepv.py
  - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/models.py
  - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/cost_aggregator.py
  - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/metadata.py
  - apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/agent.py
  - apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/holt_winters.py
  - apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/mape.py
  - apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/models.py
  - apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/repository.py
  - apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/metadata.py
  - apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/agent.py
  - apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py
  - apps/api-gateway/src/svc_api_gateway/dependencies.py
  - apps/api-gateway/src/svc_api_gateway/lifespan.py
  - apps/api-gateway/src/svc_api_gateway/main.py
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 9: Code Review Report — Supply Chain & Economics Agents

**Reviewed:** 2026-05-24T18:00:00Z
**Depth:** standard
**Files Reviewed:** 28
**Status:** issues_found

---

## Summary

La fase 9 implementa 4 agenti LangGraph per il cluster Supply Chain & Economics
(InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster) più il router
HTTP, le migrazioni DDL e il seed sintetico Mantis.

La struttura generale è notevolmente migliorata rispetto alla fase 8: tutti i
guardrail della Phase 8 review sono stati applicati con cura. In particolare:

- CR-01 (import esatti): tutti i nomi di classe importati in lifespan.py corrispondono
  esattamente a ciò che i moduli esportano. `HistoricalEventAggregator` (bug Phase 8)
  era già corretto nel lifespan.py rivisto.
- CR-02 (AuditRecord posizionale): tutti gli agenti chiamano `audit_writer.write(record)`
  con un oggetto AuditRecord posizionale — nessun kwargs.
- CR-03 (approval_id=None, .get() con default): rispettato ovunque.
- CR-04 (ID stabili): tutti gli agenti HITL derivano l'ID da `sha256(AGENT_ID.thread_id)[:32]`.
- CR-05 (clamp): `expected_savings_pct`, `mape` e `roi_savings_pct` sono tutti clampati prima
  della costruzione del modello Pydantic.
- CostAnalyzer: autonomo, Decision.AUTO, nessun interrupt, scrive COST_REPORT. Corretto.
- API gateway: frozen + extra=forbid, tz-aware validators su tutti i datetime, user_roles
  propagati, body 500 generico (no str(exc)).
- SQL: solo parametri $N, nessuna interpolazione di stringhe.

Tuttavia sono stati trovati **2 blocanti** che causano crash a runtime:

1. **IndexError nel forecast Holt-Winters** per `horizon >= 19`: l'indice nell'array
   `seasonals` supera la dimensione allocata quando l'orizzonte di previsione eccede 18 mesi,
   nonostante il modello HTTP accetti valori fino a 36.
2. **Dati forecast errati per h >= 1**: la formula dell'indice `seasonals` usa un termine
   extra `+h` che produce seasonali sbagliati già dal secondo passo di previsione (h=1),
   attingendo a elementi aggiornati in fasi diverse del training invece dell'ultimo ciclo
   stagionale corretto.

---

## Structural Findings (fallow)

*Nessun blocco `<structural_findings>` fornito per questa fase.*

---

## Narrative Findings (AI reviewer)

### Critical Issues

---

### CR-01: IndexError a runtime — `holt_winters.py` `seasonals` array troppo piccolo per `horizon >= 19`

**File:** `apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/holt_winters.py:141,154`

**Issue:** L'array `seasonals` è allocato con dimensione `n + m` (riga 141). La formula
di forecast alla riga 154 accede a `seasonals[n + h - m + (h % m)]`. Quando `h >= 18`
(con `m = 12`), l'espressione `h + (h % m) >= 2m = 24` produce un indice `>= n + m`,
causando `IndexError: index 36 is out of bounds for axis 0 with size 36`.

Verifica analitica: per `h=18, m=12`: `n + 18 - 12 + (18 % 12) = n + 18 - 12 + 6 = n + 12 = n + m`.
Numpy lancia `IndexError` perché l'indice massimo valido è `n + m - 1`.

Il modello HTTP `DemandForecastRequest` accetta `horizon` fino a 36 (`le=36`, riga 261 di
`supply_agents.py`). Qualsiasi richiesta con `horizon >= 19` crasha con 500.

**Prova sperimentale:** verificato direttamente con `n=24, m=12, horizon=19` — `IndexError`
confermato.

**Causa radice:** La formula `seasonals[n + h - m + (h % m)]` è scorretta. La semantica
intesa è "usa l'ultimo valore aggiornato del componente stagionale corrispondente al passo
`h`". L'ultimo aggiornamento di `seasonals[s]` avviene all'iterazione `t = n - m + s`
(supponendo `n % m == 0`), producendo l'indice `t + m = n + s`. Il componente da usare
è `s = h % m`, quindi l'indice corretto è `n + (h % m)` — senza il termine `+h - m`.

**Fix:**
```python
# holt_winters.py riga 153-156 — sostituire la formula dell'indice
forecasts = [
    max(0.0, L + (h + 1) * T + seasonals[n + (h % m)])
    for h in range(horizon)
]
```
Non è necessario modificare la dimensione di `seasonals` (già `n + m` è sufficiente,
poiché `n + (h % m)` è sempre in `[n, n + m - 1]`).

---

### CR-02: Previsioni Holt-Winters numericamente scorrette per `h >= 1`

**File:** `apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/holt_winters.py:154`

**Issue:** Anche per valori di `horizon` dove non si verifica l'overflow (h in [0, 17]),
la formula `seasonals[n + h - m + (h % m)]` produce **valori numericamente errati** fin
dal secondo passo di previsione (`h = 1`).

Il termine `n + h - m + (h % m)` per `h=1` vale `n - 12 + 1 + 1 = n - 10`. Questo punta
a un elemento di `seasonals` aggiornato durante il training alla metà del penultimo ciclo
stagionale, NON all'ultimo valore del componente stagionale 1. Il risultato è che i
forecast attingono a componenti stagionali nel *mezzo* dell'array di training anziché ai
valori finali, producendo proiezioni errate con errori dell'ordine di 1000-4000 kg/mese
sui dati sintetici Mantis.

**Confronto su dati Mantis (serie jersey 24 mesi):**
```
h=1: formula_sbagliata=10122.83, formula_corretta=9124.39  (errore: +998 kg)
h=2: formula_sbagliata=11124.45, formula_corretta=10125.97 (errore: +998 kg)
h=3: formula_sbagliata=8127.40,  formula_corretta=12128.14 (errore: -4000 kg)
```

Il MAPE calcolato sul held-out tail è basato su questa formula sbagliata, rendendo anche
il KPI di accuratezza non affidabile.

**Fix:** identico a CR-01 — sostituire `seasonals[n + h - m + (h % m)]` con `seasonals[n + (h % m)]`.
I due bug hanno la stessa radice e la stessa correzione.

---

### Warnings

---

### WR-01: `scm.inventory_levels` e `scm.energy_readings` — seed non idempotente su hypertable senza PK

**File:** `infra/migrations/timescale/seed/scm_mantis_seed.sql:83-150`

**Issue:** Le INSERT su `scm.inventory_levels` (riga 83) e `scm.energy_readings` (riga 116)
usano `ON CONFLICT DO NOTHING` **senza specificare la colonna di conflitto**. Queste tabelle
sono TimescaleDB hypertable e **non hanno una PRIMARY KEY** (la DDL in `011_create_scm_schema.sql`
non definisce nessun PK su queste due tabelle). La sintassi `ON CONFLICT DO NOTHING` senza
colonna di conflitto è equivalente a una INSERT senza protezione idempotente su tabelle
prive di unicità: ogni ri-esecuzione del seed duplica le righe.

Il commento in testa al file recita "Re-run safety: all INSERT statements use ON CONFLICT DO NOTHING"
ma questa garanzia è **falsa** per le due hypertable. Le tabelle `scm.sku_master` (PK=sku_id),
`scm.enpi_baseline` (PK=process) e `scm.historical_orders` (PK=order_id) sono idempotenti —
solo le hypertable non lo sono.

**Rischio:** Eseguendo il seed due volte (pipeline CI/CD, migrazione accidentale, restore di
ambiente) si ottengono doppie letture per InventoryManager ed EnergyOptimizer, portando a
soglie di reorder apparentemente dimezzate e EnPI calcolato su dati duplicati.

**Fix:** Aggiungere un vincolo di unicità sulle hypertable prima del seed, oppure proteggere
il seed con un DELETE preventivo:

```sql
-- Opzione A: aggiungere UNIQUE nella DDL (011_create_scm_schema.sql)
-- scm.inventory_levels: unicità su (ts, sku_id, location)
ALTER TABLE scm.inventory_levels ADD CONSTRAINT uq_inv_ts_sku_loc
    UNIQUE (ts, sku_id, location);

-- scm.energy_readings: unicità su (ts, asset_id, process)
ALTER TABLE scm.energy_readings ADD CONSTRAINT uq_energy_ts_asset_proc
    UNIQUE (ts, asset_id, process);

-- Poi nel seed:
INSERT INTO scm.inventory_levels ... ON CONFLICT (ts, sku_id, location) DO NOTHING;
INSERT INTO scm.energy_readings ... ON CONFLICT (ts, asset_id, process) DO NOTHING;

-- Opzione B: guard nel seed (dev-only, più semplice)
DELETE FROM scm.inventory_levels
WHERE source IN ('wms_sync', 'manual')
  AND ts > NOW() - INTERVAL '72 hours';  -- rimuove solo le righe sintetiche recenti

DELETE FROM scm.energy_readings
WHERE asset_id IN ('tintoria-01','tintoria-02','stentatoio-01','stentatoio-02',
                   'telaio-01','telaio-02','rapier-01','rapier-02');
```

---

### WR-02: `DemandRepository` — interpolazione `INTERVAL '1 month' * $2` potrebbe fallire su asyncpg

**File:** `apps/agents/supply/demand-forecaster/src/scm_demand_forecaster/repository.py:36-43`

**Issue:** La query SQL usa `INTERVAL '1 month' * $2` dove `$2` è un intero Python. asyncpg
invia i parametri Python con type inference nativa: un `int` Python viene mappato su
PostgreSQL `integer`. La moltiplicazione `INTERVAL * integer` è valida in PostgreSQL, ma
alcuni driver (e alcune versioni di asyncpg) richiedono un cast esplicito per evitare
errori di type mismatch (`operator does not exist: interval * integer`).

Inoltre, `NOW() - INTERVAL '1 month' * $2` ha una semantica leggermente diversa da
`NOW() - ($2::int * INTERVAL '1 month')`: nel primo caso PostgreSQL deve coerentemente
inferire il tipo di `$2`. Se il driver invia `$2` come `bigint` anziché `int4`, il
comportamento varia per versione.

**Fix:** Usare una forma più robusta con cast esplicito:
```python
_SQL_MONTHLY_ORDERS: ClassVar[str] = (
    "SELECT DATE_TRUNC('month', order_date) AS month, "
    "SUM(quantity_kg)::FLOAT AS total_kg "
    "FROM scm.historical_orders "
    "WHERE sku_group = $1 "
    "AND order_date >= NOW() - ($2::int * INTERVAL '1 month') "
    "GROUP BY 1 "
    "ORDER BY 1"
)
```

---

### WR-03: `InventoryManager.__call__` — synthetic fallback silenzioso quando `rows` è vuota

**File:** `apps/agents/supply/inventory-manager/src/scm_inventory_manager/agent.py:303-335`

**Issue:** Quando il repository restituisce zero righe (`rows = []`) per gli SKU richiesti,
il codice non entra nel branch `if not below_threshold_signals and rows` (riga 294 — `rows`
è falsy), quindi non ritorna early. Scende invece al blocco successivo `if below_threshold_signals`
(falso) e produce una `ReorderRecommendation` sintetica con campi `sku_id="SKU-UNKNOWN"`,
`current_qty=Decimal("0")`, `estimated_cost_eur=Decimal("0")` (righe 327-335).

Questo produce un interrupt e una successiva scrittura di audit PURCHASE_RECOMMENDATION_DRAFT
con dati completamente sintetici **anche in produzione**, se il repository restituisce zero
righe per un qualsiasi motivo (timeout, sku_ids forniti errati, problema di connessione
parziale). Il log `inventory_manager_no_reorder_needed` non viene emesso, rendendo
invisibile il problema.

Il commento alla riga 303 recita "No rows at all (mock returns []) — generate a synthetic
signal for test", ma questo path è raggiunto anche in produzione.

**Fix:** Separare esplicitamente il caso "nessuna riga dal DB" (errore/produzione) dal caso
"test mock vuoto":
```python
# Dopo il fetch (riga 275):
if not rows:
    logger.warning(
        "inventory_manager_no_rows_from_db",
        sku_ids=sku_ids,
        thread_id=full_thread_id,
    )
    return {"reorder_recommendation": None, "reorder_alert": None}

# Rimuovere il blocco sintetico (righe 302-335) e sostituire con:
if not below_threshold_signals:
    logger.info("inventory_manager_no_reorder_needed", thread_id=full_thread_id)
    return {"reorder_recommendation": None, "reorder_alert": None}

primary_signal = below_threshold_signals[0]
```

---

### WR-04: `CostAnalyzer.__init__` accetta argomenti posizionali ma `lifespan.py` li passa posizionali con commento fuorviante

**File:**
- `apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/agent.py:96-105`
- `apps/api-gateway/src/svc_api_gateway/lifespan.py:244-249`

**Issue:** `CostAnalyzer.__init__` non è definito con argomenti keyword-only (`*` prefix)
a differenza degli altri tre agenti dello stesso cluster che usano tutti `*, pool:, audit_writer:, llm:`.
Il costruttore accetta `pool, audit_writer, llm` come argomenti posizionali (riga 96:
`def __init__(self, pool: Any, audit_writer: AuditWriter | Any, llm: Any = None)`).

Il commento in `lifespan.py` alla riga 244 segnala questa differenza ("CostAnalyzer.__init__
takes positional args (not keyword-only *-args)"), ma non la risolve. Un refactor futuro
che aggiunga un parametro a `CostAnalyzer.__init__` prima di `llm` causerebbe un bug
silenzioso: `lifespan.py` passerebbe `audit_writer` come terzo argomento a `pool`.

**Fix:** Rendere `CostAnalyzer.__init__` keyword-only come gli altri agenti:
```python
# cost_analyzer/agent.py
def __init__(
    self,
    *,                                  # forza keyword-only
    pool: Any,
    audit_writer: AuditWriter | Any,
    llm: Any = None,
) -> None:
```
Aggiornare `lifespan.py` di conseguenza:
```python
cost_analyzer_agent = CostAnalyzer(
    pool=pool,
    audit_writer=audit_writer,
    llm=None,
)
```

---

### Info

---

### IN-01: `build_sensitivity_table` esegue `compute_oepv` due volte per ogni ribasso

**File:** `apps/agents/supply/cost-analyzer/src/scm_cost_analyzer/oepv.py:181-188`

**Issue:** La list comprehension in `build_sensitivity_table` chiama `compute_oepv(r, pt, config)`
due volte per ogni valore `r` del range: una volta per estrarre `.pe` e una volta per `.total_score`.
Per liste di ribasso di 20+ elementi (tipico per tabelle di sensitivity), questo raddoppia il
numero di calcoli della funzione esponenziale.

```python
# Attuale — doppia chiamata:
SensitivityRow(
    ribasso_pct=r,
    pe=compute_oepv(r, pt, config).pe,
    total_score=compute_oepv(r, pt, config).total_score,
)
```

**Fix:**
```python
return [
    SensitivityRow(
        ribasso_pct=r,
        pe=(result := compute_oepv(r, pt, config)).pe,
        total_score=result.total_score,
    )
    for r in ribasso_range
]
```
oppure, più leggibile:
```python
results = [compute_oepv(r, pt, config) for r in ribasso_range]
return [SensitivityRow(ribasso_pct=res.ribasso_pct, pe=res.pe, total_score=res.total_score)
        for res in results]
```

---

### IN-02: `supply_agents.py` non registra il `thread_id` nell'`app.state` — nessun recovery se il process crasha durante HITL

**File:** `apps/api-gateway/src/svc_api_gateway/routers/supply_agents.py:363-387`

**Issue:** Il `thread_id` per gli endpoint HITL (inventory-manager/check, energy-optimizer/optimize,
demand-forecaster/forecast) viene generato al momento della richiesta come `f"supply.*.{uuid4()}"` ma
non viene persistito in alcuno store applicativo recuperabile dall'operatore oltre alla cache di
idempotency (TTL 300s). Se il processo API gateway riavvia tra il POST `/check` e il POST `/resume`,
il supervisore non ha modo di recuperare il `thread_id` senza averlo annotato manualmente dal log.

Il `thread_id` è persistito nel LangGraph checkpoint (PostgreSQL), ma non è esposto da alcun endpoint
di listing. Questo non è un bug urgente (il pattern era già presente nelle fasi precedenti), ma
peggiora il DX per i team di operazioni.

**Fix (bassa priorità, Phase 11):** Aggiungere un endpoint `GET /v1/agents/supply/pending` che
lista i thread HITL attivi dal checkpointer PostgreSQL, oppure scrivere il `thread_id` nella
tabella di audit come campo ricercabile.

---

## Verifica checklist Phase 8 "bugs da ricontrollare"

| Guardrail | Verifica | Esito |
|-----------|---------|-------|
| CR-01: import esatti in lifespan.py | `InventoryManager`, `EnergyOptimizer`, `CostAnalyzer`, `DemandForecaster` importati per nome esatto dai rispettivi `agent.py` — tutti corretti | PASS |
| CR-02: AuditRecord posizionale | Tutti e 4 gli agenti chiamano `await self._audit.write(record)` con oggetto AuditRecord | PASS |
| CR-03: approval_id=None, .get() con default | Rispettato in tutti gli agenti | PASS |
| CR-04: ID stabili da thread_id (no uuid4 inline) | `_stable_id()` usa `sha256(AGENT_ID.thread_id)[:32]` in tutti e 3 gli agenti HITL | PASS |
| CR-05: clamp ratio | `expected_savings_pct` clamped in EnergyOptimizer; `mape` clamped in DemandForecaster; `roi_savings_pct` clamped in CostAggregator | PASS |
| HITL ordering: interrupt-before-audit | Tutti i 3 agenti HITL: interrupt() prima di qualsiasi `audit.write()` | PASS |
| No double-write on replay | Ogni agente scrive esattamente dopo il resume, una volta per riga | PASS |
| CostAnalyzer autonomo: Decision.AUTO, nessun interrupt, COST_REPORT | Confermato — nessuna chiamata a interrupt(), `decision=Decision.AUTO` | PASS |
| API gateway: frozen + extra=forbid | Tutti i 6 modelli di request lo rispettano | PASS |
| API gateway: tz-aware validators | `EnergyOptimizeRequest`, `CostAnalyzeRequest` hanno `@field_validator`; `InventoryCheckRequest`, `DemandForecastRequest` non hanno campi datetime — corretto | PASS |
| API gateway: user_roles propagati | user_roles propagati in tutti e 4 gli endpoint principali | PASS |
| API gateway: generic 500 body | `_handle_agent_error` usa `{"error": "internal_agent_error"}` — nessuna esposizione di `str(exc)` | PASS |
| asyncpg: datetime objects diretti (no .isoformat()) | Repository inventory e demand: corretti. Repository energy: `ts_from.isoformat()` usato solo nel LOG (riga 103), non come parametro SQL — corretto | PASS |
| SQL: solo $N params (no interpolazione) | Verificato in tutti e 3 i repository | PASS |
| Holt-Winters: array bounds | FAIL — vedi CR-01/CR-02 |
| Seed idempotenza hypertable | FAIL — vedi WR-01 |

---

_Reviewed: 2026-05-24T18:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
