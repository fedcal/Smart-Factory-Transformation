# Phase 1: Foundation & Monorepo - Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Stabilire la base operativa del progetto: workspace Nx polyglot Python+Angular con `@nxlv/python`+uv, stack di servizi dev orchestrato via Docker Compose (Postgres+TimescaleDB, Qdrant, NATS JetStream, Ollama, Langfuse), pipeline CI/CD su GitHub Actions con `nx affected`, license scanner SBOM-based che blocca licenze incompatibili, pre-commit hooks per Python e TypeScript, skeleton Helm chart deployabile su k8s locale e produzione-ready per evoluzione successiva.

Coprire i requirement PLAT-01..PLAT-10 e OBS-01 (Langfuse self-hosted come servizio dev).

Tutto ciò che è dominio (textile), agentico (LangGraph, agenti), simulazione OPC-UA, RAG, frontend funzionale, observability runtime, evaluation: fuori scope — sono fasi successive.

</domain>

<decisions>
## Implementation Decisions

### Monorepo Layout & Naming

- **D-01:** Mantenere 6 root-folder come da PLAT-03: `apps/`, `packages/`, `services/`, `docs/`, `infra/`, `simulators/`. Scelta motivata da leggibilità per evaluators e dal valore self-documentante del repo (vs. convenzione idiomatica `apps/`+`libs/`).
- **D-02:** SDK in `packages/sft-agents/` (core: interfacce Agent/Tool/Memory/Policy, runtime LangGraph adapter, contracts) **e** dominio tessile in `packages/sft-domain/` (defect taxonomy, asset registry models, glossario IT/EN). Lo split permette di evolvere l'SDK in altri verticali senza accoppiamento al tessile.
- **D-03:** I 16 agenti sono **app deployabili** sotto `apps/agents/{ops,maintenance,knowledge,supply}/{agent-name}/` (es. `apps/agents/ops/operator-assistant/`). Il supervisor li compone via RPC/NATS — non via import diretto. Scelta esplicita per scale orizzontale per cluster e isolamento failure, anche se sovradimensionata per PoC single-node iniziale. Implica che CORE-02 (supervisor LangGraph) chiami i cluster come servizi remoti, non come subgraph in-process. **Conseguenza importante per Fase 4** — il supervisor avrà bisogno di un transport NATS-based per dispatch ai cluster.
- **D-04:** Pacchetto `packages/sft-contracts/` come **single source of truth** Pydantic↔TypeScript. I modelli Pydantic vivono lì; un build target Nx genera OpenAPI JSON e i tipi TS in `dist/ts/`. Sia FastAPI (apps/api-gateway) sia Angular (apps/factory-ui) dipendono da questo pacchetto. SRV-05 contract test è enforced qui.
- **D-05:** Naming progetti Nx: **kebab-case con prefisso area**. Schema:
  - `sft-*` per packages cross-cutting (`sft-agents`, `sft-domain`, `sft-contracts`)
  - `ops-*` / `mnt-*` / `trn-*` / `scm-*` per gli agenti dei 4 cluster (es. `ops-operator-assistant`, `mnt-predictive-maintenance`)
  - `ui-*` per Angular (`ui-factory`, `ui-control-room` se separate)
  - `svc-*` per microservizi (`svc-ot-bridge`, `svc-api-gateway`)
  - `sim-*` per simulatori (`sim-textile`, `sim-cmapss-replay`)
  - `infra-*` per asset infrastrutturali Nx-managed se servono target Nx custom
- **D-06:** L'orchestratore supervisor è un'app a sé: `apps/orchestrator/` (Python+LangGraph), nome Nx `svc-orchestrator`.

### Docker Compose Dev Stack

- **D-07:** Split per area: `infra/compose/core.yml` (Postgres+TimescaleDB, Redis), `infra/compose/llm.yml` (variant: `llm-gpu.yml` / `llm-cpu.yml` per Ollama), `infra/compose/obs.yml` (Langfuse v3 stack: Postgres dedicato, ClickHouse, MinIO, Redis Langfuse), `infra/compose/sim.yml` (NATS JetStream, OPC-UA server simulato — popolato in Fase 3 ma container già qui per `make up` completo). Qdrant nel `core.yml` (è infrastruttura di base, non OT/sim).
- **D-08:** Due overlay LLM mutualmente esclusivi: `llm-gpu.yml` (Ollama con `deploy.resources.reservations.devices` NVIDIA) e `llm-cpu.yml` (Ollama CPU-only, profilo onboarding senza GPU). `make up` di default include `llm-cpu.yml` (funziona ovunque); `make up-gpu` sostituisce con `llm-gpu.yml`. README documenta esplicitamente quando upgradare.
- **D-09:** Persistenza dati dev via **named volumes Docker** (non bind mount): `pg-data`, `qdrant-data`, `nats-data`, `langfuse-pg-data`, `langfuse-clickhouse-data`, `langfuse-minio-data`, `ollama-models`. `make reset` = `docker compose down -v && make up`. Niente UID-mismatch su Linux, portabile su macOS/Windows.
- **D-10:** Healthchecks nativi Docker Compose per ogni servizio (`pg_isready`, Qdrant `/healthz`, NATS `/healthz`, Langfuse `/api/public/health`, Ollama `/api/tags`). Servizi dipendenti dichiarano `depends_on: condition: service_healthy`. Il comando `make up` esce solo a stack healthy — success criterion #1 soddisfatto end-to-end.
- **D-11:** `infra/compose/` contiene anche `.env.example` documentato con tutte le variabili (porte, password dev, modello Ollama default `qwen2.5:7b-instruct-q4_K_M`).

### License Scanner

- **D-12:** Scanner unificato SBOM-based: **Syft** (generazione SBOM CycloneDX) + **Grype** o **Trivy** per policy enforcement. Una sola pipeline copre deps Python+JS **e immagini container** dei servizi runtime. Pi soddisfa il claim moderno di supply-chain awareness e parla la lingua giusta agli evaluators.
- **D-13:** Policy = **allowlist esplicita** + override controllato. Allowlist iniziale: `MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MPL-2.0, PSF-2.0, Unlicense, CC0-1.0, Python-2.0`. Tutto ciò che è fuori dall'allowlist viene bloccato in CI **a meno che** appaia in `LICENSE-EXCEPTIONS.md` versionato (formato: package, versione, licenza, motivazione, data approvazione, approver). Audit trail esplicito.
- **D-14:** Scope scanner = **intero runtime**, immagini container incluse. MinIO (dipendenza di Langfuse v3) è AGPL-3.0 e entra immediatamente in `LICENSE-EXCEPTIONS.md` con nota: *"AGPL applica solo se modifichiamo MinIO. Lo usiamo as-is via container Docker upstream e distribuiamo Helm chart con default upstream. Compatibile con deploy on-prem single-tenant (no SaaS hosting → no public network service trigger)."* Trasparenza massima per evaluators.
- **D-15:** CI integration = **workflow GitHub Actions dedicato `license-scan.yml`**, eseguito su ogni PR. Required status check su branch protection di `main`. SBOM artefatto persistito 90 giorni. Output: report Markdown commentato sulla PR con diff licenze rispetto a base branch. Success criterion #3 verificato da un test CI che apre una PR fittizia con dipendenza GPL e verifica il block.

### Helm Chart Skeleton

- **D-16:** Architettura chart = **chart separati per servizio nostro** in `infra/helm/charts/{api-gateway,ot-bridge,orchestrator,agents-ops,agents-mnt,agents-trn,agents-scm,factory-ui}/` + **umbrella meta-chart** `infra/helm/sft-stack/Chart.yaml` che li include come dependencies insieme ai chart upstream (Bitnami `postgresql`, `qdrant/qdrant`, `langfuse/langfuse`, `nats-io/nats`). Permette deploy parziali (es. solo agenti senza UI) e versioning indipendente.
- **D-17:** "Skeleton" = **production-ready dal Fase 1**: ogni chart include `HorizontalPodAutoscaler`, `PodDisruptionBudget`, `NetworkPolicy`, `Ingress`, resource requests/limits, ServiceAccount + RBAC minimo, `PodSecurityContext` con `runAsNonRoot: true`. Scelta esplicita per anticipare lavoro che altrimenti pesa Fase 11; rischio over-engineering accettato. **Nota:** template completi ma `values.yaml` minimi e ben commentati — chi installa può andare in produzione con default sensati.
- **D-18:** **NetworkPolicy data-diode OT** già implementato in `svc-ot-bridge` chart: policy `egress` verso NATS consentito, policy che blocca ogni ingress dal layer agenti verso `sim-textile` (OPC-UA server). Permette di affermare già in Fase 1 che il principio architetturale **OT Bridge unidirezionale** è enforced via k8s, non solo via codice. Anticipo di SEC-06.
- **D-19:** Secret management = **SealedSecrets (Bitnami)**. Secrets cifrati con chiave del cluster e committati nel repo come SealedSecret CRD. Coerente con il modello target single-tenant on-prem. ESO/Vault rinviati a v2 quando emergeranno scenari multi-cluster.
- **D-20:** Ingress controller default = **ingress-nginx** (chart `kubernetes/ingress-nginx` come dep opzionale del meta-chart, attivabile via `values: ingress.enabled=true`). Smoke test CI: workflow `helm-smoke-test.yml` avvia un cluster **k3d** in GitHub Actions, esegue `helm dependency update`, `helm install --dry-run`, `helm install`, `kubectl wait --for=condition=ready --all`, `helm test` (test-hook con HTTP probe sui Service interni). Required check.

### Claude's Discretion

Aree dove l'utente non ha richiesto discussione esplicita — vado con default sensati ben documentati nel PLAN:

- **uv workspace strategy**: single root `pyproject.toml` con `[tool.uv.workspace]` che dichiara members `packages/*` + `apps/agents/*/*` + `apps/orchestrator` + `apps/api-gateway` + `services/*` + `simulators/*`. Lockfile unico `uv.lock` a root. Dev/test/prod splittati via `[tool.uv.sources]` + `[dependency-groups]`. Cache uv in CI tramite `actions/cache` su `~/.cache/uv`.
- **Task runner**: **Makefile** (vincolo PLAT-09 già menziona Makefile/Just; Make è universale e già conoscibile a tutti, Just rimane non standard). Comandi standard: `make up`, `make up-gpu`, `make down`, `make reset`, `make test`, `make lint`, `make format`, `make docs`, `make demo`, `make sbom`, `make helm-test`.
- **Versioning & release**: **Changesets** (`@changesets/cli`) — best fit per monorepo polyglot con SDK pubblicabile, ottimo workflow community-friendly per OSS. Per pacchetti Python pubblicabili su PyPI lo step Changesets emette `__version__.py` + tag + GH Release; pubblicazione effettiva su PyPI rinviata oltre v1.
- **Nx Cloud**: **disabilitato per default**, ma `nx.json` configurato per essere abilitato via env (`NX_CLOUD_ACCESS_TOKEN`). Cache solo locale + cache GitHub Actions (`actions/cache` con chiave Nx hash). Decisione rivedibile se i tempi CI vanno oltre 10 min.
- **Pre-commit framework**: **`pre-commit`** (Python tool standard) con `.pre-commit-config.yaml` versionato. Hook: `ruff format`, `ruff check`, `mypy --strict` (solo su `packages/sft-*`), `eslint`, `prettier`, `commitlint` (Conventional Commits), `gitleaks` (secret scanning). Eseguito anche in CI come job `pre-commit-check.yml` (success criterion #4).
- **GitHub Actions structure**: workflows separati per concern:
  - `ci.yml` — nx affected build/test/lint con `nrwl/nx-set-shas@v4`
  - `pre-commit-check.yml` — required check
  - `license-scan.yml` — required check (D-15)
  - `helm-smoke-test.yml` — required check (D-20)
  - `docs-deploy.yml` — deploy MkDocs su `gh-pages` (preparato in Fase 1 ma effettivo da Fase 2 quando docs/ è popolato)
- **Python toolchain**: Python 3.12 fissato; nessun matrix multi-versione in CI per ridurre tempo e perché lo stack runtime è 3.12 only.
- **Docs scaffolding** in Fase 1: solo struttura MkDocs Material vuota + i18n plugin + GitHub Pages deploy workflow funzionante (con placeholder pages). Contenuto sostanziale arriva da Fase 2 in poi.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project planning
- `.planning/PROJECT.md` — vision, constraints, key decisions a livello progetto
- `.planning/REQUIREMENTS.md` §Platform & Monorepo (PLAT-01..PLAT-10) — requirement v1 di Fase 1
- `.planning/REQUIREMENTS.md` §Observability & Evaluation (OBS-01) — Langfuse self-hosted come dev service
- `.planning/ROADMAP.md` §Phase 1 — goal, depends-on, success criteria, requirement mapping
- `CLAUDE.md` §Technology Stack — stack lockato, alternative scartate, version compatibility

### Project research (deep-dive 2026-05-16)
- `.planning/research/SUMMARY.md` — executive summary, key findings, rischi project-critical
- `.planning/research/STACK.md` — versioni esatte, rationale per ciascuna scelta, alternative considerate
- `.planning/research/ARCHITECTURE.md` — pattern HITL load-bearing, dipendenze tra layer
- `.planning/research/PITFALLS.md` — simulator fidelity gap, OEPV accuracy, anti-pattern noti
- `.planning/research/FEATURES.md` — dependency graph delle feature

### Tool & framework upstream docs (consultare durante research fase)
- Nx 20.x + `@nxlv/python` 21.x — convenzioni progetti, `nx affected`, dep-graph polyglot
- uv 0.6+ workspace docs — single lockfile, `[tool.uv.workspace]`
- Docker Compose v2 — profiles, healthcheck, depends_on conditions
- Helm 3 — chart dependencies, subcharts, test hooks
- Syft + Grype upstream — policy file format, SBOM-based scan
- SealedSecrets (Bitnami) — sealed-secrets-controller, kubeseal CLI
- ingress-nginx — values, controller chart
- k3d — config file format per CI, registry support

### Standard di processo
- `LICENSE` (Apache 2.0) del progetto — vincolo per allowlist
- Conventional Commits 1.0 — per Changesets + commitlint

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

Il repository è allo stato iniziale: nessun codice applicativo esistente. Asset disponibili:
- `.planning/research/*.md` — knowledge base curata da consultare a tutte le fasi di research/planning
- `CLAUDE.md` — guida operativa Claude Code per il progetto
- Niente codice da riusare ancora; Fase 1 stabilisce le fondamenta che gli step successivi riuseranno

### Established Patterns

Nessun pattern di codice consolidato. Pattern documentali e di workflow consolidati:
- Workflow GSD per fase: discuss → research → plan → execute → verify
- Bilingue IT/EN come default per qualunque artefatto user-facing
- HITL come load-bearing wall (anche se non applica direttamente a Fase 1, le scelte di layout devono permetterlo: vedi D-03, D-04)
- Single-tenant on-premise come modello target — guida scelte secret management, deploy, licenze

### Integration Points

Fase 1 non integra con codice preesistente, ma stabilisce i punti di integrazione per le fasi successive:
- `packages/sft-agents/` esporta interfacce che Fase 4 (Core Agentic Runtime) implementa
- `packages/sft-contracts/` esporta tipi che Fase 4, 6-10 importano (agenti + FastAPI + Angular)
- `infra/compose/sim.yml` predispone NATS che Fase 3 popola con eventi OPC-UA simulati
- `infra/helm/charts/` skeleton che ogni fase successiva estende quando aggiunge un servizio deployabile
- Workflow CI (`ci.yml`, `license-scan.yml`, `pre-commit-check.yml`, `helm-smoke-test.yml`) come fondamenta che future PR estendono con job per eval (DeepEval — Fase 11) e brand-scrub (Fase 12)

</code_context>

<specifics>
## Specific Ideas

- **"Production-ready dal Fase 1"** è scelta esplicita dell'utente per HPA, PDB, NetworkPolicy, Ingress nei chart Helm. Il planner non deve sotto-dimensionare lo skeleton "perché tanto basta che parta". Conseguenza: i task Helm di Fase 1 sono materiali, non placeholder.
- **NetworkPolicy data-diode già in Fase 1** (D-18): anticipo controllato di SEC-06. Il test di SEC-06 in Fase 11 si limita a verificare che la policy esista e funzioni — la policy esiste già.
- **MinIO AGPL trattato a viso aperto** in `LICENSE-EXCEPTIONS.md` con motivazione scritta — non aggirato cambiando tecnologia. Questo è un'argomentazione difendibile davanti agli evaluators che vale di più di una soluzione "pulita ma fragile" (es. swap a Garage/SeaweedFS con drift rischioso da Langfuse upstream).
- **Agenti come app deployabili** (D-03) anziché come libreria condivisa: deliberata anche se sovradimensionata per PoC. Riflette il valore di lungo periodo (scale per cluster, isolamento) e si aggancia esplicitamente al pattern supervisor + cluster subgraphs di LangGraph quando i cluster sono raggiunti via RPC/NATS.

</specifics>

<deferred>
## Deferred Ideas

- **External Secrets Operator + Vault** (alternativa a SealedSecrets): valutare in v2 se emergeranno scenari multi-cluster o deploy cloud-managed. Per ora SealedSecrets copre il caso single-tenant on-prem.
- **Cloud Ingress overlays** (AWS App Gateway, Azure App Gateway): se in futuro serve deploy cloud, aggiungere `values/aws.yaml` e `values/azure.yaml`. Non in v1.
- **Nx Cloud paid tier**: rivedere se i tempi CI superano 10 min con 16 agenti attivi (probabile da Fase 6 in poi).
- **Garage / SeaweedFS** come S3-compatible licenza-friendly alternativi a MinIO: non in v1 a meno che evaluators contestino l'eccezione AGPL.
- **PyPI publish automatico per `sft-agents`**: il workflow Changesets prepara version/tag/GitHub Release già in v1, ma pubblicazione effettiva su PyPI è rinviata fino a quando l'SDK ha una superficie API stabile (probabilmente dopo Fase 4 quando le interfacce sono testate da 16 agenti reali).
- **Multi-version Python matrix in CI** (3.12 + 3.13): non in v1; stack runtime è 3.12 only.
- **Just (justfile)** al posto di Make: rivalutabile se l'ergonomia di Make diventa un problema reale, ma non in v1.

</deferred>

---

*Phase: 1-Foundation & Monorepo*
*Context gathered: 2026-05-16*
