---
plan_id: 05-05-neo4j-compose-bootstrap
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 2
depends_on: [05-01-sft-knowledge-sdk]
requirements: [KNW-08]
files_modified:
  - infra/compose/core.yml
  - scripts/neo4j-bootstrap.py
  - infra/helm/charts/neo4j/Chart.yaml
  - infra/helm/charts/neo4j/values.yaml
  - infra/helm/charts/neo4j/templates/statefulset.yaml
  - infra/helm/charts/neo4j/templates/service.yaml
  - packages/sft-knowledge/tests/test_neo4j_builder.py
  - packages/sft-knowledge/tests/conftest.py
autonomous: true
estimated_atomic_commits: 3
must_haves:
  truths:
    - "Neo4j 5.24-community service is reachable via bolt://localhost:7687 after `make up`"
    - "APOC plugin is enabled (apoc.* procedures callable)"
    - "scripts/neo4j-bootstrap.py creates 4 unique constraints + 1 index idempotently"
    - "Helm chart skeleton deploys Neo4j to k8s with persistent volume"
    - "test_constraints_idempotent passes via testcontainer Neo4j+APOC"
  artifacts:
    - path: infra/compose/core.yml
      provides: Neo4j service block (image, env, ports, healthcheck, volume)
    - path: scripts/neo4j-bootstrap.py
      provides: idempotent constraints + index bootstrap script
    - path: infra/helm/charts/neo4j/
      provides: Helm chart skeleton for k8s deployment
  key_links:
    - from: scripts/neo4j-bootstrap.py
      to: Neo4j Bolt endpoint
      via: AsyncGraphDatabase + parametrized Cypher
      pattern: "AsyncGraphDatabase|CREATE CONSTRAINT"
    - from: infra/compose/core.yml
      to: Neo4j healthcheck
      via: HTTP probe on 7474
      pattern: "neo4j:5.24"
---

<objective>
Add Neo4j Community 5.24 to dev Docker Compose stack, write idempotent constraint+index bootstrap script, ship Helm chart skeleton for k8s deployment, and validate via testcontainer integration test.

Purpose: foundational graph infrastructure that Plan 05-08 Neo4jGraphBuilder writes to and Plan 05-09 TraverseGraphTool reads from. KNW-08 infra side closes here (population happens in Plan 05-08).

Output: a runnable Neo4j service + bootstrap script + Helm chart + green integration test.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md
@.planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md
@.planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md
@infra/compose/core.yml
@scripts/timescale-migrate.py
</context>

<interfaces>
Neo4j async driver (RESEARCH §5 + verified Python 5.x compat):
- `from neo4j import AsyncGraphDatabase`
- `driver = AsyncGraphDatabase.driver(uri, auth=(user, password))`
- `async with driver.session(database="neo4j") as session: await session.run(cypher, **params)`
- `await driver.close()`

Schema constraints (D-65 LOCKED):
- `CREATE CONSTRAINT machine_id_unique IF NOT EXISTS FOR (m:Machine) REQUIRE m.id IS UNIQUE`
- `CREATE CONSTRAINT part_id_unique IF NOT EXISTS FOR (p:Part) REQUIRE p.id IS UNIQUE`
- `CREATE CONSTRAINT failure_mode_id_unique IF NOT EXISTS FOR (f:FailureMode) REQUIRE f.id IS UNIQUE`
- `CREATE CONSTRAINT sop_id_unique IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE`
- `CREATE INDEX sop_version IF NOT EXISTS FOR (s:SOP) ON (s.version)`

Compose service block (RESEARCH §5 + PATTERNS.md core.yml section):
- image: `neo4j:5.24-community`
- env: NEO4J_AUTH (default `neo4j/devpassword`), NEO4J_PLUGINS=`'["apoc"]'`, NEO4J_apoc_export_file_enabled=true, NEO4J_apoc_import_file_enabled=true, NEO4J_dbms_security_procedures_unrestricted=`apoc.*`
- ports: 7687 (bolt), 7474 (browser dev-only)
- volume: neo4j-data:/data
- healthcheck: HTTP probe on 7474 (timeout 10s, retries 10)
- network: sft-core

Driver version constraint (RESEARCH §5 Risk 1): `neo4j>=5.24,<7` (already declared in Plan 05-01 pyproject).

APOC plugin enables Cypher procedures (e.g., `apoc.export.cypher.all` for backup, `apoc.merge.relationship` for advanced merges). Phase 5 uses pure Cypher MERGE (no APOC procedure dependency in code), but APOC is available for future use and verified callable in integration test.

Testcontainer Neo4j (RESEARCH §5 Open Question + PATTERNS.md conftest.py):
- `from testcontainers.neo4j import Neo4jContainer`
- `Neo4jContainer("neo4j:5.24-community").with_env("NEO4J_PLUGINS", '["apoc"]')`
- `container.get_connection_url()` → bolt URI
- Password: `Neo4jContainer.NEO4J_ADMIN_PASSWORD` class const
</interfaces>

<tasks>

<task id="05-05-01" type="auto">
  <name>Task 1: Add Neo4j service to docker-compose + neo4j-data volume</name>
  <files>
    infra/compose/core.yml
  </files>
  <read_first>
    infra/compose/core.yml (existing services structure + qdrant block lines 41-55 + volumes block at bottom),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-65 service config lines 230-235),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §5 (APOC env vars verified),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (infra/compose/core.yml section lines 1066-1110)
  </read_first>
  <action>
    Edit `infra/compose/core.yml`:

    1. Add new service block `neo4j:` mirroring the existing `qdrant:` block structure. Place it after `qdrant:` and before any apps-level services. Service spec:
       - `image: neo4j:5.24-community`
       - `environment:`
         - `NEO4J_AUTH: "${NEO4J_AUTH:-neo4j/devpassword}"`
         - `NEO4J_PLUGINS: '["apoc"]'`
         - `NEO4J_apoc_export_file_enabled: "true"`
         - `NEO4J_apoc_import_file_enabled: "true"`
         - `NEO4J_dbms_security_procedures_unrestricted: "apoc.*"`
       - `volumes:`
         - `- neo4j-data:/data`
       - `ports:`
         - `- "${NEO4J_BOLT_PORT:-7687}:7687"`
         - `- "${NEO4J_HTTP_PORT:-7474}:7474"`
       - `healthcheck:`
         - `test: ["CMD-SHELL", "wget -qO- http://localhost:7474 | grep -q Neo4j"]`
         - `interval: 10s`
         - `timeout: 5s`
         - `retries: 10`
       - `networks:`
         - `- sft-core`
       - `restart: unless-stopped`

    2. Add `neo4j-data:` to the `volumes:` block at file bottom (mirror existing `qdrant-data:` pattern; usually `driver: local` or empty mapping).

    3. Verify YAML is still valid: `docker compose -f infra/compose/core.yml config` exits 0 (or `docker-compose` legacy syntax — match what existing Phase 1-3 commands use).

    4. Verify boot: `docker compose -f infra/compose/core.yml up -d neo4j` then `docker compose -f infra/compose/core.yml ps neo4j` shows healthy status. Then `docker compose -f infra/compose/core.yml down` to clean. (This local boot test is optional but recommended before commit; CI testcontainer in Task 3 is the authoritative gate.)

    Commit: `feat(05-05-neo4j-compose-bootstrap): add Neo4j 5.24-community service with APOC to docker compose`.
  </action>
  <acceptance_criteria>
    - `grep -q 'image: neo4j:5.24-community' infra/compose/core.yml`
    - `grep -q 'NEO4J_PLUGINS' infra/compose/core.yml` and `grep -q 'apoc' infra/compose/core.yml`
    - `grep -q 'neo4j-data:' infra/compose/core.yml`
    - `grep -q '7687' infra/compose/core.yml` (bolt port)
    - `docker compose -f infra/compose/core.yml config` exits 0 (YAML validity)
  </acceptance_criteria>
  <verify>
    <automated>docker compose -f infra/compose/core.yml config &gt; /dev/null &amp;&amp; grep -q 'neo4j:5.24-community' infra/compose/core.yml</automated>
  </verify>
  <done>Neo4j service block added, YAML valid, APOC env vars present.</done>
</task>

<task id="05-05-02" type="auto" tdd="true">
  <name>Task 2: scripts/neo4j-bootstrap.py — idempotent constraints + index</name>
  <files>
    scripts/neo4j-bootstrap.py,
    packages/sft-knowledge/tests/test_neo4j_builder.py,
    packages/sft-knowledge/tests/conftest.py
  </files>
  <read_first>
    scripts/timescale-migrate.py (WORKSPACE_ROOT pattern, argparse, asyncio.run, env DSN, --dry-run handling),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-65 constraints list lines 237-247),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §5 (async driver pattern + APOC env),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (scripts/neo4j-bootstrap.py section lines 962-995)
  </read_first>
  <behavior>
    - Script supports `--neo4j-uri` (default `NEO4J_URI` env or `bolt://localhost:7687`) and `--neo4j-auth` (default `NEO4J_AUTH` env or `neo4j/devpassword`)
    - Supports `--dry-run` flag (prints plan, no driver connection)
    - Module-level constant `_CONSTRAINTS` containing 5 Cypher statements (4 unique constraints + 1 index) per D-65
    - Each Cypher statement uses `IF NOT EXISTS` clause (idempotent)
    - For each statement: open async session, run statement, print "OK [constraint_name]: applied"
    - APOC verification step: `CALL apoc.help('apoc')` (returns rows if APOC available); print "OK [apoc]: plugin verified" or fail with "ERROR: APOC plugin not available — check NEO4J_PLUGINS env"
    - Re-running script: all `IF NOT EXISTS` clauses make it a no-op
    - Test `test_constraints_idempotent` (integration): runs bootstrap twice; asserts no exceptions + verifies all 4 constraints via `SHOW CONSTRAINTS` + 1 index via `SHOW INDEXES`
    - Test `test_apoc_available`: runs `CALL apoc.help('apoc') YIELD core RETURN count(*) AS n`; asserts `n > 0`
  </behavior>
  <action>
    Create `scripts/neo4j-bootstrap.py`:
    - `from __future__ import annotations`, `import argparse`, `import asyncio`, `import os`, `import sys`, `from pathlib import Path`
    - `WORKSPACE_ROOT = Path(__file__).parent.parent`
    - Module-level constant tuple of Cypher constraint statements (exactly 5 statements per D-65):
      ```
      _CONSTRAINTS: tuple[str, ...] = (
          "CREATE CONSTRAINT machine_id_unique IF NOT EXISTS FOR (m:Machine) REQUIRE m.id IS UNIQUE",
          "CREATE CONSTRAINT part_id_unique IF NOT EXISTS FOR (p:Part) REQUIRE p.id IS UNIQUE",
          "CREATE CONSTRAINT failure_mode_id_unique IF NOT EXISTS FOR (f:FailureMode) REQUIRE f.id IS UNIQUE",
          "CREATE CONSTRAINT sop_id_unique IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE",
          "CREATE INDEX sop_version IF NOT EXISTS FOR (s:SOP) ON (s.version)",
      )
      ```
    - argparse with `--neo4j-uri`, `--neo4j-auth` (parsed as `user/password` colon/slash format), `--dry-run`.
    - `async def bootstrap(uri: str, auth: tuple[str, str], dry_run: bool) -> int`:
      1. If dry_run: print plan + return 0.
      2. Import driver inside function: `from neo4j import AsyncGraphDatabase`
      3. `driver = AsyncGraphDatabase.driver(uri, auth=auth)`
      4. try/finally to ensure `await driver.close()`.
      5. `async with driver.session(database="neo4j") as session:`
         - For each cypher in `_CONSTRAINTS`: `await session.run(cypher)`; print "OK [{constraint_name}]: applied" (extract name from constraint text or pass index).
         - APOC verification: `result = await session.run("CALL apoc.help('apoc') YIELD core RETURN count(*) AS n")`; `record = await result.single()`; if `record["n"] == 0`: print stderr "ERROR: APOC unavailable" + return 1.
      6. Return 0.
    - Return non-zero from main on exception with stderr message.

    Update `packages/sft-knowledge/tests/conftest.py` `neo4j_driver` fixture (replacing Plan 05-01 stub body):
    - `@pytest.fixture(scope="session")` returning AsyncGraphDatabase driver.
    - Use `Neo4jContainer("neo4j:5.24-community").with_env("NEO4J_PLUGINS", '["apoc"]')` (per RESEARCH §5 Open Question 3 mitigation).
    - Inside context manager: build URI from `container.get_connection_url()`, create `AsyncGraphDatabase.driver(uri, auth=("neo4j", Neo4jContainer.NEO4J_ADMIN_PASSWORD))`, yield driver, close on teardown.

    Update `packages/sft-knowledge/tests/test_neo4j_builder.py` (remove Plan 05-01 stub `pytestmark = pytest.mark.skip(...)`):
    - `@pytest.mark.integration async def test_constraints_idempotent(neo4j_driver):`
      1. Run subprocess.run([sys.executable, "scripts/neo4j-bootstrap.py", "--neo4j-uri", uri, "--neo4j-auth", "neo4j/{password}"], check=True). returncode == 0.
      2. `async with neo4j_driver.session() as s: rows = [r async for r in await s.run("SHOW CONSTRAINTS")]`. Assert 4 unique constraints exist (filter by `entityType = 'NODE'` + `type = 'UNIQUENESS'`).
      3. Verify index: `await s.run("SHOW INDEXES YIELD name WHERE name = 'sop_version'")` returns 1 row.
      4. Re-run subprocess.run for bootstrap; assert returncode == 0 (idempotency).
      5. SHOW CONSTRAINTS count unchanged.
    - `@pytest.mark.integration async def test_apoc_available(neo4j_driver):`
      1. `async with neo4j_driver.session() as s: result = await s.run("CALL apoc.help('apoc') YIELD core RETURN count(*) AS n"); record = await result.single()`.
      2. Assert `record["n"] > 0`.

    Commit: `feat(05-05-neo4j-compose-bootstrap): add idempotent Neo4j constraints bootstrap + integration tests`.
  </action>
  <acceptance_criteria>
    - `scripts/neo4j-bootstrap.py` exists with literal `_CONSTRAINTS` tuple
    - `grep -c 'IF NOT EXISTS' scripts/neo4j-bootstrap.py` returns ≥5
    - `grep -q 'CALL apoc' scripts/neo4j-bootstrap.py` (APOC verification call)
    - `grep -q 'AsyncGraphDatabase' scripts/neo4j-bootstrap.py`
    - `uv run python scripts/neo4j-bootstrap.py --dry-run` exits 0
    - `nx run sft-knowledge:test --args="-m integration -k 'test_constraints_idempotent or test_apoc_available' -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>uv run python scripts/neo4j-bootstrap.py --dry-run &amp;&amp; nx run sft-knowledge:test --args="-m integration -k 'test_constraints_idempotent or test_apoc_available' -v"</automated>
  </verify>
  <done>Neo4j bootstrap script + 2 integration tests green; idempotency proven; APOC plugin verified callable.</done>
</task>

<task id="05-05-03" type="auto">
  <name>Task 3: Helm chart skeleton for Neo4j k8s deployment</name>
  <files>
    infra/helm/charts/neo4j/Chart.yaml,
    infra/helm/charts/neo4j/values.yaml,
    infra/helm/charts/neo4j/templates/statefulset.yaml,
    infra/helm/charts/neo4j/templates/service.yaml
  </files>
  <read_first>
    infra/helm/ (existing Helm chart structure from Phase 1 — find via `ls infra/helm/charts/` or `find infra/helm -name Chart.yaml`),
    .planning/phases/01-foundation-monorepo/01-CONTEXT.md (Helm chart skeleton pattern from Phase 1 PLAT-08)
  </read_first>
  <action>
    Create `infra/helm/charts/neo4j/Chart.yaml`:
    - apiVersion: v2
    - name: neo4j
    - description: Neo4j 5.24 Community single-node for sft knowledge graph (Phase 5 — k3d/k8s)
    - type: application
    - version: 0.1.0
    - appVersion: "5.24.0"

    Create `infra/helm/charts/neo4j/values.yaml`:
    - `image: { repository: "neo4j", tag: "5.24-community", pullPolicy: IfNotPresent }`
    - `auth: { username: "neo4j", existingSecret: "" }` (skeleton — production uses SealedSecrets per Phase 1)
    - `plugins: ["apoc"]`
    - `service: { type: ClusterIP, boltPort: 7687, httpPort: 7474 }`
    - `persistence: { enabled: true, size: 10Gi, storageClass: "" }`
    - `resources: { requests: { memory: "2Gi", cpu: "500m" }, limits: { memory: "4Gi", cpu: "1000m" } }` (Community 4GB heap concern from STATE.md blocker — document this)

    Create `infra/helm/charts/neo4j/templates/statefulset.yaml`:
    - StatefulSet apiVersion apps/v1, name `{{ include "neo4j.fullname" . }}`, replicas 1.
    - Container spec uses values.image, env `NEO4J_AUTH` from secret (skeleton ref), `NEO4J_PLUGINS={{ .Values.plugins | toJson }}`, the same 3 `NEO4J_apoc_*` env vars from Task 1 compose.
    - Ports 7687 (bolt) + 7474 (http).
    - VolumeClaimTemplate referencing values.persistence.

    Create `infra/helm/charts/neo4j/templates/service.yaml`:
    - Service exposing bolt (7687) + http (7474) ports.

    NOTE: This is a SKELETON. Actual k8s smoke test (helm install + connectivity) is deferred to Phase 11 hardening. Phase 5 requirement: chart files exist + `helm lint infra/helm/charts/neo4j` passes (or `helm template` renders without error if helm lint not available locally).

    Verify: `helm lint infra/helm/charts/neo4j` exits 0 OR `helm template test infra/helm/charts/neo4j` renders without error.

    Commit: `feat(05-05-neo4j-compose-bootstrap): add Neo4j Helm chart skeleton (k8s deployment scaffold)`.
  </action>
  <acceptance_criteria>
    - `ls infra/helm/charts/neo4j/Chart.yaml infra/helm/charts/neo4j/values.yaml infra/helm/charts/neo4j/templates/statefulset.yaml infra/helm/charts/neo4j/templates/service.yaml | wc -l` returns 4
    - `grep -q 'appVersion: "5.24.0"' infra/helm/charts/neo4j/Chart.yaml`
    - `grep -q 'apoc' infra/helm/charts/neo4j/values.yaml`
    - `helm lint infra/helm/charts/neo4j` exits 0 (if helm available) OR `helm template test infra/helm/charts/neo4j 2>/dev/null` exits 0
  </acceptance_criteria>
  <verify>
    <automated>helm lint infra/helm/charts/neo4j 2&gt;/dev/null || helm template test infra/helm/charts/neo4j 2&gt;/dev/null &gt; /dev/null</automated>
  </verify>
  <done>Helm chart skeleton committed; helm lint/template renders successfully.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| script → Neo4j Bolt | Bootstrap script sends Cypher constraint statements; auth via env-provided credentials |
| docker compose → Neo4j HTTP browser (7474) | Dev-only port (Phase 5); production deployments must restrict via NetworkPolicy (Phase 11) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-05-01 | Tampering | bootstrap idempotency | mitigate | Every Cypher uses `IF NOT EXISTS`; integration test verifies re-run is no-op |
| T-05-05-02 | Spoofing | Neo4j auth in dev | accept | Dev credentials `neo4j/devpassword` hardcoded in compose; production overrides via `NEO4J_AUTH` env (SealedSecret in Helm) |
| T-05-05-03 | Elevation of Privilege | APOC unrestricted procedures | mitigate | `NEO4J_dbms_security_procedures_unrestricted: apoc.*` limits to APOC namespace only; Phase 11 reviews production tightening |
| T-05-05-04 | Information Disclosure | Neo4j browser HTTP 7474 | accept | Phase 5 dev-only; Phase 11 NetworkPolicy + helm chart updates remove 7474 from prod |
| T-05-05-SC | Tampering | npm/pip install | mitigate | `neo4j>=5.24,<7` and `testcontainers[neo4j]` already declared in Plan 05-01; Approved per 05-RESEARCH legitimacy audit |
</threat_model>

<verification>
- `docker compose -f infra/compose/core.yml config` exits 0
- `uv run python scripts/neo4j-bootstrap.py --dry-run` exits 0
- `nx run sft-knowledge:test --args="-m integration -k 'test_constraints_idempotent or test_apoc_available' -v"` exits 0
- `helm lint infra/helm/charts/neo4j` (or `helm template`) exits 0
- 4 unique constraints + 1 index applied via integration test
- APOC plugin verified callable via integration test
</verification>

<success_criteria>
- 3 atomic commits: `feat(05-05-neo4j-compose-bootstrap):` × 3
- Neo4j service runnable via `docker compose up neo4j`
- Bootstrap script idempotent, APOC verified
- Helm chart skeleton ready for Phase 11 production hardening
- KNW-08 infra side closed (population in Plan 05-08)
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-05-neo4j-compose-bootstrap-SUMMARY.md` when done with: 4 constraints + 1 index applied, APOC verified, Helm chart structure, idempotency proof.
</output>
