---
plan_id: 05-04-qdrant-bootstrap
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 2
depends_on: [05-01-sft-knowledge-sdk]
requirements: [KNW-01]
files_modified:
  - scripts/qdrant-bootstrap.py
  - packages/sft-knowledge/tests/test_qdrant_indexer.py
  - packages/sft-knowledge/tests/conftest.py
autonomous: true
estimated_atomic_commits: 2
must_haves:
  truths:
    - "scripts/qdrant-bootstrap.py creates 4 collections (sop, manuals, troubleshooting, training) idempotently"
    - "Each collection has named vectors: dense (1024-d cosine) + sparse (BM42)"
    - "Each collection has payload indexes on: source_uri, acl_level, lang, category, version, asset_family, sop_id"
    - "Re-running bootstrap produces zero changes (idempotency)"
    - "test_collection_bootstrap_idempotent passes via testcontainer Qdrant"
  artifacts:
    - path: scripts/qdrant-bootstrap.py
      provides: idempotent bootstrap script with CREATE COLLECTION IF NOT EXISTS pattern
    - path: packages/sft-knowledge/tests/test_qdrant_indexer.py
      provides: integration test verifying bootstrap + idempotency
  key_links:
    - from: scripts/qdrant-bootstrap.py
      to: Qdrant client
      via: AsyncQdrantClient + create_collection + create_payload_index
      pattern: "create_collection|create_payload_index"
---

<objective>
Idempotent Qdrant collection bootstrap script + integration test verifying 4 collections (sop, manuals, troubleshooting, training) come up with dense+sparse named vectors and all required payload indexes per D-61.

Purpose: foundational infrastructure that Plan 05-08 (QdrantIndexer.upsert_batch) and Plan 05-09 (RetrievalPipeline) depend on. KNW-01 requirement closes here.

Output: a runnable script + a green testcontainer-driven integration test.
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
@scripts/nats-bootstrap-streams.py
@scripts/timescale-migrate.py
</context>

<interfaces>
Qdrant client API (RESEARCH §1 verified — qdrant-client 1.16+):

- `AsyncQdrantClient(url="http://localhost:6333")`
- `await client.get_collections()` → `CollectionsResponse(collections=[CollectionDescription(name=...)])`
- `await client.create_collection(name, vectors_config=..., sparse_vectors_config=...)`
- `await client.create_payload_index(collection_name, field_name, field_schema=PayloadSchemaType.KEYWORD)`

Imports needed (per 05-RESEARCH §1 + §9):
- `from qdrant_client import AsyncQdrantClient`
- `from qdrant_client.http.models import VectorParams, SparseVectorParams, SparseIndexParams, HnswConfigDiff, Distance, PayloadSchemaType`

Collection topology (D-61 LOCKED):
- 4 collections: `sop`, `manuals`, `troubleshooting`, `training`
- Each: named dense vector `"dense"` size=1024 distance=Distance.COSINE hnsw_config=HnswConfigDiff(m=16, ef_construct=100)
- Each: named sparse vector `"sparse"` using SparseVectorParams(index=SparseIndexParams(on_disk=False))
- on_disk_payload=False

Payload indexes (D-61 + claudes_discretion CONTEXT.md):
- source_uri, acl_level, lang, category, version, asset_family, sop_id — all PayloadSchemaType.KEYWORD

Idempotency pattern (05-RESEARCH §9 + PATTERNS.md qdrant-bootstrap.py section):
```
existing = {c.name for c in (await client.get_collections()).collections}
if name not in existing:
    await client.create_collection(...)
# Payload index creation: always idempotent — re-running raises no error per Qdrant docs
for field, schema in PAYLOAD_INDEXES.items():
    await client.create_payload_index(collection_name=name, field_name=field, field_schema=schema)
```

Testcontainer pattern (per Plan 05-01 conftest.py): `qdrant_client` session-scoped fixture using `testcontainers.qdrant.QdrantContainer("qdrant/qdrant:v1.16.1")`.
</interfaces>

<tasks>

<task id="05-04-01" type="auto" tdd="true">
  <name>Task 1: scripts/qdrant-bootstrap.py — idempotent 4-collection bootstrap</name>
  <files>
    scripts/qdrant-bootstrap.py
  </files>
  <read_first>
    scripts/nats-bootstrap-streams.py (CLI structure lines 41-61, idempotency pattern lines 186-205, --dry-run handling),
    scripts/timescale-migrate.py (WORKSPACE_ROOT pattern, argparse, asyncio.run, env DSN),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-61 collection topology + payload index list),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §1 (Qdrant API exact signatures) + §9 (idempotency patterns),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (qdrant-bootstrap.py section)
  </read_first>
  <behavior>
    - Script supports `--qdrant-url` (default from `QDRANT_URL` env or `http://localhost:6333`) and `--dry-run` flag
    - For each of [sop, manuals, troubleshooting, training]:
      - If collection exists: log "OK [name]: collection already exists"
      - If not: log "OK [name]: collection created" + invoke create_collection with named dense+sparse vectors
    - For each existing/created collection: create payload indexes on the 7 fields (idempotent)
    - Exit 0 on success, exit 1 on any failure (with stderr message)
    - `--dry-run` prints planned operations without making client calls; exits 0
    - All printed messages go to stdout (script output); errors to stderr
    - Uses `asyncio.run(bootstrap(...))` pattern from analog scripts
    - Module-level constants for collection names + payload index list (no f-string in API calls)
  </behavior>
  <action>
    Create `scripts/qdrant-bootstrap.py` from the analog `scripts/nats-bootstrap-streams.py`. Adapt:

    - `WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent` (same as analog).
    - argparse args: `--qdrant-url` default `os.environ.get("QDRANT_URL", "http://localhost:6333")`, `--dry-run` action="store_true".
    - Module-level constants:
      - `COLLECTIONS: tuple[str, ...] = ("sop", "manuals", "troubleshooting", "training")`
      - `PAYLOAD_INDEX_FIELDS: tuple[str, ...] = ("source_uri", "acl_level", "lang", "category", "version", "asset_family", "sop_id")`
      - `DENSE_DIM = 1024` (BGE-M3 native size, per D-61)
    - `async def bootstrap(url: str, dry_run: bool) -> int`:
      1. Import `AsyncQdrantClient` and required model types (`VectorParams, SparseVectorParams, SparseIndexParams, HnswConfigDiff, Distance, PayloadSchemaType`) inside function body to keep top-level imports light (matches analog).
      2. If dry_run: print plan and return 0.
      3. `client = AsyncQdrantClient(url=url)`
      4. `existing = {c.name for c in (await client.get_collections()).collections}`
      5. For each name in COLLECTIONS:
         - If name in existing: print "OK [{name}]: exists"
         - Else: `await client.create_collection(collection_name=name, vectors_config={"dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE, hnsw_config=HnswConfigDiff(m=16, ef_construct=100))}, sparse_vectors_config={"sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))}, on_disk_payload=False)` then print "OK [{name}]: created"
         - For each field in PAYLOAD_INDEX_FIELDS: `await client.create_payload_index(collection_name=name, field_name=field, field_schema=PayloadSchemaType.KEYWORD)` (this call is idempotent per Qdrant docs — RESEARCH §9). Print "OK [{name}]: payload_index.{field} ready"
      6. Wrap each create_collection + create_payload_index pair in `try/except Exception as exc`: on error, print to stderr "ERROR [{name}]: {exc}" and return 1.
      7. `await client.close()` then return 0.
    - `def main() -> int: args = _parse_args(); return asyncio.run(bootstrap(args.qdrant_url, args.dry_run))`
    - `if __name__ == "__main__": sys.exit(main())`

    Run `--dry-run` once locally to validate argparse: `uv run python scripts/qdrant-bootstrap.py --dry-run`.

    Commit: `feat(05-04-qdrant-bootstrap): add idempotent 4-collection Qdrant bootstrap script`.
  </action>
  <acceptance_criteria>
    - `scripts/qdrant-bootstrap.py` exists
    - `grep -q 'COLLECTIONS' scripts/qdrant-bootstrap.py` and `grep -q 'PAYLOAD_INDEX_FIELDS' scripts/qdrant-bootstrap.py`
    - `grep -q 'AsyncQdrantClient' scripts/qdrant-bootstrap.py`
    - `grep -q 'create_payload_index' scripts/qdrant-bootstrap.py`
    - `grep -q 'SparseVectorParams' scripts/qdrant-bootstrap.py`
    - `grep -q 'DENSE_DIM = 1024' scripts/qdrant-bootstrap.py`
    - `uv run python scripts/qdrant-bootstrap.py --dry-run` exits 0
  </acceptance_criteria>
  <verify>
    <automated>uv run python scripts/qdrant-bootstrap.py --dry-run &amp;&amp; grep -q 'CREATE.*sop\|"sop"' scripts/qdrant-bootstrap.py</automated>
  </verify>
  <done>Bootstrap script exists, --dry-run exits 0, all 4 collection names + 7 payload index fields encoded.</done>
</task>

<task id="05-04-02" type="auto" tdd="true">
  <name>Task 2: Integration test test_collection_bootstrap_idempotent via testcontainer Qdrant</name>
  <files>
    packages/sft-knowledge/tests/test_qdrant_indexer.py,
    packages/sft-knowledge/tests/conftest.py
  </files>
  <read_first>
    packages/sft-knowledge/tests/conftest.py (testcontainer fixture stubs from Plan 05-01),
    scripts/qdrant-bootstrap.py (just created in Task 1),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (KNW-01 test row),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (conftest.py testcontainer fixtures section)
  </read_first>
  <behavior>
    - `test_collection_bootstrap_idempotent` (integration):
      1. Invoke `bootstrap()` function from `scripts.qdrant_bootstrap` against testcontainer Qdrant.
      2. Assert all 4 collections present after first run.
      3. Each collection has dense vector size=1024 distance=COSINE, sparse vector configured.
      4. Each collection has payload indexes on 7 expected fields (verify via `await client.get_collection(name)`).
      5. Re-run bootstrap; assert no exceptions raised AND collection count unchanged + same vector config (proves idempotency).
    - Test is decorated `@pytest.mark.integration` so it is excluded from quick CI run; runs only when `nx run-many --target=test` invokes integration suite.
    - Test uses `qdrant_client` session fixture from conftest.py (created in Plan 05-01 stub; this task implements its real body).
  </behavior>
  <action>
    Remove `pytestmark = pytest.mark.skip(...)` from `packages/sft-knowledge/tests/test_qdrant_indexer.py` (was placed by Plan 05-01 Wave 0 stub).

    Implement `qdrant_client` session-scoped fixture in `packages/sft-knowledge/tests/conftest.py` (replacing the Plan 05-01 stub body):
    - Use `testcontainers.qdrant.QdrantContainer("qdrant/qdrant:v1.16.1")` context manager.
    - Inside: `from qdrant_client import AsyncQdrantClient; client = AsyncQdrantClient(url=container.get_client_url())`.
    - `yield client`; on teardown: `await client.close()`.
    - Mark `@pytest.fixture(scope="session")` and ensure it works with `asyncio_mode = "auto"`.

    Implement `test_collection_bootstrap_idempotent` in `packages/sft-knowledge/tests/test_qdrant_indexer.py`:
    - `@pytest.mark.integration` decorator on the test function.
    - `async def test_collection_bootstrap_idempotent(qdrant_client):`
      1. Compute Qdrant URL from `qdrant_client._client.host` or pass via fixture (the testcontainer URL).
      2. Patch QDRANT_URL env var via `monkeypatch.setenv("QDRANT_URL", url)`.
      3. Import bootstrap as a Python function: `from scripts.qdrant_bootstrap import bootstrap` (may need adding `__init__.py` to scripts/ OR using subprocess; subprocess is acceptable per 05-PATTERNS Test analogs).
      4. Approach A (preferred): subprocess.run([sys.executable, "scripts/qdrant-bootstrap.py", "--qdrant-url", url], check=True) — returns 0.
      5. Fetch collections: `colls = {c.name for c in (await qdrant_client.get_collections()).collections}`; assert `colls == {"sop", "manuals", "troubleshooting", "training"}`.
      6. Verify sop collection config: `info = await qdrant_client.get_collection("sop")`; assert `info.config.params.vectors["dense"].size == 1024`, `info.config.params.vectors["dense"].distance == Distance.COSINE`, sparse vectors present.
      7. Verify payload indexes: `info.payload_schema` contains keys `{"source_uri", "acl_level", "lang", "category", "version", "asset_family", "sop_id"}` (some Qdrant versions expose payload schema differently — fall back to attempting a filter query with each field if direct schema introspection unavailable; cite RESEARCH §1 if needed).
      8. Re-run subprocess.run for bootstrap; assert returncode == 0 (idempotency: no exception even when collections already exist).
      9. Assert collection count unchanged after second run.

    Add `test_payload_indexes_complete` as a second test in same file (also `@pytest.mark.integration`): for each of 7 payload fields, run a dummy `await qdrant_client.query_points(collection_name="sop", query_filter=Filter(must=[FieldCondition(key=field, match=MatchValue(value="dummy"))]), limit=1)` and assert no exception (presence of payload index is implied by successful filter execution without full-scan error).

    Commit: `test(05-04-qdrant-bootstrap): add integration test for idempotent collection bootstrap`.
  </action>
  <acceptance_criteria>
    - `grep -q 'def test_collection_bootstrap_idempotent' packages/sft-knowledge/tests/test_qdrant_indexer.py`
    - `grep -q '@pytest.mark.integration' packages/sft-knowledge/tests/test_qdrant_indexer.py`
    - `grep -vq 'pytestmark = pytest.mark.skip' packages/sft-knowledge/tests/test_qdrant_indexer.py` (skip marker removed for this file's tests written by this plan; later tasks in 05-08 add more tests)
    - `nx run sft-knowledge:test --args="-m integration -k test_collection_bootstrap_idempotent -v"` exits 0
    - `packages/sft-knowledge/tests/conftest.py` contains real `qdrant_client` fixture body (not just stub/skip)
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m integration -k test_collection_bootstrap_idempotent -v"</automated>
  </verify>
  <done>Integration test green via testcontainer Qdrant; 4 collections + 7 payload indexes confirmed; idempotency proven by second-run no-exception.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| script → Qdrant HTTP API | Bootstrap script sends collection-creation commands; trusted localhost in dev, container network in CI |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-04-01 | Tampering | bootstrap idempotency | mitigate | Idempotent CREATE IF NOT EXISTS pattern verified by integration test; re-runs are safe |
| T-05-04-02 | Denial of Service | Qdrant resource limits | accept | Collections are empty until Plan 05-08 indexes; payload indexes pre-created cost is minimal |
| T-05-04-03 | Spoofing | Qdrant client connection | accept | Dev: localhost; CI: testcontainer-isolated network; Phase 11 adds production TLS+auth |
| T-05-04-SC | Tampering | npm/pip install | mitigate | qdrant-client + testcontainers already declared in Plan 05-01 pyproject; both on PyPI Approved per 05-RESEARCH legitimacy audit |
</threat_model>

<verification>
- `uv run python scripts/qdrant-bootstrap.py --dry-run` exits 0
- `nx run sft-knowledge:test --args="-m integration -k test_collection_bootstrap_idempotent -v"` exits 0
- 4 collections + 7 payload indexes verified via testcontainer
- Idempotency proven by second-run success
</verification>

<success_criteria>
- 2 atomic commits: `feat(05-04-qdrant-bootstrap):` + `test(05-04-qdrant-bootstrap):`
- KNW-01 requirement closed
- Plan 05-08 (QdrantIndexer) can rely on collections existing with correct schema
- Plan 05-10 ingest service can invoke `nx run knowledge-ingest:bootstrap` which will shell out to this script
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-04-qdrant-bootstrap-SUMMARY.md` when done with: 4 collection names confirmed, 7 payload index fields, dense vector size, idempotency verification.
</output>
