---
phase: 5
slug: knowledge-layer-rag-graph
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-18
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Sourced from `05-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.24+ (asyncio_mode = "auto") |
| **Config file** | `packages/sft-knowledge/pyproject.toml` + `services/knowledge-ingest/pyproject.toml` |
| **Quick run command** | `nx run sft-knowledge:test --args="-m 'not integration and not gpu'"` |
| **Full suite command** | `nx run-many --target=test --projects=sft-knowledge,knowledge-ingest` |
| **Estimated runtime** | ~5s quick / ~3min full (with testcontainers Qdrant+Neo4j+PG) |

---

## Sampling Rate

- **After every task commit:** Run `nx run sft-knowledge:test --args="-m 'not integration and not gpu'"` (~5s)
- **After every plan wave:** Run `nx run-many --target=test --projects=sft-knowledge,knowledge-ingest` (~3min)
- **Before `/gsd:verify-work`:** Full suite + A/B eval script must be green
- **Max feedback latency:** 5 seconds (unit tests); 180 seconds (integration with testcontainers)

---

## Per-Task Verification Map

| Req ID | Behavior | Plan | Wave | Test Type | Automated Command | Status |
|--------|----------|------|------|-----------|-------------------|--------|
| KNW-01 | 4 Qdrant collections bootstrapped idempotently | 05-04 | 2 | integration | `pytest -m integration packages/sft-knowledge/tests/test_qdrant_indexer.py::test_collection_bootstrap_idempotent` | ⬜ pending |
| KNW-02 | BGE-M3 embedding produces 1024-d dense + SparseVector | 05-07 | 3 | unit | `pytest packages/sft-knowledge/tests/test_semantic_chunker.py` | ⬜ pending |
| KNW-03 | A/B eval NDCG@10 BGE-M3 ≥ 0.75 (natural IT) + cross-lingual Recall@10 ≥ 0.70 | 05-10 | 4 | integration (offline batch) | `python services/knowledge-ingest/scripts/run_ab_eval.py` | ⬜ pending |
| KNW-04 | MarkdownParser parses all 41 SOPs without error; DocumentParser ABC enforced | 05-01 | 1 | unit | `pytest packages/sft-knowledge/tests/test_markdown_parser.py::test_parse_all_41_sops` | ⬜ pending |
| KNW-05 | Every indexed chunk has source_uri, chunk_idx, version, lang, acl_level, sop_id | 05-08 | 3 | integration | `pytest -m integration packages/sft-knowledge/tests/test_qdrant_indexer.py::test_provenance_fields_complete` | ⬜ pending |
| KNW-06 (SC #2) | operator role cannot retrieve `restricted` chunk | 05-09 | 4 | integration | `pytest -m integration packages/sft-knowledge/tests/test_acl_enforcement.py::test_operator_cannot_see_restricted` | ⬜ pending |
| KNW-07 (SC #3) | Re-ingest unchanged file = 0 new Qdrant points + 0 new Neo4j nodes | 05-10 | 4 | integration | `pytest -m integration services/knowledge-ingest/tests/test_ingest_pipeline.py::test_reindex_idempotent` | ⬜ pending |
| KNW-08 (SC #4) | Neo4j graph: all FailureModes have ≥1 SOP; traversal returns valid SOP | 05-08 | 3 | integration | `pytest -m integration packages/sft-knowledge/tests/test_neo4j_builder.py::test_graph_ci_validator` | ⬜ pending |
| KNW-09 | Hybrid retrieval returns fused+reranked results; scores in [0,1] | 05-09 | 4 | integration | `pytest -m integration packages/sft-knowledge/tests/test_retrieval_pipeline.py::test_hybrid_retrieval_returns_ranked` | ⬜ pending |
| KNW-01+SC #1 | Italian query retrieves correct English SOP chunk (cross-lingual E2E) | 05-09 | 4 | integration | `pytest -m integration packages/sft-knowledge/tests/test_crosslingual_e2e.py::test_it_query_returns_en_sop` | ⬜ pending |
| TRN-01 | `ingest_state` PG tracks `indexed_at` per source_uri; stale scaffold present | 05-10 | 4 | integration | `pytest -m integration services/knowledge-ingest/tests/test_ingest_pipeline.py::test_ingest_state_tracked` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `packages/sft-knowledge/pyproject.toml` — pytest + pytest-asyncio + pytest-cov configured (`asyncio_mode = "auto"`)
- [ ] `packages/sft-knowledge/tests/conftest.py` — shared fixtures: `qdrant_client` (testcontainer Qdrant 1.16+), `neo4j_driver` (testcontainer Neo4j 5.24 + APOC), `bge_m3_embedder` (lazy singleton CPU)
- [ ] `services/knowledge-ingest/tests/conftest.py` — additional fixture: `pg_pool` (asyncpg, testcontainer PG with TimescaleDB extension)
- [ ] Test stubs:
  - `packages/sft-knowledge/tests/test_markdown_parser.py` — covers KNW-04, KNW-05
  - `packages/sft-knowledge/tests/test_semantic_chunker.py` — covers KNW-02 (unit, mock embed)
  - `packages/sft-knowledge/tests/test_qdrant_indexer.py` — covers KNW-01, KNW-05 (integration)
  - `packages/sft-knowledge/tests/test_neo4j_builder.py` — covers KNW-08 (integration)
  - `packages/sft-knowledge/tests/test_retrieval_pipeline.py` — covers KNW-09 (integration)
  - `packages/sft-knowledge/tests/test_acl_enforcement.py` — covers KNW-06 SC #2 (integration)
  - `packages/sft-knowledge/tests/test_crosslingual_e2e.py` — covers SC #1 (integration)
  - `services/knowledge-ingest/tests/test_ingest_pipeline.py` — covers KNW-07, TRN-01 (integration)
- [ ] `tests/data/rag_eval/testset.jsonl` — A/B eval ground truth (generated by `generate_rag_testset.py` script, committed to repo, seed=42 deterministic)
- [ ] Framework install (Wave 1 first task): `uv add "qdrant-client[fastembed]>=1.16" FlagEmbedding "llama-index-core>=0.11" "llama-index-embeddings-huggingface>=0.3" "neo4j>=5.24,<7" python-frontmatter "pytest>=8" pytest-asyncio "testcontainers>=4"`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BGE-M3 vs multilingual-e5-large A/B selection decision recorded in `docs/eval/rag-ab-test-bge-m3-vs-e5.md` | KNW-03 | The selection criterion is justified prose (not a binary assertion); the script runs automatically but the markdown deliverable + chart must be reviewed for completeness | Reviewer reads `docs/eval/rag-ab-test-bge-m3-vs-e5.md`; confirms: (a) metrics table side-by-side, (b) Mermaid chart per query type, (c) "We choose X because..." paragraph, (d) acceptance gates documented |
| Manual spot-check 10% of synthetic test set (12 queries) | KNW-03 | LLM-generated queries can have circular bias; human spot-check validates realism + ground-truth accuracy | Reviewer runs `python services/knowledge-ingest/scripts/spot_check_testset.py --sample-rate=0.10 --seed=42`; marks each: query realistic? + gold chunk correct? Reject rate must be < 20% (else regenerate testset with revised prompt) |
| MkDocs `docs/knowledge-layer/*.md` IT+EN parallel pages | KNW-04 docs side | Documentation completeness check | `mkdocs build --strict` passes + manual review of architecture, retrieval-pipeline, acl-model, eval-results pages in both languages |

---

## Validation Sign-Off

- [ ] All 11 requirement IDs (KNW-01..09 + TRN-01) mapped to automated tests or Wave 0 dependencies
- [ ] Sampling continuity: every plan has ≥1 test → no 3 consecutive tasks without automated verify
- [ ] Wave 0 (Plan 05-01) covers all MISSING test file references before downstream waves
- [ ] No watch-mode flags in CI test commands
- [ ] Feedback latency < 5s (quick) / < 180s (full integration)
- [ ] All 5 ROADMAP Success Criteria (#1 cross-lingual, #2 ACL non-leak, #3 idempotent reindex, #4 graph traversal, #5 A/B eval decision) have explicit automated tests
- [ ] `nyquist_compliant: true` set in frontmatter after Wave 0 complete + first integration test green

**Approval:** pending (gsd-plan-checker will verify Dimension 8 coverage)
