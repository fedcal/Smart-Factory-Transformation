"""sft-knowledge: Knowledge layer per Phase 5 (RAG + Graph).

Wave 1 (this plan) espone le fondamenta dei contratti:
    DocumentParser     — ABC parser astratto (parse + supported_extensions)
    MarkdownParser     — implementazione concreta per file *.md con frontmatter
    ParsedDoc          — modello frozen del documento parsato (D-67)
    ParsedSection      — sezione con heading_path + testo
    GraphNode          — nodo del grafo (label Literal: Machine|Part|FailureMode|SOP)

Wave 2/3/4 (Plans 05-04 .. 05-09) aggiungeranno:
    SemanticChunker    — llama-index SemanticSplitterNodeParser wrapper (05-07)
    BgeM3Embedder      — bge-m3 embedding singleton (05-07)
    QdrantIndexer      — collection bootstrap + batch upsert (05-04 + 05-08)
    Neo4jGraphBuilder  — MERGE idempotente nodi/relazioni (05-05 + 05-08)
    RetrievalPipeline  — hybrid dense+sparse + reranking (05-09)
    BgeReranker        — bge-reranker-v2-m3 (05-09)
    RagSearchTool      — LangChain BaseTool (05-09)
    TraverseGraphTool  — LangChain BaseTool (05-09)
    QdrantLongTermMemory — Memory ABC impl (05-09)

Convenzioni (per 05-PATTERNS.md Shared Patterns 1-10):
    - Pydantic v2 frozen + extra=forbid su ogni model
    - datetime.now(timezone.utc) only — mai datetime.now()
    - yaml.safe_load only — mai yaml.load
    - structlog.get_logger(__name__) a livello modulo
    - markers pytest: integration, gpu
"""

from sft_knowledge.chunking import Chunk, SemanticChunker
from sft_knowledge.embedding import BgeM3Embedder, EncodeOutput
from sft_knowledge.models import GraphNode, RagCitation
from sft_knowledge.parsers import DocumentParser, MarkdownParser, ParsedDoc, ParsedSection
from sft_knowledge.path_utils import WORKSPACE_ROOT, derive_source_uri
from sft_knowledge.retrieval import (
    ROLE_TO_ACL,
    BgeReranker,
    RetrievalPipeline,
    build_acl_filter,
)
from sft_knowledge.stores import Neo4jGraphBuilder, QdrantIndexer, point_id
from sft_knowledge.memory import QdrantLongTermMemory, QdrantLongTermMemoryConfig
from sft_knowledge.tools import (
    RagSearchInput,
    RagSearchTool,
    TraverseGraphInput,
    TraverseGraphTool,
)

__all__ = [
    "DocumentParser",
    "MarkdownParser",
    "ParsedDoc",
    "ParsedSection",
    "GraphNode",
    "RagCitation",
    "BgeM3Embedder",
    "EncodeOutput",
    "SemanticChunker",
    "Chunk",
    "QdrantIndexer",
    "point_id",
    "Neo4jGraphBuilder",
    "BgeReranker",
    "RetrievalPipeline",
    "ROLE_TO_ACL",
    "build_acl_filter",
    "RagSearchTool",
    "RagSearchInput",
    "TraverseGraphTool",
    "TraverseGraphInput",
    "QdrantLongTermMemory",
    "QdrantLongTermMemoryConfig",
    "derive_source_uri",
    "WORKSPACE_ROOT",
]
