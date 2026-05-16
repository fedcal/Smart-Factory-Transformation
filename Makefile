# Smart Factory Transformation — Makefile
# Decisioni: D-09 (named volumes, reset semantics), D-10 (healthchecks via --wait)
# Claude's Discretion: Make scelto su Just per universalità (PLAT-09)

MAKEFLAGS += --no-print-directory

COMPOSE_CORE     := infra/compose/core.yml
COMPOSE_OBS      := infra/compose/obs.yml
COMPOSE_SIM      := infra/compose/sim.yml
COMPOSE_LLM_CPU  := infra/compose/llm-cpu.yml
COMPOSE_LLM_GPU  := infra/compose/llm-gpu.yml

# Stack base (core + sim + obs) usato da tutti i target tranne up-gpu
BASE_STACK := -f $(COMPOSE_CORE) -f $(COMPOSE_SIM) -f $(COMPOSE_OBS)

.PHONY: up up-gpu up-core down reset test lint format docs demo sbom license-scan helm-test ps logs

## Stack lifecycle
# -----------------------------------------------------------------------

# Avvia tutto lo stack dev (CPU mode — funziona ovunque)
# Prima esecuzione: ~60-180s per pull immagini; successive: ~30s con volumi caldi
up:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) up -d --wait

# Avvia tutto lo stack dev con Ollama su GPU NVIDIA
# Prerequisito: NVIDIA Container Toolkit installato; verificare con nvidia-smi
up-gpu:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_GPU) up -d --wait

# Avvia solo core + sim (senza obs/llm) per debug rapido
up-core:
	docker compose -f $(COMPOSE_CORE) -f $(COMPOSE_SIM) up -d --wait

# Ferma lo stack (mantiene i volumi dati)
down:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) down

# Cancella volumi e ricrea stack pulito (reset completo)
# Semantica D-09: make reset = down -v && make up
reset:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) down -v
	$(MAKE) up

## Monitoring
# -----------------------------------------------------------------------

# Stato containers (ps)
ps:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) ps

# Log di tutti i servizi o di un singolo: make logs SVC=langfuse-web
logs:
	docker compose $(BASE_STACK) -f $(COMPOSE_LLM_CPU) logs --follow $(SVC)

## Quality
# -----------------------------------------------------------------------

# Esegue tutti i test dei progetti Nx in parallelo
# Se nessun progetto ha target test definito, nx run-many ignora silenziosamente
test:
	npx nx run-many --target=test --all --parallel=4

# Linting Nx + pre-commit hooks (ruff, eslint, prettier, gitleaks, commitlint)
lint:
	npx nx run-many --target=lint --all --parallel=4
	pre-commit run --all-files

# Formattazione: Nx format + ruff-format + prettier
format:
	npx nx format:write
	pre-commit run ruff-format --all-files || true
	pre-commit run prettier --all-files || true

## Docs
# -----------------------------------------------------------------------

# Genera la documentazione MkDocs
docs:
	cd docs && mkdocs build

## Demo
# -----------------------------------------------------------------------

demo:
	@echo "Demo non implementata in Fase 1 (Fase 5+)"

## Supply chain / Security
# -----------------------------------------------------------------------

# Genera SBOM CycloneDX con Syft e verifica policy licenze con Trivy
# Prerequisito: syft (https://github.com/anchore/syft) e trivy (https://aquasecurity.github.io/trivy/) installati
# Uso: make sbom          — genera sbom.json e stampa report licenze a schermo
# Per installare: brew install syft trivy  oppure  curl -sSfL ... (vedi link sopra)
sbom:
	@command -v syft >/dev/null || (echo "syft non trovato: installa via https://github.com/anchore/syft" && exit 1)
	@command -v trivy >/dev/null || (echo "trivy non trovato: installa via https://aquasecurity.github.io/trivy/" && exit 1)
	syft . --output cyclonedx-json=sbom.json
	trivy sbom sbom.json --scanners license --config infra/license/trivy.yaml --format table

# Esegui solo la license scan su SBOM esistente (sbom.json deve gia' esistere)
license-scan:
	@command -v trivy >/dev/null || (echo "trivy non trovato: installa via https://aquasecurity.github.io/trivy/" && exit 1)
	@[ -f sbom.json ] || (echo "sbom.json non trovato: eseguire prima 'make sbom'" && exit 1)
	trivy sbom sbom.json --scanners license --config infra/license/trivy.yaml --format table

## Helm
# -----------------------------------------------------------------------

# Test smoke Helm su cluster k3d locale (plan 06)
helm-test:
	@echo "helm-test definito in plan 06 — eseguire dopo completamento plan 06"
