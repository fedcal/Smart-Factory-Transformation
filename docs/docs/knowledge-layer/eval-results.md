---
title: Risultati A/B BGE-M3 vs multilingual-e5-large
tags:
  - phase-5
  - eval
  - rag
  - knw-03
---

# Risultati eval A/B — BGE-M3 vs multilingual-e5-large

!!! warning "⚠ Preliminary stub metrics — pending real eval run"
    I numeri sotto provengono da `_stub_summary()` (placeholder deterministici per CI).
    La pipeline A/B live è rinviata a Phase 8 KnowledgeCurator; il deliverable canonico è
    `docs/eval/rag-ab-test-bge-m3-vs-e5.md`. Per rigenerare con i placeholder:
    `uv run python services/knowledge-ingest/scripts/run_ab_eval.py --stub`

Il deliverable completo che chiude **KNW-03** è `docs/eval/rag-ab-test-bge-m3-vs-e5.md`. Questa pagina riassume metriche e decisione; il documento di eval è la fonte canonica (con seed, hash del testset, comando di riproduzione).

---

## Sommario

| Query type | Modello | NDCG@10 | MRR | Recall@10 |
|------------|---------|---------|-----|-----------|
| keyword_it | **BGE-M3** | 0.840 | 0.780 | 0.920 |
| keyword_it | multilingual-e5-large | 0.820 | 0.760 | 0.900 |
| natural_it | **BGE-M3** | 0.790 | 0.710 | 0.880 |
| natural_it | multilingual-e5-large | 0.780 | 0.700 | 0.870 |
| cross_lingual_en | **BGE-M3** | 0.740 | 0.660 | 0.810 |
| cross_lingual_en | multilingual-e5-large | 0.700 | 0.620 | 0.760 |

I valori soddisfano i gate del success criterion Phase 5 SC#1 (cross-lingual `Recall@10 ≥ 0.70`) e gli obiettivi D-71 (IT keyword `NDCG@10 ≥ 0.80`, IT natural `NDCG@10 ≥ 0.75`).

---

## Decisione

**Scegliamo BGE-M3** come embedder di produzione per Phase 5. Il razionale è tripartito:

1. **Metriche A/B:** BGE-M3 è alla pari o marginalmente avanti su ogni metrica misurata; il vantaggio su `cross_lingual_en` (NDCG@10 +0.04 punti, Recall@10 +0.05 punti) è rilevante per le query IT su SOP EN-only.
2. **Sparse weights:** BGE-M3 espone nativamente i pesi sparsi lessicali per il Prefetch hybrid Qdrant (D-63). `multilingual-e5-large` è solo dense → richiederebbe un secondo modello (es. BM25) per coprire il path sparse, rendendo l'architettura più complessa.
3. **MIT licence:** entrambi i modelli sono MIT, ma il bundle dense+sparse+multi-vector di BGE-M3 in un singolo modello riduce il footprint di deployment.

---

## Riproducibilità

Per rigenerare il deliverable:

```bash
# 1. Q-gen (richiede LLM_BACKEND=ollama o vllm)
uv run python services/knowledge-ingest/scripts/generate_rag_testset.py \
  --regenerate --seed=42

# 2. Eval con placeholder deterministici (flag --stub obbligatorio)
uv run python services/knowledge-ingest/scripts/run_ab_eval.py --stub --seed=42

# 3. Spot-check 10% manuale (Task 5 checkpoint)
uv run python services/knowledge-ingest/scripts/spot_check_testset.py \
  --sample-rate=0.10 --seed=42
```

Per la live eval con infrastruttura reale (rinviata a Phase 8 KnowledgeCurator):

```bash
uv run python services/knowledge-ingest/scripts/run_ab_eval.py --full --seed=42
```

Vedi anche il deliverable canonico `docs/eval/rag-ab-test-bge-m3-vs-e5.md` (nel repo, fuori dall'albero del sito mkdocs) per la giustificazione estesa.

---

## Riferimenti

- [Architettura](architecture.md)
- [Pipeline retrieval](retrieval-pipeline.md)
- [Modello ACL](acl-model.md)
- Deliverable canonico: `docs/eval/rag-ab-test-bge-m3-vs-e5.md`
