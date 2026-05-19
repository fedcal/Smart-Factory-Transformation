---
phase: 05-knowledge-layer-rag-graph
verified: 2026-05-19T15:00:00Z
status: gaps_found
score: 7/10 truths verified (5 SC + 5 supplementary; 2 BLOCKER + 1 WARNING gap)
overrides_applied: 0
gaps:
  - truth: "KNW-09 hybrid retrieval is safe to expose to LLM agents (TraverseGraphTool is injection-proof)"
    status: failed
    reason: "TraverseGraphTool._arun() accepts arbitrary str for seed_label and relation_path and interpolates them directly into Cypher. Pydantic Literal whitelist validation only runs at args_schema/ainvoke() entry path; a direct call to _arun (which the docstring of _run explicitly invites: `await tool._arun(...)`) bypasses it. Verifier reproduced the bypass: payload seed_label='Machine) DETACH DELETE n MATCH (x', relation_path=['HAS_PART'] composes the cypher `MATCH (n:Machine) DETACH DELETE n MATCH (x {id: $seed_id})-[:HAS_PART*1..3]->(m) RETURN DISTINCT m LIMIT 100` and runs it on the driver. On a live Neo4j this destroys the graph."
    artifacts:
      - path: "packages/sft-knowledge/src/sft_knowledge/tools/graph.py"
        issue: "_arun signature accepts unvalidated str/list[str]; defense-in-depth Pydantic re-validation missing (lines 91-122)"
    missing:
      - "Re-validate inputs inside _arun via TraverseGraphInput(...) before composing Cypher (defense-in-depth)"
      - "Test that asserts ValidationError on _arun(seed_label='Machine) MATCH (x', ...)"
      - "Remove the misleading `_run` docstring hint that callers may invoke `_arun` directly; or make `_arun` accept only a validated input object"
  - truth: "KNW-07 incremental reindex never produces silent state drift (orchestrator and parser agree on source_uri)"
    status: partial
    reason: "Two independent implementations of source_uri derivation: `_derive_source_uri` in services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py uses parents[4], MarkdownParser in packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py uses parents[5]. They happen to converge to the workspace root TODAY, but the duplication is fragile (worktree / virtualenv / reorg can break it) and the fallback branches differ semantically (`.lstrip(os.sep)` vs `.lstrip('/')`) — cross-platform divergent. If the two ever drift, `state_store.get(URI_A)` returns None forever, `state_store.upsert(URI_B)` lands on a different row, and KNW-07 SC#3 (incremental reindex) silently degrades to full reindex with hidden double-rows. No test asserts equality between the two derivations."
    artifacts:
      - path: "services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py"
        issue: "Lines 55-76 duplicate parser-side source_uri logic with subtly different fallback"
      - path: "packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py"
        issue: "Lines 37-40, 123-128 own the canonical derivation but expose no public helper for the orchestrator to import"
    missing:
      - "Extract a single canonical `derive_source_uri(path)` in sft_knowledge (e.g. sft_knowledge.uri) and call it from BOTH parser and orchestrator"
      - "Add a parametrized test asserting `derive_source_uri(p) == MarkdownParser().parse(p).source_uri` across workspace/tmp/symlink paths"
  - truth: "KNW-03 A/B evaluation results documented in docs/ are real measurements, not stub numbers"
    status: partial
    reason: "Success criterion SC#5 is literally satisfied by docs/eval/rag-ab-test-bge-m3-vs-e5.md and docs/docs/knowledge-layer/eval-results.md, both of which include the metrics table and a justified decision. HOWEVER: the numbers in those tables come from `_stub_summary()` (services/knowledge-ingest/scripts/run_ab_eval.py:230-243) — six hard-coded NDCG/MRR/Recall tuples. The canonical doc has a `Preliminary run notice` disclaimer banner; the MkDocs IT/EN mirror pages publish the same numbers WITHOUT the disclaimer. `--skip-eval` defaults to True and `--full` raises NotImplementedError. The acceptance gates (NDCG@10 ≥ 0.80 keyword_it etc.) are met by the stubs by construction. This is a SC#5 literal-pass but evidence-fail: KNW-03 ('A/B evaluation su corpus tessile IT+EN documentato in `docs/`') is documented but the documentation describes a measurement that has never actually been run."
    artifacts:
      - path: "services/knowledge-ingest/scripts/run_ab_eval.py"
        issue: "Default --skip-eval=True returns _stub_summary(); --full path is NotImplementedError"
      - path: "docs/docs/knowledge-layer/eval-results.md"
        issue: "Publishes stub numbers as if measured; no disclaimer banner (the parallel docs/eval/rag-ab-test-bge-m3-vs-e5.md does have one)"
    missing:
      - "Either: implement the live A/B eval path (BGE-M3 vs multilingual-e5-large on the real testset) and re-publish the numbers; OR add the same `Preliminary run notice` banner to docs/docs/knowledge-layer/eval-results.md and its EN mirror so MkDocs readers are not misled"
      - "Change --skip-eval default to False or rename it (e.g. --stub) so a forgotten flag does not silently produce fake metrics in CI"
deferred:
  - truth: "Full PDF/DOCX/HTML parsers implemented for KNW-04"
    addressed_in: "Phase 8 (Agents — Knowledge & Training)"
    evidence: "ROADMAP Phase 5 KNW-04 scope note (line 113): 'Phase 5 ships MarkdownParser only. The DocumentParser ABC enables PDF/DOCX/HTML parsers in Phase 8 KnowledgeCurator (scoping deviation from literal KNW-04; documented in CONTEXT.md D-67).'"
---

# Phase 5: Knowledge Layer (RAG + Graph) Verification Report

**Phase Goal:** Qdrant collections with BGE-M3 hybrid retrieval, a document ingest pipeline with provenance and access control, incremental re-indexing, and a Neo4j/Memgraph entity graph are operational and validated for bilingual Italian-English retrieval quality.

**Verified:** 2026-05-19T15:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### ROADMAP Success Criteria

| #   | Truth                                                                                          | Status        | Evidence                                                                                                                                                                                                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SC1 | Italian query → English SOP chunk via cross-lingual eval suite                                 | VERIFIED      | `packages/sft-knowledge/tests/test_crosslingual_e2e.py` exists (marked integration+gpu); `RetrievalPipeline.search` is language-agnostic via BGE-M3 multilingual encoder; ACL-aware                                                                                                                                                    |
| SC2 | Every chunk carries source_uri/page/version/lang/acl_level; operator role cannot see restricted | VERIFIED      | `QdrantIndexer.upsert_batch` payload includes the 7 provenance fields (`source_uri`, `chunk_idx`, `version`, `lang`, `acl_level`, `asset_family`, `sop_id`); `build_acl_filter` enforces engine-level pre-filter; `test_acl_enforcement.py` covers operator-cannot-see-restricted; ROLE_TO_ACL is D-63 LOCKED                            |
| SC3 | Incremental reindex on document update; full reindex not triggered                              | PARTIAL       | `content_hash` early-exit gate exists in `pipeline.ingest_file` lines 169-181; `IngestStateStore` UPSERT lands only after dual-write success; `.github/workflows/reindex.yml` uses `git diff` path filter. **BUT** orchestrator/parser source_uri derivation duplicated (CR-02) — silent state drift risk; PG `acl_level` has no CHECK constraint (WR-07) |
| SC4 | Entity graph Machine→Part→FailureMode→SOP for all asset classes; traversal returns SOP          | VERIFIED      | `Neo4jGraphBuilder._MERGE_*_CYPHER` constants cover Machine, Part, FailureMode, SOP with idempotent UNWIND MERGE; `merge_sop` writes DOCUMENTED_BY edges; 32 failure modes in `failure_modes.yaml`; `TraverseGraphTool` exists. Caveat: SC#4 says "valid SOP for a given failure mode" — works, but TraverseGraphTool is unsafe (CR-01) |
| SC5 | BGE-M3 vs multilingual-e5-large A/B documented in docs/ with justified decision                 | PARTIAL       | `docs/eval/rag-ab-test-bge-m3-vs-e5.md` + 4 MkDocs pages (IT/EN) exist with metrics tables, NDCG@10/MRR/Recall@10 partition, and decision text. **Numbers are deterministic stubs from `_stub_summary()`**; only the canonical doc carries the "Preliminary run notice" disclaimer; MkDocs mirror pages do not                          |

**ROADMAP SC Score:** 3/5 fully VERIFIED, 2/5 PARTIAL.

### Supplementary Truths (PLAN frontmatter + REQUIREMENTS)

| #   | Truth                                                                       | Status     | Evidence                                                                                                                                                       |
| --- | --------------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| T1  | sft-knowledge SDK exposes the 11-symbol public surface (D-67/D-70)          | VERIFIED   | `packages/sft-knowledge/src/sft_knowledge/__init__.py` exports all 22 symbols incl. `DocumentParser`, `MarkdownParser`, `ParsedDoc`, `RagSearchTool`, `TraverseGraphTool`, `QdrantLongTermMemory` |
| T2  | All 40 SOPs in synthetic-corpus parse with reviewed status                  | VERIFIED   | Verifier ran `MarkdownParser` on all 40 files: 40 OK / 0 skipped / 0 failed. (Note: PLAN says 41; actual corpus has 40 SOP-* files — minor count drift)            |
| T3  | 4 Qdrant collections bootstrapped idempotently (KNW-01)                     | VERIFIED   | `scripts/qdrant-bootstrap.py` creates `sop`/`manuals`/`troubleshooting`/`training` with named dense (1024-d cosine) + sparse + 7 payload indexes; idempotent     |
| T4  | BGE-M3 hybrid retrieval (dense+sparse+rerank) with RRF fusion (KNW-09)      | VERIFIED   | `RetrievalPipeline.search` builds Prefetch(dense) + Prefetch(sparse) with `FusionQuery(Fusion.RRF)`, optional `BgeReranker.rerank` cross-encoder; `--rerank=True` default |
| T5  | `failure_modes.yaml` has ≥30 entries (KNW-08)                               | VERIFIED   | 32 entries (`grep -c "^  - id:" failure_modes.yaml = 32`); CI validator `scripts/validate-failure-modes.py` exists                                              |

**Aggregate Score:** 8/10 truths VERIFIED (5 SC + 5 supplementary, with 2 PARTIAL on SC3+SC5 and 1 BLOCKER on the CR-01 dimension of T4/KNW-09 safety).

---

## Requirements Coverage

| Requirement | Source Plan                                                                                 | Description                                                                                  | Status      | Evidence                                                                                                                                          |
| ----------- | ------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| KNW-01      | 05-04                                                                                       | Qdrant self-hosted, 4 collections per category                                              | SATISFIED   | `scripts/qdrant-bootstrap.py` creates 4 collections; `_COLLECTIONS = {sop, manuals, troubleshooting, training}` in stores/qdrant.py:42             |
| KNW-02      | 05-07                                                                                       | BGE-M3 (MIT) default + multilingual-e5-large adapter                                         | SATISFIED   | `BgeM3Embedder` (FlagEmbedding + fastembed fallback) with dense+sparse; e5 adapter referenced in `run_ab_eval.py` `_stub_summary`                  |
| KNW-03      | 05-10                                                                                       | A/B evaluation on tessile IT+EN corpus documented in docs/                                   | PARTIAL     | Documents exist (`docs/eval/rag-ab-test-bge-m3-vs-e5.md` + 4 MkDocs pages) but metrics are stubs; only canonical doc has disclaimer (see gap 3)    |
| KNW-04      | 05-01, 05-10                                                                                | Pipeline PDF/DOCX/HTML/MD → chunking → embedding → upsert                                    | PARTIAL     | MD path complete (parser + chunker + embedder + indexer); PDF/DOCX/HTML deferred to Phase 8 KnowledgeCurator (documented scope deviation per ROADMAP line 113 + D-67) |
| KNW-05      | 05-01, 05-08                                                                                | Provenance obbligatoria: source_uri, page, version, lang                                     | SATISFIED   | `QdrantIndexer` payload writes all 7 provenance fields per chunk; `Chunk` model carries metadata; payload index created on `source_uri`/`version`/`lang` |
| KNW-06      | 05-02, 05-09                                                                                | Access control tag per chunk (public/internal/restricted) rispettato a query time            | SATISFIED   | `ROLE_TO_ACL` (D-63 LOCKED) + `build_acl_filter` applied as Qdrant engine-level pre-filter (not Python post-filter); `migrate-sop-acl.py` migrated all 40 SOPs; `test_acl_enforcement.py` covers operator-cannot-see-restricted. WR-07: PG `acl_level` lacks CHECK constraint — defense in depth gap |
| KNW-07      | 05-06, 05-10                                                                                | Reindex incrementale via watcher / webhook Git                                               | PARTIAL     | content_hash gate + `IngestStateStore` + `.github/workflows/reindex.yml` push+path-filter implemented; **source_uri derivation duplicated** (CR-02) creating silent-drift risk (see gap 2). Also CR-03: blocking `path.read_bytes()` inside `async def ingest_file` |
| KNW-08      | 05-03, 05-05, 05-08                                                                         | Entity graph (Neo4j) per asset-procedura-difetto-causa                                       | SATISFIED   | Neo4j 5.24-community in compose + Helm; `Neo4jGraphBuilder` writes Machine/Part/FailureMode/SOP/HAS_PART/HAS_FAILURE_MODE/DOCUMENTED_BY; 32 failure modes in registry |
| KNW-09      | 05-09                                                                                       | Hybrid retrieval (dense BGE-M3 + sparse BM25) con rerank opzionale                          | PARTIAL     | Pipeline + Tools + Memory wired correctly. **BUT `TraverseGraphTool._arun` is Cypher-injectable** when called directly (verifier reproduced bypass) — see gap 1. RagSearchTool itself is safe (Pydantic Literal on category, ACL fail-closed on roles) |
| TRN-01      | 05-06, 05-10                                                                                | KnowledgeCurator ingest + dedup + stale signalling (scaffold)                                | SATISFIED   | `ingest_state` table tracks `indexed_at` per source_uri; `IngestStateRow` Pydantic-frozen; query helper `list_stale_rows` not yet implemented but the schema and store contract are in place — TRN-01 in this phase is scaffold-only by ROADMAP scope    |

**Coverage:** 10/10 declared requirement IDs accounted for. None orphaned. 4 PARTIAL, 6 SATISFIED.

---

## Required Artifacts

| Artifact                                                                                       | Expected                                              | Status   | Details                                                                                              |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------- | -------- | ---------------------------------------------------------------------------------------------------- |
| `packages/sft-knowledge/src/sft_knowledge/__init__.py`                                         | SDK public surface                                    | VERIFIED | 22 symbols exported; matches PLAN promises                                                            |
| `packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py`                                 | MarkdownParser with frontmatter + sections           | VERIFIED | Parses all 40 SOPs; produces `ParsedDoc(source_uri, lang, version, frontmatter, sections, ...)`      |
| `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`                                 | BGE-M3 dense+sparse encoder                          | VERIFIED | `BgeM3Embedder` with FlagEmbedding primary + fastembed fallback (degraded dense-only)                |
| `packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`                                | LlamaIndex SemanticSplitterNodeParser wrapper        | VERIFIED | `SemanticChunker.chunk(ParsedDoc) -> list[Chunk]` with heading_path propagation                       |
| `packages/sft-knowledge/src/sft_knowledge/stores/qdrant.py`                                    | QdrantIndexer batch upsert + deterministic IDs       | VERIFIED | `point_id(source_uri, chunk_idx, text)` sha256→UUID; `upsert_batch` flushes every 100                |
| `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py`                                     | Neo4jGraphBuilder UNWIND MERGE                       | VERIFIED | All Cypher constants module-level (no f-string on data); merge_sop writes DOCUMENTED_BY edges        |
| `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`                               | Hybrid Prefetch+RRF + ACL pre-filter                 | VERIFIED | `RetrievalPipeline.search` with FusionQuery(Fusion.RRF), composite Filter (ACL + lang + sop_ids)     |
| `packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py`                               | BgeReranker bge-reranker-v2-m3 cross-encoder         | VERIFIED | `BgeReranker.rerank(query, hits) -> list[(hit, score)]`                                              |
| `packages/sft-knowledge/src/sft_knowledge/tools/rag.py`                                        | RagSearchTool LangChain BaseTool                     | VERIFIED | Pydantic Literal category whitelist; async-only `_run` raises NotImplementedError                    |
| `packages/sft-knowledge/src/sft_knowledge/tools/graph.py`                                      | TraverseGraphTool LangChain BaseTool                 | STUB-EQUIVALENT-FOR-SAFETY | Functionally implemented but Cypher-injectable through `_arun` direct call (CR-01)                  |
| `packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py`                          | QdrantLongTermMemory Memory ABC impl                 | VERIFIED | `query()` wraps RetrievalPipeline with ACL roles default `["operator"]` (fail-safe); `store()` raises |
| `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`                               | ingest_file orchestrator                             | VERIFIED-WITH-WARNINGS | Implements content_hash gate + dual-write Neo4j-first + state UPSERT; CR-02 + CR-03 active warnings |
| `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`                               | Typer CLI run/bootstrap/validate                     | VERIFIED | Three commands wired; lazy imports for fast --help                                                    |
| `services/knowledge-ingest/src/svc_knowledge_ingest/state.py`                                  | IngestStateStore asyncpg                             | VERIFIED | All SQL as module-level constants; Pydantic IngestStateRow (frozen + tz-aware enforced)              |
| `services/knowledge-ingest/scripts/run_ab_eval.py`                                             | A/B eval deliverable                                 | VERIFIED-WITH-WARNINGS | Default --skip-eval=True returns hardcoded `_stub_summary` (IN-05); --full raises NotImplementedError |
| `scripts/qdrant-bootstrap.py`                                                                  | Idempotent collection bootstrap                      | VERIFIED | 4 collections + 7 payload indexes per collection                                                      |
| `scripts/neo4j-bootstrap.py`                                                                   | Idempotent UNIQUE constraint bootstrap               | VERIFIED | Module exists; default password `neo4j/devpassword` (CR-04 inconsistency)                            |
| `scripts/migrate-sop-acl.py`                                                                   | One-shot ACL migration                               | VERIFIED | All 40 SOPs have `acl_level` frontmatter post-migration                                              |
| `scripts/validate-failure-modes.py`                                                            | CI validator for orphan FailureMode                  | VERIFIED-WITH-WARNINGS | Module exists; IN-04: substring-match bidirectional too permissive (false negative on orphans)        |
| `infra/migrations/timescale/006_create_ingest_state.sql`                                       | knowledge.ingest_state PG table                      | VERIFIED-WITH-WARNINGS | Table+index+conditional GRANT; WR-07: no CHECK constraint on `acl_level`                              |
| `infra/compose/core.yml` (neo4j service)                                                       | Neo4j 5.24 dev compose service                       | VERIFIED-WITH-WARNINGS | neo4j:5.24-community with APOC; WR-09: APOC file IO enabled by default + CR-04 default password drift |
| `infra/helm/charts/neo4j/`                                                                     | Helm chart skeleton                                  | VERIFIED-WITH-WARNINGS | Chart+values+statefulset present; WR-10: no production guard when existingSecret absent              |
| `.github/workflows/reindex.yml`                                                                | Path-filtered reindex CI                             | VERIFIED-WITH-WARNINGS | Service containers + git diff filter; WR-08: shell-unsafe filename join                              |
| `docs/eval/rag-ab-test-bge-m3-vs-e5.md`                                                        | Canonical A/B deliverable                            | VERIFIED-WITH-WARNINGS | Has "Preliminary run notice" disclaimer; stub numbers                                                 |
| `docs/docs/knowledge-layer/{architecture,retrieval-pipeline,acl-model,eval-results}.md` (IT)   | 4 MkDocs knowledge pages                             | VERIFIED-WITH-WARNINGS | All 4 pages exist; eval-results.md re-publishes stub numbers WITHOUT disclaimer                      |
| `docs/docs/en/knowledge-layer/*.md`                                                            | EN mirrors                                            | VERIFIED-WITH-WARNINGS | Same — eval-results.md EN mirror also lacks disclaimer                                                |

---

## Key Link Verification

| From                              | To                              | Via                                            | Status      | Details                                                                                                                          |
| --------------------------------- | ------------------------------- | ---------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------- |
| `RetrievalPipeline.search`        | Qdrant `query_points`           | `prefetch=[Prefetch(dense),Prefetch(sparse)]` | WIRED       | Lines 237-263 in pipeline.py: composite filter passed to each Prefetch leg + FusionQuery(RRF)                                    |
| `ingest_file`                     | `Neo4jGraphBuilder.merge_sop`   | `await neo4j_builder.merge_sop(parsed, fm_ids)` | WIRED      | pipeline.py:217; ordered BEFORE Qdrant upsert (D-68 dual-write order)                                                            |
| `ingest_file`                     | `QdrantIndexer.upsert_batch`    | `await qdrant_indexer.upsert_batch(chunks,...)` | WIRED      | pipeline.py:221; on failure state row is NOT upserted (recovery via content_hash mismatch on next run)                           |
| `ingest_file`                     | `IngestStateStore.upsert`       | `await state_store.upsert(...)`                | WIRED       | pipeline.py:232-239; only after both writes succeed                                                                              |
| `RagSearchTool._arun`             | `RetrievalPipeline.search`      | `await self._pipeline.search(...)`             | WIRED       | tools/rag.py PrivateAttr injection                                                                                               |
| `TraverseGraphTool._arun`         | Neo4j `session.run(cypher, ...)`| f-string Cypher                                | UNSAFE-WIRED| tools/graph.py:118-127 composes Cypher with `seed_label`/`rel_pipe` interpolation; `seed_id` correctly via `$param`; BUT direct `_arun` call bypasses Literal validation (CR-01) |
| `sft_agents.memory.LongTermMemory`| `QdrantLongTermMemory`          | `try: from sft_knowledge.memory import ...`    | WIRED       | sft_agents/memory/__init__.py:26-31; WR-11: silent ImportError → StubLongTermMemory downgrade without warning                    |
| reindex.yml                       | `knowledge-ingest:run --files`  | `paste -sd, changed.txt` + `--args=...`        | WIRED-UNSAFE| WR-08: filename injection possible via unquoted shell expansion                                                                  |
| `Chunk.metadata`                  | Qdrant payload                  | `QdrantIndexer.upsert_batch` payload dict     | WIRED       | All 7 provenance fields (source_uri, chunk_idx, version, lang, acl_level, asset_family, sop_id) written + payload-indexed       |

---

## Data-Flow Trace (Level 4)

| Artifact                  | Data Variable          | Source                                                                                  | Produces Real Data | Status      |
| ------------------------- | ---------------------- | --------------------------------------------------------------------------------------- | ------------------ | ----------- |
| `RetrievalPipeline.search`| `dense_vec`, `sparse_vec` | `BgeM3Embedder.encode([query])` (real model BGE-M3, lazy-loaded via FlagEmbedding/fastembed) | YES               | FLOWING     |
| `RetrievalPipeline.search`| `fused_hits`           | `client.query_points(...)` against real Qdrant collection                              | YES (live)        | FLOWING     |
| `ingest_file`             | `chunks`               | `SemanticChunker.chunk(parsed)` via real LlamaIndex SemanticSplitter on real frontmatter docs | YES               | FLOWING     |
| `ingest_file`             | `fm_ids`               | `_infer_failure_mode_ids` matched against 32-entry `failure_modes.yaml`                | YES               | FLOWING     |
| `run_ab_eval.py`          | `summary`              | `_stub_summary()` — 6 hardcoded tuples                                                  | NO (stub by default; --full raises NotImplementedError) | STATIC      |
| `eval-results.md` (MkDocs)| metrics table          | Copied from stub numbers                                                                 | NO (no disclaimer)  | HOLLOW_PROP |

---

## Behavioral Spot-Checks

| Behavior                                                       | Command                                                                                                              | Result               | Status |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------- | ------ |
| sft-knowledge unit tests pass                                  | `uv run python -m pytest packages/sft-knowledge/tests/ services/knowledge-ingest/tests/ -m "not integration and not gpu"` | `71 passed, 31 deselected in 1.24s` | PASS   |
| MarkdownParser parses all SOPs                                 | (verifier-run) `await parser.parse(f)` over `simulators/synthetic-corpus/**/SOP-*.md`                               | `40 OK, 0 skipped, 0 failed` | PASS   |
| `failure_modes.yaml` has ≥30 entries                           | `grep -c "^  - id:" packages/sft-domain/src/sft_domain/failure_modes.yaml`                                          | `32`                  | PASS   |
| All 40 SOPs have `acl_level` frontmatter                       | `grep -c "acl_level:" simulators/synthetic-corpus/*/*/*.md`                                                          | `40`                  | PASS   |
| TraverseGraphTool._arun bypass injection check                 | (verifier-run) direct `await tool._arun(seed_label="Machine) DETACH DELETE n MATCH (x", ...)`                       | `Cypher composed: 'MATCH (n:Machine) DETACH DELETE n MATCH (x {id: $seed_id})-[:HAS_PART*1..3]->(m) ...'` | FAIL (CR-01) |
| 4 Qdrant collections declared                                  | `grep -c "sop\|manuals\|troubleshooting\|training" scripts/qdrant-bootstrap.py`                                     | All 4 in `COLLECTIONS` tuple line 49 | PASS   |
| reindex.yml workflow exists                                    | `ls .github/workflows/reindex.yml`                                                                                   | present              | PASS   |

---

## Anti-Patterns Found (cross-referenced with 05-REVIEW.md)

| File                                                                                          | Line     | Pattern                                                              | Severity | Impact                                                                              |
| --------------------------------------------------------------------------------------------- | -------- | -------------------------------------------------------------------- | -------- | ----------------------------------------------------------------------------------- |
| `packages/sft-knowledge/src/sft_knowledge/tools/graph.py`                                     | 91-122   | CR-01 Cypher injection bypass through `_arun` direct call           | BLOCKER  | Destroys Neo4j graph on adversarial input; KNW-09 + agent safety surface fail-open |
| `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py` + `parsers/markdown.py`      | 55-76 / 37-40 | CR-02 source_uri derivation duplicated, fallbacks subtly divergent | BLOCKER  | Silent state drift; KNW-07 SC#3 invariant rotto                                     |
| `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`                              | 169      | CR-03 blocking `path.read_bytes()` in `async def ingest_file`        | WARNING  | Event-loop stalls on 40+ files per reindex; cancellation not propagated             |
| `scripts/neo4j-bootstrap.py` + `infra/compose/core.yml` + `helm/values.yaml` + `__main__.py` | various  | CR-04 inconsistent default passwords (`devpassword` vs `cipassword`)| WARNING  | Cross-component handshake fails by default; hardcoded credentials in repo            |
| `packages/sft-knowledge/src/sft_knowledge/retrieval/pipeline.py`                              | 140, 258 | WR-02 `category` not bound to `_COLLECTIONS` whitelist               | WARNING  | Caller-side loophole in Pipeline (RagSearchTool itself is Literal-bounded)           |
| `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`                                | 168-171  | WR-01 `os.environ` mutation in class __init__                        | WARNING  | Race in pytest-xdist / multi-tenant runtime                                          |
| `packages/sft-knowledge/src/sft_knowledge/stores/neo4j.py`                                    | 296, 313 | WR-03 variable shadowing in `merge_sop`                              | INFO     | Latent bug                                                                            |
| `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`                                | 256      | WR-04 `assert` strippable under `python -O`                          | INFO     | Production invariant disappears under optimization                                   |
| `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`                              | 215-223  | WR-05 CLI run "continue" comment + `raise` contradiction             | WARNING  | Misleading fail-fast/best-effort semantics                                           |
| `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py`                              | 200, 238 | WR-06 acl_level fallback masks parser invariant violation            | WARNING  | T-05-09-01 fail-closed weakened                                                      |
| `infra/migrations/timescale/006_create_ingest_state.sql`                                      | 25       | WR-07 no CHECK constraint on acl_level                               | WARNING  | Direct INSERT with bad acl_level → silent invisibility (MatchAny miss)              |
| `.github/workflows/reindex.yml`                                                               | 144-146  | WR-08 shell injection via filename                                   | WARNING  | PR-controlled filename can break quoting                                             |
| `infra/compose/core.yml` + `helm/values.yaml`                                                 | 66-68 / 26-29 | WR-09 APOC file IO enabled by default                              | WARNING  | Combined with CR-01: read/write arbitrary container files                            |
| `infra/helm/charts/neo4j/templates/statefulset.yaml`                                          | 26-37    | WR-10 no production guard on default password                        | WARNING  | `helm install` without existingSecret deploys devpassword                            |
| `packages/sft-agents/src/sft_agents/memory/__init__.py`                                       | 26-31    | WR-11 silent ImportError → Stub fallback                             | WARNING  | Production with sft-knowledge unavailable: silent retrieval downgrade                |
| `packages/sft-knowledge/src/sft_knowledge/memory/qdrant_long_term.py`                         | 78-91    | WR-12 AsyncQdrantClient never closed                                 | WARNING  | Connection leak in long-running services                                             |
| `packages/sft-knowledge/src/sft_knowledge/retrieval/reranker.py`                              | 135-141  | WR-13 `zip(hits, scores)` truncates silently                         | WARNING  | Diagnosis nightmare on count mismatch                                                 |
| `services/knowledge-ingest/scripts/run_ab_eval.py`                                            | 230-260  | IN-05 `--skip-eval=True` default produces stub numbers as deliverable| WARNING  | KNW-03 docs publish fake measurements                                                |
| `scripts/migrate-sop-acl.py`                                                                  | 117-121  | IN-03 non-atomic write to SOP frontmatter                            | INFO     | Crash mid-write loses SOP content                                                    |
| `scripts/validate-failure-modes.py`                                                           | 117      | IN-04 bidirectional substring match too permissive                   | INFO     | Orphan FailureMode hidden by spurious match                                          |
| `services/knowledge-ingest/src/svc_knowledge_ingest/__main__.py`                              | 70-75    | IN-01 `_require_env` defined but never called                        | INFO     | Dead code; inline patterns duplicate intent                                          |
| `packages/sft-domain/src/sft_domain/failure_modes/_loader.py`                                 | 62-68    | IN-02 docstring "immutable" on mutable dict                          | INFO     | Cached dict in lru_cache can be mutated by any caller, contaminating process         |

---

## Cross-Reference: 05-REVIEW.md Critical Issues vs Success Criteria

| Code Review Finding                          | Invalidates Success Criterion?                                                                                                                              |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **CR-01** TraverseGraphTool Cypher injection | YES (KNW-09 / agent safety). RagSearchTool stays safe (Pydantic Literal), so retrieval primary path is intact. But graph traversal exposed to agents is destructive — must not ship to Phase 6 agents. |
| **CR-02** source_uri divergence              | PARTIAL (KNW-07 SC#3). Works today but the duplication is a latent ticking bomb. Idempotent-reindex invariant only holds while the two implementations agree.                                          |
| **CR-03** blocking I/O in async              | NO (correctness intact). Stalls event loop in 40-file reindex CI runs; not a security issue, but a propagating performance footgun.                                                                       |
| **CR-04** inconsistent default passwords     | NO (compose/CI do work as long as both sides use the same override). Security hygiene + ops UX risk. Phase 5 ROADMAP success criteria do not enforce production hardening (Phase 11 territory).        |

**Net:** CR-01 is the only ROADMAP-blocking critical issue. CR-02 is a latent invariant break on KNW-07.

---

## Gaps Summary

Three structural gaps prevent a clean PASS verdict, despite a functionally complete and tested implementation:

1. **Cypher injection via TraverseGraphTool (BLOCKER for KNW-09 / agent safety).** The `args_schema` Literal whitelist is bypassed by direct `_arun(seed_label=..., ...)` calls — and the `_run` docstring explicitly invites callers to use that path. The verifier reproduced the bypass in-process. Before Phase 6 agents are wired to TraverseGraphTool, `_arun` must re-validate inputs as defense-in-depth.

2. **source_uri derivation duplicated between orchestrator and parser (BLOCKER for KNW-07 SC#3 invariant durability).** Two `parents[N]` walks today converge, tomorrow they may not. The fallback branches already diverge cross-platform. Refactor to a single canonical `derive_source_uri(path)` plus an equality test.

3. **KNW-03 A/B numbers are stubs published as if measured (WARNING — literal SC#5 pass, intent fail).** The canonical eval doc has a "Preliminary run notice" disclaimer; the MkDocs IT/EN mirror pages publish the same stub numbers without it. Either implement the live `--full` path, or propagate the disclaimer to all four eval-results.md surfaces and rename `--skip-eval` so the default is opt-in transparency, not opt-out concealment.

The remaining 21 anti-patterns (WR-01..WR-13, IN-01..IN-06) are mostly hygiene-grade and do not block ROADMAP Phase 5 sign-off, but several (WR-09 APOC file IO, WR-11 silent Stub downgrade, WR-12 unclosed clients) will become real issues in Phase 6+ when agents start exercising the surface area.

---

_Verified: 2026-05-19T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
