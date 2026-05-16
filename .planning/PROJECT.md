# Smart Factory Transformation

> Piattaforma opensource agentica per la trasformazione digitale di un'industria tessile manifatturiera, costruita attorno al paradigma **Human-in-the-Loop**. Monorepo con SDK estendibile e 16 agenti reference che coprono Operations, Maintenance, Knowledge e Supply Chain.
>
> Repo: <https://github.com/fedcal/Smart-Factory-Transformation>

---

## What This Is

Smart Factory Transformation è una **piattaforma opensource self-hostable** che orchestra una squadra di agenti GenAI per supportare operatori, manutentori, knowledge worker e responsabili di magazzino in una fabbrica tessile (caso di riferimento: **Mantis Textile Group**). Gli agenti leggono segnali da PLC/MES/sensori industriali e da dati economici/di magazzino, suggeriscono o eseguono azioni sempre soggette al controllo umano, e capitalizzano la knowledge base aziendale per ridurre i silos di expertise.

Il progetto è simultaneamente: (a) una **reference architecture** documentata bilingue (IT/EN) servita via GitHub Pages, (b) un **SDK** Python per scrivere agenti custom, (c) un **PoC funzionante** su dati simulati e dataset pubblici (NASA C-MAPSS, UCI Manufacturing), e (d) una **proposta economica realistica** modellata sull'OEPV (Base d'Asta €108.000) per dimostrarne la sostenibilità.

## Core Value

**Ogni decisione critica dell'AI passa per un essere umano informato, ma nessun essere umano è mai solo davanti a un problema operativo.** Tutto il resto (SDK, agenti, dashboard, ROI) deve servire questo principio: ridurre il time-to-action senza bypassare la responsabilità umana.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

**Piattaforma & Monorepo**

- [ ] Monorepo Nx polyglot (Python + Angular + TypeScript) con caching e graph delle dipendenze
- [ ] SDK Python per scrivere agenti custom (interfaccia uniforme: tools, memory, policies, HITL hooks)
- [ ] CI/CD su GitHub Actions: lint, test, build, deploy docs su GitHub Pages
- [ ] Pubblicazione docs bilingue (IT/EN) via MkDocs Material con i18n

**Core Agentico**

- [ ] Orchestratore agentico basato su **LangGraph** con state machine ispezionabili
- [ ] Integrazione LLM self-hosted (**Qwen2.5 7B/14B/32B** via Ollama/vLLM) con adapter provider-agnostic
- [ ] Vector store self-hosted (Qdrant) per RAG su documentazione tecnica e SOP
- [ ] Policy layer per autorizzazioni, approvazioni umane e audit trail explainable

**Agenti Reference (4 cluster, 16 agenti)**

- [ ] **Operations & Production**: OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector
- [ ] **Maintenance & Reliability**: PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer
- [ ] **Knowledge & Training**: KnowledgeCurator, TrainingCoach, ShiftHandover, DocumentationSynthesizer
- [ ] **Supply Chain & Economics**: InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster

**Integrazione IT/OT (simulata)**

- [ ] Simulatore custom di linea tessile (telai, filatoi, orditoi) con generazione eventi sensori
- [ ] Mock OPC-UA server per integrazione PLC simulata
- [ ] Ingest di dataset pubblici (NASA C-MAPSS turbofan, UCI Manufacturing) per use-case predittivi
- [ ] Bus eventi (es. NATS/Redis Streams) per real-time + batch pipeline

**Frontend & UX**

- [ ] App Angular 18+ con SSR per UI operatore (touch-friendly, factory-floor) e UI tecnico
- [ ] Dashboard control room con visualizzazione stato agenti, KPI (downtime, MTTR, OEE) e alert
- [ ] User journey: approvazione/override umano di ogni azione agentica
- [ ] Design system riusabile (Tailwind + Angular Material o equivalente)

**Documentazione & Deliverable**

- [ ] `docs/` con: Target Architecture, End-to-End Workflows, Use Case prioritizzati (quick win / medio termine), Mock UI/User Journey, Adoption Roadmap con KPI
- [ ] Analisi del dominio tessile manifatturiero (processi, ruoli, pain point)
- [ ] Analisi economica: cost breakdown, modello OEPV simulato, value driver, rischi
- [ ] Threat model + analisi di sicurezza e governance AI (explainability, safety, accesso)
- [ ] Assumption register esplicito (data quality, limiti, scope)

**Sostenibilità & Governance**

- [ ] Modello economico con Base d'Asta €108k, ribasso giustificato, TCO 3 anni
- [ ] Stack 100% self-hostable per garantire dati industriali on-premise
- [ ] Esempi di runbook umani e procedure di escalation/audit

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- **Integrazione con PLC reali / hardware fisico** — il PoC simula OPC-UA e sensori; integrazioni hardware sono responsabilità del deploy on-premise
- **Computer vision custom per controllo qualità ottico** — `QualityInspector` lavora su segnali sensoriali e log; CV avanzata è candidata v2
- **Training/fine-tuning di LLM da zero** — usiamo modelli open-weight (Qwen2.5) eventualmente con LoRA mirate, non foundation training
- **Compliance specifiche (es. ISO 27001, certificazione SIL safety)** — la traccia è dimostrativa; cita standard ma non li certifica
- **Mobile app native** — il frontend è web responsive (Angular SSR); PWA in v2 se necessario
- **Marketplace di agenti di terze parti** — l'SDK è aperto ma niente hosting o registry centralizzato
- **Multi-tenant SaaS** — il prodotto è pensato per deploy single-tenant on-premise; multi-tenancy è anti-feature
- **Riferimenti, branding o contenuti di Accenture** — eliminati esplicitamente dall'origine della traccia
- **Riproduzione testuale della traccia originale** — il materiale è rielaborato e ampliato per evitare similarità

## Context

**Origine.** Il progetto nasce dalla traccia di una competizione aziendale (AI Business Challenge — RFP 2) basata su un cliente fittizio del tessile. La traccia richiede una piattaforma GenAI per Operations, Maintenance e Training con valutazione 70/30 tecnico/economico (modello OEPV — Offerta Economicamente Più Vantaggiosa, Base d'Asta €108.000). Il progetto trasforma e amplia la traccia trasformandola in un **prodotto opensource autocontenuto**, mantenendo il dominio tessile ma rebrandizzando il cliente in **Mantis Textile Group** e rimuovendo ogni riferimento al brand sponsor originale.

**Pain point del cliente di riferimento (Mantis Textile Group).**

- Processi semi-manuali con dipendenza da pochi tecnici esperti
- Documentazione frammentata e in larga parte non strutturata
- Bassa visibilità trasversale tra produzione, manutenzione, training
- Reazione lenta agli imprevisti, MTTR elevato, knowledge silos
- Limitato uso di automazione e AI avanzata

**Ecosistema tecnico.**

- **LLM**: famiglia Qwen2.5 (7B/14B/32B, Apache 2.0) servita via Ollama e vLLM per benchmarking
- **Orchestrazione agentica**: LangGraph (HITL nativo, state ispezionabili, retry e checkpoint)
- **Vector store**: Qdrant self-hosted con embedding multilingua (bge-m3 o simili)
- **Monorepo**: Nx con plugin Python (Nx-Python o Pants integration) e Angular
- **Frontend**: Angular 18+ con SSR, Tailwind, Angular Material
- **Backend dei servizi agentici**: FastAPI + uvicorn
- **Eventi**: NATS JetStream o Redis Streams come bus eventi
- **Simulatori**: simulatore Python custom + mock OPC-UA + replay dataset NASA C-MAPSS, UCI Manufacturing
- **Docs**: MkDocs Material con plugin i18n (IT/EN), diagrammi Mermaid/D2

**Audience.**

1. **Valutatori della competizione**: leggono `docs/` per assessment 70/30
2. **Community opensource**: developer industria 4.0, MES vendor, smart manufacturing
3. **Stakeholder Mantis (fittizi, modellati realisticamente)**: operatori turnisti, capi reparto, tecnici manutenzione, responsabile qualità, CIO, CFO

## Constraints

- **Tech stack**: Python 3.12+ per agenti/backend, Angular 18+ con SSR per UI, Nx come monorepo orchestrator — definito dall'utente
- **AI deployment**: LLM **self-hostable** (Ollama/vLLM) — requisito per sostenibilità economica e tutela dati industriali; cloud API ammesse solo come adapter opzionale
- **Documentazione**: bilingue **IT + EN** — copre sia la competizione italiana sia la community opensource internazionale
- **Repository**: monorepo singolo su <https://github.com/fedcal/Smart-Factory-Transformation>, deploy docs automatico via GitHub Pages
- **Budget di riferimento**: Base d'Asta €108.000 (OEPV) — vincolo per il modello economico
- **Branding**: **zero riferimenti ad Accenture** o ad altri brand presenti nella traccia originale
- **Originalità**: la traccia originale (`Smart Factory Transformation.md`) deve essere rielaborata e ampliata, non riprodotta
- **Hardware target**: nessuna integrazione fisica; tutto simulato in modo realistico ma esplicitamente dichiarato come tale
- **Governance AI**: ogni azione critica richiede approvazione umana (HITL) ed è auditabile; AI explainability è un requisito non funzionale

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Cliente fittizio: **Mantis Textile Group** | Mantiene il dominio tessile della traccia ma rimuove ogni riferimento al brand originale | — Pending |
| Verticale: tessile manifatturiero (come traccia) | Consente confronto con la traccia mantenendo profondità di dominio | — Pending |
| Monorepo: **Nx** | Best-in-class per polyglot Python+Angular; caching e dep-graph cruciali per CI | — Pending |
| Orchestratore: **LangGraph** | HITL nativo, state machine ispezionabili, allineato ai requisiti di governance/explainability | — Pending |
| LLM: **Qwen2.5** self-hosted via Ollama/vLLM | Open weight Apache 2.0, ottimo function calling, multilingua IT/EN, scalabile da edge a server | — Pending |
| Vector store: **Qdrant** self-hosted | Maturo, on-prem first, ottimo per RAG ibrido (dense + sparse) | — Pending |
| Frontend: **Angular 18+ con SSR** | Scelta utente; Nx ha supporto first-class | — Pending |
| Simulazione dati: **simulatore custom + dataset pubblici** (NASA C-MAPSS, UCI) | Combina realismo tessile e benchmark predittivi consolidati | — Pending |
| Docs: **bilingue IT+EN** (MkDocs Material i18n) | Copre competizione italiana + community internazionale | — Pending |
| Agenti reference: **4 cluster × 4 agenti = 16** | Copertura completa del dominio (Ops, Maint, Knowledge, Supply Chain) | — Pending |
| Modello economico: **OEPV simulato** con BA €108k | Allineamento ai criteri di valutazione 70/30 della traccia | — Pending |
| Distribuzione: **monorepo opensource su GitHub** + deploy docs su Pages | Trasparenza, riusabilità, contribuzioni community | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-16 after initialization*
