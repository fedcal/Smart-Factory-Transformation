#!/usr/bin/env python3
"""
scripts/qdrant-bootstrap.py

Idempotent Qdrant collection bootstrap per Plan 05-04 + D-61.

Crea (idempotente) le 4 collection del knowledge layer:
    sop, manuals, troubleshooting, training

Ogni collection ha:
    - named dense vector "dense"  : size=1024, distance=Cosine,
                                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100)
    - named sparse vector "sparse": SparseIndexParams(on_disk=False)
    - on_disk_payload=False

Payload indexes (KEYWORD) creati per ciascuna collection:
    source_uri, acl_level, lang, category, version, asset_family, sop_id

Idempotency (RESEARCH §9):
    - get_collections() → set di nomi esistenti; create_collection solo se mancante
    - create_payload_index è idempotente lato Qdrant (re-run non solleva eccezioni)

Usage:
    python3 scripts/qdrant-bootstrap.py [--qdrant-url URL] [--dry-run]

    Env fallback: QDRANT_URL (default: http://localhost:6333)

Exit codes:
    0  — bootstrap completato (o --dry-run completato)
    1  — errore di connessione / API

Examples:
    python3 scripts/qdrant-bootstrap.py --dry-run
    python3 scripts/qdrant-bootstrap.py --qdrant-url http://qdrant:6333
    QDRANT_URL=http://qdrant:6333 python3 scripts/qdrant-bootstrap.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import pathlib
import sys

WORKSPACE_ROOT = pathlib.Path(__file__).parent.parent

# D-61 LOCKED — 4 collection del knowledge layer.
COLLECTIONS: tuple[str, ...] = ("sop", "manuals", "troubleshooting", "training")

# D-61 + CONTEXT.md claudes_discretion — 7 payload indexes KEYWORD.
PAYLOAD_INDEX_FIELDS: tuple[str, ...] = (
    "source_uri",
    "acl_level",
    "lang",
    "category",
    "version",
    "asset_family",
    "sop_id",
)

# BGE-M3 native dense vector size (D-61).
DENSE_DIM = 1024


def _parse_args() -> argparse.Namespace:
    """Parsa gli argomenti CLI con argparse (Pattern S-4)."""
    parser = argparse.ArgumentParser(
        description=(
            "Idempotent Qdrant bootstrap: crea 4 collection "
            "(sop, manuals, troubleshooting, training) con named vectors "
            "dense (1024-d cosine) + sparse (BM42) e payload indexes "
            "(source_uri, acl_level, lang, category, version, asset_family, sop_id)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--qdrant-url",
        default=os.environ.get("QDRANT_URL", "http://localhost:6333"),
        help="Qdrant URL (default: QDRANT_URL env o http://localhost:6333)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stampa il piano di bootstrap senza chiamate al client. Exit 0.",
    )
    return parser.parse_args()


async def bootstrap(url: str, dry_run: bool) -> int:
    """Crea (idempotente) le 4 collection Qdrant + i 7 payload index per ciascuna.

    Args:
        url: URL del server Qdrant.
        dry_run: Se True, stampa il piano e ritorna 0 senza chiamate al client.

    Returns:
        0 su successo, 1 su errore.
    """
    if dry_run:
        print("[dry-run] Qdrant bootstrap plan:")
        print(f"  url: {url}")
        print(f"  dense vector size: {DENSE_DIM} (cosine, hnsw m=16 ef_construct=100)")
        print("  sparse vector: SparseVectorParams(on_disk=False)")
        print()
        for name in COLLECTIONS:
            print(f"  Collection: {name}")
            print(f"    would create if absent (CREATE COLLECTION IF NOT EXISTS)")
            print(f"    payload indexes (KEYWORD):")
            for field in PAYLOAD_INDEX_FIELDS:
                print(f"      - {field}")
            print()
        print("OK [dry-run]: no API calls performed")
        return 0

    # Lazy import — qdrant-client può non essere installato in dev runner senza
    # le extras integration. In dry-run il modulo non è richiesto.
    from qdrant_client import AsyncQdrantClient
    from qdrant_client.http.models import (
        Distance,
        HnswConfigDiff,
        PayloadSchemaType,
        SparseIndexParams,
        SparseVectorParams,
        VectorParams,
    )

    client = AsyncQdrantClient(url=url)

    try:
        existing = {c.name for c in (await client.get_collections()).collections}
    except Exception as exc:
        print(
            f"ERROR: impossibile recuperare collections da {url}: {exc}",
            file=sys.stderr,
        )
        await client.close()
        return 1

    for name in COLLECTIONS:
        try:
            if name in existing:
                print(f"OK [{name}]: exists")
            else:
                await client.create_collection(
                    collection_name=name,
                    vectors_config={
                        "dense": VectorParams(
                            size=DENSE_DIM,
                            distance=Distance.COSINE,
                            hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                        ),
                    },
                    sparse_vectors_config={
                        "sparse": SparseVectorParams(
                            index=SparseIndexParams(on_disk=False),
                        ),
                    },
                    on_disk_payload=False,
                )
                print(f"OK [{name}]: created")

            # Payload indexes — create_payload_index è idempotente lato Qdrant
            # (RESEARCH §9): re-run su field già indicizzato non solleva eccezione.
            for field in PAYLOAD_INDEX_FIELDS:
                await client.create_payload_index(
                    collection_name=name,
                    field_name=field,
                    field_schema=PayloadSchemaType.KEYWORD,
                )
                print(f"OK [{name}]: payload_index.{field} ready")
        except Exception as exc:
            print(f"ERROR [{name}]: {exc}", file=sys.stderr)
            await client.close()
            return 1

    await client.close()
    return 0


def main() -> int:
    """Entry point principale — argparse + asyncio.run(bootstrap(...))."""
    args = _parse_args()
    return asyncio.run(bootstrap(url=args.qdrant_url, dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
