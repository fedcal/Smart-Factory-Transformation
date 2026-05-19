"""sft_knowledge.embedding — wrapper di embedding (BGE-M3 dense+sparse).

Esporta:
    BgeM3Embedder  — wrapper FlagEmbedding (primary) + fastembed (fallback)
    EncodeOutput   — modello frozen dell'output di `encode()`
"""

from sft_knowledge.embedding.bge_m3 import BgeM3Embedder, EncodeOutput

__all__ = ["BgeM3Embedder", "EncodeOutput"]
