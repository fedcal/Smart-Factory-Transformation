---
phase: 05-knowledge-layer-rag-graph
plan: 05-01
subsystem: knowledge
tags: [pydantic, frontmatter, structlog, abc, markdown, sop, rag, knowledge-graph]

requires:
  - phase: 04-agent-core-runtime-hitl
    provides: RagCitation (sft_agents.models.evidence), Memory ABC (sft_agents.sdk.memory)
  - phase: 02-domain-knowledge-corpus
    provides: 40 SOP markdown files under simulators/synthetic-corpus/{it,en}/
provides:
  - sft-knowledge Python package scaffold (pyproject + Nx project)
  - DocumentParser ABC with async parse() + supported_extensions()
  - ParsedDoc / ParsedSection frozen Pydantic v2 models (D-67)
  - GraphNode frozen model with Literal["Machine","Part","FailureMode","SOP"] label
  - MarkdownParser concrete impl with status:reviewed gate (D-25) + acl_level default-internal (D-72)
  - Wave 0 conftest with integration/gpu markers + qdrant/neo4j/bge_m3 fixtures
  - 6 skipped test stubs mapping to KNW-01/04/05/06/08/09 + SC#1
affects:
  - 05-04-qdrant-bootstrap (consumes qdrant_client fixture)
  - 05-05-neo4j-compose-bootstrap (consumes neo4j_driver fixture)
  - 05-07-embedding-chunking (consumes bge_m3_embedder fixture + ParsedDoc)
  - 05-08-indexer-graph-builder (fills qdrant_indexer + neo4j_builder stubs)
  - 05-09-retrieval-pipeline-tools-memory (fills retrieval/acl/crosslingual stubs)
  - 05-10-ingest-service-cli-ci-eval-docs (consumes MarkdownParser via CLI ingest)

tech-stack:
  added:
    - python-frontmatter (YAML frontmatter parsing, wraps yaml.safe_load)
    - qdrant-client[fastembed] (declared, executed in 05-04+)
    - FlagEmbedding (declared, executed in 05-07+)
    - llama-index-core + llama-index-embeddings-huggingface (declared, executed in 05-07+)
    - neo4j>=5.24,<7 (upper bound mandatory per RESEARCH §5 Risk 1)
  patterns:
    - Pydantic v2 frozen + extra=forbid on every model (Shared Pattern 1)
    - DocumentParser ABC mirrors sft_agents.sdk.memory.Memory ABC shape
    - heading-state machine via re.MULTILINE pattern over post.content
    - immutable dict update for acl_level fallback (coding-style.md immutability rule)
    - python-frontmatter as YAML-safe wrapper (T-05-01-01 mitigation)
    - testcontainer fixtures with lazy imports to allow conftest collection
      even when integration deps absent
    - skipped-stub pattern (pytestmark + plan reference) for Wave-0 scaffolding

key-files:
  created:
    - packages/sft-knowledge/pyproject.toml
    - packages/sft-knowledge/project.json
    - packages/sft-knowledge/src/sft_knowledge/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/parsers/__init__.py
    - packages/sft-knowledge/src/sft_knowledge/parsers/base.py
    - packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py
    - packages/sft-knowledge/src/sft_knowledge/models.py
    - packages/sft-knowledge/tests/conftest.py
    - packages/sft-knowledge/tests/test_models.py
    - packages/sft-knowledge/tests/test_markdown_parser.py
    - packages/sft-knowledge/tests/test_semantic_chunker.py
    - packages/sft-knowledge/tests/test_qdrant_indexer.py
    - packages/sft-knowledge/tests/test_neo4j_builder.py
    - packages/sft-knowledge/tests/test_retrieval_pipeline.py
    - packages/sft-knowledge/tests/test_acl_enforcement.py
    - packages/sft-knowledge/tests/test_crosslingual_e2e.py
  modified:
    - pyproject.toml (workspace members: + packages/sft-knowledge)
    - uv.lock (refreshed with new deps tree)

key-decisions:
  - "ACL fallback default is 'internal' per D-67/D-72 — NEVER 'restricted' (false-positive leak risk) and NEVER 'public' (silent restricted-leak risk)"
  - "neo4j upper bound pinned to <7 per RESEARCH §5 Risk 1 to avoid v6 breaking changes"
  - "RagCitation imported from sft_agents.models.evidence — NOT redefined (D-59); test_rag_citation_reexport_is_same_class_as_sft_agents asserts identity"
  - "Task 1 scaffold pre-shaped base.py + models.py to satisfy import-time acceptance; Task 2 TDD locks invariants via test_models.py (14 tests covering frozen, extra=forbid, Literal whitelists, ABC enforcement)"
  - "test_parse_all_41_sops scoped to ≥40 SOPs (actual checkout has 40 SOP files; the plan-quoted '41' includes simulators/synthetic-corpus/README.md)"

patterns-established:
  - "Wave-0 stub pattern: each test file carries a header comment with the covered requirement ID and a pytestmark = pytest.mark.skip(reason='Implemented in Plan 05-XX') so downstream plan executors navigate failing test → covering requirement"
  - "Workspace-root path derivation: parents[5] from packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py (alternative to scripts/-relative parents[2])"
  - "Testcontainer fixtures lazy-import their drivers so the conftest stays importable when only unit tests run"

requirements-completed: [KNW-04, KNW-05]

duration: 29min
completed: 2026-05-19
---

# Phase 05 Plan 01: sft-knowledge SDK scaffold Summary

**sft-knowledge package bootstrapped with DocumentParser ABC, MarkdownParser parsing all 40 corpus SOPs (status+ACL gated, heading_path state machine), frozen Pydantic models (ParsedDoc/ParsedSection/GraphNode + RagCitation re-export), and Wave-0 test scaffolding (conftest + 6 stubs) wired to KNW-01/04/05/06/08/09+SC#1**

## Performance

- **Duration:** ~29 min
- **Started:** 2026-05-19T09:29:59Z
- **Completed:** 2026-05-19T09:58:58Z
- **Tasks:** 4 / 4
- **Files created:** 16
- **Files modified:** 2

## Accomplishments

- `sft-knowledge` package added to the uv/Nx workspace (lint + import green)
- DocumentParser ABC + ParsedDoc/ParsedSection/GraphNode models locked behind 14 invariant tests (frozen, extra=forbid, Literal whitelists, ABC enforcement, RagCitation identity)
- MarkdownParser parses **all 40 SOPs** under `simulators/synthetic-corpus/{it,en}/` with zero exceptions; status gate + ACL default-internal verified via 9 unit tests
- Wave-0 conftest + 6 skipped stubs in place so Plans 05-04/05/07/08/09 can drop in real assertions without scaffolding overhead
- Public API surface: `from sft_knowledge import DocumentParser, MarkdownParser, ParsedDoc, ParsedSection, GraphNode` and `from sft_knowledge.models import GraphNode, RagCitation`

## Task Commits

Each task committed atomically:

1. **Task 1: Scaffold sft-knowledge package** — `f4450ca` (feat)
2. **Task 2: DocumentParser ABC + frozen models** — `5fe9d17` (feat) — 14 invariant tests
3. **Task 3: MarkdownParser with status/ACL gates** — `0d7a706` (feat) — 9 tests (RED → GREEN)
4. **Task 4: Wave 0 conftest + 6 skipped stubs** — `a7ae809` (test)

**Plan metadata:** to be created in the final commit covering this SUMMARY.md

## Files Created/Modified

### Created
- `packages/sft-knowledge/pyproject.toml` — package manifest with locked deps + heavy ML deps declared (executed in later plans)
- `packages/sft-knowledge/project.json` — Nx library target `test` + `lint`; implicitDependencies [sft-domain, sft-assets, sft-agents]
- `packages/sft-knowledge/src/sft_knowledge/__init__.py` — public API Wave-1 exports
- `packages/sft-knowledge/src/sft_knowledge/parsers/__init__.py` — re-export DocumentParser, MarkdownParser, ParsedDoc, ParsedSection
- `packages/sft-knowledge/src/sft_knowledge/parsers/base.py` — DocumentParser ABC + ParsedDoc/ParsedSection frozen Pydantic v2 models
- `packages/sft-knowledge/src/sft_knowledge/parsers/markdown.py` — MarkdownParser concrete impl (status gate, ACL fallback, heading state machine)
- `packages/sft-knowledge/src/sft_knowledge/models.py` — GraphNode + RagCitation re-export from sft_agents
- `packages/sft-knowledge/tests/conftest.py` — marker registration + qdrant/neo4j testcontainer fixtures + bge_m3_embedder lazy fixture
- `packages/sft-knowledge/tests/test_models.py` — 14 model + ABC invariant tests
- `packages/sft-knowledge/tests/test_markdown_parser.py` — 9 tests including full-corpus pass
- `packages/sft-knowledge/tests/test_semantic_chunker.py` — Plan 05-07 stub (KNW-04)
- `packages/sft-knowledge/tests/test_qdrant_indexer.py` — Plan 05-04+05-08 stub (KNW-01, KNW-05)
- `packages/sft-knowledge/tests/test_neo4j_builder.py` — Plan 05-05+05-08 stub (KNW-08 SC#4)
- `packages/sft-knowledge/tests/test_retrieval_pipeline.py` — Plan 05-09 stub (KNW-09)
- `packages/sft-knowledge/tests/test_acl_enforcement.py` — Plan 05-09 stub (KNW-06 SC#2)
- `packages/sft-knowledge/tests/test_crosslingual_e2e.py` — Plan 05-09 stub (SC#1)

### Modified
- `pyproject.toml` — added `packages/sft-knowledge` to `[tool.uv.workspace] members`
- `uv.lock` — refreshed with the new package + downstream Phase 5 transitive deps

## Test counts

| Bucket | Count | Status |
|--------|-------|--------|
| Real unit tests (test_models.py + test_markdown_parser.py) | 23 | passed |
| Wave-0 skipped stubs (6 files, 9 stub tests) | 9 | skipped (intentional) |
| Integration / GPU markers | 0 executed | excluded by `-m 'not integration and not gpu'` |

## SOP parse success rate

- **Files under `simulators/synthetic-corpus/` matching `SOP-*.md`:** 40
- **Successfully parsed to ParsedDoc:** 40 / 40 (100%)
- **status=reviewed:** all 40 → none skipped by the D-25 gate
- **acl_level present in frontmatter:** 0 / 40 (all defaulted to "internal" via D-72 fallback; Plan 05-02 ACL migration will inject explicit values)

## Decisions Made

- **acl_level default = "internal"** (D-67/D-72): never `restricted` (false-positive leak risk), never `public` (silent restricted-leak risk). The fallback emits a `sop_missing_acl_level` WARN log so downstream observers can audit the path.
- **neo4j upper bound `<7`** (RESEARCH §5 Risk 1): pinned in `pyproject.toml` to avoid v6 breaking changes; acceptance grep verifies the literal in `pyproject.toml`.
- **RagCitation re-export, no redefine** (D-59): `sft_knowledge.models.RagCitation is sft_agents.models.evidence.RagCitation` enforced by `test_rag_citation_reexport_is_same_class_as_sft_agents`.
- **Task 1 / Task 2 sequencing for TDD plausibility:** because Task 1's acceptance includes "`import sft_knowledge` succeeds", the model shapes were created in Task 1's scaffold. Task 2's TDD locks the invariants in place via `test_models.py` (14 tests). Documented in the Task 2 commit body.
- **`test_parse_all_41_sops` scoped to ≥40 SOPs**: the actual checkout has 40 SOP files; the plan-quoted "41" includes `simulators/synthetic-corpus/README.md`. The test asserts `len(paths) >= 40` to remain robust to corpus growth in Plan 05-02.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SOP count discrepancy: 40 SOPs, not 41**
- **Found during:** Task 3 (`test_parse_all_41_sops` RED phase)
- **Issue:** The plan and `must_haves.truths` quote "all 41 SOPs", but `find simulators/synthetic-corpus -name 'SOP-*.md' | wc -l` returns 40. The 41st *.md under that tree is the corpus `README.md`, not an SOP.
- **Fix:** Test asserts `len(paths) >= 40` instead of `== 41` and verifies every found SOP parses to `ParsedDoc` (no exception, no skip). Comment in the test body documents the count and the README explanation.
- **Files modified:** `packages/sft-knowledge/tests/test_markdown_parser.py`
- **Verification:** `test_parse_all_41_sops` PASSED (40/40 parsed)
- **Committed in:** `0d7a706` (Task 3 commit)

**2. [Rule 3 - Blocking] Import-order auto-fix on test files**
- **Found during:** Task 4 final lint sweep (`uv run ruff check packages/sft-knowledge/`)
- **Issue:** Two ruff `I001` (import sorting) violations in `test_markdown_parser.py` and `test_models.py`; `nx run sft-knowledge:lint` only lints `src/`, so the issues slipped past the per-task gates.
- **Fix:** `uv run ruff check --fix packages/sft-knowledge/` — automatic import sort.
- **Files modified:** `packages/sft-knowledge/tests/test_markdown_parser.py`, `packages/sft-knowledge/tests/test_models.py`
- **Verification:** `uv run ruff check packages/sft-knowledge/` → All checks passed; full test suite still 23 passed / 9 skipped.
- **Committed in:** `a7ae809` (folded into the Task 4 commit body)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Neither deviation affects the plan's deliverable surface or downstream contracts. Both are accuracy corrections for the existing corpus and tooling.

## Issues Encountered

- **`nx run sft-knowledge:test`** does not work in this checkout (`@nxlv/python` plugin is referenced in `project.json` but not installed). Verification used `uv run pytest packages/sft-knowledge/tests -v` directly. The `project.json` target is correct for the eventual nx plugin install; not a blocker because plain `pytest` is the contractual verifier (`acceptance_criteria` of Task 2 calls out `nx run` but the underlying `uv run pytest …` command is what was executed).
- **`uv sync --all-packages`** initially failed to install `sft-knowledge` until the workspace root `pyproject.toml` `[tool.uv.workspace] members` list was updated. Fixed inline (Rule 3) by adding `packages/sft-knowledge` to members, then re-running `uv lock` + `uv sync`.

## Known Stubs

| File | Lines | Reason | Plan that fills it |
|------|-------|--------|--------------------|
| `tests/test_semantic_chunker.py` | full file (pytestmark.skip) | Wave-0 scaffolding | 05-07 |
| `tests/test_qdrant_indexer.py` | full file (pytestmark.skip) | Wave-0 scaffolding | 05-04 + 05-08 |
| `tests/test_neo4j_builder.py` | full file (pytestmark.skip) | Wave-0 scaffolding | 05-05 + 05-08 |
| `tests/test_retrieval_pipeline.py` | full file (pytestmark.skip) | Wave-0 scaffolding | 05-09 |
| `tests/test_acl_enforcement.py` | full file (pytestmark.skip) | Wave-0 scaffolding | 05-09 |
| `tests/test_crosslingual_e2e.py` | full file (pytestmark.skip) | Wave-0 scaffolding | 05-09 |
| `parsers/markdown.py` (no stub — full impl) | — | — | — |

All stubs are **intentional** Wave-0 scaffolding per `05-VALIDATION.md`; they do not block Plan 05-01's goal (parser/model contracts ready for Waves 2-4).

## Downstream Contract Surface (Wave 1 deliverables)

| Symbol | Path | Will be consumed by |
|--------|------|---------------------|
| `DocumentParser` | `sft_knowledge.parsers.base.DocumentParser` | 05-07 (SemanticChunker accepts ParsedDoc), 05-10 (ingest CLI dispatches by `supported_extensions()`) |
| `MarkdownParser` | `sft_knowledge.parsers.markdown.MarkdownParser` | 05-10 (CLI ingest entrypoint), 05-09 (retrieval pipeline tests) |
| `ParsedDoc` / `ParsedSection` | `sft_knowledge.parsers.base` | 05-07 (chunker input), 05-08 (indexer payload source) |
| `GraphNode` | `sft_knowledge.models.GraphNode` | 05-05 (graph builder schema), 05-08 (Neo4j MERGE statements), 05-09 (TraverseGraphTool output) |
| `RagCitation` re-export | `sft_knowledge.models.RagCitation` | 05-09 (RetrievalPipeline / RagSearchTool emits citations) |
| `qdrant_client` fixture | `tests/conftest.py` | 05-04 + 05-08 integration tests |
| `neo4j_driver` fixture | `tests/conftest.py` | 05-05 + 05-08 integration tests |
| `bge_m3_embedder` fixture | `tests/conftest.py` | 05-07 embedding tests |

## User Setup Required

None — Plan 05-01 is purely Python scaffold work. Heavy deps (Qdrant, FlagEmbedding, llama-index, neo4j) are declared in `pyproject.toml` for the dependency graph but not exercised at runtime in this plan. Plans 05-04 and 05-05 will introduce the testcontainer/Docker compose requirements.

## Next Phase Readiness

- **Plan 05-02 (ACL migration)** can rely on `MarkdownParser` to validate its corpus migration end-to-end via `test_parse_all_41_sops`.
- **Plan 05-03 (failure modes YAML)** is independent (Wave 1 sibling); no consumed contracts.
- **Plans 05-04 / 05-05** can drop their `test_collection_bootstrap_idempotent` / `test_graph_ci_validator` impls into the existing skipped stubs without touching scaffolding.
- **Plan 05-07** has `bge_m3_embedder` fixture pre-wired and `ParsedDoc` shape locked.

## Self-Check: PASSED

Verified against acceptance + done criteria:
- `packages/sft-knowledge/pyproject.toml` contains `name = "sft-knowledge"` and `"neo4j>=5.24,<7"` (grep OK)
- `packages/sft-knowledge/project.json` contains `"implicitDependencies": ["sft-domain", "sft-assets", "sft-agents"]` (grep OK)
- `packages/sft-knowledge/src/sft_knowledge/__init__.py` defines `__all__` list (grep OK)
- `nx run sft-knowledge:lint` exits 0 (Nx output OK)
- `uv run python -c "import sft_knowledge"` exits 0 (`OK ['DocumentParser', 'MarkdownParser', 'ParsedDoc', 'ParsedSection', 'GraphNode']`)
- `class DocumentParser(ABC):` in `parsers/base.py` (grep OK)
- `@abstractmethod` + `model_config = {"frozen": True, "extra": "forbid"}` in `parsers/base.py` (grep OK)
- `from sft_agents.models.evidence import RagCitation` + `class GraphNode(BaseModel):` in `models.py` (grep OK)
- `class MarkdownParser(DocumentParser):` + `frontmatter.load` + `"sop_missing_acl_level"` + `"sop_skipped_non_reviewed"` in `parsers/markdown.py` (grep OK)
- Six Wave-0 stub files exist and each contains `pytestmark = pytest.mark.skip` (count=6 OK)
- `conftest.py` registers `integration` + `gpu` markers (grep OK)
- Full suite `uv run pytest packages/sft-knowledge/tests -m "not integration and not gpu"`: 23 passed, 9 skipped, 0 failed

Commits verified in `git log`:
- f4450ca — Task 1 scaffold
- 5fe9d17 — Task 2 ABC + models
- 0d7a706 — Task 3 MarkdownParser
- a7ae809 — Task 4 Wave-0 stubs

---
*Phase: 05-knowledge-layer-rag-graph*
*Completed: 2026-05-19*
