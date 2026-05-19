"""sft_knowledge.retrieval — retrieval tier (D-63 + KNW-09).

Modules:
    reranker: BgeReranker (BGE-reranker-v2-m3 cross-encoder, FlagReranker wrapper)
    pipeline: RetrievalPipeline + build_acl_filter + ROLE_TO_ACL constant
"""

from sft_knowledge.retrieval.pipeline import (
    ROLE_TO_ACL,
    RetrievalPipeline,
    build_acl_filter,
)
from sft_knowledge.retrieval.reranker import BgeReranker

__all__ = [
    "BgeReranker",
    "ROLE_TO_ACL",
    "RetrievalPipeline",
    "build_acl_filter",
]
