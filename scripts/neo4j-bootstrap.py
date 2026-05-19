#!/usr/bin/env python3
"""
scripts/neo4j-bootstrap.py

Idempotent Neo4j constraint + index bootstrap per Plan 05-05 + D-65.

Applica (idempotente) gli statement Cypher del knowledge graph:
    - 4 unique constraints: machine_id_unique, part_id_unique,
      failure_mode_id_unique, sop_id_unique
    - 1 index: sop_version (SOP.version)

Verifica inoltre che il plugin APOC sia disponibile sulla istanza Neo4j
(CALL apoc.help('apoc')) — Phase 5 D-65.

Idempotency (RESEARCH §5):
    Tutti gli statement usano `IF NOT EXISTS` → re-run è no-op senza eccezioni.

Usage:
    python3 scripts/neo4j-bootstrap.py [--neo4j-uri URI] [--neo4j-auth USER/PASS] [--dry-run]

    Env fallback:
        NEO4J_URI  (default: bolt://localhost:7687)
        NEO4J_AUTH (default: neo4j/devpassword, formato user/password)

Exit codes:
    0 — bootstrap completato (o --dry-run completato)
    1 — errore di connessione / Cypher / APOC mancante / DSN invalida

Examples:
    python3 scripts/neo4j-bootstrap.py --dry-run
    python3 scripts/neo4j-bootstrap.py --neo4j-uri bolt://neo4j:7687
    NEO4J_AUTH=neo4j/secret python3 scripts/neo4j-bootstrap.py
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).parent.parent

# D-65 LOCKED — 4 unique constraints + 1 index del knowledge graph.
_CONSTRAINTS: tuple[str, ...] = (
    "CREATE CONSTRAINT machine_id_unique IF NOT EXISTS FOR (m:Machine) REQUIRE m.id IS UNIQUE",
    "CREATE CONSTRAINT part_id_unique IF NOT EXISTS FOR (p:Part) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT failure_mode_id_unique IF NOT EXISTS FOR (f:FailureMode) REQUIRE f.id IS UNIQUE",
    "CREATE CONSTRAINT sop_id_unique IF NOT EXISTS FOR (s:SOP) REQUIRE s.id IS UNIQUE",
    "CREATE INDEX sop_version IF NOT EXISTS FOR (s:SOP) ON (s.version)",
)


def _extract_name(cypher: str) -> str:
    """Estrae il nome del constraint/index dallo statement Cypher.

    Pattern: `CREATE (CONSTRAINT|INDEX) <name> IF NOT EXISTS ...`.
    Ritorna stringa vuota se il pattern non matcha (non dovrebbe mai accadere
    per `_CONSTRAINTS` ma manteniamo la difesa).
    """
    m = re.match(r"^CREATE\s+(?:CONSTRAINT|INDEX)\s+(\S+)", cypher, re.IGNORECASE)
    return m.group(1) if m else ""


def _parse_auth(auth: str) -> tuple[str, str]:
    """Parsa `user/password` (separatore `/`).

    Solleva ValueError se il formato è invalido (manca `/` o user vuoto).
    """
    if "/" not in auth:
        raise ValueError(
            f"--neo4j-auth must be in 'user/password' format, got: {auth!r}"
        )
    user, _, password = auth.partition("/")
    if not user:
        raise ValueError(f"--neo4j-auth has empty user component: {auth!r}")
    return user, password


def _parse_args() -> argparse.Namespace:
    """Parsa gli argomenti CLI (Pattern S-4)."""
    parser = argparse.ArgumentParser(
        description=(
            "Idempotent Neo4j bootstrap: applica 4 unique constraints + 1 index "
            "(Machine.id, Part.id, FailureMode.id, SOP.id, SOP.version) e "
            "verifica disponibilità APOC plugin."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--neo4j-uri",
        default=os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        help="Neo4j Bolt URI (default: NEO4J_URI env o bolt://localhost:7687)",
    )
    parser.add_argument(
        "--neo4j-auth",
        default=os.environ.get("NEO4J_AUTH", "neo4j/devpassword"),
        help=(
            "Credenziali Neo4j nel formato user/password "
            "(default: NEO4J_AUTH env o neo4j/devpassword)"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stampa il piano di bootstrap senza chiamate al driver. Exit 0.",
    )
    return parser.parse_args()


async def bootstrap(uri: str, auth: tuple[str, str], dry_run: bool) -> int:
    """Applica (idempotente) i constraint + index Neo4j + verifica APOC.

    Args:
        uri: Bolt URI del server Neo4j.
        auth: Tuple (user, password).
        dry_run: Se True, stampa il piano e ritorna 0 senza chiamate al driver.

    Returns:
        0 su successo, 1 su errore (connessione, Cypher, APOC mancante).
    """
    if dry_run:
        print("[dry-run] Neo4j bootstrap plan:")
        print(f"  uri: {uri}")
        print(f"  auth: {auth[0]}/***")
        print()
        for cypher in _CONSTRAINTS:
            name = _extract_name(cypher) or "<unnamed>"
            print(f"  would apply: {name}")
            print(f"    {cypher}")
        print()
        print("  would verify: CALL apoc.help('apoc') YIELD core RETURN count(*) AS n")
        print()
        print("OK [dry-run]: no driver connection performed")
        return 0

    # Lazy import — neo4j driver può non essere installato nel runner se non
    # vengono invocate sezioni non-dry-run.
    try:
        from neo4j import AsyncGraphDatabase
    except ImportError as exc:
        print(
            f"ERROR: neo4j driver not installed: {exc}. "
            "Installa con: uv add neo4j>=5.24,<7",
            file=sys.stderr,
        )
        return 1

    try:
        driver = AsyncGraphDatabase.driver(uri, auth=auth)
    except Exception as exc:
        print(
            f"ERROR: impossibile creare driver Neo4j ({uri}): {exc}",
            file=sys.stderr,
        )
        return 1

    try:
        async with driver.session(database="neo4j") as session:
            for cypher in _CONSTRAINTS:
                name = _extract_name(cypher) or "<unnamed>"
                try:
                    await session.run(cypher)
                    print(f"OK [{name}]: applied")
                except Exception as exc:
                    print(
                        f"ERROR [{name}]: {exc}",
                        file=sys.stderr,
                    )
                    return 1

            # APOC verification — Phase 5 D-65.
            try:
                result = await session.run(
                    "CALL apoc.help('apoc') YIELD core RETURN count(*) AS n"
                )
                record = await result.single()
            except Exception as exc:
                print(
                    f"ERROR: APOC unavailable (apoc.help failed): {exc} "
                    "— check NEO4J_PLUGINS env",
                    file=sys.stderr,
                )
                return 1

            if record is None or record["n"] == 0:
                print(
                    "ERROR: APOC plugin not loaded "
                    "(apoc.help returned no rows) — check NEO4J_PLUGINS env",
                    file=sys.stderr,
                )
                return 1
            print(f"OK [apoc]: plugin verified ({record['n']} procedures)")
    finally:
        await driver.close()

    return 0


def main() -> int:
    """Entry point principale — argparse + asyncio.run(bootstrap(...))."""
    args = _parse_args()
    try:
        auth = _parse_auth(args.neo4j_auth)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return asyncio.run(bootstrap(uri=args.neo4j_uri, auth=auth, dry_run=args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
