---
plan_id: 05-08-indexer-graph-builder
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 3
depends_on: [05-01-sft-knowledge-sdk, 05-04-qdrant-bootstrap, 05-05-neo4j-compose-bootstrap, 05-07-embedding-chunking, 05-03-failure-modes-yaml]
requirements: [KNW-05, KNW-08]
files_modified:
  - packages/sft-knowledge/src/sft_knowledge/stores/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py
  - packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py
  - packages/sft-knowledge/src/sft_knowledge/__init__.py
  - packages/sft-knowledge/tests/test_qdrant_indexer.py
  - packages/sft-knowledge/tests/test_neo4j_builder.py
autonomous: true
estimated_atomic_commits: 3
must_haves:
  truths:
    - "QdrantIndexer.upsert_batch(points) writes to named-vector dense+sparse collection in batches of 100 (D-69 + claudes_discretion)"
    - "point.id = sha256(source_uri + '|' + chunk_idx + '|' + text) → UUID-formatted hex string per RESEARCH §9"
    - "Every upserted point payload includes source_uri, chunk_idx, version, lang, acl_level, asset_family, sop_id, category, heading_path, created_at (KNW-05 SC#5)"
    - "Neo4jGraphBuilder.merge_sop(parsed_doc) writes SOP node + DOCUMENTED_BY edge from FailureMode using UNWIND + parametrized Cypher only (D-65)"
    - "Re-running merge_sop with same data is idempotent (MERGE pattern; no duplicate nodes/edges)"
    - "test_provenance_fields_complete asserts all KNW-05 fields present in upserted Qdrant points"
    - "test_graph_ci_validator asserts every FailureMode has ≥1 DOCUMENTED_BY edge to SOP (SC#4)"
  artifacts:
    - path: packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py
      provides: QdrantIndexer with batch upsert + deterministic point.id + payload schema validation
    - path: packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py
      provides: Neo4jGraphBuilder with UNWIND MERGE batches (size 500) + parametrized Cypher only
  key_links:
    - from: packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py
      to: Qdrant query_points
      via: PointStruct.id deterministic sha256 UUID-formatted
      pattern: "hashlib\\.sha256|PointStruct"
    - from: packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py
      to: Neo4j MERGE SOP + DOCUMENTED_BY
      via: UNWIND $sop_rows + parametrized session.run
      pattern: "UNWIND \\$|MERGE.*SOP"
---

<objective>
Implement the persistence layer: `QdrantIndexer` (batch upsert with deterministic point IDs + full provenance payload) and `Neo4jGraphBuilder` (deterministic UNWIND MERGE pattern for Machine/Part/FailureMode/SOP nodes + DOCUMENTED_BY edges from `sft-assets` and `failure_modes.yaml`).

Purpose: this is the dual-write tier of D-61 + D-65. Plan 05-10 ingest pipeline orchestrator calls both writers in Neo4j-first order (PATTERNS.md Pattern 1 — atomicity). KNW-05 (provenance) + KNW-08 (graph traversal returns valid SOP, SC#4) close here.

Output: two store modules with green integration tests covering provenance completeness + idempotent re-write + graph CI validator.
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
@packages/sft-knowledge/src/sft_knowledge/parsers/base.py
@packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py
@packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
@packages/sft-knowledge/src/sft_knowledge/models.py
@packages/sft-domain/src/sft_domain/failure_modes/_loader.py
@packages/sft-assets/src/sft_assets/_loader.py
@services/ot-bridge/src/svc_ot_bridge/timescale_writer.py
@packages/sft-agents/src/sft_agents/audit/pg_writer.py
</context>

<interfaces>
QdrantIndexer API (D-61 + D-69):

```
class QdrantIndexer:
    def __init__(self, client: AsyncQdrantClient, collection: str, batch_size: int = 100):
        ...

    @staticmethod
    def point_id(source_uri: str, chunk_idx: int, text: str) -> str:
        # sha256("{source_uri}|{chunk_idx}|{text}").hexdigest()[:32]
        # → UUID-formatted: "8-4-4-4-12" hex sections
        ...

    async def upsert_batch(self, chunks: list[Chunk], dense_vecs: list[np.ndarray], sparse_vecs: list[SparseVector]) -> int:
        # Build PointStruct list with id = point_id(), vector={"dense": dense_vec, "sparse": sparse_vec},
        # payload = chunks[i].metadata + chunk_idx + text + heading_path + created_at (datetime.now(UTC))
        # Flush in batches of self.batch_size (default 100 per claudes_discretion)
        # Returns total upserted count
        ...

    async def delete_by_source_uri_version(self, source_uri: str, version: str) -> int:
        # For version-change purge (D-69 second half)
        ...
```

Payload schema (D-61 LOCKED — must be COMPLETE per KNW-05):
- text (chunk content)
- source_uri
- chunk_idx
- version
- lang
- acl_level
- asset_family
- asset (optional)
- category (one of "sop","manuals","troubleshooting","training")
- heading_path (list[str])
- related_glossary (list[str], optional from frontmatter)
- created_at (ISO datetime UTC)
- sop_id

Point ID format (D-69 + RESEARCH §9 + Risk 6):
```
raw = hashlib.sha256(f"{source_uri}|{chunk_idx}|{text}".encode()).hexdigest()
h = raw[:32]
point_id = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"  # UUID-shaped string
```

Neo4jGraphBuilder API (D-65):

```
class Neo4jGraphBuilder:
    def __init__(self, driver: AsyncDriver, batch_size: int = 500):
        ...

    async def merge_machines_from_assets(self, assets: tuple[Asset, ...]) -> int:
        # UNWIND $machine_rows MERGE (m:Machine {id: row.machine_id}) ...
        # MERGE (m)-[:HAS_PART]->(p:Part {id: row.part_id})
        # NOTE: Asset model in sft-assets has different field names; map carefully.
        ...

    async def merge_failure_modes(self, fms: tuple[FailureMode, ...]) -> int:
        # UNWIND $fm_rows MERGE (f:FailureMode {id: row.id})
        # ON CREATE SET f.name_it = row.name_it, ...
        # For each fm.parts: MATCH (p:Part {id: part_id}) MERGE (p)-[:HAS_FAILURE_MODE]->(f)
        ...

    async def merge_sop(self, parsed_doc: ParsedDoc, failure_mode_ids: list[str]) -> int:
        # SOP.id format: f"{parsed_doc.frontmatter['id']}@{parsed_doc.version}" (D-69 multi-version coexistence)
        # UNWIND $sop_rows MERGE (s:SOP {id: row.sop_id})
        # For each fm_id in failure_mode_ids: MATCH (f:FailureMode {id: fm_id}) MERGE (f)-[:DOCUMENTED_BY]->(s)
        ...
```

Cypher constants (Shared Pattern 4 — module-level, $-param only, Literal-whitelisted labels):
```
_MERGE_SOP_CYPHER = """
UNWIND $sop_rows AS row
MERGE (s:SOP {id: row.sop_id})
  ON CREATE SET s.version = row.version, s.lang = row.lang,
                s.title = row.title, s.created_at = datetime()
  ON MATCH SET  s.version = row.version, s.updated_at = datetime()
"""

_LINK_FAILURE_MODE_TO_SOP = """
UNWIND $link_rows AS row
MATCH (f:FailureMode {id: row.failure_mode_id})
MATCH (s:SOP {id: row.sop_id})
MERGE (f)-[r:DOCUMENTED_BY]->(s)
  ON CREATE SET r.created_at = datetime()
"""
```

failure_mode_ids inference for a SOP: look at parsed_doc.frontmatter `tags`, `related_glossary`, and asset_family — match against FailureMode.id/name_it/name_en (case-insensitive substring) (same heuristic as validate-failure-modes.py from Plan 05-03 Task 2). The pipeline orchestrator (Plan 05-10) constructs the failure_mode_ids list; Neo4jGraphBuilder.merge_sop accepts it as a parameter (separation of concerns).

Phase 3 sft-assets integration: import `from sft_assets import load_assets`; Asset has fields the executor MUST inspect by reading `packages/sft-assets/src/sft_assets/models.py`. Map Asset → Neo4j Machine node with id=asset.asset_id (or whatever the registry key is — confirm during read_first).
</interfaces>

<tasks>

<task id="05-08-01" type="auto" tdd="true">
  <name>Task 1: QdrantIndexer with deterministic point.id + payload provenance + batch upsert</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/stores/__init__.py,
    packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py,
    packages/sft-knowledge/tests/test_qdrant_indexer.py
  </files>
  <read_first>
    services/ot-bridge/src/svc_ot_bridge/timescale_writer.py (module-constant SQL pattern lines 28-34, batch flush pattern lines 92-101),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-61 PointStruct schema lines 106-129; D-69 point.id format lines 487-507),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §1 (Qdrant Query API + payload structure) + §9 (point ID format Risk 6),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (stores/qdrant.py section lines 309-358),
    packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py (Chunk schema from Plan 05-07)
  </read_first>
  <behavior>
    - `point_id(source_uri, chunk_idx, text)` is pure deterministic: same inputs → same output
    - Output is UUID-formatted hex string (32 hex chars in 8-4-4-4-12 format) per RESEARCH §9 Risk 6 mitigation
    - `upsert_batch(chunks, dense_vecs, sparse_vecs)`:
      - Validates len(chunks) == len(dense_vecs) == len(sparse_vecs); raises ValueError otherwise
      - Each point payload merges chunks[i].metadata + adds chunk_idx + text + heading_path + created_at (datetime.now(UTC).isoformat()) + category (inferred from collection name)
      - Returns total upserted count (sum across batches)
      - Flushes in batches of self.batch_size (default 100) via async client.upsert
      - On batch error: log + re-raise (D-56 invariant)
    - `delete_by_source_uri_version(source_uri, version)`: uses Qdrant Filter(must=[source_uri match, version match]) → client.delete(collection, points_selector=...); returns delete count
    - test_point_id_deterministic: same inputs → identical UUID string (unit test, no infra)
    - test_point_id_uuid_format: returned string matches regex `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`
    - test_upsert_validates_input_lengths: mismatched list lengths → ValueError
    - test_provenance_fields_complete (integration, testcontainer Qdrant): index a Chunk with full metadata via real BgeM3Embedder (or mock dense+sparse); fetch the point; assert payload contains every required field (KNW-05 SC#5)
    - test_upsert_idempotent (integration): upsert same chunk twice → collection point count increments by 1 (first call), 0 (second call) — same point.id deduplicates at Qdrant level
    - test_batch_size_respected: upsert 250 chunks → exactly 3 batches (100, 100, 50); verify via mock client call count
    - test_delete_by_source_uri_version (integration): upsert 5 points → delete by source_uri+version → 0 points remain
  </behavior>
  <action>
    Create `packages/sft-knowledge/src/sft_knowledge/stores/__init__.py` re-exporting `QdrantIndexer, Neo4jGraphBuilder`.

    Create `packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py`:
    - `from __future__ import annotations`, `import hashlib`, `from datetime import datetime, timezone`, `import structlog`
    - `import numpy as np` (or `from typing import Any` if numpy is heavy at module load)
    - `UTC = timezone.utc`
    - Module constants:
      - `_COLLECTIONS: frozenset[str] = frozenset({"sop", "manuals", "troubleshooting", "training"})`
      - `_DEFAULT_BATCH_SIZE: int = 100`
    - Function `point_id(source_uri: str, chunk_idx: int, text: str) -> str`:
      - `raw = hashlib.sha256(f"{source_uri}|{chunk_idx}|{text}".encode("utf-8")).hexdigest()`
      - `h = raw[:32]`
      - return `f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"`
    - `class QdrantIndexer`:
      - `def __init__(self, client, collection: str, batch_size: int = _DEFAULT_BATCH_SIZE) -> None`: validate collection in _COLLECTIONS; store; logger via structlog.
      - `async def upsert_batch(self, chunks, dense_vecs, sparse_vecs) -> int`:
        - Validate equal lengths.
        - Build list[PointStruct]: for i, c in enumerate(chunks): build payload = `{**c.metadata, "text": c.text, "chunk_idx": c.chunk_idx, "heading_path": c.heading_path, "category": self.collection, "created_at": datetime.now(UTC).isoformat()}`; vector dict `{"dense": dense_vecs[i].tolist() if hasattr(dense_vecs[i], "tolist") else list(dense_vecs[i]), "sparse": sparse_vecs[i]}`; id via `point_id(...)`.
        - Flush in batches: `for i in range(0, len(points), self.batch_size): await self._client.upsert(collection_name=self.collection, points=points[i:i+self.batch_size])`.
        - try/except: log "qdrant_upsert_failed" + re-raise.
        - Return total count.
      - `async def delete_by_source_uri_version(self, source_uri: str, version: str) -> int`:
        - Build Filter via qdrant_client.http.models: `Filter(must=[FieldCondition(key="source_uri", match=MatchValue(value=source_uri)), FieldCondition(key="version", match=MatchValue(value=version))])`.
        - `await self._client.delete(collection_name=self.collection, points_selector=FilterSelector(filter=filter))` (verify exact API in qdrant-client 1.16+).
        - Return delete operation result count.

    Add tests to `packages/sft-knowledge/tests/test_qdrant_indexer.py` (this file already has the Plan 05-04 bootstrap test; ADD new tests in same file):
    - 3 unit tests (no marker): test_point_id_deterministic, test_point_id_uuid_format, test_upsert_validates_input_lengths.
    - 4 integration tests (`@pytest.mark.integration`): test_provenance_fields_complete, test_upsert_idempotent, test_batch_size_respected (may be unit if using mock client), test_delete_by_source_uri_version.
    - For integration tests: use existing `qdrant_client` fixture from Plan 05-04 conftest.py. Call `scripts/qdrant-bootstrap.py` once at test session start (or fixture-level) to ensure collections exist.

    Update `packages/sft-knowledge/src/sft_knowledge/__init__.py` to re-export `QdrantIndexer`.

    Commit: `feat(05-08-indexer-graph-builder): add QdrantIndexer with deterministic point.id + full provenance payload`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class QdrantIndexer' packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py`
    - `grep -q 'def point_id' packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py`
    - `grep -q 'hashlib.sha256' packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py`
    - `grep -q 'datetime.now(UTC)' packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py`
    - `grep -q 'source_uri' packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py` (provenance)
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k 'point_id or upsert_validates' -v"` exits 0 (unit tests)
    - `nx run sft-knowledge:test --args="-m integration -k 'test_provenance_fields_complete or test_upsert_idempotent or test_delete' -v"` exits 0 (integration tests)
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m integration -k 'test_provenance_fields_complete or test_upsert_idempotent' -v"</automated>
  </verify>
  <done>QdrantIndexer + 7 tests committed; KNW-05 provenance + D-69 idempotency verified via testcontainer.</done>
</task>

<task id="05-08-02" type="auto" tdd="true">
  <name>Task 2: Neo4jGraphBuilder with UNWIND MERGE + parametrized Cypher + sft-assets/failure-modes seed</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py,
    packages/sft-knowledge/tests/test_neo4j_builder.py
  </files>
  <read_first>
    packages/sft-agents/src/sft_agents/audit/pg_writer.py (module-constant pattern lines 36-44; pool acquire pattern lines 87-115; re-raise on error),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-65 schema + MERGE pattern lines 249-267; D-69 SOP.id = "{sop_id}@{version}"),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §5 (UNWIND MERGE pattern + injection defense + Open Question 2 SOP.id format),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (stores/neo4j.py section lines 361-407 + Shared Pattern 4 parametrized Cypher),
    packages/sft-assets/src/sft_assets/_loader.py (load_assets API + Asset model field names),
    packages/sft-domain/src/sft_domain/failure_modes/_loader.py (just from Plan 05-03)
  </read_first>
  <behavior>
    - All Cypher statements stored as module-level CONSTANTS (zero f-string in data path)
    - Labels (Machine, Part, FailureMode, SOP) used in f-string only for label slot AFTER Pydantic Literal whitelist validation in Plan 05-09 tools; in stores/neo4j.py labels are fixed strings (no user input)
    - Property values use `$param` placeholders only (T-V5-sql Cypher analog)
    - `merge_machines_from_assets(assets)`: UNWIND batches of size ≤500, MERGE Machine + Part nodes + HAS_PART edges; idempotent
    - `merge_failure_modes(fms)`: UNWIND batches, MERGE FailureMode + HAS_FAILURE_MODE edges to existing Parts
    - `merge_sop(parsed_doc, failure_mode_ids)`: SOP.id = f"{frontmatter['id']}@{version}" (D-69 multi-version coexistence per RESEARCH §5 Open Q2); UNWIND single-row batch MERGE SOP + DOCUMENTED_BY edge from each failure_mode_id; idempotent
    - test_merge_machines_idempotent (integration): merge_machines_from_assets twice → 30 Machine nodes total (sft-assets count), 30 after second call (not 60)
    - test_merge_failure_modes_idempotent (integration): merge_failure_modes twice → N FailureMode nodes, no duplicates
    - test_merge_sop_creates_documented_by_edge (integration): merge_sop with failure_mode_ids=["broken_end"] → query `MATCH (f:FailureMode {id:'broken_end'})-[:DOCUMENTED_BY]->(s:SOP) RETURN count(s)` returns ≥1
    - test_sop_id_includes_version (integration): merge_sop → query `MATCH (s:SOP) RETURN s.id` matches pattern `.*@\d+\.\d+`
    - test_graph_ci_validator (integration, SC#4): after merge_machines + merge_failure_modes + merge_sop for sample SOPs → run validator Cypher `MATCH (f:FailureMode) WHERE NOT (f)-[:DOCUMENTED_BY]->(:SOP) RETURN f.id` returns empty list
    - test_cypher_no_data_fstring (unit, source-scan): import the module text; assert no Python f-string with `{var_for_data}` patterns interpolating property values (only labels/relations may be f-string)
  </behavior>
  <action>
    Create `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py`:
    - `from __future__ import annotations`, `import structlog`, `from typing import Any`
    - `from sft_knowledge.parsers.base import ParsedDoc`
    - Module-level Cypher constants (verbatim from PATTERNS.md stores/neo4j.py section + adapt for parts/machines):
      - `_MERGE_MACHINE_CYPHER` = UNWIND $machine_rows AS row MERGE (m:Machine {id: row.id}) ON CREATE SET m.family=row.family, m.name_it=row.name_it, m.name_en=row.name_en, m.created_at=datetime() ON MATCH SET m.updated_at=datetime()
      - `_MERGE_PART_AND_LINK_CYPHER` = UNWIND $part_rows AS row MERGE (p:Part {id: row.id}) ON CREATE SET p.name=row.name WITH p, row MATCH (m:Machine {id: row.machine_id}) MERGE (m)-[:HAS_PART]->(p)
      - `_MERGE_FAILURE_MODE_CYPHER` = UNWIND $fm_rows AS row MERGE (f:FailureMode {id: row.id}) ON CREATE SET f.name_it=row.name_it, f.name_en=row.name_en, f.severity=row.severity, f.created_at=datetime() ON MATCH SET f.updated_at=datetime()
      - `_LINK_PART_TO_FAILURE_MODE` = UNWIND $link_rows AS row MATCH (p:Part {id: row.part_id}) MATCH (f:FailureMode {id: row.failure_mode_id}) MERGE (p)-[:HAS_FAILURE_MODE]->(f)
      - `_MERGE_SOP_CYPHER` (per PATTERNS.md stores/neo4j.py section lines 379-388) — exact text
      - `_LINK_FAILURE_MODE_TO_SOP_CYPHER` = UNWIND $link_rows AS row MATCH (f:FailureMode {id: row.failure_mode_id}) MATCH (s:SOP {id: row.sop_id}) MERGE (f)-[r:DOCUMENTED_BY]->(s) ON CREATE SET r.created_at=datetime()

    - `class Neo4jGraphBuilder`:
      - `def __init__(self, driver, batch_size: int = 500) -> None`: store driver + logger via structlog
      - `async def merge_machines_from_assets(self, assets) -> int`:
        - Build machine_rows: `[{"id": a.asset_id, "family": a.family, "name_it": getattr(a, "name_it", a.asset_id), "name_en": getattr(a, "name_en", a.asset_id)} for a in assets]` (verify Asset field names against packages/sft-assets/src/sft_assets/models.py).
        - For each batch of ≤500: `await session.run(_MERGE_MACHINE_CYPHER, machine_rows=batch)`.
        - Also derive part_rows from sft-assets (Asset.parts if exists, else skip parts seeding); MERGE parts + HAS_PART edges via _MERGE_PART_AND_LINK_CYPHER.
        - Return count of merged rows.
      - `async def merge_failure_modes(self, fms) -> int`:
        - Build fm_rows: `[{"id": f.id, "name_it": f.name_it, "name_en": f.name_en, "severity": f.severity} for f in fms]`.
        - For each batch: `await session.run(_MERGE_FAILURE_MODE_CYPHER, fm_rows=batch)`.
        - Build link_rows for each fm.parts → (part_id, failure_mode_id): `await session.run(_LINK_PART_TO_FAILURE_MODE, link_rows=...)`.
        - Return count.
      - `async def merge_sop(self, parsed_doc: ParsedDoc, failure_mode_ids: list[str]) -> int`:
        - sop_id = f"{parsed_doc.frontmatter['id']}@{parsed_doc.version}" (D-69 multi-version).
        - sop_rows = [{"sop_id": sop_id, "version": parsed_doc.version, "lang": parsed_doc.lang, "title": str(parsed_doc.frontmatter.get("title", ""))}].
        - `await session.run(_MERGE_SOP_CYPHER, sop_rows=sop_rows)`.
        - If failure_mode_ids: link_rows = [{"failure_mode_id": fm_id, "sop_id": sop_id} for fm_id in failure_mode_ids]; `await session.run(_LINK_FAILURE_MODE_TO_SOP_CYPHER, link_rows=link_rows)`.
        - Return 1 (or len(link_rows)+1 to count edges).
      - All methods use `async with self._driver.session(database="neo4j") as session:` per RESEARCH §5.
      - On exception: log + re-raise.

    Update `packages/sft-knowledge/tests/test_neo4j_builder.py` (this file has Plan 05-05 constraints test; ADD new tests):
    - 6 tests from `<behavior>` plus the new `test_graph_ci_validator` integration test which is the formal KNW-08 SC#4 gate.
    - For integration tests: use `neo4j_driver` fixture from Plan 05-05 conftest.py. Run `scripts/neo4j-bootstrap.py` against the testcontainer driver to apply constraints before tests.
    - For test_cypher_no_data_fstring (unit, source scan): open the .py file, read source, regex-check that NO f-string contains a data property reference (e.g., no `f"... {sop_id} ..."` where sop_id is a function argument). Labels in f-string are acceptable (Literal-validated). The scan can be: `grep -E 'f".*\{(sop_id|source_uri|content_hash|version|chunk_idx)\}'` returns 0 matches.

    Update `packages/sft-knowledge/src/sft_knowledge/__init__.py` to re-export `Neo4jGraphBuilder`.

    Commit: `feat(05-08-indexer-graph-builder): add Neo4jGraphBuilder with UNWIND MERGE + parametrized Cypher`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class Neo4jGraphBuilder' packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py`
    - `grep -q '_MERGE_SOP_CYPHER' packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py`
    - `grep -q 'UNWIND \$' packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py` (parametrized batches)
    - `grep -c 'MERGE' packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py` returns ≥4 (Machine, Part, FailureMode, SOP, edges)
    - `grep -E 'f"[^"]*\\{(sop_id|source_uri|version|chunk_idx)\\}' packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py | wc -l` returns 0 (data values never in f-string)
    - `nx run sft-knowledge:test --args="-m integration -k 'test_merge or test_sop_id_includes_version or test_graph_ci_validator' -v"` exits 0
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_cypher_no_data_fstring -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m integration -k 'test_graph_ci_validator' -v"</automated>
  </verify>
  <done>Neo4jGraphBuilder + 6 tests committed; KNW-08 SC#4 graph CI validator green; zero data-f-string Cypher verified.</done>
</task>

<task id="05-08-03" type="auto" tdd="true">
  <name>Task 3: Dual-write atomicity test — Neo4j-first + Qdrant second + KNW-05 end-to-end provenance</name>
  <files>
    packages/sft-knowledge/tests/test_qdrant_indexer.py,
    packages/sft-knowledge/tests/test_neo4j_builder.py
  </files>
  <read_first>
    packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py (just from Task 1),
    packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py (just from Task 2),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (Pattern 1 Dual-Write Atomicity lines 810-829),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (KNW-05 row + KNW-08 SC#4 row)
  </read_first>
  <behavior>
    - test_dual_write_neo4j_first_atomicity (integration, testcontainer Qdrant+Neo4j):
      1. merge_machines_from_assets → merge_failure_modes → merge_sop (Neo4j first per PATTERNS.md Pattern 1)
      2. Generate chunks for the same parsed_doc + dense+sparse vecs (use mock embeddings to keep test fast — np.zeros(1024) + empty SparseVector)
      3. QdrantIndexer.upsert_batch
      4. Assert Qdrant point.sop_id payload matches Neo4j SOP.id (FK consistency)
    - test_end_to_end_provenance_completeness (integration, KNW-05 SC):
      1. Parse a real SOP → chunk → mock-embed (deterministic dense+sparse) → upsert.
      2. Query Qdrant `query_points(collection="sop", limit=1)` → first hit.
      3. Assert hit.payload has every KNW-05 field present: `source_uri, chunk_idx, version, lang, acl_level, asset_family, sop_id, category, heading_path, created_at`.
      4. Assert all values are non-empty (no empty strings) except possibly `asset` and `related_glossary` which can be empty/missing.
      5. Assert created_at is parseable as ISO datetime with timezone info (tz-aware per Shared Pattern 2).
  </behavior>
  <action>
    Add `test_dual_write_neo4j_first_atomicity` to `packages/sft-knowledge/tests/test_neo4j_builder.py` (integration). It depends on both `qdrant_client` and `neo4j_driver` fixtures.

    Add `test_end_to_end_provenance_completeness` to `packages/sft-knowledge/tests/test_qdrant_indexer.py` (integration). Steps:
    1. Use real `MarkdownParser` on a small reviewed SOP (e.g., `simulators/synthetic-corpus/it/loom/SOP-LOOM-001-*.md` — pick deterministically).
    2. Use real `SemanticChunker` with embed model patched to a fast stub OR use a fake `Chunk` list constructed directly (no need for real semantic split in this test — focus is provenance).
    3. Construct dense_vecs and sparse_vecs as zero-filled placeholders (np.zeros(1024); SparseVector(indices=[1], values=[0.0])).
    4. Run scripts/qdrant-bootstrap.py to ensure collection exists (or rely on session-scoped fixture having done it).
    5. `await indexer.upsert_batch(chunks, dense_vecs, sparse_vecs)`.
    6. `points = await qdrant_client.query_points(collection_name="sop", limit=1)`.
    7. Assert payload has every KNW-05 field (use explicit list); assert created_at is parseable; assert sop_id non-empty.

    Commit: `test(05-08-indexer-graph-builder): add dual-write atomicity + KNW-05 end-to-end provenance tests`.
  </action>
  <acceptance_criteria>
    - `grep -q 'def test_dual_write_neo4j_first_atomicity' packages/sft-knowledge/tests/test_neo4j_builder.py`
    - `grep -q 'def test_end_to_end_provenance_completeness' packages/sft-knowledge/tests/test_qdrant_indexer.py`
    - `nx run sft-knowledge:test --args="-m integration -k 'test_dual_write or test_end_to_end_provenance' -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m integration -k 'test_end_to_end_provenance_completeness' -v"</automated>
  </verify>
  <done>Both dual-write atomicity + end-to-end provenance integration tests green; KNW-05 SC#5 + KNW-08 SC#4 explicitly verified.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| QdrantIndexer → Qdrant API | All data passes through typed Python models (PointStruct, Filter, FieldCondition); no string SQL/JSON injection surface |
| Neo4jGraphBuilder → Neo4j Bolt | Cypher uses $param placeholders only; labels are fixed strings (or Literal-whitelisted in Plan 05-09 tools) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-08-01 | Tampering (Cypher injection) | Neo4jGraphBuilder | mitigate | All data values via `$param`; module-constant Cypher; unit test `test_cypher_no_data_fstring` blocks f-string data paths |
| T-05-08-02 | Tampering | Qdrant point.id collisions | mitigate | sha256(source_uri+chunk_idx+text) collision probability ~2^-128; deterministic + auditable |
| T-05-08-03 | Information Disclosure | acl_level in payload | mitigate | acl_level is the ACL TAG (not the secret); Plan 05-09 retrieval enforces it via pre-filter |
| T-05-08-04 | Tampering | dual-write inconsistency | mitigate | PATTERNS.md Pattern 1 — Neo4j first (ACID), then Qdrant (UPSERT idempotent); re-ingest reconciles via deterministic point.id |
| T-05-08-SC | Tampering | npm/pip install | mitigate | qdrant-client + neo4j drivers already in Plan 05-01 pyproject; Approved per RESEARCH legitimacy audit |
</threat_model>

<verification>
- `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -v"` exits 0 (all unit tests pass including point_id deterministic + Cypher-no-f-string scan)
- `nx run sft-knowledge:test --args="-m integration -k 'test_qdrant_indexer or test_neo4j_builder' -v"` exits 0 (all integration tests pass)
- KNW-05 verified via test_end_to_end_provenance_completeness
- KNW-08 SC#4 verified via test_graph_ci_validator
- D-69 idempotency verified via test_upsert_idempotent + test_merge_*_idempotent
</verification>

<success_criteria>
- 3 atomic commits: `feat(05-08-indexer-graph-builder):` × 2 + `test(05-08-indexer-graph-builder):` × 1
- KNW-05 + KNW-08 requirements closed
- Plan 05-09 RetrievalPipeline can query QdrantIndexer's collections and TraverseGraphTool can navigate Neo4jGraphBuilder's graph
- Plan 05-10 pipeline orchestrator wires these in Neo4j-first dual-write order
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-08-indexer-graph-builder-SUMMARY.md` when done with: KNW-05 field coverage list, KNW-08 SC#4 graph validator result, integration test counts, idempotency verification.
</output>
