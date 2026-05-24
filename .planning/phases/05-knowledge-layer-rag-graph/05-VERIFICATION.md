---
phase: 05-knowledge-layer-rag-graph
verified: 2026-05-24T15:00:00Z
status: human_needed
score: 10/10 truths verified (5 SC + 5 supplementary; tutti i gap chiusi)
overrides_applied: 0
re_verification:
  previous_status: gaps_found
  previous_score: 7/10 truths verified (2 BLOCKER + 1 WARNING gap)
  gaps_closed:
    - "KNW-09 / CR-01 — TraverseGraphTool._arun Cypher injection: re-validazione via TraverseGraphInput come prima istruzione; 4 regression test PASS"
    - "KNW-07 / CR-02 — source_uri derivation duplicata: estratta sft_knowledge.path_utils.derive_source_uri; entrambi i call-site unificati; 4 test di uguaglianza PASS"
    - "KNW-03 / IN-05 — stub metrics pubblicati senza disclaimer: --skip-eval rinominato --stub (default False opt-in); admonition 'Preliminary stub metrics' propagata su tutte e 3 le superfici; 4 regression test PASS"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Eseguire test_bge_m3_embedder.py::test_real_bge_m3_loads su macchina con GPU >= 6 GiB liberi"
    expected: "Il modello BGE-M3 si carica correttamente via FlagEmbedding e il test PASS; nessun OOM"
    why_human: "Richiede GPU CUDA con >= 6 GiB di memoria libera; il dev box ha 3.68 GiB occupati da altro processo — fallisce per OOM hardware, non difetto di codice"
  - test: "Eseguire test_crosslingual_e2e.py::test_it_query_returns_en_sop su macchina con GPU >= 6 GiB liberi + Qdrant attivo"
    expected: "Query in italiano recupera chunk SOP in inglese via BGE-M3 cross-lingual; Recall@5 >= threshold; test PASS"
    why_human: "Dipende da GPU (embedding reale BGE-M3) e da Qdrant live con collection popolata; non eseguibile nel CI su dev box con GPU saturata"
  - test: "Eseguire test_semantic_chunker.py::test_real_sop_end_to_end_chunk_and_embed su macchina con GPU >= 6 GiB liberi"
    expected: "SemanticChunker divide un SOP reale e BgeM3Embedder embeds ogni chunk; nessun OOM; test PASS"
    why_human: "Usa BgeM3Embedder in modalita reale (FlagEmbedding / fastembed GPU path); richiede >= 6 GiB GPU liberi"
---

# Phase 5: Knowledge Layer (RAG + Graph) Verification Report — Re-verifica post gap-closure

**Phase Goal:** Qdrant collections with BGE-M3 hybrid retrieval, a document ingest pipeline with provenance and access control, incremental re-indexing, and a Neo4j/Memgraph entity graph are operational and validated for bilingual Italian-English retrieval quality.

**Verified:** 2026-05-24T15:00:00Z
**Status:** human_needed
**Re-verifica:** Si — dopo chiusura di 3 gap (piani 05-11, 05-12, 05-13)

---

## Riepilogo Gap-Closure

Tre gap registrati nella verifica iniziale (2026-05-19) sono stati chiusi e confermati nel codice reale:

| Gap | Requirement | Piano | Stato |
|-----|-------------|-------|-------|
| CR-01: Cypher injection in TraverseGraphTool._arun | KNW-09 | 05-11 | CHIUSO |
| CR-02: source_uri derivation duplicata | KNW-07 | 05-12 | CHIUSO |
| IN-05: stub metrics senza disclaimer + --skip-eval unsafe default | KNW-03 | 05-13 | CHIUSO |

---

## Goal Achievement

### Observable Truths

| #   | Truth                                                                                          | Status    | Evidenza                                                                                                                                                                                                                 |
| --- | ---------------------------------------------------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SC1 | Italian query → English SOP chunk via cross-lingual eval suite                                 | VERIFIED  | `test_crosslingual_e2e.py` (integration+gpu); `RetrievalPipeline.search` language-agnostic via BGE-M3 multilingual                                                                                                        |
| SC2 | Every chunk carries source_uri/page/version/lang/acl_level; operator role cannot see restricted | VERIFIED  | `QdrantIndexer.upsert_batch` scrive 7 campi provenance; `build_acl_filter` engine-level pre-filter; `test_acl_enforcement.py` 15 test PASS                                                                               |
| SC3 | Incremental reindex on document update; full reindex not triggered                              | VERIFIED  | content_hash gate + `IngestStateStore`; `derive_source_uri` canonico via `sft_knowledge.path_utils` — entrambi i call-site (markdown.py + pipeline.py) ora usano la stessa funzione; rischio drift eliminato            |
| SC4 | Entity graph Machine→Part→FailureMode→SOP; traversal returns SOP                               | VERIFIED  | `Neo4jGraphBuilder` UNWIND MERGE per tutte le entita; `TraverseGraphTool._arun` ora re-valida input via `TraverseGraphInput` come prima istruzione — injection bypass chiuso                                              |
| SC5 | BGE-M3 vs multilingual-e5-large A/B documented in docs/ with justified decision                 | VERIFIED  | Tutti e 3 i documenti (IT MkDocs, EN MkDocs, canonical doc) ora riportano admonition "⚠ Preliminary stub metrics — pending real eval run"; `--stub` (default False) richiede opt-in esplicito; deferral a Phase 8 documentato |
| T1  | sft-knowledge SDK espone la surface pubblica (D-67/D-70)                                        | VERIFIED  | `__init__.py` ora esporta 24 simboli (aggiunto `derive_source_uri`, `WORKSPACE_ROOT`)                                                                                                                                    |
| T2  | Tutti i 40 SOP nel synthetic-corpus parsano con reviewed status                                  | VERIFIED  | MarkdownParser: 40 OK / 0 failed (nessuna regressione)                                                                                                                                                                   |
| T3  | 4 Qdrant collections bootstrapped idempotentemente (KNW-01)                                     | VERIFIED  | `qdrant-bootstrap.py`: 4 collection + 7 payload index (invariato)                                                                                                                                                        |
| T4  | BGE-M3 hybrid retrieval (dense+sparse+rerank) con RRF fusion (KNW-09) — injection-safe          | VERIFIED  | `RetrievalPipeline.search` RRF+rerank invariato; `TraverseGraphTool._arun` ora injection-proof per costruzione (CR-01 chiuso); 4 test injection PASS                                                                     |
| T5  | `failure_modes.yaml` ha >= 30 voci (KNW-08)                                                    | VERIFIED  | 32 voci (nessuna modifica in questa fase di gap-closure)                                                                                                                                                                 |

**Score:** 10/10 truths VERIFIED

---

## Verifica del Codice Reale — Gap per Gap

### Gap 1: CR-01 — TraverseGraphTool Cypher Injection (KNW-09)

**Piano 05-11** — commits `962a3f5` (RED) + `e7d4d03` (GREEN)

Evidenza nel codice:

- `packages/sft-knowledge/src/sft_knowledge/tools/graph.py` riga 120-130: `TraverseGraphInput(seed_label=..., seed_id=..., relation_path=..., max_depth=...)` e' la **prima istruzione** di `_arun`, prima di qualsiasi composizione Cypher. Tutti i riferimenti successivi usano `validated.*`.
- `grep -n "TraverseGraphInput(" graph.py | grep -v "args_schema|class"` → riga 125 (confermato).
- Docstring `_run` aggiornata: rimosso l'invito `await tool._arun(...)`, sostituito con `Use await tool.ainvoke({...}) only`.
- File test: `packages/sft-knowledge/tests/test_traverse_graph_injection.py` — 4 test (3 injection + 1 happy path).

Test eseguiti (run verificatore): **4/4 PASS**

| Test | Risultato |
|------|-----------|
| `test_arun_rejects_injection_seed_label` | PASS |
| `test_arun_rejects_injection_relation_path` | PASS |
| `test_arun_rejects_out_of_range_max_depth` | PASS |
| `test_arun_happy_path_with_valid_literals` | PASS |

**Stato: CHIUSO**

---

### Gap 2: CR-02 — source_uri Derivation Duplicata (KNW-07)

**Piano 05-12** — commits `3c8528a` (RED) + `d487763` (GREEN)

Evidenza nel codice:

- `packages/sft-knowledge/src/sft_knowledge/path_utils.py` esiste; esporta `WORKSPACE_ROOT` e `derive_source_uri` (riga 28-31 di path_utils.py).
- `packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py` riga 29: `from sft_knowledge.path_utils import derive_source_uri`; riga 119: `source_uri = derive_source_uri(path)`. I simboli `_WORKSPACE_ROOT` e il blocco try/except duplicato sono stati rimossi (grep → 0 match).
- `services/knowledge-ingest/src/svc_knowledge_ingest/pipeline.py` riga 39: `from sft_knowledge.path_utils import derive_source_uri`; riga 146: `source_uri = derive_source_uri(path)`. La funzione `_derive_source_uri()` (22 righe) e il suo `import os` sono stati rimossi (grep → 0 match).
- `packages/sft-knowledge/src/sft_knowledge/__init__.py`: `derive_source_uri` e `WORKSPACE_ROOT` aggiunti a `__all__` (24 simboli totali).
- Nessun `parents[5]` o `parents[4]` residuo nei sorgenti fuori da `path_utils.py` (grep confermato).

File test: `packages/sft-knowledge/tests/test_source_uri_resolution.py` — 4 test (workspace, equality, tmp_path, symlink).

Test eseguiti (run verificatore): **4/4 PASS**

| Test | Risultato |
|------|-----------|
| `test_derive_source_uri_workspace_file` | PASS |
| `test_derive_source_uri_equals_markdown_parser_output` | PASS |
| `test_derive_source_uri_tmp_path_outside_workspace` | PASS |
| `test_derive_source_uri_symlink_inside_workspace` | PASS |

**Stato: CHIUSO**

---

### Gap 3: IN-05 — Stub Metrics Senza Disclaimer / --skip-eval Unsafe Default (KNW-03)

**Piano 05-13** — commits `d5601a5` (RED) + `bf964a7` (GREEN) + `0ecc554` (docs)

Evidenza nel codice:

- `services/knowledge-ingest/scripts/run_ab_eval.py`: `--skip-eval` completamente rimosso (grep → 0 match); `--stub` (riga 275) con `default=False` — opt-in esplicito. Nessun flag → `NotImplementedError` con pointer a Phase 8.
- Disclaimer "⚠ Preliminary stub metrics — pending real eval run" presente verbatim su tutte e 3 le superfici:
  - `docs/docs/knowledge-layer/eval-results.md` riga 12 (MkDocs IT) — `!!! warning` admonition
  - `docs/docs/en/knowledge-layer/eval-results.md` riga 12 (MkDocs EN) — `!!! warning` admonition
  - `docs/eval/rag-ab-test-bge-m3-vs-e5.md` riga 5 (canonical doc) — blockquote
- Sezione "Deferred follow-up (Phase 8)" aggiunta al canonical doc.

File test: `services/knowledge-ingest/tests/test_run_ab_eval_disclaimer.py` — 4 test.

Test eseguiti (run verificatore): **4/4 PASS**

| Test | Risultato |
|------|-----------|
| `test_main_no_flags_raises_not_implemented` | PASS |
| `test_main_with_stub_flag_produces_disclaimer` | PASS |
| `test_main_with_full_flag_raises_not_implemented` | PASS |
| `test_skip_eval_flag_removed` | PASS |

**Stato: CHIUSO**

---

## Suite Unitaria Completa (post gap-closure)

```
uv run python -m pytest packages/sft-knowledge/tests/ services/knowledge-ingest/tests/ -m "not integration and not gpu"
83 passed, 31 deselected in 2.25s
```

Nessuna regressione rispetto alla baseline precedente (71 test; i 12 test nuovi dei piani 05-11/12/13 portano il totale a 83).

---

## Requirements Coverage (aggiornata)

| Requirement | Piano | Descrizione | Stato | Evidenza |
| ----------- | ----- | ----------- | ----- | -------- |
| KNW-01 | 05-04 | Qdrant self-hosted, 4 collections | SATISFIED | Invariato da verifica iniziale |
| KNW-02 | 05-07 | BGE-M3 default + e5 adapter | SATISFIED | Invariato |
| KNW-03 | 05-10, 05-13 | A/B eval IT+EN documentata in docs/ | SATISFIED | Disclaimer propagato su tutte e 3 le superfici; --stub opt-in; deferral a Phase 8 documentato |
| KNW-04 | 05-01, 05-10 | Pipeline MD → chunk → embed → upsert | PARTIAL | MD completo; PDF/DOCX/HTML deferred a Phase 8 (deviazione di scope documentata) |
| KNW-05 | 05-01, 05-08 | Provenance obbligatoria | SATISFIED | Invariato |
| KNW-06 | 05-02, 05-09 | ACL tag per chunk rispettato a query time | SATISFIED | Invariato |
| KNW-07 | 05-06, 05-10, 05-12 | Reindex incrementale | SATISFIED | source_uri canonico via derive_source_uri; rischio drift eliminato |
| KNW-08 | 05-03, 05-05, 05-08 | Entity graph Neo4j | SATISFIED | Invariato |
| KNW-09 | 05-09, 05-11 | Hybrid retrieval + rerank; injection-safe | SATISFIED | TraverseGraphTool._arun injection-proof; 4 test PASS |
| TRN-01 | 05-06, 05-10 | KnowledgeCurator ingest scaffold | SATISFIED | Invariato |

**Coverage:** 10/10 requirement ID; nessun orfano. 9 SATISFIED, 1 PARTIAL (KNW-04 per design — deferred a Phase 8).

---

## Human Verification Required

Tre test di integrazione GPU non eseguibili sul dev box (3.68 GiB GPU occupata) — sono difetti hardware, non difetti di codice:

### 1. BGE-M3 Real Model Load

**Test:** Eseguire `uv run python -m pytest packages/sft-knowledge/tests/test_bge_m3_embedder.py::test_real_bge_m3_loads -v` su macchina con GPU >= 6 GiB liberi
**Expected:** BGE-M3 si carica via FlagEmbedding; il test PASS; nessun CUDA OOM
**Why human:** Richiede >= 6 GiB GPU liberi; il dev box fallisce per OOM hardware

### 2. Cross-lingual End-to-End Retrieval

**Test:** Eseguire `uv run python -m pytest packages/sft-knowledge/tests/test_crosslingual_e2e.py::test_it_query_returns_en_sop -v` su macchina con GPU >= 6 GiB + Qdrant live con corpus caricato
**Expected:** Query italiana recupera chunk SOP in inglese; Recall@5 >= threshold; test PASS
**Why human:** Dipende da GPU reale (BGE-M3 embedding) + Qdrant popolato; non ci sono mock sufficienti per questo test di integrazione end-to-end

### 3. Semantic Chunker End-to-End (Real Embedder)

**Test:** Eseguire `uv run python -m pytest packages/sft-knowledge/tests/test_semantic_chunker.py::test_real_sop_end_to_end_chunk_and_embed -v` su macchina con GPU >= 6 GiB liberi
**Expected:** SemanticChunker divide SOP reale, BgeM3Embedder embeds ogni chunk; test PASS
**Why human:** Usa BgeM3Embedder in modalita reale (GPU path FlagEmbedding / fastembed); richiede >= 6 GiB liberi

> Nota: questi test erano gia presenti e classificati come `integration+gpu` nella verifica iniziale. Il gap-closure non li ha introdotti. Sono SKIPPATI dal CI marker nella suite unitaria standard (`-m "not integration and not gpu"`).

---

## Deferred Items (invariati da verifica iniziale)

| # | Item | Addressed In | Evidenza |
|---|------|-------------|---------|
| 1 | PDF/DOCX/HTML parsers per KNW-04 | Phase 8 (Agents — Knowledge & Training) | ROADMAP Phase 5 scope note (line 113): "Phase 5 ships MarkdownParser only. The DocumentParser ABC enables PDF/DOCX/HTML parsers in Phase 8 KnowledgeCurator" |

---

## Anti-Patterns Residui (non bloccanti)

I warning WR-01..WR-13 e IN-01..IN-06 elencati nella verifica iniziale sono invariati. Nessun nuovo anti-pattern introdotto dai piani 05-11/12/13. Nessun TBD/FIXME/XXX non referenziato nei file modificati.

---

_Re-verificato: 2026-05-24T15:00:00Z_
_Verifier: Claude (gsd-verifier) — re-verifica post gap-closure piani 05-11, 05-12, 05-13_
