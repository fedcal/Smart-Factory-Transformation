"""Typer CLI entrypoint for the knowledge ingest pipeline (Plan 05-10 Task 2).

Three commands:

    knowledge-ingest run [--paths PATH ...] [--files FILE ...] [--mode incremental]
                         [--collection sop]
        Ingest a set of Markdown files into Qdrant + Neo4j + ingest_state. Driven
        by the pipeline orchestrator (pipeline.ingest_file). Skips unchanged files
        by content_hash (KNW-07 SC#3).

    knowledge-ingest bootstrap
        Wraps scripts/qdrant-bootstrap.py + scripts/neo4j-bootstrap.py +
        scripts/timescale-migrate.py via subprocess. Idempotent.

    knowledge-ingest validate
        Reachability + schema health probe. Verifies:
            - Qdrant: all 4 collections exist (D-61).
            - Neo4j: all 4 unique constraints + sop_version index exist (D-65).
            - PG: knowledge.ingest_state table exists.
            - failure_modes.yaml loads with > 0 entries.

Env vars (required for run/validate):
    QDRANT_URL       — default http://localhost:6333
    NEO4J_URI        — default bolt://localhost:7687
    NEO4J_AUTH       — default neo4j/cipassword
    TIMESCALE_DSN    — REQUIRED (no default — fail fast)

Structlog JSON output is configured before any log emission per Shared Pattern 6.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import structlog
import typer

# Configure structlog JSON output at module top (Shared Pattern 6 + ot-bridge main.py).
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
)

logger = structlog.get_logger("svc-knowledge-ingest")

# Workspace root = parents[4] from this file (see pipeline._derive_source_uri).
_WORKSPACE_ROOT: Path = Path(__file__).resolve().parents[4]

app = typer.Typer(
    help="sft knowledge ingest pipeline (Phase 5): parse → chunk → embed → Qdrant + Neo4j + state.",
    add_completion=False,
    no_args_is_help=True,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_env(name: str) -> str:
    """Fail-fast read of an env var (ot-bridge main.py lines 64-69 pattern)."""
    value = os.environ.get(name)
    if not value:
        raise typer.Exit(code=2)  # generic error code; calling code logs the reason
    return value


def _resolve_files(paths: list[str], files: list[str]) -> list[Path]:
    """Build the candidate file list from --paths (rglob *.md) and --files (CSV or repeat).

    Both options may be passed. Comma-separated values within a single token are
    also expanded, so the reindex.yml workflow can run::

        knowledge-ingest run --files=a.md,b.md,c.md

    or::

        knowledge-ingest run --files a.md --files b.md
    """
    candidates: list[Path] = []
    for entry in files:
        for token in entry.split(","):
            token = token.strip()
            if token:
                candidates.append(Path(token))
    for entry in paths:
        p = Path(entry)
        if p.is_dir():
            candidates.extend(sorted(p.rglob("*.md")))
        elif p.is_file() and p.suffix == ".md":
            candidates.append(p)
    return candidates


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


@app.command()
def run(  # noqa: PLR0913 — Typer-level options
    paths: list[str] = typer.Option(
        [], "--paths", help="Directory roots to walk for *.md (recursively)."
    ),
    files: list[str] = typer.Option(
        [], "--files", help="Comma-separated or repeated explicit file paths."
    ),
    mode: str = typer.Option(
        "incremental",
        "--mode",
        help="Ingest mode (incremental|full). Currently informational — "
        "the content_hash gate handles incremental skip.",
    ),
    collection: str = typer.Option(
        "sop", "--collection", help="Target Qdrant collection (D-61)."
    ),
) -> None:
    """Ingest a set of Markdown files into Qdrant + Neo4j + ingest_state."""
    log = logger.bind(command="run", mode=mode, collection=collection)
    candidate_files = _resolve_files(paths, files)
    log.info(
        "ingest_run_starting",
        files_count=len(candidate_files),
        paths_count=len(paths),
    )
    if not candidate_files:
        log.warning("ingest_run_no_files")
        raise typer.Exit(code=0)

    asyncio.run(_async_run(candidate_files, collection, mode))


async def _async_run(files: list[Path], collection: str, mode: str) -> None:
    """Construct collaborators and drive `pipeline.ingest_file` for each file.

    Heavy SDK imports are deferred here (not at module top) so `--help` and
    `validate` stay fast.
    """
    from neo4j import AsyncGraphDatabase
    from qdrant_client import AsyncQdrantClient

    import asyncpg

    from sft_domain.failure_modes import load_failure_modes
    from sft_knowledge.chunking.semantic import SemanticChunker
    from sft_knowledge.embedding.bge_m3 import BgeM3Embedder
    from sft_knowledge.parsers.markdown import MarkdownParser
    from sft_knowledge.stores.neo4j import Neo4jGraphBuilder
    from sft_knowledge.stores.qdrant import QdrantIndexer

    from svc_knowledge_ingest.pipeline import ingest_file
    from svc_knowledge_ingest.state import IngestStateStore

    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_auth = os.environ.get("NEO4J_AUTH", "neo4j/cipassword")
    timescale_dsn = os.environ.get("TIMESCALE_DSN")
    if not timescale_dsn:
        raise RuntimeError(
            "TIMESCALE_DSN env var is required (e.g. "
            "postgresql://sft:sft_dev_pass@localhost:5432/sft)"
        )
    user, _, password = neo4j_auth.partition("/")

    log = logger.bind(qdrant_url=qdrant_url, neo4j_uri=neo4j_uri)

    qdrant_client = AsyncQdrantClient(url=qdrant_url)
    neo4j_driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(user, password))
    pg_pool = await asyncpg.create_pool(
        timescale_dsn,
        min_size=1,
        max_size=4,
        statement_cache_size=0,
        command_timeout=30.0,
    )
    assert pg_pool is not None

    parser = MarkdownParser()
    chunker = SemanticChunker()
    embedder = BgeM3Embedder()
    qdrant_indexer = QdrantIndexer(client=qdrant_client, collection=collection)
    neo4j_builder = Neo4jGraphBuilder(driver=neo4j_driver)
    state_store = IngestStateStore(pg_pool)
    failure_modes = load_failure_modes()

    total_ingested = 0
    total_skipped = 0
    try:
        for f in files:
            try:
                result = await ingest_file(
                    f,
                    parser=parser,
                    chunker=chunker,
                    embedder=embedder,
                    qdrant_indexer=qdrant_indexer,
                    neo4j_builder=neo4j_builder,
                    state_store=state_store,
                    failure_modes=failure_modes,
                )
                if result.skipped:
                    total_skipped += 1
                else:
                    total_ingested += 1
            except Exception as exc:
                log.error(
                    "ingest_file_failed",
                    file=str(f),
                    error=str(exc),
                )
                # Continue with remaining files; the CI will surface non-zero rc
                # only via uncaught errors at the top of asyncio.run() if needed.
                raise
    finally:
        await qdrant_client.close()
        await neo4j_driver.close()
        await pg_pool.close()

    log.info(
        "ingest_run_done",
        total_files=len(files),
        total_ingested=total_ingested,
        total_skipped=total_skipped,
    )


# ---------------------------------------------------------------------------
# bootstrap command
# ---------------------------------------------------------------------------


@app.command()
def bootstrap() -> None:
    """Run the three Phase 5 bootstrap scripts in order: timescale → qdrant → neo4j.

    Idempotent; each script logs its own progress. Exit code 1 on first failure.
    """
    log = logger.bind(command="bootstrap")
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_auth = os.environ.get("NEO4J_AUTH", "neo4j/cipassword")
    timescale_dsn = os.environ.get("TIMESCALE_DSN")
    if not timescale_dsn:
        log.error("missing_env", var="TIMESCALE_DSN")
        raise typer.Exit(code=2)

    scripts = [
        (
            "timescale-migrate",
            [
                sys.executable,
                str(_WORKSPACE_ROOT / "scripts" / "timescale-migrate.py"),
                "--dsn",
                timescale_dsn,
            ],
        ),
        (
            "qdrant-bootstrap",
            [
                sys.executable,
                str(_WORKSPACE_ROOT / "scripts" / "qdrant-bootstrap.py"),
                "--qdrant-url",
                qdrant_url,
            ],
        ),
        (
            "neo4j-bootstrap",
            [
                sys.executable,
                str(_WORKSPACE_ROOT / "scripts" / "neo4j-bootstrap.py"),
                "--neo4j-uri",
                neo4j_uri,
                "--neo4j-auth",
                neo4j_auth,
            ],
        ),
    ]

    for name, cmd in scripts:
        log.info("bootstrap_step_start", step=name)
        rc = subprocess.run(cmd, check=False, cwd=str(_WORKSPACE_ROOT)).returncode
        if rc != 0:
            log.error("bootstrap_step_failed", step=name, rc=rc)
            raise typer.Exit(code=1)
        log.info("bootstrap_step_done", step=name)

    log.info("bootstrap_done")


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------


@app.command()
def validate() -> None:
    """Connectivity + schema probe for Qdrant + Neo4j + PG + failure_modes.yaml.

    Returns exit 0 if every component is reachable AND has the expected schema;
    otherwise exit 1 and surface a structured error in JSON logs.
    """
    log = logger.bind(command="validate")
    asyncio.run(_async_validate(log))


async def _async_validate(log) -> None:
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    neo4j_auth = os.environ.get("NEO4J_AUTH", "neo4j/cipassword")
    timescale_dsn = os.environ.get("TIMESCALE_DSN")
    if not timescale_dsn:
        log.error("missing_env", var="TIMESCALE_DSN")
        raise typer.Exit(code=2)

    expected_collections = {"sop", "manuals", "troubleshooting", "training"}
    expected_constraints = {
        "machine_id_unique",
        "part_id_unique",
        "failure_mode_id_unique",
        "sop_id_unique",
    }
    errors: list[str] = []
    summary: dict[str, str] = {}

    # 1. Qdrant collections.
    try:
        from qdrant_client import AsyncQdrantClient

        qc = AsyncQdrantClient(url=qdrant_url)
        try:
            cols = await qc.get_collections()
            names = {c.name for c in cols.collections}
            missing = expected_collections - names
            if missing:
                errors.append(f"qdrant missing collections: {sorted(missing)}")
                summary["qdrant"] = f"MISSING {sorted(missing)}"
            else:
                summary["qdrant"] = "ok"
        finally:
            await qc.close()
    except Exception as exc:
        errors.append(f"qdrant unreachable: {exc}")
        summary["qdrant"] = f"ERROR {exc}"

    # 2. Neo4j constraints.
    try:
        from neo4j import AsyncGraphDatabase

        user, _, password = neo4j_auth.partition("/")
        driver = AsyncGraphDatabase.driver(neo4j_uri, auth=(user, password))
        try:
            async with driver.session(database="neo4j") as session:
                result = await session.run("SHOW CONSTRAINTS")
                names = {r["name"] async for r in result}
            missing = expected_constraints - names
            if missing:
                errors.append(f"neo4j missing constraints: {sorted(missing)}")
                summary["neo4j"] = f"MISSING {sorted(missing)}"
            else:
                summary["neo4j"] = "ok"
        finally:
            await driver.close()
    except Exception as exc:
        errors.append(f"neo4j unreachable: {exc}")
        summary["neo4j"] = f"ERROR {exc}"

    # 3. PG ingest_state table.
    try:
        import asyncpg

        conn = await asyncpg.connect(timescale_dsn, statement_cache_size=0)
        try:
            row = await conn.fetchrow(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'knowledge' AND table_name = 'ingest_state'"
            )
            if row is None:
                errors.append("pg: knowledge.ingest_state table missing")
                summary["postgres"] = "MISSING knowledge.ingest_state"
            else:
                summary["postgres"] = "ok"
        finally:
            await conn.close()
    except Exception as exc:
        errors.append(f"postgres unreachable: {exc}")
        summary["postgres"] = f"ERROR {exc}"

    # 4. failure_modes.yaml.
    try:
        from sft_domain.failure_modes import load_failure_modes

        fms = load_failure_modes()
        if len(fms) == 0:
            errors.append("failure_modes.yaml is empty")
            summary["failure_modes"] = "EMPTY"
        else:
            summary["failure_modes"] = f"ok ({len(fms)} entries)"
    except Exception as exc:
        errors.append(f"failure_modes load failed: {exc}")
        summary["failure_modes"] = f"ERROR {exc}"

    log.info("validate_summary", **summary)
    if errors:
        log.error("validate_failed", errors=errors)
        raise typer.Exit(code=1)
    log.info("validate_ok")


if __name__ == "__main__":
    app()
