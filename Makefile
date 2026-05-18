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

.PHONY: up up-gpu up-core down reset test lint format docs docs-serve demo sbom license-scan helm-test ps logs validate-corpus generate-glossary generate-assumptions validate-glossary validate-assets validate-all migrate-timescale migrate-timescale-dry

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

# Build del sito MkDocs in strict mode (fallisce su broken link o warning critici)
# Prerequisito: mkdocs installato — cd docs && pip install -r requirements.txt
docs:
	@command -v mkdocs >/dev/null || (echo "mkdocs non trovato: cd docs && pip install -r requirements.txt" && exit 1)
	cd docs && mkdocs build --strict

# Preview locale con hot-reload su http://127.0.0.1:8000
docs-serve:
	cd docs && mkdocs serve -a 127.0.0.1:8000

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

## Content Validation (Phase 2 — glossario, corpus, assumption register)
# -----------------------------------------------------------------------

# Valida il frontmatter YAML di tutti i SOP nel corpus sintetico (D-26)
# Requisito: uv sync --all-packages (python-frontmatter, jsonschema)
# Usa 'uv run' per garantire che le dipendenze Python siano disponibili
validate-corpus:
	uv run python3 scripts/validate-corpus-frontmatter.py
	uv run python3 scripts/validate-corpus-pairing.py
	uv run python3 scripts/validate-bilingual-mirror.py

# Rigenera le pagine glossario MkDocs da YAML sorgente (D-29)
# Idempotente: eseguire due volte produce output identico
generate-glossary:
	python3 scripts/generate-glossary-pages.py

# Rigenera le pagine assumption register MkDocs da YAML sorgente (D-33)
# Idempotente: eseguire due volte produce output identico
generate-assumptions:
	python3 scripts/generate-assumption-pages.py

# Valida schema e copertura del glossario (D-29, D-32)
# Schema: validate-glossary-schema.py (jsonschema Draft 2020-12)
# Copertura: validate-glossary-coverage.py (bold token lookup, lang-matched)
validate-glossary:
	python3 scripts/validate-glossary-schema.py
	python3 scripts/validate-glossary-coverage.py

# Valida il registro asset contro asset.schema.json (D-45, IOT-09)
# Prerequisito: uv sync (pyyaml, jsonschema gia' in workspace devDeps)
validate-assets:
	python3 scripts/validate-asset-registry.py

# Esegue tutte le validazioni di contenuto in sequenza
# Include: schema glossario, copertura, corpus frontmatter, assumption register, asset registry
# e check drift pagine generate (--check mode per generate-glossary-pages.py)
# Usa 'uv run' per i validatori che richiedono dipendenze Python
validate-all: validate-glossary validate-corpus validate-assets
	uv run python3 scripts/validate-assumption-schema.py
	uv run python3 scripts/validate-assumption-components.py
	python3 scripts/generate-glossary-pages.py --check
	uv run python3 scripts/generate-assumption-pages.py --check

## Helm
# -----------------------------------------------------------------------

# Test smoke Helm su cluster k3d locale (D-20)
# Prerequisiti: helm (https://helm.sh), k3d (https://k3d.io)
# Installa: brew install helm k3d  oppure  vedi rispettivi siti upstream
# Nota: in CI k3d viene installato automaticamente via AbsaOSS/k3d-action
helm-test:
	@command -v helm >/dev/null || (echo "helm non trovato: brew install helm o https://helm.sh/docs/intro/install/" && exit 1)
	@command -v k3d >/dev/null || (echo "k3d non trovato; per CI verra' installato via AbsaOSS/k3d-action" && exit 1)
	helm dependency update infra/helm/sft-stack/
	for chart in infra/helm/charts/*; do helm lint "$$chart"; done
	helm lint infra/helm/sft-stack/
	helm install sft-test infra/helm/sft-stack/ --values infra/helm/sft-stack/values-ci.yaml --dry-run

## Phase 3: TimescaleDB migration
# -----------------------------------------------------------------------

# Applica le migration TimescaleDB all'istanza configurata in $TIMESCALE_DSN
# Idempotente: ri-eseguibile senza side-effects (CREATE TABLE IF NOT EXISTS + DO blocks)
# Prerequisito: $TIMESCALE_DSN impostato o docker compose up (make up-core)
migrate-timescale:
	python3 scripts/timescale-migrate.py

# Mostra quali migration verrebbero applicate senza connettersi al DB
migrate-timescale-dry:
	python3 scripts/timescale-migrate.py --dry-run
