---
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
phase_slug: knowledge-layer-rag-graph
discussed_at: "2026-05-18"
requirements: [KNW-01, KNW-02, KNW-03, KNW-04, KNW-05, KNW-06, KNW-07, KNW-08, KNW-09, TRN-01]
depends_on_phases: [1, 2, 4]
---

# Phase 5 Context — Knowledge Layer (RAG + Graph)

<domain>
**What this phase delivers:** the knowledge backbone on which knowledge-dependent agents (Phase 6 OperatorAssistant, Phase 7 RCASpecialist/MaintenanceCoach, Phase 8 Knowledge cluster, Phase 9 Supply) will plug in.

Concretely:
- A **`sft-knowledge` SDK** (`packages/sft-knowledge/`) with: `MarkdownParser` (+ `DocumentParser` ABC), `SemanticChunker`, `QdrantIndexer`, `Neo4jGraphBuilder`, `RagSearchTool`, `TraverseGraphTool`, `QdrantLongTermMemory` (replaces Phase 4 D-59 stub)
- A **Qdrant deployment** with 4 collections per categoria (`sop`, `manuals`, `troubleshooting`, `training`); multilingue IT/EN nello stesso collection con payload `lang`; dual-vector points (dense BGE-M3 + sparse BM42) (KNW-01)
- **BGE-M3 embedding stack** via FastEmbed (default) + LlamaIndex `SemanticSplitter` for chunking (buffer_size=1, breakpoint percentile 95) (KNW-02 + chunking decision)
- **Hybrid retrieval** Qdrant Query API single-shot: `Prefetch` dense + `Prefetch` sparse → Fusion RRF top-20 → BGE-reranker-v2-m3 sempre attivo → top-k (KNW-09)
- **Cross-lingual retrieval** affidato alle representations BGE-M3 (no query translation, no glossary expansion) — success criterion #1 verificato via A/B eval test set
- **Document ingest pipeline** (`services/knowledge-ingest/`) Markdown-only Phase 5; PDF/DOCX/HTML deferred to Phase 8 KnowledgeCurator (scoping deviation from literal KNW-04)
- **Provenance obbligatoria** in ogni point payload: `source_uri`, `chunk_idx`, `version`, `lang`, `acl_level`, `asset_family`, `heading_path`, `created_at` (KNW-05)
- **ACL enforcement** pre-filter Qdrant via payload field `acl_level: public|internal|restricted` (nuovo campo nel frontmatter SOP, migrazione 41 SOP esistenti + CI validator); retrieval tool inietta SEMPRE `must` filter su role-derived allowed set (KNW-06)
- **Reindex incrementale** via GitHub Actions su push `main` con `git diff --name-only` + `nx run ingest:run --files=...`; CLI manuale `nx run ingest:run --paths=...` per dev (KNW-07)
- **Entity graph** Neo4j Community 5.24 + APOC plugin; schema `Machine → Part → FailureMode → SOP`; popolazione deterministic da SOP frontmatter + `packages/sft-assets` registry (Phase 3) + nuovo `packages/sft-domain/failure_modes.yaml` (derivato dalla defect taxonomy Phase 2); CI validator: ogni FailureMode ha ≥1 SOP collegato (KNW-08)
- **GraphRAG retrieval** esposto tramite due Tool LangChain SEPARATI: `rag_search` (Qdrant fused+rerank, con `sop_ids` filter opzionale) + `traverse_graph` (Cypher MATCH); composizione lato agent (KNW-08 + KNW-09)
- **Idempotency** `point.id = sha256(source_uri + chunk_idx + text)` deterministico → UPSERT no-op su re-ingest dello stesso content
- **A/B evaluation BGE-M3 vs multilingual-e5-large** (KNW-03): synthetic question generation con Qwen2.5-7B via LLM adapter Phase 4 (3 query/SOP × 41 SOP ≈ 123 query, seed=42, types=keyword_it+natural_it+cross_lingual_en) + manual spot-check 10%; metriche NDCG@10, MRR, Recall@10, cross-lingual recall; deliverable `docs/eval/rag-ab-test-bge-m3-vs-e5.md`
- **TRN-01 KnowledgeCurator stub:** Phase 5 ships ingest pipeline + dedup hash + stale-detection scaffold; full curator agent business logic deferred Phase 8

This phase does NOT build agent business logic (Phase 6-9), does NOT add real-time filesystem watcher (deferred to Phase 10 quando UI upload entra in scope o quando emerge il bisogno), does NOT extend parser oltre Markdown (Phase 8 KnowledgeCurator estende il `DocumentParser` ABC), does NOT include Langfuse self-hosted server deployment (Phase 11).
</domain>

<canonical_refs>
Files downstream agents (researcher, planner) MUST consult:

- `.planning/ROADMAP.md` — Phase 5 goal + 5 success criteria + 10 requirements
- `.planning/REQUIREMENTS.md` — KNW-01..09 + TRN-01 dettaglio
- `.planning/PROJECT.md` — core value "ogni decisione AI passa per umano informato"; il knowledge layer DEVE fornire provenance per supportare HITL informato
- `.planning/research/STACK.md` — Qdrant 1.16+ + BGE-M3 MIT + BM42 + DeepEval CI + RAGAS monitoring (tutti LOCKED); Neo4j vs Memgraph alternative documentate (Phase 5 decide Neo4j Community 5.24)
- `.planning/research/ARCHITECTURE.md` — sezione "Memory & Knowledge" (Qdrant + Neo4j dual-write atomicity Neo4j-first), `doc_ingest` come processo separato (agent NON scrive), GraphRAG link
- `.planning/research/PITFALLS.md` — pitfall su agent-direct-write a knowledge stores (Phase 5 evita: ingest è batch-only)
- `.planning/research/FEATURES.md` — RAG features list (cross-lingual, provenance, ACL)
- `.planning/phases/01-foundation-monorepo/01-CONTEXT.md` — D-02 packages layout (`packages/sft-*` convention); D-09 docker-compose (Qdrant già up in `infra/compose/core.yml` v1.16.1); Helm chart skeleton per Qdrant
- `.planning/phases/02-domain-modeling-synthetic-corpus/02-CONTEXT.md` — D-25 SOP `status: reviewed` gate (Phase 5 ingest FILTRA su `status == 'reviewed'`); D-21 5 process families (informa asset_family payload field); glossary bilingue ~150 termini in `packages/sft-domain`; defect taxonomy → input per `failure_modes.yaml`
- `.planning/phases/03-it-ot-simulation-layer/03-CONTEXT.md` — `packages/sft-assets` con 30 asset seeded (Asset/Tag Pydantic models) → input per Neo4j Machine/Part nodes; idempotent migration pattern (Phase 5 estende per Neo4j schema constraints + Qdrant collection bootstrap)
- `.planning/phases/04-core-agentic-runtime-hitl/04-CONTEXT.md` — D-59 memory layer split: Phase 5 sostituisce `StubLongTermMemory` con `QdrantLongTermMemory` implementando `MemoryStore` ABC; `RagCitation = {source_uri, snippet, score, retrieved_at}` schema CONFERMATO (Phase 5 popola). D-53 cluster `knowledge-curation` esiste come subgraph skeleton (Phase 5 fornisce backend; Phase 8 fa business logic). EvidencePanel.rag_citations[] data contract
- `simulators/synthetic-corpus/{it,en}/{loom,spinning,dyeing,quality_grading}/` — 41 SOP MD esistenti con frontmatter; **Phase 5 task obbligatorio: migration script aggiunge `acl_level` field a tutti 41 SOP**
- `packages/sft-assets/src/sft_assets/{models.py,loader.py}` — Asset/Tag models → Neo4j Machine/Part population source
- `packages/sft-domain/` — glossary IT/EN + schemas → Phase 5 aggiunge `failure_modes.yaml` + loader
- `packages/sft-agents/src/sft_agents/memory/base.py` — `MemoryStore` ABC (Phase 4 D-59) → Phase 5 implementa `QdrantLongTermMemory`
- `infra/compose/core.yml` — Qdrant già configurato (v1.16.1); Phase 5 AGGIUNGE Neo4j service
- `infra/migrations/timescale/` — pattern idempotent DO $$ blocks; Phase 5 NON estende TimescaleDB (knowledge state in Qdrant + Neo4j, ingest state opzionale in PG via `ingest.documents` table per dedup tracking)
- `docs/assumptions/register.yaml` — A-013..A-018 (HITL + GDPR PII) → Phase 5 verifica: SOP content PII-free (synthetic corpus, no risk); A-014 (PoC IT-only) NON applica (Phase 5 È esplicitamente bilingue IT+EN)
- `apps/agents/knowledge/*/` — Phase 1 scaffold per knowledge cluster; Phase 4 wires come subgraph skeleton; Phase 5 fornisce solo i Tool, NON business logic

No external SPEC.md or ADR exists for Phase 5 — this CONTEXT.md is source of truth.
</canonical_refs>

<code_context>
**Already exists — reuse, do NOT duplicate:**

- `infra/compose/core.yml` — Qdrant v1.16.1 già configurato + qdrant-data volume; Phase 5 AGGIUNGE Neo4j service (Phase 1 deferred Neo4j a knowledge phase)
- `packages/sft-agents/src/sft_agents/memory/base.py` — `MemoryStore` ABC + `StubLongTermMemory` (Phase 4 D-59); Phase 5 SOSTITUISCE con `QdrantLongTermMemory`
- `packages/sft-agents/src/sft_agents/models/__init__.py` — `RagCitation` Pydantic model (Phase 4 stub schema); Phase 5 popola
- `packages/sft-assets/` (Phase 3 v0.1.0) — Asset/Tag + 30 asset seed; Phase 5 importa per Neo4j Machine/Part nodes
- `packages/sft-domain/` (Phase 2 v0.2.0) — glossary IT/EN + defect taxonomy schemas; Phase 5 aggiunge `failure_modes.yaml` + loader
- `packages/sft-tools/` (Phase 3) — `QueryTimescaleTool` + `ReplayCMAPSSTool` pattern; Phase 5 ispira `RagSearchTool` + `TraverseGraphTool` ma li mette in NUOVO `packages/sft-knowledge/`
- `simulators/synthetic-corpus/{it,en}/` — 41 SOP MD; frontmatter campi attuali: `id, title, version, lang, asset, asset_family, role, hazard_level, status, audience, tags, related_glossary`
- `apps/api-gateway/` (Phase 4) — FastAPI scaffold; Phase 5 può OPZIONALMENTE aggiungere `/v1/knowledge/search` REST endpoint (deferred → Phase 10 unless needed prima per Phase 6-7 agent calls)
- `scripts/timescale-migrate.py` — pattern idempotent migrations Phase 3; Phase 5 NON usa direttamente ma replica idiom per Qdrant collection bootstrap + Neo4j schema constraints
- `tests/conftest.py` — fixture compose_stack pattern Phase 3; Phase 5 estende con `qdrant_client` + `neo4j_driver` testcontainers fixtures
- `.github/workflows/` — Nx affected CI Phase 1; Phase 5 aggiunge `reindex.yml` workflow

**Naming conventions to honor (consistenza con Phase 1/2/3/4):**
- Conventional Commits scope `feat(05-NN-slug):` per atomic commit
- Pydantic v2 frozen + `extra=forbid` per Pydantic models (Phase 1+2+3+4 standard)
- `yaml.safe_load` mandatory (mai yaml.load)
- asyncpg `$1..$N` placeholders ONLY (no f-string SQL — T-V5-sql Phase 3 threat)
- Neo4j: parametrized Cypher SOLO (`$param` syntax), NO string interpolation (analogous SQL injection defense)
- `datetime.now(UTC)` mandatory (Pitfall 7 Phase 3)
- structlog JSON logging
- snake_case Python field names + YAML keys
- frontmatter fields: kebab-case se composti (es. `acl_level`, NON `aclLevel`)
- Test markers: `@pytest.mark.integration` per testcontainers-dependent tests; `@pytest.mark.gpu` per BGE-M3 GPU-only (skip su CPU CI)

**Esistente da Phase 4 (NOT duplicate):**
- LLM adapter `LLM_BACKEND={ollama|vllm}` → Phase 5 lo usa per: (a) synthetic question generation in A/B eval script (Qwen2.5-7B Ollama default), (b) embed BGE-M3 invocato direttamente via FastEmbed/sentence-transformers (NON LLM adapter — embedding ≠ chat)
- Langfuse v3 callback wiring → Phase 5 estende per tracciare span `rag.search` + `rag.rerank` + `graph.traverse`
- BudgetTracker middleware → Phase 5 expone `rag_search` come Tool; ogni call passa per BudgetTracker (token costs degli embedding sono trascurabili, ma latency span è traccia utile)
</code_context>

<decisions>

## D-61 — Qdrant topology: 4 collection per categoria, multilingue IT/EN unified

**Decision:** 4 collection Qdrant separate per categoria (mapping diretto KNW-01):
- `sop` — Standard Operating Procedures (corpus Phase 2 primario)
- `manuals` — manuali tecnici (Phase 5 ships collection scaffold + 0 docs; Phase 8 KnowledgeCurator popola con real data)
- `troubleshooting` — guide diagnostiche (subset SOP categoria troubleshooting Phase 2)
- `training` — materiali formativi (Phase 8 TrainingCoach popola)

Lingua IT/EN STA NELLO STESSO COLLECTION via payload field `lang: 'it'|'en'`. Query default NON filtra per lang (cross-lingual via BGE-M3 representations). Filtro opzionale `lang` esposto al Tool ma default `None`.

Dual-vector point structure:
```python
PointStruct(
  id=sha256(source_uri + chunk_idx + text)[:32],   # deterministic
  vector={
    'dense':  bge_m3_dense_vec,    # 1024-d
    'sparse': bm42_sparse_vec      # SparseVector IDF
  },
  payload={
    'text': chunk_text,                # full chunk content (per rerank)
    'source_uri': str,                 # es. 'corpus://it/loom/SOP-LOOM-001-...md'
    'chunk_idx': int,
    'version': str,                    # da frontmatter SOP
    'lang': 'it'|'en',
    'acl_level': 'public'|'internal'|'restricted',
    'asset_family': str,               # es. 'weaving','dyeing','quality_grading'
    'asset': str | None,               # specifico asset se dichiarato
    'category': 'sop'|'manuals'|'troubleshooting'|'training',
    'heading_path': list[str],         # es. ['Procedura','Step 1']
    'related_glossary': list[str],     # da frontmatter
    'created_at': '2026-05-18T...Z',
    'sop_id': str,                     # FK per join GraphRAG (Neo4j SOP.id)
  }
)
```

**Why:** Mapping diretto al testo del requirement KNW-01 (collections separate per categoria). Multilingue unified perché BGE-M3 è progettato per allineare representations cross-lingua (verificato in A/B eval). Sparse BM42 può essere meno preciso su mixed-language vocab ma rerank cross-encoder compensa (D-63).

**Rejected alternatives:**
- 8 collection (categoria × lingua): raddoppia maintenance, perde cross-lingual nativo, sparse BM42 marginal gain non giustifica.
- 1 collection `knowledge` unified: contraddice testo KNW-01.
- 4 collection × multilingual-e5 separato: deferred all'A/B eval (KNW-03) di decidere se BGE-M3 vince.

## D-62 — Semantic chunking via LlamaIndex SemanticSplitter + BGE-M3

**Decision:** `SemanticChunker` in `sft-knowledge` wrappa `llama_index.core.node_parser.SemanticSplitter`:
```python
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

splitter = SemanticSplitterNodeParser(
    buffer_size=1,
    breakpoint_percentile_threshold=95,
    embed_model=HuggingFaceEmbedding(model_name='BAAI/bge-m3'),
)
```

Per ogni SOP parsed:
1. `MarkdownParser` estrae frontmatter + body
2. Body → `SemanticSplitter.get_nodes_from_documents()` → list[TextNode]
3. Per ogni TextNode: aggiungi `heading_path` ricavato dal body originale (mapping char-offset → heading H2/H3 corrente)
4. Per ogni TextNode → 1 chunk record con `text`, `chunk_idx`, `heading_path`

**Why:** SOP tessili hanno passi procedurali che fixed-token può tagliare a metà (es. "## Step 3 — Smontare il subbio\n[testo passo]"); semantic chunking preserva coerenza concettuale. BGE-M3 embedding viene riusato (no secondo modello). Cost: ~2 embed per sentence (sentence-level + chunk-level); 41 SOP × ~30 sentence/SOP = ~2500 sentence embedding aggiuntivi (one-shot ingest = ~30s su CPU, accettabile).

**Rejected alternatives:**
- Heading-aware Markdown soft-cap 512 tok: custom chunker da testare, non riusabile per PDF (Phase 8).
- Fixed-token sliding window 512 overlap 64: deterministico ma spezza step procedurali; sub-ottimale per SOP strutturati.

## D-63 — Hybrid retrieval: BM42 nativo Qdrant + BGE-reranker-v2-m3 sempre attivo

**Decision:** Retrieval pipeline per ogni query:

1. **Embed query** con BGE-M3 (FastEmbed): produce dense_vec (1024-d) + sparse_vec (BM42 IDF SparseVector).
2. **Qdrant Query API single-shot** con `Prefetch` + Fusion RRF:
   ```python
   qdrant.query_points(
     collection_name='sop',
     prefetch=[
       Prefetch(query=dense_vec, using='dense', limit=20,
                query_filter=acl_filter),
       Prefetch(query=sparse_vec, using='sparse', limit=20,
                query_filter=acl_filter),
     ],
     query=FusionQuery(fusion=Fusion.RRF),
     limit=20,
     with_payload=True,
   )
   ```
3. **Rerank** con `BGE-reranker-v2-m3` (FlagEmbedding library, MIT, multilingue, fp16):
   ```python
   pairs = [(query, hit.payload['text']) for hit in fused_top20]
   scores = reranker.compute_score(pairs, normalize=True)
   ranked = sorted(zip(fused_top20, scores), key=lambda x: -x[1])[:k]
   ```
4. **Return** `list[RagCitation]` con `source_uri`, `snippet`, `score` (rerank score), `retrieved_at`.

ACL filter `acl_filter` derivato da `user_roles → allowed_acl_levels` mapping costante:
```python
ROLE_TO_ACL = {
  'operator':   {'public'},
  'technician': {'public', 'internal'},
  'supervisor': {'public', 'internal'},
  'manager':    {'public', 'internal', 'restricted'},
  'engineer':   {'public', 'internal', 'restricted'},
  'safety':     {'public', 'internal', 'restricted'},
}
```

`acl_filter = Filter(must=[FieldCondition(key='acl_level', match=MatchAny(any=list(allowed_acl_levels)))])`.

**Why:** BM42 nativo evita double round-trip e usa server-side fusion. Rerank cross-encoder migliora NDCG@10 di 5-15 punti tipico (verifichiamo in A/B eval), e BGE-reranker-v2-m3 è stesso vendor di BGE-M3 (allineamento delle representations). Sempre attivo perché Phase 5 SLA non è hot-path real-time (agent latency-sensitive use HITL anyway). Eventuale opt-out `rerank=False` parameter del Tool resta esposto ma default `True`.

**Rejected alternatives:**
- Dense Qdrant + BM25 puro + RRF client-side: 2 round-trip, codice fusion da mantenere; BM42 server-side è più semplice.
- BGE-M3 unified (dense+sparse+colbert) con multi-vector: storage 4-6x, ingest più lento; il guadagno colbert-rerank è marginale vs BGE-reranker-v2-m3 dedicato.
- Rerank opt-in per tool: Phase 5 ships pipeline coerente, no fragmentation; eventual opt-out resta per casi degenere.
- No rerank Phase 5: rischia retrieval quality sub-par su SOP corpus con sinonimi tessili specifici.

## D-64 — Cross-lingual retrieval: fiducia BGE-M3, no query translation

**Decision:** Single multilingual collection (per D-61), nessuna query translation, nessun glossary expansion. La query in lingua source viene embedded via BGE-M3 (dense + BM42 sparse) e cerca su entrambe le lingue del corpus. Filter `lang` NON injected by default; esposto come parameter opzionale del Tool per casi explicit (es. user dice "trova SOP in EN").

Affidabilità verificata da A/B eval (D-67) con sotto-set cross-lingual queries: 1/3 delle 123 query nel testset sono `cross_lingual_en` (query EN su SOP IT corpus o viceversa). Acceptance: cross-lingual Recall@10 ≥ 0.70 (configurato in `docs/eval/rag-ab-test-bge-m3-vs-e5.md`; sotto-soglia → escalation a query translation Phase 11).

**Why:** BGE-M3 è progettato per allineare representations cross-lingua (MTEB ~63.0, top tier). Query translation aggiunge ~500ms-1s di LLM call + complessità fusion 4 ranking. Glossary expansion è additivo solo per sparse BM42; il dense BGE-M3 già copre semantica. KISS Phase 5; query translation differita a Phase 11 SE A/B eval fallisce target cross-lingual.

**Rejected alternatives:**
- Query fan-out con LLM translate: +500ms-1s/query, complessità fusion.
- Glossary-aware query expansion: deterministico ma copre solo termini noti; dense BGE-M3 già copre sinonimi semantici.

## D-65 — Neo4j Community 5.24 + APOC; popolazione deterministic

**Decision:**

**Choice:** Neo4j Community Edition 5.24 con plugin APOC (`["apoc"]`).
- Image: `neo4j:5.24-community`
- Bolt: 7687; HTTP browser: 7474 (dev only)
- Default credentials dev: `neo4j/devpassword` (override via `NEO4J_AUTH` env in `infra/compose/core.yml`)
- License: GPLv3 (acceptable per self-hosted; verificato A-018 PROJECT.md "open-source self-hosted first")
- Driver: `neo4j` Python AsyncDriver 5.x ufficiale; `from neo4j import AsyncGraphDatabase`

**Schema constraints (Phase 5 startup migration script `scripts/neo4j-bootstrap.py` idempotente):**
```cypher
CREATE CONSTRAINT machine_id_unique IF NOT EXISTS
  FOR (m:Machine) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT part_id_unique IF NOT EXISTS
  FOR (p:Part) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT failure_mode_id_unique IF NOT EXISTS
  FOR (f:FailureMode) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT sop_id_unique IF NOT EXISTS
  FOR (s:SOP) REQUIRE s.id IS UNIQUE;
CREATE INDEX sop_version IF NOT EXISTS FOR (s:SOP) ON (s.version);
```

**Populazione DETERMINISTIC (no LLM):**
- **Sources:**
  - `packages/sft-assets` 30 asset → `Machine` nodes (`id`, `family`, `name_it`, `name_en`)
  - `packages/sft-domain/failure_modes.yaml` (NEW Phase 5) → `FailureMode` nodes + mapping a `Part` + `asset_families` → derive `Machine -[:HAS_PART]-> Part -[:HAS_FAILURE_MODE]-> FailureMode`
  - SOP frontmatter (`id`, `version`, `asset`, `asset_family`) → `SOP` nodes + `FailureMode -[:DOCUMENTED_BY]-> SOP`
- **Cypher MERGE pattern idempotent** (re-ingest = no duplicate):
  ```cypher
  UNWIND $sop_rows AS row
  MERGE (s:SOP {id: row.sop_id})
    ON CREATE SET s.version = row.version, s.lang = row.lang,
                  s.title = row.title, s.created_at = datetime()
    ON MATCH SET  s.version = row.version, s.updated_at = datetime()
  WITH s, row
  MATCH (f:FailureMode {id: row.failure_mode_id})
  MERGE (f)-[r:DOCUMENTED_BY]->(s)
    ON CREATE SET r.created_at = datetime()
  ```

**Failure modes YAML structure (`packages/sft-domain/failure_modes.yaml`):**
```yaml
failure_modes:
  - id: broken_end
    name_it: rottura filo ordito
    name_en: broken end
    asset_families: [weaving]
    parts: [warp, heddle]
    severity: medium
  - id: mispick
    name_it: trama saltata
    name_en: mispick
    asset_families: [weaving]
    parts: [shuttle, reed]
  # ... derivati da defect taxonomy Phase 2
```

**CI validator (`tests/test_graph_population.py` integration test):**
- Ogni `FailureMode` in YAML ha ≥ 1 SOP `DOCUMENTED_BY` (else fail con elenco orphan)
- Ogni `Machine` ha ≥ 1 `Part` (sanity check)
- Schema constraints rispettati (no duplicate id)

**Why:** Neo4j ha ecosystem più maturo (driver Python ufficiale stabile 5.x, plugin LangChain `Neo4jGraph` first-class, APOC procedures per analytics). Memgraph è in-memory veloce ma ecosystem più piccolo + BSL license aggiunge un'analisi legale che non vogliamo affrontare ora. Apache AGE (PG extension) sarebbe stato bello per riusare PG ma deviazione STACK.md significativa + maturità inferiore. Popolazione deterministic evita hallucination risk (anti-pattern ARCHITECTURE.md: agent non scrive al knowledge store) e produce grafo riproducibile (re-ingest = stesso grafo).

**Rejected alternatives:**
- Memgraph OSS: ecosystem ridotto, BSL license complicato per redistribuzione.
- Apache AGE su PG: maturity media, Cypher dialect parziale, deviazione STACK.
- Hybrid LLM enrichment HITL-gated: bello in teoria ma scope creep Phase 5; LLM extraction relazioni differita a Phase 8 KnowledgeCurator se utile.
- Full LLM extraction at ingest: anti-pattern dichiarato ARCHITECTURE.md.

## D-66 — GraphRAG: 2 Tool LangChain separati (`rag_search` + `traverse_graph`)

**Decision:** Espongo ad agent due Tool indipendenti, composizione lato agent:

**Tool 1 — `rag_search` (in `packages/sft-knowledge/src/sft_knowledge/tools/rag.py`):**
```python
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

class RagSearchInput(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    query: str
    user_roles: list[str]                       # caller fornisce; tool calcola acl_levels
    category: Literal['sop','manuals','troubleshooting','training'] = 'sop'
    k: int = Field(default=5, ge=1, le=20)
    lang: Literal['it','en'] | None = None      # default cross-lingual
    sop_ids: list[str] | None = None            # filter compositionale (da traverse_graph)
    asset_family: str | None = None
    rerank: bool = True

class RagSearchTool(BaseTool):
    name = "rag_search"
    description = "Cerca chunks nel knowledge base con hybrid retrieval (dense+sparse+rerank). Restituisce RagCitation list."
    args_schema = RagSearchInput
    async def _arun(self, **kwargs) -> list[RagCitation]: ...
```

**Tool 2 — `traverse_graph` (in `packages/sft-knowledge/src/sft_knowledge/tools/graph.py`):**
```python
class TraverseGraphInput(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    seed_label: Literal['Machine','Part','FailureMode','SOP']
    seed_id: str
    relation_path: list[Literal['HAS_PART','HAS_FAILURE_MODE','DOCUMENTED_BY']]
    max_depth: int = Field(default=3, ge=1, le=5)

class TraverseGraphTool(BaseTool):
    name = "traverse_graph"
    description = "Naviga il grafo entity (Machine→Part→FailureMode→SOP) seguendo relation_path. Restituisce list[GraphNode]."
    args_schema = TraverseGraphInput
    async def _arun(self, **kwargs) -> list[GraphNode]: ...
```

Cypher templating in `traverse_graph` usa **SOLO parametri** ($-prefix), MAI string interpolation:
```python
cypher = f"MATCH (n:{seed_label} {{id: $seed_id}})-[:{relation_pipe}]->(m) RETURN m LIMIT $limit"
# OK: seed_label/relation sono Literal whitelist (validato Pydantic); ma $seed_id PARAMETRO
```

**Esempio composizione agent (Phase 7 RCASpecialist hypothetical):**
```python
# 1. Da failure mode trovo SOP candidate
sops = await traverse_graph.ainvoke({
  'seed_label': 'FailureMode',
  'seed_id': 'broken_end',
  'relation_path': ['DOCUMENTED_BY']
})
# 2. Cerco chunk specifici DENTRO SOP candidate
results = await rag_search.ainvoke({
  'query': 'come riparare rottura filo ordito su telaio Picanol',
  'user_roles': ['technician'],
  'sop_ids': [s.id for s in sops],
  'k': 5
})
```

**Why:** Composizione esplicita = audit trail chiaro (EvidencePanel registra tool_calls separati con args/results). Ogni tool è testabile in isolamento. Agent (Phase 6-9) può scegliere strategy. Pattern allineato a `query_timescale` + altri Tool Phase 3 (granular).

**Rejected alternatives:**
- Unified `graphrag_search`: opaco, harder debug, agent perde controllo.
- RAG only + traverse_graph senza join: success criterion #4 lo vuole; servirebbe comunque entrambi i tool.

## D-67 — Ingest pipeline: Markdown-only Phase 5 + DocumentParser ABC pluggable

**Decision:**

**ABC interface (`packages/sft-knowledge/src/sft_knowledge/parsers/base.py`):**
```python
from abc import ABC, abstractmethod
from pathlib import Path
from pydantic import BaseModel

class ParsedSection(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    heading_path: list[str]
    text: str

class ParsedDoc(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    source_uri: str
    frontmatter: dict
    sections: list[ParsedSection]
    version: str
    lang: Literal['it','en']

class DocumentParser(ABC):
    @abstractmethod
    async def parse(self, path: Path) -> ParsedDoc: ...
    @abstractmethod
    def supported_extensions(self) -> set[str]: ...
```

**Phase 5 ships `MarkdownParser` only:**
- Frontmatter: `python-frontmatter` lib
- Headings extraction: regex `^(#{1,6})\s+(.+)$` con state machine per `heading_path` accumulato
- ACL: legge `acl_level` (campo obbligatorio Phase 5); se mancante → log WARN + default `internal` (NON `restricted` per evitare leak silenzioso di documento legittimo)
- Status filter: SOLO SOP con `status: 'reviewed'` (Phase 2 D-25 gate) vengono indicizzati; `draft` / `in_review` skipped con log info

**Differiti a Phase 8 (KnowledgeCurator):**
- `PdfParser` (docling consigliato per qualità layout 2025, MIT)
- `DocxParser` (python-docx o docling)
- `HtmlParser` (BeautifulSoup + heading detection)

**Scope deviation note:** KNW-04 letterale dice "PDF/DOCX/HTML/MD → chunking → embedding → upsert". Phase 5 chiude solo MD (100% del corpus attuale). La pipeline E2E è completa; il `DocumentParser` ABC permette aggiunta parser in Phase 8 senza modificare `QdrantIndexer` o `Neo4jGraphBuilder`. ROADMAP edit task NON necessario (la requirement KNW-04 rimane in Phase 5 con scope MD; eventual completamento PDF/DOCX/HTML su Phase 8 è tracciato come supplement non-blocking).

**Why:** Phase 5 corpus è 100% Markdown. Aggiungere docling/unstructured introduce +500MB image Docker + dipendenze pesanti (PyTorch, Tesseract) + complessità testing su 0 PDF reali esistenti. ABC pluggable mantiene il future-proofing senza pagare costo Phase 5. Phase 8 KnowledgeCurator emergerà come naturale momento per estendere parser (è il suo job aggiungere documenti reali al corpus).

**Rejected alternatives:**
- docling integration Phase 5: scope creep, zero PDF reali da testare.
- unstructured.io Phase 5: stesso problema, qualità PDF layout inferiore a docling 2025.

## D-68 — Reindex incrementale: Git CI hook + CLI manuale (no daemon Phase 5)

**Decision:**

**GitHub Actions workflow `.github/workflows/reindex.yml`:**
```yaml
on:
  push:
    branches: [main]
    paths:
      - 'simulators/synthetic-corpus/**'
      - 'docs/sops/**'              # future user-managed SOP location
      - 'packages/sft-domain/failure_modes.yaml'  # graph schema change
  workflow_dispatch:                # manual trigger

jobs:
  reindex:
    runs-on: ubuntu-latest
    services:
      qdrant: { image: qdrant/qdrant:v1.16.1, ports: ['6333:6333'] }
      neo4j:  { image: neo4j:5.24-community, env: {NEO4J_AUTH: 'neo4j/cipassword'} }
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Compute diff
        run: |
          git diff --name-only ${{ github.event.before }} ${{ github.sha }} \
            -- 'simulators/synthetic-corpus/**' 'docs/sops/**' \
            > changed.txt
      - run: nx run knowledge-ingest:run --files=$(paste -sd, changed.txt)
```

**CLI per dev (`apps/knowledge-ingest` or `services/knowledge-ingest`):**
```bash
$ nx run knowledge-ingest:run --paths=simulators/synthetic-corpus/it/loom/
$ nx run knowledge-ingest:run --files=simulators/synthetic-corpus/it/loom/SOP-LOOM-001-...md,simulators/synthetic-corpus/en/loom/SOP-LOOM-001-...md
$ nx run knowledge-ingest:bootstrap   # full re-ingest (rare; CI usa solo diff)
```

**Ingest state tracking (PG, lightweight, NEW migration 005 wait — actually Phase 5 number is `infra/migrations/timescale/006_create_ingest_state.sql`):**
```sql
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE TABLE IF NOT EXISTS knowledge.ingest_state (
  source_uri    TEXT PRIMARY KEY,
  content_hash  TEXT NOT NULL,              -- sha256 del file content
  version       TEXT NOT NULL,              -- da frontmatter
  indexed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  chunk_count   INT NOT NULL,
  collection    TEXT NOT NULL,              -- 'sop'|'manuals'|...
  acl_level     TEXT NOT NULL
);
CREATE INDEX idx_ingest_state_version ON knowledge.ingest_state (version);
```

Idempotency: ingest workflow per file = `(parse → chunk → embed → upsert Qdrant + MERGE Neo4j → UPSERT ingest_state)`. Se `content_hash` invariato vs ultimo `indexed_at`, skip (early exit log).

**Watcher real-time DEFERRED:**
- Phase 10 quando UI upload entra (filesystem watcher su mount volume) o webhook UI POST `/v1/knowledge/upload`
- Phase 5 NON ships daemon (KISS); CI + CLI coprono dev + push workflow

**Why:** Tutto il knowledge attuale viene committato Git (corpus sintetico Phase 2); push to main è single source of truth. Diff `git diff --name-only` su path filter è deterministico, audit-friendly, zero infra aggiuntiva. CLI per dev = onboarding semplice. Watcher daemon è complessità che paga solo quando ci sono upload non-Git (deferred Phase 10 quando UI emerge).

**Rejected alternatives:**
- Watchdog filesystem daemon Phase 5: nuovo servizio long-running, race conditions su rename, complessità deployment.
- Polling scheduler Phase 5: I/O cost scan ricorrente.

## D-69 — Idempotency point.id = sha256(source_uri + chunk_idx + text)

**Decision:** Qdrant `PointStruct.id = blake3(f"{source_uri}|{chunk_idx}|{text}").hex()[:32]` (UUID-shaped hex per Qdrant point ID requirement). Re-ingest stesso content = stesso ID = UPSERT no-op (Qdrant atomic).

Quando `version` di un SOP cambia (frontmatter `version: "1.0" → "1.1"`):
- Text dei chunk può differire → chunk_idx + text → ID diversi → nuove entry create
- Old entry per `source_uri` rimangono in collection finché PURGE explicit:
  ```python
  # ingest_state ha PRIMARY KEY (source_uri); detecting version change:
  if state.version != new_doc.version:
      # 1. delete old chunks: Qdrant filter delete by source_uri + version
      qdrant.delete(collection, points_selector=Filter(must=[
        FieldCondition(key='source_uri', match=MatchValue(value=source_uri)),
        FieldCondition(key='version', match=MatchValue(value=state.version)),
      ]))
      # 2. delete old Neo4j SOP node + relations (CASCADE not native; explicit)
      # SOP node con version diversa: MERGE crea new node se id+version differ
      # Phase 5 design: SOP.id include version → MERGE SOP {id: f"{sop_id}@{version}"} unique
  ```

NOTA Neo4j: `SOP.id` formato come `{sop_id}@{version}` per supportare multi-version coexistence (history retained, audit-friendly). FailureMode → DOCUMENTED_BY → SOP(latest) updated da ingest pipeline (DELETE old DOCUMENTED_BY edge, MERGE new).

**Why:** Deterministic IDs = idempotent UPSERT = re-run sicuro. blake3 più veloce di sha256 (~5x), Python stdlib disponibile da 3.12 via `hashlib`. Mantenere versions multiple in Neo4j supporta auditing storico ("quale SOP version era live quando RCA è stato fatto?").

**Rejected alternatives:**
- sha256(text) puro: dedup cross-file ma perde tracciabilità `source_uri` se duplicati.
- UUIDv4 random + PG mapping table: statefull, +1 round-trip, fragile a crash.

## D-70 — Package layout: nuovo `packages/sft-knowledge` + service `services/knowledge-ingest`

**Decision:**

**Nuovo package `packages/sft-knowledge/` (mirror pattern sft-agents/sft-tools/sft-domain):**
```
packages/sft-knowledge/
├── pyproject.toml
├── project.json                       # Nx target wiring
├── src/sft_knowledge/
│   ├── __init__.py                    # public API exports
│   ├── parsers/
│   │   ├── base.py                    # DocumentParser ABC + ParsedDoc/ParsedSection
│   │   └── markdown.py                # MarkdownParser implementation
│   ├── chunking/
│   │   └── semantic.py                # SemanticChunker (LlamaIndex wrapper)
│   ├── embedding/
│   │   └── bge_m3.py                  # BGE-M3 wrapper (FastEmbed) + sparse vec
│   ├── stores/
│   │   ├── qdrant.py                  # QdrantIndexer (collection bootstrap + upsert)
│   │   └── neo4j.py                   # Neo4jGraphBuilder (constraints + MERGE)
│   ├── retrieval/
│   │   ├── reranker.py                # BGE-reranker-v2-m3 wrapper
│   │   └── pipeline.py                # full retrieval orchestration
│   ├── tools/
│   │   ├── rag.py                     # RagSearchTool (LangChain BaseTool)
│   │   └── graph.py                   # TraverseGraphTool
│   ├── memory/
│   │   └── qdrant_long_term.py        # QdrantLongTermMemory(MemoryStore) — replaces D-59 stub
│   └── models.py                      # RagCitation (use sft-agents.models if exists), GraphNode, etc.
└── tests/
    ├── test_markdown_parser.py
    ├── test_semantic_chunker.py
    ├── test_qdrant_indexer.py         # @pytest.mark.integration testcontainers
    ├── test_neo4j_builder.py          # @pytest.mark.integration
    └── test_retrieval_e2e.py          # @pytest.mark.integration full pipeline
```

**Public API (`__init__.py`):**
```python
from sft_knowledge.parsers import DocumentParser, MarkdownParser, ParsedDoc
from sft_knowledge.chunking import SemanticChunker
from sft_knowledge.embedding import BgeM3Embedder
from sft_knowledge.stores import QdrantIndexer, Neo4jGraphBuilder
from sft_knowledge.retrieval import RetrievalPipeline, BgeReranker
from sft_knowledge.tools import RagSearchTool, TraverseGraphTool
from sft_knowledge.memory import QdrantLongTermMemory
```

**Service `services/knowledge-ingest/` (apps-like CLI consumer del package):**
```
services/knowledge-ingest/
├── pyproject.toml                     # depends on sft-knowledge, sft-domain, sft-assets
├── project.json                       # Nx targets: run, bootstrap, validate
├── src/svc_knowledge_ingest/
│   ├── __main__.py                    # CLI entrypoint (typer/argparse)
│   ├── pipeline.py                    # orchestrates: parse → chunk → embed → upsert + graph MERGE
│   └── state.py                       # ingest_state PG read/write
└── tests/
    └── test_ingest_pipeline.py        # @pytest.mark.integration
```

**Pyproject deps additions (`sft-knowledge`):**
- `qdrant-client[fastembed]>=1.16` — Qdrant + FastEmbed (BM42 sparse)
- `FlagEmbedding>=1.3` — BGE-M3 + BGE-reranker
- `llama-index-core>=0.11` + `llama-index-embeddings-huggingface>=0.3` — SemanticSplitter
- `neo4j>=5.24` — async driver
- `python-frontmatter>=1.1` — SOP frontmatter parsing
- `pydantic>=2.7` (already locked)
- `langchain-core>=0.3` — BaseTool

**Pyproject deps additions (`services/knowledge-ingest`):**
- `sft-knowledge` (workspace)
- `sft-domain` (workspace)
- `sft-assets` (workspace)
- `asyncpg>=0.29` — PG ingest_state
- `typer>=0.12` — CLI
- `structlog` (consistent)

**Why:** Cohesion — il knowledge stack ha dipendenze pesanti (BGE-M3 ~568M, FlagEmbedding, llama-index, Neo4j driver) che NON vogliamo trasudare in `sft-tools` (importato da ogni agent). Service ingest separato perché ha lifecycle diverso (CLI / scheduled job) vs library reusable.

**Rejected alternatives:**
- Extend `sft-tools` con `sft_tools.rag` e `sft_tools.graph`: sft-tools diventa monolitico con dipendenze BGE-M3/Neo4j che ogni agent paga.

## D-71 — A/B eval BGE-M3 vs multilingual-e5-large: synthetic Q-gen + 10% manual spot-check

**Decision:**

**Test set generation script (`services/knowledge-ingest/scripts/generate_rag_testset.py`):**
1. Itera tutti i SOP `status: reviewed` (41 in Phase 2 corpus)
2. Per ogni SOP, invoca Qwen2.5-7B (Ollama via Phase 4 LLM adapter, `temperature=0.3`, `seed=42`):
   ```python
   prompt = """
   Dato il seguente SOP (testo + frontmatter), genera 3 query:
   1. KEYWORD IT: query stile keyword (3-6 parole, italiano)
   2. NATURAL IT: query stile domanda naturale (italiano, max 20 parole)
   3. CROSS-LINGUAL EN: query in inglese che ANDREBBE risposta da questo SOP
      (anche se SOP è italiano)
   
   Per ogni query, indica anche il `target_section` (heading_path approssimativo).
   Output JSON: [{type, lang, text, target_section}, ...]
   """
   queries = await llm_adapter.invoke(prompt + sop_content)
   ```
3. Per ogni query: salva record nel testset con ground truth chunk ID (mapping `target_section` → chunk via heading_path).

**Test set size:** ~41 SOP × 3 query = ~123 query (forse meno se SOP corti riducono naturalness; min target 100).

**Manual spot-check 10%:** Random 12 query (10% di 123), reviewer human (Federico o domain expert) marca: (a) query realistic (yes/no), (b) target chunk corretto (yes/no). Reject rate atteso < 20% (se > 20%, regenerate con prompt revision).

**Persistenza testset:** `tests/data/rag_eval/testset.jsonl` (committed in repo per riproducibilità; seed=42 garantisce regen-deterministico):
```jsonl
{"id":"q-001","query":"come riparo rottura filo ordito","lang":"it","type":"natural_it","gold_sop_id":"SOP-LOOM-001","gold_chunk_idx":2}
{"id":"q-002","query":"warp thread break troubleshooting","lang":"en","type":"cross_lingual_en","gold_sop_id":"SOP-LOOM-001","gold_chunk_idx":2}
...
```

**Eval script (`services/knowledge-ingest/scripts/run_ab_eval.py`):**
- Per ogni embedding model in `[bge_m3, multilingual_e5_large]`:
  1. Re-index corpus con quel modello in collection separata (`sop_bgem3`, `sop_e5large`)
  2. Per ogni query in testset: run retrieval (con rerank attivo D-63 stesso BGE-reranker per fairness)
  3. Calcola metriche: NDCG@10, MRR, Recall@10, Recall@5 (subset cross-lingual `lang_query != lang_doc`)
  4. Aggrega per (model, lang, type)
- Output: `docs/eval/rag-ab-test-bge-m3-vs-e5.md` con:
  - Tabella metriche side-by-side
  - Mermaid chart per type (keyword/natural/cross-lingual)
  - **Justified decision section:** "We choose BGE-M3 because..." con quantitative + qualitative reasoning
  - Reproducibility: comando per re-run + seed + test set hash

**Acceptance gates (success criterion #5 + bonus quality):**
- BGE-M3 NDCG@10 IT keyword ≥ 0.80
- BGE-M3 NDCG@10 IT natural ≥ 0.75
- BGE-M3 cross-lingual Recall@10 ≥ 0.70 (success criterion #1)
- Vincitore documentato con ≥ 3 punti percentuale delta in almeno 2 metriche (else "comparable, default BGE-M3 per MIT + multimodal")

**Why:** Synthetic Q-gen è scalabile e copre tutto il corpus (vs manual labeling 50+50 che copre subset). Seed=42 garantisce riproducibilità. Spot-check 10% mitiga LLM-bias circolare (genera + valuta con stesso modello family). Cross-lingual subset esplicito target il success criterion #1. Acceptance gate threshold tarato su benchmark MIRACL multilingual (BGE-M3 paper riporta NDCG@10 0.75-0.85 range).

**Rejected alternatives:**
- Manual labeling 100 queries: 4-8h upfront work, copre subset, scarsa scalabilità futura.
- Adattare MTEB tessile: nessun benchmark tessile esistente, costruzione da zero comunque richiesta.

## D-72 — ACL frontmatter migration: `acl_level` campo obbligatorio + 41 SOP migration

**Decision:**

**Aggiunta campo frontmatter `acl_level`:**
```yaml
# 41 SOP esistenti vanno migrati. Pattern:
acl_level: public|internal|restricted
```

**Default mapping (script `scripts/migrate-sop-acl.py` one-shot in Phase 5):**
- `audience: operations` → `acl_level: public`
- `audience: maintenance` → `acl_level: internal`
- `audience: quality` → `acl_level: internal`
- `audience: engineering` → `acl_level: internal`
- `audience: management` → `acl_level: restricted`
- `audience: safety` → `acl_level: restricted`
- Default fallback se `audience` mancante: `internal` (conservative)

Migration script aggiunge `acl_level` field dove mancante (idempotent: skip se già presente). Output report: file migrati, audience → acl mapping applicato per ognuno. Commit `chore(05-NN-acl-migration): add acl_level to 41 SOP frontmatter`.

**CI validator (`tests/test_frontmatter_validator.py` extension Phase 2 validator):**
- Ogni SOP deve avere `acl_level` (else fail with file path)
- `acl_level` must be in `{public, internal, restricted}`

**Retrieval enforcement (in `RagSearchTool`):**
```python
ROLE_TO_ACL = {
  'operator':   {'public'},
  'technician': {'public', 'internal'},
  'supervisor': {'public', 'internal'},
  'manager':    {'public', 'internal', 'restricted'},
  'engineer':   {'public', 'internal', 'restricted'},
  'safety':     {'public', 'internal', 'restricted'},
}
allowed = set().union(*(ROLE_TO_ACL[r] for r in user_roles))
acl_filter = Filter(must=[FieldCondition(
  key='acl_level', match=MatchAny(any=sorted(allowed))
)])
```

**Non-leak test (Phase 5 success criterion #2):**
- `tests/test_acl_enforcement.py @pytest.mark.integration`:
  - Indexa corpus con vari `acl_level`
  - User con role `operator` (allowed={public}) cerca query che matcha SOP `restricted`
  - Assert: result list NON contiene chunk con `acl_level=restricted` (zero leak)
  - Verify Qdrant query log conferma filter applicato

**Why:** Pre-filter at engine level (Qdrant) = zero leak guarantee (a meno di bug in filter construction; testato esplicitamente). Esplicito `acl_level` field elimina ambiguity del mapping `audience → acl`; mapping è documentato e applicato in migrazione one-shot ma poi è il `acl_level` che governa retrieval (verifiable independently). 41 SOP migration è bounded effort.

**Rejected alternatives:**
- Post-filter Python in retrieval tool: leak risk se bug, k effettivo variabile, audit complesso.
- Mapping deterministico da `audience` senza nuovo campo: meno espressivo, future granularity ortogonale non supportata.

</decisions>

<scope_boundaries>

**In scope (Phase 5):**
- `packages/sft-knowledge/` new package: parsers (Markdown only + ABC), chunking (SemanticSplitter), embedding (BGE-M3), stores (Qdrant + Neo4j), retrieval (pipeline + rerank), tools (RagSearchTool + TraverseGraphTool), memory (QdrantLongTermMemory replacing D-59 stub)
- `services/knowledge-ingest/` CLI service consuming sft-knowledge
- Qdrant 4 collections bootstrap (`sop`, `manuals`, `troubleshooting`, `training`) — `manuals`/`troubleshooting`/`training` ship con scaffold + 0 docs (Phase 8 popola)
- Neo4j Community 5.24 added to `infra/compose/core.yml` + Helm chart skeleton
- Neo4j schema constraints + APOC plugin enabled
- `packages/sft-domain/failure_modes.yaml` (NEW) + loader + CI validator
- 41 SOP frontmatter migration: add `acl_level` field (one-shot script)
- Phase 2 frontmatter validator extension (require `acl_level`)
- PG migration `006_create_ingest_state.sql` (or next available number) — `knowledge.ingest_state` table
- BGE-M3 ingest pipeline + BGE-reranker-v2-m3 retrieval pipeline (CPU-default; GPU optional via env)
- Cross-lingual retrieval verified via A/B eval test set (no query translation)
- A/B eval: synthetic Q-gen script + run_ab_eval script + `docs/eval/rag-ab-test-bge-m3-vs-e5.md` deliverable
- GitHub Actions `reindex.yml` workflow
- Nx CLI targets: `nx run knowledge-ingest:run`, `:bootstrap`, `:validate`
- Pytest unit + integration tests (testcontainers Qdrant + Neo4j)
- ACL non-leak test (`@pytest.mark.integration`)
- Cross-lingual retrieval E2E test (Phase 5 success criterion #1)
- ROADMAP edit (Phase 5 plan count + close Phase 5 box on completion); minor edit to KNW-04 scope note (MD-only Phase 5; PDF/DOCX/HTML deferred Phase 8)
- Docs: `docs/knowledge-layer/` MkDocs pages IT+EN (architecture, retrieval pipeline, ACL model, A/B eval results)

**Explicitly NOT in scope (deferred):**
- **PDF/DOCX/HTML parsers** → Phase 8 (KnowledgeCurator) — `DocumentParser` ABC ready
- **Filesystem watcher daemon real-time** → Phase 10 (UI upload trigger emerge)
- **REST endpoint `/v1/knowledge/search`** → Phase 10 API gateway expansion (Phase 6-7 agent call direttamente via Tool import)
- **Stale-content detection logic** (TRN-01 full) → Phase 8 KnowledgeCurator — Phase 5 ships `ingest_state` table + indexed_at timestamp (data foundation only)
- **Dedup cross-document** (oltre `point.id` deterministic) → Phase 8 KnowledgeCurator
- **Document update notification (NATS event on reindex)** → Phase 8 (when agent reacts)
- **DeepEval CI gate hallucination rate** → Phase 11 (RAG eval gate)
- **RAGAS production monitoring** → Phase 11
- **GraphRAG join inline tool** (`graphrag_search` unified) → Phase 7+ se RCASpecialist lo richiede
- **LLM entity extraction enrichment** → Phase 8 (KnowledgeCurator HITL-gated, optional)
- **Manuals/Troubleshooting/Training corpus content** (only `sop` collection has data) → Phase 8 KnowledgeCurator + Phase 9 TrainingCoach popolano
- **Multi-tenancy ACL beyond 3 levels** (granular per-user / per-project) → Phase 11 governance
- **Embedding model fine-tuning su corpus tessile** → out of MVP

**Out-of-bounds entirely (mentioned but excluded):**
- ColBERT multi-vector storage in Qdrant: A-014 KISS Phase 5
- Real-time semantic search latency optimization: Phase 11
- Knowledge graph visualization UI (Neo4j Browser è dev-only): Phase 10

</scope_boundaries>

<deferred_ideas>

**Recorded during this discussion but out of Phase 5 scope:**

- **Filesystem watcher (watchdog) daemon**: real-time per upload non-Git → Phase 10 UI o quando emerge bisogno
- **REST endpoint `/v1/knowledge/search`**: agent call diretto via Tool import sufficiente Phase 5; REST utile per UI Phase 10
- **PDF/DOCX/HTML parsers (docling vs unstructured)**: deferred Phase 8 KnowledgeCurator (emergerà bisogno con upload reali)
- **LLM entity extraction HITL-gated** per arricchire grafo: Phase 8 KnowledgeCurator (opzionale)
- **Unified `graphrag_search` tool** (vector + graph join interno): Phase 7+ se RCASpecialist Phase 7 lo trova necessario
- **Query translation cross-lingual fallback**: Phase 11 SE A/B eval mostra cross-lingual Recall@10 sotto target
- **Glossary-aware query expansion**: idem Phase 11
- **Multi-version SOP coexistence query** (history retrieval): Neo4j già supporta via `SOP.id = {id}@{version}`; Phase 5 ships data foundation, Phase 8 KnowledgeCurator espone come Tool
- **Dedup detector cross-document** (sha256 text vs source_uri composite): Phase 8 KnowledgeCurator (TRN-01 dedup business logic)
- **Stale-content threshold detector** (es. `indexed_at < NOW() - 180 days`): Phase 8 KnowledgeCurator (TRN-01)
- **Adaptive rerank threshold per query type** (keyword vs natural): Phase 11 retrieval tuning
- **Fine-tuning BGE-M3 su corpus tessile** (LoRA su Qwen-like adapter): out of MVP
- **Neo4j cluster HA** (Enterprise only): out of OSS scope
- **Embedding GPU-acceleration batch ingest**: Phase 11 perf hardening
- **Multi-tenant ACL (per-project, per-team)**: Phase 11 governance

</deferred_ideas>

<claudes_discretion>

Areas where the user did not request explicit discussion — Claude's PLAN will follow these sensible defaults:

- **Qdrant collection bootstrap script:** `scripts/qdrant-bootstrap.py` idempotente (CREATE COLLECTION IF NOT EXISTS, schema named vectors `dense` + `sparse`, payload index su `acl_level`, `lang`, `category`, `source_uri`).
- **Neo4j bootstrap script:** `scripts/neo4j-bootstrap.py` idempotente: schema constraints + APOC config + initial Machine seed from `sft-assets`.
- **BGE-M3 model loading:** lazy singleton (`@lru_cache`) per process; FastEmbed default, FlagEmbedding fallback if FastEmbed unavailable; `BGE_M3_DEVICE` env (cpu/cuda) default `cpu`.
- **BGE-reranker model loading:** stessa lazy singleton; fp16 on GPU, fp32 on CPU.
- **Tokenizer per chunk_size assertion:** `tiktoken` cl100k base per logging chunk size (BGE-M3 ha tokenizer suo ma cl100k è proxy accettabile).
- **Qdrant point batch size:** 100 punti per upsert call (sweet spot Qdrant 1.16).
- **Neo4j MERGE batch size:** UNWIND $rows max 500 per query (Neo4j sweet spot driver async).
- **`RagCitation.snippet`:** primi 200 char del chunk text (per UI preview senza payload bloat).
- **Logging spans:** Langfuse callback su `rag.search` (sub-span: `embed`, `qdrant.query`, `rerank`), `graph.traverse` (sub-span: `cypher.execute`).
- **`thread_id` integration:** Phase 5 tools sono context-aware via LangGraph state (`config['configurable']['thread_id']`); ogni RagCitation include `retrieved_at` per audit reproducibility.
- **Conventional commit scope:** `feat(05-NN-slug):` per atomic commit (consistente Phase 1-4).
- **Pyproject deps versioning:** pinned via `>=` minor (no `==` lock); uv resolves transitive.
- **CI smoke test:** Phase 5 CI adds `nx run-many --target=test --projects=sft-knowledge,knowledge-ingest` + integration test job with testcontainers (Qdrant + Neo4j + PG).
- **DocumentationParser ABC location:** `packages/sft-knowledge/src/sft_knowledge/parsers/base.py` (Phase 8 estende qui).
- **Frontmatter required fields enforced:** `id, title, version, lang, status, audience, acl_level` (acl_level NEW Phase 5).
- **Index payload fields (Qdrant payload index):** `source_uri`, `acl_level`, `lang`, `category`, `version`, `asset_family`, `sop_id` (for fast filter at retrieval time).
- **Test fixtures:** `tests/conftest.py` extends Phase 3 fixture con `qdrant_client` (testcontainer) + `neo4j_driver` (testcontainer); `@pytest.mark.integration` per testcontainers; CI runs both marker classes con concurrency 1 per port collision avoidance.
- **MkDocs nav:** Phase 5 aggiunge sezione "Knowledge Layer" sotto "Architecture": `architecture.md`, `retrieval-pipeline.md`, `acl-model.md`, `eval-results.md` (IT + EN parallel).

</claudes_discretion>

<downstream_guidance>

**For gsd-phase-researcher (Phase 5):**

Research focus areas (high → low priority):
1. **Qdrant 1.16 Query API + Prefetch + Fusion RRF + named vectors (dense+sparse)** — Python client `query_points` syntax con multiple Prefetch; FusionQuery API; BM42 sparse via FastEmbed (`SparseVector` format); payload index optimization.
2. **BGE-M3 unified embedding deployment** — FastEmbed integration (default), FlagEmbedding fallback; CPU vs GPU perf; sparse vector format compatibility con Qdrant SparseVector.
3. **BGE-reranker-v2-m3 inference** — FlagEmbedding `FlagReranker` API; batch scoring; fp16/fp32 tradeoffs; multilingue verification (IT+EN sample latency).
4. **LlamaIndex SemanticSplitter** — `SemanticSplitterNodeParser` API; embed_model wrapper (HuggingFaceEmbedding con BGE-M3); buffer_size/threshold tuning per markdown SOP; integration con frontmatter retention.
5. **Neo4j 5.24 Community + AsyncDriver Python** — schema constraints API; APOC procedure list (utili: `apoc.merge.relationship`, `apoc.export.cypher` per backup); driver session/transaction patterns; Cypher parametrized queries (sicurezza); UNWIND batch MERGE pattern.
6. **GraphRAG patterns** — Qdrant + Neo4j join strategies; LangChain `Neo4jGraph` integration (anche se Phase 5 usa driver diretto); pattern di `traverse → filter Qdrant by graph result`.
7. **Cross-lingual retrieval evaluation** — MIRACL benchmark methodology; NDCG/MRR/Recall@k computation; multilingue-e5-large vs BGE-M3 head-to-head literature 2025.
8. **Synthetic question generation con LLM** — patterns per generare query realistiche da source documents (prompt engineering, type diversity, ground truth alignment); seed determinism con Ollama Qwen.
9. **Qdrant collection bootstrap idempotency** — CREATE COLLECTION IF NOT EXISTS pattern, payload index creation, schema migration in-place (es. aggiungere campo payload non richiede re-creation).
10. **`python-frontmatter` lib + Markdown heading extraction** — robust YAML frontmatter parsing; heading-aware text walker per `heading_path` accumulation.

NOT research (already decided in CONTEXT.md):
- Qdrant collection topology (D-61)
- Chunking strategy (D-62)
- Hybrid retrieval pipeline (D-63)
- Cross-lingual approach (D-64)
- Graph DB choice + population (D-65)
- Tool granularity (D-66)
- Parser scope (D-67)
- Reindex trigger (D-68)
- Idempotency strategy (D-69)
- Package layout (D-70)
- A/B eval methodology (D-71)
- ACL frontmatter (D-72)

**Output a Validation Architecture section** (Nyquist applies — cross-lingual E2E test, ACL non-leak test, idempotent reindex test, graph CI validator, A/B eval acceptance gates).

**For gsd-planner (Phase 5):**

Expected plan count: **8-10 plans** with clear wave structure:

- **Wave 1 (foundation, parallel):**
  - Plan 05-01 `sft-knowledge` SDK base: package scaffold + Pydantic models (`ParsedDoc`, `ParsedSection`, `RagCitation`, `GraphNode`) + ABCs (`DocumentParser`) + `MarkdownParser` + tests (unit-only)
  - Plan 05-02 ACL migration: `migrate-sop-acl.py` + 41 SOP frontmatter update + frontmatter validator extension + commit migration
  - Plan 05-03 `failure_modes.yaml` + loader: schema YAML in `sft-domain` + Pydantic loader + 30+ failure modes derivati da Phase 2 defect taxonomy + CI validator

- **Wave 2 (infra, parallel):**
  - Plan 05-04 Qdrant bootstrap + collection schema: `scripts/qdrant-bootstrap.py` + 4 collections + named vectors (dense+sparse BM42) + payload indexes + tests testcontainer
  - Plan 05-05 Neo4j compose + bootstrap: aggiunta service in `infra/compose/core.yml` + `scripts/neo4j-bootstrap.py` schema constraints + APOC config + Helm chart skeleton + tests testcontainer
  - Plan 05-06 PG migration `006_create_ingest_state.sql` + asyncpg state module

- **Wave 3 (pipeline, parallel after Wave 1+2):**
  - Plan 05-07 Embedding + chunking stack: `BgeM3Embedder` wrapper (FastEmbed default + FlagEmbedding fallback) + `SemanticChunker` (LlamaIndex wrapper) + unit tests (mock embed) + integration test su 1 SOP reale
  - Plan 05-08 Qdrant indexer + Neo4j graph builder: `QdrantIndexer.upsert_batch` + `Neo4jGraphBuilder.merge_sop` + idempotency point.id sha256/blake3 + tests integration

- **Wave 4 (integration):**
  - Plan 05-09 Retrieval pipeline + tools: `RetrievalPipeline` (embed → Qdrant Query → rerank) + `BgeReranker` + `RagSearchTool` (LangChain BaseTool) + `TraverseGraphTool` + ACL non-leak test + cross-lingual E2E test + `QdrantLongTermMemory` (replace D-59 stub in sft-agents)
  - Plan 05-10 Ingest service + CLI + CI workflow: `services/knowledge-ingest/` Typer CLI + pipeline orchestrator + `nx run knowledge-ingest:run/:bootstrap` targets + GitHub Actions `reindex.yml` workflow + A/B eval script + `docs/eval/rag-ab-test-bge-m3-vs-e5.md` deliverable + MkDocs `docs/knowledge-layer/*.md` IT+EN

Each plan must have:
- Atomic commit boundaries `feat(05-NN-slug):`
- Frontmatter validation step before code
- `depends_on` short-form (e.g., `["05-01"]` per dipendenze SDK; `["05-04","05-05"]` per dipendenze infra; cross-package via workspace)

**Sizing constraints:**
- 1 plan = SDK foundation (parsers + models + ABC)
- 1 plan = ACL migration (bounded, one-shot)
- 1 plan = failure_modes YAML + loader
- 1 plan = Qdrant infra (bootstrap + schema)
- 1 plan = Neo4j infra (compose + bootstrap + Helm)
- 1 plan = PG ingest_state migration
- 1 plan = embedding + chunking
- 1 plan = indexer + graph builder
- 1 plan = retrieval pipeline + tools + memory replacement
- 1 plan = ingest service + CLI + CI + eval + docs

**Critical path:** Plan 05-09 (retrieval pipeline) bloccato da 05-04+05-05+05-07+05-08; Plan 05-10 (ingest service + eval) bloccato da 05-09 + 05-06.

**Wave parallelization (executor):** Wave 1 (3 plans parallel), Wave 2 (3 plans parallel), Wave 3 (2 plans parallel), Wave 4 (2 plans sequenziali).

</downstream_guidance>

<next_steps>

Run `/clear` to free context, then:

```
/gsd-plan-phase 5
```

This will:
1. Spawn `gsd-phase-researcher` → produces `05-RESEARCH.md`
2. Spawn `gsd-pattern-mapper` → produces `05-PATTERNS.md` (analogs from Phase 1/2/3/4)
3. Spawn `gsd-planner` → produces 8-10 `05-NN-slug-PLAN.md` files
4. Spawn `gsd-plan-checker` → verification loop

Only after planning approved: `/gsd-execute-phase 5`.

**Also available:**
- `/gsd-plan-phase 5 --skip-research` to plan without research
- `/gsd-ui-phase 5` non applica (Phase 5 ha `UI hint: no`)
- review/edit `05-CONTEXT.md` before continuing

</next_steps>
