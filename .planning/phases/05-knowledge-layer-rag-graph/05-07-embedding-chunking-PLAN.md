---
plan_id: 05-07-embedding-chunking
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 3
depends_on: [05-01-sft-knowledge-sdk]
requirements: [KNW-02]
files_modified:
  - packages/sft-knowledge/src/sft_knowledge/embedding/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
  - packages/sft-knowledge/src/sft_knowledge/chunking/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py
  - packages/sft-knowledge/src/sft_knowledge/__init__.py
  - packages/sft-knowledge/tests/test_semantic_chunker.py
  - packages/sft-knowledge/tests/test_bge_m3_embedder.py
autonomous: true
estimated_atomic_commits: 3
must_haves:
  truths:
    - "BgeM3Embedder.encode(texts) returns (dense: list[np.ndarray] shape (N,1024), sparse: list[SparseVector])"
    - "BgeM3Embedder uses FlagEmbedding BGEM3FlagModel primary, fastembed fallback, raises RuntimeError if neither available"
    - "BgeM3Embedder is lazy singleton via @lru_cache (BGE_M3_DEVICE env, default cpu)"
    - "SemanticChunker.chunk(parsed_doc) returns list[Chunk] with text, chunk_idx, heading_path, metadata"
    - "SemanticChunker uses LlamaIndex SemanticSplitterNodeParser(buffer_size=1, breakpoint_percentile_threshold=95)"
    - "SemanticChunker propagates ParsedDoc.frontmatter to each Chunk.metadata (KNW-05 prerequisite)"
  artifacts:
    - path: packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
      provides: BgeM3Embedder wrapper with dense+sparse outputs + Qdrant SparseVector conversion
    - path: packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py
      provides: SemanticChunker wrapping LlamaIndex SemanticSplitter with metadata propagation
  key_links:
    - from: packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py
      to: BgeM3Embedder / HuggingFaceEmbedding
      via: shared model_name "BAAI/bge-m3" for semantic split boundaries
      pattern: "BAAI/bge-m3"
    - from: packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py
      to: qdrant_client.http.models.SparseVector
      via: to_qdrant_sparse() conversion
      pattern: "SparseVector"
---

<objective>
Implement the embedding + chunking layer of the sft-knowledge SDK: `BgeM3Embedder` (FlagEmbedding BGE-M3 wrapper with dense+sparse outputs, FastEmbed fallback, lazy singleton) and `SemanticChunker` (LlamaIndex SemanticSplitterNodeParser wrapper that preserves frontmatter metadata per chunk per D-62).

Purpose: feeds Plan 05-08 QdrantIndexer (chunks + dual vectors) and Plan 05-09 RetrievalPipeline (query embedding). KNW-02 requirement closes here.

Output: two new sub-packages (`embedding/`, `chunking/`) with unit tests (mock embed) + 1 integration test on a real SOP.
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
@packages/sft-assets/src/sft_assets/_loader.py
@packages/sft-tools/src/sft_tools/replay/cmapss.py
@packages/sft-knowledge/src/sft_knowledge/parsers/base.py
</context>

<interfaces>
BgeM3Embedder API (D-62 + RESEARCH §2):

```
class BgeM3Embedder:
    def __init__(self, device: str | None = None, batch_size: int = 12, max_length: int = 8192):
        # device overrides BGE_M3_DEVICE env (default "cpu")
        ...

    def encode(self, texts: list[str], return_dense: bool = True, return_sparse: bool = True) -> EncodeOutput:
        # returns EncodeOutput(dense_vecs: list[np.ndarray], sparse_weights: list[dict[str,float]])
        ...

    def to_qdrant_sparse(self, lexical_weights: dict[str, float]) -> SparseVector:
        # converts BGE-M3 sparse dict to Qdrant SparseVector via tokenizer ID lookup
        # filter UNK tokens (RESEARCH §2 + Open Question 1)
        ...
```

Lazy singleton model load (PATTERNS.md bge_m3.py section + Shared Pattern 8):
```
@lru_cache(maxsize=1)
def _get_model() -> BGEM3FlagModel:
    try:
        from FlagEmbedding import BGEM3FlagModel
        return BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device=os.environ.get("BGE_M3_DEVICE", "cpu"))
    except ImportError:
        try:
            from fastembed import TextEmbedding
            return _FastEmbedAdapter(TextEmbedding("BAAI/bge-m3"))
        except ImportError:
            raise RuntimeError("Neither FlagEmbedding nor fastembed available")
```

SemanticChunker API (D-62):

```
class Chunk(BaseModel):
    model_config = {"frozen": True, "extra": "forbid"}
    text: str
    chunk_idx: int
    heading_path: list[str]
    metadata: dict  # propagated from ParsedDoc.frontmatter + source_uri + sop_id

class SemanticChunker:
    def __init__(self, buffer_size: int = 1, breakpoint_percentile_threshold: int = 95, device: str | None = None):
        ...

    def chunk(self, parsed_doc: ParsedDoc) -> list[Chunk]:
        # 1. Build LlamaIndex Document(text=parsed_doc body, metadata={...})
        # 2. Run SemanticSplitterNodeParser.get_nodes_from_documents([doc])
        # 3. Per TextNode: build Chunk with chunk_idx (enumerate), heading_path (derived from node.start_char_idx via parsed_doc.sections), metadata (frontmatter copy + sop_id + source_uri)
        ...
```

Imports (RESEARCH §4 verified):
- `from llama_index.core.node_parser import SemanticSplitterNodeParser`
- `from llama_index.embeddings.huggingface import HuggingFaceEmbedding`
- `from llama_index.core import Document`

Metadata propagation pitfall (RESEARCH §4 + Risk 7): `excluded_embed_metadata_keys` in Document — don't include keys we want for filter but not embedding contamination. For each chunk produced, every Document.metadata key MUST appear in chunk.metadata.

SparseVector conversion (RESEARCH §2):
```
from qdrant_client.http.models import SparseVector

def to_qdrant_sparse(lexical_weights: dict[str, float]) -> SparseVector:
    # BGE-M3 sparse output: dict[token_str, float]
    # Qdrant expects: SparseVector(indices: list[int], values: list[float])
    # Use model.tokenizer.convert_tokens_to_ids; filter UNK
    ...
```
</interfaces>

<tasks>

<task id="05-07-01" type="auto" tdd="true">
  <name>Task 1: BgeM3Embedder with FlagEmbedding primary + fastembed fallback</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/embedding/__init__.py,
    packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py,
    packages/sft-knowledge/tests/test_bge_m3_embedder.py
  </files>
  <read_first>
    packages/sft-assets/src/sft_assets/_loader.py (lru_cache singleton pattern lines 22-49),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (claudes_discretion bge_m3 lazy singleton, BGE_M3_DEVICE env),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §2 (FlagEmbedding API + fastembed fallback + sparse conversion),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (embedding/bge_m3.py section lines 274-306)
  </read_first>
  <behavior>
    - `_get_model()` returns FlagEmbedding model on first call; uses BGE_M3_DEVICE env (default "cpu")
    - On FlagEmbedding ImportError, falls back to fastembed TextEmbedding (lighter, dense-only)
    - If BOTH unavailable, raises RuntimeError with clear message
    - `_get_model()` is @lru_cache(maxsize=1) — second call returns same object
    - `BgeM3Embedder.encode(texts)` returns dense vecs (np.ndarray (N,1024)) + sparse weights (list[dict[str,float]]); on fastembed fallback, sparse is empty list (documented degraded mode)
    - `to_qdrant_sparse(lexical_weights)` filters UNK tokens (RESEARCH §2 Assumption A2 + Open Q1), returns SparseVector(indices, values) with len(indices) == len(values)
    - test_singleton_identity: two calls to _get_model() return identical object (`is` identity)
    - test_encode_returns_1024d_dense (mock-FlagEmbedding): patch `FlagEmbedding.BGEM3FlagModel` with stub returning dict with `dense_vecs` shape (N,1024) + `lexical_weights` dict; encode([text]) returns expected shape
    - test_fastembed_fallback: monkeypatch FlagEmbedding import to raise ImportError; assert encode still works (using fastembed stub), but sparse_weights is empty
    - test_runtime_error_when_no_backend: monkeypatch BOTH imports to fail; assert RuntimeError raised with descriptive message
    - test_to_qdrant_sparse_filters_unk: build mock tokenizer where some tokens map to unk_token_id; assert returned SparseVector excludes those indices; assert len(indices) == len(values)
  </behavior>
  <action>
    Create `packages/sft-knowledge/src/sft_knowledge/embedding/__init__.py` re-exporting `BgeM3Embedder, EncodeOutput`.

    Create `packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`:
    - `from __future__ import annotations`, `import os`, `from functools import lru_cache`, `from dataclasses import dataclass` (or Pydantic frozen)
    - `import structlog; logger = structlog.get_logger(__name__)`
    - `import numpy as np` (only at module level if always installed — keep top-level imports light if heavy)
    - Internal helper class `_FastEmbedAdapter` wrapping fastembed TextEmbedding to expose `.encode(texts, return_dense, return_sparse) -> dict` shape compatible with FlagEmbedding output (with `sparse_weights = [{} for _ in texts]` since fastembed BGE-M3 is dense-only).
    - `@lru_cache(maxsize=1) def _get_model() -> Any` per PATTERNS.md bge_m3.py section: try FlagEmbedding primary, fastembed fallback, RuntimeError if both fail. Log info on which backend loaded.
    - `class EncodeOutput(BaseModel): model_config = {"frozen": True, "extra": "forbid"}; dense_vecs: list[Any]; sparse_weights: list[dict[str, float]]` (Any avoids np ndarray serialization in Pydantic — alternative: dataclass).
    - `class BgeM3Embedder`:
      - `def __init__(self, device: str | None = None, batch_size: int = 12, max_length: int = 8192) -> None`: if device given, set env (or store on instance); `self._batch_size = batch_size`; `self._max_length = max_length`
      - `def encode(self, texts: list[str], return_dense: bool = True, return_sparse: bool = True) -> EncodeOutput`: call `_get_model()` and dispatch on type — FlagEmbedding has `.encode(texts, batch_size, max_length, return_dense, return_sparse, return_colbert_vecs=False)`; FastEmbed adapter exposes same shape.
      - `def to_qdrant_sparse(self, lexical_weights: dict[str, float]) -> SparseVector`: import SparseVector inside method body (lazy import of qdrant_client.http.models); use model tokenizer (`model.tokenizer.convert_tokens_to_ids`) to map tokens; filter `unk_token_id`; ensure len(indices) == len(values).
      - All methods raise on backend-specific errors with descriptive context (never silent).

    Create `packages/sft-knowledge/tests/test_bge_m3_embedder.py`:
    - Implement 4 tests from `<behavior>` using `monkeypatch` + `MagicMock` for FlagEmbedding + fastembed imports.
    - Mark tests as unit (no marker — default fast path). Avoid loading the real BGE-M3 model (568MB) in unit tests.
    - Add `@pytest.mark.gpu` integration test `test_real_bge_m3_loads` (skipped by default in CI): loads real FlagEmbedding model, encodes "hello world", asserts dense shape (1,1024). This is the ONLY test that requires the real model.

    Update `packages/sft-knowledge/src/sft_knowledge/__init__.py` to re-export `BgeM3Embedder, EncodeOutput`.

    Commit: `feat(05-07-embedding-chunking): add BgeM3Embedder with FlagEmbedding primary + fastembed fallback`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class BgeM3Embedder' packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`
    - `grep -q '@lru_cache(maxsize=1)' packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`
    - `grep -q 'BGE_M3_DEVICE' packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`
    - `grep -q 'from fastembed' packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py` (fallback path)
    - `grep -q 'RuntimeError' packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py`
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_bge_m3 -v"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_bge_m3 -v"</automated>
  </verify>
  <done>BgeM3Embedder + 4 unit tests committed; singleton + fallback + UNK filtering verified.</done>
</task>

<task id="05-07-02" type="auto" tdd="true">
  <name>Task 2: SemanticChunker with LlamaIndex SemanticSplitterNodeParser + frontmatter propagation</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/chunking/__init__.py,
    packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py,
    packages/sft-knowledge/tests/test_semantic_chunker.py
  </files>
  <read_first>
    packages/sft-knowledge/src/sft_knowledge/parsers/base.py (ParsedDoc + ParsedSection schemas from Plan 05-01),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-62 SemanticSplitter config lines 138-160),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §4 (LlamaIndex API + metadata pitfall + heading path reconstruction + Risk 7),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (chunking/semantic.py section lines 241-271)
  </read_first>
  <behavior>
    - `_get_embed_model()` is `@lru_cache(maxsize=1)` returning HuggingFaceEmbedding("BAAI/bge-m3", device=BGE_M3_DEVICE env, embed_batch_size=10)
    - `SemanticChunker.__init__(buffer_size=1, breakpoint_percentile_threshold=95)` — both default to D-62 values
    - `chunk(parsed_doc: ParsedDoc) -> list[Chunk]`:
      1. Build full body text by joining `[s.text for s in parsed_doc.sections]` with double newline.
      2. Build `Document(text=body, metadata={"source_uri": ..., "lang": ..., "acl_level": ..., "version": ..., "asset_family": ..., "sop_id": ...}, excluded_embed_metadata_keys=["source_uri", "acl_level", "sop_id"])`.
      3. `nodes = splitter.get_nodes_from_documents([doc])`.
      4. For each node (enumerate): build `Chunk(text=node.text, chunk_idx=i, heading_path=..., metadata=node.metadata)`.
      5. heading_path derived from char offset: build heading offset map from parsed_doc.sections (each section's heading_path + cumulative offset), then for each node use `node.start_char_idx` to find heading_path of the section containing it (bisect right).
    - test_chunker_returns_text_nodes_with_metadata (mock embed): patch HuggingFaceEmbedding to a fake returning predictable embeddings; ParsedDoc with 5 sections → SemanticChunker returns ≥1 Chunk; each Chunk.metadata has source_uri + lang + acl_level + sop_id keys (KNW-05 prerequisite).
    - test_metadata_propagation_to_chunks: build ParsedDoc with specific metadata; assert ALL chunks have metadata["source_uri"] == expected (Risk 7 mitigation).
    - test_heading_path_recovered: ParsedDoc with 3 sections (H1 → H2 → H3); chunks span sections; first chunk has heading_path = section 0 heading_path; last chunk has heading_path = section -1.
    - test_chunk_frozen: assert mutating Chunk raises ValidationError.
    - test_chunk_idx_sequential: chunks have chunk_idx 0, 1, 2, ... contiguous.
  </behavior>
  <action>
    Create `packages/sft-knowledge/src/sft_knowledge/chunking/__init__.py` re-exporting `SemanticChunker, Chunk`.

    Create `packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`:
    - `from __future__ import annotations`, `import os`, `from bisect import bisect_right`, `from functools import lru_cache`, `from pydantic import BaseModel`
    - `import structlog; logger = structlog.get_logger(__name__)`
    - `from sft_knowledge.parsers.base import ParsedDoc`
    - `class Chunk(BaseModel): model_config = {"frozen": True, "extra": "forbid"}; text: str; chunk_idx: int; heading_path: list[str]; metadata: dict`
    - `@lru_cache(maxsize=1) def _get_embed_model():` — inside try: `from llama_index.embeddings.huggingface import HuggingFaceEmbedding; return HuggingFaceEmbedding(model_name="BAAI/bge-m3", device=os.environ.get("BGE_M3_DEVICE", "cpu"), embed_batch_size=10)`; on ImportError raise RuntimeError "llama-index-embeddings-huggingface not installed".
    - `class SemanticChunker`:
      - `def __init__(self, buffer_size: int = 1, breakpoint_percentile_threshold: int = 95) -> None`: store params; lazy-import splitter inside chunk() to keep top-level lightweight.
      - `def chunk(self, parsed_doc: ParsedDoc) -> list[Chunk]`:
        1. lazy-import `from llama_index.core.node_parser import SemanticSplitterNodeParser; from llama_index.core import Document`
        2. Build cumulative offset map of (offset, heading_path) tuples — start at offset 0 with parsed_doc.sections[0].heading_path; for each subsequent section build cumulative offset.
        3. Build full body = "\n\n".join(s.text for s in parsed_doc.sections).
        4. metadata = {"source_uri": parsed_doc.source_uri, "lang": parsed_doc.lang, "acl_level": parsed_doc.frontmatter.get("acl_level", "internal"), "version": parsed_doc.version, "asset_family": str(parsed_doc.frontmatter.get("asset_family", "")), "sop_id": str(parsed_doc.frontmatter.get("id", ""))}.
        5. doc = Document(text=body, metadata=metadata, excluded_embed_metadata_keys=["source_uri", "acl_level", "sop_id"]).
        6. splitter = SemanticSplitterNodeParser(buffer_size=self.buffer_size, breakpoint_percentile_threshold=self.breakpoint_percentile_threshold, embed_model=_get_embed_model()).
        7. nodes = splitter.get_nodes_from_documents([doc]).
        8. Build chunks: for i, node in enumerate(nodes), find heading_path via bisect_right(offsets, node.start_char_idx) → corresponding section heading_path; build Chunk(text=node.text, chunk_idx=i, heading_path=..., metadata={**node.metadata}).
        9. Return list.

    Update `packages/sft-knowledge/src/sft_knowledge/__init__.py` to re-export `SemanticChunker, Chunk`.

    Update `packages/sft-knowledge/tests/test_semantic_chunker.py` (remove Plan 05-01 stub skip marker):
    - Implement 5 unit tests from `<behavior>` using monkeypatch + MagicMock for both `_get_embed_model()` and `SemanticSplitterNodeParser`. The mock splitter returns a deterministic list of TextNode-like objects.
    - Use `unittest.mock.MagicMock` to fake TextNode with `.text`, `.metadata`, `.start_char_idx` attributes.
    - Do NOT load real BGE-M3 in unit tests (would be too slow + heavy). The integration test that uses real BGE-M3 is in Plan 05-08.

    Commit: `feat(05-07-embedding-chunking): add SemanticChunker with LlamaIndex SemanticSplitter + frontmatter propagation`.
  </action>
  <acceptance_criteria>
    - `grep -q 'class SemanticChunker' packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`
    - `grep -q 'buffer_size: int = 1' packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`
    - `grep -q 'breakpoint_percentile_threshold' packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`
    - `grep -q 'BAAI/bge-m3' packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`
    - `grep -q 'excluded_embed_metadata_keys' packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`
    - `grep -q 'class Chunk(BaseModel):' packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py`
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_semantic_chunker -v"` exits 0 (5 unit tests pass)
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_semantic_chunker -v"</automated>
  </verify>
  <done>SemanticChunker + 5 unit tests committed; metadata propagation + heading_path recovery + frozen Chunk verified.</done>
</task>

<task id="05-07-03" type="auto" tdd="true">
  <name>Task 3: Integration test on 1 real SOP — end-to-end parse → chunk → embed</name>
  <files>
    packages/sft-knowledge/tests/test_semantic_chunker.py
  </files>
  <read_first>
    packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py (just from Plan 05-01),
    packages/sft-knowledge/src/sft_knowledge/chunking/semantic.py (just from Task 2),
    packages/sft-knowledge/src/sft_knowledge/embedding/bge_m3.py (just from Task 1),
    simulators/synthetic-corpus/it/loom/ (pick smallest reviewed SOP file for fast test)
  </read_first>
  <behavior>
    - Integration test `test_real_sop_end_to_end_chunk_and_embed` (marked `@pytest.mark.integration` AND `@pytest.mark.gpu` since real BGE-M3 is heavy):
      1. Pick a small reviewed SOP file (~500-2000 chars body).
      2. parsed = await MarkdownParser().parse(sop_path).
      3. chunker = SemanticChunker(); chunks = chunker.chunk(parsed).
      4. Assert len(chunks) >= 1.
      5. Assert each chunk has metadata["source_uri"] == parsed.source_uri.
      6. Assert each chunk has metadata["acl_level"] in {"public", "internal", "restricted"}.
      7. embedder = BgeM3Embedder(); output = embedder.encode([chunks[0].text]).
      8. Assert output.dense_vecs[0].shape == (1024,) (BGE-M3 dense dim per D-61 + RESEARCH §2).
      9. Assert isinstance(output.sparse_weights[0], dict) and len(output.sparse_weights[0]) > 0 (BGE-M3 sparse lexical weights non-empty).
    - This is the FIRST test that touches real BGE-M3 model. Acceptable to run only locally or on GPU CI runner; mark `@pytest.mark.gpu` so it's skipped on CPU CI per VALIDATION.md sampling rate.
  </behavior>
  <action>
    Add `test_real_sop_end_to_end_chunk_and_embed` to `packages/sft-knowledge/tests/test_semantic_chunker.py`:
    - Decorate with both `@pytest.mark.integration` and `@pytest.mark.gpu`.
    - Use `pathlib.Path` to locate a known small SOP file under `simulators/synthetic-corpus/`. Choose deterministically: sort glob and take first reviewed file with body length < 2000 chars (or hardcode a specific filename if the corpus has a known small file).
    - Implement steps 1-9 from `<behavior>`.
    - On test failure due to real-model load timeout: document in test docstring that this test is gated on `@pytest.mark.gpu` and is acceptable to be skipped on CPU-only CI. Plan 05-08 covers the integration testing on testcontainer Qdrant without requiring full BGE-M3 (uses mock embeddings).

    Verify locally: `nx run sft-knowledge:test --args="-m 'integration and gpu' -k test_real_sop -v"` exits 0 IF GPU available; else `--args="-m 'gpu' -v"` reports the test SKIPPED.

    Commit: `test(05-07-embedding-chunking): add end-to-end integration test on real SOP (gpu-gated)`.
  </action>
  <acceptance_criteria>
    - `grep -q 'def test_real_sop_end_to_end_chunk_and_embed' packages/sft-knowledge/tests/test_semantic_chunker.py`
    - `grep -B1 'test_real_sop_end_to_end_chunk_and_embed' packages/sft-knowledge/tests/test_semantic_chunker.py | grep -q '@pytest.mark.gpu'`
    - Either: `nx run sft-knowledge:test --args="-m 'integration and gpu' -k test_real_sop -v"` exits 0 (test passes when run with real model)
    - OR: `nx run sft-knowledge:test --args="-v -k test_real_sop"` reports SKIPPED if no `gpu` marker mode selected (acceptable for CPU CI)
  </acceptance_criteria>
  <verify>
    <automated>grep -q '@pytest.mark.gpu' packages/sft-knowledge/tests/test_semantic_chunker.py &amp;&amp; nx run sft-knowledge:test --args="-v -k test_real_sop --collect-only" 2&gt;&amp;1 | grep -q 'test_real_sop_end_to_end_chunk_and_embed'</automated>
  </verify>
  <done>End-to-end integration test exists with @pytest.mark.gpu gate; collectable and either green on GPU runners or properly skipped on CPU CI.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| BgeM3Embedder → HuggingFace model download | First model load fetches weights from Hugging Face Hub; subsequent loads use cached weights |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-07-01 | Tampering | model weights origin | accept | HuggingFace BAAI/bge-m3 is official BAAI repo (MIT license); attack vector requires upstream HF compromise; Phase 11 considers offline mirror |
| T-05-07-02 | Information Disclosure | embedded text in vectors | mitigate | Phase 5 corpus is synthetic (no PII per A-013); D-67 ACL gate prevents indexing of non-reviewed SOPs |
| T-05-07-03 | Tampering | excluded_embed_metadata_keys | mitigate | source_uri, acl_level, sop_id excluded from embedding contamination (text-only embedding); ACL filter applied at retrieval (Plan 05-09), not at embedding |
| T-05-07-04 | Denial of Service | model OOM on large doc | mitigate | max_length=8192 caps single doc tokens; SemanticChunker splits before embed; batch_size=12 default per RESEARCH §2 |
| T-05-07-SC | Tampering | npm/pip install | mitigate | FlagEmbedding + fastembed + llama-index-core + llama-index-embeddings-huggingface already declared in Plan 05-01 pyproject; all PyPI Approved per 05-RESEARCH legitimacy audit |
</threat_model>

<verification>
- `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -v"` exits 0 (all unit tests including Task 1 + Task 2 pass)
- `nx run sft-knowledge:test --args="-v -k test_real_sop --collect-only"` discovers integration test (collectable)
- BgeM3Embedder is lazy singleton (singleton identity test passes)
- SemanticChunker preserves frontmatter in every chunk metadata (KNW-05 prerequisite verified)
- Dense vec shape (1024,) confirmed (BGE-M3 dim matches D-61)
</verification>

<success_criteria>
- 3 atomic commits: `feat(05-07-embedding-chunking):` × 2 + `test(05-07-embedding-chunking):` × 1
- KNW-02 requirement closed
- Plan 05-08 QdrantIndexer can call `BgeM3Embedder.encode()` + `to_qdrant_sparse()`
- Plan 05-09 RetrievalPipeline can call same embedder for query embedding
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-07-embedding-chunking-SUMMARY.md` when done with: embedder backends (FlagEmbedding + fastembed fallback), chunker config (buffer_size=1, percentile=95), unit test counts, integration test gpu-gating note.
</output>
