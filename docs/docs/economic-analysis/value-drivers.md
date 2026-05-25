# Value Driver

<!-- ECO-04: Value driver come SIMULATED TARGET con baseline Mantis sintetica + letteratura -->
<!-- SC-3: nessun contenuto aspirazionale non implementato nel codice -->

I value driver della trasformazione digitale sono quantificati come **SIMULATED TARGET**
ottenuti dalla baseline sintetica Mantis (Phase 9, dataset sintetico) e cross-referenziati
con i range della letteratura industry 4.0 tessile. Non rappresentano promesse di
miglioramento, ma stime coerenti con il sistema implementato e con i benchmark del settore.

> **SIMULATED TARGET — non promesse** (ECO-04, SC-3).
> Ogni percentuale e derivata dalla baseline sintetica Mantis o dalla letteratura citata.
> Vedi l'Assumption Register (`docs/docs/assumptions/index.md`) per i dettagli.

## Assumption Register — Voci Economiche (ECO-04, DOC-12)

Le assunzioni specifiche dei value driver economici sono registrate qui di seguito
e vanno lette in congiunzione con il registro principale in `docs/docs/assumptions/index.md`.

| ID | Assunzione | Categoria | Stato |
|---|---|---|:---:|
| A-051 | PT ottimistico = 68.0/70: punteggio tecnico massimo per scenario ottimistico OEPV (SIMULATED TARGET) | cost | active |
| A-052 | PT base = 55.0: punteggio tecnico realistico per offerta solida OEPV (SIMULATED TARGET) | cost | active |
| A-053 | Riduzione downtime 15-25% derivata da baseline sintetica Mantis + letteratura McKinsey/Deloitte Industry 4.0 | simulation | active |
| A-054 | Riduzione scarto (scrap rate) 10-20% derivata da proxy audit QUALITY_VERDICT + letteratura tessile | simulation | active |
| A-055 | Riduzione MTTR 20-35% derivata da attivazione agente PredictiveMaintenance + letteratura Accenture/IDC Industry 4.0 | simulation | active |
| A-056 | Riduzione tempo formazione 30-40% derivata da attivazione TrainingCoach + baseline SOP sintetica Phase 8 | simulation | active |
| A-057 | Riuso conoscenza 40-60% derivata da KnowledgeCurator (Phase 8) + letteratura KM industry 4.0 | simulation | active |

## 1. Riduzione Downtime (ECO-04)

> **SIMULATED TARGET: 15-25%** — Assumption A-053

**Baseline Mantis sintetica (Phase 9):** il simulatore `sim-textile` inietta fault mode
(rottura trama, deriva tensione, anomalie termiche) con frequenza calibrata sul dataset
sintetico. Il rilevamento precoce da parte dell'AnomalyDetector riduce il tempo tra
il primo segnale anomalo e l'intervento dell'operatore.

**Range letteratura tessile industry 4.0:**
- McKinsey Global Institute (2022), "Industry 4.0 in Textiles": riduzione downtime 15-30%
  con manutenzione predittiva AI nei 24 mesi post-deployment.
- Deloitte (2021), "Smart Factory Survey": 70% dei siti con manutenzione predittiva riporta
  riduzione unplanned downtime >15%.

**Sistema implementato:** AnomalyDetector (Phase 6) + PredictiveMaintenance (Phase 7)
con HITL interrupt-to-resume; alert pubblicati su NATS JetStream; audit trail completo.

## 2. Riduzione Scrap Rate (ECO-04)

> **SIMULATED TARGET: 10-20%** — Assumption A-054

**Baseline Mantis sintetica:** il proxy per lo scrap rate e il rapporto tra audit rows
con `action_type=QUALITY_VERDICT` negative e totali (Phase 9 CostAnalyzer, Phase 10 UI KPI).
Il sistema implementa la rilevazione di anomalie qualitative in tempo reale.

**Range letteratura:**
- European Textile Industry (Euratex, 2023), "Digitalisation in Textile Manufacturing":
  riduzione difettosita 10-25% con controllo qualita AI real-time.
- Fraunhofer IPA (2022): sistemi di visione + AI riducono scrap 12-18% in filatura.

**Sistema implementato:** ShiftHandover (Phase 8) con aggregazione alert ANOMALY_ALERT;
KPI scrap_rate nel dashboard Angular (Phase 10).

## 3. Riduzione MTTR (Mean Time To Repair) (ECO-04)

> **SIMULATED TARGET: 20-35%** — Assumption A-055

**Baseline Mantis sintetica:** il PredictiveMaintenance agent (Phase 7) genera
raccomandazioni HITL per interventi preventivi. Il MTTR sintetico e calcolato come
delta tra primo alert e chiusura del ticket HITL (audit trail Phase 4).

**Range letteratura:**
- IDC Manufacturing Insights (2023), "AI-Powered Maintenance in EU SME":
  riduzione MTTR 20-40% con sistemi AI-assisted nei 18 mesi post-deployment.
- Aveva / OMRON (2022): riduzione MTTR 25-35% in impianti tessili con gemello digitale.

**Sistema implementato:** PredictiveMaintenance + MaintenanceCoach (Phase 7) con HITL
interrupt-to-resume; RCA specialist per analisi causa radice.

## 4. Riduzione Tempo Formazione (ECO-04)

> **SIMULATED TARGET: 30-40%** — Assumption A-056

**Baseline Mantis sintetica (Phase 8):** il TrainingCoach eroga SOP sintetiche
strutturate (Phase 8, knowledge cluster). Il tempo di onboarding e stimato sulla
baseline di 20 SOP + 10 domain pages indicizzate in Qdrant (BGE-M3, Phase 5).

**Range letteratura:**
- Gartner (2022), "AI in Corporate Learning": sistemi RAG-based riducono il tempo
  di ricerca informazioni del 30-50% rispetto a ricerca manuale su documenti statici.
- Brandon Hall Group (2023): personalizzazione AI del training riduce il tempo di
  completamento moduli del 25-40%.

**Sistema implementato:** TrainingCoach (Phase 8) + RetrievalPipeline BGE-M3/Qdrant
(Phase 5) + KnowledgeCurator per ingestione continua SOP (Phase 8).

## 5. Riuso Conoscenza / Knowledge Reuse (ECO-04)

> **SIMULATED TARGET: 40-60%** — Assumption A-057

**Baseline Mantis sintetica (Phase 8):** KnowledgeCurator indicizza automaticamente
i documenti operativi (SOP, shift handover, incidenti risolti) in Qdrant. Il retrieval
ibrido BGE-M3 (dense + sparse) consente il riuso della conoscenza tacita formalizzata.

**Range letteratura:**
- McKinsey (2023), "The Economic Potential of Generative AI": riduzione tempo ricerca
  informazioni 40-60% in contesti manifatturieri con RAG enterprise.
- AIIM (2022), "State of Information Management": sistemi KM AI-assistiti riducono
  la ri-creazione di documenti duplicati del 35-55%.

**Sistema implementato:** KnowledgeCurator (Phase 8, autonomous D-KC-04) + DocumentationSynthesizer
+ ShiftHandover per formalizzazione shift knowledge (Phase 8).

## Tabella Riepilogativa

| Value Driver | SIMULATED TARGET | Baseline | Letteratura | Sistema |
|---|:---:|---|---|---|
| Riduzione Downtime | 15-25% | sim-textile fault injection | McKinsey 2022; Deloitte 2021 | AnomalyDetector + PredictiveMaint. |
| Riduzione Scrap | 10-20% | QUALITY_VERDICT proxy | Euratex 2023; Fraunhofer IPA 2022 | ShiftHandover + CostAnalyzer KPI |
| Riduzione MTTR | 20-35% | HITL ticket delta | IDC 2023; Aveva/OMRON 2022 | PredictiveMaint. + MaintenanceCoach |
| Riduzione Formazione | 30-40% | SOP baseline sintetica | Gartner 2022; Brandon Hall 2023 | TrainingCoach + RetrievalPipeline |
| Knowledge Reuse | 40-60% | KnowledgeCurator ingest | McKinsey 2023; AIIM 2022 | KnowledgeCurator + BGE-M3/Qdrant |

> Tutti i valori sono **SIMULATED TARGET** derivati da sistemi implementati nel codice
> (SC-3 traceability). Le percentuali non costituiscono SLA o garanzie contrattuali.

## Avvertenza Metodologica

Il dataset Mantis e sintetico (non reale): i sensori sono generati da `sim-textile`
con distribuzione gaussiana calibrata su fault mode industria tessile (Assumption A-031).
I benchmark letteratura citati si riferiscono a contesti industry 4.0 manifatturiero
europeo con caratteristiche simili (PMI, filatura/tessitura).

La validazione su dati reali richiede un deployment pilota con misure prima/dopo
su KPI operativi reali (fuori scope MVP v1.0, Assumption A-017).
