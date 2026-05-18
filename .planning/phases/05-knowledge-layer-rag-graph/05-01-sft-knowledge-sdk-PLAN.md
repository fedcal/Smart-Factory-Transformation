---
plan_id: 05-01-sft-knowledge-sdk
phase: 5
phase_name: Knowledge Layer (RAG + Graph)
wave: 1
depends_on: []
requirements: [KNW-04, KNW-05]
files_modified:
  - packages/sft-knowledge/pyproject.toml
  - packages/sft-knowledge/project.json
  - packages/sft-knowledge/src/sft_knowledge/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/parsers/__init__.py
  - packages/sft-knowledge/src/sft_knowledge/parsers/base.py
  - packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py
  - packages/sft-knowledge/src/sft_knowledge/models.py
  - packages/sft-knowledge/tests/conftest.py
  - packages/sft-knowledge/tests/test_markdown_parser.py
  - packages/sft-knowledge/tests/test_semantic_chunker.py
  - packages/sft-knowledge/tests/test_qdrant_indexer.py
  - packages/sft-knowledge/tests/test_neo4j_builder.py
  - packages/sft-knowledge/tests/test_retrieval_pipeline.py
  - packages/sft-knowledge/tests/test_acl_enforcement.py
  - packages/sft-knowledge/tests/test_crosslingual_e2e.py
autonomous: true
estimated_atomic_commits: 4
must_haves:
  truths:
    - "sft-knowledge package is importable via `from sft_knowledge import MarkdownParser, DocumentParser, ParsedDoc`"
    - "MarkdownParser parses all 41 SOPs without raising"
    - "DocumentParser ABC enforces async parse() + supported_extensions()"
    - "All Wave 0 test files exist with skipped/xfail markers so subsequent waves can fill them in"
  artifacts:
    - path: packages/sft-knowledge/pyproject.toml
      provides: package manifest with locked deps
    - path: packages/sft-knowledge/src/sft_knowledge/parsers/base.py
      provides: DocumentParser ABC + ParsedDoc/ParsedSection frozen models
    - path: packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py
      provides: MarkdownParser implementation
    - path: packages/sft-knowledge/src/sft_knowledge/models.py
      provides: GraphNode model + re-export RagCitation from sft-agents
  key_links:
    - from: packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py
      to: simulators/synthetic-corpus/
      via: pathlib rglob + frontmatter.load
      pattern: "frontmatter\\.load"
---

<objective>
Scaffold the `sft-knowledge` Python package: pyproject + Nx project + DocumentParser ABC + MarkdownParser implementation + Pydantic models (ParsedDoc, ParsedSection, GraphNode; reuse RagCitation from sft-agents) + Wave 0 test file stubs per 05-VALIDATION.md.

Purpose: lay the foundation contracts (parser ABC, frozen models, test scaffolding) that Waves 2/3/4 build on. No external infra dependencies (Qdrant/Neo4j) — pure Python.

Output: an importable, lintable, testable `sft-knowledge` package with MarkdownParser working on all 41 SOPs and 8 test stubs in place.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md
@.planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md
@.planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md
@.planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md
@packages/sft-tools/pyproject.toml
@packages/sft-tools/project.json
@packages/sft-tools/src/sft_tools/__init__.py
@packages/sft-agents/src/sft_agents/sdk/memory.py
@packages/sft-agents/src/sft_agents/models/evidence.py
@scripts/validate-corpus-frontmatter.py
</context>

<interfaces>
<!-- Existing exports the executor must import, not redefine. -->

From packages/sft-agents/src/sft_agents/models/evidence.py:
- `class RagCitation(BaseModel)` with `model_config = {"frozen": True, "extra": "forbid"}` and fields `source_uri, snippet, score, retrieved_at`. Phase 5 MUST `from sft_agents.models.evidence import RagCitation` — DO NOT redefine.

From packages/sft-agents/src/sft_agents/sdk/memory.py:
- `class Memory(ABC)` with `async def query(...)` and `async def store(...)`. Phase 5 QdrantLongTermMemory (Plan 05-09) implements this.

Conventions enforced (per 05-PATTERNS.md Shared Patterns 1-10):
- Pydantic v2 `model_config = {"frozen": True, "extra": "forbid"}` on every model
- `datetime.now(timezone.utc)` only; never `datetime.now()`
- `yaml.safe_load` only; never `yaml.load`
- `structlog.get_logger(__name__)` at module top; `structlog.configure(...)` ONLY in __main__.py
- pytest markers: `integration` (requires testcontainers), `gpu` (requires CUDA)
</interfaces>

<tasks>

<task id="05-01-01" type="auto">
  <name>Task 1: Scaffold sft-knowledge package (pyproject + project.json + __init__)</name>
  <files>
    packages/sft-knowledge/pyproject.toml,
    packages/sft-knowledge/project.json,
    packages/sft-knowledge/src/sft_knowledge/__init__.py,
    packages/sft-knowledge/src/sft_knowledge/parsers/__init__.py
  </files>
  <read_first>
    packages/sft-tools/pyproject.toml,
    packages/sft-tools/project.json,
    packages/sft-tools/src/sft_tools/__init__.py,
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (sections "pyproject.toml" and "project.json")
  </read_first>
  <action>
    Create `packages/sft-knowledge/pyproject.toml` mirroring `packages/sft-tools/pyproject.toml`. Set `name = "sft-knowledge"`, `version = "0.1.0"`, `requires-python = ">=3.12,<3.13"`, `description = "Knowledge layer: parsers, chunking, embedding, stores, retrieval, tools, memory (Phase 5)"`.

    Dependencies block: `pydantic>=2.7`, `langchain-core>=0.3`, `python-frontmatter>=1.1`, `structlog>=24.4`, `qdrant-client[fastembed]>=1.16`, `FlagEmbedding>=1.3`, `llama-index-core>=0.11,<0.15`, `llama-index-embeddings-huggingface>=0.3`, `neo4j>=5.24,<7` (the `<7` upper bound is mandatory per RESEARCH §5 Risk 1 to prevent v6 breaking changes).

    `[tool.hatch.build.targets.wheel] packages = ["src/sft_knowledge"]`. `[tool.uv.sources]` block entries: `sft-agents = { workspace = true }`, `sft-domain = { workspace = true }`, `sft-assets = { workspace = true }`.

    `[tool.pytest.ini_options]` block: `asyncio_mode = "auto"`, `testpaths = ["tests"]`, `markers = ["integration: requires docker / testcontainers", "gpu: requires CUDA GPU"]`.

    Create `packages/sft-knowledge/project.json` mirroring `packages/sft-tools/project.json` with `"name": "sft-knowledge"`, `"projectType": "library"`, `"sourceRoot": "packages/sft-knowledge/src"`, targets `test` (runs `uv run pytest packages/sft-knowledge/tests -x -v`) and `lint` (runs `uv run ruff check src`). `implicitDependencies` list MUST be `["sft-domain", "sft-assets", "sft-agents"]`.

    Create `packages/sft-knowledge/src/sft_knowledge/__init__.py` with module docstring listing public exports. Re-export `DocumentParser, MarkdownParser, ParsedDoc, ParsedSection` from `.parsers` and `GraphNode` from `.models`. Phase 5 Wave 3/4 will add `SemanticChunker, BgeM3Embedder, QdrantIndexer, Neo4jGraphBuilder, RetrievalPipeline, BgeReranker, RagSearchTool, TraverseGraphTool, QdrantLongTermMemory`.

    Create `packages/sft-knowledge/src/sft_knowledge/parsers/__init__.py` re-exporting `DocumentParser, MarkdownParser, ParsedDoc, ParsedSection` from `.base` and `.markdown`.

    Run `uv lock` from workspace root to refresh lockfile (per Phase 4 convention).

    Commit: `feat(05-01-sft-knowledge-sdk): scaffold sft-knowledge package with pyproject + Nx wiring`.
  </action>
  <acceptance_criteria>
    - `packages/sft-knowledge/pyproject.toml` exists and contains literal string `name = "sft-knowledge"`
    - `packages/sft-knowledge/pyproject.toml` contains literal string `"neo4j>=5.24,<7"` (upper bound enforced)
    - `packages/sft-knowledge/project.json` contains literal `"implicitDependencies": ["sft-domain", "sft-assets", "sft-agents"]`
    - `packages/sft-knowledge/src/sft_knowledge/__init__.py` exists and defines `__all__` list
    - `nx run sft-knowledge:lint` exits 0
    - `uv run python -c "import sft_knowledge"` from `packages/sft-knowledge/` exits 0
  </acceptance_criteria>
  <verify>
    <automated>grep -q 'name = "sft-knowledge"' packages/sft-knowledge/pyproject.toml &amp;&amp; grep -q '"neo4j&gt;=5.24,&lt;7"' packages/sft-knowledge/pyproject.toml &amp;&amp; nx run sft-knowledge:lint</automated>
  </verify>
  <done>Package scaffold exists, `nx run sft-knowledge:lint` exits 0, package importable.</done>
</task>

<task id="05-01-02" type="auto" tdd="true">
  <name>Task 2: Implement DocumentParser ABC + Pydantic models (ParsedDoc, ParsedSection, GraphNode)</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/parsers/base.py,
    packages/sft-knowledge/src/sft_knowledge/models.py
  </files>
  <read_first>
    packages/sft-agents/src/sft_agents/sdk/memory.py,
    packages/sft-agents/src/sft_agents/models/evidence.py (RagCitation lines ~60-79; tz-aware validator lines ~17-24),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-67 ParsedDoc schema lines 376-398),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (sections "parsers/base.py" and "models.py")
  </read_first>
  <behavior>
    - ParsedSection(BaseModel) frozen+forbid: `heading_path: list[str]`, `text: str`
    - ParsedDoc(BaseModel) frozen+forbid: `source_uri: str`, `frontmatter: dict`, `sections: list[ParsedSection]`, `version: str`, `lang: Literal["it","en"]`
    - GraphNode(BaseModel) frozen+forbid: `label: Literal["Machine","Part","FailureMode","SOP"]`, `node_id: str`, `properties: dict[str, Any]` default `{}`
    - DocumentParser ABC: `async def parse(self, path: Path) -> ParsedDoc` (abstract) + `def supported_extensions(self) -> set[str]` (abstract)
    - models.py re-exports `RagCitation` from `sft_agents.models.evidence` (do NOT redefine)
    - Instantiating ParsedDoc with `extra` field MUST raise ValidationError (extra=forbid enforced)
    - Mutating a ParsedDoc field MUST raise ValidationError (frozen enforced)
  </behavior>
  <action>
    In `packages/sft-knowledge/src/sft_knowledge/parsers/base.py`:
    - `from __future__ import annotations`
    - `from abc import ABC, abstractmethod`
    - `from pathlib import Path`
    - `from typing import Literal`
    - `from pydantic import BaseModel`
    - Define `ParsedSection(BaseModel)` with `model_config = {"frozen": True, "extra": "forbid"}`, fields `heading_path: list[str]`, `text: str`.
    - Define `ParsedDoc(BaseModel)` with same `model_config`, fields `source_uri: str`, `frontmatter: dict`, `sections: list[ParsedSection]`, `version: str`, `lang: Literal["it", "en"]`.
    - Define `class DocumentParser(ABC)` with `@abstractmethod async def parse(self, path: Path) -> ParsedDoc: ...` and `@abstractmethod def supported_extensions(self) -> set[str]: ...`.

    In `packages/sft-knowledge/src/sft_knowledge/models.py`:
    - `from __future__ import annotations`
    - `from typing import Any, Literal`
    - `from pydantic import BaseModel`
    - `from sft_agents.models.evidence import RagCitation` (re-export; do NOT redefine per D-59 + PATTERNS.md models.py)
    - Define `class GraphNode(BaseModel)` frozen+forbid with `label: Literal["Machine", "Part", "FailureMode", "SOP"]`, `node_id: str`, `properties: dict[str, Any] = {}`.
    - `__all__ = ["RagCitation", "GraphNode"]`.

    No fenced code blocks in this action — implementation excerpts above are reference shape only; the executor uses the analog files + 05-PATTERNS.md.

    Write tests in `packages/sft-knowledge/tests/test_models.py` (NEW small unit file): test that ParsedDoc frozen rejects mutation, extra=forbid rejects unknown field, GraphNode label Literal whitelist rejects invalid label, RagCitation re-import works.

    Commit: `feat(05-01-sft-knowledge-sdk): add DocumentParser ABC + ParsedDoc/ParsedSection/GraphNode frozen models`.
  </action>
  <acceptance_criteria>
    - `grep -q "class DocumentParser(ABC):" packages/sft-knowledge/src/sft_knowledge/parsers/base.py`
    - `grep -q '@abstractmethod' packages/sft-knowledge/src/sft_knowledge/parsers/base.py`
    - `grep -q 'model_config = {"frozen": True, "extra": "forbid"}' packages/sft-knowledge/src/sft_knowledge/parsers/base.py`
    - `grep -q "from sft_agents.models.evidence import RagCitation" packages/sft-knowledge/src/sft_knowledge/models.py`
    - `grep -q "class GraphNode(BaseModel):" packages/sft-knowledge/src/sft_knowledge/models.py`
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_models"` exits 0
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_models"</automated>
  </verify>
  <done>ABC + models defined with frozen+forbid enforced; unit tests exit 0; RagCitation re-exported (not redefined).</done>
</task>

<task id="05-01-03" type="auto" tdd="true">
  <name>Task 3: Implement MarkdownParser with frontmatter + heading_path + status/ACL gates</name>
  <files>
    packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py,
    packages/sft-knowledge/tests/test_markdown_parser.py
  </files>
  <read_first>
    scripts/validate-corpus-frontmatter.py (frontmatter.load pattern lines 76-80; heading regex lines 50-52; status filter),
    .planning/phases/05-knowledge-layer-rag-graph/05-CONTEXT.md (D-67 MarkdownParser spec lines 400-411; D-25 status:reviewed gate; D-72 acl_level default fallback "internal"),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (parsers/markdown.py section),
    .planning/phases/05-knowledge-layer-rag-graph/05-RESEARCH.md §10 (python-frontmatter API + heading regex)
  </read_first>
  <behavior>
    - MarkdownParser implements DocumentParser ABC
    - supported_extensions() returns {".md"}
    - parse(path) returns ParsedDoc if status == "reviewed", returns None otherwise (caller handles None) — log via structlog "sop_skipped_non_reviewed" with path + status
    - If acl_level missing in frontmatter → log WARN "sop_missing_acl_level" + default to "internal" (NEVER "restricted" per D-67)
    - heading_path accumulator: regex `^(#{1,6})\s+(.+?)(?:\s+#+)?$` MULTILINE; track current path; reset deeper levels when higher-level heading appears
    - Each section text = body slice between heading offsets (exclusive of heading line itself)
    - ParsedDoc.frontmatter includes all original keys + injected `acl_level` (after default fallback)
    - test_parse_all_41_sops: iterates simulators/synthetic-corpus/{it,en}/**/*.md, asserts parser returns ParsedDoc or None (no exception); ≥40 of 41 must parse successfully (the 1 tolerance covers any non-reviewed). Note: after Plan 05-02 migration adds acl_level, all 41 parse successfully.
    - test_extracts_heading_path: synthetic MD with H1/H2/H3 → assert sections list contains ["H1 title", "H2 title", "H3 title"] heading_path entries
    - test_status_draft_returns_none: MD with status: draft → parse returns None
    - test_missing_acl_level_defaults_internal: MD without acl_level → ParsedDoc.frontmatter["acl_level"] == "internal"
  </behavior>
  <action>
    In `packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py`:
    - `from __future__ import annotations`, `import re`, `from pathlib import Path`, `import frontmatter`, `import structlog`
    - `from sft_knowledge.parsers.base import DocumentParser, ParsedDoc, ParsedSection`
    - `logger = structlog.get_logger(__name__)`
    - Module-level constant `HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$", re.MULTILINE)`
    - Class `MarkdownParser(DocumentParser)`:
      - `def supported_extensions(self) -> set[str]: return {".md"}`
      - `async def parse(self, path: Path) -> ParsedDoc | None`:
        1. `post = frontmatter.load(str(path))` — python-frontmatter uses yaml.safe_load internally (RESEARCH §10), no manual yaml call required.
        2. Status gate: if `post.metadata.get("status") != "reviewed"`: log info "sop_skipped_non_reviewed", return None.
        3. ACL default: if `"acl_level" not in post.metadata`: log warning "sop_missing_acl_level"; build NEW dict `metadata = {**post.metadata, "acl_level": "internal"}` (immutable update per coding-style.md).
        4. Required fields check: ensure `id`, `title`, `version`, `lang` present; raise `ValueError` with file path if missing.
        5. Extract heading state machine via `HEADING_RE.finditer(post.content)`; build `list[tuple[int_offset, list[str]_path]]`.
        6. Build `list[ParsedSection]`: for each heading offset, section text = `post.content[heading_end:next_heading_start]` stripped. Skip empty sections.
        7. Build source_uri as `f"corpus://{path.relative_to(workspace_root).as_posix()}"` — derive workspace_root by walking up to find `pyproject.toml` at root (use `Path(__file__).resolve().parents[N]` pattern; document the chosen N).
        8. Return `ParsedDoc(source_uri=..., frontmatter=metadata, sections=sections, version=str(metadata["version"]), lang=metadata["lang"])`.
      - All errors are explicit (raise with descriptive message); never silently swallow.

    In `packages/sft-knowledge/tests/test_markdown_parser.py`:
    - Use real fixtures (NO mocks for I/O) — point at `simulators/synthetic-corpus/`.
    - `test_parse_all_41_sops` (async): collect all *.md under corpus, assert each `await MarkdownParser().parse(path)` returns ParsedDoc OR None (must NOT raise).
    - `test_extracts_heading_path` (async): pass tmp_path-created MD with frontmatter + ## H2 + ### H3; assert one section has `heading_path == ["H2 title", "H3 title"]` (or similar).
    - `test_status_draft_returns_none` (async): tmp MD with `status: draft`; assert parse returns None.
    - `test_missing_acl_level_defaults_internal` (async): tmp MD without `acl_level`; assert returned ParsedDoc.frontmatter["acl_level"] == "internal".
    - `test_required_field_missing_raises` (async): MD without `id`; assert ValueError raised.

    Commit: `feat(05-01-sft-knowledge-sdk): implement MarkdownParser with status/ACL gates + heading_path extraction`.
  </action>
  <acceptance_criteria>
    - `grep -q "class MarkdownParser(DocumentParser):" packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py`
    - `grep -q 'frontmatter.load' packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py`
    - `grep -q '"sop_missing_acl_level"' packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py`
    - `grep -q '"sop_skipped_non_reviewed"' packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py`
    - `nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_markdown"` exits 0
    - `test_parse_all_41_sops` passes (handles full 41-SOP corpus without exception)
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-m 'not integration and not gpu' -k test_markdown"</automated>
  </verify>
  <done>MarkdownParser parses all 41 SOPs; status/ACL gates work; unit tests exit 0.</done>
</task>

<task id="05-01-04" type="auto">
  <name>Task 4: Wave 0 conftest + 7 test stubs (skipped/xfail) for downstream waves</name>
  <files>
    packages/sft-knowledge/tests/conftest.py,
    packages/sft-knowledge/tests/test_semantic_chunker.py,
    packages/sft-knowledge/tests/test_qdrant_indexer.py,
    packages/sft-knowledge/tests/test_neo4j_builder.py,
    packages/sft-knowledge/tests/test_retrieval_pipeline.py,
    packages/sft-knowledge/tests/test_acl_enforcement.py,
    packages/sft-knowledge/tests/test_crosslingual_e2e.py
  </files>
  <read_first>
    packages/sft-agents/tests/conftest.py (marker registration lines 24-35; mock pool fixture lines 55-91),
    .planning/phases/05-knowledge-layer-rag-graph/05-VALIDATION.md (Wave 0 Requirements section),
    .planning/phases/05-knowledge-layer-rag-graph/05-PATTERNS.md (conftest.py section + testcontainers fixtures)
  </read_first>
  <action>
    Create `packages/sft-knowledge/tests/conftest.py`:
    - `import pytest`
    - `def pytest_configure(config: pytest.Config) -> None:` registers markers `integration` and `gpu` per 05-PATTERNS.md Shared Pattern 10.
    - Define stub fixtures `qdrant_client` (session scope, async) and `neo4j_driver` (session scope, async) using `testcontainers.qdrant.QdrantContainer("qdrant/qdrant:v1.16.1")` and `testcontainers.neo4j.Neo4jContainer("neo4j:5.24-community")`. Mark BOTH fixtures with `@pytest.fixture(scope="session")`. These fixtures will be CONSUMED by integration tests in Plans 05-04, 05-05, 05-08, 05-09.
    - Add `bge_m3_embedder` fixture (session scope) — lazy: imports `BgeM3Embedder` from `sft_knowledge.embedding.bge_m3` inside fixture body. If import fails (module not yet created by Plan 05-07), `pytest.skip("BgeM3Embedder not yet implemented (Plan 05-07)")`.

    Create 6 test file stubs that import from yet-to-be-created modules but defer execution via `pytestmark = pytest.mark.skip(reason="Wave N stub — implemented in Plan 05-XX")`:
    - `test_semantic_chunker.py` — `pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-07")`. Include placeholder test functions `def test_semantic_chunker_returns_text_nodes_with_metadata(): ...` and `def test_metadata_propagation_to_chunks(): ...` with `pass` body.
    - `test_qdrant_indexer.py` — `pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-04 + 05-08")`. Placeholders `test_collection_bootstrap_idempotent` (KNW-01) and `test_provenance_fields_complete` (KNW-05).
    - `test_neo4j_builder.py` — `pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-05 + 05-08")`. Placeholders `test_graph_ci_validator` (KNW-08 SC#4), `test_merge_sop_idempotent`.
    - `test_retrieval_pipeline.py` — `pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-09")`. Placeholder `test_hybrid_retrieval_returns_ranked` (KNW-09).
    - `test_acl_enforcement.py` — `pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-09")`. Placeholder `test_operator_cannot_see_restricted` (KNW-06 SC#2).
    - `test_crosslingual_e2e.py` — `pytestmark = pytest.mark.skip(reason="Implemented in Plan 05-09")`. Placeholder `test_it_query_returns_en_sop` (SC#1).

    Each stub file MUST contain a header comment with the requirement ID it will cover (e.g., `# Covers KNW-09 per 05-VALIDATION.md`) so the executor in later plans can navigate from failing test → covering requirement directly.

    Run `nx run sft-knowledge:test --args="-v"` and verify: all real tests pass (test_models, test_markdown_parser), all stubs reported as SKIPPED.

    Commit: `test(05-01-sft-knowledge-sdk): add Wave 0 conftest + 6 skipped test stubs per VALIDATION.md`.
  </action>
  <acceptance_criteria>
    - All 7 test files exist: `ls packages/sft-knowledge/tests/test_{semantic_chunker,qdrant_indexer,neo4j_builder,retrieval_pipeline,acl_enforcement,crosslingual_e2e}.py | wc -l` equals 6
    - conftest.py contains `addinivalue_line("markers", "integration` and `addinivalue_line("markers", "gpu`
    - `nx run sft-knowledge:test --args="-v"` exits 0 and reports ≥6 SKIPPED tests
    - `grep -l 'pytestmark = pytest.mark.skip' packages/sft-knowledge/tests/*.py | wc -l` equals 6
  </acceptance_criteria>
  <verify>
    <automated>nx run sft-knowledge:test --args="-v" 2&gt;&amp;1 | grep -E "(passed|skipped)" | grep -q "skipped"</automated>
  </verify>
  <done>All Wave 0 test scaffolding exists, conftest registers markers + testcontainer fixtures, downstream plans can fill in skipped stubs without scaffolding overhead.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| filesystem → MarkdownParser | Markdown corpus files are read; YAML frontmatter parsed via python-frontmatter (wraps yaml.safe_load) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-05-01-01 | Tampering | YAML frontmatter parsing | mitigate | python-frontmatter uses yaml.safe_load internally (RESEARCH §10 verified); never call yaml.load directly |
| T-05-01-02 | Information Disclosure | ACL default fallback | mitigate | Missing acl_level defaults to "internal" (NEVER "restricted") to avoid silently exposing a public doc as restricted (which would be a false-positive leak risk) — and never default to "public" which would leak silently-restricted docs. "internal" is the principled middle ground per D-67. |
| T-05-01-03 | Tampering | source_uri construction | accept | source_uri is derived from file path inside repo; not user-provided |
| T-05-01-SC | Tampering | npm/pip install | mitigate | Only stdlib-adjacent deps in this plan (pydantic, python-frontmatter, structlog already in workspace). Heavy deps (Qdrant, FlagEmbedding, llama-index, neo4j) declared in pyproject but NOT executed in this plan. Per Phase 5 RESEARCH Package Legitimacy Audit: all packages OK on PyPI. |
</threat_model>

<verification>
- `nx run sft-knowledge:lint` exits 0
- `nx run sft-knowledge:test --args="-m 'not integration and not gpu'"` exits 0
- All 41 SOPs parse without raising in `test_parse_all_41_sops`
- 6 Wave 0 test stubs report as SKIPPED with the correct reason string
- `uv run python -c "from sft_knowledge import DocumentParser, MarkdownParser, ParsedDoc, ParsedSection; from sft_knowledge.models import GraphNode, RagCitation; print('ok')"` prints `ok`
</verification>

<success_criteria>
- Plan 05-01 commits 4 atomic commits with conventional commit scope `feat(05-01-sft-knowledge-sdk):` or `test(05-01-sft-knowledge-sdk):`
- `nx run sft-knowledge:test` exits 0 with all real tests green + all Wave 0 stubs skipped
- All 6 Wave 0 test stubs from 05-VALIDATION.md exist
- MarkdownParser handles all 41 SOPs (after Plan 05-02 ACL migration: 41/41; before: ≥40/41)
- Public API surface (`__init__.py`) exposes the Wave 1 deliverables: DocumentParser, MarkdownParser, ParsedDoc, ParsedSection, GraphNode
</success_criteria>

<output>
Create `.planning/phases/05-knowledge-layer-rag-graph/05-01-sft-knowledge-sdk-SUMMARY.md` when done with: files created, test counts (real + skipped), 41-SOP parse success rate, downstream contract surface (what Plans 05-04/05/07/08/09 will fill in).
</output>
