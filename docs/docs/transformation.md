---
lang: it
requirements:
  - DOC-17
tags:
  - trasformazione
  - opensource
  - agentic
  - hitl
  - oepv
---

# Trasformazione — Dalla Traccia Originale alla Piattaforma Agentica

## Origine del Progetto

Questo progetto nasce dalla rielaborazione di una traccia originale del concorso,
che descriveva un cliente fittizio del settore tessile con esigenze di digitalizzazione
di Operations, Maintenance e Training, valutata con il criterio OEPV 70/30
(offerta economicamente più vantaggiosa — 70% tecnico, 30% economico, Base d'Asta €108.000).

La traccia originale è stata **trasformata e ampliata** in un prodotto opensource
autocontenuto, mantenendo il dominio tessile come caso di riferimento ma ridisegnando
l'architettura, il modello di delivery e la governance AI.

---

## Cosa È Cambiato e Perché

### Da Consulenza Proprietaria a Piattaforma Opensource Self-Hosted

**Traccia originale del concorso:** soluzione GenAI erogata tramite stack cloud con
servizi proprietari; il cliente dipende dal vendor per aggiornamenti e sicurezza dei dati.

**Questa piattaforma:** stack 100% self-hostable (Ollama/vLLM + Qdrant + FastAPI + Angular SSR
su Nx monorepo), con LLM open-weight (famiglia Qwen2.5, licenza Apache 2.0). I dati
industriali restano on-premise. Il codice è riusabile e modificabile da qualsiasi organizzazione.

**Perché:** la tutela dei dati industriali è un requisito non negoziabile per le PMI
manifatturiere. L'opensource garantisce auditabilità, sostenibilità economica nel lungo
periodo e libertà da vendor lock-in.

### Da "AI che Decide" a Human-in-the-Loop Sistematico

**Traccia originale del concorso:** gli agenti AI sono presentati come strumenti di
automazione; il ruolo dell'operatore umano è implicito.

**Questa piattaforma:** ogni azione critica di un agente AI richiede l'approvazione
esplicita di un essere umano informato (HITL — Human-in-the-Loop), con evidenze tracciabili
(audit trail, RAG citations, confidence score) prima che l'azione venga eseguita.
Il principio guida è: *nessun essere umano è mai solo davanti a un problema operativo,
ma nessuna decisione critica bypassa la responsabilità umana.*

**Perché:** le normative emergenti sull'AI (EU AI Act, ISO/IEC 42001) e il contesto
operativo industriale (sicurezza, MTTR, qualità) richiedono governance esplicita e
auditabilità. La fiducia operativa si costruisce con trasparenza, non con automazione cieca.

### Da Tre Cluster a Quattro Cluster con Supply Chain

**Traccia originale del concorso:** Operations, Maintenance, Training — tre domini.

**Questa piattaforma:** quattro cluster di agenti (16 agenti reference):
- **Operations & Production:** OperatorAssistant, ProductionPlanner, QualityInspector, AnomalyDetector
- **Maintenance & Reliability:** PredictiveMaintenance, RCASpecialist, MaintenanceCoach, DowntimeAnalyzer
- **Knowledge & Training:** KnowledgeCurator, TrainingCoach, ShiftHandover, DocumentationSynthesizer
- **Supply Chain & Economics:** InventoryManager, EnergyOptimizer, CostAnalyzer, DemandForecaster

**Perché:** il dominio tessile manifatturiero ha dipendenze forti tra qualità, produzione
e supply chain. CostAnalyzer e DemandForecaster chiudono il ciclo economico con
modelli OEPV riproducibili.

### Da Dataset Generici a Dati Tessili Simulati + Benchmark Pubblici

**Traccia originale del concorso:** dataset non specificati; uso di LLM generici.

**Questa piattaforma:** simulatore custom di linea tessile (telai, filatoi, orditoi)
con eventi OPC-UA simulati + replay di dataset pubblici validati (NASA C-MAPSS per
manutenzione predittiva, UCI Manufacturing). LLM: Qwen2.5 multilingua (IT/EN)
con supporto nativo del dominio manifatturiero.

**Perché:** la credibilità tecnica richiede dati di dominio. I dataset pubblici rendono
i benchmark riproducibili da terzi.

### Da Valutazione 70/30 Narrativa a Modello OEPV Riproducibile

**Traccia originale del concorso:** la valutazione OEPV è descritta come criterio
di gara senza un modello economico verificabile.

**Questa piattaforma:** il modello economico è un notebook/script Python riproducibile
(`docs/economic-analysis/`) che, dati i parametri configurabili (Base d'Asta €108.000,
ammortamento GPU su 3 anni, elettricità 0,25 EUR/kWh, ribasso giustificato 10–15%
con rationale scritto), genera: TCO 3 anni, punteggio OEPV 70/30, analisi di
sensibilità non lineare, comparison stack cloud vs self-hosted.

**Perché:** una proposta economica difendibile in sede di gara deve essere riproducibile
e tracciabile. L'Assumption Register (DOC-12) documenta ogni ipotesi con fonte.

---

## Scelte Chiave Mantenute dalla Traccia Originale

| Elemento | Descrizione |
|----------|-------------|
| Dominio | Industria tessile manifatturiera (cliente di riferimento fittizio: Mantis Textile Group) |
| Criteri di gara | OEPV 70/30, Base d'Asta €108.000 |
| Lingua principale | Italiano (con mirror EN per la community opensource) |
| Audience primaria | Operatori di fabbrica, tecnici manutenzione, capi reparto, CIO |
| Scope | PoC funzionante su dati simulati, non integrazione hardware reale |

---

## Scelte Introdotte dalla Trasformazione

| Scelta | Rationale |
|--------|-----------|
| Stack 100% self-hostable | Tutela dati industriali on-premise; nessun vendor lock-in |
| LLM open-weight (Qwen2.5) | Apache 2.0; multilingua IT/EN; costo inferenza controllato |
| HITL sistematico (LangGraph) | Governance AI esplicita; audit trail per ogni decisione critica |
| RAG su knowledge base aziendale | Riduzione knowledge silos; SOP ricercabili da tutti i ruoli |
| Modello economico riproducibile | Difendibilità in sede di gara; trasparenza per valutatori |
| Documentazione bilingue IT/EN | Competizione italiana + community opensource internazionale |
| Monorepo Nx polyglot | Python (agenti/backend) + Angular SSR (UI); CI/CD unificata |

---

## Elementi Esplicitamente Esclusi

- Riferimenti, branding o contenuti della traccia originale del concorso riprodotti testualmente
- Integrazione con hardware fisico (PLC reali, sensori fisici) — tutto simulato
- Fine-tuning LLM da zero — LoRA mirata è candidata v2
- Multi-tenant SaaS — il prodotto è single-tenant on-premise by design
- Computer vision custom per controllo qualità ottico — candidata v2

---

## Traceability dei Requisiti

| Requisito | Elemento di trasformazione |
|-----------|---------------------------|
| DOC-17 | Questo documento |
| SC-4 | Nessun riferimento al brand originale in deliverable pubblici |
| ECO-01..08 | Modello OEPV riproducibile in `docs/economic-analysis/` |
| DEL-01..08 | Sezioni docs corrispondenti (architettura, workflow, use case, UI, roadmap, economico) |
| HITL (tutti i cluster) | LangGraph interrupt + `/v1/approvals` + audit trail |
