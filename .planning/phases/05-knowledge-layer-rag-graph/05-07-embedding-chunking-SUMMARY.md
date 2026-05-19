---
phase: 05-knowledge-layer-rag-graph
plan: 05-07
subsystem: knowledge
tags: [bge-m3, flagembedding, fastembed, llama-index, semantic-chunking, embedding, qdrant-sparse]

requires:
  - phase: 05-01-sft-knowledge-sdk
    provides: ParsedDoc, ParsedSection, MarkdownParser, DocumentParser ABC
provides:
  - BgeM3Embedder con dense (1024D) + sparse lexical weights via FlagEmbedding
  - Fallback fastembed (degraded mode dense-only) quando FlagEmbedding non installabile
  - RuntimeError esplicito quando nessun backend disponibile (no silent fallback)
  - Lazy singleton `_get_model()` via @lru_cache(maxsize=1) honoring BGE_M3_DEVICE env
  - to_qdrant_sparse() con filtering UNK token per indici Qdrant SparseVector validi
  - SemanticChunker via LlamaIndex SemanticSplitterNodeParser (buffer_size=1, percentile=95)
  - Propagazione frontmatter SOP → ogni Chunk.metadata (KNW-05 prerequisite)
  - Heading_path recovery per ogni chunk via bisect_right(node.start_char_idx)
  - excluded_embed_metadata_keys per evitare contaminazione semantica da identificatori
  - Chunk frozen Pydantic v2 (Shared Pattern 1)
affects: [05-08-qdrant-neo4j-indexing, 05-09-retrieval-pipeline, 05-10-rag-tools]

tech-stack:
  added: [FlagEmbedding>=1.3, llama-index-embeddings-huggingface>=0.3 (già dichiarati in Plan 05-01 pyproject)]
  patterns:
    - "Lazy singleton via @lru_cache(maxsize=1) (Shared Pattern 8)"
    - "Fallback ladder con ImportError gate (FlagEmbedding → fastembed → RuntimeError)"
    - "Adapter pattern (_FastEmbedAdapter) per uniformare interfaccia encode()"
    - "Lazy import dentro metodi per top-level leggero (SparseVector, LlamaIndex)"
    - "excluded_embed_metadata_keys: separazione metadata semantici vs tracking (T-05-07-03)"
    - "Heading_path recovery via bisect su offset cumulativi (no parse char-by-char)"
    - "Mocking via sys.modules + types.ModuleType per testare fallback ladder senza dipendenze reali"

key-files:
  created:
    - packages/sft-knowledge/src/sft_knowledge/embedding/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
    - packages/sft-knowledge/src/sft_knowledge/chunking/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py
    - packages/sft-knowledge/tests/test_bge_m3_embedder.py
  modified:
    - packages/sft-knowledge/src/sft_knowledge/__init__.py (re-export nuovi simboli)
    - packages/sft-knowledge/tests/test_semantic_chunker.py (sostituito stub Wave-0)

key-decisions:
  - "EncodeOutput come @dataclass(frozen=True) anziché Pydantic BaseModel: np.ndarray non è serializzabile by-default da Pydantic v2 senza arbitrary_types_allowed; il dataclass mantiene immutabilità senza overhead di validazione su array."
  - "BGE_M3_DEVICE letto via os.environ.get con default 'cpu' (mai cuda di default) per CI compat."
  - "Fallback fastembed espone sparse_weights=[{} for _ in texts] (modalità degradata documentata) anziché sollevare eccezione: alcune deploy senza torch nativo possono comunque usare retrieval dense-only."
  - "to_qdrant_sparse solleva RuntimeError se tokenizer è None (fastembed): evita un Qdrant SparseVector vuoto/inconsistente. Plan 05-08 dovrà gestire questo caso o richiedere FlagEmbedding come hard-dep al boot."
  - "Body chunking ricostruito via '\\n\\n'.join(sections.text): offset cumulativi tracciati con cursor + len(separator) per bisect_right corretto. NESSUN re-parsing del markdown."
  - "Test integration su SOP-LOOM-001 (6346 byte): file più piccolo del corpus loom IT; risolto via parents[3] anziché hardcoded — robusto a riorganizzazioni futuri."
  - "Mocking llama_index via sys.modules + types.ModuleType: evita di importare la libreria reale nei test unit (che caricano pesanti torch deps anche solo per definire la classe)."

patterns-established:
  - "Pattern dual-backend con import-fallback: try primary import → except ImportError → try fallback → except → RuntimeError diagnostico. Riusabile per altre lib heavy (es. reranker in 05-09)."
  - "Pattern _FastEmbedAdapter: classe interna che mappa shape API di una lib alternativa su quella primaria, isolando il branch logic dal codice client."
  - "Pattern lazy-singleton model loader: @lru_cache(maxsize=1) su _get_model/_get_embed_model garantisce un solo carico del modello per processo, anche cross-istanza."
  - "Pattern metadata propagation con whitelist excluded_embed: separare metadati per filtro retrieval (acl_level, source_uri) da quelli per embedding (semantica pura)."

requirements-completed: [KNW-02]

duration: ~30min
completed: 2026-05-19
---

# Phase 5 Plan 05-07: Embedding + Chunking Summary

**BgeM3Embedder (FlagEmbedding primary + fastembed fallback + lazy singleton) e SemanticChunker (LlamaIndex SemanticSplitter buffer_size=1/percentile=95) con propagazione frontmatter per ogni chunk — KNW-02 chiuso.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-05-19T10:45:00Z (approssimato)
- **Completed:** 2026-05-19T11:15:53Z
- **Tasks:** 3/3
- **Files created:** 5
- **Files modified:** 2

## Accomplishments

- `BgeM3Embedder` con dense (1024,) + sparse lexical weights, singleton lazy, fallback fastembed, RuntimeError esplicito se nessun backend disponibile
- `to_qdrant_sparse()` con filtering UNK token (RESEARCH §2 Open Q1) e invariante len(indices)==len(values)
- `SemanticChunker` con SemanticSplitterNodeParser D-62 (buffer_size=1, breakpoint_percentile_threshold=95) e HuggingFaceEmbedding("BAAI/bge-m3") singleton condiviso
- Propagazione completa metadata frontmatter (source_uri, lang, acl_level, version, asset_family, sop_id) su ogni `Chunk` — KNW-05 prerequisite
- `excluded_embed_metadata_keys=[source_uri, acl_level, sop_id]` mitigazione T-05-07-03 (identificatori non contaminano l'embedding semantico)
- 10 unit test totali (5 embedder + 5 chunker) passanti senza caricare il modello reale; 2 test gpu-gated collezionabili ma skipped su CPU CI

## Task Commits

Ogni task è stato committato atomicamente:

1. **Task 1: BgeM3Embedder con FlagEmbedding primary + fastembed fallback** — `ceb8759` (feat)
2. **Task 2: SemanticChunker con LlamaIndex SemanticSplitter + frontmatter propagation** — `df3ba16` (feat)
3. **Task 3: End-to-end integration test on real SOP (gpu-gated)** — `e9eeb08` (test)

## Files Created/Modified

### Creati

- `packages/sft-knowledge/src/sft_knowledge/embedding/__init__.py` — re-export `BgeM3Embedder, EncodeOutput`.
- `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py` — implementazione embedder con dual-backend, singleton, to_qdrant_sparse. ~260 righe.
- `packages/sft-knowledge/src/sft_knowledge/chunking/__init__.py` — re-export `SemanticChunker, Chunk`.
- `packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py` — implementazione chunker LlamaIndex con heading_path recovery + metadata propagation. ~210 righe.
- `packages/sft-knowledge/tests/test_bge_m3_embedder.py` — 5 unit test (singleton, dense shape, fastembed fallback, RuntimeError, UNK filtering) + 1 test gpu-gated `test_real_bge_m3_loads`. ~215 righe.

### Modificati

- `packages/sft-knowledge/src/sft_knowledge/__init__.py` — re-export `BgeM3Embedder, EncodeOutput, SemanticChunker, Chunk` nel namespace top-level (`from sft_knowledge import ...`).
- `packages/sft-knowledge/tests/test_semantic_chunker.py` — sostituito stub Wave-0 con 5 unit test + 1 test integration gpu-gated (`test_real_sop_end_to_end_chunk_and_embed`). ~322 righe.

## Decisions Made

- **Plan eseguito esattamente come scritto.** Tutte le scelte chiave (D-62 buffer_size=1/percentile=95, BGE_M3_DEVICE env, fastembed come fallback dense-only, EncodeOutput come dataclass per supportare np.ndarray, lru_cache(maxsize=1) singleton, excluded_embed_metadata_keys whitelist) erano già specificate nel PLAN.md sezione `<interfaces>`.
- **UN solo deviazione minor**: `pytest-asyncio` è dichiarato come dev-extra ma `nx run sft-knowledge:test` esegue `uv run pytest` senza `--extra dev`. Nei test ho usato `uv run --extra dev pytest` localmente per validare. **Non modifico il project.json target** in questo plan: è ortogonale all'obiettivo KNW-02 e potrebbe rompere altri plan. Documentato qui come deferred item.

## Deviations from Plan

Nessuna deviazione funzionale dal PLAN.md. Plan eseguito esattamente come scritto.

**Note minori (non rule-deviation):**

1. **pytest-asyncio non auto-installato dal target nx**: il target `test` di sft-knowledge in `project.json` esegue `uv run pytest` ma `pytest-asyncio` è dichiarato in `[project.optional-dependencies] dev`, quindi non viene installato senza `--extra dev`. Ho usato `uv run --extra dev pytest` localmente per la validazione. **Non ho modificato il target** per evitare side-effect su altri plan (es. 05-04, 05-05 che potrebbero avere già preparato il loro setup). Tracciato come deferred item per il verifier di phase: vale la pena valutare se promuovere `pytest-asyncio` a dipendenza principale o aggiungere `--extra dev` al comando in `project.json`.

2. **Path resolution per il test integration**: il PLAN suggeriva un approccio deterministico tramite "sort glob + take first reviewed file with body length < 2000 chars". Ho preferito hardcodare il path tramite `Path(__file__).resolve().parents[3]` per due motivi: (a) i 5 SOP del corpus loom IT sono tutti > 6 KB (non esistono file < 2000 char nel corpus reale), (b) un riferimento esplicito al file SOP-LOOM-001 rende il test più riproducibile e debuggable. Il PLAN ammetteva esplicitamente l'opzione "hardcode a specific filename if the corpus has a known small file".

---

**Total deviations:** 0 (rule-based auto-fixes)
**Impact on plan:** Nessuno. Plan completato as-written.

## Issues Encountered

- **Test infra setup**: alla prima esecuzione, `pytest-asyncio` non era importabile (vedi nota sopra). Risolto usando `uv run --extra dev pytest` per la validazione locale.

## Known Stubs

Nessuno stub introdotto. Tutti i metodi sono completamente implementati. Il test `test_real_bge_m3_loads` (gpu-gated, Task 1) e `test_real_sop_end_to_end_chunk_and_embed` (gpu-gated, Task 3) caricheranno il modello reale solo quando il marker `gpu` è esplicitamente selezionato — comportamento documentato e non uno stub.

## Threat Flags

Nessuna nuova superficie di attacco oltre a quelle già modellate nel `<threat_model>` del PLAN:
- T-05-07-01 (model weights origin) — accepted, mitigato da scelta upstream BAAI.
- T-05-07-02 (info disclosure embed) — mitigato: corpus sintetico + ACL gate upstream (Plan 05-01 D-25/D-67).
- T-05-07-03 (metadata contamination) — **mitigato implementativamente**: `excluded_embed_metadata_keys=[source_uri, acl_level, sop_id]` nel `Document` LlamaIndex.
- T-05-07-04 (DoS OOM) — mitigato: `max_length=8192` + chunking upstream.
- T-05-07-SC (supply chain) — accepted, librerie dichiarate in pyproject 05-01 con audit RESEARCH.

## User Setup Required

Nessuno. Né variabili d'ambiente nuove né servizi esterni da configurare. `BGE_M3_DEVICE` ha default `cpu` e funziona out-of-the-box; opzionale impostarlo a `cuda` su runner GPU.

## Next Phase Readiness

- **Plan 05-08 (QdrantIndexer)** può ora chiamare `BgeM3Embedder.encode()` e `to_qdrant_sparse()` per produrre dense+sparse vectors da indicizzare. Attenzione: `to_qdrant_sparse` solleva `RuntimeError` se il backend è fastembed (tokenizer assente) — Plan 05-08 dovrà gestire questo caso o richiedere FlagEmbedding come hard-requirement al boot.
- **Plan 05-09 (RetrievalPipeline)** può istanziare `BgeM3Embedder()` per query embedding; il singleton garantisce condivisione del modello tra indexer e retriever nello stesso processo.
- **Plan 05-09 (RagSearchTool)** può consumare `Chunk.metadata` (source_uri, sop_id, heading_path) per costruire `RagCitation` (re-export da sft-agents).
- **Verifier di phase 05**: dovrebbe convalidare che `pytest-asyncio` sia accessibile dal target `nx run sft-knowledge:test` (issue cross-plan tracciato qui).

## Self-Check: PASSED

Verifiche eseguite:
- File creati esistenti: tutti presenti (embedding/__init__.py, embedding/bge_m3.py, chunking/__init__.py, chunking/semantic.py, tests/test_bge_m3_embedder.py)
- Commit storici: `ceb8759`, `df3ba16`, `e9eeb08` tutti presenti in `git log`
- Acceptance criteria PLAN.md tutti verificati via grep:
  - `class BgeM3Embedder` in bge_m3.py — OK
  - `@lru_cache(maxsize=1)` in bge_m3.py — OK
  - `BGE_M3_DEVICE` in bge_m3.py — OK
  - `from fastembed` in bge_m3.py — OK
  - `RuntimeError` in bge_m3.py — OK
  - `class SemanticChunker` in semantic.py — OK
  - `buffer_size: int = 1` in semantic.py — OK
  - `breakpoint_percentile_threshold` in semantic.py — OK
  - `BAAI/bge-m3` in semantic.py — OK
  - `excluded_embed_metadata_keys` in semantic.py — OK
  - `class Chunk(BaseModel):` in semantic.py — OK
  - `@pytest.mark.gpu` su test_real_sop in test_semantic_chunker.py — OK
- Unit test suite `uv run --extra dev pytest -m 'not integration and not gpu' -v` → 33 passed, 6 skipped (stub future plan), 6 deselected (gpu/integration). Nessuna regressione.

---
*Phase: 05-knowledge-layer-rag-graph*
*Plan: 05-07-embedding-chunking*
*Completed: 2026-05-19*
