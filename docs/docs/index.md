# Smart Factory Transformation

> **Ogni decisione critica dell'AI passa per un essere umano informato, ma nessun essere umano è mai solo davanti a un problema operativo.**

---

## Cos'è

Smart Factory Transformation è una **piattaforma opensource self-hostable** che orchestra una squadra di agenti GenAI per supportare operatori, manutentori, knowledge worker e responsabili di magazzino in una fabbrica tessile. Gli agenti leggono segnali da PLC, MES e sensori industriali, suggeriscono o eseguono azioni sempre soggette al controllo umano, e capitalizzano la knowledge base aziendale per ridurre i silos di expertise.

Il progetto è simultaneamente:

- una **reference architecture** documentata bilingue (IT/EN) servita via GitHub Pages
- un **SDK Python** per scrivere agenti custom estendibili ad altri verticali industriali
- un **PoC funzionante** su dati simulati e dataset pubblici (NASA C-MAPSS, UCI Manufacturing)
- una **proposta economica realistica** modellata sull'OEPV (Base d'Asta €108.000)

Il principio architetturale fondamentale è il **Human-in-the-Loop (HITL)**: nessuna azione critica viene eseguita senza che un essere umano informato abbia approvato o potuto intervenire. Questo non è un vincolo tecnico — è il presupposto etico del progetto.

## Per chi

| Audience | Cosa trovano qui |
|----------|-----------------|
| **Valutatori della competizione** | Documentazione tecnica ed economica per assessment 70/30; architettura, workflow, use case, ROI |
| **Community opensource** | SDK estendibile, 16 agenti reference documentati, pattern HITL riusabili in altri verticali industria 4.0 |
| **Stakeholder Mantis (fittizi)** | Workflow operativi, dashboard, runbook di approvazione/override, analisi del dominio tessile |

## Stato del progetto

![Phase 1: Foundation & Monorepo](https://img.shields.io/badge/Phase_1-Foundation_%26_Monorepo-blue)

Il progetto si sviluppa in fasi successive:

| Fase | Titolo | Stato |
|------|--------|-------|
| **1** | Foundation & Monorepo | In corso |
| **2** | Documentation & Domain Analysis | Prossima |
| **3** | OT Integration & Simulation | — |
| **4** | Core Agentic Runtime | — |
| **5** | Frontend & UX | — |
| **6+** | Agenti Reference, Observability, Security, Economic Model | — |

## Navigazione

- [Iniziare](getting-started.md) — Requisiti, setup locale e prime esecuzioni
- [Architettura](architecture/overview.md) — Diagramma ad alto livello e principi guida
- [Contributing](contributing/index.md) — Convenzioni, toolchain e workflow CI

---

*Progetto: [fedcal/Smart-Factory-Transformation](https://github.com/fedcal/Smart-Factory-Transformation) — Licenza: Apache 2.0*
