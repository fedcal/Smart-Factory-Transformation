# Value Drivers

<!-- ECO-04: Value drivers as SIMULATED TARGET with synthetic Mantis baseline + literature -->
<!-- SC-3: no aspirational content not implemented in code -->

The value drivers of the digital transformation are quantified as **SIMULATED TARGETS**
derived from the synthetic Mantis baseline (Phase 9, synthetic dataset) and cross-referenced
against industry 4.0 textile literature ranges. They do not represent performance promises,
but estimates consistent with the implemented system and sector benchmarks.

> **SIMULATED TARGET — not promises** (ECO-04, SC-3).
> Each percentage is derived from the synthetic Mantis baseline or cited literature.
> See the Assumption Register (`docs/docs/assumptions/index.md`) for details.

## Assumption Register — Economic Entries (ECO-04, DOC-12)

Economic value driver assumptions are recorded below and should be read in conjunction
with the main register at `docs/docs/assumptions/index.md`.

| ID | Assumption | Category | Status |
|---|---|---|:---:|
| A-051 | Optimistic PT = 68.0/70: maximum technical score for optimistic OEPV scenario (SIMULATED TARGET) | cost | active |
| A-052 | Base PT = 55.0: realistic technical score for solid offer OEPV scenario (SIMULATED TARGET) | cost | active |
| A-053 | Downtime reduction 15-25% derived from synthetic Mantis baseline + McKinsey/Deloitte Industry 4.0 literature | simulation | active |
| A-054 | Scrap rate reduction 10-20% derived from QUALITY_VERDICT audit proxy + textile literature | simulation | active |
| A-055 | MTTR reduction 20-35% derived from PredictiveMaintenance agent activation + IDC/Aveva Industry 4.0 literature | simulation | active |
| A-056 | Training time reduction 30-40% derived from TrainingCoach activation + synthetic SOP baseline Phase 8 | simulation | active |
| A-057 | Knowledge reuse 40-60% derived from KnowledgeCurator (Phase 8) + KM industry 4.0 literature | simulation | active |

## 1. Downtime Reduction (ECO-04)

> **SIMULATED TARGET: 15-25%** — Assumption A-053

**Synthetic Mantis baseline (Phase 9):** the `sim-textile` simulator injects fault modes
(weft breakage, tension drift, thermal anomalies) at frequencies calibrated on the synthetic
dataset. Early detection by AnomalyDetector reduces the time between the first anomaly signal
and operator intervention.

**Textile industry 4.0 literature ranges:**
- McKinsey Global Institute (2022), "Industry 4.0 in Textiles": 15-30% downtime reduction
  with AI predictive maintenance in 24 months post-deployment.
- Deloitte (2021), "Smart Factory Survey": 70% of sites with predictive maintenance report
  unplanned downtime reduction >15%.

**Implemented system:** AnomalyDetector (Phase 6) + PredictiveMaintenance (Phase 7)
with HITL interrupt-to-resume; alerts published on NATS JetStream; full audit trail.

## 2. Scrap Rate Reduction (ECO-04)

> **SIMULATED TARGET: 10-20%** — Assumption A-054

**Synthetic Mantis baseline:** the proxy for scrap rate is the ratio between audit rows
with negative `action_type=QUALITY_VERDICT` and totals (Phase 9 CostAnalyzer, Phase 10 UI KPI).
The system implements real-time quality anomaly detection.

**Literature ranges:**
- European Textile Industry (Euratex, 2023), "Digitalisation in Textile Manufacturing":
  10-25% defect reduction with real-time AI quality control.
- Fraunhofer IPA (2022): vision + AI systems reduce scrap 12-18% in spinning.

**Implemented system:** ShiftHandover (Phase 8) with ANOMALY_ALERT aggregation;
scrap_rate KPI in Angular dashboard (Phase 10).

## 3. MTTR Reduction (Mean Time To Repair) (ECO-04)

> **SIMULATED TARGET: 20-35%** — Assumption A-055

**Synthetic Mantis baseline:** the PredictiveMaintenance agent (Phase 7) generates HITL
recommendations for preventive interventions. Synthetic MTTR is calculated as the delta
between first alert and HITL ticket closure (Phase 4 audit trail).

**Literature ranges:**
- IDC Manufacturing Insights (2023), "AI-Powered Maintenance in EU SME":
  20-40% MTTR reduction with AI-assisted systems in 18 months post-deployment.
- Aveva / OMRON (2022): 25-35% MTTR reduction in textile plants with digital twin.

**Implemented system:** PredictiveMaintenance + MaintenanceCoach (Phase 7) with HITL
interrupt-to-resume; RCA specialist for root cause analysis.

## 4. Training Time Reduction (ECO-04)

> **SIMULATED TARGET: 30-40%** — Assumption A-056

**Synthetic Mantis baseline (Phase 8):** TrainingCoach delivers structured synthetic SOPs
(Phase 8, knowledge cluster). Onboarding time is estimated against the baseline of 20 SOPs
+ 10 domain pages indexed in Qdrant (BGE-M3, Phase 5).

**Literature ranges:**
- Gartner (2022), "AI in Corporate Learning": RAG-based systems reduce information search
  time by 30-50% compared to manual search on static documents.
- Brandon Hall Group (2023): AI personalisation of training reduces module completion
  time by 25-40%.

**Implemented system:** TrainingCoach (Phase 8) + RetrievalPipeline BGE-M3/Qdrant
(Phase 5) + KnowledgeCurator for continuous SOP ingestion (Phase 8).

## 5. Knowledge Reuse (ECO-04)

> **SIMULATED TARGET: 40-60%** — Assumption A-057

**Synthetic Mantis baseline (Phase 8):** KnowledgeCurator automatically indexes operational
documents (SOPs, shift handovers, resolved incidents) in Qdrant. BGE-M3 hybrid retrieval
(dense + sparse) enables reuse of formalised tacit knowledge.

**Literature ranges:**
- McKinsey (2023), "The Economic Potential of Generative AI": 40-60% reduction in
  information search time in manufacturing contexts with enterprise RAG.
- AIIM (2022), "State of Information Management": AI-assisted KM systems reduce
  duplicate document re-creation by 35-55%.

**Implemented system:** KnowledgeCurator (Phase 8, autonomous D-KC-04) + DocumentationSynthesizer
+ ShiftHandover for shift knowledge formalisation (Phase 8).

## Summary Table

| Value Driver | SIMULATED TARGET | Baseline | Literature | System |
|---|:---:|---|---|---|
| Downtime Reduction | 15-25% | sim-textile fault injection | McKinsey 2022; Deloitte 2021 | AnomalyDetector + PredictiveMaint. |
| Scrap Reduction | 10-20% | QUALITY_VERDICT proxy | Euratex 2023; Fraunhofer IPA 2022 | ShiftHandover + CostAnalyzer KPI |
| MTTR Reduction | 20-35% | HITL ticket delta | IDC 2023; Aveva/OMRON 2022 | PredictiveMaint. + MaintenanceCoach |
| Training Reduction | 30-40% | Synthetic SOP baseline | Gartner 2022; Brandon Hall 2023 | TrainingCoach + RetrievalPipeline |
| Knowledge Reuse | 40-60% | KnowledgeCurator ingest | McKinsey 2023; AIIM 2022 | KnowledgeCurator + BGE-M3/Qdrant |

> All values are **SIMULATED TARGETS** derived from systems implemented in code
> (SC-3 traceability). Percentages do not constitute SLA or contractual guarantees.

## Methodological Note

The Mantis dataset is synthetic (not real): sensors are generated by `sim-textile`
with Gaussian distribution calibrated on textile industry fault modes (Assumption A-031).
Literature benchmarks cited refer to European industry 4.0 manufacturing contexts
with similar characteristics (SMEs, spinning/weaving).

Validation on real data requires a pilot deployment with before/after measurements
on real operational KPIs (out of scope MVP v1.0, Assumption A-017).
