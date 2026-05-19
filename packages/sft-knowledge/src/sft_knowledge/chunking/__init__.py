"""sft_knowledge.chunking — chunking semantico LlamaIndex.

Esporta:
    SemanticChunker — wrapper di `SemanticSplitterNodeParser` con propagazione metadata
    Chunk           — modello frozen del singolo chunk (text, idx, heading_path, metadata)
"""

from sft_knowledge.chunking.semantic import Chunk, SemanticChunker

__all__ = ["SemanticChunker", "Chunk"]
