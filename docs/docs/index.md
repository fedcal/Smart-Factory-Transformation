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

> **Nota metriche:** tutti i valori quantitativi (riduzione downtime, MTTR, scrap rate, ROI)
> sono **SIMULATED TARGET** derivati dalla baseline sintetica Mantis (Phase 9) e dalla
> letteratura industry 4.0. Non rappresentano SLA o promesse contrattuali. Vedi
> [Analisi Economica → Value Driver](economic-analysis/value-drivers.md) e il
> [Assumption Register](assumptions/index.md) per i dettagli metodologici.

## Per chi

| Audience | Cosa trovano qui |
|----------|-----------------|
| **Valutatori della competizione** | Documentazione tecnica ed economica per assessment 70/30; architettura, workflow, use case, ROI |
| **Community opensource** | SDK estendibile, 16 agenti reference documentati, pattern HITL riusabili in altri verticali industria 4.0 |
| **Stakeholder Mantis (fittizi)** | Workflow operativi, dashboard, runbook di approvazione/override, analisi del dominio tessile |

## Deliverable di Concorso

Indice delle sezioni deliverable principali per la valutazione 70/30:

| Area | Sezione | Descrizione |
|------|---------|-------------|
| **Architettura** | [Architettura](architecture/overview.md) | Diagrammi C4, stack tecnico, HITL cycle |
| **Analisi Funzionale** | [Analisi Funzionale](functional-analysis/index.md) | Workflow Operations, Maintenance, Training |
| **Casi d'Uso** | [Casi d'Uso](use-cases/index.md) | 8 use case prioritizzati (quick win / medio termine) |
| **Roadmap** | [Roadmap di Adozione](adoption-roadmap/index.md) | Fasi, KPI, milestone, rischi |
| **Analisi Economica** | [Analisi Economica](economic-analysis/index.md) | TCO 3 anni, OEPV simulato, value driver |
| **Security & Governance** | [Sicurezza & Governance](security/index.md) | STRIDE threat model, OWASP LLM, explainability |
| **ADR** | [ADR](adr/index.md) | 5 Architecture Decision Records tracciati |
| **Trasformazione** | [Trasformazione](transformation.md) | Percorso di trasformazione e vision |
| **Interfaccia Utente** | [Mock UI](ui-mock.md) | User journey, dashboard, approvazione HITL |

## Navigazione

- [Iniziare](getting-started.md) — Requisiti, setup locale e prime esecuzioni
- [Architettura](architecture/overview.md) — Diagramma ad alto livello e principi guida
- [Dominio](domain/index.md) — Analisi del dominio tessile manifatturiero
- [Agenti](agents/operations/operator-assistant.md) — 16 agenti reference documentati
- [Knowledge Layer](knowledge-layer/architecture.md) — RAG ibrido BGE-M3 + Qdrant
- [Contributing](contributing/index.md) — Convenzioni, toolchain e workflow CI

---

*Progetto: [smart-factory-transformation/smart-factory-transformation](https://github.com/smart-factory-transformation/smart-factory-transformation) — Licenza: Apache 2.0*
