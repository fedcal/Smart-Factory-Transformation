# Phase 9: Agents — Supply Chain & Economics - Research

**Researched:** 2026-05-24
**Domain:** LangGraph agents + TimescaleDB SCM schema + Holt-Winters forecasting + OEPV/ribasso simulation
**Confidence:** HIGH (codebase direct inspection + PyPI verification; no external APIs needed)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Data sources:** Nuovo schema sintetico `scm.*` in TimescaleDB, NON derivato da tabelle esistenti.
Tabelle: `scm.inventory_levels`, `scm.energy_readings`, `scm.historical_orders` + master SKU/reorder.
Seed da dataset sintetico documentato Mantis. Pattern asyncpg (datetime, mai `.isoformat()`).

**OEPV / boundary F9 ↔ F12:** Phase 9 realizza un simulatore parametrico funzionante —
scoring 70% tecnico / 30% economico + curva ribasso non lineare (ECO-02) + sensitivity analysis (ECO-05),
con formula configurabile (coefficienti, BA, soglie come input).
La precisione legale definitiva (Codice Appalti 2023, ECO/DEL-06) è demandata a Phase 12.
CostAnalyzer è autonomo / read-only (nessun HITL).

**DemandForecaster:** Previsione statistica deterministica — Holt-Winters con fallback seasonal-naive
per serie brevi; LLM-free. Input: `scm.historical_orders`; output: piano domanda per ≥2 gruppi SKU.
Segnali esterni configurabili via config (nessuna API live). KPI: rolling MAPE.
HITL: piano domanda pubblicato a ProductionPlanner tramite approvazione HITL.

**Mantis data:** Valori sintetici realistici generati da Claude; documentati esplicitamente come sintetici
in `docs/`. Anchor OEPV: Base d'Asta €108.000. EnPI ISO 50001 in kWh/kg per tintoria e finissaggio.

**Portato dalle Fasi 6/7/8 (non ridiscusso):**
- Pattern cluster subgraph: aggiungere `build_supply_subgraph` in `clusters.py`
- HITL: interrupt-then-audit, no audit prima del resume, no double-write in replay,
  `approval_id=None` per righe HITL pending, ID stabili da state/thread_id (mai inline uuid4)
- Audit: estendere `ActionType` enum + migrazione CHECK in lockstep (pattern 08-00a)
- API gateway: request models frozen+extra=forbid, validatori tz-aware, user_roles ACL, generic 500 body
- Scaffold supply già presenti: `apps/agents/supply/{inventory-manager,energy-optimizer,cost-analyzer}`
- DemandForecaster scaffold: `apps/agents/supply/demand-forecaster` (già presente)
- Target HITL DemandForecaster: `apps/agents/ops/production-planner`
- Nyquist: scaffold test contracts prima dell'implementazione (pattern 08-00b)
- Execution: worktrees DISABILITATI — executor sequenziale su main tree

### Claude's Discretion

N/A — tutte le gray area sono state risolte nelle decisioni bloccate sopra.

### Deferred Ideas (OUT OF SCOPE)

- Modello OEPV/ribasso definitivo conforme al Codice Appalti 2023 → Phase 12
- Segnali di domanda esterni live (API reali) → fuori scope milestone; F9 usa segnali sintetici config-driven
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCM-01 | InventoryManager — monitora livelli magazzino, suggerisce riordini con HITL procurement | Schema `scm.inventory_levels` + `scm.sku_master`; logica reorder-point deterministica; pattern HITL da ShiftHandover |
| SCM-02 | EnergyOptimizer — analizza consumi (kWh, vapore), suggerisce schedule energy-efficient via HITL | Schema `scm.energy_readings`; ISO 50001 EnPI kWh/kg; pattern HITL da TrainingCoach |
| SCM-03 | CostAnalyzer — calcola impatto economico e simulatore OEPV ribasso (autonomo) | Formula OEPV 70/30 + curva ribasso non lineare + sensitivity; KnowledgeCurator come analogo autonomo |
| SCM-04 | DemandForecaster — previsione domanda Holt-Winters, piano a ProductionPlanner via HITL | Schema `scm.historical_orders`; implementazione HW con numpy; rolling MAPE; wiring su ProductionPlanner |
| SCM-05 | Esempi numerici realistici Mantis documentati come sintetici in `docs/` | Dataset sintetico completo: SKU, capacità, costi unitari, baseline EnPI, ordini storici |
</phase_requirements>

---

## Summary

La Fase 9 implementa il quarto cluster agentivo — Supply Chain & Economics — riutilizzando
interamente i pattern consolidati nelle Fasi 6, 7 e 8. La struttura architetturale è stabile:
tre agenti con HITL (InventoryManager, EnergyOptimizer, DemandForecaster) e un agente autonomo
read-only (CostAnalyzer), connessi via `build_supply_subgraph` specchiato su `build_knowledge_subgraph`.

La principale novità tecnica rispetto alle fasi precedenti è la creazione dello schema `scm.*`
in TimescaleDB (hypertable per energy_readings e inventory_levels, tabella temporale per
historical_orders) e l'implementazione di logica di dominio specifica: punto di riordino
statistico (InventoryManager), calcolo EnPI ISO 50001 (EnergyOptimizer), simulatore OEPV
parametrico con curva ribasso non lineare (CostAnalyzer), previsione Holt-Winters deterministica
con rolling MAPE (DemandForecaster).

Il rischio principale è la replicazione dei 5 bug critici della Fase 8: ID instabili nel replay,
chiamata sbagliata di AuditWriter, KeyError su state, ImportError da import name mismatch,
ValidationError per overflow di KPI. Il planner deve trattare questi cinque trappole come
veto-check espliciti su ogni piano agent.

**Primary recommendation:** Iniziare con Wave 0 (migrazione 011 + enum lockstep + test scaffold
Nyquist) prima di qualsiasi implementazione agent, esattamente come 08-00a / 08-00b. Poi procedere
wave per wave: schema SCM, dataset Mantis sintetico, poi i quattro agenti in ordine crescente
di dipendenza (InventoryManager → EnergyOptimizer → CostAnalyzer → DemandForecaster).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Schema `scm.*` (DDL + seed) | Database / TimescaleDB | — | Dati time-series; hypertable per energy_readings; tabella relazionale per sku_master |
| Reorder-point logic (EOQ / fixed) | API / Agent (InventoryManager) | Database (query) | Calcolo deterministico in Python su dati da scm.inventory_levels + sku_master |
| EnPI ISO 50001 kWh/kg | API / Agent (EnergyOptimizer) | Database (query) | Aggregazione su scm.energy_readings; confronto con baseline configurable |
| OEPV / ribasso simulator | API / Agent (CostAnalyzer) | — | Calcolo parametrico puro; nessuna scrittura su DB; read-only da audit.actions |
| Holt-Winters forecast | API / Agent (DemandForecaster) | Database (query) | Previsione deterministica su scm.historical_orders |
| HITL interrupt/resume | API / Agent (3 agenti HITL) | PostgreSQL checkpointer | Pattern LangGraph nativo; PG è la source of truth per lo stato |
| HITL approval verso ProductionPlanner | API / Agent cross-cluster | — | DemandForecaster scrive un piano che il ProductionPlanner receve via state |
| ActionType enum + CHECK migration | Database + packages/sft-agents | — | Lockstep obbligatorio: enum.py + migrazione 011 modificati in atomicità |
| API gateway router | API / FastAPI | — | Mirror di knowledge_agents.py; supply_agents.py nel gateway |
| Documenti Mantis sintetici | Docs layer | — | Dati puramente documentali in `docs/`; nessuna logica di business |

---

## Standard Stack

### Core (già nel workspace — nessuna nuova dipendenza obbligatoria)

| Libreria | Versione pinned nel workspace | Scopo | Motivo dell'uso |
|----------|------------------------------|-------|-----------------|
| `langgraph` | `>=0.4,<0.5` (sft-agents) | Grafo agentivo + interrupt HITL | Standard di progetto [ASSUMED] |
| `asyncpg` | `>=0.30,<0.31` (sft-agents) | Query TimescaleDB async | Standard di progetto [ASSUMED] |
| `pydantic` v2 | `>=2.9,<3` (sft-agents) | Modelli frozen + extra=forbid | Standard di progetto [ASSUMED] |
| `numpy` | `>=1.26.0,<3.0.0` (sft-ml) | Calcoli Holt-Winters hand-rolled + OEPV | Già nel workspace via sft-ml [ASSUMED] |
| `pandas` | `>=2.3.0,<3.0.0` (sft-ml) | Preparazione serie temporali per HW | Già nel workspace via sft-ml [ASSUMED] |
| `structlog` | `>=24.4` (sft-agents) | Logging strutturato | Standard di progetto [ASSUMED] |

### Nuova dipendenza proposta: `statsmodels`

**Decisione:** NON aggiungere `statsmodels` come dipendenza. [VERIFIED: PyPI]

**Motivazione:** Il CONTEXT.md specifica esplicitamente "minimal new deps" e "deterministic +
testable". `statsmodels.tsa.holtwinters.ExponentialSmoothing` porta una dipendenza pesante
(~30MB) e introduce comportamento non-deterministico legato all'ottimizzazione dei parametri.
Una implementazione Holt-Winters hand-rolled con `numpy` (già presente in `sft-ml`) è:
- Pienamente deterministica con parametri fissi (α, β, γ configurabili)
- Testabile con numeri esatti
- Zero nuove dipendenze
- Sufficiente per la complessità richiesta (serie mensili di ordini tessili)

Il fallback seasonal-naive (media stagionale) è banalmente implementabile in numpy.

`statsmodels` rimane un'alternativa valida se in futuro si richiedesse ottimizzazione MLE
dei parametri, ma non è necessario per Phase 9.

**Versione verificata su PyPI:** `statsmodels==0.14.6` [VERIFIED: PyPI - pip index versions]

### Package Legitimacy Audit

> slopcheck 0.6.1 installato e verificato. Nota: slopcheck controlla npm, non PyPI.
> Per il progetto Python si utilizza `pip index versions` come verifica canonica.

| Package | Registry | Fonte | Versione corrente | Stato | Disposizione |
|---------|----------|-------|-------------------|-------|--------------|
| `statsmodels` | PyPI | statsmodels.org (NumFOCUS) | 0.14.6 | Pacchetto maturo, ~15 anni di storia | Approvato ma NON usato (vedi decisione sopra) |
| `numpy` | PyPI | numpy.org | 2.4.6 | Fondamentale dell'ecosistema scientifico | Approvato (già in workspace) |
| `pandas` | PyPI | pandas.pydata.org | 3.0.3 | Fondamentale dell'ecosistema scientifico | Approvato (già in workspace) |
| `asyncpg` | PyPI | github.com/MagicStack/asyncpg | 0.31.0 | Standard del progetto | Approvato (già in workspace) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*Note: slopcheck verifica npm; per pacchetti PyPI la legittimità è confermata via `pip index versions`
e reputazione consolidata nell'ecosistema scientifico Python.*

---

## Architecture Patterns

### System Architecture Diagram

```
HTTP Request (supply cluster)
        |
        v
 FastAPI /v1/agents/supply/*
 (supply_agents.py — mirror knowledge_agents.py)
        |
        v
 supervisor_graph.ainvoke(state={target_agent: "..."})
        |
        v
 build_supply_subgraph (clusters.py)
   START → conditional_edges(_route) → [slug] → END
        |
   ┌────┴────────────────────────────────────────┐
   |           |              |                  |
   v           v              v                  v
InventoryMgr  EnergyOpt   CostAnalyzer   DemandForecaster
(HITL-sup)   (HITL-sup)  (AUTO, R/O)    (HITL-sup)
   |           |              |                  |
   v           v              v                  v
scm.inventory  scm.energy   audit.actions   scm.historical
_levels +      _readings +  (cost KPIs)     _orders +
sku_master     enpi_baseline                sku_groups
   |           |              |                  |
   v           v              v                  v
 interrupt()  interrupt()  AuditWriter      interrupt() →
 HITL pause   HITL pause   write(AUTO)      ProductionPlanner
   |           |                                 |
   v           v                                 v
AuditWriter  AuditWriter                  audit.actions
(post-resume)(post-resume)               (DEMAND_PLAN_DRAFT +
                                          DEMAND_PLAN_SIGNOFF)
        |
        v
 PostgreSQL checkpointer (stato HITL persistito)
        +
 audit.actions (append-only, CHECK constraint migrazione 011)
```

### Recommended Project Structure

```
apps/agents/supply/
├── inventory-manager/
│   └── src/scm_inventory_manager/
│       ├── __init__.py
│       ├── metadata.py          # AGENT_ID, CLUSTER, costanti
│       ├── models.py            # InventoryAlert, ReorderRecommendation (frozen)
│       ├── repository.py        # query asyncpg su scm.inventory_levels + sku_master
│       ├── reorder.py           # logica reorder-point (pure function, testabile)
│       └── agent.py             # InventoryManager.__call__ + HITL pattern
├── energy-optimizer/
│   └── src/scm_energy_optimizer/
│       ├── metadata.py
│       ├── models.py            # EnergyReading, EnpiReport, OffPeakProposal
│       ├── repository.py        # query scm.energy_readings
│       ├── enpi.py              # calcolo kWh/kg ISO 50001 (pure function)
│       └── agent.py             # EnergyOptimizer.__call__ + HITL
├── cost-analyzer/
│   └── src/scm_cost_analyzer/
│       ├── metadata.py
│       ├── models.py            # CostBreakdown, OepvResult, SensitivityTable
│       ├── cost_aggregator.py   # query aggregazione costi da audit.actions
│       ├── oepv.py              # simulatore OEPV parametrico (pure function)
│       └── agent.py             # CostAnalyzer.__call__ (autonomo, no HITL)
└── demand-forecaster/
    └── src/scm_demand_forecaster/
        ├── metadata.py
        ├── models.py            # DemandPlan, SkuForecast, MapeReport
        ├── repository.py        # query scm.historical_orders
        ├── holt_winters.py      # HW hand-rolled + seasonal-naive fallback (numpy)
        ├── mape.py              # rolling MAPE (pure function)
        └── agent.py             # DemandForecaster.__call__ + HITL a ProductionPlanner

infra/migrations/timescale/
├── 011_create_scm_schema.sql    # scm.* DDL + hypertables
└── tests/test_migration_011.py  # mirror test_migration_010.py + scm schema smoke test

infra/migrations/timescale/seed/
└── scm_mantis_seed.sql          # dati sintetici Mantis (SKU, ordini, energie, livelli)

docs/docs/agents/supply/         # bilingual IT+EN
├── inventory-manager.md
├── energy-optimizer.md
├── cost-analyzer.md
├── demand-forecaster.md
└── mantis-synthetic-dataset.md  # ESPLICITAMENTE documentato come sintetico
docs/docs/en/agents/supply/      # speculare EN
```

### Pattern 1: build_supply_subgraph (mirror esatto di build_knowledge_subgraph)

**Cosa:** Subgrafo condizionale START → _route → [slug] → END con fallback su `cost-analyzer`
(autonomo, nessun HITL, nessun effetto collaterale irreversibile — analogo a `knowledge-curator`).

**Quando usare:** Sempre per il cluster supply; il supervisor rooter invoca questo subgrafo
quando `state["target_agent"]` appartiene al cluster supply.

**Costante fallback:** `_SCM_DEFAULT_AGENT: str = "cost-analyzer"` (autonomo, read-only)

```python
# Source: packages/sft-agents/src/sft_agents/runtime/clusters.py — estendere con:
_SCM_DEFAULT_AGENT: str = "cost-analyzer"

def build_supply_subgraph(
    child_callables: Mapping[str, Callable[[AgentState], Awaitable[dict[str, Any]]]],
) -> StateGraph:
    """Return an *uncompiled* SUPPLY-cluster StateGraph with conditional routing.

    Mirrors build_knowledge_subgraph (D-X-04 gateway pattern).
    Falls back to 'cost-analyzer' (autonomous, read-only) — no HITL, no
    irreversible side effects. Emits 'scm_route_unknown_target' structlog warning.
    MUST include 'cost-analyzer' (the fallback) — ValueError otherwise.
    """
    if not child_callables:
        raise ValueError("child_callables must be non-empty for the supply subgraph")
    if _SCM_DEFAULT_AGENT not in child_callables:
        raise ValueError(
            f"child_callables must include {_SCM_DEFAULT_AGENT!r} (the fallback "
            f"target for the supply router); got slugs {sorted(child_callables)}"
        )
    children = dict(child_callables)
    g: StateGraph = StateGraph(AgentState)
    for slug, fn in children.items():
        g.add_node(slug, fn)

    def _route(state: AgentState) -> str:
        target = state.get("target_agent") if isinstance(state, dict) else None
        if not target or target not in children:
            _log.warning("scm_route_unknown_target", target=target, fallback=_SCM_DEFAULT_AGENT)
            return _SCM_DEFAULT_AGENT
        return str(target)

    g.add_conditional_edges(START, _route, {slug: slug for slug in children})
    for slug in children:
        g.add_edge(slug, END)
    return g
```

[ASSUMED] — struttura derivata da codebase diretta; non richiede verifica esterna.

### Pattern 2: Interrupt-then-audit (eredità da ShiftHandover / TrainingCoach)

**Regola fondamentale:** Nessuna scrittura audit prima del resume. L'audit write avviene
DOPO che `interrupt()` ritorna, non prima. LangGraph re-esegue il nodo dall'inizio ad ogni
resume; qualsiasi write prima di interrupt() viene eseguita due volte.

```python
# Struttura corretta per agenti HITL del cluster supply:
async def __call__(self, state):
    # 1. Calcolo deterministico (pure function — reorder, EnPI, HW forecast)
    recommendation = self._compute(state)

    # 2. interrupt() — RAISES su prima esecuzione, RETURNS su resume
    interrupt({"recommendation": recommendation, "agent_id": AGENT_ID})

    # 3. Audit write — eseguita SOLO dopo resume (post-interrupt)
    await self._write_audit(
        record_id=self._stable_id(state),   # MAI uuid4() inline
        recommendation=recommendation,
        action_type=ActionType.REORDER_ALERT,   # esempio
    )
    return {"recommendation": recommendation}
```

### Pattern 3: Stable ID derivation (CR-04 fix da Phase 8)

**Problema:** uuid4() inline ricalcolato ad ogni re-esecuzione del nodo → IDs diversi per
la stessa HITL session → impossibile correlare draft + signoff in audit.

**Soluzione:** derivare l'ID da input stabili (thread_id del config LangGraph):

```python
import hashlib

def _stable_recommendation_id(self, state: Mapping[str, Any]) -> str:
    """Derive stable ID from thread_id (stable across LangGraph replay).

    NEVER use uuid4() inline — Phase 8 CR-04 lesson.
    thread_id is set by the gateway per-request and does NOT change on resume.
    """
    thread_id = state.get("thread_id") or "unknown"
    return hashlib.sha256(f"{AGENT_ID}.{thread_id}".encode()).hexdigest()[:32]
```

### Pattern 4: AuditWriter.write(record: AuditRecord) — POSIZIONALE (CR-02 fix da Phase 8)

**Problema:** TrainingCoach chiamava `self._audit.write(action_type=..., decision=...)` con
keyword args → TypeError: `write()` accetta solo un AuditRecord posizionale.

**Soluzione:** costruire sempre un AuditRecord completo, poi passarlo posizionalmente:

```python
from sft_agents.models.audit import AuditRecord
from sft_agents.models.proposed_action import ProposedAction

record = AuditRecord(
    id=uuid4(),
    ts=datetime.now(timezone.utc),         # sempre tz-aware
    action_id=action.id,
    agent_id=AGENT_ID,
    thread_id=thread_id,
    cluster=CLUSTER,
    action_type=ActionType.REORDER_ALERT.value,
    evidence_panel=evidence_panel,
    decision=Decision.HITL_SUPERVISOR,
    decision_actor=None,
    motivation=motivation_string,
    budget_snapshot=_EMPTY_BUDGET,
    approval_id=None,   # CR-03: mai fabricare UUID per HITL pending
)
await self._audit.write(record)   # POSIZIONALE — non kwargs
```

### Pattern 5: Schema scm.* DDL (TimescaleDB hypertable)

**Cosa:** Tre tabelle principali + due master tables. `scm.energy_readings` e
`scm.inventory_levels` sono hypertable (time-series); `scm.historical_orders` è tabella
relazionale con timestamp ma non necessariamente hypertable.

```sql
-- 011_create_scm_schema.sql (idempotente — Pattern 010/009)
-- Nota: statement_cache_size=0 richiesto per asyncpg su TimescaleDB (Pitfall 6 da Plan 04-02)

CREATE SCHEMA IF NOT EXISTS scm;

-- SKU master table (reference data)
CREATE TABLE IF NOT EXISTS scm.sku_master (
    sku_id         TEXT PRIMARY KEY,
    sku_name       TEXT NOT NULL,
    category       TEXT NOT NULL CHECK (category IN ('raw_yarn','accessory','spare_part','fabric')),
    unit            TEXT NOT NULL,  -- 'kg', 'pcs', 'roll'
    reorder_point  NUMERIC(10,2) NOT NULL,   -- soglia di riordino
    reorder_qty    NUMERIC(10,2) NOT NULL,   -- quantità da riordinare
    lead_time_days INTEGER NOT NULL DEFAULT 7,
    unit_cost_eur  NUMERIC(10,4) NOT NULL,
    sku_group      TEXT NOT NULL DEFAULT 'default'  -- per DemandForecaster grouping
);

-- Inventory levels (hypertable time-series)
CREATE TABLE IF NOT EXISTS scm.inventory_levels (
    ts           TIMESTAMPTZ NOT NULL,
    sku_id       TEXT NOT NULL REFERENCES scm.sku_master(sku_id),
    quantity     NUMERIC(12,3) NOT NULL,
    location     TEXT NOT NULL DEFAULT 'main_warehouse',
    source       TEXT NOT NULL DEFAULT 'manual'
);
SELECT create_hypertable('scm.inventory_levels', 'ts', if_not_exists => TRUE);

-- Energy readings (hypertable time-series)
CREATE TABLE IF NOT EXISTS scm.energy_readings (
    ts            TIMESTAMPTZ NOT NULL,
    asset_id      TEXT NOT NULL,
    process       TEXT NOT NULL CHECK (process IN ('dyeing','finishing','spinning','weaving','other')),
    kwh           NUMERIC(10,4) NOT NULL,
    kg_processed  NUMERIC(10,4),   -- null se non misurabile in quel campione
    shift         TEXT NOT NULL DEFAULT 'day',
    is_peak_hour  BOOLEAN NOT NULL DEFAULT FALSE
);
SELECT create_hypertable('scm.energy_readings', 'ts', if_not_exists => TRUE);

-- Historical orders (relazionale con timestamp — base per DemandForecaster)
CREATE TABLE IF NOT EXISTS scm.historical_orders (
    order_id       TEXT PRIMARY KEY,
    sku_id         TEXT NOT NULL REFERENCES scm.sku_master(sku_id),
    sku_group      TEXT NOT NULL,
    order_date     TIMESTAMPTZ NOT NULL,
    delivery_date  TIMESTAMPTZ,
    quantity_kg    NUMERIC(12,3) NOT NULL,
    unit_price_eur NUMERIC(10,4) NOT NULL,
    customer_type  TEXT NOT NULL DEFAULT 'b2b',
    season         TEXT  -- 'spring','summer','autumn','winter'
);

-- EnPI baseline per processo (ISO 50001)
CREATE TABLE IF NOT EXISTS scm.enpi_baseline (
    process           TEXT PRIMARY KEY,
    kwh_per_kg_target NUMERIC(8,4) NOT NULL,  -- obiettivo ISO 50001
    kwh_per_kg_actual_ytd NUMERIC(8,4),
    baseline_year     INTEGER NOT NULL DEFAULT 2024,
    notes             TEXT
);
```

### Pattern 6: Logica Reorder-Point (InventoryManager)

**Formula EOQ semplificata (fixed reorder point):**

```python
# reorder.py — pure function, completamente testabile
from dataclasses import dataclass
from decimal import Decimal

@dataclass(frozen=True)
class ReorderSignal:
    sku_id: str
    current_qty: Decimal
    reorder_point: Decimal
    reorder_qty: Decimal
    lead_time_days: int
    is_below_threshold: bool
    deficit_qty: Decimal
    estimated_cost_eur: Decimal

def check_reorder(
    sku_id: str,
    current_qty: float,
    reorder_point: float,
    reorder_qty: float,
    unit_cost_eur: float,
    lead_time_days: int = 7,
) -> ReorderSignal:
    """Check if a SKU needs reordering (pure function).

    Returns ReorderSignal with is_below_threshold=True when
    current_qty < reorder_point.
    """
    below = current_qty < reorder_point
    deficit = max(0.0, reorder_point - current_qty)
    return ReorderSignal(
        sku_id=sku_id,
        current_qty=Decimal(str(current_qty)),
        reorder_point=Decimal(str(reorder_point)),
        reorder_qty=Decimal(str(reorder_qty)),
        lead_time_days=lead_time_days,
        is_below_threshold=below,
        deficit_qty=Decimal(str(deficit)),
        estimated_cost_eur=Decimal(str(reorder_qty * unit_cost_eur)),
    )
```

### Pattern 7: ISO 50001 EnPI kWh/kg (EnergyOptimizer)

**Definizione:** Energy Performance Indicator = consumo elettrico [kWh] / produzione [kg].
Il confronto con il baseline rivela l'efficienza energetica del processo.

```python
# enpi.py — pure function, testabile con numeri esatti
from dataclasses import dataclass

@dataclass(frozen=True)
class EnpiReport:
    process: str
    kwh_total: float
    kg_total: float
    enpi_actual: float           # kWh/kg misurato nel periodo
    enpi_baseline: float         # kWh/kg obiettivo ISO 50001
    deviation_pct: float         # (actual - baseline) / baseline * 100
    is_above_baseline: bool
    off_peak_kwh_pct: float      # % consumi in ore fuori picco

def compute_enpi(
    kwh_readings: list[float],
    kg_readings: list[float],
    enpi_baseline_kwh_per_kg: float,
    is_peak_hour_flags: list[bool],
) -> EnpiReport:
    """Compute ISO 50001 Energy Performance Indicator.

    Args:
        kwh_readings: List of kWh measurements for each time slot.
        kg_readings: List of kg processed in each time slot (may contain None → skip).
        enpi_baseline_kwh_per_kg: ISO 50001 target (from scm.enpi_baseline).
        is_peak_hour_flags: True when reading was during peak tariff hours.

    Returns:
        EnpiReport with actual vs baseline comparison.
    """
    # Filter slots where kg_processed is known
    valid_pairs = [
        (kwh, kg) for kwh, kg in zip(kwh_readings, kg_readings) if kg and kg > 0
    ]
    if not valid_pairs:
        raise ValueError("Nessun dato valido (kg > 0) nei readings forniti")

    kwh_total = sum(k for k, _ in valid_pairs)
    kg_total = sum(g for _, g in valid_pairs)
    enpi_actual = kwh_total / kg_total if kg_total > 0 else float("inf")
    deviation_pct = (enpi_actual - enpi_baseline_kwh_per_kg) / enpi_baseline_kwh_per_kg * 100

    total_kwh_all = sum(kwh_readings)
    off_peak_kwh = sum(k for k, flag in zip(kwh_readings, is_peak_hour_flags) if not flag)
    off_peak_pct = off_peak_kwh / total_kwh_all * 100 if total_kwh_all > 0 else 0.0

    return EnpiReport(
        process="computed",
        kwh_total=kwh_total,
        kg_total=kg_total,
        enpi_actual=round(enpi_actual, 4),
        enpi_baseline=enpi_baseline_kwh_per_kg,
        deviation_pct=round(deviation_pct, 2),
        is_above_baseline=enpi_actual > enpi_baseline_kwh_per_kg,
        off_peak_kwh_pct=round(off_peak_pct, 2),
    )
```

### Pattern 8: Simulatore OEPV parametrico (CostAnalyzer)

**Formula OEPV:** Punteggio totale = 0.70 * Pt + 0.30 * Pe

dove:
- Pt = punteggio tecnico (0–70, configurabile da input)
- Pe = punteggio economico calcolato dalla curva ribasso non lineare

**Curva ribasso non lineare (D.Lgs 50/2016 / Codice Appalti 2023 semplificata — parametrica):**

Il punteggio economico Pe per un ribasso Ri% sulla Base d'Asta BA:

```
Pe(Ri) = Pe_max * (1 - exp(-lambda * Ri / Ri_ref))
```

dove lambda e Ri_ref sono parametri configurabili (non i valori definitivi del Codice Appalti).
Questa è la forma parametrica F9 — la calibrazione legale è rimandata a F12.

```python
# oepv.py — simulatore parametrico, pure function, completamente testabile
import math
from dataclasses import dataclass, field

@dataclass(frozen=True)
class OepvConfig:
    """Parametri configurabili del modello OEPV F9.

    Tutti i coefficienti sono input espliciti — nessun hardcoded.
    F12 sostituirà con i valori definitivi del Codice Appalti 2023.
    """
    base_d_asta_eur: float = 108_000.0    # BA Mantis (configurabile)
    weight_technical: float = 0.70         # 70% tecnico
    weight_economic: float = 0.30          # 30% economico
    pe_max: float = 30.0                   # punteggio economico massimo
    lambda_curve: float = 3.0             # curvatura ribasso (parametrico F9)
    ribasso_ref_pct: float = 20.0         # ribasso di riferimento per normalizzazione
    anomaly_threshold_pct: float = 20.0   # soglia warning ribasso anomalo (configurabile)

@dataclass(frozen=True)
class OepvResult:
    ribasso_pct: float
    offer_eur: float
    pt: float                  # punteggio tecnico (input)
    pe: float                  # punteggio economico calcolato
    total_score: float         # 0.70*Pt + 0.30*Pe (normalizzato su 100)
    is_anomaly_warning: bool   # ribasso > anomaly_threshold (warning non definitivo)
    sensitivity: dict          # {ribasso_delta: score_delta} per ±1%, ±5%, ±10%

@dataclass(frozen=True)
class SensitivityRow:
    ribasso_pct: float
    pe: float
    total_score: float

def compute_oepv(
    ribasso_pct: float,
    pt: float,
    config: OepvConfig = OepvConfig(),
) -> OepvResult:
    """Calcola il punteggio OEPV per un dato ribasso % e punteggio tecnico.

    Args:
        ribasso_pct: Ribasso percentuale sull'offerta economica (es. 10.5 = 10.5%).
        pt: Punteggio tecnico assegnato (0–70).
        config: Parametri configurabili del modello.

    Returns:
        OepvResult con score totale + sensitivity analysis + warning anomalia.
    """
    if not (0 <= ribasso_pct <= 100):
        raise ValueError(f"ribasso_pct deve essere in [0, 100], ricevuto: {ribasso_pct}")
    if not (0 <= pt <= 100 * config.weight_technical):
        raise ValueError(f"pt deve essere in [0, {100*config.weight_technical}]")

    # Curva ribasso non lineare (parametrica F9)
    pe = config.pe_max * (1 - math.exp(-config.lambda_curve * ribasso_pct / config.ribasso_ref_pct))

    # Punteggio totale normalizzato su 100
    total = config.weight_technical * pt + config.weight_economic * pe

    offer = config.base_d_asta_eur * (1 - ribasso_pct / 100)
    is_anomaly = ribasso_pct >= config.anomaly_threshold_pct

    # Sensitivity: variazione score per ribasso ±1%, ±5%, ±10%
    sensitivity = {}
    for delta in [-10.0, -5.0, -1.0, +1.0, +5.0, +10.0]:
        r_alt = max(0.0, min(100.0, ribasso_pct + delta))
        pe_alt = config.pe_max * (1 - math.exp(-config.lambda_curve * r_alt / config.ribasso_ref_pct))
        total_alt = config.weight_technical * pt + config.weight_economic * pe_alt
        sensitivity[f"{delta:+.0f}%"] = round(total_alt - total, 4)

    return OepvResult(
        ribasso_pct=ribasso_pct,
        offer_eur=round(offer, 2),
        pt=round(pt, 4),
        pe=round(pe, 4),
        total_score=round(total, 4),
        is_anomaly_warning=is_anomaly,
        sensitivity=sensitivity,
    )

def build_sensitivity_table(
    ribasso_range: list[float],
    pt: float,
    config: OepvConfig = OepvConfig(),
) -> list[SensitivityRow]:
    """Genera una tabella di sensitivity su un range di ribassi."""
    return [
        SensitivityRow(
            ribasso_pct=r,
            pe=compute_oepv(r, pt, config).pe,
            total_score=compute_oepv(r, pt, config).total_score,
        )
        for r in ribasso_range
    ]
```

### Pattern 9: Holt-Winters hand-rolled con numpy (DemandForecaster)

**Motivazione:** Preferenza per minimal new deps + determinismo. I parametri α, β, γ sono
configurabili e fissi (no ottimizzazione MLE). Il fallback seasonal-naive viene attivato
automaticamente per serie con < `min_periods` osservazioni.

```python
# holt_winters.py — implementazione deterministica, LLM-free, numpy-only
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class HoltWintersConfig:
    alpha: float = 0.3        # livello (smoothing)
    beta: float = 0.1         # trend
    gamma: float = 0.3        # stagionalità
    season_length: int = 12   # 12 mesi per domanda tessile
    min_periods: int = 24     # minimo per HW; sotto → fallback seasonal-naive

@dataclass(frozen=True)
class ForecastResult:
    sku_group: str
    horizon: int
    forecast: list[float]
    method: str               # "holt_winters" | "seasonal_naive"
    config: HoltWintersConfig

def forecast_holt_winters(
    series: list[float],
    horizon: int,
    config: HoltWintersConfig = HoltWintersConfig(),
    sku_group: str = "unknown",
) -> ForecastResult:
    """Triple Exponential Smoothing (Holt-Winters additive) — deterministic, numpy-only.

    Falls back to seasonal_naive when len(series) < config.min_periods.
    All parameters are fixed (no MLE optimization) — fully reproducible.
    """
    n = len(series)
    if n < config.min_periods:
        return _seasonal_naive_fallback(series, horizon, config, sku_group)

    arr = np.array(series, dtype=float)
    m = config.season_length
    alpha, beta, gamma = config.alpha, config.beta, config.gamma

    # Initialization: level = mean of first season, trend = mean slope, seasonals = deviation
    L = np.mean(arr[:m])
    T = (np.mean(arr[m:2*m]) - np.mean(arr[:m])) / m if n >= 2 * m else 0.0
    S = arr[:m] - L

    levels = np.zeros(n)
    trends = np.zeros(n)
    seasonals = np.zeros(n + horizon)
    seasonals[:m] = S

    for t in range(n):
        s_idx = t % m
        L_new = alpha * (arr[t] - seasonals[s_idx]) + (1 - alpha) * (L + T)
        T_new = beta * (L_new - L) + (1 - beta) * T
        seasonals[t + m] = gamma * (arr[t] - L) + (1 - gamma) * seasonals[s_idx]
        L, T = L_new, T_new
        levels[t], trends[t] = L, T

    # Forecast
    forecasts = [
        max(0.0, L + (h + 1) * T + seasonals[n + h - m + (h % m)])
        for h in range(horizon)
    ]

    return ForecastResult(
        sku_group=sku_group,
        horizon=horizon,
        forecast=[round(f, 2) for f in forecasts],
        method="holt_winters",
        config=config,
    )

def _seasonal_naive_fallback(
    series: list[float],
    horizon: int,
    config: HoltWintersConfig,
    sku_group: str,
) -> ForecastResult:
    """Seasonal naive: ripete l'ultima stagione disponibile."""
    m = config.season_length
    tail = series[-m:] if len(series) >= m else series
    forecast = [tail[i % len(tail)] for i in range(horizon)]
    return ForecastResult(
        sku_group=sku_group,
        horizon=horizon,
        forecast=[round(f, 2) for f in forecast],
        method="seasonal_naive",
        config=config,
    )
```

### Pattern 10: Rolling MAPE (DemandForecaster KPI)

```python
# mape.py — pure function
def compute_mape(actuals: list[float], forecasts: list[float]) -> float:
    """Compute Mean Absolute Percentage Error over matched pairs.

    Returns MAPE in [0.0, inf). Returns 0.0 when no valid pairs exist.
    Clamps contribution per punto a max 100% per evitare outlier da valori vicino a 0.
    """
    if not actuals or not forecasts:
        return 0.0
    pairs = [(a, f) for a, f in zip(actuals, forecasts) if a > 0]
    if not pairs:
        return 0.0
    return sum(min(abs(a - f) / a, 1.0) for a, f in pairs) / len(pairs) * 100
```

### Pattern 11: Mantis Synthetic Dataset (SCM-05)

Valori sintetici realistici per un'impresa tessile italiana SME. Tutti i valori sono inventati
e documentati esplicitamente come sintetici.

**SKU Master (esempi):**
```
SKU-YARN-NE20-BLU   | Filato Ne20 Blu       | raw_yarn  | 850 kg reorder | 7gg lead | €3.20/kg
SKU-YARN-NE30-BIA   | Filato Ne30 Bianco    | raw_yarn  | 1200 kg        | 7gg      | €2.85/kg
SKU-DYE-REACT-BLU   | Colorante Reattivo Bl | accessory | 50 kg          | 14gg     | €28.50/kg
SKU-SPARE-NEEDLE-L  | Aghi telaio Large     | spare_part| 200 pcs        | 21gg     | €0.85/pcs
SKU-FAB-JERSEY-BLU  | Jersey Blu 140gsm     | fabric    | 500 kg         | —        | €8.40/kg
SKU-FAB-TWILL-GRY   | Twill Grigio 180gsm   | fabric    | 300 kg         | —        | €10.20/kg
```

**EnPI Baseline ISO 50001 per Mantis:**
```
Tintoria (dyeing):    3.80 kWh/kg  (target), 4.12 kWh/kg (YTD 2024 — 8% sopra baseline)
Finissaggio (finishing): 2.20 kWh/kg (target), 2.18 kWh/kg (YTD 2024 — entro baseline)
```

**Capacità produttiva Mantis (sintetica):**
```
Telai: 12 unità, produzione media 850 kg/turno/telaio
Tintoria: 4 vasche da 500 kg, 2 cicli/giorno
Finissaggio: 2 stentatoi, 1.200 kg/h
Turni: 3 × 8h, 5 giorni/settimana
```

**Dati ordini storici (18 mesi, sintetici):**
- SKU group "jersey": ~12.000 kg/mese con picco estivo (+35%) e invernale (+20%)
- SKU group "twill": ~8.000 kg/mese, domanda più stabile (CV ~12%)

### Anti-Patterns to Avoid

- **uuid4() inline nel nodo:** Re-genera ID diversi ad ogni replay → audit inconsistente (CR-04)
- **write() con kwargs:** `await self._audit.write(action_type=...)` → TypeError immediato (CR-02)
- **Audit prima di interrupt():** Doppia scrittura su replay → righe duplicate in audit.actions (CR-02)
- **Datetime naive nel gateway:** Passare `"2026-01-01T08:00:00"` senza tz → 500 invece di 422 (WR-02)
- **str(exc) nel body 500:** Espone DSN o class names ad attaccanti (WR-05)
- **KPI senza clamp:** MAPE o ratio senza bounds → ValidationError su modelli Pydantic con le= (CR-05)
- **Import da __all__ sbagliato:** `from module import NonExistentClass` → ImportError al boot (CR-01)
- **reorder_qty senza default_factory:** lista mutabile come default in Pydantic → shared state bug

---

## Don't Hand-Roll

| Problema | Non costruire | Usare invece | Perché |
|----------|---------------|-------------|--------|
| Routing condizionale del cluster supply | Custom dispatcher | `build_supply_subgraph` (nuovo, mirror di `build_knowledge_subgraph`) | Già testato; gestisce fallback + logging automatico |
| Scrittura audit | Custom PG INSERT | `AuditWriter.write(record)` (positional) | Garantisce dual-write PG+NATS + outbox fallback (D-56) |
| Persistenza stato HITL | Custom session storage | `AsyncPostgresSaver` (LangGraph checkpoint) | Resume cross-session, survive restart |
| Enum ActionType + CHECK constraint | Custom validation | Estendere `enums.py` + migrazione 011 in lockstep | Drift tra enum e SQL → CheckViolationError a runtime |
| Idempotency per gateway endpoints | Custom cache | `IdempotencyCache` + `check_idempotency_cache` (già in gateway) | Già implementato con TTL 5min; evita double-submission |
| ID di correlazione audit | uuid4() inline | `_stable_id(state)` derivato da thread_id | uuid4() inline non sopravvive a replay (CR-04) |

**Key insight:** Ogni elemento di infrastruttura — subgraph, audit, checkpoint, idempotency —
è già implementato nelle Fasi 4-8. Phase 9 aggiunge solo logica di dominio SCM pura
(reorder, EnPI, OEPV, HW). Usare l'infrastruttura esistente senza modificarla.

---

## Common Pitfalls

### Pitfall 1: Replicare CR-04 — ID instabili nel replay LangGraph

**Cosa va storto:** Ogni agente HITL genera un ID (recommendation_id, proposal_id, plan_id)
con `uuid4()` al momento dell'esecuzione del nodo. LangGraph re-esegue il nodo ad ogni resume
dell'interrupt: prima esecuzione → ID_A, resume → ID_B. Le righe di audit draft + signoff
hanno IDs diversi, rendendo impossibile la correlazione.

**Perché succede:** È il comportamento normale di LangGraph con stateful nodes — il nodo viene
"riavvolto" ad ogni resume per garantire la consistenza del grafo.

**Come evitare:** Derivare SEMPRE l'ID da `state.get("thread_id")` (stabile tra replay) o
includere l'ID nello state delta al primo giro e leggerlo dallo state al resume:

```python
# Corretto — derivato da thread_id (stabile)
proposal_id = hashlib.sha256(
    f"{AGENT_ID}.{state.get('thread_id', 'unknown')}".encode()
).hexdigest()[:32]
```

**Warning signs:** ID diversi tra HITL_DRAFT e HITL_SIGNOFF nelle righe di `audit.actions`
per lo stesso `thread_id`.

---

### Pitfall 2: Replicare CR-02 — AuditWriter chiamato con kwargs

**Cosa va storto:** `await self._audit.write(action_type=ActionType.REORDER_ALERT, ...)` →
`TypeError: write() got unexpected keyword argument 'action_type'`. L'agente non scrive
mai audit e propaga 500.

**Perché succede:** `AuditWriter.write(self, record: AuditRecord)` accetta un solo argomento
posizionale di tipo AuditRecord. Il pattern sbagliato è copiato da documentazione o da
implementazioni precedenti senza leggere la firma.

**Come evitare:** Costruire sempre `AuditRecord(...)` completo, poi `await self._audit.write(record)`.
Riferimento: `trn_shift_handover/agent.py::_write_audit()` — usare come template.

**Warning signs:** Crash immediato su ogni percorso HITL; test che mockano l'audit_writer
ma non verificano la firma.

---

### Pitfall 3: Replicare CR-01 — ImportError al boot da nome classe sbagliato

**Cosa va storto:** `lifespan.py` importa `from scm_cost_analyzer.aggregator import CostAggregator`
ma il modulo espone `HistoricalCostAggregator`. ImportError al boot → gateway non avvia.

**Perché succede:** Il nome della classe nel modulo Python non corrisponde a quello usato
nell'import (typo, refactoring parziale, `__all__` aggiornato ma import non allineato).

**Come evitare:** Verificare `__all__` del modulo prima di scrivere l'import nel gateway.
Non assumere che il nome della classe sia uguale al tipo che si vuole importare.

**Warning signs:** `ImportError: cannot import name 'X' from 'module'` al boot del gateway.

---

### Pitfall 4: Replicare WR-02 — datetime naive nel request model

**Cosa va storto:** `EnergyOptimizerRequest` non ha `@field_validator` per i datetime.
Il client invia `"2026-01-15T08:00:00"` senza timezone → Pydantic lo accetta come naive →
crash 500 interno all'agente invece del 422 al boundary HTTP.

**Perché succede:** Il confine di validazione è spostato all'interno dell'agente invece di
essere al perimetro HTTP dove appartiene.

**Come evitare:** Ogni request model del gateway con campi `datetime` DEVE avere:

```python
@field_validator("ts_from", "ts_to")
@classmethod
def _require_tz(cls, v: datetime) -> datetime:
    if v.tzinfo is None:
        raise ValueError("Il campo datetime deve essere tz-aware (UTC).")
    return v
```

**Warning signs:** 500 invece di 422 per richieste con datetime senza timezone.

---

### Pitfall 5: Replicare WR-05 — str(exc) nel body HTTP 500

**Cosa va storto:** `{"error": str(exc), "thread_id": ...}` nel body della risposta 500
espone DSN del database, path del filesystem, nomi di classi interne, stack trace parziali.

**Come evitare:** Usare il pattern WR-05 dal gateway knowledge:

```python
def _handle_agent_error(exc: Exception, thread_id: str) -> JSONResponse:
    logger.error("supply_agent_error", thread_id=thread_id, error=str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_agent_error", "thread_id": thread_id},
    )
```

**Warning signs:** Vedere DSN o path nel body di risposta durante i test di integrazione.

---

### Pitfall 6: MAPE o altri ratio senza clamp → ValidationError su Pydantic le=

**Cosa va storto:** `mape = abs(actual - forecast) / actual` restituisce >100% su valori
vicini a zero → `ValidationError` su `MapeReport.mape: float = Field(le=100.0)`.

**Come evitare:** Clampare sempre prima di costruire il modello:

```python
mape = min(compute_mape(actuals, forecasts), 100.0)
```

**Warning signs:** ValidationError su costruzione modello report con valori estremi.

---

### Pitfall 7: asyncpg datetime — NEVER use .isoformat() in queries

**Cosa va storto:** `await conn.fetch("SELECT * FROM scm.energy_readings WHERE ts > $1", ts.isoformat())`
→ asyncpg non accetta stringhe come parametri temporali; richiede oggetti `datetime`.

**Come evitare:** Passare SEMPRE oggetti `datetime` Python direttamente ad asyncpg:

```python
# CORRETTO
rows = await conn.fetch(
    "SELECT * FROM scm.energy_readings WHERE ts >= $1 AND ts < $2",
    ts_from,   # datetime object, tz-aware
    ts_to,     # datetime object, tz-aware
)
# SBAGLIATO
rows = await conn.fetch(
    "SELECT * FROM scm.energy_readings WHERE ts >= $1",
    ts_from.isoformat(),  # NON fare questo
)
```

---

## Code Examples

### Query asyncpg su scm.inventory_levels

```python
# repository.py — InventoryManager
async def fetch_current_levels(
    pool: asyncpg.Pool,
    sku_ids: list[str],
) -> list[dict]:
    """Fetch latest inventory level per SKU (latest ts per sku_id)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT ON (il.sku_id)
                il.sku_id,
                il.quantity,
                il.ts,
                sm.reorder_point,
                sm.reorder_qty,
                sm.unit_cost_eur,
                sm.lead_time_days
            FROM scm.inventory_levels il
            JOIN scm.sku_master sm USING (sku_id)
            WHERE il.sku_id = ANY($1::text[])
            ORDER BY il.sku_id, il.ts DESC
            """,
            sku_ids,
        )
    return [dict(r) for r in rows]
```

### Query aggregazione EnPI per periodo

```python
# repository.py — EnergyOptimizer
async def fetch_energy_readings(
    pool: asyncpg.Pool,
    process: str,
    ts_from: datetime,
    ts_to: datetime,
) -> list[dict]:
    """Fetch energy readings for a process in [ts_from, ts_to)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT ts, asset_id, kwh, kg_processed, is_peak_hour
            FROM scm.energy_readings
            WHERE process = $1 AND ts >= $2 AND ts < $3
            ORDER BY ts
            """,
            process,
            ts_from,   # datetime object — mai .isoformat()
            ts_to,
        )
    return [dict(r) for r in rows]
```

### Query ordini storici per DemandForecaster

```python
# repository.py — DemandForecaster
async def fetch_monthly_orders(
    pool: asyncpg.Pool,
    sku_group: str,
    months_back: int = 24,
) -> list[dict]:
    """Fetch monthly aggregated orders for a SKU group."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                DATE_TRUNC('month', order_date) AS month,
                SUM(quantity_kg) AS total_kg
            FROM scm.historical_orders
            WHERE sku_group = $1
              AND order_date >= NOW() - INTERVAL '1 month' * $2
            GROUP BY 1
            ORDER BY 1
            """,
            sku_group,
            months_back,
        )
    return [dict(r) for r in rows]
```

---

## State of the Art

| Approccio vecchio | Approccio attuale (Phase 9) | Quando cambiato | Impatto |
|-------------------|-----------------------------|-----------------|---------|
| Placeholder node lineare (Phase 4) | Subgraph condizionale con routing (Phase 6 pattern) | Phase 6 | Il cluster supply deve usare `build_supply_subgraph`, non `build_cluster_subgraph` |
| uuid4() inline per correlation ID | ID stabile derivato da thread_id | Phase 8 CR-04 | Obbligatorio per correttezza audit HITL |
| AuditWriter con kwargs | AuditWriter con AuditRecord posizionale | Phase 8 CR-02 | TypeError a runtime se non corretto |
| approval_id generato per HITL pending | approval_id=None per pending | Phase 7 CR-03 | ValidationError o inconsistenza audit |
| statsmodels ExponentialSmoothing | HW hand-rolled numpy (Phase 9 decision) | Phase 9 | Zero nuove dipendenze; determinismo garantito |
| ExponentialSmoothing con fit() | Parametri fissi α,β,γ da config | Phase 9 decision | Riproducibilità; nessuna dipendenza da scipy.optimize |

**Deprecated/outdated per Phase 9:**
- `build_cluster_subgraph` per il cluster supply: usare `build_supply_subgraph` (nuova funzione)
- Qualsiasi `uuid4()` inline come correlation ID in nodi HITL: usare hash del thread_id

---

## Assumptions Log

| # | Claim | Section | Rischio se sbagliato |
|---|-------|---------|----------------------|
| A1 | `sft-ml` (numpy, pandas, scikit-learn) è già nel workspace uv e disponibile ai pacchetti supply come dipendenza transitiva | Standard Stack | Aggiungere dipendenza esplicita a pyproject.toml di scm-demand-forecaster |
| A2 | `build_supply_subgraph` andrà aggiunto a `clusters.py` con fallback su `cost-analyzer` — la costante `_SCM_DEFAULT_AGENT` non confligge con nomi esistenti | Architecture Patterns | Minimo — solo conflitto di naming se già esistesse una costante |
| A3 | La migrazione 011 è il prossimo indice disponibile (010 = ultima migrazione confermata in codebase) | Standard Stack / DDL | Se esiste già una 011 da un altro branch, rinumerare |
| A4 | Il ProductionPlanner (`apps/agents/ops/production-planner`) ha già un'interfaccia `__call__(state)` standard che accetta un `AgentState` con il piano domanda nel campo state | Architecture (DemandForecaster HITL target) | Leggere il contratto di state del ProductionPlanner prima di implementare il wiring |
| A5 | I parametri HW α=0.3, β=0.1, γ=0.3, stagionalità=12 sono ragionevoli per dati mensili di ordini tessili | Holt-Winters | Valori di alpha/beta/gamma non ottimali → previsioni imprecise; il KPI MAPE rivelerà il problema |
| A6 | I valori OEPV sintetici Mantis (BA=108.000€, Pt calcolato dal punteggio tecnico simulato) sono realistici per un'offerta software SME tessile italiana | OEPV simulator | Puramente documentale/dimostrativo — nessun impatto funzionale |

---

## Open Questions

1. **Dipendenza sft-ml nei pacchetti supply**
   - Cosa sappiamo: `sft-ml` ha numpy+pandas; i pacchetti supply hanno `dependencies = []` nel pyproject.toml attuale.
   - Cosa non è chiaro: se aggiungere `sft-ml` come dipendenza esplicita o referenziare numpy direttamente.
   - Raccomandazione: aggiungere `numpy>=1.26.0,<3.0.0` + `pandas>=2.3.0,<3.0.0` direttamente nel `pyproject.toml` di `scm-demand-forecaster` e `scm-cost-analyzer` (che usa numpy per la curva ribasso). Non serve sft-ml come dipendenza diretta — le librerie di base bastano.

2. **Wiring DemandForecaster → ProductionPlanner nel subgraph supply**
   - Cosa sappiamo: DemandForecaster deve pubblicare il piano a ProductionPlanner via HITL.
   - Cosa non è chiaro: ProductionPlanner è nel cluster ops; DemandForecaster è nel cluster supply. Il HITL cross-cluster avviene tramite state dict (il piano viene scritto in `state["demand_plan"]`) o tramite una chiamata diretta al supervisor?
   - Raccomandazione: Il piano domanda viene incluso nel `state` delta di ritorno di DemandForecaster. L'approvazione HITL è gestita internamente a DemandForecaster (interrupt + audit). Dopo l'approvazione, il piano è disponibile in state e il gateway può routarlo separatamente a ProductionPlanner se necessario. Questa è la soluzione più semplice che non richiede cross-cluster invocation.

3. **Seed SQL vs fixture Python per il dataset Mantis**
   - Cosa sappiamo: il CONTEXT.md parla di "seed migration + fixture".
   - Raccomandazione: usare un file `011_create_scm_schema.sql` per DDL + un file separato `scm_mantis_seed.sql` (non numerato, da applicare solo in dev/test). Le migrazioni numerate devono restare idempotenti; i seed dati sono one-shot e non devono essere numerati come migrazioni.

---

## Environment Availability

| Dipendenza | Richiesta da | Disponibile | Versione | Fallback |
|------------|-------------|-------------|---------|----------|
| PostgreSQL + TimescaleDB | scm.* schema DDL + query | ✓ (Docker Compose) | timescale/timescaledb:2.18.0-pg16 | — |
| asyncpg | query agents | ✓ (sft-agents dep) | 0.31.0 | — |
| numpy | HW forecasting + OEPV | ✓ (sft-ml dep) | >=1.26.0 | — |
| pandas | preparazione serie temporali | ✓ (sft-ml dep) | >=2.3.0 | — |
| langgraph | HITL interrupt/resume | ✓ (sft-agents dep) | >=0.4,<0.5 | — |
| statsmodels | alternativa HW | NON usato (decisione) | 0.14.6 su PyPI | Hand-rolled HW con numpy |
| testcontainers | test migrazione 011 | ✓ (pattern 009/010) | come test_migration_010.py | — |

**Missing dependencies with no fallback:** nessuna

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` di ogni pacchetto (`[tool.pytest.ini_options]`) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -m "not integration"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Tipo test | Comando automatizzato | File |
|--------|----------|-----------|----------------------|------|
| SCM-01 | Reorder alert quando qty < reorder_point | unit | `pytest tests/test_reorder.py -x` | Wave 0 |
| SCM-01 | HITL interrupt + audit singolo row dopo resume | unit (mock) | `pytest tests/test_inventory_hitl.py -x` | Wave 0 |
| SCM-02 | EnPI kWh/kg confronto con baseline | unit | `pytest tests/test_enpi.py -x` | Wave 0 |
| SCM-02 | HITL interrupt + audit energy proposal | unit (mock) | `pytest tests/test_energy_hitl.py -x` | Wave 0 |
| SCM-03 | OEPV score formula 70/30 con curva non lineare | unit | `pytest tests/test_oepv.py -x` | Wave 0 |
| SCM-03 | CostAnalyzer autonomo — audit con Decision.AUTO | unit (mock) | `pytest tests/test_cost_analyzer_agent.py -x` | Wave 0 |
| SCM-04 | Holt-Winters output deterministico per serie fissa | unit | `pytest tests/test_holt_winters.py -x` | Wave 0 |
| SCM-04 | Fallback seasonal-naive per serie < min_periods | unit | `pytest tests/test_holt_winters.py::test_seasonal_naive -x` | Wave 0 |
| SCM-04 | Rolling MAPE calcolato correttamente | unit | `pytest tests/test_mape.py -x` | Wave 0 |
| SCM-04 | DemandForecaster HITL interrupt + piano in state | unit (mock) | `pytest tests/test_demand_hitl.py -x` | Wave 0 |
| SCM-05 | Seed data presente in DB (smoke) | integration | `pytest tests/ -m integration -x` | Wave SCM schema |
| General | migrazione 011 idempotente + nuovi action types | integration | `pytest infra/migrations/timescale/tests/test_migration_011.py` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q -m "not integration"`
- **Per wave merge:** `pytest tests/ -q -m "not integration"` + `pytest infra/migrations/timescale/tests/`
- **Phase gate:** Full suite green prima di `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `apps/agents/supply/inventory-manager/tests/test_reorder.py` — REQ SCM-01 unit
- [ ] `apps/agents/supply/inventory-manager/tests/test_inventory_hitl.py` — REQ SCM-01 HITL
- [ ] `apps/agents/supply/energy-optimizer/tests/test_enpi.py` — REQ SCM-02 unit
- [ ] `apps/agents/supply/energy-optimizer/tests/test_energy_hitl.py` — REQ SCM-02 HITL
- [ ] `apps/agents/supply/cost-analyzer/tests/test_oepv.py` — REQ SCM-03 unit (formula OEPV)
- [ ] `apps/agents/supply/cost-analyzer/tests/test_cost_analyzer_agent.py` — REQ SCM-03 agent
- [ ] `apps/agents/supply/demand-forecaster/tests/test_holt_winters.py` — REQ SCM-04 HW
- [ ] `apps/agents/supply/demand-forecaster/tests/test_mape.py` — REQ SCM-04 MAPE
- [ ] `apps/agents/supply/demand-forecaster/tests/test_demand_hitl.py` — REQ SCM-04 HITL
- [ ] `infra/migrations/timescale/tests/test_migration_011.py` — migrazione + schema scm

---

## Security Domain

### Applicable ASVS Categories

| Categoria ASVS | Si applica | Controllo standard |
|---------------|-----------|-------------------|
| V2 Authentication | no (Phase 11 concern — dev-mode user_roles) | — |
| V3 Session Management | parziale | AsyncPostgresSaver (LangGraph PG checkpointer) |
| V4 Access Control | parziale | `user_roles` propagato in state (Phase 11 enforcement) |
| V5 Input Validation | **sì** | Pydantic frozen+extra=forbid su tutti i request models; `@field_validator` tz-aware |
| V6 Cryptography | no | Nessuna crittografia applicativa in Phase 9 |

### Known Threat Patterns per lo stack SCM

| Pattern | STRIDE | Mitigazione standard |
|---------|--------|---------------------|
| SQL injection via sku_id / process params | Tampering | Parametri asyncpg ($1, $2...) — mai string interpolation |
| Prompt injection via sku_name / failure_mode (se LLM è coinvolto) | Tampering | CostAnalyzer e DemandForecaster sono LLM-free; EnergyOptimizer usa LLM solo per rationale (non per decisioni) |
| Replay attack su endpoint HITL (double-resume) | Tampering | IdempotencyCache (già nel gateway) |
| Data exposure di DSN nel body 500 | Info Disclosure | Pattern WR-05 — generic error body |
| Overflow KPI (MAPE > 100%, EnPI negativa) | Tampering | Validazione Pydantic + clamp esplicito nei pure functions |
| OWASP LLM — Supply-chain risk (SCM-05 SEC-02) | Supply-Chain | Nessuna dipendenza LLM esterna nei calcoli core; parametri OEPV da config firmata |

---

## Sources

### Primary (HIGH confidence — codebase diretta)

- `packages/sft-agents/src/sft_agents/runtime/clusters.py` — pattern esatto `build_knowledge_subgraph` replicato per supply
- `packages/sft-agents/src/sft_agents/audit/writer.py` — firma `write(self, record: AuditRecord)` verificata
- `packages/sft-agents/src/sft_agents/models/enums.py:67` — `ActionType` enum verificata; lockstep migration 010
- `infra/migrations/timescale/010_extend_audit_knw.sql` — template migrazione CHECK constraint verificato
- `apps/api-gateway/src/svc_api_gateway/routers/knowledge_agents.py` — template gateway verificato
- `apps/api-gateway/src/svc_api_gateway/lifespan.py` — wiring DI verificato
- `apps/api-gateway/src/svc_api_gateway/dependencies.py` — pattern `get_knowledge_children` verificato
- `.planning/phases/08-agents-knowledge-training/08-REVIEW.md` — 5 Critical + 5 Warning lessons verificate

### Secondary (MEDIUM confidence — PyPI verificato)

- PyPI `statsmodels==0.14.6` [VERIFIED: `pip index versions statsmodels`] — verificato ma non usato
- PyPI `numpy>=1.26.0` [VERIFIED: in `sft-ml/pyproject.toml` del workspace]
- PyPI `pandas>=2.3.0` [VERIFIED: in `sft-ml/pyproject.toml` del workspace]

### Tertiary (ASSUMED — conoscenza di training)

- Logica reorder-point EOQ: formula standard operations research [ASSUMED]
- ISO 50001 EnPI definizione kWh/kg: standard industriale internazionale [ASSUMED]
- Holt-Winters Triple Exponential Smoothing algoritmo: algoritmo classico forecasting [ASSUMED]
- OEPV formula 70/30 + curva non lineare: come da REQUIREMENTS.md (ECO-02) [ASSUMED — parametrizzazione F9]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — tutte le dipendenze verificate nel workspace o su PyPI
- Architecture patterns: HIGH — codice sorgente Phase 6/7/8 letto direttamente
- Domain logic (reorder, EnPI, HW, OEPV): MEDIUM — algoritmi standard ma parametri Mantis ASSUMED
- Pitfalls: HIGH — derivati dai 5 bug critici documentati in 08-REVIEW.md
- Security: MEDIUM — ASVS applicato per analogia con Phase 8 (nessun cambio sostanziale di threat surface)

**Research date:** 2026-05-24
**Valid until:** 2026-06-24 (stack stabile; solo aggiornamenti breaking di langgraph potrebbero invalidare)
