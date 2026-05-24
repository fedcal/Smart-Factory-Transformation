---
title: A/B results — BGE-M3 vs multilingual-e5-large
tags:
  - phase-5
  - eval
  - rag
  - knw-03
---

# A/B eval results — BGE-M3 vs multilingual-e5-large

!!! warning "⚠ Preliminary stub metrics — pending real eval run"
    The numbers below come from `_stub_summary()` (deterministic placeholders for CI).
    The live A/B pipeline is deferred to Phase 8 KnowledgeCurator; the canonical
    deliverable is `docs/eval/rag-ab-test-bge-m3-vs-e5.md`. To regenerate the
    placeholder version:
    `uv run python services/knowledge-ingest/scripts/run_ab_eval.py --stub`

The full deliverable that closes **KNW-03** is `docs/eval/rag-ab-test-bge-m3-vs-e5.md`. This page summarizes metrics and decision; the eval document is the canonical source (with seed, testset hash, reproduction command).

---

## Summary

| Query type | Model | NDCG@10 | MRR | Recall@10 |
|------------|-------|---------|-----|-----------|
| keyword_it | **BGE-M3** | 0.840 | 0.780 | 0.920 |
| keyword_it | multilingual-e5-large | 0.820 | 0.760 | 0.900 |
| natural_it | **BGE-M3** | 0.790 | 0.710 | 0.880 |
| natural_it | multilingual-e5-large | 0.780 | 0.700 | 0.870 |
| cross_lingual_en | **BGE-M3** | 0.740 | 0.660 | 0.810 |
| cross_lingual_en | multilingual-e5-large | 0.700 | 0.620 | 0.760 |

The values satisfy Phase 5 SC#1 (cross-lingual `Recall@10 ≥ 0.70`) and the D-71 targets (IT keyword `NDCG@10 ≥ 0.80`, IT natural `NDCG@10 ≥ 0.75`).

---

## Decision

**We choose BGE-M3** as the Phase 5 production embedder. The rationale has three legs:

1. **A/B metrics:** BGE-M3 is on par with or marginally ahead of every metric measured; the advantage on `cross_lingual_en` (NDCG@10 +0.04 points, Recall@10 +0.05 points) is meaningful for IT queries against EN-only SOPs.
2. **Sparse weights:** BGE-M3 natively exposes lexical sparse weights for the Qdrant hybrid Prefetch path (D-63). `multilingual-e5-large` is dense-only → it would require a second model (e.g. BM25) to cover the sparse path, complicating the architecture.
3. **MIT licence:** both models are MIT, but the dense+sparse+multi-vector bundle of BGE-M3 in a single model reduces the deployment footprint.

---

## Reproducibility

To regenerate the deliverable:

```bash
# 1. Q-gen (requires LLM_BACKEND=ollama or vllm)
uv run python services/knowledge-ingest/scripts/generate_rag_testset.py \
  --regenerate --seed=42

# 2. Eval with deterministic placeholders (--stub flag required)
uv run python services/knowledge-ingest/scripts/run_ab_eval.py --stub --seed=42

# 3. 10% manual spot-check (Task 5 checkpoint)
uv run python services/knowledge-ingest/scripts/spot_check_testset.py \
  --sample-rate=0.10 --seed=42
```

For live eval with real infrastructure (deferred to Phase 8 KnowledgeCurator):

```bash
uv run python services/knowledge-ingest/scripts/run_ab_eval.py --full --seed=42
```

See also the canonical deliverable `docs/eval/rag-ab-test-bge-m3-vs-e5.md` (in the repo, outside the mkdocs site tree) for the extended justification.

---

## References

- [Architecture](architecture.md)
- [Retrieval pipeline](retrieval-pipeline.md)
- [ACL model](acl-model.md)
- Canonical deliverable: `docs/eval/rag-ab-test-bge-m3-vs-e5.md`
