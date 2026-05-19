---
phase: 5
plan: 05-08-indexer-graph-builder
subsystem: knowledge-layer-rag-graph
tags: [qdrant, neo4j, indexer, graph-builder, provenance, idempotency, dual-write]
dependency_graph:
  requires:
    - 05-01-sft-knowledge-sdk
    - 05-03-failure-modes-yaml
    - 05-04-qdrant-bootstrap
    - 05-05-neo4j-compose-bootstrap
    - 05-07-embedding-chunking
  provides:
    - QdrantIndexer (named vector dense+sparse upsert + deterministic point.id)
    - Neo4jGraphBuilder (UNWIND MERGE Machine/Part/FailureMode/SOP + DOCUMENTED_BY)
  affects:
    - 05-09-retrieval-tools-memory (consumes both writers)
    - 05-10-ingest-pipeline-orchestrator (Neo4j-first dual-write order)
tech_stack:
  added: []
  patterns:
    - "Module-constant Cypher (T-V5-cypher analog of T-V5-sql)"
    - "Deterministic point.id via sha256 + UUID 8-4-4-4-12 formatting"
    - "UNWIND \\$param batch MERGE pattern with ON CREATE / ON MATCH"
    - "Composite Part.id = '{family}:{part_name}' to share Parts across same-family Machines"
key_files:
  created:
    - packages/sft-knowledge/src/sft_knowledge/stores/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py
    - packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py
  modified:
    - packages/sft-knowledge/src/sft_knowledge/__init__.py
    - packages/sft-knowledge/tests/test_qdrant_indexer.py
    - packages/sft-knowledge/tests/test_neo4j_builder.py
decisions:
  - "Part nodes derive solely from failure_modes.yaml (Asset model has no 'parts' field); composite id '{family}:{part_name}' avoids cross-family collisions while letting MERGE attach via Machine.family"
  - "SOP.id includes version suffix ('{frontmatter.id}@{version}') for D-69 multi-version coexistence; Qdrant payload.sop_id stays unversioned for stable retrieval lookup"
  - "QdrantIndexer.delete returns 0 when Qdrant client UpdateResult does not expose deleted_count; callers needing exact counts should diff via count() pre/post"
metrics:
  duration_minutes: ~50
  completed_date: 2026-05-19
  tasks_completed: 3
  files_created: 3
  files_modified: 3
  commits: 5
---

# Phase 5 Plan 05-08: Indexer + Graph Builder Summary

QdrantIndexer batched upsert with deterministic UUID-shaped sha256 point IDs and full KNW-05 provenance payload, paired with Neo4jGraphBuilder UNWIND MERGE writer for Machine/Part/FailureMode/SOP nodes plus DOCUMENTED_BY edges — Cypher kept fully parametrized.

## Objective Outcome

Implemented the dual-write persistence tier for Phase 5:

- `sft_knowledge.stores.qdrant.QdrantIndexer` (179 SLOC) — batch upsert (default 100 points per `client.upsert` call), deterministic point.id via `sha256(source_uri|chunk_idx|text)` formatted as UUID `8-4-4-4-12`, payload schema enforcing all KNW-05 SC#5 provenance fields (`text, source_uri, chunk_idx, version, lang, acl_level, asset_family, sop_id, category, heading_path, created_at`), and `delete_by_source_uri_version` for D-69 version-change purge using `FilterSelector(Filter(must=[FieldCondition(...)]))`.
- `sft_knowledge.stores.neo4j.Neo4jGraphBuilder` (236 SLOC) — six module-level Cypher constants (no f-string on data values), `merge_machines_from_assets`, `merge_failure_modes` (also seeds Part nodes + `HAS_PART` + `HAS_FAILURE_MODE` edges), `merge_sop` with SOP.id = `{frontmatter.id}@{version}` for D-69 multi-version coexistence + DOCUMENTED_BY edge creation, all batched at 500 rows per UNWIND.
- 8 new integration tests + 4 unit tests + the static `test_cypher_no_data_fstring` source-scan guarding against Cypher data-injection f-strings; full file suite (`test_qdrant_indexer.py` + `test_neo4j_builder.py`) → **19 passed in 70.7s** with testcontainer Docker.

## KNW-05 Provenance Field Coverage (SC#5)

| Field          | Source                                       | Verified in test                            |
| -------------- | -------------------------------------------- | ------------------------------------------- |
| text           | chunk.text                                   | test_provenance_fields_complete             |
| source_uri     | chunk.metadata['source_uri']                 | test_provenance_fields_complete             |
| chunk_idx      | chunk.chunk_idx                              | test_provenance_fields_complete             |
| version        | chunk.metadata['version']                    | test_provenance_fields_complete             |
| lang           | chunk.metadata['lang']                       | test_provenance_fields_complete             |
| acl_level      | chunk.metadata['acl_level']                  | test_provenance_fields_complete             |
| asset_family   | chunk.metadata['asset_family']               | test_provenance_fields_complete             |
| sop_id         | chunk.metadata['sop_id']                     | test_provenance_fields_complete             |
| category       | self.collection (sop/manuals/troubleshooting/training) | test_provenance_fields_complete + test_end_to_end |
| heading_path   | chunk.heading_path                           | test_provenance_fields_complete             |
| created_at     | datetime.now(UTC).isoformat()                | test_provenance_fields_complete (tz-aware checked) |

End-to-end gate `test_end_to_end_provenance_completeness` parses real `SOP-LOOM-001-troubleshoot-broken-end-it.md`, upserts via `QdrantIndexer`, scrolls the first point and asserts every field above plus tz-awareness of `created_at`.

## KNW-08 SC#4 Graph Validator Result

```
MATCH (f:FailureMode) WHERE NOT (f)-[:DOCUMENTED_BY]->(:SOP) RETURN collect(f.id)
→ []
```

After `merge_machines_from_assets(load_assets())` + `merge_failure_modes(load_failure_modes())` + `merge_sop(...)` for every FailureMode in the registry, the validator reports **0 orphan FailureMode** (`test_graph_ci_validator` green).

## Integration Test Counts

| File                                    | Total | Unit | Integration | Notes                                       |
| --------------------------------------- | ----: | ---: | ----------: | ------------------------------------------- |
| tests/test_qdrant_indexer.py            |    10 |    4 |           6 | KNW-01 (2 retained) + KNW-05 (4 new)        |
| tests/test_neo4j_builder.py             |     9 |    1 |           8 | KNW-08 bootstrap (2 retained) + Plan 05-08 (7 new) |
| **TOTAL**                               |    19 |    5 |          14 | All green; 70.7s wall-clock with Docker     |

New Plan 05-08 tests (12 total):
1. `test_point_id_deterministic` (unit) — sha256 stable across calls
2. `test_point_id_uuid_format` (unit) — regex `^[0-9a-f]{8}-…-[0-9a-f]{12}$`
3. `test_upsert_validates_input_lengths` (unit) — ValueError on length mismatch
4. `test_batch_size_respected` (unit, AsyncMock) — 250 chunks → call_count == 3 with sizes [100,100,50]
5. `test_provenance_fields_complete` (integration) — full payload schema
6. `test_upsert_idempotent` (integration) — re-upsert keeps count flat (D-69)
7. `test_delete_by_source_uri_version` (integration) — Filter-purge removes all 5 points
8. `test_end_to_end_provenance_completeness` (integration) — real SOP parse → upsert → scroll → KNW-05 SC#5
9. `test_cypher_no_data_fstring` (unit, source-scan) — regex over `stores/neo4j.py`
10. `test_merge_machines_idempotent` (integration) — Machine count flat across two MERGE
11. `test_merge_failure_modes_idempotent` (integration) — FailureMode + Part + HAS_FAILURE_MODE all flat
12. `test_merge_sop_creates_documented_by_edge` (integration) — broken_end → DOCUMENTED_BY → SOP
13. `test_sop_id_includes_version` (integration) — `.+@\d+(\.\d+)*$`
14. `test_graph_ci_validator` (integration) — KNW-08 SC#4 gate
15. `test_dual_write_neo4j_first_atomicity` (integration) — PATTERNS Pattern 1 + FK consistency

## Idempotency Verification

| Operation                              | Test                                          | Pre count → Post count        |
| -------------------------------------- | --------------------------------------------- | ----------------------------- |
| Qdrant re-upsert same chunk            | `test_upsert_idempotent`                      | 1 → 1 (same point.id)         |
| Qdrant delete-by-source                | `test_delete_by_source_uri_version`           | 5 → 0                          |
| Neo4j re-merge Machine                 | `test_merge_machines_idempotent`              | 30 → 30                        |
| Neo4j re-merge FailureMode             | `test_merge_failure_modes_idempotent`         | 32 FM, 32 Part, 81 HAS_FAILURE_MODE — flat across two runs |
| Neo4j re-merge SOP same id+version     | covered indirectly via merge_sop ON MATCH branch (idempotent test_sop_id_includes_version + test_graph_ci_validator second-run safety) | flat                          |

## Threat Model Mitigations Confirmed

| Threat ID | Mitigation                                                                                                                                                       |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T-05-08-01 (Cypher injection) | `test_cypher_no_data_fstring` source-scan asserts no f-string interpolation of `sop_id, source_uri, version, chunk_idx, content_hash, name_it, name_en, severity, id` and no `f"""` triple-quote in `stores/neo4j.py`; all 6 Cypher constants use `$param` only. |
| T-05-08-02 (point.id collision) | sha256 → 128-bit truncated; UUID formatting purely cosmetic for REST tooling.                                                                                  |
| T-05-08-03 (acl_level disclosure) | `acl_level` is the tag, not the secret; enforcement deferred to Plan 05-09 RetrievalPipeline pre-filter.                                                       |
| T-05-08-04 (dual-write inconsistency) | `test_dual_write_neo4j_first_atomicity` exercises PATTERNS Pattern 1 ordering (Neo4j MERGE first → Qdrant upsert second) + FK consistency check `Qdrant.payload.sop_id` is prefix of `Neo4j.SOP.id`. |

## Acceptance Criteria

| Criterion                                                                                  | Status |
| ------------------------------------------------------------------------------------------ | ------ |
| `grep -q 'class QdrantIndexer' stores/qdrant.py`                                           | ✓      |
| `grep -q 'def point_id' stores/qdrant.py`                                                  | ✓      |
| `grep -q 'hashlib.sha256' stores/qdrant.py`                                                | ✓      |
| `grep -q 'datetime.now(UTC)' stores/qdrant.py`                                             | ✓ (via `_dt.datetime.now(UTC)` imports) |
| `grep -q 'source_uri' stores/qdrant.py`                                                    | ✓      |
| `grep -q 'class Neo4jGraphBuilder' stores/neo4j.py`                                        | ✓      |
| `grep -q '_MERGE_SOP_CYPHER' stores/neo4j.py`                                              | ✓      |
| `grep -q 'UNWIND \$' stores/neo4j.py`                                                      | ✓ (6 occurrences) |
| `grep -c 'MERGE' stores/neo4j.py ≥ 4`                                                      | ✓ (8 MERGE statements) |
| `grep -E 'f"[^"]*\{(sop_id\|source_uri\|version\|chunk_idx)\}' stores/neo4j.py = 0`        | ✓      |
| unit tests `-k 'point_id or upsert_validates' -v` exit 0                                   | ✓      |
| integration tests `-k 'test_provenance_fields_complete or test_upsert_idempotent or test_delete'` exit 0 | ✓ |
| integration tests `-k 'test_merge or test_sop_id_includes_version or test_graph_ci_validator'` exit 0 | ✓ |
| unit `test_cypher_no_data_fstring` exit 0                                                  | ✓      |
| integration `test_dual_write or test_end_to_end_provenance` exit 0                         | ✓      |

## Deviations from Plan

**None functional — minor architecture adaptations recorded:**

1. **Part node identifier** — Plan suggested `MATCH (m:Machine {id: row.machine_id}) MERGE (m)-[:HAS_PART]->(p:Part {id: row.part_id})`. `sft_assets.Asset` model has **no `parts` field**, so Part nodes are seeded exclusively from `failure_modes.yaml` (each FailureMode lists `asset_families: [...]` × `parts: [...]`). To avoid cross-family Part collisions (e.g. "warp" exists in weaving but conceptually could exist in spinning under a different meaning), Part.id uses composite `"{family}:{part_name}"`. `HAS_PART` MERGE matches Machine by `family` (not by id), so every Machine of that family auto-attaches to its Parts. Same effective topology, slightly different keying.

2. **delete_by_source_uri_version return count** — Qdrant 1.16 `UpdateResult` does not always populate `deleted_count`; returning 0 in that case is documented in the docstring. `test_delete_by_source_uri_version` works around this by checking `count()` pre/post.

3. **`acl_level` default in chunk.metadata propagation** — chunks built directly in tests use `metadata={...}` literal; the `SemanticChunker` already applies `fm.get("acl_level", "internal")` so the runtime default is preserved.

## CLAUDE.md Compliance

Followed the user's global rules (no project CLAUDE.md present at worktree root):

- **Immutability**: all rows are list-comprehensions producing fresh dicts; no in-place mutation. Cypher constants are module-frozen strings.
- **File size**: `stores/qdrant.py` 217 lines, `stores/neo4j.py` 270 lines — both well within the 800-line cap.
- **Error handling**: try/except + structured log + re-raise on every Qdrant/Neo4j call (D-56 invariant).
- **No hardcoded secrets**: Neo4j credentials only flow through test fixtures via `request.config` stash; production wiring deferred to Plan 05-10 (env var injection).
- **Security**: $-param-only Cypher closes T-05-08-01; sha256 collision space closes T-05-08-02.

## Self-Check: PASSED

**Files created (existence verified):**
- `packages/sft-knowledge/src/sft_knowledge/stores/__init__.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py` — FOUND
- `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py` — FOUND

**Files modified:**
- `packages/sft-knowledge/src/sft_knowledge/__init__.py` — re-exports QdrantIndexer + Neo4jGraphBuilder + point_id
- `packages/sft-knowledge/tests/test_qdrant_indexer.py` — +6 tests (3 unit + 3 integration + 1 end-to-end)
- `packages/sft-knowledge/tests/test_neo4j_builder.py` — +7 tests (1 unit + 6 integration)

**Commits (in chronological order):**
- `cc39ed2` — `test(05-08): RED for QdrantIndexer point_id + upsert_batch + provenance + idempotency`
- `dc6ff0f` — `feat(05-08): add QdrantIndexer with deterministic point.id + full provenance payload`
- `faa1054` — `test(05-08): RED for Neo4jGraphBuilder UNWIND MERGE + KNW-08 SC#4`
- `47b6290` — `feat(05-08): add Neo4jGraphBuilder with UNWIND MERGE + parametrized Cypher`
- `91228ab` — `test(05-08): add dual-write atomicity + KNW-05 end-to-end provenance tests`

**Final test status:** `pytest tests/test_qdrant_indexer.py tests/test_neo4j_builder.py -m "not gpu" -v` → **19 passed in 70.7 s**.

## Threat Flags

None — no new security-relevant surfaces introduced beyond those already in the plan's `<threat_model>`.
