---
plan_id: 05-10-ingest-service-cli-ci-eval-docs
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 4
depends_on: [05-06-pg-migration-ingest-state, 05-09-retrieval-pipeline-tools-memory]
requirements: [KNW-03, KNW-04, KNW-07, TRN-01]
files_modified:
  - services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py
  - services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py
  - services/knowledge-ingest/scripts/generate_rag_testset.py
  - services/knowledge-ingest/scripts/run_ab_eval.py
  - services/knowledge-ingest/scripts/spot_check_testset.py
  - services/knowledge-ingest/tests/test_ingest_pipeline.py
  - .github/workflows/reindex.yml
  - docs/eval/rag-ab-test-bge-m3-vs-e5.md
  - docs/knowledge-layer/architecture.it.md
  - docs/knowledge-layer/architecture.en.md
  - docs/knowledge-layer/retrieval-pipeline.it.md
  - docs/knowledge-layer/retrieval-pipeline.en.md
  - docs/knowledge-layer/acl-model.it.md
  - docs/knowledge-layer/acl-model.en.md
  - docs/knowledge-layer/eval-results.it.md
  - docs/knowledge-layer/eval-results.en.md
  - docs/mkdocs.yml
  - tests/data/rag_eval/testset.jsonl
  - .planning/ROADMAP.md
autonomous: false
estimated_atomic_commits: 6
must_haves:
  truths:
    - "Typer CLI `knowledge-ingest` runs `nx run knowledge-ingest:run|:bootstrap|:validate` targets"
    - "Pipeline orchestrator chains: parse → chunk → embed → Neo4j MERGE first → Qdrant upsert → ingest_state UPSERT (D-68 + dual-write atomicity)"
    - "content_hash content gate: if state.content_hash == new_hash → early exit (KNW-07 SC#3 idempotent reindex)"
    - "GitHub Actions reindex.yml runs on push to main with git diff --name-only path filter"
    - "generate_rag_testset.py uses Qwen2.5-7B via Phase 4 LLM adapter, seed=42, 3 query types × 41 SOPs ≈ 123 queries"
    - "run_ab_eval.py computes NDCG@10, MRR, Recall@10 for BGE-M3 vs multilingual-e5-large; outputs docs/eval/rag-ab-test-bge-m3-vs-e5.md"
    - "spot_check_testset.py samples 10% (12 queries) for human review (manual checkpoint)"
    - "MkDocs nav includes Knowledge Layer section with 4 IT+EN pages"
    - "ROADMAP.md edit marks Phase 5 complete after successful run (BLOCKING checkpoint)"
    - "test_reindex_idempotent passes (KNW-07 SC#3); test_ingest_state_tracked passes (TRN-01)"
  artifacts:
    - path: services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py
      provides: Typer CLI entrypoint with run/bootstrap/validate modes
    - path: services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py
      provides: orchestrator chaining parse → chunk → embed → dual-write → state
    - path: .github/workflows/reindex.yml
      provides: GitHub Actions workflow with git diff --name-only path filter
    - path: docs/eval/rag-ab-test-bge-m3-vs-e5.md
      provides: A/B eval results with metrics table + decision justification (KNW-03)
    - path: docs/knowledge-layer/{architecture,retrieval-pipeline,acl-model,eval-results}.{it,en}.md
      provides: 8 MkDocs pages documenting Phase 5 deliverables (KNW-04 docs)
  key_links:
    - from: services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py
      to: IngestStateStore from Plan 05-06
      via: content_hash early-exit + UPSERT after dual-write
      pattern: "content_hash|ingest_state"
    - from: .github/workflows/reindex.yml
      to: nx run knowledge-ingest:run --files=...
      via: git diff --name-only path filter
      pattern: "git diff --name-only"
---

<objective>
Wave 4 Plan 10: build the `services/knowledge-ingest` Typer CLI, pipeline orchestrator, GitHub Actions reindex workflow, A/B evaluation deliverable, MkDocs documentation (IT+EN), and the final ROADMAP Phase 5 completion edit.

Purpose: this plan ties together every Wave 1-3 deliverable into a runnable, documented, CI-gated ingest pipeline. KNW-03 (A/B eval doc), KNW-04 (docs side), KNW-07 (incremental reindex SC#3), TRN-01 (ingest_state tracking) close here.

Output: a complete end-to-end deliverable — the ingest pipeline can be invoked locally (`nx run knowledge-ingest:run`) or automatically via GitHub Actions on push to main; the A/B eval produces the deliverable markdown that closes KNW-03; MkDocs documentation is committed; Phase 5 ROADMAP box is checked.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md
@.planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md
@.planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md
@services/knowledge-ingest/pyproject.toml
@services/knowledge-ingest/project.json
@services/knowledge-ingest/src/svc_knowledge_ingest/state.py
@services/ot-bridge/src/svc_ot_bridge/main.py
@.github/workflows/ci.yml
@docs/mkdocs.yml
@packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py
@packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py
@packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
@packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py
@packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py
@packages/sft-agents/src/sft_agents/llm/factory.py
</context>

<interfaces>
Pipeline orchestrator (D-67 + D-68 + PATTERNS.md Pattern 1):
```
async def ingest_file(
    path: Path,
    *,
    parser: MarkdownParser,
    chunker: SemanticChunker,
    embedder: BgeM3Embedder,
    qdrant_indexer: QdrantIndexer,
    neo4j_builder: Neo4jGraphBuilder,
    state_store: IngestStateStore,
    failure_modes: tuple[FailureMode, ...],
) -> IngestResult:
    # 1. Compute content_hash = sha256(file bytes)
    # 2. Early exit: if state_store.get(source_uri).content_hash == content_hash → log + return IngestResult(skipped=True)
    # 3. parse → if None (non-reviewed status) → return IngestResult(skipped=True, reason="non_reviewed")
    # 4. chunk → embed → produce dense_vecs + sparse_vecs
    # 5. Infer failure_mode_ids by matching parsed_doc.frontmatter tags/related_glossary against FailureMode IDs/names
    # 6. Neo4j FIRST (atomicity): await neo4j_builder.merge_sop(parsed_doc, failure_mode_ids)
    # 7. Qdrant SECOND: await qdrant_indexer.upsert_batch(chunks, dense_vecs, sparse_vecs)
    # 8. state UPSERT: await state_store.upsert(source_uri, content_hash, version, chunk_count, collection, acl_level)
    # 9. Return IngestResult(skipped=False, chunks_upserted=N, sop_id=...)
```

Typer CLI (`__main__.py`):
```
app = typer.Typer()

@app.command()
def run(paths: list[str] = typer.Option([]), files: list[str] = typer.Option([]),
        mode: str = typer.Option("incremental"), collection: str = typer.Option("sop")) -> None:
    asyncio.run(_async_main(paths, files, mode, collection))

@app.command()
def bootstrap() -> None:
    # 1. Run scripts/qdrant-bootstrap.py (subprocess)
    # 2. Run scripts/neo4j-bootstrap.py (subprocess)
    # 3. Run scripts/timescale-migrate.py with migration 006 (subprocess)
    ...

@app.command()
def validate() -> None:
    # 1. Verify connectivity: Qdrant, Neo4j, PG all reachable
    # 2. Verify failure_modes.yaml loadable
    # 3. Verify schema constraints in Neo4j
    # 4. Print summary; exit 0 if all healthy
    ...

if __name__ == "__main__":
    app()
```

A/B eval scripts (D-71 LOCKED):

`generate_rag_testset.py`:
- For each reviewed SOP (41): invoke Qwen2.5-7B via Phase 4 LLM adapter with seed=42, temperature=0.3
- Generate 3 queries per SOP (keyword_it, natural_it, cross_lingual_en)
- Write to `tests/data/rag_eval/testset.jsonl` (one JSON per line: {id, query, lang, type, gold_sop_id, gold_chunk_idx})
- Idempotent: --regenerate flag forces rewrite; default skips if testset.jsonl exists

`run_ab_eval.py`:
- For each model in [bge_m3, multilingual_e5_large]:
  1. Re-index corpus into collection `sop_{model}`
  2. For each query in testset: run retrieval (with rerank attached, same BGE-reranker for fairness)
  3. Compute NDCG@10, MRR, Recall@10; partition by query type (keyword_it, natural_it, cross_lingual_en)
- Aggregate results; write `docs/eval/rag-ab-test-bge-m3-vs-e5.md` with:
  - Metrics table side-by-side
  - Mermaid bar chart per query type
  - Justified decision section ("We choose BGE-M3 because...")
  - Reproducibility notes (commands + seed + testset hash)

`spot_check_testset.py`:
- Interactive CLI: presents 10% random sample (~12 queries) for human review
- For each: asks "is query realistic? (y/n)", "is gold chunk correct? (y/n)"
- Outputs reject rate; exits 1 if > 20%

Reindex CI workflow (D-68 LOCKED — PATTERNS.md reindex.yml section):

```
on:
  push:
    branches: [main]
    paths:
      - 'simulators/synthetic-corpus/**'
      - 'docs/sops/**'
      - 'packages/sft-domain/failure_modes.yaml'
  workflow_dispatch:

jobs:
  reindex:
    services:
      qdrant: { image: qdrant/qdrant:v1.16.1, ports: ['6333:6333'] }
      neo4j: { image: neo4j:5.24-community, env: {NEO4J_AUTH: 'neo4j/cipassword', NEO4J_PLUGINS: '["apoc"]'}, ports: ['7687:7687'] }
    steps:
      - uses: actions/checkout@v4 with fetch-depth: 0
      - Setup Python 3.12 + uv + Node 20 + nx (mirror ci.yml lines 22-79)
      - run: git diff --name-only ${{ github.event.before }} ${{ github.sha }} -- 'simulators/synthetic-corpus/**' 'docs/sops/**' > changed.txt
      - run: nx run knowledge-ingest:run --args="--files=$(paste -sd, changed.txt)"
```

MkDocs documentation pages (8 files, IT+EN parallel) covering:
- architecture: high-level diagram + dual-write pattern + 4 collections + Neo4j schema
- retrieval-pipeline: D-63 hybrid retrieval pipeline + RRF + rerank + ACL filter flow
- acl-model: D-72 ACL mapping table + ROLE_TO_ACL constant + non-leak guarantees
- eval-results: link to docs/eval/rag-ab-test-bge-m3-vs-e5.md + summary of A/B decision

ROADMAP edit ([BLOCKING] checkpoint per CONTEXT.md scope_boundaries):
- Mark Phase 5 box as [x] complete
- Update Phase 5 row in Progress table: `5. Knowledge Layer (RAG + Graph) | 10/10 | Complete | YYYY-MM-DD`
- Add KNW-04 supplement note (MD-only Phase 5; PDF/DOCX/HTML deferred Phase 8)
</interfaces>

<tasks>

<task id="05-10-01" type="auto" tdd="true">
  <name>Task 1: Pipeline orchestrator with content_hash early exit + dual-write + state UPSERT</name>
  <files>
    services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py,
    services/knowledge-ingest/tests/test_ingest_pipeline.py
  </files>
  <read_first>
    services/knowledge-ingest/src/svc_knowledge_ingest/state.py (IngestStateStore API from Plan 05-06),
    packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py,
    packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py,
    packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py,
    packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py,
    packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py,
    packages/sft-domain/src/sft_domain/failure_modes/_loader.py,
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-68 idempotency lines 473-478; Pattern 1 atomicity from PATTERNS.md),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (KNW-07 SC#3 + TRN-01 test rows)
  </read_first>
  <behavior>
    - `ingest_file(path, *, parser, chunker, embedder, qdrant_indexer, neo4j_builder, state_store, failure_modes) -> IngestResult`:
      1. Compute `content_hash = hashlib.sha256(path.read_bytes()).hexdigest()`
      2. `existing = await state_store.get(source_uri)`; if `existing and existing.content_hash == content_hash`: log info "ingest_skipped_unchanged" + return IngestResult(skipped=True, reason="content_unchanged")
      3. `parsed = await parser.parse(path)`; if parsed is None (non-reviewed): return IngestResult(skipped=True, reason="non_reviewed")
      4. `chunks = chunker.chunk(parsed)`
      5. `output = embedder.encode([c.text for c in chunks])`; dense_vecs from output.dense_vecs; sparse_vecs from `[embedder.to_qdrant_sparse(w) for w in output.sparse_weights]`
      6. Infer failure_mode_ids: cross-reference parsed.frontmatter (tags + related_glossary) with failure_modes (id/name_it/name_en case-insensitive); return list of matched FailureMode.id values.
      7. Neo4j FIRST: `await neo4j_builder.merge_sop(parsed, failure_mode_ids)`
      8. Qdrant SECOND: `chunk_count = await qdrant_indexer.upsert_batch(chunks, dense_vecs, sparse_vecs)`
      9. State UPSERT: `await state_store.upsert(source_uri=parsed.source_uri, content_hash=content_hash, version=parsed.version, chunk_count=chunk_count, collection=qdrant_indexer.collection, acl_level=parsed.frontmatter["acl_level"])`
      10. Return `IngestResult(skipped=False, chunks_upserted=chunk_count, sop_id=parsed.frontmatter["id"], content_hash=content_hash)`
    - On exception between Neo4j and Qdrant: log "ingest_inconsistent_state" + re-raise; reconciliation = re-run ingest (deterministic IDs make this safe)
    - test_reindex_idempotent (KNW-07 SC#3, integration testcontainer Qdrant+Neo4j+PG): ingest file once → returns chunks_upserted=N; ingest same file again → returns IngestResult(skipped=True, reason="content_unchanged"); Qdrant point count unchanged; Neo4j SOP node count unchanged
    - test_ingest_state_tracked (TRN-01, integration): after ingest, state_store.get(source_uri) returns IngestStateRow with non-null indexed_at + chunk_count > 0 + acl_level matches
    - test_content_hash_change_reingests: ingest file → modify file body → ingest again → new chunks created (Qdrant point count increases) + state.content_hash updated
    - test_non_reviewed_skip: ingest a file with status=draft → IngestResult(skipped=True, reason="non_reviewed") + no Qdrant + no Neo4j write
    - test_neo4j_first_atomicity (integration): mock qdrant_indexer.upsert_batch to raise; ingest_file → exception propagates AFTER Neo4j MERGE succeeded; state UPSERT NOT called; second ingest is recoverable (same content_hash; re-attempt completes)
  </behavior>
  <action>
    Create `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`:
    - `from __future__ import annotations`, `import hashlib`, `import structlog`, `from pathlib import Path`
    - `from pydantic import BaseModel`
    - `class IngestResult(BaseModel): model_config = {"frozen": True, "extra": "forbid"}; skipped: bool; reason: str | None = None; chunks_upserted: int = 0; sop_id: str | None = None; content_hash: str | None = None`
    - `def _infer_failure_mode_ids(frontmatter: dict, failure_modes: tuple[FailureMode, ...]) -> list[str]`: build search set from tags + related_glossary + title (lowercase substring); match against fm.id, fm.name_it.lower(), fm.name_en.lower(); return list of matched fm.id.
    - `async def ingest_file(path, *, parser, chunker, embedder, qdrant_indexer, neo4j_builder, state_store, failure_modes) -> IngestResult`: implement steps 1-10 per `<behavior>`.
    - Use structlog with bound context: `logger.bind(source_uri=..., content_hash=...)`.

    Update `services/knowledge-ingest/tests/test_ingest_pipeline.py`:
    - 5 tests from `<behavior>`. All marked `@pytest.mark.integration` (since they need testcontainer Qdrant+Neo4j+PG).
    - For Qdrant/Neo4j: use existing fixtures from packages/sft-knowledge/tests/conftest.py — Plan 05-06 Task 3 already set up pg_pool in services/knowledge-ingest/tests/conftest.py. Add qdrant_client + neo4j_driver to services/knowledge-ingest/tests/conftest.py (import them from sft-knowledge tests OR re-create with same pattern — verify pytest discovery permits cross-package fixture import; if not, duplicate the fixture).
    - Bootstrap Qdrant collections + Neo4j constraints via subprocess calls inside test setup (or a session-scoped autouse fixture).

    Commit: `feat(05-10-ingest-service-cli-ci-eval-docs): add pipeline orchestrator with content_hash early exit + dual-write`.
  </action>
  <acceptance_criteria>
    - `grep -q 'async def ingest_file' services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`
    - `grep -q 'content_hash' services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`
    - `grep -q 'await neo4j_builder.merge_sop' services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py` (Neo4j-first order)
    - `grep -q 'await state_store.upsert' services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`
    - `nx run knowledge-ingest:test --args="-m integration -k 'test_reindex_idempotent or test_ingest_state_tracked or test_content_hash_change or test_non_reviewed_skip or test_neo4j_first_atomicity' -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run knowledge-ingest:test --args="-m integration -k 'test_reindex_idempotent or test_ingest_state_tracked' -v"</automated>
  </verify>
  <done>Pipeline + 5 tests committed; KNW-07 SC#3 + TRN-01 verified; dual-write atomicity verified.</done>
</task>

<task id="05-10-02" type="auto">
  <name>Task 2: Typer CLI __main__.py (run/bootstrap/validate) + Nx targets verification</name>
  <files>
    services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py
  </files>
  <read_first>
    services/ot-bridge/src/svc_ot_bridge/main.py (structlog JSON config lines 30-41, env fail-fast lines 64-69),
    services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py (just from Task 1),
    services/knowledge-ingest/project.json (Nx targets from Plan 05-06)
  </read_first>
  <action>
    Create `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`:
    - `from __future__ import annotations`, `import asyncio`, `import os`, `import sys`, `from pathlib import Path`
    - structlog JSON configure at module top (per Shared Pattern 6 + ot-bridge main.py lines 30-41).
    - `import typer`; `app = typer.Typer(help="sft knowledge ingest pipeline (Phase 5)")`
    - Three commands:
      1. `@app.command() def run(paths: list[str] = ..., files: list[str] = ..., mode: str = "incremental", collection: str = "sop") -> None`:
         - Collect candidate files: if `files` given, parse comma-separated list; if `paths` given, rglob "*.md" in each path.
         - `asyncio.run(_async_run(file_list, collection))` where `_async_run` builds parser+chunker+embedder+indexer+builder+state_store and calls `ingest_file` for each.
      2. `@app.command() def bootstrap() -> None`:
         - subprocess.run for `scripts/qdrant-bootstrap.py`, `scripts/neo4j-bootstrap.py`, `scripts/timescale-migrate.py` in that order.
         - Exit 1 if any fails.
      3. `@app.command() def validate() -> None`:
         - Connect to Qdrant: assert all 4 collections exist.
         - Connect to Neo4j: assert all 4 constraints exist.
         - Connect to PG: assert knowledge.ingest_state table exists.
         - Load failure_modes via `load_failure_modes()`; assert count > 0.
         - Print summary table; exit 0 if all healthy else 1.
    - Env fail-fast pattern for required env vars (QDRANT_URL, NEO4J_URI, TIMESCALE_DSN) per ot-bridge main.py lines 64-69.
    - `if __name__ == "__main__": app()`

    Verify Nx targets work end-to-end:
    - `nx run knowledge-ingest:validate` (requires services running locally OR via docker compose; if local infra not available, accept that the Nx target can be invoked and reports connection failure with clean error message — wrap in try/except to provide friendly diagnostic).
    - `nx run knowledge-ingest:bootstrap` (requires local Qdrant+Neo4j+PG up).
    - `nx run knowledge-ingest:run --args="--files=simulators/synthetic-corpus/it/loom/SOP-LOOM-001-*.md"` end-to-end (manual run; acceptance is `validate` mode passing).

    Commit: `feat(05-10-ingest-service-cli-ci-eval-docs): add Typer CLI with run/bootstrap/validate commands`.
  </action>
  <acceptance_criteria>
    - `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py` exists
    - `grep -q 'import typer' services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`
    - `grep -q 'app = typer.Typer' services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`
    - `grep -E '@app.command\\(\\)' services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py | wc -l` returns 3
    - `grep -q 'def bootstrap' services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`
    - `grep -q 'def validate' services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`
    - `uv run python -m svc_knowledge_ingest --help` exits 0 and lists the 3 commands
  </acceptance_criteria>
  <verify>
    <automated>cd services/knowledge-ingest &amp;&amp; uv run python -m svc_knowledge_ingest --help 2&gt;&amp;1 | grep -E '(run|bootstrap|validate)'</automated>
  </verify>
  <done>Typer CLI shipped; all 3 commands wired; Nx targets functional.</done>
</task>

<task id="05-10-03" type="auto">
  <name>Task 3: GitHub Actions reindex.yml workflow (push to main + path filter)</name>
  <files>
    .github/workflows/reindex.yml
  </files>
  <read_first>
    .github/workflows/ci.yml (Python+uv+Node setup steps lines 22-79),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-68 workflow spec lines 423-449),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (reindex.yml section lines 1114-1174)
  </read_first>
  <action>
    Create `.github/workflows/reindex.yml`:
    - `name: Reindex Knowledge Layer`
    - `on:` `push: branches: [main] paths: - 'simulators/synthetic-corpus/**' - 'docs/sops/**' - 'packages/sft-domain/failure_modes.yaml'` + `workflow_dispatch:`
    - `jobs:` `reindex:` `runs-on: ubuntu-latest`
    - `services:`
      - `qdrant: image: qdrant/qdrant:v1.16.1, ports: ['6333:6333']`
      - `neo4j: image: neo4j:5.24-community, env: {NEO4J_AUTH: 'neo4j/cipassword', NEO4J_PLUGINS: '["apoc"]'}, ports: ['7687:7687']`
      - `postgres: image: postgres:16, env: {POSTGRES_USER: postgres, POSTGRES_PASSWORD: postgres, POSTGRES_DB: sft}, ports: ['5432:5432']`
    - `steps:`
      1. `actions/checkout@v4` with `fetch-depth: 0`
      2. setup-node@v4 (Node 20)
      3. setup-python@v5 (Python 3.12)
      4. astral-sh/setup-uv@v5
      5. Install workspace deps: `uv sync`
      6. Wait for services healthy: simple bash poll for Qdrant /healthz + Neo4j 7474 + PG pg_isready
      7. Bootstrap: `uv run python scripts/timescale-migrate.py --dsn ...` + `uv run python scripts/qdrant-bootstrap.py --qdrant-url http://localhost:6333` + `uv run python scripts/neo4j-bootstrap.py --neo4j-uri bolt://localhost:7687 --neo4j-auth neo4j/cipassword`
      8. Compute changed: `git diff --name-only ${{ github.event.before || 'HEAD~1' }} ${{ github.sha }} -- 'simulators/synthetic-corpus/**' 'docs/sops/**' 'packages/sft-domain/failure_modes.yaml' > changed.txt`
      9. Print changed file count: `echo "Changed files:"; cat changed.txt`
      10. `nx run knowledge-ingest:run --args="--files=$(paste -sd, changed.txt)"` (only if changed.txt non-empty)
    - env vars at job level: `QDRANT_URL`, `NEO4J_URI`, `NEO4J_AUTH`, `TIMESCALE_DSN` pointing at the service containers.

    Verify locally: `gh workflow view reindex.yml` (if gh CLI available) or yamllint to check syntax: `python -c "import yaml; yaml.safe_load(open('.github/workflows/reindex.yml'))"` exits 0.

    Commit: `ci(05-10-ingest-service-cli-ci-eval-docs): add reindex.yml workflow with path filter`.
  </action>
  <acceptance_criteria>
    - `.github/workflows/reindex.yml` exists
    - `python -c "import yaml; yaml.safe_load(open('.github/workflows/reindex.yml'))"` exits 0 (valid YAML)
    - `grep -q "branches: \[main\]" .github/workflows/reindex.yml`
    - `grep -q 'simulators/synthetic-corpus' .github/workflows/reindex.yml`
    - `grep -q 'git diff --name-only' .github/workflows/reindex.yml`
    - `grep -q 'nx run knowledge-ingest:run' .github/workflows/reindex.yml`
    - `grep -q 'qdrant/qdrant:v1.16.1' .github/workflows/reindex.yml`
    - `grep -q 'neo4j:5.24-community' .github/workflows/reindex.yml`
  </acceptance_criteria>
  <verify>
    <automated>python -c "import yaml; yaml.safe_load(open('.github/workflows/reindex.yml'))" &amp;&amp; grep -q 'nx run knowledge-ingest:run' .github/workflows/reindex.yml</automated>
  </verify>
  <done>Reindex workflow shipped, YAML valid, runs on push to main with proper path filter + service containers.</done>
</task>

<task id="05-10-04" type="auto">
  <name>Task 4: A/B eval scripts (generate_rag_testset, run_ab_eval, spot_check_testset) + deliverable</name>
  <files>
    services/knowledge-ingest/scripts/generate_rag_testset.py,
    services/knowledge-ingest/scripts/run_ab_eval.py,
    services/knowledge-ingest/scripts/spot_check_testset.py,
    tests/data/rag_eval/testset.jsonl,
    docs/eval/rag-ab-test-bge-m3-vs-e5.md
  </files>
  <read_first>
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-71 full spec lines 599-651),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §7 + §8 (NDCG/MRR computation + Q-gen prompt patterns),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (KNW-03 + manual spot-check rows),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (scripts/generate_rag_testset.py section),
    packages/sft-agents/src/sft_agents/llm/factory.py (LLM_BACKEND adapter API from Phase 4)
  </read_first>
  <action>
    Create `services/knowledge-ingest/scripts/generate_rag_testset.py`:
    - WORKSPACE_ROOT pattern; argparse `--seed=42`, `--regenerate` flag, `--output=tests/data/rag_eval/testset.jsonl`
    - For each reviewed SOP: invoke `from sft_agents.llm.factory import get_llm_adapter; llm = get_llm_adapter()`; prompt per D-71 lines 605-616.
    - Pass seed=42 via langchain-ollama model_kwargs.
    - Parse JSON response: list of {type, lang, text, target_section}.
    - Map target_section → gold_chunk_idx via heading_path lookup.
    - Append each query as JSONL line: `{"id": "q-NNN", "query": str, "lang": "it|en", "type": "keyword_it|natural_it|cross_lingual_en", "gold_sop_id": str, "gold_chunk_idx": int}`.
    - Idempotent: skip if output file exists unless --regenerate.

    Create `services/knowledge-ingest/scripts/run_ab_eval.py`:
    - argparse `--testset=tests/data/rag_eval/testset.jsonl`, `--output=docs/eval/rag-ab-test-bge-m3-vs-e5.md`, `--skip-qgen` flag (for CI without LLM)
    - For each model in ["BAAI/bge-m3", "intfloat/multilingual-e5-large"]:
      1. Re-index corpus into collection `sop_bgem3` or `sop_e5large` (build separate QdrantIndexer with model-specific embedder)
      2. For each query: run RetrievalPipeline.search; compute NDCG@10, MRR, Recall@10 per RESEARCH §7 formulas.
      3. Partition by query_type.
    - Build markdown deliverable per D-71 lines 636-642:
      - Metrics table side-by-side
      - Mermaid bar chart per (model, query_type)
      - Decision section: "We choose BGE-M3 because..." (template; choose winner based on delta ≥3pp in ≥2 metrics OR default to BGE-M3 per CONTEXT.md "comparable, default BGE-M3 per MIT + multimodal")
      - Reproducibility: testset hash, seed, command to re-run.
    - Verify acceptance gates: BGE-M3 NDCG@10 IT keyword ≥ 0.80; BGE-M3 NDCG@10 IT natural ≥ 0.75; cross-lingual Recall@10 ≥ 0.70.

    Create `services/knowledge-ingest/scripts/spot_check_testset.py`:
    - argparse `--sample-rate=0.10`, `--seed=42`, `--testset=tests/data/rag_eval/testset.jsonl`
    - Load testset; random.seed(42); sample 10%.
    - For each sample: print SOP id + query + target_section; prompt user `query realistic? (y/n)` + `gold chunk correct? (y/n)`.
    - Compute reject_rate = (rejects / sampled); exit 1 if reject_rate > 0.20; exit 0 otherwise.
    - This is the MANUAL CHECKPOINT (autonomous=false in plan frontmatter — declared at top).

    Run the scripts to produce concrete outputs:
    - `uv run python services/knowledge-ingest/scripts/generate_rag_testset.py --seed=42` → writes `tests/data/rag_eval/testset.jsonl` (committed)
    - `uv run python services/knowledge-ingest/scripts/run_ab_eval.py` → writes `docs/eval/rag-ab-test-bge-m3-vs-e5.md` (committed). If LLM adapter unavailable in CI, use `--skip-qgen` and provide a placeholder testset (still committed) so the deliverable can be reviewed; mark in the markdown that "A/B numbers below are from a preliminary run; final numbers will be regenerated when LLM infra is available".

    Commit: `feat(05-10-ingest-service-cli-ci-eval-docs): add A/B eval scripts + testset + rag-ab-test deliverable`.
  </action>
  <acceptance_criteria>
    - 3 scripts exist: `services/knowledge-ingest/scripts/{generate_rag_testset,run_ab_eval,spot_check_testset}.py`
    - `grep -q 'seed=42' services/knowledge-ingest/scripts/generate_rag_testset.py`
    - `grep -q 'NDCG' services/knowledge-ingest/scripts/run_ab_eval.py` and `grep -q 'Recall@10' services/knowledge-ingest/scripts/run_ab_eval.py`
    - `tests/data/rag_eval/testset.jsonl` exists with ≥100 lines (or a smaller placeholder if LLM unavailable; document in commit msg)
    - `docs/eval/rag-ab-test-bge-m3-vs-e5.md` exists with metrics table + decision section
    - `grep -q '"We choose' docs/eval/rag-ab-test-bge-m3-vs-e5.md` (justified decision per D-71)
    - `grep -q 'Mermaid\\|mermaid' docs/eval/rag-ab-test-bge-m3-vs-e5.md` (chart per D-71)
  </acceptance_criteria>
  <verify>
    <automated>ls services/knowledge-ingest/scripts/generate_rag_testset.py services/knowledge-ingest/scripts/run_ab_eval.py services/knowledge-ingest/scripts/spot_check_testset.py docs/eval/rag-ab-test-bge-m3-vs-e5.md tests/data/rag_eval/testset.jsonl</automated>
  </verify>
  <done>3 A/B eval scripts + testset + deliverable committed; KNW-03 requirement closed (deliverable exists with metrics + decision); manual spot-check script ready for human review.</done>
</task>

<task id="05-10-05" type="checkpoint:human-verify" gate="blocking">
  <name>Task 5: Human spot-check on A/B eval testset (10% sample manual review)</name>
  <what-built>
    Plan 05-10 Task 4 produced `tests/data/rag_eval/testset.jsonl` (≥100 queries) and the deliverable `docs/eval/rag-ab-test-bge-m3-vs-e5.md`.
    Per D-71 LOCKED decision: a 10% manual spot-check is REQUIRED to mitigate LLM-bias circular validation (Qwen2.5 generated queries; Qwen-family also used in some retrieval flows).
  </what-built>
  <how-to-verify>
    1. Run the interactive spot-check script:
       `uv run python services/knowledge-ingest/scripts/spot_check_testset.py --sample-rate=0.10 --seed=42`
    2. For each of the ~12 sampled queries, the script prints:
       - The SOP id + frontmatter title (IT or EN)
       - The generated query text (keyword_it | natural_it | cross_lingual_en)
       - The proposed target_section / gold_chunk_idx
    3. For each item, decide:
       - Is the query **realistic** (a textile factory operator could plausibly type this)? y/n
       - Is the gold chunk **correct** (does target_section actually contain the answer)? y/n
    4. Script reports reject_rate at the end.
    5. **Acceptance gate (D-71 LOCKED):** reject_rate must be < 20%. If reject_rate ≥ 20%, regenerate testset with prompt revision via `--regenerate` flag on `generate_rag_testset.py` and re-spot-check.
  </how-to-verify>
  <resume-signal>
    Type "approved" if reject_rate < 20%; or "regenerate" if testset needs Q-gen prompt revision; or describe issues for triage.
  </resume-signal>
</task>

<task id="05-10-06" type="auto">
  <name>Task 6: MkDocs knowledge-layer pages (4 IT + 4 EN) + nav update</name>
  <files>
    docs/knowledge-layer/architecture.it.md,
    docs/knowledge-layer/architecture.en.md,
    docs/knowledge-layer/retrieval-pipeline.it.md,
    docs/knowledge-layer/retrieval-pipeline.en.md,
    docs/knowledge-layer/acl-model.it.md,
    docs/knowledge-layer/acl-model.en.md,
    docs/knowledge-layer/eval-results.it.md,
    docs/knowledge-layer/eval-results.en.md,
    docs/mkdocs.yml
  </files>
  <read_first>
    docs/mkdocs.yml (existing nav structure + i18n plugin config),
    docs/it-ot/ (Phase 3 IT/OT docs IT+EN pattern as analog),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (claudes_discretion MkDocs nav section lines 798),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (KNW-04 docs side row + Manual-Only Verifications)
  </read_first>
  <action>
    Create 8 MkDocs documentation pages under `docs/knowledge-layer/`. Use the Phase 3 `docs/it-ot/` directory as the structural analog (IT+EN parallel pages, same headings translated, Mermaid diagrams where useful):

    1. `architecture.it.md` + `.en.md` — high-level architecture:
       - System diagram (Mermaid) showing: SOP corpus → ingest service → Qdrant + Neo4j (dual-write, Neo4j first) → agents read via RagSearchTool + TraverseGraphTool.
       - 4 Qdrant collections + payload schema (D-61).
       - Neo4j schema Machine → Part → FailureMode → SOP (D-65).
       - Package layout: `packages/sft-knowledge` + `services/knowledge-ingest` (D-70).

    2. `retrieval-pipeline.it.md` + `.en.md` — hybrid retrieval flow:
       - D-63 pipeline diagram: query → embed (BGE-M3) → Qdrant Query API (Prefetch dense + Prefetch sparse → Fusion RRF top-20) → BGE-reranker-v2-m3 → top-k.
       - Code example using `RagSearchTool.ainvoke({...})`.
       - Cross-lingual retrieval explanation (D-64 — no query translation, BGE-M3 representations).

    3. `acl-model.it.md` + `.en.md` — ACL governance:
       - D-72 audience → acl_level mapping table.
       - ROLE_TO_ACL constant + ROLE→ACL flow.
       - Pre-filter at engine level explanation (PATTERNS.md Pattern 2).
       - Phase 5 SC#2 non-leak guarantee + reference to integration test.

    4. `eval-results.it.md` + `.en.md` — A/B eval summary:
       - Reference to `docs/eval/rag-ab-test-bge-m3-vs-e5.md` (the full deliverable).
       - Summary table (metrics).
       - "We chose BGE-M3 because..." short version with link to full reasoning.

    Update `docs/mkdocs.yml`:
    - Add `Knowledge Layer:` section under existing `nav:` (place after `IT/OT Simulation:` or wherever Phase 3 pages live):
      ```
      - Knowledge Layer:
        - Architecture: knowledge-layer/architecture.md
        - Retrieval pipeline: knowledge-layer/retrieval-pipeline.md
        - ACL model: knowledge-layer/acl-model.md
        - Eval results: knowledge-layer/eval-results.md
      ```
    - The IT/EN routing is handled by the existing mkdocs-i18n plugin (per docs/mkdocs.yml Phase 1 setup) — verify that `.it.md` and `.en.md` suffix convention matches what the plugin expects (alternative: nested locale dirs).

    Verify: `mkdocs build --strict` (or `cd docs && mkdocs build --strict`) exits 0. No broken links. All 8 pages render.

    Commit: `docs(05-10-ingest-service-cli-ci-eval-docs): add knowledge-layer MkDocs pages IT+EN + nav update`.
  </action>
  <acceptance_criteria>
    - `ls docs/knowledge-layer/{architecture,retrieval-pipeline,acl-model,eval-results}.{it,en}.md | wc -l` returns 8
    - `grep -q 'Knowledge Layer' docs/mkdocs.yml`
    - `grep -q 'knowledge-layer/architecture' docs/mkdocs.yml`
    - `cd docs && mkdocs build --strict` exits 0 (or `mkdocs build --strict -f docs/mkdocs.yml` exits 0)
    - Each .md page non-empty (`find docs/knowledge-layer -name '*.md' -size -500c | wc -l` returns 0 — no file under 500 bytes)
  </acceptance_criteria>
  <verify>
    <automated>ls docs/knowledge-layer/architecture.it.md docs/knowledge-layer/architecture.en.md docs/knowledge-layer/retrieval-pipeline.it.md docs/knowledge-layer/retrieval-pipeline.en.md docs/knowledge-layer/acl-model.it.md docs/knowledge-layer/acl-model.en.md docs/knowledge-layer/eval-results.it.md docs/knowledge-layer/eval-results.en.md &amp;&amp; (cd docs &amp;&amp; mkdocs build --strict)</automated>
  </verify>
  <done>8 MkDocs pages + nav update committed; `mkdocs build --strict` exits 0; KNW-04 docs side closed.</done>
</task>

<task id="05-10-07" type="auto">
  <name>Task 7: [BLOCKING] ROADMAP edit — mark Phase 5 complete</name>
  <files>
    .planning/ROADMAP.md
  </files>
  <read_first>
    .planning/ROADMAP.md (Phase 5 section + Progress table — current state shows "0/TBD | Not started"),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (scope_boundaries section — ROADMAP edit task explicitly listed)
  </read_first>
  <action>
    Edit `.planning/ROADMAP.md`:

    1. Top-level Phases list (lines 9-20): change `- [ ] **Phase 5: Knowledge Layer (RAG + Graph)**` to `- [x] **Phase 5: Knowledge Layer (RAG + Graph)** - ... (completed YYYY-MM-DD)` using today's date.

    2. Phase 5 detail block (`### Phase 5: Knowledge Layer (RAG + Graph)`):
       - After the existing Success Criteria block, add an explicit note:
         ```
         **KNW-04 scope note:** Phase 5 ships MarkdownParser only. The DocumentParser ABC enables PDF/DOCX/HTML parsers in Phase 8 KnowledgeCurator (scoping deviation from literal KNW-04; documented in CONTEXT.md D-67).
         ```
       - Update the `**Plans**: TBD` line to: `**Plans**: 10 plans` and add a checked list of all 10 plans:
         ```
         - [x] 05-01-sft-knowledge-sdk-PLAN.md — sft-knowledge SDK scaffold + Pydantic models + MarkdownParser (KNW-04, KNW-05)
         - [x] 05-02-acl-migration-PLAN.md — acl_level migration script + 41 SOP frontmatter update + validator extension (KNW-06)
         - [x] 05-03-failure-modes-yaml-PLAN.md — failure_modes.yaml + loader + 30+ entries + CI validator (KNW-08)
         - [x] 05-04-qdrant-bootstrap-PLAN.md — 4-collection bootstrap script + integration test (KNW-01)
         - [x] 05-05-neo4j-compose-bootstrap-PLAN.md — Neo4j 5.24 compose + bootstrap + Helm + APOC (KNW-08 infra)
         - [x] 05-06-pg-migration-ingest-state-PLAN.md — migration 006 + state.py + knowledge-ingest scaffold (KNW-07, TRN-01)
         - [x] 05-07-embedding-chunking-PLAN.md — BgeM3Embedder + SemanticChunker (KNW-02)
         - [x] 05-08-indexer-graph-builder-PLAN.md — QdrantIndexer + Neo4jGraphBuilder (KNW-05, KNW-08)
         - [x] 05-09-retrieval-pipeline-tools-memory-PLAN.md — RetrievalPipeline + RagSearchTool + TraverseGraphTool + QdrantLongTermMemory (KNW-06, KNW-09)
         - [x] 05-10-ingest-service-cli-ci-eval-docs-PLAN.md — Typer CLI + pipeline + reindex.yml + A/B eval + MkDocs (KNW-03, KNW-04, KNW-07, TRN-01)
         ```

    3. Progress table (lines 205-218): change Phase 5 row from `| 5. Knowledge Layer (RAG + Graph) | 0/TBD | Not started | - |` to `| 5. Knowledge Layer (RAG + Graph) | 10/10 | Complete | YYYY-MM-DD |` with today's date.

    **CRITICAL:** This edit MUST be the FINAL commit of Phase 5, executed only AFTER tasks 1-6 are green AND the human spot-check (Task 5) returned approved AND all integration tests pass full suite. Verify before commit:
    - `nx run sft-knowledge:test --args="-v"` exits 0 (real + skipped + integration)
    - `nx run knowledge-ingest:test --args="-v"` exits 0
    - `mkdocs build --strict` exits 0
    - `uv run python scripts/validate-corpus-frontmatter.py` exits 0
    - `uv run python scripts/validate-failure-modes.py` exits 0

    Commit: `docs(05-10-ingest-service-cli-ci-eval-docs): mark Phase 5 complete in ROADMAP`.
  </action>
  <acceptance_criteria>
    - `grep -q '- \[x\] \*\*Phase 5: Knowledge Layer' .planning/ROADMAP.md`
    - `grep -q '| 5\. Knowledge Layer (RAG + Graph) | 10/10 | Complete' .planning/ROADMAP.md`
    - `grep -q '05-01-sft-knowledge-sdk-PLAN.md' .planning/ROADMAP.md`
    - `grep -q '05-10-ingest-service-cli-ci-eval-docs-PLAN.md' .planning/ROADMAP.md`
    - `grep -c '- \[x\] 05-' .planning/ROADMAP.md` returns ≥10
    - All Phase 5 verification gates green BEFORE this commit (see action body checklist)
  </acceptance_criteria>
  <verify>
    <automated>grep -q '- \[x\] \*\*Phase 5: Knowledge Layer' .planning/ROADMAP.md &amp;&amp; grep -q '10/10 | Complete' .planning/ROADMAP.md</automated>
  </verify>
  <done>ROADMAP Phase 5 box checked; all 10 plans listed as complete; Progress table updated; Phase 5 formally closed.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| GitHub Actions push event → reindex workflow | git diff input is trusted (signed commits on main); path filter limits scope to known directories |
| Pipeline orchestrator → dual-write (Neo4j first, then Qdrant) | atomicity gap exists between writes; mitigated by deterministic point.id allowing safe re-run |
| LLM adapter → synthetic Q-gen | Qwen2.5 output is parsed as JSON; malformed responses are caught + logged + skipped |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-10-01 | Tampering | reindex.yml git diff scope | mitigate | Path filter restricts to simulators/synthetic-corpus + docs/sops + failure_modes.yaml — no broad-file changes trigger reindex |
| T-05-10-02 | Tampering | dual-write inconsistency between Neo4j + Qdrant | mitigate | Neo4j first (ACID); on Qdrant failure re-run with same content_hash recovers; deterministic point.id + Neo4j MERGE both idempotent |
| T-05-10-03 | Information Disclosure | A/B eval testset committed to repo | accept | Testset queries are derived from public synthetic SOPs (no PII); committed for reproducibility per D-71 |
| T-05-10-04 | Repudiation | A/B eval decision provenance | mitigate | Deliverable doc includes seed + testset hash + reproducibility command; human spot-check (Task 5) records manual review of 10% sample |
| T-05-10-05 | Denial of Service | GH Actions reindex on every push | accept | Path filter limits triggers; ingest is fast for typical diff (1-3 files) |
| T-05-10-06 | Elevation of Privilege | ROADMAP edit | accept | Task 7 is a documentation edit only; no code or infra access changes |
| T-05-10-SC | Tampering | npm/pip install | mitigate | All deps already declared in Plan 05-01 + Plan 05-06 pyproject; Approved per RESEARCH legitimacy audit; typer + asyncpg + structlog already in workspace from Phase 3-4 |
</threat_model>

<verification>
- `nx run knowledge-ingest:test --args="-m integration -v"` exits 0 (all pipeline tests pass)
- `uv run python -m svc_knowledge_ingest --help` lists run/bootstrap/validate
- `python -c "import yaml; yaml.safe_load(open('.github/workflows/reindex.yml'))"` exits 0
- `mkdocs build --strict` exits 0
- 8 knowledge-layer MD pages exist
- A/B eval deliverable + testset committed
- Phase 5 ROADMAP box marked complete with date + 10 plans listed
- Manual spot-check task 5 returned "approved" with reject rate < 20%
- KNW-03, KNW-04, KNW-07, TRN-01 requirements closed
- SC#3 (idempotent reindex) verified via test_reindex_idempotent
</verification>

<success_criteria>
- 6 atomic commits: `feat(05-10-...):` × 3 + `ci(05-10-...):` × 1 + `docs(05-10-...):` × 2
- KNW-03 deliverable: `docs/eval/rag-ab-test-bge-m3-vs-e5.md` with metrics + decision
- KNW-04 docs side: 8 MkDocs pages IT+EN + nav wired
- KNW-07 SC#3: idempotent reindex verified via integration test
- TRN-01: ingest_state tracking verified
- Phase 5 ROADMAP complete + sign-off
- All A/B eval acceptance gates either met (BGE-M3 chosen with delta ≥3pp on ≥2 metrics) OR documented "comparable, default BGE-M3 per MIT + multimodal" per D-71 fallback
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-10-ingest-service-cli-ci-eval-docs-SUMMARY.md` when done with: pipeline test counts, A/B eval winner + delta, MkDocs page list, ROADMAP commit hash, KNW-03/04/07 + TRN-01 closure confirmation, manual spot-check reject rate.
</output>
