# Feature Research

**Domain:** Opensource agentic smart-factory platform — textile manufacturing vertical
**Researched:** 2026-05-16
**Confidence:** MEDIUM-HIGH (ecosystem well-documented; textile-specific GenAI agent capabilities verified from multiple industrial and academic sources; HITL patterns verified against LangGraph docs and industrial AI guidance)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features whose absence makes the platform non-credible to evaluators and non-useful to operators.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Real-time sensor/event ingestion | MES and industrial AI baseline; operators expect live data, not batch | MEDIUM | OPC-UA mock → NATS/Redis Streams → agent subscriptions |
| OEE dashboard (Availability × Performance × Quality) | First question any production manager asks; absent = product feels like a toy | LOW-MEDIUM | Requires sensor streams + production schedule; target ≥85% world-class benchmark |
| MTBF / MTTR display per asset | Maintenance baseline KPI; evaluators will look for this immediately | LOW | Calculated from downtime event log; requires structured fault records |
| Anomaly alert with confidence score | Every industrial AI platform ships this; missing it signals immaturity | HIGH | Multivariate time-series; autoencoders or ensemble classifiers on sensor streams |
| HITL approval gate on every non-trivial agent action | Core governance requirement; missing = platform cannot be trusted in production | HIGH | LangGraph `interrupt()` + persistent checkpointer (AsyncPostgresSaver); every action that writes state or triggers work order must pause |
| Audit trail: who approved what and when | Compliance baseline (ISO-equivalent, OEPV evaluators expect it) | MEDIUM | Immutable append-only log: agent proposal → reviewer identity → decision → timestamp → rationale |
| Agent action explainability | Operators will not follow recommendations they cannot understand | HIGH | Each agent must emit a structured `rationale` field alongside its recommendation; no opaque "the AI says so" |
| Override / rollback of any agent decision | If a technician overrides, that decision must be reversible and logged | MEDIUM | State graph rollback via LangGraph checkpoint; override event stored in audit log |
| Shift handover report auto-generation | Industrial operators expect this; verbal handover loses 40-60% of actionable info | MEDIUM | Auto-compile from event log: open alerts, completed tasks, equipment status, open work orders → structured PDF/UI |
| Per-user role-based access (operator / supervisor / technician / manager) | Without RBAC, the HITL model breaks down (anyone can approve anything) | MEDIUM | Policy layer in SDK; four roles minimum; approval authority scoped by role |
| RAG over internal SOPs and technical manuals | Every knowledge platform in industry does this now; it is the minimum viable knowledge feature | HIGH | Qdrant vector store + hybrid dense+sparse retrieval + chunk attribution; multilingual IT/EN |
| Structured downtime event log | Prerequisite for MTBF, MTTR, RCA, predictive maintenance — everything else depends on it | LOW-MEDIUM | Event: asset_id, start_time, end_time, category, cause_code, technician_id |
| Production schedule / work order integration | Agents cannot advise on scheduling without knowing what is planned | MEDIUM | Read-only interface to production plan; mock for PoC, real ERP adapter in v2 |
| Inventory stock level visibility | InventoryManager and CostAnalyzer are useless without it | MEDIUM | BOM-linked stock view; reorder point alerts |
| Documentation in both IT and EN | OEPV evaluation is Italian; community is international | LOW | MkDocs Material i18n plugin; already decided |
| Self-hostable deployment (all components on-prem) | Industrial data sovereignty is non-negotiable; evaluators will flag cloud-only as a risk | HIGH | Docker Compose + optional Kubernetes manifests; no mandatory external API calls |

---

### Differentiators (Competitive Advantage vs Commercial MES/EMI)

Features that separate this platform from Siemens Opcenter, Rockwell FactoryTalk, Tulip, and similar commercial offerings.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| 16 reference agents as working code, not demos | Commercial platforms sell "AI-ready" but ship dashboards; this ships running agents | HIGH | Each agent has concrete tool bindings, not just a chat widget |
| Textile-specific defect taxonomy embedded in QualityInspector | Generic platforms apply no domain knowledge; textile defect vocabulary (broken end, mispick, slub, selvage fault, neppy, oil spot, shade deviation) is built-in | HIGH | Defect ontology in Qdrant; 4-point grading system logic |
| Dye lot tracking and shade deviation alerting | Most industrial AI platforms do not model dye lot as a first-class concept | MEDIUM | Lot → spectrophotometer CIELab delta → tolerance band → alert; right-first-time KPI |
| RUL (Remaining Useful Life) estimation on textile machinery | Bearing degradation on ring spindles, traveller wear, heddle fatigue are textile-specific failure modes not covered in generic platforms | HIGH | NASA C-MAPSS methodology adapted to spindle/loom; outputs days-to-failure distribution |
| OEPV ribasso simulator | No commercial platform ships a procurement scoring model; this is a unique proposal tool | MEDIUM | Formula engine: linear / bilinear / non-linear scoring; TCO 3-year model; sensitivity analysis on ribasso |
| Multi-cluster agent orchestration with inspectable state | LangGraph state machine is fully visible; commercial platforms are black boxes | HIGH | Every agent state transition logged; graph topology visualized in control room UI |
| SDK for custom agent development | Operators can extend the platform without vendor lock-in | HIGH | Python SDK: uniform interface (tools, memory, policy hooks, HITL hooks); documented with examples |
| Bi-directional context between agent clusters | Maintenance findings feed QualityInspector; Quality alerts feed PredictiveMaintenance; no commercial platform does cross-domain agent communication openly | HIGH | Shared event bus (NATS); typed message contracts between clusters |
| On-the-job coaching with step-by-step procedure guidance | TrainingCoach delivers contextual instructions at the machine, not in a training room | HIGH | SOP → step decomposition → current operator query → context-grounded next-step guidance |
| Knowledge reuse rate KPI | Measures how often operator queries are resolved from the knowledge base vs. escalated; no commercial platform tracks this | MEDIUM | Event: query_resolved_from_kb vs. escalated; ratio per week/month |
| Demand forecasting with seasonal textile signals | Apparel seasonality (collections, lead times) differs from generic manufacturing; specialized signals matter | HIGH | Time-series + seasonal decomposition + fabric/yarn demand patterns |
| Energy per unit KPI with ISO 50001 framing | Wet processing (dyeing/finishing) is 60% of textile energy use; tracking energy per kg of processed fabric against ISO 50001 EnPIs is industry-specific | MEDIUM | Energy meter (simulated) → kg output → ratio; baseline + trend |

---

### Anti-Features (Deliberately NOT Built)

Features that seem valuable but should be explicitly rejected.

| Anti-Feature | Why Requested | Why Problematic | Alternative |
|--------------|---------------|-----------------|-------------|
| Fully autonomous agent execution on safety-critical actions | "Why does the human need to approve everything? Just let it do it." | Agentic systems embedded in safety control loops cause cascading failures; blast radius of an error compounds; rollback becomes impossible; industrial safety frameworks (IEC 62443) prohibit AI in safety loops | HITL gate on all irreversible actions; bounded autonomy only for low-risk, easily-reversible operations (e.g., generating a draft report) |
| Multi-tenant SaaS deployment | "Make it available as a cloud service" | Industrial sensor data and production plans are commercially sensitive; cloud processing violates data sovereignty requirements; adds auth/isolation complexity orthogonal to the mission | Single-tenant on-prem deployment; Docker Compose for self-hosting; cloud adapter as optional add-on only |
| Marketplace / third-party agent registry | "Let the community publish agents" | Registry requires trust model, vetting, versioning, hosting — a full product on its own; quality control is unsolvable at launch | Open SDK with documented extension points; community agents live in their own repos |
| Real-time computer vision quality control | "Can the camera detect defects automatically?" | CV requires specialized hardware (line scan cameras, lighting rigs), model training on proprietary defect images, and physical integration — all out of scope for a PoC and documented as v2 | QualityInspector works on sensor signals, statistical process control signals, and manually logged defect events; CV noted explicitly as a v2 candidate |
| Fine-tuning / training LLMs from scratch | "Train a textile-specific model" | Foundation model training requires GPU clusters, millions in compute, and months of work; LoRA fine-tuning is feasible but must be bounded | Use Qwen2.5 open-weight models; LoRA adaptation for domain vocabulary is acceptable in v2 if evaluation data exists |
| Native mobile app | "Operators use phones on the factory floor" | Native app doubles frontend complexity; factory floor environments favor ruggedized terminals, not personal phones; Angular SSR with PWA covers 90% of mobile needs | Responsive Angular SSR; PWA manifest for home-screen installation; touch-friendly UI components |
| Predictive quality "auto-correction" (agent writes PLC setpoints) | "If the agent knows the bath temperature is wrong, why doesn't it just fix it?" | Writing setpoints to PLCs requires SIL-certified safety engineering; an AI-written setpoint that causes an unsafe temperature could injure workers or damage equipment | Agent issues a HITL alert with recommended setpoint adjustment; human operator confirms and applies via certified HMI |
| "Everything agent" (one agent with all tools and broad permissions) | "Simpler to maintain one big agent" | Single large-permission agent dramatically expands attack surface; task drift is harder to detect; errors propagate faster with no containment boundary | 16 scoped agents with minimal tool sets and explicit permission boundaries; each agent answers to a single cluster |
| Real-time streaming to external cloud analytics (telemetry-by-default) | "Send everything to the cloud for analysis" | Production sensor data and quality records leaving the factory without operator consent violates data sovereignty; many textile manufacturers operate under NDA with clients | All analytics run on-prem; external reporting is an opt-in, anonymized, aggregate export only |
| Autonomous purchase order generation | "InventoryManager should just order parts automatically" | Unauthorized financial commitments require ERP authorization flows; AI-generated POs without human review create liability | InventoryManager generates a purchase recommendation with justification; procurement supervisor approves in HITL gate; PO issued by human via ERP |

---

## Standard KPI Definitions

These KPIs must be exposed in the control room dashboard. Definitions are authoritative — agents must use consistent formulas.

| KPI | Formula | Unit | Direction | World-Class Target | Agent(s) Using It |
|-----|---------|------|-----------|-------------------|-------------------|
| **OEE** | Availability × Performance × Quality | % | Higher | ≥85% | AnomalyDetector, ProductionPlanner, DowntimeAnalyzer |
| **Availability** | (Planned Run Time − Downtime) / Planned Run Time | % | Higher | ≥90% | AnomalyDetector, DowntimeAnalyzer |
| **Performance** | (Ideal Cycle Time × Total Count) / Planned Run Time | % | Higher | ≥95% | ProductionPlanner, OperatorAssistant |
| **Quality** | Good Units / Total Units Produced | % | Higher | ≥99.5% | QualityInspector, AnomalyDetector |
| **MTBF** | Total Operating Time / Number of Failures | hours | Higher | Asset-specific baseline | PredictiveMaintenance, DowntimeAnalyzer |
| **MTTR** | Total Repair Time / Number of Repairs | hours | Lower | Asset-specific baseline | MaintenanceCoach, DowntimeAnalyzer, RCASpecialist |
| **Downtime** | Planned Run Time − Actual Run Time | hours/period | Lower | <5% of planned | DowntimeAnalyzer, OperatorAssistant |
| **Scrap Rate** | Scrapped Units / Total Units Produced | % | Lower | <0.5% | QualityInspector, CostAnalyzer |
| **First-Pass Yield (FPY)** | Units passing all quality checks without rework / Total Units Started | % | Higher | ≥99% | QualityInspector, ProductionPlanner |
| **Right-First-Time (RFT) — dyehouse** | Batches achieving target shade without re-dyeing / Total Batches | % | Higher | ≥95% | QualityInspector (dyeing context) |
| **End Break Rate** (spinning) | Number of yarn breaks / 1000 spindle-hours | breaks/1000 sh | Lower | Asset-specific | AnomalyDetector, PredictiveMaintenance |
| **Stops per 100m** (looms) | Loom stop events / metres of fabric produced | stops/100m | Lower | Asset-specific | AnomalyDetector, OperatorAssistant |
| **Training Completion Rate** | Operators who completed training module / Total assigned | % | Higher | ≥95% | TrainingCoach |
| **Knowledge Reuse Rate** | Queries resolved from KB / Total queries | % | Higher | ≥70% | KnowledgeCurator |
| **Energy per Unit** | kWh consumed / kg of processed fabric | kWh/kg | Lower | ISO 50001 EnPI baseline | EnergyOptimizer |
| **Planned vs Unplanned Maintenance** | Planned maintenance events / Total maintenance events | % | Higher (planned) | ≥80% planned | PredictiveMaintenance, DowntimeAnalyzer |
| **Inventory Turnover** | Cost of Goods Sold / Average Inventory Value | ratio | Context-dependent | Textile sector norms | InventoryManager |
| **Demand Forecast Accuracy** | 1 − (|Forecast − Actual| / Actual) | % | Higher | ≥85% | DemandForecaster |

---

## Economic / Financial Features

Required for the OEPV proposal and for making the platform credible to a CFO audience.

| Feature | What It Shows | Complexity | Notes |
|---------|--------------|------------|-------|
| TCO calculator (3-year) | Total cost of ownership: infra, licenses (€0 open-source), integration labor, training, operation | MEDIUM | Parameterized model: server cost, hours of integration work, FTE for operation |
| ROI dashboard | Value drivers: downtime reduction × hourly production value, scrap reduction × material cost, MTTR reduction × labor cost | MEDIUM | Inputs from KPI deltas; outputs estimated annual savings vs. platform cost |
| OEPV ribasso simulator | Given base d'asta €108k and scoring weights (70 tech / 30 economic), compute optimal ribasso under linear/bilinear/non-linear formula | MEDIUM | Formula-parametric; sensitivity table showing score vs. ribasso % |
| Value driver decomposition | Break ROI into: (a) downtime, (b) quality, (c) energy, (d) training time, (e) knowledge reuse | LOW-MEDIUM | Additive model; each driver independently adjustable |
| Assumption register | Explicit list of data quality assumptions, scope limitations, simulation caveats | LOW | Static document but referenced by the economic model to avoid overpromising |

---

## Per-Agent Capability Matrix

### Cluster 1 — Operations & Production

#### OperatorAssistant

**Purpose:** First-line support for machine operators during runtime. Reduces dependency on scarce expert technicians.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Contextual procedure lookup ("how do I fix this loom stop?") | `qdrant.search(defect_type, machine_id)` | SOP vector store, machine spec sheets | None — advisory only |
| Next-step guidance during fault resolution | `rag.retrieve(current_step, fault_code)` | Troubleshooting history, SOP | None — advisory only |
| Alert acknowledgment and routing | `alert.acknowledge(alert_id, operator_id)` | Alert queue | HITL: operator confirms acknowledgment |
| Escalation trigger to supervisor | `escalation.create(alert_id, reason, priority)` | Escalation policy rules | HITL: operator confirms escalation |
| Real-time OEE and machine status read | `telemetry.query(asset_id, metrics=[oee, status])` | Sensor stream, event log | None — read-only |
| Stop categorization logging | `downtime.log(asset_id, category, cause_code)` | Downtime taxonomy | HITL: operator selects cause code |
| Shift status summary | `shift.summarize(shift_id)` | Event log, open alerts | None — read-only |

**Textile-specific tools:** Loom defect vocabulary lookup (broken end, mispick, tight end, slub, selvage, harness failure); spindle status query (end break rate, traveller condition flag); stenter temperature profile check.

---

#### ProductionPlanner

**Purpose:** Translate production targets into executable schedules; adapt plan in real time when disruptions occur.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Schedule generation from demand forecast | `schedule.generate(demand_plan, asset_availability)` | DemandForecaster output, machine calendar, BOM | HITL: supervisor approves schedule before release |
| Changeover optimization (minimize setup time between fabric types) | `changeover.optimize(current_order, next_order, loom_config)` | Changeover matrix, loom specifications | HITL: planner reviews before confirming |
| Real-time schedule replan on disruption | `schedule.replan(disrupted_asset_id, remaining_orders)` | Current schedule, asset availability | HITL: supervisor approves replan |
| Capacity utilization reporting | `capacity.report(period, asset_group)` | Production log, asset calendar | None — read-only |
| Schedule adherence KPI | `kpi.compute(schedule_adherence, period)` | Planned vs. actual completion | None — read-only |
| Work order creation (draft) | `workorder.draft(asset_id, task, priority)` | Production plan | HITL: supervisor approves WO before issuing |

**Textile-specific tools:** Warp beam lifecycle tracking (warp beam changes are long setup events); yarn count and weave structure compatibility check before scheduling order transitions; color sequence optimization (light-to-dark dye scheduling reduces contamination risk).

---

#### QualityInspector

**Purpose:** Continuous quality monitoring across the production chain; classify defects, grade fabric lots, trigger corrective actions.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| In-process defect detection from sensor signals | `defect.detect(asset_id, sensor_window)` | Loom stop patterns, tension variance, speed deviation | None — advisory; alert raised to operator |
| 4-point fabric grading computation | `grade.compute(defect_log, fabric_lot_id)` | Defect log, 4-point system tables | HITL: quality inspector confirms grade before recording |
| Dye lot shade deviation alert | `shade.check(lot_id, cie_lab_values, tolerance_band)` | Spectrophotometer readings (simulated), approved references | HITL: quality supervisor confirms pass/fail |
| Right-First-Time (RFT) rate computation | `kpi.compute(rft, period, asset_group)` | Dye batch records | None — read-only |
| Non-conformance report (NCR) generation | `ncr.draft(lot_id, defect_type, root_cause_hypothesis)` | Defect log, SOP for NCR | HITL: quality manager approves NCR before filing |
| Statistical process control (SPC) chart | `spc.chart(parameter, asset_id, window)` | Process parameter history | None — read-only |
| Scrap / rework disposition recommendation | `disposition.recommend(lot_id, defect_severity)` | Defect grading, cost data | HITL: quality supervisor approves disposition |

**Textile-specific knowledge:** Woven fabric defect taxonomy — broken end, mispick, tight end, slub, neppy, oil spot, color fly, knots, dropped pick, selvage (cut/waved/creased), reed mark. Knit fabric defect taxonomy — dropped stitch, hole, run, barre effect. Dyeing defects — shade variation (between-batch, within-batch), unlevel dyeing, streakiness, bleed.

---

#### AnomalyDetector

**Purpose:** Continuous multivariate anomaly detection on all sensor streams; classify anomaly severity; route alerts.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Real-time anomaly scoring | `anomaly.score(asset_id, sensor_window, model_id)` | Sensor streams (temperature, vibration, current, pressure, tension) | None — automated; fires alert if threshold exceeded |
| Alert classification (severity: info / warning / critical) | `alert.classify(anomaly_score, asset_id, context)` | Anomaly score, historical baseline, asset criticality | None — automated; HITL triggered at warning/critical |
| Alert routing to appropriate agent/operator | `alert.route(alert_id, severity, asset_id)` | Routing policy (which severity → which role) | None — automated routing |
| Anomaly explanation generation | `anomaly.explain(alert_id)` | Feature importance from detection model, sensor readings | None — advisory |
| False-positive feedback capture | `feedback.record(alert_id, operator_verdict)` | Operator acknowledgment | HITL: operator marks as false positive after review |
| Baseline drift detection (seasonal / production shift) | `baseline.check(asset_id, current_period, reference_period)` | Historical sensor baselines | Advisory; maintenance team notified |
| Confidence threshold enforcement | `threshold.get(asset_id, alert_type)` | Threshold policy store | None — configuration |

**Textile-specific sensors monitored:** Loom: weft insertion pressure, warp tension, reed force, motor current, picks-per-minute. Spinning: spindle RPM per position, ring temperature, traveller wear signal (current spike pattern), end break events. Warping: beam tension uniformity, speed consistency, yarn count deviation. Dyeing: bath temperature profile, pH, liquor ratio, pump pressure, chemical dosing rate. Stenter: chamber temperatures (multi-zone), chain speed, overfeed ratio, exit width.

---

### Cluster 2 — Maintenance & Reliability

#### PredictiveMaintenance

**Purpose:** Estimate Remaining Useful Life (RUL) for critical assets; generate maintenance recommendations before failure occurs.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| RUL estimation per asset | `rul.estimate(asset_id, sensor_history, model_id)` | Sensor history (NASA C-MAPSS methodology adapted), maintenance history | None — advisory output |
| Maintenance recommendation generation | `maintenance.recommend(asset_id, rul_estimate, workload)` | RUL estimate, production schedule, parts inventory | HITL: maintenance supervisor approves before scheduling |
| Predictive maintenance work order draft | `workorder.draft(asset_id, task, recommended_date, parts_list)` | Maintenance recommendation | HITL: supervisor approves WO |
| MTBF trend analysis | `kpi.trend(mtbf, asset_id, rolling_window)` | Downtime event log | None — read-only |
| Planned vs. unplanned maintenance ratio | `kpi.compute(planned_ratio, period)` | Maintenance event log | None — read-only |
| Parts inventory check for recommended maintenance | `inventory.check(parts_list)` | Inventory store (InventoryManager integration) | None — read-only |

**Textile-specific failure modes:** Spindle bearing degradation (vibration signature 3-6 weeks before failure); traveller/ring wear (current spike pattern); heddle fatigue (warp stop frequency increase); warp beam brake wear; dye machine pump bearing; stenter chain lubrication state.

**Datasets used in PoC:** NASA C-MAPSS turbofan dataset for RUL methodology validation; adapted degradation curves applied to textile asset profiles.

---

#### RCASpecialist

**Purpose:** Structured root cause analysis for failures and quality escapes; prevent recurrence.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Automated 5-Why chain generation | `rca.five_why(failure_event_id, sensor_context)` | Fault event, sensor readings, maintenance history | HITL: RCA report reviewed and approved by supervisor before action |
| Fishbone / Ishikawa diagram generation | `rca.fishbone(failure_event_id)` | Failure context, causal categories | HITL: engineering review before corrective action |
| Fault-symptom pattern matching | `rca.match(symptom_pattern, knowledge_graph)` | Historical failure cases, RCA knowledge graph | None — advisory |
| Corrective action recommendation | `action.recommend(rca_result)` | RCA output, SOP library | HITL: supervisor approves corrective actions |
| Recurrence check (has this fault pattern occurred before?) | `history.search(fault_pattern, lookback_days)` | Historical fault log, RCA records | None — read-only |
| RCA report generation | `report.generate(rca_id, template)` | All RCA data | HITL: manager approves before filing |
| FMEA cross-reference | `fmea.lookup(failure_mode, asset_class)` | FMEA knowledge base | None — read-only |

---

#### MaintenanceCoach

**Purpose:** Step-by-step procedure guidance for maintenance technicians during repairs; reduce MTTR by surfacing the right SOP instantly.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Procedure retrieval (natural language query) | `rag.retrieve(query, asset_class, fault_code)` | SOP vector store, maintenance manuals | None — advisory |
| Step-by-step repair guidance | `procedure.steps(procedure_id, current_step)` | Procedure store | None — advisory |
| Spare parts lookup for current repair | `inventory.lookup(asset_id, procedure_id)` | Inventory store, BOM | None — read-only |
| Lockout/tagout (LOTO) procedure retrieval | `loto.get(asset_id)` | Safety procedure store | None — advisory; HITL on any physical isolation confirmation |
| Repair time logging | `time.log(workorder_id, technician_id, duration)` | Work order | HITL: technician confirms completion |
| MTTR contribution logging | `kpi.update(mttr, asset_id, repair_event)` | Repair time log | None — automated |
| Escalation to expert | `escalation.create(workorder_id, reason)` | Work order, technician capability profile | HITL: technician confirms escalation |

---

#### DowntimeAnalyzer

**Purpose:** Structured analysis of downtime events; compute Pareto of causes; feed insights to PredictiveMaintenance and ProductionPlanner.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Downtime Pareto analysis | `downtime.pareto(asset_group, period, cause_taxonomy)` | Downtime event log | None — read-only |
| OEE decomposition (Availability / Performance / Quality waterfall) | `oee.decompose(asset_id, period)` | OEE component data | None — read-only |
| Downtime cost estimation | `cost.estimate(downtime_hours, asset_id, production_value)` | Downtime log, production value parameters | None — read-only |
| Chronic vs. sporadic downtime classification | `downtime.classify(event_id)` | Downtime history | None — read-only |
| Trend alerting (downtime increasing on asset) | `trend.alert(asset_id, metric=downtime, threshold)` | Rolling downtime trend | Alert to maintenance supervisor; HITL if action required |
| Improvement recommendation | `improvement.recommend(pareto_result)` | Pareto analysis, SOP library | HITL: production manager reviews recommendations |
| Shift-level downtime report | `report.shift_downtime(shift_id)` | Downtime events in shift window | None — read-only |

---

### Cluster 3 — Knowledge & Training

#### KnowledgeCurator

**Purpose:** Maintain the quality and freshness of the knowledge base; ingest new documents; detect outdated content; track knowledge reuse.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Document ingestion pipeline | `ingest.process(document, metadata)` | New SOPs, manuals, maintenance reports | HITL: knowledge manager approves before indexing |
| Duplicate / conflict detection | `kb.check_conflict(new_doc, existing_chunks)` | Vector store | HITL: curator resolves conflicts before indexing |
| Outdated content flagging | `kb.flag_stale(doc_id, last_reviewed, threshold_days)` | Document metadata | Advisory; knowledge manager notified |
| Knowledge reuse rate tracking | `kpi.compute(knowledge_reuse_rate, period)` | Query log: resolved_from_kb vs. escalated | None — read-only |
| Tag and metadata management | `kb.tag(doc_id, tags, asset_class, process_area)` | Document catalog | HITL: curator confirms tags |
| Retrieval quality feedback loop | `feedback.record(query_id, retrieved_chunks, verdict)` | Operator feedback on retrieval quality | HITL: curator reviews low-quality feedback |

---

#### TrainingCoach

**Purpose:** On-the-job coaching for operators; adaptive training delivery; competency tracking.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Training module assignment | `training.assign(operator_id, skill_gap_profile)` | Competency matrix, skills assessment | HITL: supervisor approves assignment |
| Contextual step-by-step coaching | `training.coach(operator_id, current_task, skill_level)` | SOP, operator profile, skill level | None — advisory |
| Competency assessment (quiz / task observation log) | `competency.assess(operator_id, module_id, results)` | Quiz results, observation log | HITL: supervisor reviews and confirms competency sign-off |
| Training completion rate KPI | `kpi.compute(training_completion, period)` | Assignment log, completion events | None — read-only |
| Knowledge gap detection from query patterns | `gap.detect(operator_id, query_history)` | Query log, competency matrix | Advisory; coach notified |
| Personalized SOP recommendation | `rag.retrieve(operator_query, operator_role, skill_level)` | SOP vector store, operator profile | None — advisory |

---

#### ShiftHandover

**Purpose:** Auto-generate structured shift handover reports; ensure no critical information is lost between shifts.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Auto-compile shift summary | `handover.compile(shift_id)` | Event log: alerts, completions, open WOs, quality events, equipment status | None — auto-generated draft |
| Priority ranking of open items | `handover.prioritize(open_items)` | Severity, asset criticality, time-sensitivity | None — automated ranking |
| Outgoing supervisor review | `handover.review(shift_id, supervisor_id)` | Draft report | HITL: outgoing supervisor reviews and signs off |
| Incoming supervisor acknowledgment | `handover.acknowledge(shift_id, incoming_supervisor_id)` | Final report | HITL: incoming supervisor acknowledges receipt |
| Handover report archival | `handover.archive(shift_id)` | Signed-off report | None — automated |
| Anomaly / alert continuity tracking (carries open alerts across shifts) | `alert.carry_over(shift_id_from, shift_id_to)` | Open alert list | None — automated |
| Equipment status snapshot | `status.snapshot(asset_group, timestamp)` | Telemetry, maintenance status | None — read-only |

**Target:** Reduce handover time from 15-30 minutes to under 3 minutes. Auto-populate 5 of 7 report sections; only the "supervisor notes" and "priority items" fields require manual input.

---

#### DocumentationSynthesizer

**Purpose:** Transform raw technical documents (maintenance logs, incident reports, field notes) into structured, searchable knowledge assets.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Unstructured document parsing and chunking | `doc.parse(raw_document, format)` | Raw PDFs, Word docs, handwritten scans (simulated) | None — automated |
| Structured summary generation | `doc.summarize(parsed_chunks, target_format)` | Parsed document | HITL: knowledge manager reviews before publishing |
| Cross-document synthesis (merge multiple sources on same topic) | `doc.synthesize(doc_ids, topic)` | Multiple parsed documents | HITL: curator approves merged output |
| SOP gap detection ("no procedure exists for this failure mode") | `sop.gap_detect(failure_mode, sop_store)` | Failure event, SOP vector store | Advisory; KnowledgeCurator notified |
| Bilingual (IT/EN) output generation | `doc.translate(content, target_lang)` | Synthesized content | HITL: reviewer approves translation before publication |
| Changelog and version tracking | `doc.version(doc_id, change_summary)` | Document history | None — automated |

---

### Cluster 4 — Supply Chain & Economics

#### InventoryManager

**Purpose:** Real-time inventory visibility; reorder point alerting; spare parts management for maintenance.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Stock level monitoring with reorder alerts | `inventory.check(sku_id, reorder_point)` | Inventory store | Alert to procurement; HITL: supervisor approves reorder action |
| Purchase recommendation (draft, not autonomous PO) | `purchase.recommend(sku_id, quantity, supplier_id)` | Inventory levels, lead times, safety stock | HITL: procurement supervisor approves before any order |
| BOM linkage (which parts are needed per asset/procedure) | `bom.lookup(asset_id, procedure_id)` | BOM store, maintenance procedures | None — read-only |
| Inventory turnover KPI | `kpi.compute(inventory_turnover, period)` | Inventory transaction log | None — read-only |
| Dye lot inventory tracking | `inventory.dye_lot(lot_id, remaining_quantity, expiry)` | Dye lot records | Alert if expiry approaching or stock below minimum |
| Spare parts availability for planned maintenance | `inventory.check_maintenance(workorder_id)` | Work order, BOM, inventory | Advisory to PredictiveMaintenance |

---

#### EnergyOptimizer

**Purpose:** Monitor energy consumption per process and machine; identify waste; recommend ISO 50001-aligned efficiency measures.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Energy per unit KPI computation | `kpi.compute(energy_per_unit, asset_group, period)` | Energy meter (simulated), production output | None — read-only |
| Energy baseline and EnPI tracking (ISO 50001) | `energy.baseline(asset_id, period)` | Energy consumption history | None — read-only |
| Peak demand alerting | `energy.peak_alert(current_demand, threshold)` | Real-time energy meter | Alert to operations; no autonomous action |
| Efficiency recommendation (shift high-energy processes to off-peak) | `energy.recommend(schedule, energy_tariff, process_profile)` | Production schedule, energy tariff, process energy profiles | HITL: operations manager reviews recommendation |
| Wet processing energy focus (dyeing/finishing = 60% of consumption) | `energy.wet_process_report(period)` | Dyeing/finishing energy data | None — read-only |
| Carbon footprint estimation | `carbon.estimate(energy_kwh, emission_factor)` | Energy consumption, grid emission factor | None — read-only |

---

#### CostAnalyzer

**Purpose:** Economic impact analysis; connect operational KPIs to financial outcomes; feed ROI and TCO dashboards.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Downtime cost computation | `cost.downtime(asset_id, downtime_hours, hourly_production_value)` | Downtime log, production value parameters | None — read-only |
| Scrap cost computation | `cost.scrap(lot_id, scrap_units, material_cost_per_unit)` | Scrap log, material cost | None — read-only |
| Energy cost per period | `cost.energy(period, kwh_consumed, energy_tariff)` | Energy consumption, tariff | None — read-only |
| ROI dashboard data aggregation | `roi.aggregate(period)` | Downtime cost, scrap cost, energy cost, KPI deltas vs. baseline | None — read-only |
| TCO 3-year model | `tco.compute(infra_cost, integration_labor, operational_fte, years=3)` | Cost parameters (configurable) | None — read-only; parameterizable |
| OEPV ribasso simulator | `oepv.simulate(base_d_asta, ribasso_pct, formula_type, tech_score)` | OEPV parameters | None — read-only |
| Value driver decomposition | `roi.decompose(period)` | ROI components: downtime, quality, energy, training, knowledge reuse | None — read-only |

---

#### DemandForecaster

**Purpose:** Forecast fabric/yarn demand with textile-specific seasonality; feed ProductionPlanner with demand signal.

| Capability | Tools Called | Data Read | HITL Gate |
|------------|-------------|-----------|-----------|
| Time-series demand forecasting | `forecast.generate(sku_group, horizon_weeks)` | Historical demand data, seasonal calendar | Advisory output to ProductionPlanner |
| Seasonal decomposition (fashion collection cycles) | `forecast.decompose(demand_series)` | Historical demand, collection launch calendar | None — read-only |
| Forecast accuracy KPI | `kpi.compute(forecast_accuracy, period)` | Forecast vs. actual | None — read-only |
| Safety stock recommendation | `inventory.safety_stock(sku_id, demand_variance, lead_time)` | Forecast, lead time data | Advisory to InventoryManager |
| Demand plan publication to ProductionPlanner | `demand_plan.publish(forecast_id, horizon)` | Forecast output | HITL: demand planner reviews and approves before publishing |
| Scenario analysis (what-if on demand up/down 20%) | `forecast.scenario(baseline_forecast, delta_pct)` | Baseline forecast | None — read-only |

---

## HITL / Governance Feature Specification

These are table stakes — they apply platform-wide, not per-agent.

### Escalation Tier Model

```
Tier 0 — Automated (no human required)
  Conditions: confidence >95%, action is reversible, blast radius is low
  Examples: generating draft reports, read-only queries, alert routing
  Logging: all automated actions still logged to audit trail

Tier 1 — Operator HITL (frontline worker approves)
  Conditions: action affects their machine, reversible within shift
  Examples: acknowledging an alert, logging a downtime cause code
  Timeout: if not acknowledged in N minutes, escalates to Tier 2

Tier 2 — Supervisor HITL (shift supervisor or department head approves)
  Conditions: affects production schedule, work order issuance, shift handover sign-off
  Timeout: if not acknowledged in M minutes, escalates to Tier 3 or blocks

Tier 3 — Manager HITL (production/quality/maintenance manager approves)
  Conditions: NCR filing, corrective action plans, purchase recommendations above threshold
  No timeout — blocks until resolved

Tier 4 — Safety INTERLOCK (agent cannot proceed regardless of who approves)
  Conditions: any action that would write PLC setpoints, modify safety parameters
  Resolution: action is rejected by the platform; must go through certified HMI path
```

### HITL Implementation Requirements (LangGraph)

- Every HITL gate uses `interrupt()` with a structured payload containing: `agent_id`, `action_type`, `proposed_action`, `rationale`, `confidence_score`, `affected_asset_id`, `tier`
- State is persisted via `AsyncPostgresSaver` so the graph can survive server restarts during long approvals
- Resume uses `Command(resume=decision)` where `decision` is one of: `approve`, `reject`, `edit` (with modified parameters), `escalate`
- Timeout handling: unanswered Tier 1 interrupts fire a new interrupt to Tier 2 after configurable N minutes; Tier 3 never times out
- All approved/rejected/edited actions are written to the immutable audit log with: `reviewer_id`, `decision`, `timestamp`, `original_proposal`, `edited_proposal` (if edited), `rationale` (free text, required for rejections)

### Confidence Threshold Policy

| Score | Label | Action |
|-------|-------|--------|
| >95% | High confidence | Auto-process at Tier 0; notify human |
| 70-95% | Medium confidence | HITL at appropriate tier |
| <70% | Low confidence | Mandatory human review; agent flags uncertainty explicitly |
| Any | Safety-relevant | Always HITL regardless of score (Tier 3+) |

---

## Feature Dependencies

```
[HITL Policy Layer]
    └──required by──> All 16 agents (every agent action routes through policy)
    └──required by──> Audit Trail

[Audit Trail]
    └──required by──> OEPV compliance argument
    └──required by──> Explainability requirement

[Sensor Ingestion / Event Bus]
    └──required by──> AnomalyDetector
    └──required by──> PredictiveMaintenance
    └──required by──> QualityInspector
    └──required by──> EnergyOptimizer
    └──required by──> DowntimeAnalyzer
    └──required by──> OEE dashboard

[Downtime Event Log]
    └──required by──> DowntimeAnalyzer
    └──required by──> PredictiveMaintenance (MTBF)
    └──required by──> OEE Availability component
    └──required by──> RCASpecialist
    └──required by──> CostAnalyzer (downtime cost)

[RAG / Vector Store]
    └──required by──> OperatorAssistant
    └──required by──> MaintenanceCoach
    └──required by──> TrainingCoach
    └──required by──> RCASpecialist (historical cases)
    └──required by──> DocumentationSynthesizer (gap detection)
    └──required by──> KnowledgeCurator (conflict detection)

[Inventory Store]
    └──required by──> InventoryManager
    └──required by──> PredictiveMaintenance (parts availability)
    └──required by──> MaintenanceCoach (spare parts lookup)
    └──required by──> CostAnalyzer

[ProductionPlanner output]
    └──required by──> EnergyOptimizer (schedule-to-energy mapping)
    └──required by──> InventoryManager (demand-driven safety stock)

[DemandForecaster output]
    └──required by──> ProductionPlanner (demand-driven scheduling)
    └──required by──> InventoryManager (safety stock sizing)

[QualityInspector]
    └──feeds──> RCASpecialist (quality escape triggers RCA)
    └──feeds──> DowntimeAnalyzer (quality-related stops)

[RCASpecialist]
    └──feeds──> KnowledgeCurator (RCA reports → knowledge base)
    └──feeds──> PredictiveMaintenance (recurring causes inform RUL model)

[CostAnalyzer]
    └──requires──> DowntimeAnalyzer (downtime hours)
    └──requires──> QualityInspector (scrap rate)
    └──requires──> EnergyOptimizer (energy consumption)
    └──produces──> ROI Dashboard, TCO model, OEPV simulator
```

### Dependency Notes

- **HITL Policy Layer must exist before any agent ships:** Agents without governance are anti-features
- **Sensor ingestion and downtime log must exist before any monitoring agent:** AnomalyDetector with no real data is a demo widget, not a tool
- **RAG store must be seeded before knowledge agents are useful:** Empty vector store = useless coaching
- **CostAnalyzer depends on all three peer clusters:** It is the last agent to become useful; build it in the final phase

---

## MVP Definition

### Launch With (v1) — Minimum to validate the concept and satisfy OEPV evaluators

- [ ] Sensor ingestion pipeline (mock OPC-UA → NATS → agent subscriptions)
- [ ] AnomalyDetector with confidence-scored alerts — why: core value demo
- [ ] HITL policy layer with Tier 0-3 gates — why: non-negotiable governance
- [ ] Audit trail (immutable log) — why: OEPV evaluators will look for this
- [ ] OEE / MTBF / MTTR dashboard — why: first question from any evaluator
- [ ] RAG over seeded SOPs (at least loom troubleshooting + dye procedures) — why: KnowledgeCurator and OperatorAssistant need content to be useful
- [ ] OperatorAssistant (procedure lookup + alert acknowledgment) — why: highest-value, lowest-risk agent; demonstrates HITL immediately
- [ ] ShiftHandover (auto-compile from event log) — why: high visible ROI, low complexity, impressive in demos
- [ ] Control room dashboard (agent state, KPIs, alert queue, HITL inbox) — why: evaluators need something to look at
- [ ] Downtime event log with cause taxonomy — why: everything else depends on it

### Add After Validation (v1.x)

- [ ] PredictiveMaintenance + RUL estimation — trigger: baseline sensor data available
- [ ] QualityInspector with textile defect taxonomy — trigger: simulated quality events in place
- [ ] ProductionPlanner with schedule generation — trigger: demand data flowing
- [ ] TrainingCoach with competency tracking — trigger: operator profiles defined
- [ ] InventoryManager with reorder alerting — trigger: inventory mock data seeded
- [ ] RCASpecialist with 5-Why chains — trigger: fault history accumulated
- [ ] DowntimeAnalyzer with Pareto — trigger: downtime event log populated
- [ ] EnergyOptimizer — trigger: energy simulation in place

### Future Consideration (v2+)

- [ ] DemandForecaster with fashion seasonality signals — defer: requires historical demand data
- [ ] DocumentationSynthesizer with multilingual output — defer: requires real document corpus
- [ ] CostAnalyzer full ROI/TCO/OEPV simulator — partial v1; full model in v2
- [ ] LoRA fine-tuning of Qwen2.5 on textile vocabulary — defer: requires evaluation dataset
- [ ] Computer vision integration for optical defect detection — explicitly scoped out of v1
- [ ] MaintenanceCoach with LOTO procedure retrieval — defer: safety-critical content needs careful vetting

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| HITL Policy Layer | HIGH | MEDIUM | P1 |
| Audit Trail | HIGH | LOW | P1 |
| Sensor Ingestion / Event Bus | HIGH | MEDIUM | P1 |
| OEE / MTBF / MTTR Dashboard | HIGH | MEDIUM | P1 |
| AnomalyDetector | HIGH | HIGH | P1 |
| Downtime Event Log | HIGH | LOW | P1 |
| RAG / Vector Store seeded | HIGH | MEDIUM | P1 |
| OperatorAssistant | HIGH | MEDIUM | P1 |
| ShiftHandover auto-report | HIGH | MEDIUM | P1 |
| Control Room UI | HIGH | HIGH | P1 |
| PredictiveMaintenance + RUL | HIGH | HIGH | P2 |
| QualityInspector + defect taxonomy | HIGH | HIGH | P2 |
| ProductionPlanner + scheduling | MEDIUM | HIGH | P2 |
| RCASpecialist + 5-Why | HIGH | MEDIUM | P2 |
| DowntimeAnalyzer + Pareto | MEDIUM | LOW | P2 |
| InventoryManager | MEDIUM | MEDIUM | P2 |
| TrainingCoach + competency | MEDIUM | MEDIUM | P2 |
| MaintenanceCoach | HIGH | MEDIUM | P2 |
| EnergyOptimizer + ISO 50001 | MEDIUM | MEDIUM | P2 |
| KnowledgeCurator | MEDIUM | MEDIUM | P2 |
| CostAnalyzer + ROI/TCO | HIGH | MEDIUM | P2 |
| OEPV Ribasso Simulator | HIGH (for evaluators) | LOW | P2 |
| DemandForecaster | MEDIUM | HIGH | P3 |
| DocumentationSynthesizer | MEDIUM | HIGH | P3 |
| CV-based quality inspection | LOW (deferred) | HIGH | P3 |

---

## Competitor Feature Analysis

| Feature | Siemens Opcenter / Mendix | Rockwell FactoryTalk | Tulip | Our Approach |
|---------|--------------------------|----------------------|-------|--------------|
| Real-time anomaly detection | Via add-on analytics module | Via FactoryTalk Analytics | Via AI-powered apps | Built into AnomalyDetector; self-hosted; no add-on license |
| HITL approval gates | Manual workflow configuration | Not native | App-configured | Native via LangGraph `interrupt()`; first-class concept |
| Textile defect taxonomy | Generic; requires customization | Generic | Fully custom | Built-in 4-point grading; dye lot; domain vocabulary in Qdrant |
| RAG over SOPs | Via Siemens Industrial Copilot | Not available | Limited | Full RAG pipeline; hybrid retrieval; bilingual |
| Shift handover | Module purchase | Separate product | App-configurable | Native ShiftHandover agent; auto-compiled from event log |
| On-prem self-hosted | Possible but complex licensing | Possible | Cloud-first | 100% self-hosted; Docker Compose; no license fees |
| Agentic multi-agent orchestration | Not available | Not available | Not available | 16 reference agents; LangGraph state machine; SDK for extension |
| Open source | No | No | No | Full open-source; GitHub; Apache/MIT license |
| OEPV simulator | No | No | No | Built into CostAnalyzer; unique differentiator |
| SDK for custom agents | No | No | No | Python SDK; uniform interface; documented |

---

## Sources

- [IoT-Driven Real-Time Process Monitoring in Textile Manufacturing (EPJ Web of Conferences 2026)](https://www.epj-conferences.org/articles/epjconf/abs/2026/10/epjconf_gcmm2025_04004/epjconf_gcmm2025_04004.html)
- [IIoT for Textile Manufacturing: Looms, Spinning, Dyeing Monitoring (MachineCDN)](https://www.machinecdn.com/blog/iiot-textile-manufacturing/)
- [AI-Driven Anomaly Detection in Textile Manufacturing (Springer 2025)](https://link.springer.com/chapter/10.1007/978-981-95-5136-1_31)
- [Woven Fabric Defect Control Methods in Shuttle Loom (SAGE Journals 2021)](https://journals.sagepub.com/doi/full/10.1177/15589250211014181)
- [Textile Dyeing ERP: Recipe Management, Shade Matching, Effluent Tracking (FlowSense)](https://www.flowsense.solutions/blog/textile-dyeing-processing-erp)
- [Business Central for Textile Manufacturing: Dye Lots, Shrinkage, QC (ERP Software Blog 2026)](https://erpsoftwareblog.com/2026/05/business-central-for-textile-manufacturing-managing-dye-lots-shrinkage-and-quality-control/)
- [Human-in-the-Loop AI in Manufacturing — Tulip](https://tulip.co/blog/human-in-the-loop-ai-explained/)
- [LangGraph Human-in-the-Loop: Interrupts, Approvals, Async Execution](https://www.abstractalgorithms.dev/langgraph-human-in-the-loop)
- [HITL Patterns in LangGraph: Approve, Reject, Edit (Medium)](https://medium.com/the-advanced-school-of-ai/human-in-the-loop-in-langgraph-approve-or-reject-pattern-fcf6ba0c5990)
- [Complete Guide to Agentic AI in Industrial Operations 2025 (XMPRO)](https://xmpro.com/the-complete-guide-to-agentic-ai-in-industrial-operations-how-ai-agents-are-transforming-manufacturing-mining-and-asset-intensive-industries-in-2025/)
- [Fully Autonomous AI Agents Should Not Be Developed (arXiv 2025)](https://arxiv.org/html/2502.02649v3)
- [AI Root Cause Analysis in Manufacturing with Causal Bayesian Networks and Knowledge Graphs (arXiv)](https://arxiv.org/html/2402.00043)
- [FMEA for Root Cause Analysis in Manufacturing with AI (DataGrid)](https://datagrid.com/blog/fmea-root-cause-analysis-manufacturing)
- [Digital Shift Handover in Manufacturing — Best Practices (OxMaint)](https://oxmaint.com/industries/manufacturing-plant/digital-shift-handover-manufacturing-process-template)
- [AI-Driven Shift Logs and Handovers (DimensionSoft)](https://dimensionsoft.com/shift-handover/)
- [Predictive Maintenance with IoT and AIoT (PMC/MDPI Sensors 2025)](https://pmc.ncbi.nlm.nih.gov/articles/PMC12737171/)
- [MTBF, MTTR, OEE Maintenance KPIs Complete Guide 2026 (OxMaint)](https://oxmaint.com/article/mtbf-mttr-oee-maintenance-kpis)
- [ISO 50001 Energy Management for Textile Manufacturing (Textile School)](https://www.textileschool.com/29259/energy-efficient-textile-production-strategies-for-a-greener-industry/)
- [2025 MES Vendor Comparison Guide — Composable MES (Tulip)](https://tulip.co/blog/2025-mes-vendor-comparison-guide/)
- [Agentic AI in Manufacturing (Deloitte 2025)](https://www.deloitte.com/us/en/services/consulting/blogs/business-operations-room/agentic-ai-in-manufacturing.html)
- [How Agentic RAG Transforms Risk Management for Industrial Companies (Modgility)](https://www.modgility.com/blog/how-an-agentic-rag-system-transforms-risk-management-for-industrial-companies)
- [OEPV: Formule per simulazione offerta economicamente più vantaggiosa](https://www.vincenzogliottone.it/formule-per-simulazione-offerta-economicamente-piu-vantaggiosa/)

---

*Feature research for: Smart Factory Transformation — textile manufacturing agentic platform*
*Researched: 2026-05-16*
