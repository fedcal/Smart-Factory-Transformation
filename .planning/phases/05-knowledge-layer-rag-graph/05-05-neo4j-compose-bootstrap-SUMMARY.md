---
phase: 05-knowledge-layer-rag-graph
plan: 05
subsystem: infra
tags: [neo4j, apoc, docker-compose, helm, statefulset, testcontainers, knowledge-graph, cypher]

# Dependency graph
requires:
  - phase: 05-knowledge-layer-rag-graph (Wave 1 / 05-01)
    provides: sft-knowledge package skeleton + neo4j>=5.24,<7 dependency + testcontainers[neo4j] dev extra
provides:
  - Neo4j 5.24 Community service nel dev Docker Compose stack (porte 7687/7474)
  - APOC plugin abilitato + verifica callable
  - scripts/neo4j-bootstrap.py idempotente per 4 unique constraints + 1 index (D-65 locked)
  - Helm chart skeleton infra/helm/charts/neo4j/ (Chart + values + StatefulSet + Service + _helpers)
  - Fixture neo4j_driver session-scoped (loop_scope=session) + testcontainers integration
  - Knowledge graph schema constraints scope (Machine.id, Part.id, FailureMode.id, SOP.id, SOP.version)
affects: [05-08-neo4j-graph-builder, 05-09-traverse-graph-tool, 11-hardening, knowledge-layer, graph-rag]

# Tech tracking
tech-stack:
  added:
    - "neo4j:5.24-community (docker image)"
    - "APOC plugin (Cypher procedure library)"
    - "Helm chart skeleton for Neo4j single-node StatefulSet"
  patterns:
    - "Bootstrap script CLI pattern (parallelo a qdrant-bootstrap.py): argparse + env fallback + --dry-run + asyncio.run"
    - "IF NOT EXISTS Cypher idempotency: tutti i CREATE CONSTRAINT/INDEX riapplicabili senza eccezioni"
    - "Testcontainer session fixture publishing _neo4j_uri/_user/_password su request.config per subprocess CLI"
    - "pytest_asyncio.fixture(scope=session, loop_scope=session) per condividere event loop con async driver pool"

key-files:
  created:
    - "scripts/neo4j-bootstrap.py"
    - "infra/helm/charts/neo4j/Chart.yaml"
    - "infra/helm/charts/neo4j/values.yaml"
    - "infra/helm/charts/neo4j/templates/_helpers.tpl"
    - "infra/helm/charts/neo4j/templates/statefulset.yaml"
    - "infra/helm/charts/neo4j/templates/service.yaml"
  modified:
    - "infra/compose/core.yml (added neo4j service + neo4j-data volume)"
    - "packages/sft-knowledge/tests/conftest.py (neo4j_driver fixture: APOC plugin env + connection params stash + pytest_asyncio.fixture)"
    - "packages/sft-knowledge/tests/test_neo4j_builder.py (test_constraints_idempotent + test_apoc_available integration)"

key-decisions:
  - "Aggiunto _helpers.tpl (non in PLAN files_modified list) per name/labels conformi al pattern dei chart Phase 1 (api-gateway) — riuso DRY, evita label hard-coded sparsi nei template"
  - "Fixture neo4j_driver migrata a pytest_asyncio.fixture(loop_scope=session) per evitare 'Future attached to different loop' (Neo4j AsyncDriver pool è tightly bound al loop di creazione)"
  - "Publish _neo4j_uri/_user/_password su request.config (parallelo al pattern _qdrant_url di 05-04) invece di ispezionare driver._pool — interfaccia pubblica robusta a refactor del driver"
  - "Password testcontainer letta da container.password (env NEO4J_PASSWORD o default 'password'), NON da costante NEO4J_ADMIN_PASSWORD (inesistente in testcontainers 4.x)"

patterns-established:
  - "Pattern Neo4j-bootstrap CLI: argparse(--neo4j-uri, --neo4j-auth, --dry-run) + env NEO4J_URI/NEO4J_AUTH + asyncio.run + tuple _CONSTRAINTS module-level"
  - "Pattern Neo4j integration test: subprocess + SHOW CONSTRAINTS/INDEXES introspection + idempotency rerun"
  - "Pattern Helm chart Neo4j StatefulSet: single replica + volumeClaimTemplate + APOC env vars + readiness HTTP/7474 + liveness TCP/7687"
  - "Pattern fixture session async: pytest_asyncio.fixture(scope=session, loop_scope=session) + @pytest.mark.asyncio(loop_scope=session) sui test che la consumano"

requirements-completed:
  - KNW-08

# Metrics
duration: ~38min
completed: 2026-05-19
---

# Phase 5 Plan 05: Neo4j Compose + Bootstrap Summary

**Neo4j 5.24 Community + APOC nel dev Docker Compose, script bootstrap idempotente per 4 unique constraints + 1 index (D-65), Helm chart skeleton single-node con StatefulSet 10Gi e integration test green via testcontainer.**

## Performance

- **Duration:** ~38 min
- **Started:** 2026-05-19 (worktree-agent-a238ba4665bf59848)
- **Completed:** 2026-05-19
- **Tasks:** 3 (4 commits totali, TDD RED+GREEN su Task 2)
- **Files modified:** 3 (compose/core.yml, conftest.py, test_neo4j_builder.py)
- **Files created:** 6 (neo4j-bootstrap.py + 5 file Helm chart)

## Accomplishments
- Neo4j 5.24-community nel `infra/compose/core.yml` (porte 7687 bolt + 7474 http, healthcheck HTTP, volume `neo4j-data`)
- APOC plugin abilitato (`NEO4J_PLUGINS=["apoc"]`) + procedure unrestricted limitate al namespace `apoc.*` (T-05-05-03 mitigation)
- `scripts/neo4j-bootstrap.py`: 5 statement Cypher idempotenti (4 unique constraints + 1 index per D-65) + APOC verification via `apoc.help('apoc')`
- Helm chart `infra/helm/charts/neo4j/`: Chart.yaml, values.yaml (image, APOC config, persistence 10Gi, resources 2-4Gi heap, podSecurityContext non-root), StatefulSet con volumeClaimTemplate + readiness/liveness, Service ClusterIP bolt+http
- Integration test green: `test_constraints_idempotent` (bootstrap subprocess 2x, SHOW CONSTRAINTS + SHOW INDEXES, count stabile) + `test_apoc_available` (apoc.help ritorna n>0)
- `helm lint` + `helm template` PASS

## Task Commits

Ogni task committato atomicamente sul branch `worktree-agent-a238ba4665bf59848`:

1. **Task 1: Add Neo4j service to docker-compose** — `a1d4134` (feat)
2. **Task 2 RED: Failing integration tests** — `d004f4e` (test, TDD RED)
3. **Task 2 GREEN: Bootstrap script + fixture fix** — `ed8de7e` (feat, TDD GREEN)
4. **Task 3: Helm chart skeleton** — `b853bc5` (feat)

_TDD Gate Compliance (plan-level type tdd su Task 2): RED commit `d004f4e` precede GREEN commit `ed8de7e` ✓_

## Files Created/Modified

### Created
- `scripts/neo4j-bootstrap.py` — Idempotent constraint+index bootstrap (4 unique + 1 index per D-65) + APOC verification, argparse + asyncio + dry-run
- `infra/helm/charts/neo4j/Chart.yaml` — apiVersion v2, version 0.1.0, appVersion 5.24.0
- `infra/helm/charts/neo4j/values.yaml` — image, auth (existingSecret stub), plugins, persistence 10Gi, resources requests 2Gi/500m + limits 4Gi/1000m, podSecurityContext
- `infra/helm/charts/neo4j/templates/_helpers.tpl` — neo4j.fullname/labels/selectorLabels (pattern api-gateway Phase 1)
- `infra/helm/charts/neo4j/templates/statefulset.yaml` — Single replica, env NEO4J_AUTH+NEO4J_PLUGINS+APOC, readiness HTTP /7474, liveness TCP 7687, volumeClaimTemplate
- `infra/helm/charts/neo4j/templates/service.yaml` — ClusterIP bolt 7687 + http 7474

### Modified
- `infra/compose/core.yml` — Aggiunto service `neo4j` (immagine 5.24-community, env APOC, porte 7687/7474, healthcheck HTTP, volume `neo4j-data`) + volume `neo4j-data:` in elenco volumes
- `packages/sft-knowledge/tests/conftest.py` — Fixture `neo4j_driver` migrata a `pytest_asyncio.fixture(scope=session, loop_scope=session)`, APOC plugin abilitato via `with_env`, publish `_neo4j_uri/_user/_password` su `request.config` per subprocess CLI
- `packages/sft-knowledge/tests/test_neo4j_builder.py` — Aggiunti `test_constraints_idempotent` + `test_apoc_available` (entrambi `@pytest.mark.asyncio(loop_scope="session")`), rimosso `pytestmark.skip` globale, stub di Plan 05-08 mantenuti con `pytest.skip()` mirato

## Decisions Made

- **`_helpers.tpl` aggiunto al chart Helm** (non listato esplicitamente in PLAN `files_modified` ma necessario per `{{ include "neo4j.fullname" . }}` e `{{ include "neo4j.labels" . }}` referenziati negli altri template — riuso del pattern api-gateway). Considerato sotto Rule 3 (blocking — senza helpers helm template fallisce).
- **`pytest_asyncio.fixture(loop_scope=session)`** invece di `pytest.fixture` (Rule 1 bug-fix): senza loop_scope il driver Neo4j AsyncBolt si lega al loop del primo test e i test successivi vedono "Future attached to different loop". Soluzione standard pytest-asyncio.
- **Connection params stashed su `request.config`** (`_neo4j_uri/_user/_password`) invece di ispezionare `driver._pool.address`: l'interfaccia pubblica del driver non garantisce stabilità di `_pool` (membro privato). Pattern parallelo a `_qdrant_url` di Plan 05-04.
- **Password testcontainer = `container.password`** (default `"password"` o env `NEO4J_PASSWORD`): la costante `Neo4jContainer.NEO4J_ADMIN_PASSWORD` menzionata nel plan _non_ esiste in testcontainers 4.14.2 — sostituita con accesso all'attributo di istanza.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Fixture `neo4j_driver` legato a loop wrong → AuthError + "Future attached to different loop"**
- **Found during:** Task 2 GREEN (prima run di `test_apoc_available`)
- **Issue:** Il primo test (`test_constraints_idempotent`) passa, ma il secondo fallisce con `RuntimeError: Task got Future attached to a different loop`. Causa: `@pytest.fixture(scope="session")` su fixture async crea il driver in un loop diverso da quello dei singoli test (pytest-asyncio default per-function loop scope).
- **Fix:**
  - Aggiunto `import pytest_asyncio` in `conftest.py`
  - Cambiato decoratore fixture da `@pytest.fixture(scope="session")` a `@pytest_asyncio.fixture(scope="session", loop_scope="session")`
  - Aggiunto `@pytest.mark.asyncio(loop_scope="session")` ai 2 test che consumano la fixture
- **Files modified:** `packages/sft-knowledge/tests/conftest.py`, `packages/sft-knowledge/tests/test_neo4j_builder.py`
- **Verification:** `uv run pytest tests/test_neo4j_builder.py -m integration -v` → 2 passed, 13.31s. Regressione non-integration: 23 passed, 8 skipped.
- **Committed in:** `ed8de7e` (Task 2 GREEN)

**2. [Rule 1 — Bug] Password testcontainer letta da costante inesistente → AuthError "unauthorized"**
- **Found during:** Task 2 GREEN (prima run integration test)
- **Issue:** Plan suggeriva `Neo4jContainer.NEO4J_ADMIN_PASSWORD` come costante di classe. In testcontainers 4.14.2 questa costante non esiste — la password è un attributo di istanza `container.password` (default `"password"` o env `NEO4J_PASSWORD`). Conftest stub Plan 05-01 cadeva sul `getattr` fallback `"neo4j"` → mismatch con env del container (`neo4j/password`) → `Neo.ClientError.Security.Unauthorized`.
- **Fix:** Fixture ora estrae `running.username` e `running.password` direttamente dall'istanza container.
- **Files modified:** `packages/sft-knowledge/tests/conftest.py`
- **Verification:** Login + bootstrap + `CALL apoc.help('apoc')` funzionanti — test pass.
- **Committed in:** `ed8de7e` (Task 2 GREEN)

**3. [Rule 3 — Blocking] Helm `_helpers.tpl` mancante → render fail su `{{ include "neo4j.fullname" . }}`**
- **Found during:** Task 3 (helm template render)
- **Issue:** StatefulSet e Service referenziano `{{ include "neo4j.fullname" . }}` + `{{ include "neo4j.labels" . }}` ma il plan non lista esplicitamente `templates/_helpers.tpl`. Senza file helpers, `helm template` fallisce.
- **Fix:** Creato `templates/_helpers.tpl` parallelo al pattern api-gateway (`neo4j.name`, `neo4j.fullname`, `neo4j.chart`, `neo4j.labels`, `neo4j.selectorLabels`).
- **Files modified:** `infra/helm/charts/neo4j/templates/_helpers.tpl` (nuovo)
- **Verification:** `helm lint infra/helm/charts/neo4j` → 0 chart failed; `helm template test infra/helm/charts/neo4j` → render OK.
- **Committed in:** `b853bc5` (Task 3)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** Tutti i fix essenziali per correttezza/funzionalità. Nessuno scope creep — restano solo i 6 file dichiarati nel plan + `_helpers.tpl` infrastrutturale al chart Helm.

## Issues Encountered

- **Testcontainers Neo4j wait_for_logs deprecation warnings**: la versione 4.14.2 emette `DeprecationWarning` per `@wait_container_is_ready` e `wait_for_logs` con string predicate. Non bloccante — warning informativi, da rivedere quando testcontainers 5.x diventerà standard. Lasciato in stato deferred (non in scope per Plan 05-05).
- **uv `dev` extras non sincronizzate**: `uv sync` di default non installa le optional-dependencies `[dev]` del package — eseguito `uv sync --extra dev` per portare in venv testcontainers/pytest/pytest-asyncio. Non bloccante, è il workflow normale per integration test.

## User Setup Required

None — nessuna configurazione esterna richiesta. Variabili `NEO4J_AUTH`, `NEO4J_BOLT_PORT`, `NEO4J_HTTP_PORT` opzionali in `.env` per override; default validi per dev locale.

## Known Stubs

Nessuno stub introdotto da questo plan. I 2 stub `test_graph_ci_validator` e `test_merge_sop_idempotent` in `test_neo4j_builder.py` sono stati mantenuti con `pytest.skip("Implemented in Plan 05-08")` — esplicitamente in scope per Plan 05-08 (Neo4jGraphBuilder).

## Threat Flags

Nessun nuovo trust boundary introdotto oltre a quelli già documentati nel `<threat_model>` del PLAN:
- `script → Neo4j Bolt` (auth env-provided) — mitigato via IF NOT EXISTS idempotency
- `compose → Neo4j HTTP 7474` (dev-only) — accept disposition, Phase 11 NetworkPolicy hardening

## Self-Check: PASSED

File esistenza (artifact obbligatori):
- ✅ `infra/compose/core.yml` (modified — service neo4j presente, grep 'neo4j:5.24-community' OK)
- ✅ `scripts/neo4j-bootstrap.py` (created, executable)
- ✅ `infra/helm/charts/neo4j/Chart.yaml` (appVersion "5.24.0" OK)
- ✅ `infra/helm/charts/neo4j/values.yaml` (apoc listed)
- ✅ `infra/helm/charts/neo4j/templates/statefulset.yaml`
- ✅ `infra/helm/charts/neo4j/templates/service.yaml`
- ✅ `infra/helm/charts/neo4j/templates/_helpers.tpl` (extra — deviation 3)
- ✅ `packages/sft-knowledge/tests/conftest.py` (modified)
- ✅ `packages/sft-knowledge/tests/test_neo4j_builder.py` (modified)

Commit esistenza:
- ✅ `a1d4134` (Task 1 compose)
- ✅ `d004f4e` (Task 2 RED)
- ✅ `ed8de7e` (Task 2 GREEN)
- ✅ `b853bc5` (Task 3 helm)

Verifica funzionale:
- ✅ `docker compose -f infra/compose/core.yml config` → exit 0
- ✅ `python3 scripts/neo4j-bootstrap.py --dry-run` → exit 0
- ✅ `uv run pytest tests/test_neo4j_builder.py -m integration -k 'test_constraints_idempotent or test_apoc_available' -v` → 2 passed in 13.31s
- ✅ `helm lint infra/helm/charts/neo4j` → 0 chart failed
- ✅ `helm template test infra/helm/charts/neo4j` → render OK

## Next Phase Readiness

- **Plan 05-08 (Neo4jGraphBuilder)** può ora consumare il `neo4j_driver` session fixture + la stash `_neo4j_uri/_user/_password` per integration test del builder. Constraints già pronti via bootstrap → MERGE su `:Machine/:Part/:FailureMode/:SOP` rispetta unique constraint.
- **Plan 05-09 (TraverseGraphTool)** ha Neo4j runnable in dev + indice `sop_version` pronto per query SOP.
- **Phase 11 (Hardening)** deve coprire: SealedSecret per `auth.existingSecret`, NetworkPolicy che rimuova esposizione di 7474, eventuale passaggio a Enterprise/cluster se dataset cresce oltre 4GB heap.

---
*Phase: 05-knowledge-layer-rag-graph*
*Plan: 05-05-neo4j-compose-bootstrap*
*Completed: 2026-05-19*
